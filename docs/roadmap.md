# Hive|Mind Roadmap

This roadmap explains what Hive|Mind can do now, what is demo-only, and what
should remain future work. It complements the per-phase summary table in the
[README](../README.md), the [Intelligence Surface Plan](intelligence-surface-plan.md),
the portfolio-facing [Demo Guide](demo-guide.md), and the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md).

## Current status

**Active phase:** Phase 12A — Demo Freeze + Release Snapshot.

Phase 12A is documentation-only. It freezes the demo-ready state after Phase 11C
and records exactly what is implemented, read-only, fixture-backed, and
intentionally deferred. See the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md).
Phase 11C (the prior phase) updated project status, demo guidance, screenshot
guidance, API/docs consistency, and agent coordination docs after the Phase 11B
Intelligence Report fixture UX work landed on `main`.

No backend logic, frontend component changes, new endpoints, persistence changes,
intelligence heuristics, AI/LLM integration, graph mutation, Obsidian importer
changes, dependencies, or branding changes are part of Phase 11C.

## Implemented foundation

- React/Vite frontend and FastAPI backend app shell.
- Local JSON-backed `HiveStore` and Pydantic API models.
- Safe Hive Console API and frontend panel.
- Source Registry backend, frontend panel, and inspector.
- Obsidian adapter/import pipeline and frontend import action surface.
- Knowledge Graph API and read-only Knowledge Graph panel.
- Deterministic SVG graph visualization with inspector sync and demo polish.
- Intelligence report contracts and `GET /api/intelligence/report`.
- Read-only Intelligence Report panel with deterministic demo fixtures.

## Demo-only intelligence surface

The Intelligence Report is currently a **mostly fixture-backed demo surface**.
As of Phase 13A the **Temporal Decay** section is backend-derived (read-only)
from real store timestamps; the remaining sections are still static sample data
useful for explaining planned product direction and producing screenshots.

Backend-derived sections (read-only):

- Temporal decay statuses (Phase 13A — deterministic timestamp thresholds).

Current fixture sections:

- Dreaming-style suggestions.
- Provenance-style chains.
- Query trail-style entries.

Current non-capabilities:

- No real Dreaming engine.
- No provenance inference engine.
- No query persistence or query-memory logic.
- No AI/LLM calls.
- No automatic graph mutation.

## Phase history

| Phase | Status | Notes |
| --- | ---: | --- |
| 0 | Complete | Project initialization and planning foundation. |
| 1 | Complete | React/FastAPI foundation with health/status routes. |
| 2 | Complete | API contract and shared data model planning. |
| 3A-3D | Complete | Store, persistence, search helpers, and backend console. |
| 4A-4B | Complete | Frontend console panel and UX polish. |
| 5A-5C | Complete | Source Registry backend, frontend, inspector, and UX polish. |
| 6A-6E | Complete | Obsidian adapter/import pipeline and registry wiring. |
| 7A-7B | Complete | Frontend Obsidian import action panel and UX hardening. |
| 8A-8C | Complete | Knowledge Graph API, panel, and view-model prep. |
| 9A-9C | Complete | Read-only SVG graph visualization and QA polish. |
| 10A | Complete | Intelligence surface planning. |
| 10B | Complete | Intelligence contract types / read-only schemas. |
| 10C | Complete | Intelligence report endpoint foundation. |
| 10D | Complete | Intelligence Report frontend read-only panel. |
| 10E | Complete | Intelligence Report UX hardening / demo readiness. |
| 11A | Complete | Deterministic intelligence demo/seed fixtures. |
| 11B | Complete | Intelligence fixture UX review and screenshot readiness. |
| 11C | Complete | Repo cohesion, API/docs consistency, and demo documentation. |
| 12A | Active | Demo freeze and release snapshot (documentation only). |
| 13A | Complete | Temporal Decay section backend-derived from store timestamps (read-only MVP). |
| 13B | Complete | Intelligence Report frontend visibility for backend-derived Temporal Decay (bucket badges, reason/age/review surfacing, provenance labelling). |
| 13C | Complete | Temporal Decay end-to-end QA + demo-evidence and status-language pass (see [Phase 13C QA note](releases/phase-13c-temporal-decay-qa.md)). |

## Future roadmap

Future implementation should replace fixture content with real deterministic,
read-only derivation in narrow phases. Keep the order conservative:

| Future track | Goal | Guardrail |
| --- | --- | --- |
| Intelligence derivation | Generate Dreaming-style suggestions from actual graph/store state. | Read-only; no AI/LLM until separately planned. |
| Temporal decay | Backend-derived MVP shipped in Phase 13A (timestamp thresholds). Remaining: richer reference/last-seen signals. | No graph mutation; indicators remain advisory. |
| Provenance | Build source/import/node chains from real imported records. | Present existing evidence; do not invent lineage. |
| Query trails | Persist and present useful console/search history. | Requires explicit persistence design before implementation. |
| Agent Ops | Expose governed agent/source registry data in the app. | Start read-only from `docs/agent-lab/` shapes. |

## Standing guardrails

- Read-only surfaces first.
- Suggestions are advisory and never silently applied.
- Deterministic logic before any AI/LLM integration.
- Additive contracts only.
- No dashboard redesign or branding churn inside backend/API phases.
- Demo fixtures must stay labeled as demo data.
- Human merge gate remains with devdevbuilds.
