"""Phase 10C — intelligence report builder (Phase 11A demo fixtures).

Assembles a read-only :class:`IntelligenceReport` from the existing store state.
This is the backend foundation a future intelligence dashboard will consume; it
reuses the Phase 10B contract shapes (Dreaming suggestions, decay statuses,
provenance chains, query trails) and exposes them through one stable report.

Phase 13A makes the **Temporal Decay** section real: it is now derived from the
store's nodes/sources via deterministic timestamp thresholds (see
:mod:`app.services.temporal_decay`). Those rows carry ``metadata["derived"] =
True``. The remaining sections — Dreaming heuristics, provenance engine, query
persistence — still run NO real intelligence; Phase 11A populates them with
deterministic **demo/seed fixtures** (see
:mod:`app.services.intelligence_fixtures`) tagged ``metadata["fixture"] = True``
so the frontend panel shows meaningful sample content for demos and screenshots.
Those real logics arrive in later, dedicated phases.

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
    demo_dreaming_suggestions,
    demo_provenance_chains,
    demo_query_trail_entries,
)
from app.services.temporal_decay import derive_decay_statuses
from app.store.store import store as default_store


def build_intelligence_report(*, store=default_store) -> IntelligenceReport:
    """Build a deterministic, read-only :class:`IntelligenceReport`.

    ``store`` is read, never mutated. The Temporal Decay section is derived from
    it (Phase 13A); the remaining sections are still deterministic demo fixtures
    pending their own phases.
    """
    dreaming_suggestions = demo_dreaming_suggestions()
    # Phase 13A: the Temporal Decay section is now derived from real store state
    # (deterministic timestamp thresholds), not a static fixture. The remaining
    # sections stay fixture-backed pending their own phases.
    decay_statuses = derive_decay_statuses(store=store)
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
