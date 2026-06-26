# Hive|Mind Roadmap

This roadmap explains what Hive|Mind can do now, what is demo-only, and what
should remain future work. It complements the per-phase summary table in the
[README](../README.md), the [Intelligence Surface Plan](intelligence-surface-plan.md),
and the portfolio-facing [Demo Guide](demo-guide.md).

## Current status

**Active phase:** Phase 15B — Provenance Chains Contract Types / Schema Alignment.

Phase 14E QA/evidence note: a Dreaming Suggestions end-to-end evidence pass was
requested, but this checkout does not contain the Phase 14C/14D backend-derived
Dreaming Suggestions implementation. The evidence record is documented in
[Phase 14E Dreaming Suggestions E2E Evidence](qa/phase-14e-dreaming-suggestions-e2e-evidence.md).

Phase 11C is documentation-only. It updates project status, demo guidance,
screenshot guidance, API/docs consistency, and agent coordination docs after the
Phase 11B Intelligence Report fixture UX work landed on `main`.

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

The Intelligence Report is currently a **fixture-backed demo surface**. It is
useful for explaining planned product direction and producing portfolio
screenshots, but the content is static sample data.

Current fixture sections:

- Dreaming-style suggestions.
- Temporal decay-style statuses.
- Provenance-style chains.
- Query trail-style entries.

Current non-capabilities:

- No real Dreaming engine.
- No temporal decay calculation.
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
| 11C | Active | Repo cohesion, API/docs consistency, and demo documentation. |
| 14E | QA finding | Evidence pass recorded; Phase 14C/14D backend-derived Dreaming Suggestions are not present in this checkout. |
| 15A | Complete | Planning-only Provenance Chains backend derivation plan. |
| 15B | Active | Provenance Chains contract types / schema alignment. |

## Future roadmap

Future implementation should replace fixture content with real deterministic,
read-only derivation in narrow phases. Keep the order conservative:

| Future track | Goal | Guardrail |
| --- | --- | --- |
| Intelligence derivation | Generate Dreaming-style suggestions from actual graph/store state. | Read-only; no AI/LLM until separately planned. |
| Temporal decay | Calculate freshness/staleness from timestamps and source context. | No graph mutation; indicators remain advisory. |
| Provenance | Build source/import/node chains from real imported records. See [Phase 15A Provenance Chains Derivation Plan](intelligence/provenance-chains-derivation-plan.md). | Present existing evidence; do not invent lineage. |
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
