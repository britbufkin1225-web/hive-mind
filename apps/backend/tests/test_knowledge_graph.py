"""Phase 8A — knowledge graph API foundation tests.

Covers the deterministic graph builder (``app/services/knowledge_graph.py``) and
the ``GET /api/knowledge-graph`` endpoint. The builder is exercised against
isolated throwaway stores so seed data never affects assertions; the endpoint
test only asserts the stable response *shape*.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.hive_models import (
    GraphNodeType,
    GraphRelationship,
    HiveGraphEdge,
    HiveGraphNode,
    VaultFileMeta,
)
from app.services.knowledge_graph import build_knowledge_graph
from app.services.obsidian_import import import_vault
from app.store.registry import SourceRegistry
from app.store.store import HiveStore

client = TestClient(app)

_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #
def empty_store(tmp_path) -> HiveStore:
    """A store seeded with explicitly empty collections (no mock seed data)."""
    store = HiveStore(persistence_path=tmp_path / "store.json")
    store._nodes = {}
    store._edges = {}
    store._sources = {}
    return store


def fresh_store(tmp_path) -> HiveStore:
    return HiveStore(persistence_path=tmp_path / "store.json")


def fresh_registry(tmp_path) -> SourceRegistry:
    return SourceRegistry(persistence_path=tmp_path / "registry.json")


def _note_node(node_id: str, label: str, *, wiki_links=None, vault_path=None) -> HiveGraphNode:
    return HiveGraphNode(
        id=node_id,
        label=label,
        type=GraphNodeType.NOTE,
        metadata={"origin": "obsidian", "wiki_links": wiki_links or [], "markdown_links": []},
        created_at=_NOW,
        updated_at=_NOW,
        file_meta=VaultFileMeta(
            vault_path=vault_path or f"{label}.md",
            file_name=f"{label}.md",
            extension=".md",
            origin="obsidian",
        ),
    )


def build_vault(root) -> None:
    """Two interlinked notes plus one unlinked note."""
    (root / "Welcome.md").write_text(
        "# Welcome\n\nJump to [[Project Alpha]].\n", encoding="utf-8"
    )
    (root / "Project Alpha.md").write_text(
        "# Project Alpha\n\nBack to [[Welcome]].\n", encoding="utf-8"
    )
    (root / "Loner.md").write_text("# Loner\n\nNo links here.\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Empty graph
# --------------------------------------------------------------------------- #
def test_empty_graph_returns_stable_shape(tmp_path) -> None:
    graph = build_knowledge_graph(store=empty_store(tmp_path))
    assert graph.nodes == []
    assert graph.edges == []
    assert graph.summary.node_count == 0
    assert graph.summary.edge_count == 0


# --------------------------------------------------------------------------- #
# Populated graph from imported records
# --------------------------------------------------------------------------- #
def test_imported_records_become_nodes(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    build_vault(root)
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    # Start from an empty store so only imported nodes are present.
    store._nodes = {}
    store._edges = {}
    import_vault(str(root), "Vault", store=store, registry=registry)

    graph = build_knowledge_graph(store=store)
    labels = sorted(n.label for n in graph.nodes)
    assert labels == ["Loner", "Project Alpha", "Welcome"]
    assert graph.summary.node_count == 3


def test_summary_counts_match_collections(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {
        n.id: n
        for n in [
            _note_node("n-a", "Welcome", wiki_links=["Project Alpha"]),
            _note_node("n-b", "Project Alpha"),
        ]
    }
    graph = build_knowledge_graph(store=store)
    assert graph.summary.node_count == len(graph.nodes) == 2
    assert graph.summary.edge_count == len(graph.edges) == 1


# --------------------------------------------------------------------------- #
# Edge derivation from links
# --------------------------------------------------------------------------- #
def test_wiki_links_become_edges(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {
        n.id: n
        for n in [
            _note_node("n-a", "Welcome", wiki_links=["Project Alpha"]),
            _note_node("n-b", "Project Alpha", wiki_links=["Welcome"]),
        ]
    }
    graph = build_knowledge_graph(store=store)
    pairs = {(e.source_node_id, e.target_node_id) for e in graph.edges}
    assert pairs == {("n-a", "n-b"), ("n-b", "n-a")}
    for edge in graph.edges:
        assert edge.relationship == GraphRelationship.REFERENCES
        assert edge.metadata["origin"] == "knowledge_graph_builder"


def test_links_resolve_by_vault_relative_path(tmp_path) -> None:
    store = empty_store(tmp_path)
    daily = _note_node("n-daily", "Daily", vault_path="Notes/Daily.md")
    welcome = _note_node("n-welcome", "Welcome", wiki_links=["Notes/Daily"])
    store._nodes = {daily.id: daily, welcome.id: welcome}
    graph = build_knowledge_graph(store=store)
    assert ("n-welcome", "n-daily") in {
        (e.source_node_id, e.target_node_id) for e in graph.edges
    }


def test_unresolved_links_are_ignored(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {"n-a": _note_node("n-a", "Welcome", wiki_links=["Does Not Exist"])}
    graph = build_knowledge_graph(store=store)
    assert graph.edges == []
    assert graph.summary.edge_count == 0


def test_self_links_are_ignored(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {"n-a": _note_node("n-a", "Welcome", wiki_links=["Welcome"])}
    graph = build_knowledge_graph(store=store)
    assert graph.edges == []


def test_nodes_without_links_yield_no_edges(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {
        "n-a": _note_node("n-a", "Loner"),
        "n-b": _note_node("n-b", "Other"),
    }
    graph = build_knowledge_graph(store=store)
    assert graph.nodes and graph.edges == []


# --------------------------------------------------------------------------- #
# Existing stored edges + determinism + dedupe
# --------------------------------------------------------------------------- #
def test_existing_stored_edges_are_included(tmp_path) -> None:
    store = empty_store(tmp_path)
    a = _note_node("n-a", "A")
    b = _note_node("n-b", "B")
    store._nodes = {a.id: a, b.id: b}
    store._edges = {
        "edge-1": HiveGraphEdge(
            id="edge-1",
            source_node_id="n-a",
            target_node_id="n-b",
            relationship=GraphRelationship.LINKED_TO,
            created_at=_NOW,
        )
    }
    graph = build_knowledge_graph(store=store)
    assert any(e.id == "edge-1" for e in graph.edges)


def test_stored_edges_with_missing_endpoints_are_dropped(tmp_path) -> None:
    store = empty_store(tmp_path)
    a = _note_node("n-a", "A")
    store._nodes = {a.id: a}
    store._edges = {
        "edge-orphan": HiveGraphEdge(
            id="edge-orphan",
            source_node_id="n-a",
            target_node_id="n-missing",
            relationship=GraphRelationship.LINKED_TO,
            created_at=_NOW,
        )
    }
    graph = build_knowledge_graph(store=store)
    assert graph.edges == []


def test_derived_edges_do_not_duplicate_stored_edges(tmp_path) -> None:
    store = empty_store(tmp_path)
    a = _note_node("n-a", "Welcome", wiki_links=["Project Alpha"])
    b = _note_node("n-b", "Project Alpha")
    store._nodes = {a.id: a, b.id: b}
    # A pre-existing REFERENCES edge for the same pair the link would derive.
    store._edges = {
        "edge-pre": HiveGraphEdge(
            id="edge-pre",
            source_node_id="n-a",
            target_node_id="n-b",
            relationship=GraphRelationship.REFERENCES,
            created_at=_NOW,
        )
    }
    graph = build_knowledge_graph(store=store)
    edges_for_pair = [
        e for e in graph.edges if e.source_node_id == "n-a" and e.target_node_id == "n-b"
    ]
    assert len(edges_for_pair) == 1
    assert edges_for_pair[0].id == "edge-pre"


def test_build_is_deterministic_and_non_mutating(tmp_path) -> None:
    store = empty_store(tmp_path)
    store._nodes = {
        n.id: n
        for n in [
            _note_node("n-a", "Welcome", wiki_links=["Project Alpha"]),
            _note_node("n-b", "Project Alpha", wiki_links=["Welcome"]),
        ]
    }
    first = build_knowledge_graph(store=store)
    second = build_knowledge_graph(store=store)
    assert [e.id for e in first.edges] == [e.id for e in second.edges]
    # Repeated builds never write derived edges back into the store.
    assert store.get_edges() == []


def test_repeated_imports_do_not_duplicate_nodes(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    build_vault(root)
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    store._nodes = {}
    store._edges = {}
    import_vault(str(root), "Vault", store=store, registry=registry)
    import_vault(str(root), "Vault", store=store, registry=registry)

    graph = build_knowledge_graph(store=store)
    ids = [n.id for n in graph.nodes]
    assert len(ids) == len(set(ids)) == 3


# --------------------------------------------------------------------------- #
# API endpoint (shape only — runs against the shared app store)
# --------------------------------------------------------------------------- #
def test_api_knowledge_graph_returns_stable_shape() -> None:
    response = client.get("/api/knowledge-graph")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"nodes", "edges", "summary"}
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert data["summary"]["node_count"] == len(data["nodes"])
    assert data["summary"]["edge_count"] == len(data["edges"])
