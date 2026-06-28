"""Phase 11A — deterministic intelligence demo / seed fixtures.

This module supplies **read-only demo data** that historically backed the
fixture sections of the Phase 10C intelligence report. As of Phase 16C every
intelligence-report section is backend-derived, so the report no longer wires
any of these fixtures in: Temporal Decay (Phase 13A), Dreaming Suggestions
(Phase 14C), Provenance Chains (Phase 15C), and Query Trails (Phase 16C) are all
sourced from their derivation services. The demo builders below are retained for
reference and standalone illustration only (mirroring the retained
``demo_provenance_chains``); they are not part of the live report payload.

It is explicitly *not* real intelligence:

  * NO temporal decay calculation runs here (now derived: ``temporal_decay``).
  * NO Dreaming engine, heuristics, or scoring runs here (now derived:
    ``dreaming``).
  * NO query persistence runs here (Query Trails now derived: ``query_trails``).
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
    ProvenanceChain,
    ProvenanceChainStatus,
    ProvenanceLink,
    ProvenanceLinkKind,
    QueryTrailCategory,
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


def demo_provenance_chains() -> list[ProvenanceChain]:
    """A single static provenance chain: Obsidian note -> node -> edge -> report."""
    return [
        ProvenanceChain(
            node_id="demo-node-obsidian-1",
            id="demo-provenance-demo-node-obsidian-1",
            title="Obsidian note lineage",
            summary=(
                "Demo chain linking an Obsidian source to a normalized node "
                "and illustrative edge evidence."
            ),
            status=ProvenanceChainStatus.PARTIAL,
            read_only=True,
            source_id="demo-source-obsidian-vault",
            source_name="Demo Obsidian Vault",
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
            category=QueryTrailCategory.REPEATED_QUERY,
            status=QueryTrailStatus.RESOLVED,
            result_node_ids=["demo-node-obsidian-1", "demo-node-graph-7"],
            result_source_ids=["demo-source-obsidian-vault"],
            provenance_chain_ids=["demo-provenance-demo-node-obsidian-1"],
            result_count=2,
            occurrence_count=3,
            pinned=True,
            confidence_hint="high",
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
            category=QueryTrailCategory.UNRESOLVED_QUESTION,
            status=QueryTrailStatus.UNRESOLVED,
            result_node_ids=[],
            result_source_ids=[],
            provenance_chain_ids=[],
            result_count=0,
            occurrence_count=1,
            pinned=False,
            confidence_hint="low",
            last_executed_at=_T_QUERY_OLDER,
            metadata=_fixture_meta(
                "Unresolved query example; nothing surfaced (demo only)."
            ),
        ),
    ]
