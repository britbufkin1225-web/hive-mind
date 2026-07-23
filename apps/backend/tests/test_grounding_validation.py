"""Phase 40D — Grounded Synthesis validation guardrail tests.

Focused coverage of the deterministic, read-only packet validator: evidence
identity, provenance resolution, repository/source safety, packet
self-consistency, bounds and truncation claims, readiness determination, and the
stability and secret-safety properties the diagnostics promise.

Two fixture styles, used deliberately:

* **canonical typed fixtures** for everything a legitimate producer can build —
  hand-assembled :class:`SynthesisContextPacket` records and real Phase 40C
  assemblies;
* **``model_copy`` tampering** for the cases the Phase 40B model makes
  unreachable through normal construction. Those cases are the entire reason
  Phase 40D exists: a packet that reaches a future synthesis stage by any path
  other than full model construction must still be caught, so the guardrails are
  proven against a packet that was edited after it was validated.

Every test drives the pure core from explicit fixtures — no store, no clock, no
Git, no filesystem, no network — so a passing run proves determinism rather than
assuming it.
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

from app.models.active_memory import (
    ClaimValueKind,
    ConfidenceBand,
    ContradictionClass,
    ContradictionRecord,
    ContradictionResolutionState,
    ContradictionSeverity,
    EvidenceRecord,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceType,
    LifecycleState,
    MemoryClaim,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models.grounded_synthesis import (
    GROUNDED_SYNTHESIS_CONTRACT_VERSION,
    MAX_SYNTHESIS_LABEL_LENGTH,
    GroundedSynthesisMode,
    GroundedSynthesisRequest,
    GroundingEvidenceKind,
    GroundingEvidenceReference,
    SynthesisContextPacket,
    SynthesisContextSummary,
    SynthesisEvidenceConflict,
    SynthesisMissingContext,
    SynthesisReadinessStatus,
    SynthesisSourceCoverage,
    SynthesisValidationStatus,
    SynthesisValidationSubject,
    SynthesisWarning,
    SynthesisWarningCode,
)
from app.models.grounded_synthesis_validation import (
    DIAGNOSTIC_ISSUE_CODE,
    DIAGNOSTIC_SEVERITY,
    GROUNDED_SYNTHESIS_VALIDATION_VERSION,
    GroundingDiagnosticCode,
    GroundingDiagnosticSeverity,
    GroundingValidationDiagnostic,
    SynthesisPacketValidationReport,
)
from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    RepositoryEvidence,
    RepositoryIdentity,
    RepositoryIdentityStatus,
    RepositorySnapshot,
    SnapshotCompleteness,
    TruncationState,
)
from app.services import grounding_validation as gv_module
from app.services.grounding_context import (
    GROUNDING_CONTEXT_ASSEMBLY_VERSION,
    GroundingAssemblyLimits,
    GroundingEvidenceSources,
    assemble_grounding_context,
)
from app.services.grounding_validation import (
    SynthesisContextPacketValidator,
    validate_synthesis_context_packet,
)

FIXED_TS = datetime(2026, 7, 1, 9, 30, 0)
ASSEMBLED_AT = datetime(2026, 7, 2, 8, 0, 0)
REPOSITORY_ID = "repo-hive-mind"
ABSOLUTE_PATH = "C:/Users/britb/Documents/hive-mind/apps/backend/app/main.py"
CREDENTIAL_URL = "https://svc-user:s3cr3t-token@example.invalid/hive-mind.git"


# --------------------------------------------------------------------------- #
# Builders — canonical typed fixtures
# --------------------------------------------------------------------------- #
def _observer_source() -> MemorySource:
    return MemorySource(
        source_type=MemorySourceType.REPOSITORY_OBSERVER,
        source_id="repository-observer:observer.v1",
    )


_OMITTED: Any = object()
"""Sentinel distinguishing "argument omitted" from an explicit ``None``.

``source=None`` is a meaningful fixture — it builds a reference with no declared
producer — so the builder cannot use ``None`` as its own default.
"""


def _reference(
    evidence_id: str = "gs-ev-1",
    *,
    kind: GroundingEvidenceKind = GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
    reference: EvidenceReference | None = None,
    source_record_id: str | None = "ev-1",
    source: Any = _OMITTED,
    evidence_type: EvidenceType | None = EvidenceType.COMMIT,
    scope: MemoryScope | None = None,
    label: str | None = "commit evidence ev-1",
    summary: str | None = "Commit landing the assembly service.",
    confidence: ConfidenceBand | None = None,
    observed_at: datetime | None = FIXED_TS,
    metadata: dict[str, Any] | None = None,
) -> GroundingEvidenceReference:
    return GroundingEvidenceReference(
        evidence_id=evidence_id,
        grounding_kind=kind,
        reference=reference
        or EvidenceReference(
            reference_kind=EvidenceReferenceKind.COMMIT_HASH,
            value="333deaa308417217653ea89276a2bfd97efd855e",
        ),
        evidence_type=evidence_type,
        source=(
            MemorySource(
                source_type=MemorySourceType.REPOSITORY_OBSERVER, source_id="observer"
            )
            if source is _OMITTED
            else source
        ),
        source_record_id=source_record_id,
        scope=scope,
        observed_at=observed_at,
        confidence=confidence,
        label=label,
        summary=summary,
        metadata=dict(metadata or {}),
    )


def _packet(
    *,
    packet_id: str = "gs-packet-hand-built",
    request_id: str = "gs-request-1",
    readiness: SynthesisReadinessStatus = SynthesisReadinessStatus.READY,
    evidence_references: list[GroundingEvidenceReference] | None = None,
    context_summaries: list[SynthesisContextSummary] | None = None,
    conflicts: list[SynthesisEvidenceConflict] | None = None,
    missing_context: list[SynthesisMissingContext] | None = None,
    source_coverage: list[SynthesisSourceCoverage] | None = None,
    warnings: list[SynthesisWarning] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SynthesisContextPacket:
    return SynthesisContextPacket(
        packet_id=packet_id,
        request_id=request_id,
        mode=GroundedSynthesisMode.LOOM,
        readiness=readiness,
        evidence_references=(
            [_reference()] if evidence_references is None else evidence_references
        ),
        context_summaries=context_summaries or [],
        conflicts=conflicts or [],
        missing_context=missing_context or [],
        source_coverage=source_coverage or [],
        warnings=warnings or [],
        assembled_at=ASSEMBLED_AT,
        metadata=dict(metadata or {}),
    )


def _memory_record(record_id: str = "mem-1") -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        kind=MemoryRecordKind.PROJECT_FACT,
        claim=MemoryClaim(
            subject="phase-40d",
            predicate="status",
            value="in_progress",
            value_kind=ClaimValueKind.ENUM,
            summary="Phase 40D validates assembled grounding.",
        ),
        project_id="hive-mind",
        source=MemorySource(
            source_type=MemorySourceType.CLAUDE_CODE, source_id="claude-code"
        ),
        verification_state=VerificationState.VERIFIED,
        lifecycle_state=LifecycleState.ACTIVE,
        confidence=ConfidenceBand.HIGH,
        observed_at=FIXED_TS,
        created_at=FIXED_TS,
    )


def _evidence_record(evidence_id: str = "ev-1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type=EvidenceType.COMMIT,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.COMMIT_HASH,
            value="333deaa308417217653ea89276a2bfd97efd855e",
        ),
        source=_observer_source(),
        captured_at=FIXED_TS,
        summary="Commit landing the assembly service.",
    )


def _contradiction(
    contradiction_id: str = "contra-1",
    *,
    involved: tuple[str, ...] = ("mem-1", "ev-1"),
    severity: ContradictionSeverity | None = ContradictionSeverity.WARNING,
) -> ContradictionRecord:
    return ContradictionRecord(
        contradiction_id=contradiction_id,
        contradiction_class=ContradictionClass.PENDING_VS_MERGED,
        involved_record_ids=list(involved),
        summary="Two records disagree about merge status.",
        detection_source=MemorySource(
            source_type=MemorySourceType.CLI_REPORT, source_id="detector"
        ),
        detected_at=FIXED_TS,
        resolution_state=ContradictionResolutionState.OPEN,
        severity=severity,
    )


def _snapshot(
    *, status: RepositoryIdentityStatus = RepositoryIdentityStatus.VERIFIED
) -> RepositorySnapshot:
    return RepositorySnapshot(
        snapshot_id="snap-1",
        repository_identity=RepositoryIdentity(
            repository_id=REPOSITORY_ID,
            canonical_root="C:/Users/britb/Documents/hive-mind",
            normalized_root="c:/users/britb/documents/hive-mind",
            repository_name="hive-mind",
            status=status,
        ),
        observed_at=FIXED_TS,
        branch="main",
        commit="333deaa308417217653ea89276a2bfd97efd855e",
        evidence=[
            RepositoryEvidence(
                evidence_id="obs-ev-1",
                category=EvidenceCategory.GIT_METADATA,
                authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
                source="git status --porcelain=v2",
                summary="Working tree is clean.",
                digest="a1b2c3d4",
                captured_at=FIXED_TS,
                truncation_state=TruncationState.NOT_TRUNCATED,
            )
        ],
        completeness=SnapshotCompleteness.COMPLETE,
    )


def _request(**overrides: Any) -> GroundedSynthesisRequest:
    fields: dict[str, Any] = {
        "request_id": "gs-request-1",
        "mode": GroundedSynthesisMode.LOOM,
        "objective": "Assemble grounding for the next repository change.",
    }
    fields.update(overrides)
    return GroundedSynthesisRequest(**fields)


def _assembled(
    *,
    evidence: GroundingEvidenceSources | None = None,
    request: GroundedSynthesisRequest | None = None,
) -> SynthesisContextPacket:
    """A real Phase 40C packet — the integration fixture."""

    return assemble_grounding_context(
        request or _request(),
        evidence=evidence
        or GroundingEvidenceSources(
            memory_records=[_memory_record()], evidence_records=[_evidence_record()]
        ),
        assembled_at=ASSEMBLED_AT,
    )


def _codes(report: SynthesisPacketValidationReport) -> list[GroundingDiagnosticCode]:
    return [diagnostic.code for diagnostic in report.diagnostics]


def _tamper(packet: SynthesisContextPacket, **updates: Any) -> SynthesisContextPacket:
    """Edit a packet *after* construction, bypassing the Phase 40B validators.

    ``model_copy`` does not re-run validation, which is precisely the shape of
    the threat Phase 40D guards: a packet that was valid when it was built and
    was modified afterwards.
    """

    return packet.model_copy(update=updates)


# =========================================================================== #
# Valid packet
# =========================================================================== #
def test_canonical_assembled_packet_is_synthesis_ready() -> None:
    report = validate_synthesis_context_packet(_assembled())

    assert report.diagnostics == []
    assert report.synthesis_ready is True
    assert report.assessed_readiness is SynthesisReadinessStatus.READY
    assert report.declared_readiness is SynthesisReadinessStatus.READY
    assert report.evidence_count == 2
    assert report.family_count == 2
    assert report.schema_version == GROUNDED_SYNTHESIS_CONTRACT_VERSION
    assert report.validation_version == GROUNDED_SYNTHESIS_VALIDATION_VERSION
    assert report.read_only is True


def test_hand_built_packet_without_assembly_claims_validates_cleanly() -> None:
    report = validate_synthesis_context_packet(_packet())

    assert report.diagnostics == []
    assert report.synthesis_ready is True


def test_validation_does_not_mutate_the_packet() -> None:
    packet = _assembled()
    before = packet.model_dump_json()

    validate_synthesis_context_packet(packet)

    assert packet.model_dump_json() == before


def test_validation_does_not_mutate_a_failing_packet() -> None:
    packet = _tamper(_assembled(), correlation_id="tampered-correlation")
    before = packet.model_dump_json()

    report = validate_synthesis_context_packet(packet)

    assert report.synthesis_ready is False
    assert packet.model_dump_json() == before


def test_repeated_validation_is_identical() -> None:
    packet = _assembled()
    validator = SynthesisContextPacketValidator()

    first = validator.validate(packet)
    second = validator.validate(packet)

    assert first.model_dump() == second.model_dump()


def test_module_wrapper_matches_the_service() -> None:
    packet = _assembled()

    assert (
        validate_synthesis_context_packet(packet).model_dump()
        == SynthesisContextPacketValidator().validate(packet).model_dump()
    )


def test_valid_report_projects_onto_the_canonical_validation_result() -> None:
    packet = _assembled()

    result = validate_synthesis_context_packet(packet).to_validation_result()

    assert result.status is SynthesisValidationStatus.VALID
    assert result.subject is SynthesisValidationSubject.CONTEXT_PACKET
    assert result.subject_id == packet.packet_id
    assert result.issues == []
    assert result.human_review_required is True


def test_empty_packet_is_advised_not_blocked() -> None:
    packet = _packet(
        readiness=SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE,
        evidence_references=[],
    )

    report = validate_synthesis_context_packet(packet)

    assert _codes(report) == [GroundingDiagnosticCode.NO_GROUNDING_EVIDENCE]
    assert report.blocking_diagnostics == []
    assert report.synthesis_ready is False
    assert report.assessed_readiness is SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE
    assert report.to_validation_result().status is SynthesisValidationStatus.VALID


# =========================================================================== #
# Evidence identity
# =========================================================================== #
def test_identical_duplicate_canonical_identity_is_advisory() -> None:
    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1"),
            _reference("gs-ev-2"),
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert _codes(report) == [GroundingDiagnosticCode.REDUNDANT_EVIDENCE_IDENTITY]
    assert report.synthesis_ready is True


def test_materially_conflicting_duplicate_identity_blocks() -> None:
    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1", summary="Commit landed on main."),
            _reference("gs-ev-2", summary="Commit was reverted."),
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY in _codes(report)
    assert report.synthesis_ready is False
    assert report.assessed_readiness is SynthesisReadinessStatus.BLOCKED


def test_conflicting_source_identity_blocks_with_its_own_code() -> None:
    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1"),
            _reference(
                "gs-ev-2",
                source=MemorySource(
                    source_type=MemorySourceType.HUMAN, source_id="brit"
                ),
            ),
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.CONFLICTING_SOURCE_IDENTITY in _codes(report)
    assert GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY not in _codes(report)
    assert report.synthesis_ready is False


def test_same_provider_id_in_separate_families_is_not_collapsed() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                "gs-ev-1",
                kind=GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
                source_record_id="shared-1",
            ),
            _reference(
                "gs-ev-2",
                kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
                source_record_id="shared-1",
                evidence_type=None,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID,
                    value="shared-1",
                ),
            ),
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert report.diagnostics == []
    assert report.family_count == 2


def test_unicode_normalized_identity_collision_is_detected() -> None:
    composed = unicodedata.normalize("NFC", "café-record")
    decomposed = unicodedata.normalize("NFD", "café-record")
    assert composed != decomposed

    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1", source_record_id=composed),
            _reference("gs-ev-2", source_record_id=decomposed),
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY in _codes(report)


def test_duplicate_evidence_identifier_is_detected_on_a_tampered_packet() -> None:
    packet = _tamper(
        _packet(),
        evidence_references=[_reference("gs-ev-1"), _reference("gs-ev-1")],
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.DUPLICATE_EVIDENCE_IDENTIFIER in _codes(report)
    assert report.synthesis_ready is False


def test_unsupported_grounding_family_blocks() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                "gs-ev-1",
                kind=GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="node-1"
                ),
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    codes = _codes(report)
    assert GroundingDiagnosticCode.UNSUPPORTED_GROUNDING_KIND in codes
    diagnostic = next(
        item
        for item in report.diagnostics
        if item.code is GroundingDiagnosticCode.UNSUPPORTED_GROUNDING_KIND
    )
    assert diagnostic.grounding_kind is GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE
    assert report.synthesis_ready is False


def test_validation_is_independent_of_evidence_order() -> None:
    references = [
        _reference("gs-ev-1", summary="Commit landed on main."),
        _reference("gs-ev-2", summary="Commit was reverted."),
        _reference(
            "gs-ev-3",
            kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
            source_record_id="mem-9",
            evidence_type=None,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-9"
            ),
        ),
    ]

    forward = validate_synthesis_context_packet(_packet(evidence_references=references))
    reverse = validate_synthesis_context_packet(
        _packet(evidence_references=list(reversed(references)))
    )

    assert [item.model_dump() for item in forward.diagnostics] == [
        item.model_dump() for item in reverse.diagnostics
    ]
    assert forward.assessed_readiness is reverse.assessed_readiness


# =========================================================================== #
# Provenance
# =========================================================================== #
def test_missing_source_record_identifier_blocks() -> None:
    packet = _packet(evidence_references=[_reference(source_record_id=None)])

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.MISSING_PROVENANCE_REFERENCE in _codes(report)
    assert report.synthesis_ready is False


def test_repository_family_without_a_producing_source_blocks() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
                source_record_id="snap-1:obs-ev-1",
                source=None,
                evidence_type=EvidenceType.SOURCE_CODE,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.FILE_PATH,
                    value="apps/backend/app/main.py",
                ),
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.MISSING_PROVENANCE_SOURCE in _codes(report)
    assert report.synthesis_ready is False


def test_unexpected_provenance_pointer_kind_is_advisory() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
                source_record_id="mem-1",
                evidence_type=None,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.EXTERNAL_SOURCE_ID,
                    value="external-1",
                ),
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert _codes(report) == [
        GroundingDiagnosticCode.UNEXPECTED_PROVENANCE_REFERENCE_KIND
    ]
    assert report.synthesis_ready is True


def test_dangling_conflict_reference_blocks() -> None:
    packet = _tamper(
        _packet(
            evidence_references=[_reference("gs-ev-1"), _reference("gs-ev-2")],
            conflicts=[
                SynthesisEvidenceConflict(
                    conflict_id="gs-conflict-1",
                    summary="Two records disagree.",
                    evidence_ids=["gs-ev-1", "gs-ev-2"],
                    severity=ContradictionSeverity.WARNING,
                )
            ],
        ),
        evidence_references=[_reference("gs-ev-1")],
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE in _codes(report)
    assert report.synthesis_ready is False


def test_ungrounded_context_summary_blocks() -> None:
    packet = _packet(
        context_summaries=[
            SynthesisContextSummary(
                summary_id="gs-sum-1",
                label="Repository state",
                summary="Everything looks fine.",
                evidence_ids=[],
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNGROUNDED_CONTEXT_SUMMARY in _codes(report)
    assert report.synthesis_ready is False


def test_assembler_declared_packet_carrying_summaries_blocks() -> None:
    packet = _tamper(
        _assembled(),
        context_summaries=[
            SynthesisContextSummary(
                summary_id="gs-sum-1",
                label="Repository state",
                summary="A narrative the assembler never produced.",
                evidence_ids=[],
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    codes = _codes(report)
    assert GroundingDiagnosticCode.UNEXPECTED_CONTEXT_SUMMARY in codes
    assert GroundingDiagnosticCode.UNGROUNDED_CONTEXT_SUMMARY in codes
    assert report.synthesis_ready is False


# =========================================================================== #
# Repository and source safety
# =========================================================================== #
def test_unsafe_repository_identity_blocks_and_stays_visible() -> None:
    packet = _assembled(
        evidence=GroundingEvidenceSources(
            memory_records=[_memory_record()],
            repository_snapshots=[
                _snapshot(status=RepositoryIdentityStatus.UNSAFE_LOCATION)
            ],
        )
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY in _codes(report)
    assert report.synthesis_ready is False
    assert report.assessed_readiness is SynthesisReadinessStatus.BLOCKED
    # The safe evidence that survived alongside the unsafe repository is still
    # represented and is not itself reported as unsafe.
    assert report.evidence_count == 1
    assert GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE not in _codes(report)


def test_absolute_file_pointer_blocks_only_the_offending_record() -> None:
    safe = _reference("gs-ev-safe")
    unsafe = _reference(
        "gs-ev-unsafe",
        kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
        source_record_id="snap-1:obs-ev-1",
        source=_observer_source(),
        evidence_type=EvidenceType.SOURCE_CODE,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.FILE_PATH, value=ABSOLUTE_PATH
        ),
    )
    report = validate_synthesis_context_packet(
        _packet(evidence_references=[safe, unsafe])
    )

    unsafe_findings = [
        item
        for item in report.diagnostics
        if item.code is GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE
    ]
    assert len(unsafe_findings) == 1
    assert unsafe_findings[0].subject_id == "gs-ev-unsafe"
    assert report.synthesis_ready is False


def test_path_traversal_pointer_blocks() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
                source_record_id="snap-1:obs-ev-1",
                source=_observer_source(),
                evidence_type=EvidenceType.SOURCE_CODE,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.FILE_PATH,
                    value="apps/../../../secrets/id_rsa",
                ),
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE in _codes(report)


def test_credential_bearing_pointer_blocks_without_echoing_the_secret() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.EXTERNAL_SOURCE_ID,
                    value=CREDENTIAL_URL,
                )
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE in _codes(report)
    for diagnostic in report.diagnostics:
        assert "s3cr3t-token" not in diagnostic.message
        assert CREDENTIAL_URL not in diagnostic.message


def test_diagnostic_messages_never_echo_a_filesystem_path() -> None:
    packet = _packet(
        evidence_references=[
            _reference(
                kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
                source_record_id="snap-1:obs-ev-1",
                source=_observer_source(),
                evidence_type=EvidenceType.SOURCE_CODE,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.FILE_PATH, value=ABSOLUTE_PATH
                ),
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert report.diagnostics
    for diagnostic in report.diagnostics:
        assert ABSOLUTE_PATH not in diagnostic.message
        assert "C:/Users" not in diagnostic.message


# =========================================================================== #
# Packet integrity
# =========================================================================== #
def test_incorrect_evidence_total_blocks() -> None:
    packet = _assembled()
    tampered = _tamper(
        packet, metadata={**packet.metadata, "candidates_accepted": 7}
    )

    report = validate_synthesis_context_packet(tampered)

    assert GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH in _codes(report)
    assert report.synthesis_ready is False


def test_accepted_beyond_inspected_blocks() -> None:
    packet = _packet(
        metadata={
            "candidates_accepted": 1,
            "candidates_inspected": 0,
        }
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH in _codes(report)


def test_incorrect_family_coverage_total_blocks() -> None:
    packet = _packet(
        source_coverage=[
            SynthesisSourceCoverage(
                grounding_kind=(
                    GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD
                ),
                referenced_count=5,
            )
        ]
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.COVERAGE_COUNT_MISMATCH in _codes(report)
    assert report.synthesis_ready is False


def test_partial_coverage_reports_the_missing_family() -> None:
    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1"),
            _reference(
                "gs-ev-2",
                kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
                source_record_id="mem-1",
                evidence_type=None,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID,
                    value="mem-1",
                ),
            ),
        ],
        source_coverage=[
            SynthesisSourceCoverage(
                grounding_kind=(
                    GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD
                ),
                referenced_count=1,
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    missing = [
        item
        for item in report.diagnostics
        if item.code is GroundingDiagnosticCode.MISSING_COVERAGE_ENTRY
    ]
    assert len(missing) == 1
    assert missing[0].grounding_kind is GroundingEvidenceKind.ACTIVE_MEMORY_RECORD


def test_incorrect_critical_conflict_total_blocks() -> None:
    packet = _packet(metadata={"critical_conflict_count": 2})

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.CONFLICT_COUNT_MISMATCH in _codes(report)


def test_ready_claim_without_evidence_blocks() -> None:
    packet = _tamper(_packet(), evidence_references=[])

    report = validate_synthesis_context_packet(packet)

    codes = _codes(report)
    assert GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED in codes
    assert report.declared_readiness is SynthesisReadinessStatus.READY
    assert report.assessed_readiness is SynthesisReadinessStatus.BLOCKED
    assert report.synthesis_ready is False


def test_ready_claim_with_a_critical_conflict_blocks() -> None:
    packet = _tamper(
        _packet(
            readiness=SynthesisReadinessStatus.BLOCKED,
            evidence_references=[_reference("gs-ev-1"), _reference("gs-ev-2")],
            conflicts=[
                SynthesisEvidenceConflict(
                    conflict_id="gs-conflict-1",
                    summary="Records disagree.",
                    evidence_ids=["gs-ev-1", "gs-ev-2"],
                    severity=ContradictionSeverity.CRITICAL,
                )
            ],
        ),
        readiness=SynthesisReadinessStatus.READY,
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED in _codes(report)
    assert report.synthesis_ready is False


def test_blocking_readiness_reason_with_a_ready_claim_blocks() -> None:
    packet = _packet(metadata={"readiness_reason": "critical_conflict"})

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED in _codes(report)
    assert report.assessed_readiness is SynthesisReadinessStatus.BLOCKED


def test_unqualified_ready_reason_alongside_warnings_blocks() -> None:
    packet = _packet(
        metadata={"readiness_reason": "ready"},
        warnings=[
            SynthesisWarning(
                code=SynthesisWarningCode.COVERAGE_GAP,
                message="One family contributed nothing.",
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED in _codes(report)


def test_unsupported_contract_version_blocks() -> None:
    packet = _tamper(_packet(), schema_version="grounded-synthesis.v99")

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION in _codes(report)
    assert report.synthesis_ready is False


def test_unsupported_assembly_version_blocks() -> None:
    packet = _packet(metadata={"assembly_version": "grounding-context-assembly.v99"})

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNSUPPORTED_ASSEMBLY_VERSION in _codes(report)
    assert report.synthesis_ready is False


def test_edited_packet_fails_identity_re_derivation() -> None:
    packet = _assembled()
    assert packet.metadata["assembly_version"] == GROUNDING_CONTEXT_ASSEMBLY_VERSION

    tampered = _tamper(packet, correlation_id="tampered-correlation")
    report = validate_synthesis_context_packet(tampered)

    assert _codes(report) == [GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH]
    assert report.synthesis_ready is False


def test_non_canonical_ordering_is_reported_and_is_advisory() -> None:
    packet = _assembled()
    tampered = _tamper(packet, source_coverage=list(reversed(packet.source_coverage)))

    report = validate_synthesis_context_packet(tampered)

    ordering = next(
        item
        for item in report.diagnostics
        if item.code is GroundingDiagnosticCode.NON_CANONICAL_ORDERING
    )
    assert ordering.severity is GroundingDiagnosticSeverity.ADVISORY
    assert (
        DIAGNOSTIC_SEVERITY[GroundingDiagnosticCode.NON_CANONICAL_ORDERING]
        is GroundingDiagnosticSeverity.ADVISORY
    )


# =========================================================================== #
# Bounds, truncation and overflow
# =========================================================================== #
def test_packet_bound_exceeded_blocks_without_dropping_evidence() -> None:
    references = [_reference(f"gs-ev-{index}", source_record_id=f"ev-{index}") for index in range(4)]
    validator = SynthesisContextPacketValidator(
        limits=GroundingAssemblyLimits(max_evidence_items=2)
    )

    report = validator.validate(_packet(evidence_references=references))

    assert GroundingDiagnosticCode.PACKET_BOUND_EXCEEDED in _codes(report)
    assert report.synthesis_ready is False
    # The overflow is reported, never hidden by clipping the packet.
    assert report.evidence_count == 4


def test_family_bound_exceeded_blocks_when_several_families_contribute() -> None:
    references = [
        _reference("gs-ev-1", source_record_id="ev-1"),
        _reference("gs-ev-2", source_record_id="ev-2"),
        _reference(
            "gs-ev-3",
            kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
            source_record_id="mem-1",
            evidence_type=None,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-1"
            ),
        ),
    ]
    validator = SynthesisContextPacketValidator(
        limits=GroundingAssemblyLimits(max_items_per_kind=1)
    )

    report = validator.validate(_packet(evidence_references=references))

    family = next(
        item
        for item in report.diagnostics
        if item.code is GroundingDiagnosticCode.FAMILY_BOUND_EXCEEDED
    )
    assert family.grounding_kind is (
        GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD
    )
    assert report.synthesis_ready is False


def test_family_bound_is_lifted_for_a_single_family_packet() -> None:
    references = [
        _reference(f"gs-ev-{index}", source_record_id=f"ev-{index}") for index in range(3)
    ]
    validator = SynthesisContextPacketValidator(
        limits=GroundingAssemblyLimits(max_items_per_kind=1)
    )

    report = validator.validate(_packet(evidence_references=references))

    assert GroundingDiagnosticCode.FAMILY_BOUND_EXCEEDED not in _codes(report)


def test_inconsistent_truncation_metadata_blocks() -> None:
    packet = _packet(
        metadata={
            "items_truncated": 3,
            "exclusion_reasons": {"bounds_exceeded": 1},
        },
        warnings=[
            SynthesisWarning(
                code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                message="3 eligible evidence item(s) omitted.",
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.INVALID_TRUNCATION_CLAIM in _codes(report)
    assert report.synthesis_ready is False


def test_truncation_without_the_required_warning_blocks() -> None:
    packet = _packet(
        metadata={
            "items_truncated": 2,
            "exclusion_reasons": {"bounds_exceeded": 2},
        }
    )

    report = validate_synthesis_context_packet(packet)

    assert _codes(report) == [GroundingDiagnosticCode.UNDECLARED_TRUNCATION]
    assert report.synthesis_ready is False


def test_declared_critical_evidence_loss_blocks() -> None:
    packet = _packet(
        readiness=SynthesisReadinessStatus.BLOCKED,
        metadata={"readiness_reason": "critical_evidence_truncated"},
    )

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.UNKNOWN_CRITICAL_EVIDENCE in _codes(report)
    assert report.synthesis_ready is False


def test_oversized_evidence_label_blocks() -> None:
    oversized = _reference().model_copy(
        update={"label": "x" * (MAX_SYNTHESIS_LABEL_LENGTH + 1)}
    )
    packet = _tamper(_packet(), evidence_references=[oversized])

    report = validate_synthesis_context_packet(packet)

    assert GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD in _codes(report)
    assert report.synthesis_ready is False


# =========================================================================== #
# Integration against real Phase 40C assemblies
# =========================================================================== #
def test_assembled_packet_with_an_open_conflict_validates_cleanly() -> None:
    packet = _assembled(
        evidence=GroundingEvidenceSources(
            memory_records=[_memory_record()],
            evidence_records=[_evidence_record()],
            contradictions=[_contradiction()],
        )
    )

    report = validate_synthesis_context_packet(packet)

    assert packet.conflicts
    assert report.diagnostics == []
    assert report.synthesis_ready is True


def test_assembled_packet_with_a_critical_conflict_is_blocked_by_the_packet() -> None:
    packet = _assembled(
        evidence=GroundingEvidenceSources(
            memory_records=[_memory_record()],
            evidence_records=[_evidence_record()],
            contradictions=[
                _contradiction(severity=ContradictionSeverity.CRITICAL)
            ],
        )
    )

    report = validate_synthesis_context_packet(packet)

    assert packet.readiness is SynthesisReadinessStatus.BLOCKED
    assert report.diagnostics == []
    assert report.synthesis_ready is False
    assert report.assessed_readiness is SynthesisReadinessStatus.BLOCKED


def test_assembled_packet_with_requested_gaps_is_not_ready() -> None:
    request = _request(
        evidence_references=[
            _reference(
                "gs-ev-requested",
                kind=GroundingEvidenceKind.CONTEXT_PACKET_ENTRY,
                source_record_id="packet-entry-1",
                evidence_type=None,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.ARTIFACT_ID,
                    value="packet-entry-1",
                ),
            )
        ]
    )
    packet = _assembled(
        request=request,
        evidence=GroundingEvidenceSources(evidence_records=[_evidence_record()]),
    )

    report = validate_synthesis_context_packet(packet)

    assert packet.missing_context
    assert packet.readiness is SynthesisReadinessStatus.CONTEXT_REQUIRED
    assert report.diagnostics == []
    assert report.synthesis_ready is False
    assert report.assessed_readiness is SynthesisReadinessStatus.CONTEXT_REQUIRED


def test_scoped_assembly_validates_cleanly() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id=REPOSITORY_ID)
    packet = _assembled(
        request=_request(scope=scope),
        evidence=GroundingEvidenceSources(
            repository_snapshots=[_snapshot()],
            evidence_records=[_evidence_record()],
        ),
    )

    report = validate_synthesis_context_packet(packet)

    assert report.diagnostics == []
    assert report.synthesis_ready is True


# =========================================================================== #
# Report contract behavior
# =========================================================================== #
def test_severity_is_fixed_by_the_diagnostic_code() -> None:
    with pytest.raises(ValidationError):
        GroundingValidationDiagnostic(
            code=GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY,
            severity=GroundingDiagnosticSeverity.ADVISORY,
            message="downgraded",
        )


def test_severity_defaults_from_the_code() -> None:
    diagnostic = GroundingValidationDiagnostic(
        code=GroundingDiagnosticCode.NON_CANONICAL_ORDERING, message="ordering"
    )

    assert diagnostic.severity is GroundingDiagnosticSeverity.ADVISORY
    assert diagnostic.blocking is False


def test_every_diagnostic_code_has_a_severity_and_an_issue_projection() -> None:
    for code in GroundingDiagnosticCode:
        assert code in DIAGNOSTIC_SEVERITY, code
        assert code in DIAGNOSTIC_ISSUE_CODE, code


def test_report_rejects_ready_alongside_a_blocking_diagnostic() -> None:
    with pytest.raises(ValidationError):
        SynthesisPacketValidationReport(
            packet_id="gs-packet-1",
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            declared_readiness=SynthesisReadinessStatus.READY,
            assessed_readiness=SynthesisReadinessStatus.READY,
            synthesis_ready=True,
            evidence_count=1,
            family_count=1,
            diagnostics=[
                GroundingValidationDiagnostic(
                    code=GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY,
                    message="unsafe",
                )
            ],
        )


def test_report_rejects_a_synthesis_ready_flag_that_disagrees() -> None:
    with pytest.raises(ValidationError):
        SynthesisPacketValidationReport(
            packet_id="gs-packet-1",
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            declared_readiness=SynthesisReadinessStatus.READY,
            assessed_readiness=SynthesisReadinessStatus.CONTEXT_REQUIRED,
            synthesis_ready=True,
            evidence_count=1,
            family_count=1,
        )


def test_report_rejects_out_of_order_diagnostics() -> None:
    with pytest.raises(ValidationError):
        SynthesisPacketValidationReport(
            packet_id="gs-packet-1",
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            declared_readiness=SynthesisReadinessStatus.READY,
            assessed_readiness=SynthesisReadinessStatus.READY,
            synthesis_ready=True,
            evidence_count=1,
            family_count=1,
            diagnostics=[
                GroundingValidationDiagnostic(
                    code=GroundingDiagnosticCode.NON_CANONICAL_ORDERING,
                    message="ordering",
                ),
                GroundingValidationDiagnostic(
                    code=GroundingDiagnosticCode.NO_GROUNDING_EVIDENCE,
                    message="empty",
                ),
            ],
        )


def test_report_rejects_duplicate_diagnostics() -> None:
    diagnostic = GroundingValidationDiagnostic(
        code=GroundingDiagnosticCode.NON_CANONICAL_ORDERING, message="ordering"
    )
    with pytest.raises(ValidationError):
        SynthesisPacketValidationReport(
            packet_id="gs-packet-1",
            request_id="gs-request-1",
            mode=GroundedSynthesisMode.LOOM,
            declared_readiness=SynthesisReadinessStatus.READY,
            assessed_readiness=SynthesisReadinessStatus.READY,
            synthesis_ready=True,
            evidence_count=1,
            family_count=1,
            diagnostics=[diagnostic, diagnostic.model_copy()],
        )


def test_blocking_report_projects_onto_an_invalid_validation_result() -> None:
    packet = _tamper(_assembled(), correlation_id="tampered-correlation")

    result = validate_synthesis_context_packet(packet).to_validation_result()

    assert result.status is SynthesisValidationStatus.INVALID
    assert len(result.issues) == 1
    assert result.issues[0].code is (
        DIAGNOSTIC_ISSUE_CODE[GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH]
    )


def test_advisory_findings_do_not_make_a_result_invalid() -> None:
    packet = _packet(
        evidence_references=[_reference("gs-ev-1"), _reference("gs-ev-2")]
    )

    report = validate_synthesis_context_packet(packet)

    assert report.advisory_diagnostics
    assert report.blocking_diagnostics == []
    assert report.to_validation_result().status is SynthesisValidationStatus.VALID


# =========================================================================== #
# Structural determinism / read-only guarantees
# =========================================================================== #
def test_diagnostics_are_returned_in_canonical_order() -> None:
    packet = _packet(
        evidence_references=[
            _reference("gs-ev-1", summary="Commit landed."),
            _reference("gs-ev-2", summary="Commit reverted."),
            _reference(
                "gs-ev-3",
                kind=GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE,
                source_record_id=None,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value="node-1"
                ),
            ),
        ],
        source_coverage=[
            SynthesisSourceCoverage(
                grounding_kind=GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE,
                referenced_count=4,
            )
        ],
    )

    report = validate_synthesis_context_packet(packet)

    keys = [diagnostic.sort_key() for diagnostic in report.diagnostics]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))
    assert len(keys) > 1


_FORBIDDEN_CALLS = {
    "now",
    "utcnow",
    "today",
    "monotonic",
    "time",
    "uuid1",
    "uuid4",
    "random",
    "shuffle",
    "choice",
    "getenv",
    "open",
    "run",
    "urlopen",
    "system",
    "popen",
}
_FORBIDDEN_IMPORTS = {
    "os",
    "random",
    "secrets",
    "socket",
    "subprocess",
    "time",
    "urllib",
    "uuid",
    "requests",
    "httpx",
    "pathlib",
}


def test_validation_module_performs_no_clock_random_io_or_network_access() -> None:
    tree = ast.parse(Path(inspect.getfile(gv_module)).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in _FORBIDDEN_IMPORTS, alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in _FORBIDDEN_IMPORTS, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in _FORBIDDEN_CALLS, name


def test_validator_is_stateless_between_calls() -> None:
    validator = SynthesisContextPacketValidator()
    clean = _assembled()
    tampered = _tamper(clean, correlation_id="tampered-correlation")

    first = validator.validate(clean)
    validator.validate(tampered)
    third = validator.validate(clean)

    assert first.model_dump() == third.model_dump()


def test_validator_defaults_to_the_assembly_limits() -> None:
    assert SynthesisContextPacketValidator().limits == GroundingAssemblyLimits()
