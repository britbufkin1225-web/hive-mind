"""Phase 14C — unit tests for deterministic Dreaming suggestion derivation.

These cover :func:`app.services.dreaming.derive_dreaming_suggestions` directly
with an injected ``now`` and a lightweight fake store, so derivation is fully
deterministic and never depends on the real wall clock. They also assert the
read-only / non-mutating guarantee, the stable evidence contract, and that the
blocked types (``unresolved_query`` / ``source_coverage_gap``) are never emitted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.hive_models import (
    DreamingSuggestionType,
    GraphNodeType,
    GraphRelationship,
    HiveGraphEdge,
    HiveGraphNode,
    HiveSource,
    SourceStatus,
    SourceType,
)
from app.services.dreaming import (
    STALE_LINK_MIN_AGE_DAYS,
    STALE_LINK_MIN_DRIFT_DAYS,
    derive_dreaming_suggestions,
)

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


class FakeStore:
    """Minimal read-only store exposing only what the derivation needs."""

    def __init__(self, nodes=(), edges=(), sources=()):
        self._nodes = list(nodes)
        self._edges = list(edges)
        self._sources = list(sources)

    def get_nodes(self):
        return list(self._nodes)

    def get_edges(self):
        return list(self._edges)

    def get_sources(self):
        return list(self._sources)


def _node(
    node_id: str,
    *,
    label: str | None = None,
    updated_days_ago: int = 0,
    created_days_ago: int | None = None,
    source_id: str | None = None,
    parent_id: str | None = None,
) -> HiveGraphNode:
    if created_days_ago is None:
        created_days_ago = updated_days_ago
    return HiveGraphNode(
        id=node_id,
        label=label if label is not None else node_id,
        type=GraphNodeType.NOTE,
        source_id=source_id,
        parent_id=parent_id,
        created_at=NOW - timedelta(days=created_days_ago),
        updated_at=NOW - timedelta(days=updated_days_ago),
    )


def _edge(
    edge_id: str,
    src: str,
    tgt: str,
    *,
    created_days_ago: int = 0,
) -> HiveGraphEdge:
    return HiveGraphEdge(
        id=edge_id,
        source_node_id=src,
        target_node_id=tgt,
        relationship=GraphRelationship.LINKED_TO,
        created_at=NOW - timedelta(days=created_days_ago),
    )


def _source(source_id: str) -> HiveSource:
    return HiveSource(
        id=source_id,
        name=source_id,
        type=SourceType.MARKDOWN,
        status=SourceStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def _derive(store):
    return derive_dreaming_suggestions(store=store, now=NOW)


# --------------------------------------------------------------------------- #
# Empty / clean state
# --------------------------------------------------------------------------- #
def test_empty_store_returns_empty_section() -> None:
    assert derive_dreaming_suggestions(store=FakeStore(), now=NOW) == []


def test_clean_connected_graph_yields_no_suggestions() -> None:
    # Distinct labels, every node connected via an edge, recent edge -> nothing.
    nodes = [
        _node("a", label="Alpha"),
        _node("b", label="Beta"),
    ]
    edges = [_edge("e1", "a", "b")]
    assert _derive(FakeStore(nodes, edges)) == []


# --------------------------------------------------------------------------- #
# duplicate
# --------------------------------------------------------------------------- #
def test_duplicate_signal_derivation() -> None:
    nodes = [
        _node("n2", label="API Contracts"),
        _node("n1", label="  api   contracts "),  # normalizes to the same key
        _node("n3", label="Something Else"),
    ]
    suggestions = _derive(FakeStore(nodes, edges=[_edge("e", "n1", "n2")]))
    dupes = [s for s in suggestions if s.type is DreamingSuggestionType.DUPLICATE]
    assert len(dupes) == 1
    dupe = dupes[0]
    assert dupe.node_ids == ["n1", "n2"]  # sorted by id
    assert dupe.confidence_hint == "high"
    assert dupe.origin == "dreaming"
    assert dupe.metadata["derived"] is True
    assert dupe.metadata["normalized_key"] == "api contracts"
    evidence = dupe.metadata["evidence"]
    assert evidence["node_ids"] == ["n1", "n2"]
    assert evidence["fields_used"] == ["label", "source_id"]
    assert "api contracts" in evidence["reason"]


def test_distinct_and_blank_labels_are_not_duplicates() -> None:
    nodes = [
        _node("n1", label="Unique One"),
        _node("n2", label="Unique Two"),
        _node("n3", label="   "),  # blank -> not a defensible duplicate signal
        _node("n4", label=""),
    ]
    suggestions = _derive(FakeStore(nodes))
    assert not [s for s in suggestions if s.type is DreamingSuggestionType.DUPLICATE]


# --------------------------------------------------------------------------- #
# orphan
# --------------------------------------------------------------------------- #
def test_orphaned_node_derivation() -> None:
    nodes = [
        _node("lonely"),  # no edge, no source, no parent -> orphan
        _node("linked"),
        _node("withsource", source_id="s1"),
        _node("withparent", parent_id="lonely"),
    ]
    edges = [_edge("e", "linked", "withparent")]
    suggestions = _derive(FakeStore(nodes, edges, sources=[_source("s1")]))
    orphans = [s for s in suggestions if s.type is DreamingSuggestionType.ORPHAN]
    assert [o.node_ids[0] for o in orphans] == ["lonely"]
    orphan = orphans[0]
    assert orphan.confidence_hint == "high"
    assert orphan.metadata["edge_count"] == 0
    assert orphan.metadata["evidence"]["fields_used"] == [
        "edges",
        "source_id",
        "parent_id",
    ]


def test_node_with_only_an_edge_is_not_orphaned() -> None:
    nodes = [_node("a"), _node("b")]
    edges = [_edge("e", "a", "b")]
    suggestions = _derive(FakeStore(nodes, edges))
    assert not [s for s in suggestions if s.type is DreamingSuggestionType.ORPHAN]


# --------------------------------------------------------------------------- #
# stale
# --------------------------------------------------------------------------- #
def test_stale_knowledge_link_derivation() -> None:
    nodes = [
        _node("a", updated_days_ago=10),  # updated long after the edge
        _node("b", updated_days_ago=10),
    ]
    edges = [_edge("old-link", "a", "b", created_days_ago=120)]
    suggestions = _derive(FakeStore(nodes, edges))
    stale = [s for s in suggestions if s.type is DreamingSuggestionType.STALE]
    assert len(stale) == 1
    link = stale[0]
    assert link.edge_ids == ["old-link"]
    assert sorted(link.node_ids) == ["a", "b"]
    assert link.confidence_hint == "low"
    assert link.metadata["edge_age_days"] == 120
    assert link.metadata["max_endpoint_drift_days"] == 110
    assert link.metadata["evidence"]["fields_used"] == [
        "edge.created_at",
        "node.updated_at",
    ]


def test_recent_edge_is_not_stale() -> None:
    nodes = [_node("a", updated_days_ago=1), _node("b", updated_days_ago=1)]
    edges = [_edge("fresh", "a", "b", created_days_ago=STALE_LINK_MIN_AGE_DAYS - 1)]
    suggestions = _derive(FakeStore(nodes, edges))
    assert not [s for s in suggestions if s.type is DreamingSuggestionType.STALE]


def test_old_edge_without_endpoint_drift_is_not_stale() -> None:
    # Edge old enough, but endpoints never changed after it was created.
    nodes = [_node("a", updated_days_ago=200), _node("b", updated_days_ago=200)]
    edges = [_edge("old", "a", "b", created_days_ago=200)]
    suggestions = _derive(FakeStore(nodes, edges))
    assert not [s for s in suggestions if s.type is DreamingSuggestionType.STALE]


def test_stale_drift_boundary_is_inclusive() -> None:
    # Drift exactly at the threshold qualifies (>=).
    edge_age = STALE_LINK_MIN_AGE_DAYS + 5
    node_age = edge_age - STALE_LINK_MIN_DRIFT_DAYS
    nodes = [
        _node("a", updated_days_ago=node_age),
        _node("b", updated_days_ago=node_age),
    ]
    edges = [_edge("e", "a", "b", created_days_ago=edge_age)]
    stale = [
        s
        for s in _derive(FakeStore(nodes, edges))
        if s.type is DreamingSuggestionType.STALE
    ]
    assert len(stale) == 1
    assert stale[0].metadata["max_endpoint_drift_days"] == STALE_LINK_MIN_DRIFT_DAYS


def test_stale_link_with_missing_endpoint_is_skipped() -> None:
    # Edge references a node that is not present -> incomplete data, skip.
    nodes = [_node("a", updated_days_ago=10)]
    edges = [_edge("dangling", "a", "ghost", created_days_ago=120)]
    suggestions = _derive(FakeStore(nodes, edges))
    assert not [s for s in suggestions if s.type is DreamingSuggestionType.STALE]


# --------------------------------------------------------------------------- #
# Contract / shape / guardrails
# --------------------------------------------------------------------------- #
def test_blocked_types_are_never_emitted() -> None:
    # A rich store that triggers every implemented rule must still never emit the
    # blocked/deferred types.
    nodes = [
        _node("d1", label="Dup"),
        _node("d2", label="dup"),
        _node("orphan"),
        _node("x", updated_days_ago=5),
        _node("y", updated_days_ago=5),
    ]
    edges = [_edge("old", "x", "y", created_days_ago=120)]
    suggestions = _derive(FakeStore(nodes, edges))
    emitted_types = {s.type for s in suggestions}
    assert DreamingSuggestionType.DUPLICATE in emitted_types
    assert DreamingSuggestionType.ORPHAN in emitted_types
    assert DreamingSuggestionType.STALE in emitted_types
    assert DreamingSuggestionType.UNRESOLVED_QUERY not in emitted_types
    assert "source_coverage_gap" not in {s.type.value for s in suggestions}


def test_every_suggestion_has_required_contract_fields() -> None:
    nodes = [
        _node("d1", label="Dup"),
        _node("d2", label="dup"),
        _node("orphan"),
        _node("x", updated_days_ago=5),
        _node("y", updated_days_ago=5),
    ]
    edges = [_edge("old", "x", "y", created_days_ago=120)]
    suggestions = _derive(FakeStore(nodes, edges))
    assert suggestions  # sanity: the rich store produces output
    for s in suggestions:
        assert s.id
        assert s.type in DreamingSuggestionType
        assert s.rationale  # title/summary text required by contract
        assert s.confidence_hint in {"high", "medium", "low"}
        assert s.origin == "dreaming"
        evidence = s.metadata["evidence"]
        # Stable evidence trail with every documented key present.
        for key in ("node_ids", "source_ids", "edge_ids", "reason", "derivation", "fields_used"):
            assert key in evidence
        assert evidence["reason"]
        assert evidence["derivation"]


def test_output_is_grouped_by_type_then_id() -> None:
    nodes = [
        _node("d1", label="Dup"),
        _node("d2", label="dup"),
        _node("zorphan"),
        _node("aorphan"),
        _node("x", updated_days_ago=5),
        _node("y", updated_days_ago=5),
    ]
    # Link the duplicate pair so they register only as a duplicate, not orphans.
    edges = [
        _edge("dlink", "d1", "d2"),
        _edge("old", "x", "y", created_days_ago=120),
    ]
    types = [s.type for s in _derive(FakeStore(nodes, edges))]
    # duplicate (rank 0) -> orphan (rank 1) -> stale (rank 2).
    assert types == sorted(
        types,
        key=lambda t: {
            DreamingSuggestionType.DUPLICATE: 0,
            DreamingSuggestionType.ORPHAN: 1,
            DreamingSuggestionType.STALE: 2,
        }[t],
    )
    orphan_ids = [
        s.node_ids[0]
        for s in _derive(FakeStore(nodes, edges))
        if s.type is DreamingSuggestionType.ORPHAN
    ]
    assert orphan_ids == ["aorphan", "zorphan"]  # sorted by id within a type


def test_derivation_is_repeatable_and_read_only() -> None:
    nodes = [_node("d1", label="Dup"), _node("d2", label="dup"), _node("orphan")]
    store = FakeStore(nodes)
    first = _derive(store)
    second = _derive(store)
    assert [s.model_dump() for s in first] == [s.model_dump() for s in second]
    # Fake store collections are unchanged (pure projection).
    assert len(store.get_nodes()) == len(nodes)
    assert store.get_edges() == []
