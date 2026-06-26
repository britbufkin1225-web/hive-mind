"""Phase 11A — deterministic intelligence demo / seed fixtures.

This module supplies **read-only demo data** for the Phase 10C intelligence
report so the Phase 10D/10E frontend panel shows meaningful, stable content for
demos, screenshots, and README presentation.

It is explicitly *not* real intelligence:

  * NO Dreaming engine, heuristics, or scoring runs here.
  * NO temporal decay calculation runs here.
  * NO provenance engine or query persistence runs here.
  * NO AI/LLM integration.

Every value is a hand-authored, static fixture. There is no randomness and no
"now" anywhere in this module — all timestamps are frozen constants — so the
report content is byte-for-byte deterministic and safe for screenshots. Every
fixture is tagged ``metadata["fixture"] = True`` (and carries a human-readable
``note``) so it is unambiguous, in the wire payload itself, that this is
seed/demo data rather than production intelligence.

The fixtures reference plausible-looking node/source/edge ids but resolve to no
real store records; they are illustrative only. Nothing here mutates state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    DreamingSuggestion,
    DreamingSuggestionStatus,
    DreamingSuggestionType,
    ProvenanceChain,
    ProvenanceLink,
    ProvenanceLinkKind,
    QueryTrailEntry,
    QueryTrailKind,
    QueryTrailStatus,
    RegistrySourceType,
)

# Frozen reference timestamps — never `datetime.now()`. Keeping these as module
# constants makes the fixtures fully deterministic and trivially reviewable.
_T_IMPORTED = datetime(2026, 6, 20, 9, 0, 0, tzinfo=timezone.utc)
_T_UPDATED = datetime(2026, 6, 21, 11, 15, 0, tzinfo=timezone.utc)
_T_CREATED = datetime(2026, 6, 19, 8, 0, 0, tzinfo=timezone.utc)
_T_QUERY_RECENT = datetime(2026, 6, 24, 16, 45, 0, tzinfo=timezone.utc)
_T_QUERY_OLDER = datetime(2026, 6, 23, 10, 5, 0, tzinfo=timezone.utc)

# Tag every fixture so demo/seed origin is obvious in the payload itself.
_FIXTURE = "fixture"


def _fixture_meta(note: str) -> dict[str, object]:
    """Build the shared ``metadata`` marker stamped on every demo fixture."""
    return {_FIXTURE: True, "demo": True, "note": note}


def demo_dreaming_suggestions() -> list[DreamingSuggestion]:
    """Static Dreaming-style suggestions (advisory demo data only)."""
    return [
        DreamingSuggestion(
            id="demo-dream-1",
            type=DreamingSuggestionType.DUPLICATE,
            status=DreamingSuggestionStatus.OPEN,
            rationale=(
                "Potential duplicate concept between Obsidian import notes and "
                "source registry entries."
            ),
            node_ids=["demo-node-obsidian-1", "demo-node-registry-1"],
            edge_ids=[],
            confidence_hint="medium",
            metadata=_fixture_meta(
                "Illustrative duplicate suggestion; no dedup heuristic ran."
            ),
            created_at=_T_CREATED,
        ),
        DreamingSuggestion(
            id="demo-dream-2",
            type=DreamingSuggestionType.RELATED_NODES,
            status=DreamingSuggestionStatus.ACKNOWLEDGED,
            rationale=(
                "Soft link candidate between knowledge graph node and prior "
                "query trail."
            ),
            node_ids=["demo-node-graph-7"],
            edge_ids=["demo-edge-references-3"],
            confidence_hint="low",
            metadata=_fixture_meta(
                "Illustrative related-node suggestion; no link scoring ran."
            ),
            created_at=_T_UPDATED,
        ),
    ]


def demo_provenance_chains() -> list[ProvenanceChain]:
    """A single static provenance chain: Obsidian note -> node -> edge -> report."""
    return [
        ProvenanceChain(
            node_id="demo-node-obsidian-1",
            source_id="demo-source-obsidian-vault",
            source_type=RegistrySourceType.OBSIDIAN,
            origin_path="vault/notes/graph-import-behavior.md",
            links=[
                ProvenanceLink(
                    kind=ProvenanceLinkKind.SOURCE,
                    ref_id="demo-source-obsidian-vault",
                    label="Obsidian note",
                    origin="import",
                    metadata=_fixture_meta("Demo source record."),
                ),
                ProvenanceLink(
                    kind=ProvenanceLinkKind.NODE,
                    ref_id="demo-node-obsidian-1",
                    label="Normalized node",
                    origin="import",
                    metadata=_fixture_meta("Demo normalized node."),
                ),
                ProvenanceLink(
                    kind=ProvenanceLinkKind.EDGE,
                    ref_id="demo-edge-references-3",
                    label="Graph edge",
                    origin="dreaming",
                    metadata=_fixture_meta("Demo derived graph edge."),
                ),
            ],
            linked_node_ids=["demo-node-registry-1", "demo-node-graph-7"],
            derived_edge_ids=["demo-edge-references-3"],
            stored_edge_ids=[],
            created_at=_T_CREATED,
            updated_at=_T_UPDATED,
            last_imported_at=_T_IMPORTED,
            metadata=_fixture_meta(
                "Obsidian note -> normalized node -> graph edge -> report mention."
            ),
        ),
    ]


def demo_query_trail_entries() -> list[QueryTrailEntry]:
    """Static query-memory entries (no query persistence ran)."""
    return [
        QueryTrailEntry(
            id="demo-query-1",
            query="graph import behavior",
            kind=QueryTrailKind.SEARCH,
            status=QueryTrailStatus.RESOLVED,
            result_node_ids=["demo-node-obsidian-1", "demo-node-graph-7"],
            result_count=2,
            occurrence_count=3,
            pinned=True,
            last_executed_at=_T_QUERY_RECENT,
            metadata=_fixture_meta(
                "User searched graph import behavior; surfaced source, node, "
                "and a stale connection."
            ),
        ),
        QueryTrailEntry(
            id="demo-query-2",
            query="source confidence scoring",
            kind=QueryTrailKind.CONSOLE,
            status=QueryTrailStatus.UNRESOLVED,
            result_node_ids=[],
            result_count=0,
            occurrence_count=1,
            pinned=False,
            last_executed_at=_T_QUERY_OLDER,
            metadata=_fixture_meta(
                "Unresolved query example; nothing surfaced (demo only)."
            ),
        ),
    ]
