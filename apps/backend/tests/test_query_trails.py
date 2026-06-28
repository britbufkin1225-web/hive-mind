"""Phase 16C — Query Trails backend derivation tests.

Covers :func:`app.services.query_trails.derive_query_trail_entries`: the
supported MVP categories derived from existing structural store data
(``source_followup``, ``knowledge_gap``, ``related_query_cluster``), the
empty-state guarantee, deterministic ordering, read-only behavior, backend-owned
evidence metadata, and the guardrail that query-history-dependent categories
(``repeated_query`` / ``unresolved_question``) are never emitted without persisted
query history.
"""

from datetime import datetime, timezone

from app.models.hive_models import (
    GraphNodeType,
    HiveGraphNode,
    HiveSource,
    QueryTrailCategory,
    QueryTrailKind,
    QueryTrailStatus,
    SourceStatus,
    SourceType,
)
from app.services.query_trails import (
    _BLOCKED_CATEGORIES,
    derive_query_trail_entries,
)

_NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


class _FakeStore:
    """Tiny read-only store double exposing only what the derivation reads."""

    def __init__(self, nodes=(), sources=()):
        self._nodes = list(nodes)
        self._sources = list(sources)
        self.mutated = False

    def get_nodes(self):
        # Hand back copies so accidental mutation by the derivation is detectable.
        return list(self._nodes)

    def get_sources(self):
        return list(self._sources)


def _node(node_id, *, label="Concept", source_id=None, tags=(), updated_at=_NOW):
    return HiveGraphNode(
        id=node_id,
        label=label,
        type=GraphNodeType.NOTE,
        source_id=source_id,
        tags=list(tags),
        created_at=_NOW,
        updated_at=updated_at,
    )


def _source(source_id, *, name="Source", updated_at=_NOW):
    return HiveSource(
        id=source_id,
        name=name,
        type=SourceType.MARKDOWN,
        status=SourceStatus.ACTIVE,
        created_at=_NOW,
        updated_at=updated_at,
    )


# --------------------------------------------------------------------------- #
# Empty / fallback state
# --------------------------------------------------------------------------- #
def test_empty_store_yields_no_trails() -> None:
    assert derive_query_trail_entries(store=_FakeStore()) == []


def test_store_with_only_a_covered_source_has_no_gap() -> None:
    # A source with a linked node yields a follow-up, not a knowledge gap.
    store = _FakeStore(
        nodes=[_node("n-1", source_id="s-1")],
        sources=[_source("s-1")],
    )
    cats = {e.category for e in derive_query_trail_entries(store=store)}
    assert QueryTrailCategory.SOURCE_FOLLOWUP in cats
    assert QueryTrailCategory.KNOWLEDGE_GAP not in cats


# --------------------------------------------------------------------------- #
# source_followup
# --------------------------------------------------------------------------- #
def test_source_followup_derived_for_source_with_linked_nodes() -> None:
    store = _FakeStore(
        nodes=[
            _node("n-1", source_id="s-1"),
            _node("n-2", source_id="s-1"),
        ],
        sources=[_source("s-1", name="Research Vault")],
    )
    followups = [
        e
        for e in derive_query_trail_entries(store=store)
        if e.category is QueryTrailCategory.SOURCE_FOLLOWUP
    ]
    assert len(followups) == 1
    entry = followups[0]
    assert entry.id == "qt-source-followup-s-1"
    assert entry.status is QueryTrailStatus.RESOLVED
    assert entry.kind is QueryTrailKind.SEARCH
    assert entry.result_node_ids == ["n-1", "n-2"]
    assert entry.result_source_ids == ["s-1"]
    # Cross-links to derived provenance chains by id only.
    assert entry.provenance_chain_ids == ["provenance-n-1", "provenance-n-2"]
    assert entry.result_count == 2
    assert "Research Vault" in entry.query
    assert entry.metadata["evidence"]["reason"]


# --------------------------------------------------------------------------- #
# knowledge_gap
# --------------------------------------------------------------------------- #
def test_knowledge_gap_for_unsourced_node() -> None:
    store = _FakeStore(nodes=[_node("orphan-1", label="Floating Idea")])
    gaps = [
        e
        for e in derive_query_trail_entries(store=store)
        if e.category is QueryTrailCategory.KNOWLEDGE_GAP
    ]
    assert len(gaps) == 1
    entry = gaps[0]
    assert entry.id == "qt-knowledge-gap-node-orphan-1"
    # A gap is an open/unresolved state.
    assert entry.status is QueryTrailStatus.UNRESOLVED
    assert entry.result_count == 0
    assert entry.metadata["evidence"]["history_available"] is False
    assert entry.metadata["gap_kind"] == "unsourced_node"


def test_knowledge_gap_for_uncovered_source() -> None:
    store = _FakeStore(sources=[_source("s-empty", name="Untouched Import")])
    gaps = [
        e
        for e in derive_query_trail_entries(store=store)
        if e.category is QueryTrailCategory.KNOWLEDGE_GAP
    ]
    assert len(gaps) == 1
    entry = gaps[0]
    assert entry.id == "qt-knowledge-gap-source-s-empty"
    assert entry.status is QueryTrailStatus.UNRESOLVED
    assert entry.result_source_ids == ["s-empty"]
    assert entry.metadata["gap_kind"] == "uncovered_source"


# --------------------------------------------------------------------------- #
# related_query_cluster
# --------------------------------------------------------------------------- #
def test_related_query_cluster_for_shared_tag() -> None:
    store = _FakeStore(
        nodes=[
            _node("n-1", source_id="s-1", tags=["backend", "solo"]),
            _node("n-2", source_id="s-1", tags=["backend"]),
        ],
        sources=[_source("s-1")],
    )
    clusters = [
        e
        for e in derive_query_trail_entries(store=store)
        if e.category is QueryTrailCategory.RELATED_QUERY_CLUSTER
    ]
    # "backend" is shared by 2 nodes -> a cluster; "solo" appears once -> none.
    assert len(clusters) == 1
    entry = clusters[0]
    assert entry.id == "qt-related-cluster-backend"
    assert entry.result_node_ids == ["n-1", "n-2"]
    assert entry.metadata["shared_tag"] == "backend"
    assert entry.metadata["cluster_size"] == 2


def test_single_node_tag_is_not_a_cluster() -> None:
    store = _FakeStore(nodes=[_node("n-1", source_id="s-1", tags=["unique"])])
    clusters = [
        e
        for e in derive_query_trail_entries(store=store)
        if e.category is QueryTrailCategory.RELATED_QUERY_CLUSTER
    ]
    assert clusters == []


# --------------------------------------------------------------------------- #
# Blocked / deferred categories
# --------------------------------------------------------------------------- #
def test_blocked_categories_never_emitted() -> None:
    # A data shape that could superficially look "repeated" or "unresolved" must
    # still never produce those query-history-dependent categories.
    store = _FakeStore(
        nodes=[
            _node("n-1", source_id="s-1", tags=["x"]),
            _node("n-2", source_id="s-1", tags=["x"]),
            _node("n-3"),  # unsourced
        ],
        sources=[_source("s-1"), _source("s-2")],  # s-2 uncovered
    )
    entries = derive_query_trail_entries(store=store)
    assert entries, "expected some derived trails for this store"
    emitted = {e.category for e in entries}
    for blocked in _BLOCKED_CATEGORIES:
        assert blocked not in emitted
    assert QueryTrailCategory.REPEATED_QUERY not in emitted
    assert QueryTrailCategory.UNRESOLVED_QUESTION not in emitted
    # No fabricated query memory anywhere.
    assert all(e.occurrence_count == 1 for e in entries)
    assert all(e.pinned is False for e in entries)


# --------------------------------------------------------------------------- #
# Determinism, evidence, and read-only behavior
# --------------------------------------------------------------------------- #
def test_output_is_deterministic_and_sorted_by_category() -> None:
    store = _FakeStore(
        nodes=[
            _node("n-2", source_id="s-1", tags=["t"]),
            _node("n-1", source_id="s-1", tags=["t"]),
            _node("n-3"),
        ],
        sources=[_source("s-1")],
    )
    first = derive_query_trail_entries(store=store)
    second = derive_query_trail_entries(store=store)
    assert first == second
    # Category rank order: source_followup < knowledge_gap < related_query_cluster.
    rank = {
        QueryTrailCategory.SOURCE_FOLLOWUP: 0,
        QueryTrailCategory.KNOWLEDGE_GAP: 1,
        QueryTrailCategory.RELATED_QUERY_CLUSTER: 2,
    }
    ranks = [rank[e.category] for e in first]
    assert ranks == sorted(ranks)


def test_every_entry_carries_backend_owned_evidence() -> None:
    store = _FakeStore(
        nodes=[_node("n-1", source_id="s-1", tags=["t"]), _node("n-2", tags=["t"])],
        sources=[_source("s-1"), _source("s-empty")],
    )
    for entry in derive_query_trail_entries(store=store):
        assert entry.metadata["derived"] is True
        assert entry.metadata["fixture"] is False
        assert entry.metadata["derivation_origin"] == "query_trail_derivation"
        evidence = entry.metadata["evidence"]
        assert evidence["reason"]
        assert evidence["derivation"]
        assert evidence["fields_used"]
        # Honesty markers: not a real query log.
        assert evidence["history_available"] is False
        assert evidence["last_executed_at_basis"] == "underlying_record_activity"


def test_derivation_does_not_mutate_store_records() -> None:
    nodes = [_node("n-1", source_id="s-1", tags=["t"]), _node("n-2", tags=["t"])]
    sources = [_source("s-1")]
    store = _FakeStore(nodes=nodes, sources=sources)
    before_node = nodes[0].model_dump()
    before_source = sources[0].model_dump()
    derive_query_trail_entries(store=store)
    assert nodes[0].model_dump() == before_node
    assert sources[0].model_dump() == before_source
