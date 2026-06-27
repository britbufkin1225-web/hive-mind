"""Phase 15C — deterministic provenance chain derivation.

Builds read-only :class:`ProvenanceChain` rows from the existing graph/source
state. This is a pure projection: it reads store nodes, store sources, source
registry records, and graph-builder edge output, but never persists or mutates
anything.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.hive_models import (
    HiveGraphEdge,
    HiveGraphNode,
    HiveSource,
    ProvenanceChain,
    ProvenanceChainStatus,
    ProvenanceLink,
    ProvenanceLinkKind,
    RegistrySourceType,
    SourceRecord,
    SourceType,
)
from app.services.knowledge_graph import build_knowledge_graph
from app.store.registry import registry as default_registry

_DERIVATION_ORIGIN = "provenance_derivation"
_GRAPH_BUILDER_ORIGIN = "knowledge_graph_builder"

_SOURCE_TYPE_MAP = {
    SourceType.MARKDOWN: RegistrySourceType.LOCAL_FILES,
    SourceType.TEXT: RegistrySourceType.LOCAL_FILES,
    SourceType.JSON: RegistrySourceType.API,
    SourceType.FOLDER: RegistrySourceType.LOCAL_FILES,
    SourceType.UNKNOWN: None,
}


def _registry_sources(registry) -> dict[str, SourceRecord]:
    if registry is None or not hasattr(registry, "list_sources"):
        return {}
    return {source.id: source for source in registry.list_sources()}


def _origin_path(
    node: HiveGraphNode,
    registry_source: SourceRecord | None,
    store_source: HiveSource | None,
) -> str | None:
    if node.file_meta is not None:
        return (
            node.file_meta.vault_path
            or node.file_meta.file_path
            or node.file_meta.file_name
        )
    for key in ("origin_path", "source_path", "vault_path", "file_path"):
        value = node.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if registry_source is not None:
        return registry_source.root_path
    if store_source is not None:
        return store_source.path or store_source.vault_path
    return None


def _source_type(
    node: HiveGraphNode,
    registry_source: SourceRecord | None,
    store_source: HiveSource | None,
) -> RegistrySourceType | None:
    if registry_source is not None:
        return registry_source.type
    if store_source is None:
        return None
    origin = store_source.origin
    if origin is None and node.file_meta is not None:
        origin = node.file_meta.origin
    if origin == RegistrySourceType.OBSIDIAN.value:
        return RegistrySourceType.OBSIDIAN
    return _SOURCE_TYPE_MAP.get(store_source.type)


def _last_imported_at(
    node: HiveGraphNode,
    registry_source: SourceRecord | None,
    store_source: HiveSource | None,
) -> datetime | None:
    if registry_source is not None and registry_source.last_imported_at is not None:
        return registry_source.last_imported_at
    if node.file_meta is not None and node.file_meta.last_modified is not None:
        return node.file_meta.last_modified
    if store_source is not None:
        return store_source.updated_at
    return None


def _edge_origin(edge: HiveGraphEdge) -> str:
    origin = edge.metadata.get("origin")
    if isinstance(origin, str) and origin:
        return origin
    return "store"


def _link_metadata(reason: str, fields_used: list[str]) -> dict[str, object]:
    return {
        "derived": True,
        "reason": reason,
        "fields_used": fields_used,
        "derivation_origin": _DERIVATION_ORIGIN,
    }


def _edge_links(edges: list[HiveGraphEdge]) -> list[ProvenanceLink]:
    return [
        ProvenanceLink(
            kind=ProvenanceLinkKind.EDGE,
            ref_id=edge.id,
            label=f"{edge.source_node_id} {edge.relationship.value} {edge.target_node_id}",
            origin=_edge_origin(edge),
            metadata=_link_metadata(
                "found graph edge relationship",
                ["edge.id", "edge.source_node_id", "edge.target_node_id"],
            ),
        )
        for edge in edges
    ]


def _chain_status(
    *,
    node: HiveGraphNode,
    source_found: bool,
    incident_edges: list[HiveGraphEdge],
) -> ProvenanceChainStatus:
    if source_found and incident_edges:
        return ProvenanceChainStatus.COMPLETE
    if source_found or node.source_id or incident_edges or node.parent_id or node.file_meta:
        return ProvenanceChainStatus.PARTIAL
    return ProvenanceChainStatus.UNKNOWN


def _evidence(
    *,
    node: HiveGraphNode,
    registry_source: SourceRecord | None,
    store_source: HiveSource | None,
    incident_edges: list[HiveGraphEdge],
) -> dict[str, Any]:
    source_found = registry_source is not None or store_source is not None
    reasons: list[str] = []
    fields_used = ["node.id", "node.label", "node.source_id"]

    if registry_source is not None:
        reasons.append("matched source registry record")
        fields_used.extend(["source_registry.id", "source_registry.last_imported_at"])
    elif store_source is not None:
        reasons.append("matched source_id from graph node metadata")
        fields_used.extend(["store_source.id", "store_source.updated_at"])
    elif node.source_id:
        reasons.append("source metadata unavailable")
    else:
        reasons.append("node has no linked source")

    if node.file_meta is not None:
        reasons.append("found Obsidian/import file metadata")
        fields_used.extend(["node.file_meta.vault_path", "node.file_meta.last_modified"])

    if incident_edges:
        reasons.append("found graph edge relationship")
        fields_used.extend(["edge.id", "edge.relationship"])
        if any(edge.metadata.get("origin") == _GRAPH_BUILDER_ORIGIN for edge in incident_edges):
            reasons.append("relationship inferred from existing import link metadata")

    return {
        "node_ids": sorted(
            {
                node.id,
                *[
                    edge.target_node_id if edge.source_node_id == node.id else edge.source_node_id
                    for edge in incident_edges
                ],
            }
        ),
        "source_ids": [node.source_id] if node.source_id else [],
        "edge_ids": [edge.id for edge in incident_edges],
        "reason": "; ".join(reasons),
        "derivation": (
            "Read existing nodes, source registry/store records, and graph edges; "
            "emitted no chain when no nodes exist."
        ),
        "fields_used": list(dict.fromkeys(fields_used)),
        "source_found": source_found,
    }


def _chain_for_node(
    *,
    node: HiveGraphNode,
    registry_source: SourceRecord | None,
    store_source: HiveSource | None,
    incident_edges: list[HiveGraphEdge],
) -> ProvenanceChain:
    source_found = registry_source is not None or store_source is not None
    source_name = (
        registry_source.name
        if registry_source is not None
        else store_source.name if store_source is not None else None
    )
    edge_ids = [edge.id for edge in incident_edges]
    derived_edge_ids = [
        edge.id for edge in incident_edges if edge.metadata.get("origin") == _GRAPH_BUILDER_ORIGIN
    ]
    stored_edge_ids = [edge.id for edge in incident_edges if edge.id not in derived_edge_ids]
    linked_node_ids = sorted(
        {
            edge.target_node_id if edge.source_node_id == node.id else edge.source_node_id
            for edge in incident_edges
        }
    )

    links: list[ProvenanceLink] = []
    if node.source_id:
        links.append(
            ProvenanceLink(
                kind=ProvenanceLinkKind.SOURCE,
                ref_id=node.source_id,
                label=source_name,
                origin="source_registry" if registry_source is not None else "store",
                metadata=_link_metadata(
                    (
                        "matched source registry record"
                        if registry_source is not None
                        else "matched source_id from graph node metadata"
                        if store_source is not None
                        else "source metadata unavailable"
                    ),
                    ["node.source_id"],
                ),
            )
        )
    if registry_source is not None and registry_source.last_imported_at is not None:
        links.append(
            ProvenanceLink(
                kind=ProvenanceLinkKind.IMPORT,
                ref_id=f"{registry_source.id}:last_import",
                label="Last import",
                origin="source_registry",
                metadata=_link_metadata(
                    "found Obsidian import metadata"
                    if registry_source.type is RegistrySourceType.OBSIDIAN
                    else "found source import metadata",
                    ["source_registry.last_imported_at"],
                ),
            )
        )
    links.append(
        ProvenanceLink(
            kind=ProvenanceLinkKind.NODE,
            ref_id=node.id,
            label=node.label,
            origin="graph",
            metadata=_link_metadata(
                "existing knowledge graph node",
                ["node.id", "node.label"],
            ),
        )
    )
    links.extend(_edge_links(incident_edges))

    status = _chain_status(
        node=node,
        source_found=source_found,
        incident_edges=incident_edges,
    )
    evidence = _evidence(
        node=node,
        registry_source=registry_source,
        store_source=store_source,
        incident_edges=incident_edges,
    )

    return ProvenanceChain(
        node_id=node.id,
        id=f"provenance-{node.id}",
        title=f"{node.label} lineage",
        summary=(
            f"Derived read-only provenance for '{node.label}' from existing "
            f"node, source, and {len(edge_ids)} graph edge record(s)."
        ),
        status=status,
        read_only=True,
        source_id=node.source_id,
        source_name=source_name,
        source_type=_source_type(node, registry_source, store_source),
        origin_path=_origin_path(node, registry_source, store_source),
        links=links,
        linked_node_ids=linked_node_ids,
        derived_edge_ids=derived_edge_ids,
        stored_edge_ids=stored_edge_ids,
        created_at=node.created_at,
        updated_at=node.updated_at,
        last_imported_at=_last_imported_at(node, registry_source, store_source),
        metadata={
            "derived": True,
            "derivation_origin": _DERIVATION_ORIGIN,
            "fixture": False,
            "evidence": evidence,
        },
    )


def derive_provenance_chains(
    *,
    store,
    registry=default_registry,
) -> list[ProvenanceChain]:
    """Derive provenance chains from existing graph/source/import data.

    Returns an empty list for an empty graph. Output is sorted by status
    attention rank, then node id, so tests and screenshots remain stable.
    """
    nodes = sorted(store.get_nodes(), key=lambda node: node.id)
    if not nodes:
        return []

    registry_sources = _registry_sources(registry)
    store_sources = {source.id: source for source in store.get_sources()}
    graph = build_knowledge_graph(store=store)
    incident_by_node: dict[str, list[HiveGraphEdge]] = {node.id: [] for node in nodes}
    for edge in graph.edges:
        if edge.source_node_id in incident_by_node:
            incident_by_node[edge.source_node_id].append(edge)
        if edge.target_node_id in incident_by_node:
            incident_by_node[edge.target_node_id].append(edge)

    status_rank = {
        ProvenanceChainStatus.UNKNOWN: 0,
        ProvenanceChainStatus.PARTIAL: 1,
        ProvenanceChainStatus.COMPLETE: 2,
    }
    chains = [
        _chain_for_node(
            node=node,
            registry_source=registry_sources.get(node.source_id) if node.source_id else None,
            store_source=store_sources.get(node.source_id) if node.source_id else None,
            incident_edges=sorted(incident_by_node[node.id], key=lambda edge: edge.id),
        )
        for node in nodes
    ]
    chains.sort(key=lambda chain: (status_rank[chain.status], chain.node_id))
    return chains
