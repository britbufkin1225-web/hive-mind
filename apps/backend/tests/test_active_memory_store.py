"""Phase 37C — Deterministic Active Memory store tests.

Covers the storage domain and deterministic lifecycle behavior of
:mod:`app.store.active_memory_store`: insertion, retrieval, stable listing order,
contract-backed filtering, duplicate rejection, not-found behavior, allowed and
rejected lifecycle transitions, evidence/provenance preservation, defensive-copy
immutability, stable serialization, restoration, malformed-snapshot rejection,
and repeated-operation determinism.

These use contract-valid Phase 37B fixtures and do not weaken the Phase 37B
contract tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models.active_memory import (
    ACTIVE_MEMORY_CONTRACT_VERSION,
    ConfidenceBand,
    EvidenceReference,
    EvidenceReferenceKind,
    LifecycleState,
    MemoryClaim,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    SupersessionKind,
    SupersessionReference,
    VerificationMetadata,
    VerificationState,
)
from app.store.active_memory_store import (
    LIFECYCLE_TRANSITIONS,
    SNAPSHOT_RECORDS_KEY,
    SNAPSHOT_VERSION_KEY,
    DuplicateRecordError,
    InMemoryActiveMemoryStore,
    InvalidLifecycleTransitionError,
    MalformedSnapshotError,
    MemoryStore,
    RecordNotFoundError,
)

# Deterministic, injected timestamps — the store never generates its own.
TS_EARLY = datetime(2026, 1, 1, 8, 0, 0)
TS_MID = datetime(2026, 1, 1, 12, 0, 0)
TS_LATE = datetime(2026, 1, 2, 9, 30, 0)


# --------------------------------------------------------------------------- #
# Contract-valid fixture builders
# --------------------------------------------------------------------------- #
def _source(source_id: str = "repo-observer") -> MemorySource:
    return MemorySource(
        source_type=MemorySourceType.REPOSITORY_OBSERVER,
        source_id=source_id,
        display_label="Repository Observer",
        session_id="sess-1",
    )


def _record(
    record_id: str,
    *,
    kind: MemoryRecordKind = MemoryRecordKind.PHASE_STATUS,
    project_id: str = "hive-mind",
    created_at: datetime = TS_MID,
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE,
    verification_state: VerificationState = VerificationState.UNVERIFIED,
    scope: MemoryScope | None = None,
    value: str = "merged",
) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        kind=kind,
        claim=MemoryClaim(
            subject="Phase 37B", predicate="merge_status", value=value
        ),
        project_id=project_id,
        scope=scope,
        source=_source(),
        verification_state=verification_state,
        lifecycle_state=lifecycle_state,
        created_at=created_at,
    )


def _evidenced_record(record_id: str = "rec-evidence") -> MemoryRecord:
    """A fully populated record carrying evidence, provenance, and supersession."""
    return MemoryRecord(
        record_id=record_id,
        kind=MemoryRecordKind.CAPABILITY,
        claim=MemoryClaim(
            subject="active memory store",
            predicate="implementation_state",
            value="implemented",
            summary="In-memory deterministic store implemented in Phase 37C.",
        ),
        project_id="hive-mind",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="37C"),
        source=_source("claude-code"),
        verification_state=VerificationState.PARTIALLY_VERIFIED,
        lifecycle_state=LifecycleState.ACTIVE,
        confidence=ConfidenceBand.MEDIUM,
        evidence_ids=["ev-1", "ev-2"],
        verification=VerificationMetadata(
            state=VerificationState.PARTIALLY_VERIFIED,
            checked_at=TS_MID,
            checker=_source(),
            evidence_ids=["ev-1"],
            note="Code present; live behavior untested.",
        ),
        supersession_refs=[
            SupersessionReference(
                kind=SupersessionKind.SUPERSEDES,
                target_record_id="rec-old",
                reason="Newer capability observation.",
                created_at=TS_MID,
            )
        ],
        observed_at=TS_EARLY,
        created_at=TS_MID,
        metadata={"evidence": {"note": "scoped to code presence"}},
    )


# --------------------------------------------------------------------------- #
# 1. Successful insertion
# --------------------------------------------------------------------------- #
def test_insert_stores_and_returns_record() -> None:
    store = InMemoryActiveMemoryStore()
    returned = store.insert(_record("rec-1"))
    assert returned.record_id == "rec-1"
    assert len(store) == 1
    assert "rec-1" in store
    # The in-memory implementation satisfies the small store protocol.
    assert isinstance(store, MemoryStore)


# --------------------------------------------------------------------------- #
# 2. Deterministic retrieval
# --------------------------------------------------------------------------- #
def test_get_returns_equal_record() -> None:
    store = InMemoryActiveMemoryStore()
    original = _record("rec-1")
    store.insert(original)
    fetched = store.get("rec-1")
    assert fetched == original
    # Repeated reads return equal values and never mutate stored state.
    assert store.get("rec-1") == store.get("rec-1")
    assert len(store) == 1


def test_find_returns_none_for_missing() -> None:
    store = InMemoryActiveMemoryStore()
    assert store.find("nope") is None


# --------------------------------------------------------------------------- #
# 3. Stable listing order
# --------------------------------------------------------------------------- #
def test_list_is_ordered_by_created_at_then_record_id() -> None:
    store = InMemoryActiveMemoryStore()
    # Insert out of order; two share a timestamp to exercise the id tiebreak.
    store.insert(_record("rec-late", created_at=TS_LATE))
    store.insert(_record("rec-b", created_at=TS_MID))
    store.insert(_record("rec-a", created_at=TS_MID))
    store.insert(_record("rec-early", created_at=TS_EARLY))

    ids = [r.record_id for r in store.list_records()]
    assert ids == ["rec-early", "rec-a", "rec-b", "rec-late"]
    # Insertion order must not affect output.
    other = InMemoryActiveMemoryStore()
    for rid, ts in [
        ("rec-a", TS_MID),
        ("rec-early", TS_EARLY),
        ("rec-late", TS_LATE),
        ("rec-b", TS_MID),
    ]:
        other.insert(_record(rid, created_at=ts))
    assert [r.record_id for r in other.list_records()] == ids


# --------------------------------------------------------------------------- #
# 4. Supported filtering (contract-backed fields, AND-combined, stable)
# --------------------------------------------------------------------------- #
def test_filtering_by_contract_fields() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(
        _record("fact-1", kind=MemoryRecordKind.PROJECT_FACT, created_at=TS_EARLY)
    )
    store.insert(
        _record(
            "phase-1",
            kind=MemoryRecordKind.PHASE_STATUS,
            verification_state=VerificationState.VERIFIED,
            created_at=TS_MID,
        )
    )
    store.insert(
        _record(
            "phase-2",
            kind=MemoryRecordKind.PHASE_STATUS,
            lifecycle_state=LifecycleState.STALE,
            created_at=TS_LATE,
        )
    )
    store.insert(
        _record(
            "other-project",
            project_id="other",
            kind=MemoryRecordKind.PHASE_STATUS,
            created_at=TS_MID,
        )
    )

    by_kind = store.list_records(kind=MemoryRecordKind.PHASE_STATUS)
    # phase-1 and other-project share TS_MID; the record_id tiebreak orders them.
    assert [r.record_id for r in by_kind] == ["other-project", "phase-1", "phase-2"]

    by_project_and_kind = store.list_records(
        project_id="hive-mind", kind=MemoryRecordKind.PHASE_STATUS
    )
    assert [r.record_id for r in by_project_and_kind] == ["phase-1", "phase-2"]

    by_lifecycle = store.list_records(lifecycle_state=LifecycleState.STALE)
    assert [r.record_id for r in by_lifecycle] == ["phase-2"]

    by_verification = store.list_records(
        verification_state=VerificationState.VERIFIED
    )
    assert [r.record_id for r in by_verification] == ["phase-1"]


def test_filtering_by_scope_type() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(
        _record(
            "scoped",
            scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="37C"),
            created_at=TS_EARLY,
        )
    )
    store.insert(_record("unscoped", created_at=TS_MID))
    scoped = store.list_records(scope_type=MemoryScopeType.PHASE)
    assert [r.record_id for r in scoped] == ["scoped"]


# --------------------------------------------------------------------------- #
# 5. Duplicate identifier rejection
# --------------------------------------------------------------------------- #
def test_duplicate_record_id_rejected() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1"))
    with pytest.raises(DuplicateRecordError):
        store.insert(_record("rec-1", value="different"))
    # The original is untouched by the rejected insert.
    assert store.get("rec-1").claim.value == "merged"
    assert len(store) == 1


# --------------------------------------------------------------------------- #
# 6. Record-not-found behavior
# --------------------------------------------------------------------------- #
def test_get_missing_raises_not_found() -> None:
    store = InMemoryActiveMemoryStore()
    with pytest.raises(RecordNotFoundError):
        store.get("ghost")


def test_transition_missing_raises_not_found() -> None:
    store = InMemoryActiveMemoryStore()
    with pytest.raises(RecordNotFoundError):
        store.transition_lifecycle("ghost", LifecycleState.ARCHIVED)


# --------------------------------------------------------------------------- #
# 7. Allowed lifecycle transition
# --------------------------------------------------------------------------- #
def test_allowed_lifecycle_transition() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1", lifecycle_state=LifecycleState.ACTIVE))
    updated = store.transition_lifecycle("rec-1", LifecycleState.SUPERSEDED)
    assert updated.lifecycle_state is LifecycleState.SUPERSEDED
    # The change is persisted in the store, not just returned.
    assert store.get("rec-1").lifecycle_state is LifecycleState.SUPERSEDED


def test_idempotent_self_transition_is_noop() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1", lifecycle_state=LifecycleState.ACTIVE))
    same = store.transition_lifecycle("rec-1", LifecycleState.ACTIVE)
    assert same.lifecycle_state is LifecycleState.ACTIVE
    assert same == store.get("rec-1")


def test_transition_table_matches_documented_rules() -> None:
    # The table is the single source of truth; assert its exact shape so a silent
    # edit to the rules is caught.
    assert LIFECYCLE_TRANSITIONS[LifecycleState.ACTIVE] == frozenset(
        {
            LifecycleState.INACTIVE,
            LifecycleState.SUPERSEDED,
            LifecycleState.RETRACTED,
            LifecycleState.STALE,
            LifecycleState.ARCHIVED,
        }
    )
    assert LIFECYCLE_TRANSITIONS[LifecycleState.INACTIVE] == frozenset(
        {LifecycleState.ACTIVE, LifecycleState.ARCHIVED}
    )
    assert LIFECYCLE_TRANSITIONS[LifecycleState.SUPERSEDED] == frozenset(
        {LifecycleState.ARCHIVED}
    )
    assert LIFECYCLE_TRANSITIONS[LifecycleState.RETRACTED] == frozenset(
        {LifecycleState.ARCHIVED}
    )
    assert LIFECYCLE_TRANSITIONS[LifecycleState.ARCHIVED] == frozenset()


# --------------------------------------------------------------------------- #
# 8. Rejected lifecycle transition
# --------------------------------------------------------------------------- #
def test_rejected_lifecycle_transition_is_consistent() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1", lifecycle_state=LifecycleState.ARCHIVED))
    # Archived is terminal: nothing but the idempotent self-transition is allowed.
    for target in (
        LifecycleState.ACTIVE,
        LifecycleState.INACTIVE,
        LifecycleState.SUPERSEDED,
        LifecycleState.RETRACTED,
        LifecycleState.STALE,
    ):
        with pytest.raises(InvalidLifecycleTransitionError):
            store.transition_lifecycle("rec-1", target)
    # The stored record is left untouched by every rejected transition.
    assert store.get("rec-1").lifecycle_state is LifecycleState.ARCHIVED


def test_terminal_states_cannot_revert_to_active() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("sup", lifecycle_state=LifecycleState.SUPERSEDED))
    store.insert(_record("ret", lifecycle_state=LifecycleState.RETRACTED))
    with pytest.raises(InvalidLifecycleTransitionError):
        store.transition_lifecycle("sup", LifecycleState.ACTIVE)
    with pytest.raises(InvalidLifecycleTransitionError):
        store.transition_lifecycle("ret", LifecycleState.ACTIVE)


# --------------------------------------------------------------------------- #
# 9. Evidence and provenance preservation across a transition
# --------------------------------------------------------------------------- #
def test_transition_preserves_evidence_and_provenance() -> None:
    store = InMemoryActiveMemoryStore()
    original = _evidenced_record()
    store.insert(original)
    updated = store.transition_lifecycle("rec-evidence", LifecycleState.STALE)

    # Only lifecycle_state changed; everything else is carried forward untouched.
    assert updated.lifecycle_state is LifecycleState.STALE
    assert updated.evidence_ids == original.evidence_ids
    assert updated.verification == original.verification
    assert updated.supersession_refs == original.supersession_refs
    assert updated.source == original.source
    assert updated.scope == original.scope
    assert updated.claim == original.claim
    assert updated.confidence == original.confidence
    assert updated.observed_at == original.observed_at
    assert updated.metadata == original.metadata
    # The one intended difference is the lifecycle state.
    assert updated == original.model_copy(
        update={"lifecycle_state": LifecycleState.STALE}
    )


# --------------------------------------------------------------------------- #
# 10. Defensive-copy / immutability behavior
# --------------------------------------------------------------------------- #
def test_mutating_inserted_instance_does_not_change_store() -> None:
    store = InMemoryActiveMemoryStore()
    original = _evidenced_record("rec-1")
    store.insert(original)
    # Mutate the caller's instance after insert.
    original.evidence_ids.append("ev-injected")
    original.metadata["tampered"] = True
    stored = store.get("rec-1")
    assert stored.evidence_ids == ["ev-1", "ev-2"]
    assert "tampered" not in stored.metadata


def test_mutating_returned_record_does_not_change_store() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_evidenced_record("rec-1"))
    fetched = store.get("rec-1")
    fetched.evidence_ids.append("ev-injected")
    fetched.claim.value = "tampered"
    # A fresh read is unaffected by mutation of a previously returned copy.
    again = store.get("rec-1")
    assert again.evidence_ids == ["ev-1", "ev-2"]
    assert again.claim.value == "implemented"


def test_listed_records_are_independent_copies() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_evidenced_record("rec-1"))
    listed = store.list_records()
    listed[0].evidence_ids.append("ev-injected")
    assert store.get("rec-1").evidence_ids == ["ev-1", "ev-2"]


# --------------------------------------------------------------------------- #
# 11. Stable serialization
# --------------------------------------------------------------------------- #
def test_serialize_is_stable_and_versioned() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-b", created_at=TS_MID))
    store.insert(_record("rec-a", created_at=TS_EARLY))

    snapshot = store.serialize()
    assert snapshot[SNAPSHOT_VERSION_KEY] == ACTIVE_MEMORY_CONTRACT_VERSION
    # Records appear in the same deterministic order as list_records().
    assert [r["record_id"] for r in snapshot[SNAPSHOT_RECORDS_KEY]] == [
        "rec-a",
        "rec-b",
    ]
    # Repeated serialization of unchanged state is byte-identical.
    assert store.to_json() == store.to_json()
    assert store.serialize() == snapshot


# --------------------------------------------------------------------------- #
# 12. Valid restoration from serialized data
# --------------------------------------------------------------------------- #
def test_round_trip_restore_preserves_records() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_evidenced_record("rec-1"))
    store.insert(_record("rec-2", created_at=TS_LATE))

    restored = InMemoryActiveMemoryStore.restore(store.serialize())
    assert len(restored) == 2
    assert restored.get("rec-1") == store.get("rec-1")
    assert restored.get("rec-2") == store.get("rec-2")
    # A second serialization of the restored store matches the first exactly.
    assert restored.serialize() == store.serialize()


def test_round_trip_via_json_string() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_evidenced_record("rec-1"))
    restored = InMemoryActiveMemoryStore.from_json(store.to_json())
    assert restored.get("rec-1") == store.get("rec-1")


# --------------------------------------------------------------------------- #
# 13. Malformed stored data rejection
# --------------------------------------------------------------------------- #
def test_restore_rejects_non_mapping() -> None:
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.restore(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_restore_rejects_wrong_contract_version() -> None:
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.restore(
            {SNAPSHOT_VERSION_KEY: "active-memory.v999", SNAPSHOT_RECORDS_KEY: []}
        )


def test_restore_rejects_non_list_records() -> None:
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.restore(
            {SNAPSHOT_VERSION_KEY: ACTIVE_MEMORY_CONTRACT_VERSION,
             SNAPSHOT_RECORDS_KEY: {"rec-1": {}}}
        )


def test_restore_rejects_malformed_record() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1"))
    snapshot = store.serialize()
    # Corrupt a required field so contract validation fails.
    del snapshot[SNAPSHOT_RECORDS_KEY][0]["record_id"]
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.restore(snapshot)


def test_restore_rejects_duplicate_ids_in_snapshot() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-1"))
    snapshot = store.serialize()
    snapshot[SNAPSHOT_RECORDS_KEY].append(dict(snapshot[SNAPSHOT_RECORDS_KEY][0]))
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.restore(snapshot)


def test_from_json_rejects_invalid_json() -> None:
    with pytest.raises(MalformedSnapshotError):
        InMemoryActiveMemoryStore.from_json("{not valid json")


# --------------------------------------------------------------------------- #
# 14. Repeated-operation determinism
# --------------------------------------------------------------------------- #
def test_repeated_operations_are_deterministic() -> None:
    def build() -> InMemoryActiveMemoryStore:
        store = InMemoryActiveMemoryStore()
        store.insert(_record("rec-b", created_at=TS_MID))
        store.insert(_record("rec-a", created_at=TS_EARLY))
        store.insert(_evidenced_record("rec-c"))
        store.transition_lifecycle("rec-a", LifecycleState.STALE)
        return store

    first = build()
    second = build()
    assert first.to_json() == second.to_json()
    assert [r.record_id for r in first.list_records()] == [
        r.record_id for r in second.list_records()
    ]


def test_repeated_reads_do_not_mutate_store() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_evidenced_record("rec-1"))
    before = store.to_json()
    for _ in range(5):
        store.get("rec-1")
        store.list_records()
        store.find("rec-1")
    assert store.to_json() == before
