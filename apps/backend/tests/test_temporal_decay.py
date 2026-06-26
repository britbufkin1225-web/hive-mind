"""Phase 13A — unit tests for deterministic temporal decay derivation.

These cover :func:`app.services.temporal_decay.derive_decay_statuses` directly
with an injected ``now`` and a lightweight fake store, so classification is
fully deterministic and never depends on the real wall clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.hive_models import (
    DecayStatusBucket,
    GraphNodeType,
    HiveGraphNode,
    HiveSource,
    SourceStatus,
    SourceType,
    VaultFileMeta,
)
from app.services.temporal_decay import (
    AGING_MAX_DAYS,
    FRESH_MAX_DAYS,
    derive_decay_statuses,
)

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


class FakeStore:
    """Minimal read-only store exposing only what the derivation needs."""

    def __init__(self, nodes, sources=()):
        self._nodes = list(nodes)
        self._sources = list(sources)

    def get_nodes(self):
        return list(self._nodes)

    def get_sources(self):
        return list(self._sources)


def _node(
    node_id: str,
    *,
    updated_days_ago: int | None = 0,
    created_days_ago: int | None = None,
    source_id: str | None = None,
    file_modified_days_ago: int | None = None,
) -> HiveGraphNode:
    if created_days_ago is None:
        created_days_ago = updated_days_ago if updated_days_ago is not None else 0
    file_meta = None
    if file_modified_days_ago is not None:
        file_meta = VaultFileMeta(
            last_modified=NOW - timedelta(days=file_modified_days_ago)
        )
    return HiveGraphNode(
        id=node_id,
        label=node_id,
        type=GraphNodeType.NOTE,
        source_id=source_id,
        created_at=NOW - timedelta(days=created_days_ago),
        updated_at=NOW - timedelta(days=updated_days_ago),
        file_meta=file_meta,
    )


def _source(source_id: str, status: SourceStatus) -> HiveSource:
    return HiveSource(
        id=source_id,
        name=source_id,
        type=SourceType.MARKDOWN,
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def _one(store) -> object:
    statuses = derive_decay_statuses(store=store, now=NOW)
    assert len(statuses) == 1
    return statuses[0]


def test_fresh_record_is_classified_fresh() -> None:
    status = _one(FakeStore([_node("n", updated_days_ago=10)]))
    assert status.status is DecayStatusBucket.FRESH
    assert status.review_needed is False
    assert status.metadata["derived"] is True
    assert status.metadata["age_days"] == 10
    assert status.metadata.get("fixture") is not True


def test_aging_record_is_classified_aging() -> None:
    status = _one(FakeStore([_node("n", updated_days_ago=60)]))
    assert status.status is DecayStatusBucket.AGING
    assert status.review_needed is True


def test_stale_record_is_classified_stale() -> None:
    status = _one(FakeStore([_node("n", updated_days_ago=200)]))
    assert status.status is DecayStatusBucket.STALE
    assert status.review_needed is True


def test_bucket_boundaries_are_inclusive_upper_bounds() -> None:
    cases = {
        FRESH_MAX_DAYS: DecayStatusBucket.FRESH,
        FRESH_MAX_DAYS + 1: DecayStatusBucket.AGING,
        AGING_MAX_DAYS: DecayStatusBucket.AGING,
        AGING_MAX_DAYS + 1: DecayStatusBucket.STALE,
    }
    for days, expected in cases.items():
        status = _one(FakeStore([_node("n", updated_days_ago=days)]))
        assert status.status is expected, f"{days}d should be {expected}"


def test_missing_timestamps_classified_unknown() -> None:
    # Real HiveGraphNode always carries created_at/updated_at, so the unknown
    # path is defensive. Force the no-usable-timestamp case via model_construct.
    node = HiveGraphNode.model_construct(
        id="n",
        label="n",
        type=GraphNodeType.NOTE,
        source_id=None,
        created_at=None,
        updated_at=None,
        file_meta=None,
    )
    status = _one(FakeStore([node]))
    assert status.status is DecayStatusBucket.UNKNOWN
    assert status.review_needed is True
    assert status.metadata["derived"] is True


def test_most_recent_signal_drives_bucket() -> None:
    # Created long ago, but a recent file modification keeps it fresh.
    node = _node("n", updated_days_ago=200, created_days_ago=300, file_modified_days_ago=5)
    status = _one(FakeStore([node]))
    assert status.status is DecayStatusBucket.FRESH
    assert status.metadata["age_days"] == 5


def test_source_reliability_hint_derives_from_source_status() -> None:
    store = FakeStore(
        nodes=[
            _node("active", source_id="s-active"),
            _node("error", source_id="s-error"),
            _node("orphan"),
        ],
        sources=[
            _source("s-active", SourceStatus.ACTIVE),
            _source("s-error", SourceStatus.ERROR),
        ],
    )
    by_id = {s.node_id: s for s in derive_decay_statuses(store=store, now=NOW)}
    assert by_id["active"].source_reliability_hint == "reliable"
    assert by_id["error"].source_reliability_hint == "review"
    assert by_id["orphan"].source_reliability_hint is None


def test_output_ordering_is_deterministic() -> None:
    store = FakeStore(
        [
            _node("z-fresh", updated_days_ago=1),
            _node("a-fresh", updated_days_ago=1),
            _node("stale", updated_days_ago=400),
            _node("aging", updated_days_ago=60),
        ]
    )
    order = [s.node_id for s in derive_decay_statuses(store=store, now=NOW)]
    # Most-stale-first, then alphabetical within a bucket.
    assert order == ["stale", "aging", "a-fresh", "z-fresh"]


def test_derivation_is_repeatable_and_read_only() -> None:
    store = FakeStore([_node("n", updated_days_ago=10)])
    first = derive_decay_statuses(store=store, now=NOW)
    second = derive_decay_statuses(store=store, now=NOW)
    assert [s.model_dump() for s in first] == [s.model_dump() for s in second]
    # Fake store collections are unchanged (pure projection).
    assert len(store.get_nodes()) == 1
