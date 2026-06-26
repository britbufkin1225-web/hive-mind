"""Phase 14C — deterministic, read-only Dreaming suggestion derivation.

Replaces the static Dreaming demo fixture with a real backend derivation.
:func:`derive_dreaming_suggestions` projects the existing store nodes/edges/
sources into read-only :class:`DreamingSuggestion` rows using simple, explainable
rules. Every emitted row carries ``metadata["derived"] = True`` and a stable
``metadata["evidence"]`` trail, mirroring the Temporal Decay derivation
(:mod:`app.services.temporal_decay`).

Guardrails honored here:

  * NO AI/LLM, NO scoring engine — only label/edge/timestamp comparisons.
  * NO randomness; ``now`` is injectable so the stale-link rule is fully
    deterministic in tests.
  * NO graph/source/store mutation and NO filesystem access — this is a pure,
    read-only projection over already-persisted store state.

Implemented suggestion types (Phase 14C):

  * ``duplicate`` — nodes that share a normalized label.
  * ``orphan`` — nodes with no edges, no source link, and no parent.
  * ``stale`` — old edges whose endpoint nodes changed after the link was
    asserted (a lightweight "review this relationship" hint, intentionally not a
    re-implementation of per-node Temporal Decay).

Deliberately NOT implemented:

  * ``source_coverage_gap`` — deferred/blocked. Phase 14B pinned the
    ``DreamingSuggestionType`` contract and intentionally omits this value; it
    awaits a future contract-expansion phase and is not re-added here.
  * ``unresolved_query`` — blocked until query history is persisted. No
    derivation produces it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    DreamingSuggestion,
    DreamingSuggestionType,
    HiveGraphEdge,
    HiveGraphNode,
)

# --------------------------------------------------------------------------- #
# Explainable thresholds (kept as module constants so the rules are trivially
# reviewable and stable). The stale-link rule is intentionally conservative.
# --------------------------------------------------------------------------- #
# An edge must be at least this old before it is even considered for staleness.
STALE_LINK_MIN_AGE_DAYS = 90
# ...and an endpoint node must have changed at least this long *after* the edge
# was created for the relationship to look like it predates current knowledge.
STALE_LINK_MIN_DRIFT_DAYS = 30

# Deterministic ordering: group by type (most-confident signal first), then id.
_TYPE_SORT_RANK = {
    DreamingSuggestionType.DUPLICATE: 0,
    DreamingSuggestionType.ORPHAN: 1,
    DreamingSuggestionType.STALE: 2,
}


def _normalize_label(label: str) -> str:
    """Collapse whitespace and casefold a label into a stable comparison key."""
    return " ".join(label.split()).casefold()


def _slug(value: str) -> str:
    """Build a stable, id-safe slug from an arbitrary string key."""
    return "".join(ch if ch.isalnum() else "-" for ch in value).strip("-") or "x"


def _evidence(
    *,
    node_ids: list[str],
    edge_ids: list[str],
    source_ids: list[str],
    reason: str,
    derivation: str,
    fields_used: list[str],
) -> dict[str, object]:
    """Build the stable ``metadata.evidence`` trail stamped on every suggestion."""
    return {
        "node_ids": node_ids,
        "source_ids": source_ids,
        "edge_ids": edge_ids,
        "reason": reason,
        "derivation": derivation,
        "fields_used": fields_used,
    }


# --------------------------------------------------------------------------- #
# Rule: duplicate — nodes sharing a normalized label.
# --------------------------------------------------------------------------- #
def _derive_duplicates(nodes: list[HiveGraphNode]) -> list[DreamingSuggestion]:
    groups: dict[str, list[HiveGraphNode]] = {}
    for node in nodes:
        key = _normalize_label(node.label)
        if not key:
            continue  # blank labels are not a defensible duplicate signal
        groups.setdefault(key, []).append(node)

    suggestions: list[DreamingSuggestion] = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        members_sorted = sorted(members, key=lambda n: n.id)
        node_ids = [n.id for n in members_sorted]
        source_ids = sorted({n.source_id for n in members_sorted if n.source_id})
        reason = (
            f"{len(node_ids)} nodes share the normalized label '{key}'."
        )
        suggestions.append(
            DreamingSuggestion(
                id=f"dream-duplicate-{_slug(key)}",
                type=DreamingSuggestionType.DUPLICATE,
                rationale=(
                    "Possible duplicate concept: nodes "
                    f"{', '.join(node_ids)} normalize to the same label "
                    f"'{key}'. Review and merge if they describe the same thing."
                ),
                node_ids=node_ids,
                edge_ids=[],
                confidence_hint="high",
                metadata={
                    "derived": True,
                    "evidence": _evidence(
                        node_ids=node_ids,
                        edge_ids=[],
                        source_ids=source_ids,
                        reason=reason,
                        derivation=(
                            "Grouped nodes by whitespace-collapsed, casefolded "
                            "label; emitted groups of 2+."
                        ),
                        fields_used=["label", "source_id"],
                    ),
                    "normalized_key": key,
                },
                # Deterministic: newest member update, not wall-clock `now`.
                created_at=max(n.updated_at for n in members_sorted),
            )
        )
    return suggestions


# --------------------------------------------------------------------------- #
# Rule: orphan — node with no edges, no source link, and no parent.
# --------------------------------------------------------------------------- #
def _derive_orphans(
    nodes: list[HiveGraphNode], edges: list[HiveGraphEdge]
) -> list[DreamingSuggestion]:
    connected: set[str] = set()
    for edge in edges:
        connected.add(edge.source_node_id)
        connected.add(edge.target_node_id)

    suggestions: list[DreamingSuggestion] = []
    for node in nodes:
        # Conservative triple condition: only flag a node that is disconnected by
        # every available signal, so incomplete edge data alone never trips it.
        if node.id in connected or node.source_id or node.parent_id:
            continue
        reason = (
            f"Node '{node.id}' has no incident edges, no source_id, and no "
            "parent_id."
        )
        suggestions.append(
            DreamingSuggestion(
                id=f"dream-orphan-{node.id}",
                type=DreamingSuggestionType.ORPHAN,
                rationale=(
                    f"Orphaned node: '{node.label}' ({node.id}) has no graph "
                    "edges, source linkage, or parent. Consider linking it or "
                    "removing it."
                ),
                node_ids=[node.id],
                edge_ids=[],
                confidence_hint="high",
                metadata={
                    "derived": True,
                    "evidence": _evidence(
                        node_ids=[node.id],
                        edge_ids=[],
                        source_ids=[],
                        reason=reason,
                        derivation=(
                            "Node id absent from every edge endpoint and "
                            "carrying neither source_id nor parent_id."
                        ),
                        fields_used=["edges", "source_id", "parent_id"],
                    ),
                    "edge_count": 0,
                    "source_linkage": "none",
                },
                created_at=node.updated_at,
            )
        )
    return suggestions


# --------------------------------------------------------------------------- #
# Rule: stale — old edge whose endpoints changed after it was asserted.
# --------------------------------------------------------------------------- #
def _derive_stale_links(
    nodes: list[HiveGraphNode],
    edges: list[HiveGraphEdge],
    now: datetime,
) -> list[DreamingSuggestion]:
    nodes_by_id = {n.id: n for n in nodes}
    suggestions: list[DreamingSuggestion] = []

    for edge in edges:
        if edge.created_at is None:
            continue  # no usable timestamp; cannot assess staleness
        edge_age_days = (now - edge.created_at).days
        if edge_age_days < STALE_LINK_MIN_AGE_DAYS:
            continue

        endpoints = [
            nodes_by_id.get(edge.source_node_id),
            nodes_by_id.get(edge.target_node_id),
        ]
        # Incomplete-data guard: only assess links whose endpoints both resolve.
        if any(node is None for node in endpoints):
            continue

        drifts = [
            (node.updated_at - edge.created_at).days
            for node in endpoints
            if node is not None and node.updated_at is not None
        ]
        if not drifts:
            continue
        max_drift = max(drifts)
        if max_drift < STALE_LINK_MIN_DRIFT_DAYS:
            continue

        node_ids = [edge.source_node_id, edge.target_node_id]
        reason = (
            f"Edge '{edge.id}' was created {edge_age_days}d ago, but an endpoint "
            f"node was updated {max_drift}d later; the link predates current "
            "knowledge."
        )
        suggestions.append(
            DreamingSuggestion(
                id=f"dream-stale-{edge.id}",
                type=DreamingSuggestionType.STALE,
                rationale=(
                    f"Possibly stale link: edge '{edge.id}' connects nodes that "
                    "changed after it was asserted. Review whether the "
                    "relationship still holds."
                ),
                node_ids=node_ids,
                edge_ids=[edge.id],
                confidence_hint="low",
                metadata={
                    "derived": True,
                    "evidence": _evidence(
                        node_ids=node_ids,
                        edge_ids=[edge.id],
                        source_ids=[],
                        reason=reason,
                        derivation=(
                            "Edge older than "
                            f"{STALE_LINK_MIN_AGE_DAYS}d whose endpoint updated "
                            f">= {STALE_LINK_MIN_DRIFT_DAYS}d after the edge was "
                            "created."
                        ),
                        fields_used=["edge.created_at", "node.updated_at"],
                    ),
                    "edge_age_days": edge_age_days,
                    "max_endpoint_drift_days": max_drift,
                },
                created_at=edge.created_at,
            )
        )
    return suggestions


def derive_dreaming_suggestions(
    *, store, now: datetime | None = None
) -> list[DreamingSuggestion]:
    """Derive deterministic Dreaming suggestions from store nodes/edges.

    Read-only: ``store`` is only queried, never mutated. ``now`` defaults to the
    current UTC time but is injectable so the stale-link rule is fully
    deterministic in tests. Output is sorted by suggestion type, then ``id``.

    Returns an empty list cleanly when no suggestions are derivable (e.g. an
    empty store), so callers can consume the section unconditionally.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    nodes = store.get_nodes()
    edges = store.get_edges()

    suggestions = [
        *_derive_duplicates(nodes),
        *_derive_orphans(nodes, edges),
        *_derive_stale_links(nodes, edges, now),
    ]
    suggestions.sort(key=lambda s: (_TYPE_SORT_RANK[s.type], s.id))
    return suggestions
