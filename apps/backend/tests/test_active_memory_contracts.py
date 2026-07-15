"""Phase 37B — Active Agent Memory + Verification Layer contract tests.

Contract/validation only. These shapes have no endpoint, store, persistence,
ingestion, contradiction/active-state/packet logic yet; the tests assert
defaults, stable enum wire values, the two separate state axes, structured
claims, bounded evidence references, source identity without trust, explicit
supersession directionality, the five Phase 37D contradiction classes, the
context-packet structure, malformed-record rejection, and exact
frontend/backend wire-value parity.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.active_memory import (
    ACTIVE_MEMORY_CONTRACT_VERSION,
    ActiveStateResult,
    ClaimValueKind,
    ConfidenceBand,
    ContextPacket,
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
    PacketWarning,
    RepositoryBaseline,
    SupersessionKind,
    SupersessionReference,
    VerificationMetadata,
    VerificationState,
    VerificationSummary,
)

FIXED_TS = datetime(2026, 1, 1, 12, 0, 0)


# --------------------------------------------------------------------------- #
# Small builders
# --------------------------------------------------------------------------- #
def _source() -> MemorySource:
    return MemorySource(
        source_type=MemorySourceType.REPOSITORY_OBSERVER, source_id="repo-observer"
    )


def _minimal_record() -> MemoryRecord:
    return MemoryRecord(
        record_id="rec-1",
        kind=MemoryRecordKind.PHASE_STATUS,
        claim=MemoryClaim(subject="Phase 36J", predicate="merge_status", value="merged"),
        project_id="hive-mind",
        source=_source(),
        created_at=FIXED_TS,
    )


# --------------------------------------------------------------------------- #
# Minimum valid records + defaults
# --------------------------------------------------------------------------- #
def test_minimal_memory_record_defaults() -> None:
    record = _minimal_record()
    # Two axes default independently: unverified belief, active in-force.
    assert record.verification_state is VerificationState.UNVERIFIED
    assert record.lifecycle_state is LifecycleState.ACTIVE
    assert record.confidence is None
    assert record.evidence_ids == []
    assert record.verification is None
    assert record.supersession_refs == []
    assert record.observed_at is None
    assert record.scope is None
    assert record.metadata == {}
    # Claim carries a structured triple, not prose-only.
    assert record.claim.subject == "Phase 36J"
    assert record.claim.predicate == "merge_status"
    assert record.claim.value_kind is ClaimValueKind.STRING


def test_minimal_evidence_record_defaults() -> None:
    evidence = EvidenceRecord(
        evidence_id="ev-1",
        evidence_type=EvidenceType.PULL_REQUEST,
        reference=EvidenceReference(
            reference_kind=EvidenceReferenceKind.PULL_REQUEST_NUMBER, value="152"
        ),
        captured_at=FIXED_TS,
    )
    assert evidence.scope is None
    assert evidence.source is None
    assert evidence.valid_until is None
    assert evidence.summary is None
    assert evidence.metadata == {}


def test_minimal_contradiction_and_packet_defaults() -> None:
    contradiction = ContradictionRecord(
        contradiction_id="con-1",
        contradiction_class=ContradictionClass.PENDING_VS_MERGED,
        involved_record_ids=["rec-a", "rec-b"],
        summary="One record says pending, another says merged; no merge evidence.",
        detection_source=_source(),
        detected_at=FIXED_TS,
    )
    assert contradiction.resolution_state is ContradictionResolutionState.OPEN
    assert contradiction.resolution_record_id is None
    assert contradiction.severity is None
    assert contradiction.evidence_ids == []

    packet = ContextPacket(generated_at=FIXED_TS, project_id="hive-mind")
    assert packet.packet_version == ACTIVE_MEMORY_CONTRACT_VERSION
    assert packet.read_only is True
    assert packet.active_facts == []
    assert packet.active_decisions == []
    assert packet.active_constraints == []
    assert packet.known_capabilities == []
    assert packet.unresolved_contradictions == []
    assert packet.warnings == []
    assert packet.evidence_references == []
    assert packet.prohibited_assumptions == []
    assert packet.verification_summary == VerificationSummary()


# --------------------------------------------------------------------------- #
# Fully populated record + serialization shape
# --------------------------------------------------------------------------- #
def test_fully_populated_memory_record_round_trips() -> None:
    record = MemoryRecord(
        record_id="rec-full",
        kind=MemoryRecordKind.CAPABILITY,
        claim=MemoryClaim(
            subject="elastic node-pull",
            predicate="implementation_state",
            value="implemented",
            value_kind=ClaimValueKind.ENUM,
            summary="Elastic node-pull is implemented in spatialHiveElasticity.ts.",
        ),
        project_id="hive-mind",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="36H"),
        source=MemorySource(
            source_type=MemorySourceType.CLAUDE_CODE,
            source_id="claude-code",
            display_label="Claude Code",
            session_id="sess-42",
        ),
        verification_state=VerificationState.PARTIALLY_VERIFIED,
        lifecycle_state=LifecycleState.ACTIVE,
        confidence=ConfidenceBand.MEDIUM,
        evidence_ids=["ev-1", "ev-2"],
        verification=VerificationMetadata(
            state=VerificationState.PARTIALLY_VERIFIED,
            checked_at=FIXED_TS,
            checker=_source(),
            evidence_ids=["ev-1"],
            note="Code present; live behavior untested.",
        ),
        supersession_refs=[
            SupersessionReference(
                kind=SupersessionKind.SUPERSEDES,
                target_record_id="rec-old",
                reason="Newer capability observation.",
                created_at=FIXED_TS,
            )
        ],
        observed_at=FIXED_TS,
        created_at=FIXED_TS,
        metadata={"evidence": {"note": "scoped to code presence"}},
    )
    dumped = record.model_dump(mode="json")
    assert dumped["kind"] == "capability"
    assert dumped["claim"]["value_kind"] == "enum"
    assert dumped["verification_state"] == "partially_verified"
    assert dumped["lifecycle_state"] == "active"
    assert dumped["confidence"] == "medium"
    assert dumped["scope"] == {"scope_type": "phase", "scope_id": "36H"}
    assert dumped["supersession_refs"][0]["kind"] == "supersedes"
    assert MemoryRecord.model_validate(dumped) == record


# --------------------------------------------------------------------------- #
# Verification and lifecycle are separate axes
# --------------------------------------------------------------------------- #
def test_verification_and_lifecycle_are_separate_fields() -> None:
    fields = MemoryRecord.model_fields
    assert "verification_state" in fields
    assert "lifecycle_state" in fields
    # The two axes share no wire values, so neither can be mistaken for the other.
    verification_values = {m.value for m in VerificationState}
    lifecycle_values = {m.value for m in LifecycleState}
    assert verification_values.isdisjoint(lifecycle_values)
    # superseded/retracted/stale live ONLY on the lifecycle axis (Phase 37B
    # settled the Phase 37A §7 overload).
    for moved in ("superseded", "retracted", "stale"):
        assert moved in lifecycle_values
        assert moved not in verification_values


# --------------------------------------------------------------------------- #
# Stable enum wire values (the frontend unions key on these literals)
# --------------------------------------------------------------------------- #
def test_memory_record_kind_wire_values() -> None:
    assert {m.name: m.value for m in MemoryRecordKind} == {
        "PROJECT_FACT": "project_fact",
        "PROJECT_DECISION": "project_decision",
        "PROJECT_CONSTRAINT": "project_constraint",
        "PHASE_STATUS": "phase_status",
        "REPOSITORY_STATE": "repository_state",
        "CAPABILITY": "capability",
    }


def test_verification_state_wire_values() -> None:
    assert {m.value for m in VerificationState} == {
        "unverified",
        "partially_verified",
        "verified",
        "human_confirmed",
        "contradicted",
        "unresolvable",
    }


def test_lifecycle_state_wire_values() -> None:
    assert {m.value for m in LifecycleState} == {
        "active",
        "inactive",
        "superseded",
        "retracted",
        "stale",
        "archived",
    }


def test_evidence_type_wire_values() -> None:
    assert {m.value for m in EvidenceType} == {
        "human_confirmation",
        "repository_command_output",
        "commit",
        "branch",
        "pull_request",
        "test_output",
        "ci_output",
        "runtime_api_response",
        "source_code",
        "source_controlled_doc",
        "structured_cli_report",
        "structured_agent_report",
        "screenshot",
        "video",
        "conversational_summary",
        "inferred_context",
    }


def test_evidence_reference_kind_wire_values() -> None:
    assert {m.value for m in EvidenceReferenceKind} == {
        "commit_hash",
        "branch_name",
        "pull_request_number",
        "file_path",
        "symbol_reference",
        "command_id",
        "test_run_id",
        "source_record_id",
        "artifact_id",
        "external_source_id",
    }


def test_source_scope_confidence_claim_wire_values() -> None:
    assert {m.value for m in MemorySourceType} == {
        "human",
        "claude_code",
        "codex",
        "chatgpt",
        "cli_report",
        "repository_observer",
        "ci_system",
        "imported_document",
        "unknown",
    }
    assert {m.value for m in MemoryScopeType} == {
        "project",
        "repository",
        "branch",
        "phase",
        "feature",
        "component",
        "session",
    }
    assert {m.value for m in ConfidenceBand} == {"low", "medium", "high"}
    assert {m.value for m in ClaimValueKind} == {
        "string",
        "boolean",
        "integer",
        "float",
        "timestamp",
        "identifier",
        "enum",
    }


def test_contradiction_and_active_state_wire_values() -> None:
    # The five Phase 37D MVP classes, exactly.
    assert {m.value for m in ContradictionClass} == {
        "duplicate_phase_status",
        "pending_vs_merged",
        "frontend_only_vs_backend_modification",
        "current_vs_superseded_decision",
        "clean_vs_dirty_working_tree",
    }
    assert {m.value for m in ContradictionResolutionState} == {
        "open",
        "resolved",
        "archived",
    }
    assert {m.value for m in ContradictionSeverity} == {"info", "warning", "critical"}
    assert {m.value for m in ActiveStateResult} == {
        "active",
        "inactive",
        "unresolved",
        "no_eligible_record",
    }


def test_supersession_kind_wire_values() -> None:
    assert {m.value for m in SupersessionKind} == {
        "supersedes",
        "superseded_by",
        "retracts",
        "retracted_by",
    }


# --------------------------------------------------------------------------- #
# Confidence is separate from verification (distinct fields)
# --------------------------------------------------------------------------- #
def test_confidence_is_separate_from_verification() -> None:
    fields = MemoryRecord.model_fields
    assert "confidence" in fields
    assert "verification_state" in fields
    # Confidence is a qualitative band, optional, and not a numeric score.
    assert fields["confidence"].default is None
    record = _minimal_record()
    record_hi = record.model_copy(update={"confidence": ConfidenceBand.HIGH})
    # High confidence with an unverified state is representable (separate axes).
    assert record_hi.verification_state is VerificationState.UNVERIFIED
    assert record_hi.confidence is ConfidenceBand.HIGH


# --------------------------------------------------------------------------- #
# Supersession directionality: only forward links are stored
# --------------------------------------------------------------------------- #
def test_supersession_stores_only_forward_direction() -> None:
    ok = SupersessionReference(
        kind=SupersessionKind.RETRACTS,
        target_record_id="rec-wrong",
        created_at=FIXED_TS,
    )
    assert ok.kind is SupersessionKind.RETRACTS

    for derived in (SupersessionKind.SUPERSEDED_BY, SupersessionKind.RETRACTED_BY):
        with pytest.raises(ValidationError):
            SupersessionReference(
                kind=derived, target_record_id="rec-x", created_at=FIXED_TS
            )


# --------------------------------------------------------------------------- #
# Evidence references are bounded and non-blank
# --------------------------------------------------------------------------- #
def test_evidence_reference_rejects_blank_and_oversized_value() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference(reference_kind=EvidenceReferenceKind.COMMIT_HASH, value="   ")
    with pytest.raises(ValidationError):
        EvidenceReference(
            reference_kind=EvidenceReferenceKind.FILE_PATH, value="x" * 5000
        )


# --------------------------------------------------------------------------- #
# Context packet structure: bounded, reference-carrying, active-only baseline
# --------------------------------------------------------------------------- #
def test_context_packet_structure_and_serialization() -> None:
    packet = ContextPacket(
        generated_at=FIXED_TS,
        project_id="hive-mind",
        repository_baseline=RepositoryBaseline(
            project_id="hive-mind",
            branch="main",
            head_commit="bbe378a",
            working_tree_clean=True,
            observed_at=FIXED_TS,
            evidence_ids=["ev-tree"],
        ),
        active_track="Track 2 — Agent Intelligence Infrastructure",
        active_phase="Phase 37B",
        active_decisions=[
            MemoryRecord(
                record_id="dec-1",
                kind=MemoryRecordKind.PROJECT_DECISION,
                claim=MemoryClaim(
                    subject="gesture control",
                    predicate="default_state",
                    value="opt_in_off",
                ),
                project_id="hive-mind",
                source=MemorySource(
                    source_type=MemorySourceType.HUMAN, source_id="brit"
                ),
                verification_state=VerificationState.HUMAN_CONFIRMED,
                created_at=FIXED_TS,
            )
        ],
        unresolved_contradictions=[
            ContradictionRecord(
                contradiction_id="con-1",
                contradiction_class=ContradictionClass.DUPLICATE_PHASE_STATUS,
                involved_record_ids=["rec-a", "rec-b"],
                summary="Two active statuses for one phase.",
                detection_source=_source(),
                detected_at=FIXED_TS,
                severity=ContradictionSeverity.WARNING,
            )
        ],
        warnings=[
            PacketWarning(
                record_id="rec-old",
                lifecycle_state=LifecycleState.SUPERSEDED,
                reason="Replaced by rec-new.",
            )
        ],
        evidence_references=[
            EvidenceReference(
                reference_kind=EvidenceReferenceKind.BRANCH_NAME, value="main"
            )
        ],
        prohibited_assumptions=["Do not assume live-camera gesture tuning is done."],
    )
    dumped = packet.model_dump(mode="json")
    assert dumped["packet_version"] == "active-memory.v1"
    assert dumped["read_only"] is True
    assert dumped["repository_baseline"]["working_tree_clean"] is True
    assert dumped["active_decisions"][0]["verification_state"] == "human_confirmed"
    assert dumped["unresolved_contradictions"][0]["contradiction_class"] == (
        "duplicate_phase_status"
    )
    assert dumped["warnings"][0]["lifecycle_state"] == "superseded"
    assert ContextPacket.model_validate(dumped) == packet


def test_repository_baseline_unknown_tree_is_none_not_false() -> None:
    baseline = RepositoryBaseline(project_id="hive-mind")
    # Unknown working-tree state is `None`, never silently `False`.
    assert baseline.working_tree_clean is None
    assert RepositoryBaseline.model_fields["working_tree_clean"].default is None


# --------------------------------------------------------------------------- #
# Malformed-record rejection
# --------------------------------------------------------------------------- #
def test_blank_required_identifiers_are_rejected() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            record_id="   ",
            kind=MemoryRecordKind.PROJECT_FACT,
            claim=MemoryClaim(subject="s", predicate="p", value="v"),
            project_id="hive-mind",
            source=_source(),
            created_at=FIXED_TS,
        )
    with pytest.raises(ValidationError):
        MemoryClaim(subject="", predicate="p", value="v")


def test_invalid_enum_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            record_id="rec-1",
            kind="not_a_real_kind",  # type: ignore[arg-type]
            claim=MemoryClaim(subject="s", predicate="p", value="v"),
            project_id="hive-mind",
            source=_source(),
            created_at=FIXED_TS,
        )


def test_invalid_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            record_id="rec-1",
            kind=MemoryRecordKind.PROJECT_FACT,
            claim=MemoryClaim(subject="s", predicate="p", value="v"),
            project_id="hive-mind",
            source=_source(),
            created_at="not-a-timestamp",  # type: ignore[arg-type]
        )


def test_contradiction_requires_two_records() -> None:
    with pytest.raises(ValidationError):
        ContradictionRecord(
            contradiction_id="con-1",
            contradiction_class=ContradictionClass.PENDING_VS_MERGED,
            involved_record_ids=["only-one"],
            summary="Incomplete.",
            detection_source=_source(),
            detected_at=FIXED_TS,
        )


# --------------------------------------------------------------------------- #
# Frontend / backend wire parity
#
# The frontend union types (apps/frontend/src/types/api.ts) must mirror the
# backend StrEnum wire values byte-for-byte. This scans the committed TS file and
# asserts every backend enum value appears as a quoted string literal there. It
# is the repository's parity method extended to the active-memory contracts: the
# same "these literals are the wire contract" pinning the Phase 10B tests use,
# now checked directly against the mirrored frontend source.
# --------------------------------------------------------------------------- #
def _frontend_api_ts() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    api_ts = repo_root / "apps" / "frontend" / "src" / "types" / "api.ts"
    return api_ts.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "enum_cls",
    [
        MemoryRecordKind,
        VerificationState,
        LifecycleState,
        ConfidenceBand,
        ClaimValueKind,
        MemoryScopeType,
        MemorySourceType,
        EvidenceType,
        EvidenceReferenceKind,
        SupersessionKind,
        ContradictionClass,
        ContradictionResolutionState,
        ContradictionSeverity,
        ActiveStateResult,
    ],
)
def test_frontend_mirrors_backend_enum_values(enum_cls: type) -> None:
    api_ts = _frontend_api_ts()
    for member in enum_cls:
        assert f'"{member.value}"' in api_ts, (
            f"{enum_cls.__name__}.{member.name} wire value "
            f"'{member.value}' missing from frontend api.ts"
        )


def test_frontend_contract_version_matches_backend() -> None:
    api_ts = _frontend_api_ts()
    assert f'"{ACTIVE_MEMORY_CONTRACT_VERSION}"' in api_ts
