"""Phase 10C — intelligence report builder.

Assembles a read-only :class:`IntelligenceReport` from the existing store state.
This is the backend foundation a future intelligence dashboard will consume; it
reuses the Phase 10B contract shapes (Dreaming suggestions, decay statuses,
provenance chains, query trails) and exposes them through one stable report.

The builder is intentionally inert for this phase: it runs NO Dreaming
heuristics, NO temporal decay calculation, NO provenance engine, and NO query
persistence — none of those produce stored data yet, so every section is an
empty list and the summary counts are all zero. The shape is what is contracted
here; the logic arrives in later, dedicated phases.

The builder is pure and read-only: it never writes to the store, so calling it
repeatedly never accumulates or mutates state. ``generated_at`` is the only
non-deterministic field (request time), matching ``HiveSystemStatus`` /
``HiveExportSnapshot`` conventions; all report content is deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    DecayStatus,
    DreamingSuggestion,
    IntelligenceReport,
    IntelligenceReportSummary,
    ProvenanceChain,
    QueryTrailEntry,
)
from app.store.store import store as default_store


def build_intelligence_report(*, store=default_store) -> IntelligenceReport:
    """Build a deterministic, read-only :class:`IntelligenceReport`.

    ``store`` is accepted for forward compatibility (later phases will derive
    intelligence from it) but is only read, never mutated. In this foundation
    phase no derived intelligence exists, so each section is empty.
    """
    # Reading is enough to confirm this builder stays a pure projection; it does
    # not mutate the store. No derived intelligence is produced in this phase.
    _ = store

    dreaming_suggestions: list[DreamingSuggestion] = []
    decay_statuses: list[DecayStatus] = []
    provenance_chains: list[ProvenanceChain] = []
    query_trail_entries: list[QueryTrailEntry] = []

    return IntelligenceReport(
        generated_at=datetime.now(tz=timezone.utc),
        dreaming_suggestions=dreaming_suggestions,
        decay_statuses=decay_statuses,
        provenance_chains=provenance_chains,
        query_trail_entries=query_trail_entries,
        summary=IntelligenceReportSummary(
            dreaming_suggestion_count=len(dreaming_suggestions),
            decay_status_count=len(decay_statuses),
            provenance_chain_count=len(provenance_chains),
            query_trail_entry_count=len(query_trail_entries),
        ),
    )
