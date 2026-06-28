"""Phase 16C — deterministic, read-only Query Trails derivation.

Replaces the static Query Trails demo fixture as the Intelligence Report's
primary source with a real backend derivation. :func:`derive_query_trail_entries`
projects the existing store nodes/sources into read-only :class:`QueryTrailEntry`
rows using simple, explainable structural rules. Every emitted row carries
``metadata["derived"] = True`` and a stable ``metadata["evidence"]`` trail,
mirroring the Temporal Decay, Dreaming, and Provenance derivations
(:mod:`app.services.temporal_decay`, :mod:`app.services.dreaming`,
:mod:`app.services.provenance`).

Why this is backend-owned and not fixture/AI/persistence
--------------------------------------------------------
Query Trails are meant to surface useful follow-up paths and knowledge gaps. The
honest constraint in Phase 16C is that Hive|Mind has **no persisted query
history** — no query log, no stored search/console records. So this phase derives
*only* the Query Trail categories that existing structural store data can support
deterministically, and **defers** the categories that genuinely require persisted
query history. This keeps the surface honest: real derivation where data exists,
no manufactured query memory.

Guardrails honored here:

  * NO AI/LLM, NO scoring engine — only label/tag/source/timestamp comparisons.
  * NO randomness; all timestamps come from the underlying store records.
  * NO query persistence, query logging, storage tables, or new endpoints.
  * NO graph/source/store mutation and NO filesystem access — this is a pure,
    read-only projection over already-persisted store state.

Derived (supported by existing data) categories — Phase 16C MVP:

  * ``source_followup`` — a source that already produced linked knowledge nodes;
    suggests following up to explore the rest of that source's content.
  * ``knowledge_gap`` — a structural gap in the existing data: a node with no
    linked source (unsourced knowledge), or a registered source that produced no
    knowledge nodes yet (uncovered source). Emitted ``status = unresolved``.
  * ``related_query_cluster`` — two or more nodes sharing a tag; suggests they are
    related concepts worth exploring together.

Blocked / deferred (require real persisted query history) categories:

  * ``repeated_query`` — needs a persisted count of how often a query recurred.
    Without query history there is nothing to count, so ``occurrence_count`` stays
    ``1`` and no ``repeated_query`` record is ever manufactured.
  * ``unresolved_question`` — needs a persisted record that a user asked a question
    that surfaced nothing. This is the query-trail analogue of the still-blocked
    Dreaming ``unresolved_query`` type and is likewise not emitted here.

The ``last_executed_at`` field is **required** by the contract but these derived
trails were never "executed" as user queries. It therefore carries the underlying
store record's most recent activity timestamp (node/source ``updated_at``), and
the evidence trail states explicitly that it reflects underlying-data activity,
not a real query execution. ``occurrence_count`` stays ``1`` and ``pinned`` stays
``False`` because both require persisted user/query history that does not exist.
"""

from __future__ import annotations

from datetime import datetime

from app.models.hive_models import (
    HiveGraphNode,
    HiveSource,
    QueryTrailCategory,
    QueryTrailEntry,
    QueryTrailKind,
    QueryTrailStatus,
)

# Origin marker stamped in metadata so derived rows are unambiguous in the wire
# payload itself (the contract ``origin`` field stays "query_trail", advertising
# the read-only query-trail surface, exactly like the fixture path).
_DERIVATION_ORIGIN = "query_trail_derivation"

# Categories this phase can honestly derive from existing structural data.
_DERIVED_CATEGORIES = (
    QueryTrailCategory.SOURCE_FOLLOWUP,
    QueryTrailCategory.KNOWLEDGE_GAP,
    QueryTrailCategory.RELATED_QUERY_CLUSTER,
)

# Categories blocked until real persisted query history exists. Listed here so the
# guardrail is reviewable and tests can assert these are never emitted.
_BLOCKED_CATEGORIES = (
    QueryTrailCategory.REPEATED_QUERY,
    QueryTrailCategory.UNRESOLVED_QUESTION,
)

# Deterministic ordering: group by category (most actionable signal first), then
# by id, so tests and screenshots stay stable.
_CATEGORY_SORT_RANK = {
    QueryTrailCategory.SOURCE_FOLLOWUP: 0,
    QueryTrailCategory.KNOWLEDGE_GAP: 1,
    QueryTrailCategory.RELATED_QUERY_CLUSTER: 2,
}


def _slug(value: str) -> str:
    """Build a stable, id-safe slug from an arbitrary string key."""
    return "".join(ch if ch.isalnum() else "-" for ch in value).strip("-") or "x"


def _provenance_chain_id(node_id: str) -> str:
    """Id of the provenance chain the provenance derivation emits for a node.

    Mirrors :func:`app.services.provenance.derive_provenance_chains` (which keys
    chains as ``provenance-{node.id}``). This is an id-only cross-reference; it
    never resolves, copies, or mutates the linked chain.
    """
    return f"provenance-{node_id}"


def _evidence(
    *,
    node_ids: list[str],
    source_ids: list[str],
    reason: str,
    derivation: str,
    fields_used: list[str],
) -> dict[str, object]:
    """Build the stable ``metadata.evidence`` trail stamped on every entry."""
    return {
        "node_ids": node_ids,
        "source_ids": source_ids,
        "reason": reason,
        "derivation": derivation,
        "fields_used": fields_used,
        # Make the honesty constraint explicit in the payload itself: these
        # timestamps/counts come from existing records, not a real query log.
        "last_executed_at_basis": "underlying_record_activity",
        "history_available": False,
    }


def _metadata(
    *,
    category: QueryTrailCategory,
    evidence: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    meta: dict[str, object] = {
        "derived": True,
        "fixture": False,
        "derivation_origin": _DERIVATION_ORIGIN,
        "category": category.value,
        "evidence": evidence,
    }
    if extra:
        meta.update(extra)
    return meta


# --------------------------------------------------------------------------- #
# Rule: source_followup — a source that already produced linked knowledge nodes.
# --------------------------------------------------------------------------- #
def _derive_source_followups(
    sources: list[HiveSource],
    nodes_by_source: dict[str, list[HiveGraphNode]],
) -> list[QueryTrailEntry]:
    entries: list[QueryTrailEntry] = []
    for source in sources:
        members = nodes_by_source.get(source.id, [])
        if not members:
            continue  # uncovered sources are a knowledge_gap, not a follow-up
        members_sorted = sorted(members, key=lambda n: n.id)
        node_ids = [n.id for n in members_sorted]
        last_activity = max(
            (n.updated_at for n in members_sorted if n.updated_at is not None),
            default=source.updated_at,
        )
        reason = (
            f"Source '{source.name}' ({source.id}) already produced "
            f"{len(node_ids)} linked knowledge node(s); following up can explore "
            "the rest of its content."
        )
        entries.append(
            QueryTrailEntry(
                id=f"qt-source-followup-{_slug(source.id)}",
                query=f"more from {source.name}",
                kind=QueryTrailKind.SEARCH,
                category=QueryTrailCategory.SOURCE_FOLLOWUP,
                status=QueryTrailStatus.RESOLVED,
                result_node_ids=node_ids,
                result_source_ids=[source.id],
                provenance_chain_ids=[_provenance_chain_id(nid) for nid in node_ids],
                result_count=len(node_ids),
                occurrence_count=1,
                pinned=False,
                confidence_hint="high",
                last_executed_at=last_activity,
                metadata=_metadata(
                    category=QueryTrailCategory.SOURCE_FOLLOWUP,
                    evidence=_evidence(
                        node_ids=node_ids,
                        source_ids=[source.id],
                        reason=reason,
                        derivation=(
                            "Grouped graph nodes by source_id; emitted a "
                            "follow-up trail for each source with >= 1 linked node."
                        ),
                        fields_used=["node.source_id", "source.name", "node.updated_at"],
                    ),
                    extra={"linked_node_count": len(node_ids)},
                ),
            )
        )
    return entries


# --------------------------------------------------------------------------- #
# Rule: knowledge_gap — unsourced nodes and uncovered sources.
# --------------------------------------------------------------------------- #
def _derive_knowledge_gaps(
    nodes: list[HiveGraphNode],
    sources: list[HiveSource],
    nodes_by_source: dict[str, list[HiveGraphNode]],
) -> list[QueryTrailEntry]:
    entries: list[QueryTrailEntry] = []

    # Gap 1: nodes with no linked source — knowledge with no provenance to follow.
    for node in sorted(nodes, key=lambda n: n.id):
        if node.source_id:
            continue
        reason = (
            f"Node '{node.label}' ({node.id}) has no linked source_id, so its "
            "origin is an open knowledge gap."
        )
        entries.append(
            QueryTrailEntry(
                id=f"qt-knowledge-gap-node-{_slug(node.id)}",
                query=f"source for {node.label}",
                kind=QueryTrailKind.SEARCH,
                category=QueryTrailCategory.KNOWLEDGE_GAP,
                status=QueryTrailStatus.UNRESOLVED,
                result_node_ids=[node.id],
                result_source_ids=[],
                provenance_chain_ids=[_provenance_chain_id(node.id)],
                result_count=0,
                occurrence_count=1,
                pinned=False,
                confidence_hint="medium",
                last_executed_at=node.updated_at,
                metadata=_metadata(
                    category=QueryTrailCategory.KNOWLEDGE_GAP,
                    evidence=_evidence(
                        node_ids=[node.id],
                        source_ids=[],
                        reason=reason,
                        derivation=(
                            "Node carries no source_id; flagged as an unsourced "
                            "knowledge gap."
                        ),
                        fields_used=["node.source_id", "node.label", "node.updated_at"],
                    ),
                    extra={"gap_kind": "unsourced_node"},
                ),
            )
        )

    # Gap 2: registered sources that produced no knowledge nodes — uncovered input.
    for source in sorted(sources, key=lambda s: s.id):
        if nodes_by_source.get(source.id):
            continue
        reason = (
            f"Source '{source.name}' ({source.id}) is registered but produced no "
            "knowledge nodes yet, so its content is an open knowledge gap."
        )
        entries.append(
            QueryTrailEntry(
                id=f"qt-knowledge-gap-source-{_slug(source.id)}",
                query=f"extract knowledge from {source.name}",
                kind=QueryTrailKind.SEARCH,
                category=QueryTrailCategory.KNOWLEDGE_GAP,
                status=QueryTrailStatus.UNRESOLVED,
                result_node_ids=[],
                result_source_ids=[source.id],
                provenance_chain_ids=[],
                result_count=0,
                occurrence_count=1,
                pinned=False,
                confidence_hint="medium",
                last_executed_at=source.updated_at,
                metadata=_metadata(
                    category=QueryTrailCategory.KNOWLEDGE_GAP,
                    evidence=_evidence(
                        node_ids=[],
                        source_ids=[source.id],
                        reason=reason,
                        derivation=(
                            "Source id absent from every node's source_id; flagged "
                            "as an uncovered-source knowledge gap."
                        ),
                        fields_used=["source.id", "source.name", "node.source_id"],
                    ),
                    extra={"gap_kind": "uncovered_source"},
                ),
            )
        )

    return entries


# --------------------------------------------------------------------------- #
# Rule: related_query_cluster — two or more nodes sharing a tag.
# --------------------------------------------------------------------------- #
def _derive_related_clusters(nodes: list[HiveGraphNode]) -> list[QueryTrailEntry]:
    groups: dict[str, list[HiveGraphNode]] = {}
    for node in nodes:
        for tag in node.tags:
            key = tag.strip()
            if not key:
                continue
            groups.setdefault(key, []).append(node)

    entries: list[QueryTrailEntry] = []
    for tag, members in groups.items():
        if len(members) < 2:
            continue  # a single node is not a defensible "related" cluster
        members_sorted = sorted(members, key=lambda n: n.id)
        node_ids = [n.id for n in members_sorted]
        source_ids = sorted({n.source_id for n in members_sorted if n.source_id})
        last_activity = max(
            n.updated_at for n in members_sorted if n.updated_at is not None
        )
        reason = (
            f"{len(node_ids)} nodes share the tag '{tag}', forming a related "
            "concept cluster worth exploring together."
        )
        entries.append(
            QueryTrailEntry(
                id=f"qt-related-cluster-{_slug(tag)}",
                query=f"explore '{tag}' concepts",
                kind=QueryTrailKind.SEARCH,
                category=QueryTrailCategory.RELATED_QUERY_CLUSTER,
                status=QueryTrailStatus.RESOLVED,
                result_node_ids=node_ids,
                result_source_ids=source_ids,
                provenance_chain_ids=[_provenance_chain_id(nid) for nid in node_ids],
                result_count=len(node_ids),
                occurrence_count=1,
                pinned=False,
                confidence_hint="low",
                last_executed_at=last_activity,
                metadata=_metadata(
                    category=QueryTrailCategory.RELATED_QUERY_CLUSTER,
                    evidence=_evidence(
                        node_ids=node_ids,
                        source_ids=source_ids,
                        reason=reason,
                        derivation=(
                            "Grouped nodes by shared tag; emitted a related-cluster "
                            "trail for each tag shared by 2+ nodes."
                        ),
                        fields_used=["node.tags", "node.source_id", "node.updated_at"],
                    ),
                    extra={"shared_tag": tag, "cluster_size": len(node_ids)},
                ),
            )
        )
    return entries


def derive_query_trail_entries(*, store) -> list[QueryTrailEntry]:
    """Derive deterministic Query Trail entries from existing store state.

    Read-only: ``store`` is only queried, never mutated. Output is sorted by
    category rank, then ``id``, so tests and screenshots remain stable.

    Returns an empty list cleanly when nothing is derivable (e.g. an empty store),
    so callers can consume the section unconditionally. Only the Phase 16C MVP
    categories (``source_followup``, ``knowledge_gap``, ``related_query_cluster``)
    are derived; ``repeated_query`` and ``unresolved_question`` stay blocked until
    real persisted query history exists.
    """
    nodes = store.get_nodes()
    sources = store.get_sources()
    if not nodes and not sources:
        return []

    nodes_by_source: dict[str, list[HiveGraphNode]] = {}
    for node in nodes:
        if node.source_id:
            nodes_by_source.setdefault(node.source_id, []).append(node)

    entries = [
        *_derive_source_followups(sources, nodes_by_source),
        *_derive_knowledge_gaps(nodes, sources, nodes_by_source),
        *_derive_related_clusters(nodes),
    ]
    # Defensive guardrail: never emit a blocked, query-history-dependent category.
    entries = [e for e in entries if e.category not in _BLOCKED_CATEGORIES]
    entries.sort(key=lambda e: (_CATEGORY_SORT_RANK[e.category], e.id))
    return entries
