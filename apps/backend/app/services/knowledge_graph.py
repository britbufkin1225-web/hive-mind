"""Phase 8A — knowledge graph builder.

Derives a graph-shaped projection (nodes + edges + summary) from the existing
records in the ``HiveStore``. This is the backend foundation a future frontend
graph visualization will consume; nothing here scans a filesystem, runs an
import, or invents speculative/AI ("dreaming") connections.

The builder is pure and deterministic for a given store state:

  * **Nodes** are the stored graph nodes, de-duplicated by stable id (the store
    is already keyed by id; the builder guards against duplicates defensively
    and preserves insertion order).
  * **Edges** are the union of (a) edges already persisted in the store and
    (b) link edges *derived* from imported Obsidian notes whose captured
    ``wiki_links`` resolve to another node in the graph. Derived edges carry a
    deterministic id so repeated builds produce identical output, and are never
    duplicated against an existing stored edge with the same
    ``(source, target, relationship)``.
  * If no edges exist or resolve, ``edges`` is an empty list and the response
    shape is unchanged.

Derived edges are not written back to the store — the builder is a read-only
projection, so calling it repeatedly never accumulates state.
"""

from __future__ import annotations

import hashlib

from app.models.hive_models import (
    GraphRelationship,
    HiveGraphEdge,
    HiveGraphNode,
    KnowledgeGraphResponse,
    KnowledgeGraphSummary,
)
from app.store.store import store as default_store

# Marker placed on derived (link-resolved) edges so consumers can distinguish
# them from edges that were explicitly persisted in the store.
_DERIVED_ORIGIN = "knowledge_graph_builder"


def _link_keys_for(node: HiveGraphNode) -> list[str]:
    """Return the lowercased keys an inbound wiki link could use to address ``node``.

    Obsidian ``[[wiki links]]`` reference a note by its name or vault-relative
    path (without the ``.md`` extension). We index each node under several
    candidate keys so a link such as ``[[Project Alpha]]`` or ``[[Notes/Daily]]``
    resolves to the right node regardless of which form the author used.
    """
    keys: list[str] = []
    meta = node.file_meta
    if meta is not None:
        if meta.vault_path:
            vp = meta.vault_path
            keys.append(vp)
            if vp.lower().endswith(".md"):
                keys.append(vp[: -len(".md")])
        if meta.file_name:
            fn = meta.file_name
            keys.append(fn)
            if fn.lower().endswith(".md"):
                keys.append(fn[: -len(".md")])
    if node.label:
        keys.append(node.label)
    # Order-preserving, case-insensitive de-dupe.
    seen: set[str] = set()
    out: list[str] = []
    for key in keys:
        norm = key.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def _derived_edge_id(source_id: str, target_id: str, relationship: str) -> str:
    digest = hashlib.sha1(
        f"{source_id}->{target_id}:{relationship}".encode("utf-8")
    ).hexdigest()[:12]
    return f"kg-edge-{digest}"


def build_knowledge_graph(*, store=default_store) -> KnowledgeGraphResponse:
    """Build a deterministic :class:`KnowledgeGraphResponse` from ``store`` state."""
    # Nodes: de-dupe defensively by id, preserving order.
    nodes: list[HiveGraphNode] = []
    seen_node_ids: set[str] = set()
    for node in store.get_nodes():
        if node.id in seen_node_ids:
            continue
        seen_node_ids.add(node.id)
        nodes.append(node)

    # Build a resolver from link key -> node id. When two nodes share a key the
    # first one wins, keeping resolution deterministic.
    resolver: dict[str, str] = {}
    for node in nodes:
        for key in _link_keys_for(node):
            resolver.setdefault(key, node.id)

    edges: list[HiveGraphEdge] = []
    # (source, target, relationship) triples already represented, so derived
    # edges never duplicate a stored edge or each other.
    seen_pairs: set[tuple[str, str, str]] = set()

    # 1) Existing persisted edges (only those whose endpoints are present).
    for edge in store.get_edges():
        if edge.source_node_id not in seen_node_ids:
            continue
        if edge.target_node_id not in seen_node_ids:
            continue
        edges.append(edge)
        seen_pairs.add(
            (edge.source_node_id, edge.target_node_id, edge.relationship.value)
        )

    # 2) Edges derived from captured Obsidian wiki links.
    relationship = GraphRelationship.REFERENCES
    for node in nodes:
        wiki_links = node.metadata.get("wiki_links")
        if not isinstance(wiki_links, list):
            continue
        for raw_target in wiki_links:
            if not isinstance(raw_target, str):
                continue
            target_id = resolver.get(raw_target.strip().lower())
            if target_id is None or target_id == node.id:
                continue  # unresolved link or self-link: skip
            pair = (node.id, target_id, relationship.value)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            edges.append(
                HiveGraphEdge(
                    id=_derived_edge_id(node.id, target_id, relationship.value),
                    source_node_id=node.id,
                    target_node_id=target_id,
                    relationship=relationship,
                    metadata={"origin": _DERIVED_ORIGIN, "link": raw_target},
                    created_at=node.updated_at,
                )
            )

    return KnowledgeGraphResponse(
        nodes=nodes,
        edges=edges,
        summary=KnowledgeGraphSummary(node_count=len(nodes), edge_count=len(edges)),
    )
