"""Phase 10C — intelligence report builder.

Assembles a read-only :class:`IntelligenceReport` from the existing store state.
This is the backend foundation a future intelligence dashboard will consume; it
reuses the Phase 10B contract shapes (Dreaming suggestions, decay statuses,
provenance chains, query trails) and exposes them through one stable report.

Phase 13A makes the **Temporal Decay** section real: it is now derived from the
store's nodes/sources via deterministic timestamp thresholds (see
:mod:`app.services.temporal_decay`). Phase 14C makes the **Dreaming Suggestions**
section real too: it is derived from the store's nodes/edges via deterministic,
explainable rules (see :mod:`app.services.dreaming`). Phase 15C makes
**Provenance Chains** backend-derived from existing source, node, import, and
edge state (see :mod:`app.services.provenance`). These derived sections carry
``metadata["derived"] = True`` and return clean empty sections when nothing is
derivable. Query persistence still runs NO real intelligence; Phase 11A keeps
that section populated with deterministic **demo/seed fixtures** (see
:mod:`app.services.intelligence_fixtures`) tagged ``metadata["fixture"] = True``
so the frontend panel shows meaningful sample content for demos and screenshots.

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
from app.services.dreaming import derive_dreaming_suggestions
from app.services.intelligence_fixtures import demo_query_trail_entries
from app.services.provenance import derive_provenance_chains
from app.services.temporal_decay import derive_decay_statuses
from app.store.registry import registry as default_registry
from app.store.store import store as default_store


def build_intelligence_report(
    *,
    store=default_store,
    registry=default_registry,
) -> IntelligenceReport:
    """Build a deterministic, read-only :class:`IntelligenceReport`.

    ``store`` and ``registry`` are read, never mutated. Temporal Decay (Phase
    13A), Dreaming Suggestions (Phase 14C), and Provenance Chains (Phase 15C)
    are derived from existing state; Query Trails remain deterministic demo
    fixtures pending their own phase.
    """
    # Phase 14C: Dreaming Suggestions are now derived from real store state
    # (deterministic label/edge/timestamp rules), not a static fixture.
    dreaming_suggestions = derive_dreaming_suggestions(store=store)
    # Phase 13A: the Temporal Decay section is likewise derived from real store
    # state (deterministic timestamp thresholds).
    decay_statuses = derive_decay_statuses(store=store)
    # Phase 15C: Provenance Chains are derived from existing graph/source/import
    # state. Query Trails remain fixture-backed until their dedicated phase.
    provenance_chains = derive_provenance_chains(store=store, registry=registry)
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
