# Hive|Mind — Phase 12A Demo Freeze + Release Snapshot

Parent label: **devdevbuilds**

## Snapshot summary

This document freezes the current demo-ready state of Hive|Mind after the
read-only Knowledge Graph, read-only Intelligence Report, intelligence demo
fixtures, and repo-cohesion documentation work landed on `main` through Phase
11C.

It is a **release snapshot and freeze marker**, not a feature expansion. It
records exactly what is implemented, what is intentionally read-only, what is
fixture/demo data, and what should not be changed until the next development
phase. No product features are added in Phase 12A.

For broader context, see the [README](../../README.md),
[Roadmap](../roadmap.md), [Demo Guide](../demo-guide.md),
[Intelligence Surface Plan](../intelligence-surface-plan.md), and
[Screenshot Checklist](../screenshot-checklist.md).

## Current demo status

- **Snapshot title:** Phase 12A — Demo Freeze + Release Snapshot.
- **Branch state at freeze:** `main` clean and merged through Phase 11C.
- **Demo readiness:** Stable, explainable, and portfolio/screenshot ready.
- **Nature of this phase:** Documentation/release-snapshot only.

The application runs locally as a full-stack demo: a FastAPI backend with a
local JSON-backed store and a React/Vite frontend presenting source registry,
import, console, knowledge graph, and intelligence report surfaces.

## Completed system areas

- Phases 0–2: Project initialization, planning, and API/data-model contracts.
- Phases 3A–4B: Backend store/persistence, console API, and console panel/UX.
- Phases 5A–6E: Source Registry (backend + frontend + inspector) and the
  Obsidian adapter/import pipeline with source-metadata visibility.
- Phases 7A–7B: Frontend Obsidian import action panel and UX hardening.
- Phases 8A–9C: Knowledge Graph API, read-only panel, custom SVG visualization,
  inspector sync, and demo polish.
- Phases 10A–10E: Intelligence surface planning, contract types, read-only
  Intelligence Report API, frontend panel, and UX hardening.
- Phases 11A–11C: Deterministic intelligence demo fixtures, screenshot
  readiness, repo cohesion, and demo documentation.

## What is implemented

- FastAPI backend foundation with health/status routes.
- React/Vite/TypeScript frontend foundation.
- Local JSON-backed `HiveStore` with explicit Pydantic contracts.
- Source Registry backend, frontend panel, and inspector.
- Obsidian import MVP and source-metadata visibility in the registry.
- Hive Console API and frontend console panel.
- Knowledge Graph API.
- Read-only Knowledge Graph frontend panel.
- Custom read-only SVG knowledge graph visualization.
- Node/edge inspector behavior with selection-driven highlighting.
- Intelligence contract models (shared backend/frontend shapes).
- Read-only Intelligence Report API (`GET /api/intelligence/report`).
- Read-only Intelligence Report frontend panel.
- Intelligence demo fixtures for every report section.
- Demo/screenshot readiness polish.

## Read-only boundaries

The following surfaces are intentionally **read-only** in this snapshot. They
present data for inspection and demonstration and never mutate stored state:

- Knowledge graph visualization.
- Intelligence report.
- Dreaming-style suggestions.
- Temporal decay-style status indicators.
- Provenance-style chains.
- Query trail-style entries.

## Fixture / demo data boundaries

The Intelligence Report content is currently **fixture-backed/demo-oriented**.
`GET /api/intelligence/report` returns deterministic demo/seed fixtures for
every section so the panel shows meaningful sample content for demos and
screenshots.

This content is illustrative sample data. It is **not** produced by full
production intelligence heuristics. Each fixture is labeled as demo/seed data so
the demo stays honest about what is real versus planned.

## What is intentionally not implemented yet

- Real Dreaming engine.
- Real Temporal Knowledge Decay logic.
- User-confirmed graph mutations.
- Persistent intelligence trails.
- Live Obsidian watcher/sync.
- Full external source ingestion.
- Production auth/deployment layer.

These are deliberate deferrals, not gaps to patch in this phase.

## Expected demo flow

1. Start the backend (`npm run dev:backend`).
2. Start the frontend (`npm run dev:frontend`).
3. Show the **Source Registry**.
4. Show **Obsidian import** visibility and source metadata.
5. Show the **Console** as a safe app command interface (not a shell).
6. Show the **Knowledge Graph** read-only visualization.
7. Select nodes/edges and show the **inspector**.
8. Show the **Intelligence Report**.
9. Explain the read-only intelligence surfaces and the planned next logic,
   framing fixtures as illustrative demo data.

## Validation

Run from the repository root.

Backend:

```bash
pytest apps/backend
```

Frontend:

```bash
npm run build --workspace apps/frontend
```

See the [README verification checklist](../../README.md#verification-checklist)
and [Demo Guide](../demo-guide.md) for the manual pre-demo checks.

## Known guardrails for the next phase

Keep the project stable, explainable, and demo-ready. Until the next development
phase is explicitly planned, do not:

- Add new backend endpoints.
- Add intelligence heuristics.
- Add a Dreaming implementation.
- Add Temporal Knowledge Decay logic.
- Add graph mutation controls.
- Add persistence changes.
- Add new dependencies.
- Redesign the dashboard.
- Modify branding/assets.
- Add fake implementation claims.

## Next recommended phase

**Phase 12B — Demo Script + Screenshot Capture Pack.**

Purpose: create the actual portfolio/demo presentation layer — screenshot
checklist execution, demo script, feature walkthrough, README demo section
polish, and an optional GitHub release notes draft.

Do not start Phase 12B in this branch.
