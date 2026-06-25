# Hive|Mind Roadmap

This is the forward-looking roadmap for Hive|Mind, focused on the **intelligence
layer** planned in Phase 10A. It complements the per-phase summary table in the
[README](../README.md) and the [Intelligence Surface Plan](intelligence-surface-plan.md).

The intelligence layer is built in small, safe, mostly paired phases:
**contract → backend stub/scoring → frontend read-only surface.** This keeps each
phase reviewable and preserves the read-only, suggestion-only guarantees.

## Completed foundation

The app shell, in-memory store, Hive Console (API + panel), Source Registry
(backend + frontend + inspector), Obsidian adapter and import pipeline, the
Knowledge Graph API, and the read-only Knowledge Graph panel (with its custom SVG
visualization, view model, and inspector sync) are complete. See the README phase
table for the detailed history through the knowledge graph visualization QA and
polish work.

## Phase 10A — Intelligence Surface Planning (current)

Documentation and architecture only. Defines the intelligence surfaces, Tier 1
vs. Tier 2 features, guardrails, and the phase order below. No intelligence
logic, endpoints, models, or panels are added. Deliverables:
[intelligence-surface-plan.md](intelligence-surface-plan.md) and this roadmap.

## Intelligence implementation phases

Each phase is intentionally small. Contract phases add only shared shapes (no
logic); backend phases add deterministic, read-only computation; frontend phases
add read-only surfaces.

| Phase | Focus | Type | Builds on |
| --- | --- | --- | --- |
| 10B | Intelligence Contract Types / read-only schemas | Contract | 10A |
| 10C | Dreaming suggestions backend stub | Backend | 10B |
| 10D | Dreaming suggestions frontend read-only panel | Frontend | 10C |
| 10E | Intelligence report UX hardening / demo readiness | Frontend | 10D |
| 11A | Temporal Knowledge Decay contract | Contract | 10B |
| 11B | Temporal decay backend scoring | Backend | 11A |
| 11C | Temporal decay frontend indicators | Frontend | 11B |
| 12A | Provenance chain contract | Contract | 10B |
| 12B | Provenance inspector surface | Frontend | 12A |
| 13A | Query Memory / Knowledge Trails contract | Contract | 10B |
| 13B | Query trail frontend surface | Frontend | 13A |

### Why this order

1. **10B first** establishes every shared shape so the backend and frontend
   phases agree before any logic is written — the same discipline Phase 2 used
   for the API contract.
2. **Dreaming (10C/10D) leads** because it is the most visible intelligence
   surface and exercises the read-only suggestion pattern that the other
   surfaces reuse.
3. **Temporal Decay (11A–11C)** follows as a full contract → scoring → indicator
   vertical slice, and feeds Dreaming's "stale knowledge" suggestions.
4. **Provenance (12A/12B)** mostly *presents* fields that already exist at import
   time, so it needs a contract and a frontend surface but little new backend
   logic.
5. **Query Memory (13A/13B)** comes last in Tier 1 because it is the only surface
   that implies new persistence, so it should land after the read-only patterns
   are proven.

## Tier 2 (future, unscheduled)

Documented in the [Intelligence Surface Plan](intelligence-surface-plan.md) but
deliberately **not** scheduled yet. None should be built before Tier 1 is
complete.

- Uncertainty Tagging
- Session Snapshots
- Intent-Driven Graph Layouts
- CLI-only Ambient Capture

## Standing guardrails

All phases above inherit the intelligence-layer guardrails: read-only by default,
suggestions never silently applied, deterministic before AI/LLM, additive
contracts only, and no dashboard/branding/large-CSS churn. The full list lives in
the [Intelligence Surface Plan](intelligence-surface-plan.md#guardrails-for-future-agents).
