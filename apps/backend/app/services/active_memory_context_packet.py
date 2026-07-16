"""Phase 37E - deterministic Active Memory context packet builder.

Read-only derivation over the Phase 37C store and Phase 37D contradiction
detector. The caller supplies the clock; this module never observes time, runs
commands, resolves evidence, mutates records, or chooses winners.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.models.active_memory import (
    MAX_MEMORY_COLLECTION_ITEMS,
    ContextPacket,
    ContradictionRecord,
    ContradictionResolutionState,
    LifecycleState,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScope,
    PacketWarning,
    RepositoryBaseline,
    VerificationState,
    VerificationSummary,
)
from app.services.active_memory_contradiction import (
    ActiveMemoryContradictionDetector,
)
from app.store.active_memory_store import MemoryStore


class ContextPacketTruncationUnsupportedError(ValueError):
    """Raised when a packet collection would exceed the existing contract limit.

    ``PacketWarning`` represents lifecycle warnings for specific records, not
    packet-level truncation. Failing closed is therefore more truthful than
    silently clipping data or fabricating a misleading warning record.
    """


_WARNING_STATES = frozenset(
    {
        LifecycleState.SUPERSEDED,
        LifecycleState.STALE,
        LifecycleState.RETRACTED,
        LifecycleState.INACTIVE,
    }
)

_UNVERIFIED_CAPABILITY_STATES = frozenset(
    {
        VerificationState.UNVERIFIED,
        VerificationState.PARTIALLY_VERIFIED,
    }
)


def build_context_packet(
    *,
    store: MemoryStore,
    project_id: str,
    generated_at: datetime,
    detector: ActiveMemoryContradictionDetector | None = None,
    scope: MemoryScope | None = None,
) -> ContextPacket:
    """Build a deterministic, bounded, read-only ``ContextPacket``.

    Records are selected by exact ``project_id`` and, when supplied, exact
    ``MemoryScope``. Active records stay visible regardless of verification
    state. Non-active, non-archived records become lifecycle warnings.
    """

    records = _select_records(store=store, project_id=project_id, scope=scope)
    active_records = [
        record for record in records if record.lifecycle_state is LifecycleState.ACTIVE
    ]
    contradictions = _open_contradictions(
        detector=detector or ActiveMemoryContradictionDetector(),
        records=records,
        generated_at=generated_at,
    )

    active_facts = _records_of_kind(active_records, MemoryRecordKind.PROJECT_FACT)
    active_decisions = _records_of_kind(
        active_records, MemoryRecordKind.PROJECT_DECISION
    )
    active_constraints = _records_of_kind(
        active_records, MemoryRecordKind.PROJECT_CONSTRAINT
    )
    known_capabilities = _records_of_kind(active_records, MemoryRecordKind.CAPABILITY)
    warnings = _warnings_for(records)
    prohibited_assumptions = _prohibited_assumptions(
        constraints=active_constraints,
        capabilities=known_capabilities,
        contradictions=contradictions,
    )

    _assert_collection_within_limit("active_facts", active_facts)
    _assert_collection_within_limit("active_decisions", active_decisions)
    _assert_collection_within_limit("active_constraints", active_constraints)
    _assert_collection_within_limit("known_capabilities", known_capabilities)
    _assert_collection_within_limit("unresolved_contradictions", contradictions)
    _assert_collection_within_limit("warnings", warnings)
    _assert_collection_within_limit("prohibited_assumptions", prohibited_assumptions)

    return ContextPacket(
        generated_at=generated_at,
        project_id=project_id,
        repository_baseline=_repository_baseline(project_id, active_records),
        active_track=_active_status_value(active_records, "active_track"),
        active_phase=_active_status_value(active_records, "active_phase"),
        active_facts=active_facts,
        active_decisions=active_decisions,
        active_constraints=active_constraints,
        known_capabilities=known_capabilities,
        unresolved_contradictions=contradictions,
        warnings=warnings,
        evidence_references=[],
        verification_summary=_verification_summary(active_records),
        prohibited_assumptions=prohibited_assumptions,
        read_only=True,
    )


def _select_records(
    *,
    store: MemoryStore,
    project_id: str,
    scope: MemoryScope | None,
) -> list[MemoryRecord]:
    records = store.list_records(project_id=project_id)
    if scope is None:
        return records
    return [
        record
        for record in records
        if record.scope is not None
        and record.scope.scope_type is scope.scope_type
        and record.scope.scope_id == scope.scope_id
    ]


def _records_of_kind(
    records: Iterable[MemoryRecord], kind: MemoryRecordKind
) -> list[MemoryRecord]:
    return [record for record in records if record.kind is kind]


def _open_contradictions(
    *,
    detector: ActiveMemoryContradictionDetector,
    records: list[MemoryRecord],
    generated_at: datetime,
) -> list[ContradictionRecord]:
    return [
        contradiction
        for contradiction in detector.detect(records, detected_at=generated_at)
        if contradiction.resolution_state is ContradictionResolutionState.OPEN
    ]


def _warnings_for(records: Iterable[MemoryRecord]) -> list[PacketWarning]:
    return [
        PacketWarning(
            record_id=record.record_id,
            lifecycle_state=record.lifecycle_state,
            reason=(
                f"Record {record.record_id!r} is {record.lifecycle_state.value!r} "
                "and excluded from the active baseline."
            ),
        )
        for record in records
        if record.lifecycle_state in _WARNING_STATES
    ]


def _verification_summary(records: Iterable[MemoryRecord]) -> VerificationSummary:
    summary = VerificationSummary()
    for record in records:
        if record.verification_state is VerificationState.VERIFIED:
            summary.verified_count += 1
        elif record.verification_state is VerificationState.HUMAN_CONFIRMED:
            summary.human_confirmed_count += 1
        elif record.verification_state is VerificationState.PARTIALLY_VERIFIED:
            summary.partially_verified_count += 1
        elif record.verification_state is VerificationState.UNVERIFIED:
            summary.unverified_count += 1
        elif record.verification_state is VerificationState.CONTRADICTED:
            summary.contradicted_count += 1
        elif record.verification_state is VerificationState.UNRESOLVABLE:
            summary.unresolvable_count += 1
    return summary


def _repository_baseline(
    project_id: str, records: Iterable[MemoryRecord]
) -> RepositoryBaseline | None:
    candidates: list[tuple[datetime, datetime, str, RepositoryBaseline]] = []
    for record in records:
        if record.kind is not MemoryRecordKind.REPOSITORY_STATE:
            continue
        raw = record.metadata.get("repository_baseline")
        if not isinstance(raw, dict):
            continue
        baseline = _baseline_from_metadata(project_id, record, raw)
        if baseline is None:
            continue
        observed = baseline.observed_at or datetime.min
        candidates.append((observed, record.created_at, record.record_id, baseline))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[-1][3]


def _baseline_from_metadata(
    project_id: str, record: MemoryRecord, raw: dict[str, Any]
) -> RepositoryBaseline | None:
    branch = raw.get("branch")
    head_commit = raw.get("head_commit")
    working_tree_clean = raw.get("working_tree_clean")
    observed_at = raw.get("observed_at", record.observed_at)

    if branch is not None and not isinstance(branch, str):
        return None
    if head_commit is not None and not isinstance(head_commit, str):
        return None
    if working_tree_clean is not None and not isinstance(working_tree_clean, bool):
        return None
    if observed_at is not None and not isinstance(observed_at, datetime):
        return None

    return RepositoryBaseline(
        project_id=project_id,
        branch=branch,
        head_commit=head_commit,
        working_tree_clean=working_tree_clean,
        observed_at=observed_at,
        evidence_ids=list(record.evidence_ids),
        metadata={"source_record_id": record.record_id},
    )


def _active_status_value(records: Iterable[MemoryRecord], key: str) -> str | None:
    candidates: list[tuple[datetime, datetime, str, str]] = []
    for record in records:
        if record.kind is not MemoryRecordKind.PHASE_STATUS:
            continue
        value = record.metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        observed = record.observed_at or datetime.min
        candidates.append((observed, record.created_at, record.record_id, value.strip()))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[-1][3]


def _prohibited_assumptions(
    *,
    constraints: list[MemoryRecord],
    capabilities: list[MemoryRecord],
    contradictions: list[ContradictionRecord],
) -> list[str]:
    assumptions: list[str] = []
    assumptions.extend(
        f'Do not assume constraint "{record.claim.subject}" may be violated.'
        for record in constraints
    )
    assumptions.extend(
        f'Do not assume capability "{record.claim.subject}" is verified.'
        for record in capabilities
        if record.verification_state in _UNVERIFIED_CAPABILITY_STATES
    )
    assumptions.extend(
        f'Do not assume contradiction "{contradiction.contradiction_id}" is resolved.'
        for contradiction in contradictions
    )
    return assumptions


def _assert_collection_within_limit(name: str, values: list[object]) -> None:
    if len(values) <= MAX_MEMORY_COLLECTION_ITEMS:
        return
    raise ContextPacketTruncationUnsupportedError(
        f"{name} contains {len(values)} items, exceeding "
        f"MAX_MEMORY_COLLECTION_ITEMS={MAX_MEMORY_COLLECTION_ITEMS}; the existing "
        "ContextPacket contract has no truthful packet-level truncation warning"
    )
