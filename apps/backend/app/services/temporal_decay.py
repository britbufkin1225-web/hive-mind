"""Phase 13A — deterministic temporal knowledge decay derivation.

Replaces the static Temporal Knowledge Decay demo fixture with a real backend
derivation. :func:`derive_decay_statuses` projects the existing store nodes (and
their linked sources) into read-only :class:`DecayStatus` rows using simple,
explainable timestamp thresholds.

Guardrails honored here:

  * NO AI/LLM, NO scoring engine — only timestamp arithmetic.
  * NO randomness; ``now`` is injectable so tests are fully deterministic.
  * NO graph/knowledge mutation and NO filesystem access — this is a pure,
    read-only projection over already-persisted store state.

Temporal Decay, Dreaming Suggestions, and Provenance Chains now each have their
own derivation service. Query Trails remain fixture-backed pending their
dedicated phase (see :mod:`app.services.intelligence_fixtures`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    DecayStatus,
    DecayStatusBucket,
    HiveGraphNode,
    HiveSource,
    SourceStatus,
)

# Explainable freshness thresholds (inclusive upper bounds in days), measured
# against the most recent usable timestamp on a node. Kept as module constants
# so the rule is trivially reviewable and stable.
FRESH_MAX_DAYS = 30
AGING_MAX_DAYS = 90

# Deterministic ordering: most-needs-attention first, then by node id.
_BUCKET_SORT_RANK = {
    DecayStatusBucket.STALE: 0,
    DecayStatusBucket.UNKNOWN: 1,
    DecayStatusBucket.AGING: 2,
    DecayStatusBucket.FRESH: 3,
}

# Lightweight reliability labels derived from the linked source's status. This is
# a presentational hint, not a trust engine.
_SOURCE_RELIABILITY_HINT = {
    SourceStatus.ACTIVE: "reliable",
    SourceStatus.PENDING: "provisional",
    SourceStatus.ERROR: "review",
    SourceStatus.DISABLED: "inactive",
}


def _classify(age_days: int) -> DecayStatusBucket:
    """Bucket a node by how many whole days since its most recent activity."""
    if age_days <= FRESH_MAX_DAYS:
        return DecayStatusBucket.FRESH
    if age_days <= AGING_MAX_DAYS:
        return DecayStatusBucket.AGING
    return DecayStatusBucket.STALE


def _node_imported_at(node: HiveGraphNode, source: HiveSource | None) -> datetime | None:
    """Best-available "last imported" signal for a node.

    Prefers the node's own vault file modification time (set on import), falling
    back to the linked source's ``updated_at`` (when the source was last
    ingested/refreshed). Returns ``None`` when neither is available.
    """
    if node.file_meta is not None and node.file_meta.last_modified is not None:
        return node.file_meta.last_modified
    if source is not None:
        return source.updated_at
    return None


def _decay_status_for_node(
    node: HiveGraphNode,
    source: HiveSource | None,
    now: datetime,
) -> DecayStatus:
    last_updated_at = node.updated_at
    last_imported_at = _node_imported_at(node, source)
    source_reliability_hint = (
        _SOURCE_RELIABILITY_HINT.get(source.status) if source is not None else None
    )

    # The freshest signal we have about this node drives the bucket.
    candidates = [
        ts
        for ts in (last_updated_at, last_imported_at, node.created_at)
        if ts is not None
    ]

    if not candidates:
        return DecayStatus(
            node_id=node.id,
            status=DecayStatusBucket.UNKNOWN,
            last_imported_at=last_imported_at,
            last_referenced_at=None,
            last_updated_at=last_updated_at,
            source_reliability_hint=source_reliability_hint,
            review_needed=True,
            metadata={
                "derived": True,
                "reason": "No usable timestamp on node; freshness cannot be assessed.",
            },
        )

    reference = max(candidates)
    age_days = (now - reference).days
    status = _classify(age_days)
    review_needed = status is not DecayStatusBucket.FRESH

    reason = (
        f"Most recent activity {reference.date().isoformat()} "
        f"({age_days}d ago); classified {status.value} "
        f"(fresh <= {FRESH_MAX_DAYS}d, aging <= {AGING_MAX_DAYS}d)."
    )

    return DecayStatus(
        node_id=node.id,
        status=status,
        last_imported_at=last_imported_at,
        last_referenced_at=None,
        last_updated_at=last_updated_at,
        source_reliability_hint=source_reliability_hint,
        review_needed=review_needed,
        metadata={
            "derived": True,
            "reason": reason,
            "age_days": age_days,
        },
    )


def derive_decay_statuses(*, store, now: datetime | None = None) -> list[DecayStatus]:
    """Derive deterministic temporal decay rows from store nodes.

    Read-only: ``store`` is only queried, never mutated. ``now`` defaults to the
    current UTC time but is injectable so the derivation is fully deterministic
    in tests. Output is sorted most-stale-first, then by ``node_id``.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    sources_by_id = {s.id: s for s in store.get_sources()}

    statuses = [
        _decay_status_for_node(
            node,
            sources_by_id.get(node.source_id) if node.source_id else None,
            now,
        )
        for node in store.get_nodes()
    ]

    statuses.sort(key=lambda s: (_BUCKET_SORT_RANK[s.status], s.node_id))
    return statuses
