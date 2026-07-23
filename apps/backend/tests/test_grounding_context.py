"""Phase 40C — Grounding Context Assembly service tests.

Focused coverage of the deterministic assembly pipeline: request validation,
collection and normalization from the existing read-only providers, eligibility
filtering, deduplication, ranking, bounds and truncation, packet construction,
readiness evaluation, diagnostics, and the security/metadata protections carried
over from Phase 40B.

Every test drives the pure core from explicit fixtures — no store, no clock, no
Git, no filesystem, no network — so a passing run proves determinism rather than
assuming it.
"""

from __future__ import annotations

import ast
import inspect
import random
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

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
    MAX_SYNTHESIS_SUMMARY_LENGTH,
    GroundedSynthesisMode,
    GroundedSynthesisRequest,
    GroundingEvidenceKind,
    GroundingEvidenceReference,
    SynthesisConstraints,
    SynthesisContextPacket,
    SynthesisReadinessStatus,
    SynthesisWarningCode,
)
from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    RepositoryDriftAnalysis,
    RepositoryDriftStatus,
    RepositoryEvidence,
    RepositoryIdentity,
    RepositoryIdentityStatus,
    RepositorySnapshot,
    SnapshotCompleteness,
    TruncationState,
)
from app.services import grounding_context as gc_module
from app.services.grounding_context import (
    GROUNDING_CONTEXT_ASSEMBLY_VERSION,
    SUPPORTED_GROUNDING_KINDS,
    GroundingAssemblyLimits,
    GroundingCandidateOverflowError,
    GroundingContextAssemblyService,
    GroundingEvidenceSources,
    GroundingExclusionReason,
    GroundingPacketIdentityError,
    GroundingRequestNotAssemblableError,
    assemble_grounding_context,
)

FIXED_TS = datetime(2026, 7, 1, 9, 30, 0)
ASSEMBLED_AT = datetime(2026, 7, 2, 8, 0, 0)
REPOSITORY_ID = "repo-hive-mind"


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _request(**overrides: Any) -> GroundedSynthesisRequest:
    fields: dict[str, Any] = {
        "request_id": "gs-request-1",
        "mode": GroundedSynthesisMode.LOOM,
        "objective": "Assemble grounding for the next repository change.",
    }
    fields.update(overrides)
    return GroundedSynthesisRequest(**fields)


def _memory_record(
    record_id: str = "mem-1",
    *,
    lifecycle: LifecycleState = LifecycleState.ACTIVE,
    verification: VerificationState = VerificationState.VERIFIED,
    scope: MemoryScope | None = None,
    confidence: ConfidenceBand | None = ConfidenceBand.HIGH,
    observed_at: datetime | None = FIXED_TS,
    subject: str = "phase-40c",
    summary: str | None = "Phase 40C assembles grounding context.",
) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        kind=MemoryRecordKind.PROJECT_FACT,
        claim=MemoryClaim(
            subject=subject,
            predicate="status",
            value="in_progress",
            value_kind=ClaimValueKind.ENUM,
            summary=summary,
        ),
        project_id="hive-mind",
        scope=scope,
        source=MemorySource(
            source_type=MemorySourceType.CLAUDE_CODE, source_id="claude-code"
        ),
        verification_state=verification,
        lifecycle_state=lifecycle,
        confidence=confidence,
        observed_at=observed_at,
        created_at=FIXED_TS,
    )


def _evidence_record(
    evidence_id: str = "ev-1",
    *,
    evidence_type: EvidenceType = EvidenceType.COMMIT,
    scope: MemoryScope | None = None,
    captured_at: datetime = FIXED_TS,
    summary: str | None = "Commit landing the assembly service.",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.COMMIT_HASH,
            value="333deaa308417217653ea89276a2bfd97efd855e",
        ),
        scope=scope,
        source=MemorySource(
            source_type=MemorySourceType.REPOSITORY_OBSERVER, source_id="observer"
        ),
        captured_at=captured_at,
        summary=summary,
    )


def _contradiction(
    contradiction_id: str = "contra-1",
    *,
    involved: tuple[str, ...] = ("mem-1", "mem-2"),
    severity: ContradictionSeverity | None = ContradictionSeverity.WARNING,
    resolution: ContradictionResolutionState = ContradictionResolutionState.OPEN,
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
        resolution_state=resolution,
        severity=severity,
    )


def _identity(
    status: RepositoryIdentityStatus = RepositoryIdentityStatus.VERIFIED,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        repository_id=REPOSITORY_ID,
        canonical_root="C:/Users/britb/Documents/hive-mind",
        normalized_root="c:/users/britb/documents/hive-mind",
        repository_name="hive-mind",
        status=status,
    )


def _observer_evidence(
    evidence_id: str = "obs-ev-1",
    *,
    category: EvidenceCategory = EvidenceCategory.GIT_METADATA,
    authority: EvidenceAuthority = EvidenceAuthority.DIRECT_GIT_OUTPUT,
    path: str | None = None,
    digest: str | None = "a1b2c3d4",
    truncation: TruncationState = TruncationState.NOT_TRUNCATED,
    captured_at: datetime | None = FIXED_TS,
    excerpt: str | None = None,
) -> RepositoryEvidence:
    return RepositoryEvidence(
        evidence_id=evidence_id,
        category=category,
        authority=authority,
        source="git status --porcelain=v2",
        repository_relative_path=path,
        summary="Working tree is clean.",
        bounded_excerpt=excerpt,
        excerpt_limit=None if excerpt is None else 4096,
        digest=digest,
        captured_at=captured_at,
        truncation_state=truncation,
    )


def _snapshot(
    *,
    snapshot_id: str = "snap-1",
    identity_status: RepositoryIdentityStatus = RepositoryIdentityStatus.VERIFIED,
    evidence: tuple[RepositoryEvidence, ...] = (),
) -> RepositorySnapshot:
    return RepositorySnapshot(
        snapshot_id=snapshot_id,
        repository_identity=_identity(identity_status),
        observed_at=FIXED_TS,
        branch="main",
        commit="333deaa308417217653ea89276a2bfd97efd855e",
        evidence=list(evidence or (_observer_evidence(),)),
        completeness=SnapshotCompleteness.COMPLETE,
    )


def _drift(
    *,
    drift_id: str = "drift-1",
    identity_status: RepositoryIdentityStatus = RepositoryIdentityStatus.VERIFIED,
    evidence: tuple[RepositoryEvidence, ...] = (),
) -> RepositoryDriftAnalysis:
    return RepositoryDriftAnalysis(
        drift_id=drift_id,
        repository_identity=_identity(identity_status),
        observed_at=FIXED_TS,
        baseline_reference="HEAD",
        baseline_commit_hash="333deaa308417217653ea89276a2bfd97efd855e",
        drift_status=RepositoryDriftStatus.CLEAN,
        evidence=list(
            evidence
            or (
                _observer_evidence(
                    "drift-ev-1", category=EvidenceCategory.WORKING_TREE_METADATA
                ),
            )
        ),
    )


def _sources(**overrides: Any) -> GroundingEvidenceSources:
    fields: dict[str, Any] = {
        "memory_records": (_memory_record(),),
        "evidence_records": (_evidence_record(),),
        "contradictions": (),
        "repository_snapshots": (_snapshot(),),
        "repository_drift_analyses": (_drift(),),
    }
    fields.update(overrides)
    return GroundingEvidenceSources(**fields)


def _assemble(
    request: GroundedSynthesisRequest | None = None,
    sources: GroundingEvidenceSources | None = None,
    *,
    limits: GroundingAssemblyLimits | None = None,
    assembled_at: datetime | None = ASSEMBLED_AT,
) -> SynthesisContextPacket:
    return GroundingContextAssemblyService(limits=limits).assemble(
        request or _request(),
        evidence=sources or _sources(),
        assembled_at=assembled_at,
    )


# --------------------------------------------------------------------------- #
# Basic assembly
# --------------------------------------------------------------------------- #
def test_valid_request_produces_valid_packet() -> None:
    packet = _assemble()

    assert isinstance(packet, SynthesisContextPacket)
    assert packet.schema_version == GROUNDED_SYNTHESIS_CONTRACT_VERSION
    assert packet.request_id == "gs-request-1"
    assert packet.mode is GroundedSynthesisMode.LOOM
    assert packet.read_only is True
    assert packet.assembled_at == ASSEMBLED_AT
    # Re-validating the serialized packet proves it satisfies the Phase 40B
    # contract end to end, not merely that construction happened to succeed.
    assert SynthesisContextPacket.model_validate(packet.model_dump()) == packet


def test_packet_carries_normalized_evidence_from_every_eligible_provider() -> None:
    packet = _assemble()

    kinds = {item.grounding_kind for item in packet.evidence_references}
    assert kinds == {
        GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
        GroundingEvidenceKind.REPOSITORY_OBSERVATION,
        GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING,
    }
    for reference in packet.evidence_references:
        assert reference.source_record_id
        assert reference.reference.value
        assert reference.evidence_id.startswith("gs-ev-")


def test_normalization_preserves_traceable_origin_fields() -> None:
    packet = _assemble()
    by_kind = {item.grounding_kind: item for item in packet.evidence_references}

    observation = by_kind[GroundingEvidenceKind.REPOSITORY_OBSERVATION]
    assert observation.source_record_id == "snap-1:obs-ev-1"
    assert observation.scope == MemoryScope(
        scope_type=MemoryScopeType.REPOSITORY, scope_id=REPOSITORY_ID
    )
    assert observation.source is not None
    assert observation.source.source_type is MemorySourceType.REPOSITORY_OBSERVER
    assert observation.evidence_type is EvidenceType.REPOSITORY_COMMAND_OUTPUT
    assert observation.content_digest == "a1b2c3d4"
    assert observation.observed_at == FIXED_TS
    assert dict(observation.metadata)["authority"] == "direct_git_output"

    evidence_record = by_kind[GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD]
    assert evidence_record.evidence_type is EvidenceType.COMMIT
    assert evidence_record.reference.reference_kind is EvidenceReferenceKind.COMMIT_HASH

    memory = by_kind[GroundingEvidenceKind.ACTIVE_MEMORY_RECORD]
    # A claim is never asserted to be evidence of itself.
    assert memory.evidence_type is None
    assert memory.confidence is ConfidenceBand.HIGH
    assert memory.reference.reference_kind is EvidenceReferenceKind.SOURCE_RECORD_ID


def test_assembly_never_produces_synthesis_content() -> None:
    packet = _assemble()

    # Summaries spanning several records would be synthesis; Phase 40C emits none.
    assert packet.context_summaries == []


def test_module_level_helper_matches_service() -> None:
    assert assemble_grounding_context(
        _request(), evidence=_sources(), assembled_at=ASSEMBLED_AT
    ) == _assemble()


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_identical_input_produces_model_equivalent_output() -> None:
    first = _assemble()
    second = _assemble()

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.packet_id == second.packet_id


def test_shuffled_candidate_input_produces_the_same_ordered_packet() -> None:
    records = [_memory_record(f"mem-{index}") for index in range(6)]
    evidence = [_evidence_record(f"ev-{index}") for index in range(6)]
    observations = [_observer_evidence(f"obs-{index}") for index in range(6)]

    baseline = _assemble(
        sources=_sources(
            memory_records=tuple(records),
            evidence_records=tuple(evidence),
            repository_snapshots=(_snapshot(evidence=tuple(observations)),),
        )
    )

    shuffler = random.Random(40_301)
    for _ in range(5):
        shuffled_records = records[:]
        shuffled_evidence = evidence[:]
        shuffled_observations = observations[:]
        shuffler.shuffle(shuffled_records)
        shuffler.shuffle(shuffled_evidence)
        shuffler.shuffle(shuffled_observations)
        shuffled = _assemble(
            sources=_sources(
                memory_records=tuple(shuffled_records),
                evidence_records=tuple(shuffled_evidence),
                repository_snapshots=(_snapshot(evidence=tuple(shuffled_observations)),),
            )
        )
        assert shuffled.packet_id == baseline.packet_id
        assert [item.evidence_id for item in shuffled.evidence_references] == [
            item.evidence_id for item in baseline.evidence_references
        ]


def test_packet_id_changes_when_material_content_changes() -> None:
    baseline = _assemble()

    different_evidence = _assemble(
        sources=_sources(memory_records=(_memory_record("mem-other"),))
    )
    different_time = _assemble(assembled_at=ASSEMBLED_AT + timedelta(hours=1))
    different_request = _assemble(request=_request(request_id="gs-request-2"))

    ids = {
        baseline.packet_id,
        different_evidence.packet_id,
        different_time.packet_id,
        different_request.packet_id,
    }
    assert len(ids) == 4


def test_lexical_tie_breakers_are_stable_across_equal_ranked_items() -> None:
    # Six evidence records identical in family, type, confidence and freshness:
    # only the final derived-identifier tie-break can order them.
    evidence = tuple(_evidence_record(f"ev-tie-{index}") for index in range(6))
    packet = _assemble(
        sources=GroundingEvidenceSources(evidence_records=evidence)
    )
    ordered = [
        item.evidence_id
        for item in packet.evidence_references
        if item.grounding_kind is GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD
    ]
    assert ordered == sorted(ordered)
    assert len(ordered) == 6


def test_unicode_equivalent_identifiers_remain_deterministic() -> None:
    composed = unicodedata.normalize("NFC", "mem-café")
    decomposed = unicodedata.normalize("NFD", "mem-café")
    assert composed != decomposed

    composed_packet = _assemble(
        sources=GroundingEvidenceSources(memory_records=(_memory_record(composed),))
    )
    decomposed_packet = _assemble(
        sources=GroundingEvidenceSources(memory_records=(_memory_record(decomposed),))
    )

    assert composed_packet.packet_id == decomposed_packet.packet_id
    assert (
        composed_packet.evidence_references[0].evidence_id
        == decomposed_packet.evidence_references[0].evidence_id
    )


def test_ranking_places_critical_conflict_evidence_first() -> None:
    packet = _assemble(
        sources=_sources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-2")),
            contradictions=(
                _contradiction(severity=ContradictionSeverity.CRITICAL),
            ),
        )
    )
    leading = [item.source_record_id for item in packet.evidence_references[:3]]
    assert set(leading) == {"contra-1", "mem-1", "mem-2"}


def test_directly_requested_evidence_outranks_unrequested_peers() -> None:
    requested = GroundingEvidenceReference(
        evidence_id="caller-ev-1",
        grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        source_record_id="mem-2",
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-2"
        ),
    )
    packet = _assemble(
        request=_request(evidence_references=[requested]),
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-2"))
        ),
    )
    assert packet.evidence_references[0].source_record_id == "mem-2"


# --------------------------------------------------------------------------- #
# Request validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "status",
    [
        SynthesisReadinessStatus.PROPOSED,
        SynthesisReadinessStatus.VALIDATION_FAILED,
        SynthesisReadinessStatus.HUMAN_REVIEW_REQUIRED,
    ],
)
def test_artifact_status_request_is_rejected(status: SynthesisReadinessStatus) -> None:
    request = _request(
        status=status,
        evidence_references=[
            GroundingEvidenceReference(
                evidence_id="caller-ev-1",
                grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
                reference=EvidenceReference(
                    reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-1"
                ),
            )
        ],
    )
    with pytest.raises(GroundingRequestNotAssemblableError):
        _assemble(request=request)


def test_request_with_embedded_packet_is_rejected() -> None:
    embedded = _assemble()
    request = _request(context_packet=embedded, context_packet_id=embedded.packet_id)
    with pytest.raises(GroundingRequestNotAssemblableError):
        _assemble(request=request)


def test_declared_context_packet_id_must_match_the_assembled_packet() -> None:
    with pytest.raises(GroundingPacketIdentityError):
        _assemble(request=_request(context_packet_id="gs-packet-someone-elses"))

    produced = _assemble()
    # The correct declaration round-trips.
    assert (
        _assemble(request=_request(context_packet_id=produced.packet_id)).packet_id
        == produced.packet_id
    )


def test_request_constraint_narrows_the_packet_but_cannot_widen_it() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(5))
    packet = _assemble(
        request=_request(constraints=SynthesisConstraints(max_evidence_references=2)),
        sources=GroundingEvidenceSources(memory_records=records),
    )
    assert len(packet.evidence_references) == 2


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #
def test_out_of_scope_evidence_is_excluded() -> None:
    in_scope = MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="phase-40c")
    other = MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="phase-39d")
    packet = _assemble(
        request=_request(scope=in_scope),
        sources=GroundingEvidenceSources(
            memory_records=(
                _memory_record("mem-in", scope=in_scope),
                _memory_record("mem-out", scope=other),
            )
        ),
    )
    assert [item.source_record_id for item in packet.evidence_references] == ["mem-in"]
    assert packet.metadata["exclusion_reasons"][
        GroundingExclusionReason.OUT_OF_SCOPE.value
    ] == 1


def test_unscoped_evidence_survives_a_scoped_request() -> None:
    """Absence of a declared scope is not evidence of being out of scope.

    Contradiction records carry no scope; excluding them under a scoped request
    would hide exactly the conflicts a scoped packet most needs.
    """

    scope = MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="phase-40c")
    packet = _assemble(
        request=_request(scope=scope),
        sources=GroundingEvidenceSources(
            memory_records=(
                _memory_record("mem-1", scope=scope),
                _memory_record("mem-2", scope=scope),
            ),
            contradictions=(_contradiction(),),
        ),
    )
    assert "contra-1" in {item.source_record_id for item in packet.evidence_references}


@pytest.mark.parametrize(
    "lifecycle",
    [
        LifecycleState.SUPERSEDED,
        LifecycleState.STALE,
        LifecycleState.RETRACTED,
        LifecycleState.INACTIVE,
    ],
)
def test_non_active_memory_records_are_excluded(lifecycle: LifecycleState) -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(
                _memory_record("mem-active"),
                _memory_record("mem-other", lifecycle=lifecycle),
            )
        )
    )
    assert [item.source_record_id for item in packet.evidence_references] == [
        "mem-active"
    ]
    assert packet.metadata["exclusion_reasons"][
        GroundingExclusionReason.NOT_ACTIVE_LIFECYCLE.value
    ] == 1


def test_unresolvable_verification_is_excluded_but_contradicted_is_retained() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(
                _memory_record("mem-contradicted", verification=VerificationState.CONTRADICTED),
                _memory_record("mem-unresolvable", verification=VerificationState.UNRESOLVABLE),
            )
        )
    )
    included = {item.source_record_id for item in packet.evidence_references}
    assert included == {"mem-contradicted"}
    assert packet.metadata["exclusion_reasons"][
        GroundingExclusionReason.UNRESOLVABLE_VERIFICATION.value
    ] == 1


@pytest.mark.parametrize(
    "kind",
    [
        GroundingEvidenceKind.KNOWLEDGE_GRAPH_NODE,
        GroundingEvidenceKind.SOURCE_REGISTRY_ENTRY,
        GroundingEvidenceKind.QUERY_TRAIL,
        GroundingEvidenceKind.CONTEXT_PACKET_ENTRY,
    ],
)
def test_unsupported_evidence_families_are_handled_deterministically(
    kind: GroundingEvidenceKind,
) -> None:
    assert kind not in SUPPORTED_GROUNDING_KINDS
    requested = GroundingEvidenceReference(
        evidence_id="caller-ev-1",
        grounding_kind=kind,
        source_record_id="node-1",
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.EXTERNAL_SOURCE_ID, value="node-1"
        ),
    )
    packet = _assemble(request=_request(evidence_references=[requested]))

    assert kind.value not in {
        item.grounding_kind.value for item in packet.evidence_references
    }
    assert packet.metadata["unsupported_evidence_kinds"] == [kind.value]
    assert packet.metadata["exclusion_reasons"][
        GroundingExclusionReason.UNSUPPORTED_EVIDENCE_KIND.value
    ] == 1
    assert any(
        warning.code is SynthesisWarningCode.COVERAGE_GAP for warning in packet.warnings
    )


@pytest.mark.parametrize(
    "authority",
    [
        EvidenceAuthority.UNSUPPORTED_ASSUMPTION,
        EvidenceAuthority.UNAVAILABLE_INFORMATION,
    ],
)
def test_ungrounded_observer_authorities_are_excluded(
    authority: EvidenceAuthority,
) -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            repository_snapshots=(
                _snapshot(evidence=(_observer_evidence(authority=authority),)),
            )
        )
    )
    assert packet.evidence_references == []
    assert packet.readiness is SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE


def test_omitted_observer_evidence_is_excluded() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            repository_snapshots=(
                _snapshot(
                    evidence=(_observer_evidence(truncation=TruncationState.OMITTED),)
                ),
            )
        )
    )
    assert packet.evidence_references == []
    assert packet.metadata["exclusion_reasons"][
        GroundingExclusionReason.OMITTED_CONTENT.value
    ] == 1


@pytest.mark.parametrize(
    "status",
    [
        RepositoryIdentityStatus.UNSAFE_LOCATION,
        RepositoryIdentityStatus.MISMATCHED_ROOT,
        RepositoryIdentityStatus.MISMATCHED_REMOTE,
    ],
)
def test_unsafe_repository_identity_never_yields_a_ready_packet(
    status: RepositoryIdentityStatus,
) -> None:
    packet = _assemble(
        sources=_sources(repository_snapshots=(_snapshot(identity_status=status),))
    )

    assert packet.readiness is SynthesisReadinessStatus.BLOCKED
    assert packet.metadata["readiness_reason"] == "unsafe_repository_identity"
    assert GroundingEvidenceKind.REPOSITORY_OBSERVATION not in {
        item.grounding_kind for item in packet.evidence_references
    }
    assert any(
        warning.code is SynthesisWarningCode.CONSTRAINT_LIMITED
        for warning in packet.warnings
    )


def test_observer_evidence_without_any_safe_pointer_still_grounds_on_the_snapshot() -> None:
    snapshot = RepositorySnapshot(
        snapshot_id="snap-bare",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
        evidence=[_observer_evidence("obs-bare")],
        completeness=SnapshotCompleteness.UNAVAILABLE,
    )
    packet = _assemble(
        sources=GroundingEvidenceSources(repository_snapshots=(snapshot,))
    )
    reference = packet.evidence_references[0].reference
    assert reference.reference_kind is EvidenceReferenceKind.ARTIFACT_ID
    assert reference.value == "snap-bare"


# --------------------------------------------------------------------------- #
# Deduplication
# --------------------------------------------------------------------------- #
def test_duplicate_canonical_evidence_is_included_once() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-1"))
        )
    )
    assert len(packet.evidence_references) == 1
    assert packet.metadata["duplicates_removed"] == 1


def test_deduplication_winner_follows_documented_precedence() -> None:
    weak = _memory_record("mem-1", verification=VerificationState.UNVERIFIED)
    strong = _memory_record("mem-1", verification=VerificationState.HUMAN_CONFIRMED)

    for ordering in ((weak, strong), (strong, weak)):
        packet = _assemble(
            sources=GroundingEvidenceSources(memory_records=ordering)
        )
        assert len(packet.evidence_references) == 1
        metadata = dict(packet.evidence_references[0].metadata)
        assert metadata["verification_state"] == VerificationState.HUMAN_CONFIRMED.value


def test_provider_record_beats_a_caller_supplied_duplicate() -> None:
    requested = GroundingEvidenceReference(
        evidence_id="caller-ev-1",
        grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        source_record_id="mem-1",
        label="caller label",
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-1"
        ),
    )
    packet = _assemble(
        request=_request(evidence_references=[requested]),
        sources=GroundingEvidenceSources(memory_records=(_memory_record("mem-1"),)),
    )
    assert len(packet.evidence_references) == 1
    assert dict(packet.evidence_references[0].metadata).get("origin") is None


def test_duplicate_input_order_does_not_affect_output() -> None:
    first = _memory_record("mem-1")
    second = _memory_record("mem-2")
    forward = _assemble(
        sources=GroundingEvidenceSources(memory_records=(first, second, first))
    )
    backward = _assemble(
        sources=GroundingEvidenceSources(memory_records=(second, first, second))
    )
    assert [item.evidence_id for item in forward.evidence_references] == [
        item.evidence_id for item in backward.evidence_references
    ]


# --------------------------------------------------------------------------- #
# Bounds and truncation
# --------------------------------------------------------------------------- #
def test_raw_candidate_guard_fails_closed_rather_than_clipping() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(12))
    with pytest.raises(GroundingCandidateOverflowError):
        _assemble(
            sources=GroundingEvidenceSources(memory_records=records),
            limits=GroundingAssemblyLimits(max_raw_candidates=5),
        )


def test_packet_item_limit_is_enforced_with_a_deterministic_warning() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10))
    packet = _assemble(
        sources=GroundingEvidenceSources(memory_records=records),
        limits=GroundingAssemblyLimits(max_evidence_items=4),
    )
    assert len(packet.evidence_references) == 4
    assert packet.metadata["items_truncated"] == 6
    assert any(
        warning.code is SynthesisWarningCode.BOUNDS_EXCEEDED
        for warning in packet.warnings
    )


def test_per_family_limit_prevents_one_provider_consuming_the_packet() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10))
    evidence = tuple(_evidence_record(f"ev-{index}") for index in range(10))
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=records, evidence_records=evidence
        ),
        limits=GroundingAssemblyLimits(max_items_per_kind=3, max_evidence_items=64),
    )
    counts: dict[GroundingEvidenceKind, int] = {}
    for reference in packet.evidence_references:
        counts[reference.grounding_kind] = counts.get(reference.grounding_kind, 0) + 1
    assert counts == {
        GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD: 3,
        GroundingEvidenceKind.ACTIVE_MEMORY_RECORD: 3,
    }
    assert any(
        warning.subject_id == GroundingEvidenceKind.ACTIVE_MEMORY_RECORD.value
        for warning in packet.warnings
    )


def test_per_family_limit_is_lifted_for_a_single_contributing_family() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10))
    packet = _assemble(
        sources=GroundingEvidenceSources(memory_records=records),
        limits=GroundingAssemblyLimits(max_items_per_kind=3, max_evidence_items=64),
    )
    assert len(packet.evidence_references) == 10


def test_truncation_is_deterministic_across_runs() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10))
    limits = GroundingAssemblyLimits(max_evidence_items=4)
    first = _assemble(
        sources=GroundingEvidenceSources(memory_records=records), limits=limits
    )
    second = _assemble(
        sources=GroundingEvidenceSources(memory_records=tuple(reversed(records))),
        limits=limits,
    )
    assert first.packet_id == second.packet_id


def test_oversized_text_is_bounded_and_reported() -> None:
    # The Phase 40B contract already caps claim text at 2048, so an over-long
    # value is produced here by narrowing the assembly bound rather than by
    # smuggling an invalid record past the contract edge.
    oversized = "x" * 400
    assert len(oversized) <= MAX_SYNTHESIS_SUMMARY_LENGTH
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1", summary=oversized),)
        ),
        limits=GroundingAssemblyLimits(max_summary_length=64),
    )
    summary = packet.evidence_references[0].summary
    assert summary is not None
    assert len(summary) == 64
    assert summary.endswith("…")
    assert packet.metadata["text_truncations"] == 1
    assert any(
        warning.code is SynthesisWarningCode.BOUNDS_EXCEEDED
        for warning in packet.warnings
    )


def test_critical_conflict_evidence_is_not_lost_behind_ordinary_evidence() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10)) + (
        _memory_record("mem-critical-a"),
        _memory_record("mem-critical-b"),
    )
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=records,
            contradictions=(
                _contradiction(
                    involved=("mem-critical-a", "mem-critical-b"),
                    severity=ContradictionSeverity.CRITICAL,
                ),
            ),
        ),
        limits=GroundingAssemblyLimits(max_evidence_items=3, max_items_per_kind=48),
    )
    retained = {item.source_record_id for item in packet.evidence_references}
    assert {"mem-critical-a", "mem-critical-b", "contra-1"} == retained


def test_limits_cannot_exceed_the_phase_40b_contract_ceilings() -> None:
    with pytest.raises(ValueError, match="contract ceiling"):
        GroundingAssemblyLimits(max_evidence_items=10_000)
    with pytest.raises(ValueError, match="positive integer"):
        GroundingAssemblyLimits(max_items_per_kind=0)


# --------------------------------------------------------------------------- #
# Readiness and conflicts
# --------------------------------------------------------------------------- #
def test_sufficient_evidence_produces_ready() -> None:
    packet = _assemble()
    assert packet.readiness is SynthesisReadinessStatus.READY
    assert packet.metadata["readiness_reason"] in {"ready", "ready_with_warnings"}


def test_empty_evidence_produces_insufficient_evidence() -> None:
    packet = _assemble(sources=GroundingEvidenceSources())
    assert packet.readiness is SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE
    assert packet.metadata["readiness_reason"] == "no_eligible_evidence"
    assert packet.evidence_references == []


def test_critical_conflict_blocks_readiness_and_is_surfaced() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-2")),
            contradictions=(_contradiction(severity=ContradictionSeverity.CRITICAL),),
        )
    )
    assert packet.readiness is SynthesisReadinessStatus.BLOCKED
    assert len(packet.conflicts) == 1
    conflict = packet.conflicts[0]
    assert conflict.severity is ContradictionSeverity.CRITICAL
    assert conflict.contradiction_record_id == "contra-1"
    assert len(conflict.evidence_ids) == 2
    # Conflicts are surfaced, never resolved: both participants remain.
    assert packet.metadata["critical_conflict_count"] == 1


def test_non_critical_conflict_is_surfaced_without_blocking() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-2")),
            contradictions=(_contradiction(severity=ContradictionSeverity.WARNING),),
        )
    )
    assert packet.readiness is SynthesisReadinessStatus.READY
    assert len(packet.conflicts) == 1


def test_unrepresentable_critical_conflict_blocks_rather_than_disappearing() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"),),
            contradictions=(
                _contradiction(
                    involved=("mem-1", "mem-absent"),
                    severity=ContradictionSeverity.CRITICAL,
                ),
            ),
        )
    )
    assert packet.conflicts == []
    assert packet.readiness is SynthesisReadinessStatus.BLOCKED
    assert any(
        warning.code is SynthesisWarningCode.CONFLICTING_EVIDENCE
        for warning in packet.warnings
    )


@pytest.mark.parametrize(
    "resolution",
    [ContradictionResolutionState.RESOLVED, ContradictionResolutionState.ARCHIVED],
)
def test_closed_contradictions_do_not_block(
    resolution: ContradictionResolutionState,
) -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1"), _memory_record("mem-2")),
            contradictions=(
                _contradiction(
                    severity=ContradictionSeverity.CRITICAL, resolution=resolution
                ),
            ),
        )
    )
    assert packet.conflicts == []
    assert packet.readiness is SynthesisReadinessStatus.READY


def test_requested_evidence_that_is_filtered_out_becomes_a_context_gap() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="phase-40c")
    requested = GroundingEvidenceReference(
        evidence_id="caller-ev-1",
        grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        source_record_id="mem-out",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="phase-39d"),
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-out"
        ),
    )
    packet = _assemble(
        request=_request(scope=scope, evidence_references=[requested]),
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-in", scope=scope),)
        ),
    )
    assert packet.readiness is SynthesisReadinessStatus.CONTEXT_REQUIRED
    assert len(packet.missing_context) == 1
    assert packet.missing_context[0].required_evidence_kinds == [
        GroundingEvidenceKind.ACTIVE_MEMORY_RECORD
    ]


def test_ready_packet_and_ready_request_stay_consistent() -> None:
    packet = _assemble()
    assert packet.readiness is SynthesisReadinessStatus.READY
    # A 'ready' request embedding this packet validates under the Phase 40B rule
    # that a ready request requires a ready packet.
    request = _request(
        status=SynthesisReadinessStatus.READY,
        context_packet=packet,
        context_packet_id=packet.packet_id,
    )
    assert request.context_packet is not None
    assert request.context_packet.readiness is SynthesisReadinessStatus.READY


def test_warnings_do_not_downgrade_ready() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(6))
    packet = _assemble(
        sources=GroundingEvidenceSources(memory_records=records),
        limits=GroundingAssemblyLimits(max_evidence_items=2),
    )
    assert packet.warnings
    assert packet.readiness is SynthesisReadinessStatus.READY
    assert packet.metadata["readiness_reason"] == "ready_with_warnings"


# --------------------------------------------------------------------------- #
# Diagnostics and coverage
# --------------------------------------------------------------------------- #
def test_diagnostics_are_bounded_counts_and_closed_literals() -> None:
    packet = _assemble()
    metadata = packet.metadata

    assert metadata["assembly_version"] == GROUNDING_CONTEXT_ASSEMBLY_VERSION
    assert metadata["request_mode"] == GroundedSynthesisMode.LOOM.value
    assert metadata["candidates_inspected"] == 4
    assert metadata["candidates_accepted"] == 4
    assert metadata["candidates_excluded"] == 0
    assert metadata["duplicates_removed"] == 0
    assert metadata["items_truncated"] == 0
    assert len(metadata) <= 32
    for value in metadata.values():
        assert isinstance(value, (str, int, list, dict))


def test_source_coverage_records_offered_and_used_families() -> None:
    packet = _assemble(
        sources=_sources(
            memory_records=(
                _memory_record("mem-inactive", lifecycle=LifecycleState.STALE),
            )
        )
    )
    coverage = {item.grounding_kind: item for item in packet.source_coverage}
    assert coverage[GroundingEvidenceKind.ACTIVE_MEMORY_RECORD].referenced_count == 0
    assert coverage[GroundingEvidenceKind.ACTIVE_MEMORY_RECORD].note is not None
    assert coverage[GroundingEvidenceKind.REPOSITORY_OBSERVATION].referenced_count == 1
    kinds = [item.grounding_kind.value for item in packet.source_coverage]
    assert kinds == sorted(kinds)


def test_warnings_are_canonically_ordered() -> None:
    records = tuple(_memory_record(f"mem-{index}") for index in range(10))
    evidence = tuple(_evidence_record(f"ev-{index}") for index in range(10))
    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=records, evidence_records=evidence
        ),
        limits=GroundingAssemblyLimits(max_items_per_kind=2, max_evidence_items=8),
    )
    keys = [
        (item.code.value, item.message, item.subject_id or "") for item in packet.warnings
    ]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------- #
# Security and metadata protections
# --------------------------------------------------------------------------- #
def test_raw_provider_payloads_never_reach_the_packet() -> None:
    secret_excerpt = "AUTHORIZATION: Bearer super-secret-token"
    snapshot = _snapshot(
        evidence=(
            _observer_evidence(
                category=EvidenceCategory.BOUNDED_TEXT_EXCERPT, excerpt=secret_excerpt
            ),
        )
    )
    packet = _assemble(
        sources=GroundingEvidenceSources(repository_snapshots=(snapshot,))
    )
    serialized = packet.model_dump_json()

    assert secret_excerpt not in serialized
    # Machine-specific absolute repository roots are never copied either.
    assert "C:/Users" not in serialized
    assert "c:/users" not in serialized


def test_caller_metadata_bag_is_not_passed_through() -> None:
    requested = GroundingEvidenceReference(
        evidence_id="caller-ev-1",
        grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
        source_record_id="mem-caller",
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value="mem-caller"
        ),
        metadata={"caller_note": "arbitrary caller payload"},
    )
    packet = _assemble(
        request=_request(evidence_references=[requested]),
        sources=GroundingEvidenceSources(),
    )
    assert packet.evidence_references[0].metadata == {"origin": "requested_reference"}


def test_packet_metadata_avoids_forbidden_provider_and_runtime_keys() -> None:
    packet = _assemble()
    forbidden = {
        "agent",
        "api_key",
        "credentials",
        "model",
        "prompt",
        "provider",
        "temperature",
        "token_budget",
    }
    assert not forbidden & set(packet.metadata)
    for reference in packet.evidence_references:
        assert not forbidden & set(reference.metadata)


def test_phase_40b_metadata_protections_still_reject_unsafe_requests() -> None:
    """The assembly service never weakens the Phase 40B contract edge."""

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _request(metadata={"api_key": "secret"})
    with pytest.raises(ValidationError):
        _request(metadata={"score": float("inf")})
    with pytest.raises(ValidationError):
        _request(metadata={"payload": object()})
    with pytest.raises(ValidationError):
        _request(metadata={"deep": {"a": {"b": {"c": {"d": {"e": 1}}}}}})


def test_non_hex_digests_are_dropped_rather_than_carried() -> None:
    packet = _assemble(
        sources=GroundingEvidenceSources(
            repository_snapshots=(
                _snapshot(evidence=(_observer_evidence(digest="NOT-A-DIGEST"),)),
            )
        )
    )
    assert packet.evidence_references[0].content_digest is None


# --------------------------------------------------------------------------- #
# Structural determinism / read-only guarantees
# --------------------------------------------------------------------------- #
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


def test_service_module_performs_no_clock_random_io_or_network_access() -> None:
    tree = ast.parse(Path(inspect.getfile(gc_module)).read_text(encoding="utf-8"))
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


def test_service_is_stateless_between_calls() -> None:
    service = GroundingContextAssemblyService()
    first = service.assemble(_request(), evidence=_sources(), assembled_at=ASSEMBLED_AT)
    service.assemble(
        _request(request_id="gs-other"), evidence=_sources(), assembled_at=ASSEMBLED_AT
    )
    third = service.assemble(_request(), evidence=_sources(), assembled_at=ASSEMBLED_AT)
    assert first == third


def test_sources_container_copies_caller_sequences() -> None:
    records = [_memory_record("mem-1")]
    sources = GroundingEvidenceSources(memory_records=records)
    records.append(_memory_record("mem-2"))
    assert sources.total_records() == 1
    assert len(_assemble(sources=sources).evidence_references) == 1


def test_memory_record_without_observed_at_falls_back_to_created_at() -> None:
    """``observed_at`` is the freshness axis; ``created_at`` is the fallback.

    A memory record is never treated as undated when it records when it was
    created, so freshness ranking stays meaningful.
    """

    packet = _assemble(
        sources=GroundingEvidenceSources(
            memory_records=(_memory_record("mem-1", observed_at=None),)
        )
    )
    assert packet.evidence_references[0].observed_at == FIXED_TS


def test_aware_naive_and_undated_timestamps_order_without_raising() -> None:
    def _reference(evidence_id: str, observed_at: datetime | None) -> GroundingEvidenceReference:
        return GroundingEvidenceReference(
            evidence_id=evidence_id,
            grounding_kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
            source_record_id=evidence_id,
            observed_at=observed_at,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID, value=evidence_id
            ),
        )

    aware = _reference("ref-aware", datetime(2026, 7, 1, 9, 30, tzinfo=timezone.utc))
    naive = _reference("ref-naive", datetime(2026, 6, 1, 9, 30))
    undated = _reference("ref-undated", None)

    packet = _assemble(
        request=_request(evidence_references=[undated, naive, aware]),
        sources=GroundingEvidenceSources(),
    )
    assert [item.source_record_id for item in packet.evidence_references] == [
        "ref-aware",
        "ref-naive",
        "ref-undated",
    ]
