"""Phase 15C — deterministic provenance chain derivation tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    GraphNodeType,
    GraphRelationship,
    HiveGraphEdge,
    HiveGraphNode,
    HiveSource,
    ProvenanceChainStatus,
    RegistrySourceStatus,
    RegistrySourceType,
    SourceRecord,
    SourceStatus,
    SourceType,
    VaultFileMeta,
)
from app.services.provenance import derive_provenance_chains

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


class FakeStore:
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


class FakeRegistry:
    def __init__(self, sources=()):
        self._sources = list(sources)

    def list_sources(self):
        return list(self._sources)


def _node(
    node_id: str,
    *,
    source_id: str | None = None,
    label: str | None = None,
    file_meta: VaultFileMeta | None = None,
    metadata: dict | None = None,
) -> HiveGraphNode:
    return HiveGraphNode(
        id=node_id,
        label=label or node_id,
        type=GraphNodeType.NOTE,
        source_id=source_id,
        metadata=metadata or {},
        file_meta=file_meta,
        created_at=NOW,
        updated_at=NOW,
    )


def _edge(edge_id: str, src: str, tgt: str) -> HiveGraphEdge:
    return HiveGraphEdge(
        id=edge_id,
        source_node_id=src,
        target_node_id=tgt,
        relationship=GraphRelationship.LINKED_TO,
        created_at=NOW,
    )


def _source(source_id: str) -> HiveSource:
    return HiveSource(
        id=source_id,
        name="Store Source",
        type=SourceType.MARKDOWN,
        status=SourceStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def _registry_source(source_id: str) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        name="Registry Vault",
        type=RegistrySourceType.OBSIDIAN,
        root_path="/vault",
        status=RegistrySourceStatus.ACTIVE,
        last_imported_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        metadata={"origin": "obsidian"},
    )


def test_empty_store_returns_no_fabricated_chains() -> None:
    chains = derive_provenance_chains(store=FakeStore(), registry=FakeRegistry())
    assert chains == []


def test_derives_source_to_node_and_edge_chain() -> None:
    nodes = [_node("a", source_id="s1"), _node("b", source_id="s1")]
    store = FakeStore(nodes=nodes, edges=[_edge("e1", "a", "b")], sources=[_source("s1")])

    chains = derive_provenance_chains(store=store, registry=FakeRegistry())
    by_id = {chain.node_id: chain for chain in chains}
    chain = by_id["a"]

    assert chain.status is ProvenanceChainStatus.COMPLETE
    assert chain.source_id == "s1"
    assert chain.source_name == "Store Source"
    assert chain.stored_edge_ids == ["e1"]
    assert chain.linked_node_ids == ["b"]
    assert {link.kind.value for link in chain.links} >= {"source", "node", "edge"}
    assert chain.metadata["derived"] is True
    assert "matched source_id" in chain.metadata["evidence"]["reason"]


def test_registry_import_metadata_enriches_chain() -> None:
    file_meta = VaultFileMeta(
        vault_path="Notes/A.md",
        last_modified=NOW,
        origin="obsidian",
    )
    store = FakeStore(nodes=[_node("a", source_id="reg-1", file_meta=file_meta)])
    chains = derive_provenance_chains(
        store=store,
        registry=FakeRegistry([_registry_source("reg-1")]),
    )

    chain = chains[0]
    assert chain.source_name == "Registry Vault"
    assert chain.source_type is RegistrySourceType.OBSIDIAN
    assert chain.origin_path == "Notes/A.md"
    assert chain.last_imported_at == NOW
    assert "import" in {link.kind.value for link in chain.links}
    assert "found Obsidian/import file metadata" in chain.metadata["evidence"]["reason"]


def test_missing_source_metadata_is_honest_partial_chain() -> None:
    chains = derive_provenance_chains(
        store=FakeStore(nodes=[_node("a", source_id="missing")]),
        registry=FakeRegistry(),
    )
    chain = chains[0]
    assert chain.status is ProvenanceChainStatus.PARTIAL
    assert chain.source_id == "missing"
    assert chain.source_name is None
    assert "source metadata unavailable" in chain.metadata["evidence"]["reason"]


def test_missing_timestamps_do_not_crash() -> None:
    node = HiveGraphNode.model_construct(
        id="a",
        label="A",
        type=GraphNodeType.NOTE,
        source_id=None,
        parent_id=None,
        metadata={},
        file_meta=None,
        created_at=None,
        updated_at=None,
    )
    chains = derive_provenance_chains(store=FakeStore(nodes=[node]), registry=FakeRegistry())
    assert chains[0].created_at is None
    assert chains[0].updated_at is None
    assert chains[0].status is ProvenanceChainStatus.UNKNOWN


def test_derived_graph_builder_edges_are_identified() -> None:
    nodes = [
        _node("a", label="A", metadata={"wiki_links": ["B"]}),
        _node("b", label="B"),
    ]
    chains = derive_provenance_chains(store=FakeStore(nodes=nodes), registry=FakeRegistry())
    by_id = {chain.node_id: chain for chain in chains}
    assert by_id["a"].derived_edge_ids
    assert by_id["a"].stored_edge_ids == []
    assert "relationship inferred" in by_id["a"].metadata["evidence"]["reason"]


def test_ordering_is_deterministic_by_status_then_node_id() -> None:
    store = FakeStore(
        nodes=[
            _node("z", source_id="s1"),
            _node("a"),
            _node("m", source_id="missing"),
        ],
        edges=[_edge("e1", "z", "m")],
        sources=[_source("s1")],
    )
    order = [chain.node_id for chain in derive_provenance_chains(store=store)]
    assert order == ["a", "m", "z"]


def test_derivation_is_repeatable_and_read_only() -> None:
    nodes = [_node("a", source_id="s1"), _node("b")]
    edges = [_edge("e1", "a", "b")]
    sources = [_source("s1")]
    store = FakeStore(nodes=nodes, edges=edges, sources=sources)

    first = derive_provenance_chains(store=store, registry=FakeRegistry())
    second = derive_provenance_chains(store=store, registry=FakeRegistry())

    assert [chain.model_dump() for chain in first] == [
        chain.model_dump() for chain in second
    ]
    assert store.get_nodes() == nodes
    assert store.get_edges() == edges
    assert store.get_sources() == sources
