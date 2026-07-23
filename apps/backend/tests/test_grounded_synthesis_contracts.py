"""Phase 40B — Grounded Synthesis Layer contract tests (``grounded-synthesis.v1``).

Contract/validation only. These shapes have no producer, service, endpoint,
persistence, policy engine, or AI/LLM integration yet; the tests assert valid
construction for both synthesis modes, stable enum wire values, the mandatory
provenance/citation relationship, explicit insufficient-evidence handling,
bounded rejection of malformed input, deterministic serialization and ordering,
and — structurally and at runtime — that constructing a contract performs no
filesystem, Git, network, store, graph, clock, or randomness access.
"""

from __future__ import annotations

import ast
import inspect
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.models import grounded_synthesis as gs_module
from app.models.active_memory import (
    ConfidenceBand,
    ContradictionSeverity,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceType,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
)
from app.models.grounded_synthesis import (
    GROUNDED_SYNTHESIS_CONTRACT_VERSION,
    MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH,
    MAX_SYNTHESIS_EVIDENCE_REFERENCES,
    MAX_SYNTHESIS_METADATA_ENTRIES,
    PROPOSED_ARTIFACT_STATUSES,
    GroundedSynthesisArtifact,
    GroundedSynthesisArtifactSection,
    GroundedSynthesisMode,
    GroundedSynthesisRequest,
    GroundingEvidenceKind,
    GroundingEvidenceReference,
    SynthesisArtifactCategory,
    SynthesisConstraints,
    SynthesisContextPacket,
    SynthesisContextSummary,
    SynthesisEvidenceConflict,
    SynthesisGenerationMethod,
    SynthesisMissingContext,
    SynthesisProvenance,
    SynthesisReadinessStatus,
    SynthesisSourceCoverage,
    SynthesisValidationIssue,
    SynthesisValidationIssueCode,
    SynthesisValidationResult,
    SynthesisValidationStatus,
    SynthesisValidationSubject,
    SynthesisWarning,
    SynthesisWarningCode,
    derive_grounded_synthesis_id,
)

FIXED_TS = datetime(2026, 7, 1, 9, 30, 0)


# --------------------------------------------------------------------------- #
# Small builders
# --------------------------------------------------------------------------- #
def _evidence(evidence_id: str = "ev-1") -> GroundingEvidenceReference:
    return GroundingEvidenceReference(
        evidence_id=evidence_id,
        grounding_kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.COMMIT_HASH,
            value="ed52c26d6be239216e66c9773dd967f2f84ebf30",
        ),
    )


def _packet(**overrides: Any) -> SynthesisContextPacket:
    fields: dict[str, Any] = {
        "packet_id": "gs-packet-1",
        "request_id": "gs-request-1",
        "mode": GroundedSynthesisMode.LOOM,
        "readiness": SynthesisReadinessStatus.READY,
        "evidence_references": [_evidence()],
    }
    fields.update(overrides)
    return SynthesisContextPacket(**fields)


def _provenance(**overrides: Any) -> SynthesisProvenance:
    fields: dict[str, Any] = {
        "request_id": "gs-request-1",
        "context_packet_id": "gs-packet-1",
        "used_evidence_ids": ["ev-1"],
        "transformation_version": "grounded-synthesis.v1-phase-40b",
    }
    fields.update(overrides)
    return SynthesisProvenance(**fields)


def _artifact(**overrides: Any) -> GroundedSynthesisArtifact:
    fields: dict[str, Any] = {
        "artifact_id": "gs-artifact-1",
        "request_id": "gs-request-1",
        "mode": GroundedSynthesisMode.LOOM,
        "category": SynthesisArtifactCategory.IMPLEMENTATION_PROPOSAL,
        "citations": ["ev-1"],
        "provenance": _provenance(),
        "sections": [
            GroundedSynthesisArtifactSection(
                section_id="section-1",
                heading="Proposed approach",
                body="Assemble grounding from the existing observer snapshot.",
                evidence_ids=["ev-1"],
            )
        ],
    }
    fields.update(overrides)
    return GroundedSynthesisArtifact(**fields)


# =========================================================================== #
# Valid construction
# =========================================================================== #
def test_valid_musings_request() -> None:
    request = GroundedSynthesisRequest(
        request_id="gs-request-musings",
        mode=GroundedSynthesisMode.MUSINGS,
        objective="Explore why observer drift keeps reappearing after 39D.",
        requested_category=SynthesisArtifactCategory.MUSING,
        evidence_references=[_evidence()],
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="40B"),
        requesting_source=MemorySource(
            source_type=MemorySourceType.HUMAN, source_id="devdevbuilds"
        ),
        submitted_at=FIXED_TS,
    )
    assert request.schema_version == GROUNDED_SYNTHESIS_CONTRACT_VERSION
    assert request.mode is GroundedSynthesisMode.MUSINGS
    assert request.status is SynthesisReadinessStatus.DRAFT
    assert request.context_packet is None
    assert request.metadata == {}
    # Defaults are the safe values, not permissive ones.
    assert request.constraints.require_human_review is True
    assert request.constraints.prohibit_repository_writes is True
    assert request.constraints.prohibit_graph_mutation is True


def test_valid_loom_request_with_embedded_packet() -> None:
    packet = _packet()
    request = GroundedSynthesisRequest(
        request_id="gs-request-1",
        mode=GroundedSynthesisMode.LOOM,
        objective="Draft a work packet for the grounding assembly service.",
        context_packet_id="gs-packet-1",
        context_packet=packet,
        correlation_id="trace-40b",
    )
    assert request.context_packet is not None
    assert request.context_packet.packet_id == "gs-packet-1"
    assert request.correlation_id == "trace-40b"


def test_valid_evidence_reference_defaults() -> None:
    evidence = _evidence()
    assert evidence.evidence_type is None
    assert evidence.source is None
    assert evidence.scope is None
    assert evidence.observed_at is None
    assert evidence.confidence is None
    assert evidence.content_digest is None
    assert evidence.metadata == {}


def test_valid_evidence_reference_full() -> None:
    evidence = GroundingEvidenceReference(
        evidence_id="ev-active-memory",
        grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="rec-42"
        ),
        evidence_type=EvidenceType.REPOSITORY_COMMAND_OUTPUT,
        source=MemorySource(
            source_type=MemorySourceType.REPOSITORY_OBSERVER, source_id="repo-observer"
        ),
        source_record_id="rec-42",
        scope=MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id="hive-mind"),
        observed_at=FIXED_TS,
        confidence=ConfidenceBand.HIGH,
        label="observer snapshot",
        summary="Working tree clean at the locked baseline.",
        content_digest="deadbeefcafe1234",
        metadata={"phase": "40B"},
    )
    assert evidence.confidence is ConfidenceBand.HIGH
    assert evidence.content_digest == "deadbeefcafe1234"


def test_valid_context_packet_sections() -> None:
    packet = _packet(
        evidence_references=[_evidence("ev-1"), _evidence("ev-2")],
        context_summaries=[
            SynthesisContextSummary(
                summary_id="sum-1",
                label="Repository baseline",
                summary="Branch is aligned with origin/main.",
                evidence_ids=["ev-1"],
            )
        ],
        conflicts=[
            SynthesisEvidenceConflict(
                conflict_id="conflict-1",
                summary="Snapshot and drift disagree on the working-tree state.",
                evidence_ids=["ev-1", "ev-2"],
                severity=ContradictionSeverity.WARNING,
            )
        ],
        source_coverage=[
            SynthesisSourceCoverage(
                grounding_kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
                referenced_count=2,
            )
        ],
        warnings=[
            SynthesisWarning(
                code=SynthesisWarningCode.CONFLICTING_EVIDENCE,
                message="An unresolved conflict is present and was not resolved.",
                subject_id="conflict-1",
            )
        ],
        assembled_at=FIXED_TS,
    )
    assert packet.read_only is True
    assert packet.readiness is SynthesisReadinessStatus.READY
    assert len(packet.evidence_references) == 2


def test_valid_provenance_defaults_to_deterministic_generation() -> None:
    provenance = _provenance(excluded_evidence_ids=["ev-9"])
    assert provenance.generation_method is SynthesisGenerationMethod.DETERMINISTIC
    assert provenance.producer is None
    assert provenance.parent_artifact_id is None
    assert provenance.excluded_evidence_ids == ["ev-9"]
    # A single-member vocabulary: no model-backed producer is representable.
    assert [member.value for member in SynthesisGenerationMethod] == ["deterministic"]


def test_valid_proposed_artifact() -> None:
    artifact = _artifact(created_at=FIXED_TS)
    assert artifact.status is SynthesisReadinessStatus.PROPOSED
    assert artifact.human_review_required is True
    assert artifact.read_only is True
    assert artifact.citations == ["ev-1"]
    assert artifact.provenance.request_id == artifact.request_id


def test_valid_validation_results() -> None:
    valid = SynthesisValidationResult(
        subject=SynthesisValidationSubject.ARTIFACT,
        subject_id="gs-artifact-1",
        status=SynthesisValidationStatus.VALID,
    )
    assert valid.issues == []
    assert valid.human_review_required is True

    invalid = SynthesisValidationResult(
        subject=SynthesisValidationSubject.REQUEST,
        subject_id="gs-request-1",
        status=SynthesisValidationStatus.INVALID,
        issues=[
            SynthesisValidationIssue(
                code=SynthesisValidationIssueCode.INSUFFICIENT_EVIDENCE,
                message="No grounding evidence was supplied for the objective.",
                subject_id="gs-request-1",
            )
        ],
    )
    assert invalid.issues[0].code is SynthesisValidationIssueCode.INSUFFICIENT_EVIDENCE


def test_valid_serialization_round_trip() -> None:
    artifact = _artifact(created_at=FIXED_TS)
    payload = artifact.model_dump(mode="json")
    assert payload["schema_version"] == GROUNDED_SYNTHESIS_CONTRACT_VERSION
    assert payload["mode"] == "loom"
    assert payload["status"] == "proposed"
    restored = GroundedSynthesisArtifact.model_validate(payload)
    assert restored == artifact


# =========================================================================== #
# Invalid construction
# =========================================================================== #
def test_unsupported_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode="autonomous_agent",  # type: ignore[arg-type]
            objective="Do the work.",
        )


def test_unsupported_schema_version_rejected() -> None:
    for model, kwargs in (
        (
            GroundedSynthesisRequest,
            {
                "request_id": "gs-request-1",
                "mode": GroundedSynthesisMode.LOOM,
                "objective": "Draft a plan.",
            },
        ),
        (
            SynthesisContextPacket,
            {
                "packet_id": "gs-packet-1",
                "request_id": "gs-request-1",
                "mode": GroundedSynthesisMode.LOOM,
            },
        ),
        (
            SynthesisProvenance,
            {
                "request_id": "gs-request-1",
                "transformation_version": "v1",
            },
        ),
    ):
        with pytest.raises(ValidationError, match="unsupported schema_version"):
            model(schema_version="grounded-synthesis.v2", **kwargs)  # type: ignore[arg-type]


def test_empty_and_whitespace_identifiers_rejected() -> None:
    with pytest.raises(ValidationError):
        GroundedSynthesisRequest(
            request_id="   ",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
        )
    with pytest.raises(ValidationError):
        GroundingEvidenceReference(
            evidence_id="",
            grounding_kind=GroundingEvidenceKind.QUERY_TRAIL,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="a-1"
            ),
        )


def test_whitespace_only_objective_rejected() -> None:
    with pytest.raises(ValidationError, match="objective must not be empty"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.MUSINGS,
            objective="   \t\n ",
        )


def test_ungrounded_request_cannot_claim_a_grounded_status() -> None:
    with pytest.raises(ValidationError, match="requires a grounding reference"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan with no evidence at all.",
            status=SynthesisReadinessStatus.READY,
        )


def test_empty_packet_cannot_be_ready() -> None:
    with pytest.raises(ValidationError, match="cannot be 'ready'"):
        _packet(evidence_references=[])


def test_packet_with_missing_context_cannot_be_ready() -> None:
    with pytest.raises(ValidationError, match="unresolved missing context"):
        _packet(
            missing_context=[
                SynthesisMissingContext(
                    gap_id="gap-1",
                    description="No CI evidence for the current branch.",
                    required_evidence_kinds=[GroundingEvidenceKind.QUERY_TRAIL],
                )
            ]
        )


def test_packet_with_critical_conflict_cannot_be_ready() -> None:
    with pytest.raises(ValidationError, match="critical conflict"):
        _packet(
            evidence_references=[_evidence("ev-1"), _evidence("ev-2")],
            conflicts=[
                SynthesisEvidenceConflict(
                    conflict_id="conflict-critical",
                    summary="The repository baselines are irreconcilable.",
                    evidence_ids=["ev-1", "ev-2"],
                    severity=ContradictionSeverity.CRITICAL,
                )
            ],
        )


def test_ready_request_requires_ready_embedded_packet() -> None:
    with pytest.raises(ValidationError, match="embedded context_packet to be 'ready'"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            status=SynthesisReadinessStatus.READY,
            context_packet=_packet(readiness=SynthesisReadinessStatus.CONTEXT_REQUIRED),
        )


def test_artifact_requires_provenance() -> None:
    with pytest.raises(ValidationError):
        GroundedSynthesisArtifact(
            artifact_id="gs-artifact-1",
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            category=SynthesisArtifactCategory.DESIGN_BRIEF,
            citations=["ev-1"],
        )


def test_proposed_artifact_requires_evidence_and_citations() -> None:
    with pytest.raises(ValidationError, match="requires provenance evidence"):
        _artifact(
            citations=[],
            sections=[],
            provenance=_provenance(used_evidence_ids=[]),
        )
    with pytest.raises(ValidationError, match="must cite the evidence"):
        _artifact(citations=[], sections=[])


def test_citation_not_recorded_in_provenance_rejected() -> None:
    with pytest.raises(ValidationError, match="not recorded in provenance"):
        _artifact(citations=["ev-1", "ev-unlisted"])


def test_section_citing_unrecorded_evidence_rejected() -> None:
    with pytest.raises(ValidationError, match="cites evidence not recorded"):
        _artifact(
            sections=[
                GroundedSynthesisArtifactSection(
                    section_id="section-1",
                    heading="Approach",
                    body="Body",
                    evidence_ids=["ev-ghost"],
                )
            ]
        )


def test_excessive_evidence_references_rejected() -> None:
    too_many = [
        _evidence(f"ev-{index}") for index in range(MAX_SYNTHESIS_EVIDENCE_REFERENCES + 1)
    ]
    with pytest.raises(ValidationError):
        _packet(evidence_references=too_many)


def test_evidence_count_above_declared_constraint_rejected() -> None:
    with pytest.raises(ValidationError, match="exceeds the declared limit"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            evidence_references=[_evidence("ev-1"), _evidence("ev-2")],
            constraints=SynthesisConstraints(max_evidence_references=1),
        )


def test_excessive_artifact_content_rejected() -> None:
    oversized = "x" * 16_384
    sections = [
        GroundedSynthesisArtifactSection(
            section_id=f"section-{index}", heading="H", body=oversized
        )
        for index in range(5)
    ]
    assert sum(len(section.body) for section in sections) > (
        MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH
    )
    with pytest.raises(ValidationError, match="artifact content length"):
        _artifact(sections=sections)


def test_excessive_metadata_rejected() -> None:
    too_many = {f"key-{index}": index for index in range(MAX_SYNTHESIS_METADATA_ENTRIES + 1)}
    with pytest.raises(ValidationError, match="metadata exceeds"):
        _packet(metadata=too_many)
    with pytest.raises(ValidationError, match="metadata value exceeds"):
        _packet(metadata={"note": "y" * 2000})
    with pytest.raises(ValidationError, match="metadata key exceeds"):
        _packet(metadata={"k" * 200: "value"})


def test_deeply_nested_metadata_rejected() -> None:
    nested: dict[str, Any] = {"leaf": 1}
    for _ in range(10):
        nested = {"level": nested}
    with pytest.raises(ValidationError, match="too deeply nested"):
        _packet(metadata=nested)


def test_metadata_rejects_wide_non_finite_and_non_json_values() -> None:
    with pytest.raises(ValidationError, match="metadata container exceeds"):
        _packet(metadata={"nested": list(range(33))})
    with pytest.raises(ValidationError, match="must be finite"):
        _packet(metadata={"score": float("inf")})
    with pytest.raises(ValidationError, match="JSON-compatible"):
        _packet(metadata={"opaque": b"bytes"})


def test_provider_configuration_cannot_hide_in_metadata() -> None:
    for metadata in (
        {"provider": "openai"},
        {"runtime": {"temperature": 0.2}},
        {"runtime": {"API-KEY": "secret"}},
    ):
        with pytest.raises(ValidationError, match="provider/runtime metadata key"):
            _packet(metadata=metadata)


def test_invalid_artifact_status_rejected() -> None:
    for status in (
        SynthesisReadinessStatus.DRAFT,
        SynthesisReadinessStatus.CONTEXT_REQUIRED,
        SynthesisReadinessStatus.READY,
    ):
        assert status not in PROPOSED_ARTIFACT_STATUSES
        with pytest.raises(ValidationError, match="not a proposed-artifact status"):
            _artifact(status=status)
    with pytest.raises(ValidationError):
        _artifact(status="accepted")  # type: ignore[arg-type]


def test_malformed_evidence_type_and_grounding_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        GroundingEvidenceReference(
            evidence_id="ev-1",
            grounding_kind="repository_gossip",  # type: ignore[arg-type]
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="a-1"
            ),
        )
    with pytest.raises(ValidationError):
        GroundingEvidenceReference(
            evidence_id="ev-1",
            grounding_kind=GroundingEvidenceKind.SOURCE_REGISTRY_ENTRY,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="a-1"
            ),
            evidence_type="vibes",  # type: ignore[arg-type]
        )


def test_non_hex_content_digest_rejected() -> None:
    with pytest.raises(ValidationError, match="lowercase hexadecimal"):
        GroundingEvidenceReference(
            evidence_id="ev-1",
            grounding_kind=GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="a-1"
            ),
            content_digest="NOT-A-DIGEST",
        )


def test_duplicate_evidence_identifiers_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate evidence_id"):
        _packet(evidence_references=[_evidence("ev-1"), _evidence("ev-1")])
    with pytest.raises(ValidationError, match="duplicate used_evidence_ids"):
        _provenance(used_evidence_ids=["ev-1", "ev-1"])
    with pytest.raises(ValidationError, match="duplicate citations"):
        _artifact(citations=["ev-1", "ev-1"])


def test_duplicate_source_coverage_kind_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate source_coverage"):
        _packet(
            source_coverage=[
                SynthesisSourceCoverage(
                    grounding_kind=GroundingEvidenceKind.QUERY_TRAIL,
                    referenced_count=1,
                ),
                SynthesisSourceCoverage(
                    grounding_kind=GroundingEvidenceKind.QUERY_TRAIL,
                    referenced_count=2,
                ),
            ]
        )


def test_dangling_summary_and_conflict_references_rejected() -> None:
    with pytest.raises(ValidationError, match="references unknown evidence ids"):
        _packet(
            context_summaries=[
                SynthesisContextSummary(
                    summary_id="sum-1",
                    label="Baseline",
                    summary="Summary text.",
                    evidence_ids=["ev-ghost"],
                )
            ]
        )
    with pytest.raises(ValidationError, match="references unknown evidence ids"):
        _packet(
            evidence_references=[_evidence("ev-1"), _evidence("ev-2")],
            conflicts=[
                SynthesisEvidenceConflict(
                    conflict_id="conflict-1",
                    summary="Conflict text.",
                    evidence_ids=["ev-1", "ev-ghost"],
                )
            ],
        )


def test_conflict_requires_two_participants() -> None:
    with pytest.raises(ValidationError, match="at least two evidence ids"):
        SynthesisEvidenceConflict(
            conflict_id="conflict-1",
            summary="Only one side.",
            evidence_ids=["ev-1"],
        )


def test_conflicting_identifiers_rejected() -> None:
    packet = _packet()
    with pytest.raises(ValidationError, match="context_packet.request_id must match"):
        GroundedSynthesisRequest(
            request_id="gs-request-other",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            context_packet=packet,
        )
    with pytest.raises(ValidationError, match="context_packet.mode must match"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.MUSINGS,
            objective="Draft a plan.",
            context_packet=packet,
        )
    with pytest.raises(ValidationError, match="disagrees with the embedded"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            context_packet_id="gs-packet-other",
            context_packet=packet,
        )
    with pytest.raises(ValidationError, match="provenance.request_id must match"):
        _artifact(provenance=_provenance(request_id="gs-request-other"))


def test_evidence_cannot_be_both_used_and_excluded() -> None:
    with pytest.raises(ValidationError, match="both used and excluded"):
        _provenance(used_evidence_ids=["ev-1"], excluded_evidence_ids=["ev-1"])


def test_requested_category_outside_allowlist_rejected() -> None:
    with pytest.raises(ValidationError, match="not in the declared"):
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            requested_category=SynthesisArtifactCategory.PATCH_PROPOSAL,
            constraints=SynthesisConstraints(
                allowed_artifact_categories=[SynthesisArtifactCategory.TEST_PLAN]
            ),
        )


def test_booleans_supplied_as_integers_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be a boolean"):
        SynthesisConstraints(max_evidence_references=True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="must not be a boolean"):
        SynthesisSourceCoverage(
            grounding_kind=GroundingEvidenceKind.QUERY_TRAIL,
            referenced_count=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError, match="must be a boolean"):
        SynthesisConstraints(require_human_review=1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="must be a boolean"):
        _artifact(read_only=1)  # type: ignore[arg-type]


def test_negative_limits_rejected() -> None:
    with pytest.raises(ValidationError):
        SynthesisConstraints(max_evidence_references=-1)
    with pytest.raises(ValidationError):
        SynthesisConstraints(max_artifact_content_length=0)
    with pytest.raises(ValidationError):
        SynthesisSourceCoverage(
            grounding_kind=GroundingEvidenceKind.QUERY_TRAIL, referenced_count=-1
        )


def test_safety_flags_cannot_be_disabled() -> None:
    for field in (
        "require_human_review",
        "prohibit_repository_writes",
        "prohibit_graph_mutation",
    ):
        with pytest.raises(ValidationError, match="must remain True"):
            SynthesisConstraints(**{field: False})
    with pytest.raises(ValidationError, match="human_review_required must remain True"):
        _artifact(human_review_required=False)
    with pytest.raises(ValidationError, match="read_only must remain True"):
        _artifact(read_only=False)
    with pytest.raises(ValidationError, match="read_only must remain True"):
        _packet(read_only=False)


def test_validation_result_cannot_be_valid_with_issues() -> None:
    issue = SynthesisValidationIssue(
        code=SynthesisValidationIssueCode.MALFORMED_REFERENCE,
        message="Reference value was blank.",
    )
    with pytest.raises(ValidationError, match="must carry no issues"):
        SynthesisValidationResult(
            subject=SynthesisValidationSubject.PROVENANCE,
            subject_id="gs-request-1",
            status=SynthesisValidationStatus.VALID,
            issues=[issue],
        )
    with pytest.raises(ValidationError, match="must carry at least one issue"):
        SynthesisValidationResult(
            subject=SynthesisValidationSubject.PROVENANCE,
            subject_id="gs-request-1",
            status=SynthesisValidationStatus.INVALID,
        )


def test_unexpected_extra_fields_rejected() -> None:
    """Provider/model configuration cannot ride in on an unknown key."""

    for extra in (
        {"model": "claude-opus-4-8"},
        {"temperature": 0.7},
        {"max_tokens": 4096},
        {"prompt_template": "You are a helpful assistant."},
        {"api_key": "sk-test"},
        {"agent_directive": "commit the change"},
    ):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            GroundedSynthesisRequest(
                request_id="gs-request-1",
                mode=GroundedSynthesisMode.LOOM,
                objective="Draft a plan.",
                **extra,  # type: ignore[arg-type]
            )


def test_no_provider_specific_fields_exist_on_the_contracts() -> None:
    forbidden = {
        "model",
        "model_name",
        "provider",
        "temperature",
        "top_p",
        "max_tokens",
        "token_budget",
        "prompt",
        "prompt_template",
        "system_prompt",
        "api_key",
        "api_base",
        "credentials",
        "agent_directive",
    }
    for model in (
        GroundedSynthesisRequest,
        SynthesisContextPacket,
        SynthesisConstraints,
        GroundingEvidenceReference,
        SynthesisProvenance,
        GroundedSynthesisArtifact,
        SynthesisValidationResult,
    ):
        assert not forbidden & set(model.model_fields), model.__name__


def test_mutable_defaults_do_not_leak_between_instances() -> None:
    first = GroundedSynthesisRequest(
        request_id="gs-request-1",
        mode=GroundedSynthesisMode.LOOM,
        objective="First objective.",
    )
    second = GroundedSynthesisRequest(
        request_id="gs-request-2",
        mode=GroundedSynthesisMode.LOOM,
        objective="Second objective.",
    )
    first.evidence_references.append(_evidence())
    first.metadata["touched"] = True
    assert second.evidence_references == []
    assert second.metadata == {}
    assert SynthesisConstraints().allowed_artifact_categories == []


# =========================================================================== #
# Determinism
# =========================================================================== #
def test_enum_wire_values_are_stable() -> None:
    assert GROUNDED_SYNTHESIS_CONTRACT_VERSION == "grounded-synthesis.v1"
    assert [member.value for member in GroundedSynthesisMode] == ["musings", "loom"]
    assert [member.value for member in SynthesisReadinessStatus] == [
        "draft",
        "context_required",
        "ready",
        "insufficient_evidence",
        "blocked",
        "proposed",
        "validation_failed",
        "human_review_required",
    ]
    assert [member.value for member in SynthesisValidationStatus] == ["valid", "invalid"]
    assert [member.value for member in SynthesisValidationIssueCode] == [
        "invalid_request",
        "insufficient_evidence",
        "unsupported_mode",
        "unsupported_artifact_category",
        "conflicting_evidence",
        "constraint_violation",
        "malformed_reference",
        "missing_provenance",
        "duplicate_evidence_reference",
        "bounds_exceeded",
    ]
    assert [member.value for member in GroundingEvidenceKind] == [
        "repository_observation",
        "repository_drift_finding",
        "active_memory_record",
        "active_memory_evidence_record",
        "contradiction_record",
        "context_packet_entry",
        "knowledge_graph_node",
        "source_registry_entry",
        "query_trail",
    ]


def test_no_status_implies_acceptance_or_mutation() -> None:
    forbidden = {
        "accepted",
        "approved",
        "canonical",
        "committed",
        "merged",
        "applied",
        "published",
        "written",
    }
    assert not forbidden & {member.value for member in SynthesisReadinessStatus}
    assert not forbidden & {member.value for member in SynthesisArtifactCategory}


def test_serialization_is_byte_stable() -> None:
    artifact = _artifact(created_at=FIXED_TS)
    first = artifact.model_dump_json()
    second = _artifact(created_at=FIXED_TS).model_dump_json()
    assert first == second


def test_normalized_packet_ordering_is_deterministic() -> None:
    packet = _packet(
        evidence_references=[_evidence("ev-b"), _evidence("ev-a")],
        context_summaries=[
            SynthesisContextSummary(
                summary_id="sum-b", label="B", summary="B", evidence_ids=["ev-b"]
            ),
            SynthesisContextSummary(
                summary_id="sum-a", label="A", summary="A", evidence_ids=["ev-a"]
            ),
        ],
        source_coverage=[
            SynthesisSourceCoverage(
                grounding_kind=GroundingEvidenceKind.QUERY_TRAIL, referenced_count=1
            ),
            SynthesisSourceCoverage(
                grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
                referenced_count=1,
            ),
        ],
    )
    normalized = packet.normalized()
    assert [item.evidence_id for item in normalized.evidence_references] == [
        "ev-a",
        "ev-b",
    ]
    assert [item.summary_id for item in normalized.context_summaries] == [
        "sum-a",
        "sum-b",
    ]
    assert [item.grounding_kind.value for item in normalized.source_coverage] == [
        "active_memory_record",
        "query_trail",
    ]
    # Normalizing is idempotent and does not mutate the original.
    assert normalized.normalized().model_dump_json() == normalized.model_dump_json()
    assert [item.evidence_id for item in packet.evidence_references] == ["ev-b", "ev-a"]


def test_round_trip_equality_for_every_top_level_contract() -> None:
    packet = _packet()
    for instance in (
        packet,
        GroundedSynthesisRequest(
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            objective="Draft a plan.",
            context_packet=packet,
        ),
        _provenance(),
        _artifact(created_at=FIXED_TS),
        SynthesisValidationResult(
            subject=SynthesisValidationSubject.ARTIFACT,
            subject_id="gs-artifact-1",
            status=SynthesisValidationStatus.VALID,
        ),
    ):
        restored = type(instance).model_validate(instance.model_dump(mode="json"))
        assert restored == instance


def test_derived_identifiers_are_pure_functions_of_their_inputs() -> None:
    first = derive_grounded_synthesis_id("gs-packet", "gs-request-1", "ev-1")
    second = derive_grounded_synthesis_id("gs-packet", "gs-request-1", "ev-1")
    assert first == second
    assert first.startswith("gs-packet-")
    assert first != derive_grounded_synthesis_id("gs-packet", "gs-request-1", "ev-2")
    # Whitespace is normalized before hashing, so equivalent inputs agree.
    assert first == derive_grounded_synthesis_id(" gs-packet ", " gs-request-1 ", " ev-1 ")
    with pytest.raises(ValueError, match="at least one input part"):
        derive_grounded_synthesis_id("gs-packet")
    with pytest.raises(ValueError, match="must not be empty"):
        derive_grounded_synthesis_id("gs-packet", "   ")


def test_derived_identifier_part_boundaries_are_unambiguous() -> None:
    assert derive_grounded_synthesis_id("gs", "ab", "c") != (
        derive_grounded_synthesis_id("gs", "a", "bc")
    )
    assert derive_grounded_synthesis_id("gs", "a\x1fb", "c") != (
        derive_grounded_synthesis_id("gs", "a", "b\x1fc")
    )
    assert derive_grounded_synthesis_id("gs", "a", "b") != (
        derive_grounded_synthesis_id("gs", "b", "a")
    )


def test_derived_identifier_unicode_normalization_is_explicit() -> None:
    composed = "caf\u00e9"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed
    assert derive_grounded_synthesis_id("gs", composed) == (
        derive_grounded_synthesis_id("gs", decomposed)
    )


def test_no_timestamp_or_identifier_is_auto_populated() -> None:
    """Caller-owned clock: nothing defaults to 'now', nothing invents an id."""

    request = GroundedSynthesisRequest(
        request_id="gs-request-1",
        mode=GroundedSynthesisMode.MUSINGS,
        objective="Draft a plan.",
    )
    assert request.submitted_at is None
    packet = _packet()
    assert packet.assembled_at is None
    artifact = _artifact()
    assert artifact.created_at is None
    # Two constructions moments apart are byte-identical.
    assert _artifact().model_dump_json() == _artifact().model_dump_json()


# =========================================================================== #
# Boundary separation
# =========================================================================== #
def test_contract_module_imports_no_io_or_nondeterminism() -> None:
    """Structural proof that the contract module cannot reach the outside world.

    Parsing the module's own AST is cheaper and more honest than mocking
    dependencies it does not have: if a later change adds a Git call, a store
    query, a clock read, or a random identifier, the import or attribute simply
    will not be there to add without failing this test.
    """

    source = Path(inspect.getfile(gs_module)).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden_modules = {
        "subprocess",
        "socket",
        "os",
        "shutil",
        "sqlite3",
        "random",
        "secrets",
        "uuid",
        "time",
        "urllib",
        "http",
        "httpx",
        "requests",
        "anthropic",
        "openai",
        "pathlib",
        "tempfile",
    }
    assert not forbidden_modules & imported

    # Allowed imports only: stdlib hashing/typing/enum, pydantic, and the
    # existing pure in-repo contract + validation helpers.
    assert imported <= {
        "__future__",
        "app",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "math",
        "pydantic",
        "typing",
        "unicodedata",
    }

    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    forbidden_calls = {
        "open",
        "now",
        "utcnow",
        "today",
        "time",
        "uuid4",
        "uuid1",
        "getenv",
        "run",
        "check_output",
        "Popen",
        "connect",
        "get",
        "post",
        "exec",
        "eval",
        "__import__",
    }
    assert not forbidden_calls & called_names


def test_constructing_contracts_performs_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runtime proof: with I/O primitives poisoned, every contract still builds."""

    import builtins
    import socket
    import subprocess

    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("grounded synthesis contracts must perform no I/O")

    monkeypatch.setattr(builtins, "open", _explode)
    monkeypatch.setattr(subprocess, "run", _explode)
    monkeypatch.setattr(subprocess, "Popen", _explode)
    monkeypatch.setattr(socket, "socket", _explode)

    packet = _packet()
    request = GroundedSynthesisRequest(
        request_id="gs-request-1",
        mode=GroundedSynthesisMode.LOOM,
        objective="Draft a plan.",
        context_packet=packet,
    )
    artifact = _artifact(created_at=FIXED_TS)
    result = SynthesisValidationResult(
        subject=SynthesisValidationSubject.ARTIFACT,
        subject_id=artifact.artifact_id,
        status=SynthesisValidationStatus.VALID,
    )
    for instance in (packet, request, artifact, result):
        assert instance.model_dump_json()
    assert derive_grounded_synthesis_id("gs-packet", "gs-request-1")


def test_contracts_expose_no_write_or_synthesis_behavior() -> None:
    """The family is data + validation: no persist/apply/synthesize surface."""

    forbidden_methods = {
        "save",
        "persist",
        "write",
        "commit",
        "push",
        "merge",
        "apply",
        "insert",
        "delete",
        "mutate",
        "synthesize",
        "generate",
        "produce",
        "execute",
        "run",
        "export",
        "approve",
        "accept",
    }
    for model in (
        GroundedSynthesisRequest,
        SynthesisContextPacket,
        SynthesisConstraints,
        GroundingEvidenceReference,
        SynthesisProvenance,
        GroundedSynthesisArtifact,
        SynthesisValidationResult,
    ):
        declared = {
            name
            for name, value in vars(model).items()
            if callable(value) and not name.startswith("_")
        }
        assert not forbidden_methods & declared, model.__name__

    # Functions the module itself defines (imported helpers excluded): the only
    # public one is the pure identifier derivation helper.
    module_callables = {
        name
        for name, value in vars(gs_module).items()
        if inspect.isfunction(value)
        and not name.startswith("_")
        and value.__module__ == gs_module.__name__
    }
    assert module_callables == {"derive_grounded_synthesis_id"}
