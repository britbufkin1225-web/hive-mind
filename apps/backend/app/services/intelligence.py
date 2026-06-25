"""Phase 10C — intelligence report builder (Phase 11A demo fixtures).

Assembles a read-only :class:`IntelligenceReport` from the existing store state.
This is the backend foundation a future intelligence dashboard will consume; it
reuses the Phase 10B contract shapes (Dreaming suggestions, decay statuses,
provenance chains, query trails) and exposes them through one stable report.

The builder still runs NO real intelligence: NO Dreaming heuristics, NO temporal
decay calculation, NO provenance engine, and NO query persistence. Phase 11A
simply populates the report with deterministic **demo/seed fixtures** (see
:mod:`app.services.intelligence_fixtures`) so the frontend panel shows
meaningful sample content for demos and screenshots. Every fixture is tagged as
demo data in its ``metadata``; none of it is derived from store state. The real
logic still arrives in later, dedicated phases.

The builder is pure and read-only: it never writes to the store, so calling it
repeatedly never accumulates or mutates state. ``generated_at`` is the only
non-deterministic field (request time), matching ``HiveSystemStatus`` /
``HiveExportSnapshot`` conventions; all report content is deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.hive_models import (
    IntelligenceReport,
    IntelligenceReportSummary,
)
from app.services.intelligence_fixtures import (
    demo_decay_statuses,
    demo_dreaming_suggestions,
    demo_provenance_chains,
    demo_query_trail_entries,
)
from app.store.store import store as default_store


def build_intelligence_report(*, store=default_store) -> IntelligenceReport:
    """Build a deterministic, read-only :class:`IntelligenceReport`.

    ``store`` is accepted for forward compatibility (later phases will derive
    intelligence from it) but is only read, never mutated. In this phase the
    sections are filled with deterministic demo fixtures rather than store-
    derived intelligence.
    """
    # Reading is enough to confirm this builder stays a pure projection; it does
    # not mutate the store. No store-derived intelligence is produced yet — the
    # populated sections below are static demo fixtures only.
    _ = store

    dreaming_suggestions = demo_dreaming_suggestions()
    decay_statuses = demo_decay_statuses()
    provenance_chains = demo_provenance_chains()
    query_trail_entries = demo_query_trail_entries()

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
