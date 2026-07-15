"""Phase 37D — Deterministic Active Memory contradiction-detection tests.

Covers the read-only derivation service in
:mod:`app.services.active_memory_contradiction`: positive detection of the
implemented contract classes, conservative negative behavior (no guessed
contradictions), determinism / order-independence / stable ids, and store safety
(detection never mutates the store, its record count, or lifecycle state).

Fixtures are contract-valid Phase 37B records; assertions are targeted rather than
snapshot blobs. The detector never reads the wall clock, so every call passes a
fixed ``DETECTED_AT``.
"""

from __future__ import annotations

from datetime import datetime

from app.models.active_memory import (
    ClaimValueKind,
    ContradictionClass,
    ContradictionResolutionState,
    ContradictionSeverity,
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
    VerificationState,
)
from app.services.active_memory_contradiction import (
    ActiveMemoryContradictionDetector,
    detect_contradictions,
)
from app.store.active_memory_store import InMemoryActiveMemoryStore

DETECTED_AT = datetime(2026, 7, 15, 9, 0, 0)
TS = datetime(2026, 1, 1, 12, 0, 0)


# --------------------------------------------------------------------------- #
# Contract-valid fixture builders
# --------------------------------------------------------------------------- #
def _source(source_id: str = "repo-observer") -> MemorySource:
    return MemorySource(
        source_type=MemorySourceType.REPOSITORY_OBSERVER, source_id=source_id
    )


def _record(
    record_id: str,
    *,
    kind: MemoryRecordKind = MemoryRecordKind.PHASE_STATUS,
    subject: str = "Phase 37B",
    predicate: str = "merge_status",
    value: str = "merged",
    value_kind: ClaimValueKind = ClaimValueKind.STRING,
    project_id: str = "hive-mind",
    scope: MemoryScope | None = None,
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE,
    verification_state: VerificationState = VerificationState.UNVERIFIED,
    evidence_ids: list[str] | None = None,
    supersession_refs: list[SupersessionReference] | None = None,
    created_at: datetime = TS,
) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        kind=kind,
        claim=MemoryClaim(
            subject=subject, predicate=predicate, value=value, value_kind=value_kind
        ),
        project_id=project_id,
        scope=scope,
        source=_source(),
        verification_state=verification_state,
        lifecycle_state=lifecycle_state,
        evidence_ids=evidence_ids or [],
        supersession_refs=supersession_refs or [],
        created_at=created_at,
    )


def _detect(records: list[MemoryRecord]):
    return detect_contradictions(records, detected_at=DETECTED_AT)


# =========================================================================== #
# Positive detection
# =========================================================================== #
def test_pending_vs_merged_pair_produces_one_contradiction() -> None:
    merged = _record("rec-merged", value="merged", evidence_ids=["ev-1"])
    pending = _record("rec-pending", value="pending", evidence_ids=["ev-2"])
    results = _detect([merged, pending])

    assert len(results) == 1
    contradiction = results[0]
    assert contradiction.contradiction_class is ContradictionClass.PENDING_VS_MERGED
    # Both supporting records are included as evidence (sorted).
    assert contradiction.involved_record_ids == ["rec-merged", "rec-pending"]
    # Evidence references the originals' evidence, unioned and sorted.
    assert contradiction.evidence_ids == ["ev-1", "ev-2"]
    # Never auto-resolved.
    assert contradiction.resolution_state is ContradictionResolutionState.OPEN
    assert contradiction.severity is ContradictionSeverity.CRITICAL
    # Canonical conflicting values are represented for both records.
    conflicting = contradiction.metadata["conflicting_values"]
    assert {c["record_id"]: c["normalized_value"] for c in conflicting} == {
        "rec-merged": "merged",
        "rec-pending": "pending",
    }


def test_clean_vs_dirty_working_tree_pair() -> None:
    clean = _record(
        "rec-clean",
        kind=MemoryRecordKind.REPOSITORY_STATE,
        subject="working tree",
        predicate="state",
        value="clean",
    )
    dirty = _record(
        "rec-dirty",
        kind=MemoryRecordKind.REPOSITORY_STATE,
        subject="working tree",
        predicate="state",
        value="dirty",
    )
    results = _detect([clean, dirty])
    assert len(results) == 1
    assert (
        results[0].contradiction_class
        is ContradictionClass.CLEAN_VS_DIRTY_WORKING_TREE
    )
    assert results[0].severity is ContradictionSeverity.INFO


def test_duplicate_phase_status_pair_for_generic_value_difference() -> None:
    a = _record("rec-a", predicate="status", value="complete")
    b = _record("rec-b", predicate="status", value="in_progress")
    results = _detect([a, b])
    assert len(results) == 1
    assert results[0].contradiction_class is ContradictionClass.DUPLICATE_PHASE_STATUS
    assert results[0].severity is ContradictionSeverity.WARNING


def test_current_vs_superseded_decision() -> None:
    decision = _record(
        "rec-old-decision",
        kind=MemoryRecordKind.PROJECT_DECISION,
        subject="storage medium",
        predicate="chosen",
        value="in_memory",
        evidence_ids=["ev-old"],
    )
    newer = _record(
        "rec-new-decision",
        kind=MemoryRecordKind.PROJECT_DECISION,
        subject="storage medium",
        predicate="chosen",
        value="in_memory",  # same value on purpose: conflict is structural, not value
        evidence_ids=["ev-new"],
        supersession_refs=[
            SupersessionReference(
                kind=SupersessionKind.SUPERSEDES,
                target_record_id="rec-old-decision",
                created_at=TS,
            )
        ],
    )
    results = _detect([decision, newer])
    # Same value + same target would NOT be a value conflict; the supersession
    # pass is what fires here.
    classes = {r.contradiction_class for r in results}
    assert ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION in classes
    supersede = next(
        r
        for r in results
        if r.contradiction_class
        is ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION
    )
    assert supersede.involved_record_ids == ["rec-new-decision", "rec-old-decision"]
    assert supersede.evidence_ids == ["ev-new", "ev-old"]
    assert supersede.metadata["superseded_record_id"] == "rec-old-decision"
    assert supersede.metadata["superseding_record_id"] == "rec-new-decision"


def test_stable_contradiction_id_is_content_derived() -> None:
    merged = _record("rec-merged", value="merged")
    pending = _record("rec-pending", value="pending")
    first = _detect([merged, pending])[0]
    # Re-running over unchanged records reproduces the same id.
    second = _detect([merged, pending])[0]
    assert first.contradiction_id == second.contradiction_id
    assert first.contradiction_id.startswith("contradiction-")


# =========================================================================== #
# Negative detection (conservative — no guessed contradictions)
# =========================================================================== #
def test_identical_assertions_do_not_conflict() -> None:
    a = _record("rec-a", value="merged")
    b = _record("rec-b", value="merged")
    assert _detect([a, b]) == []


def test_unrelated_subjects_do_not_conflict() -> None:
    a = _record("rec-a", subject="Phase 37B", value="merged")
    b = _record("rec-b", subject="Phase 37C", value="pending")
    assert _detect([a, b]) == []


def test_unrelated_scopes_do_not_conflict() -> None:
    a = _record(
        "rec-a",
        value="merged",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="37B"),
    )
    b = _record(
        "rec-b",
        value="pending",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="37C"),
    )
    assert _detect([a, b]) == []


def test_scoped_vs_unscoped_do_not_conflict() -> None:
    # No scope inheritance in this phase: a scoped and an unscoped claim about the
    # same subject/predicate are different targets.
    scoped = _record(
        "rec-scoped",
        value="merged",
        scope=MemoryScope(scope_type=MemoryScopeType.PHASE, scope_id="37B"),
    )
    unscoped = _record("rec-unscoped", value="pending")
    assert _detect([scoped, unscoped]) == []


def test_unrelated_predicates_do_not_conflict() -> None:
    a = _record("rec-a", predicate="merge_status", value="merged")
    b = _record("rec-b", predicate="review_status", value="pending")
    assert _detect([a, b]) == []


def test_single_record_never_conflicts_with_itself() -> None:
    assert _detect([_record("rec-a", value="merged")]) == []


def test_duplicate_record_does_not_duplicate_output() -> None:
    merged = _record("rec-merged", value="merged")
    pending = _record("rec-pending", value="pending")
    # The same records passed twice must not double the contradiction.
    once = _detect([merged, pending])
    twice = _detect([merged, pending, merged, pending])
    assert len(once) == 1
    assert len(twice) == 1
    assert once[0].contradiction_id == twice[0].contradiction_id


def test_value_kind_mismatch_is_not_a_guessed_contradiction() -> None:
    # Missing/mismatched comparison basis: compared like-with-like only.
    string_val = _record("rec-a", value="merged", value_kind=ClaimValueKind.STRING)
    bool_val = _record("rec-b", value="pending", value_kind=ClaimValueKind.BOOLEAN)
    assert _detect([string_val, bool_val]) == []


def test_generic_value_difference_without_class_is_not_reported() -> None:
    # Two non-phase-status records with differing values that match no recognized
    # exclusivity vocabulary produce nothing (no general "values differ" class).
    a = _record(
        "rec-a",
        kind=MemoryRecordKind.PROJECT_FACT,
        subject="db",
        predicate="engine",
        value="sqlite",
    )
    b = _record(
        "rec-b",
        kind=MemoryRecordKind.PROJECT_FACT,
        subject="db",
        predicate="engine",
        value="postgres",
    )
    assert _detect([a, b]) == []


def test_lifecycle_ineligible_records_are_excluded() -> None:
    active_merged = _record("rec-merged", value="merged")
    for ineligible_state in (
        LifecycleState.SUPERSEDED,
        LifecycleState.RETRACTED,
        LifecycleState.STALE,
        LifecycleState.INACTIVE,
        LifecycleState.ARCHIVED,
    ):
        other = _record(
            "rec-pending", value="pending", lifecycle_state=ineligible_state
        )
        assert _detect([active_merged, other]) == [], ineligible_state


def test_superseded_decision_excluded_when_target_not_active() -> None:
    # If the decision has already left the active baseline, there is no conflict.
    decision = _record(
        "rec-old-decision",
        kind=MemoryRecordKind.PROJECT_DECISION,
        lifecycle_state=LifecycleState.SUPERSEDED,
    )
    newer = _record(
        "rec-new-decision",
        kind=MemoryRecordKind.PROJECT_DECISION,
        supersession_refs=[
            SupersessionReference(
                kind=SupersessionKind.SUPERSEDES,
                target_record_id="rec-old-decision",
                created_at=TS,
            )
        ],
    )
    assert _detect([decision, newer]) == []


def test_supersedes_link_to_non_decision_is_not_reported() -> None:
    fact = _record("rec-fact", kind=MemoryRecordKind.PROJECT_FACT)
    newer = _record(
        "rec-new",
        kind=MemoryRecordKind.PROJECT_DECISION,
        supersession_refs=[
            SupersessionReference(
                kind=SupersessionKind.SUPERSEDES,
                target_record_id="rec-fact",
                created_at=TS,
            )
        ],
    )
    # Different subjects anyway, but the point is the supersession pass only fires
    # for a superseded *decision*.
    supersede = [
        r
        for r in _detect([fact, newer])
        if r.contradiction_class
        is ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION
    ]
    assert supersede == []


def test_frontend_vs_backend_class_is_deferred_not_emitted() -> None:
    # The deferred class must never be produced by the MVP detector.
    constraint = _record(
        "rec-constraint",
        kind=MemoryRecordKind.PROJECT_CONSTRAINT,
        subject="phase 37d",
        predicate="scope",
        value="backend_only",
    )
    modification = _record(
        "rec-mod",
        kind=MemoryRecordKind.REPOSITORY_STATE,
        subject="frontend/src/app.tsx",
        predicate="modified",
        value="true",
        value_kind=ClaimValueKind.BOOLEAN,
    )
    classes = {r.contradiction_class for r in _detect([constraint, modification])}
    assert (
        ContradictionClass.FRONTEND_ONLY_VS_BACKEND_MODIFICATION not in classes
    )


# =========================================================================== #
# Determinism
# =========================================================================== #
def test_reversed_insertion_order_produces_identical_results() -> None:
    records = [
        _record("rec-merged", value="merged"),
        _record("rec-pending", value="pending"),
        _record(
            "rec-clean",
            kind=MemoryRecordKind.REPOSITORY_STATE,
            subject="tree",
            predicate="state",
            value="clean",
        ),
        _record(
            "rec-dirty",
            kind=MemoryRecordKind.REPOSITORY_STATE,
            subject="tree",
            predicate="state",
            value="dirty",
        ),
    ]
    forward = _detect(records)
    backward = _detect(list(reversed(records)))
    assert [c.contradiction_id for c in forward] == [
        c.contradiction_id for c in backward
    ]
    assert [c.model_dump() for c in forward] == [c.model_dump() for c in backward]


def test_repeated_detection_is_identical() -> None:
    records = [
        _record("rec-merged", value="merged"),
        _record("rec-pending", value="pending"),
    ]
    first = _detect(records)
    second = _detect(records)
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]


def test_result_order_is_stable_and_severity_first() -> None:
    # A critical (pending/merged) and an info (clean/dirty) contradiction: the
    # critical one must sort first regardless of input order.
    records = [
        _record(
            "rec-clean",
            kind=MemoryRecordKind.REPOSITORY_STATE,
            subject="tree",
            predicate="state",
            value="clean",
        ),
        _record(
            "rec-dirty",
            kind=MemoryRecordKind.REPOSITORY_STATE,
            subject="tree",
            predicate="state",
            value="dirty",
        ),
        _record("rec-merged", value="merged"),
        _record("rec-pending", value="pending"),
    ]
    ordered = _detect(records)
    severities = [c.severity for c in ordered]
    assert severities[0] is ContradictionSeverity.CRITICAL
    assert severities[-1] is ContradictionSeverity.INFO
    # Order is invariant under input reordering.
    assert [c.contradiction_id for c in ordered] == [
        c.contradiction_id for c in _detect(list(reversed(records)))
    ]


def test_case_and_whitespace_equivalent_values_do_not_conflict() -> None:
    a = _record("rec-a", value="Merged")
    b = _record("rec-b", value="  merged  ")
    assert _detect([a, b]) == []


def test_case_insensitive_target_grouping_still_detects_conflict() -> None:
    # Subjects differing only by case are the same target.
    a = _record("rec-a", subject="Phase 37B", value="merged")
    b = _record("rec-b", subject="phase 37b", value="pending")
    results = _detect([a, b])
    assert len(results) == 1
    assert results[0].contradiction_class is ContradictionClass.PENDING_VS_MERGED


# =========================================================================== #
# Store safety (read-only)
# =========================================================================== #
def test_detection_via_store_does_not_mutate_it() -> None:
    store = InMemoryActiveMemoryStore()
    store.insert(_record("rec-merged", value="merged", evidence_ids=["ev-1"]))
    store.insert(_record("rec-pending", value="pending", evidence_ids=["ev-2"]))
    before = store.to_json()
    before_len = len(store)

    detector = ActiveMemoryContradictionDetector()
    results = detector.detect_from_store(store, detected_at=DETECTED_AT)

    assert len(results) == 1
    # No record was mutated, added, removed, relifecycled, or resolved.
    assert store.to_json() == before
    assert len(store) == before_len
    assert store.get("rec-merged").lifecycle_state is LifecycleState.ACTIVE
    assert store.get("rec-pending").lifecycle_state is LifecycleState.ACTIVE


def test_detect_from_store_matches_pure_function() -> None:
    merged = _record("rec-merged", value="merged")
    pending = _record("rec-pending", value="pending")
    store = InMemoryActiveMemoryStore.from_records([merged, pending])
    detector = ActiveMemoryContradictionDetector()
    from_store = detector.detect_from_store(store, detected_at=DETECTED_AT)
    pure = _detect([merged, pending])
    assert [c.model_dump() for c in from_store] == [c.model_dump() for c in pure]


def test_verification_state_does_not_affect_eligibility() -> None:
    # A contradiction is structural: an unverified active claim still participates.
    merged = _record(
        "rec-merged", value="merged", verification_state=VerificationState.UNVERIFIED
    )
    pending = _record(
        "rec-pending",
        value="pending",
        verification_state=VerificationState.VERIFIED,
    )
    assert len(_detect([merged, pending])) == 1
