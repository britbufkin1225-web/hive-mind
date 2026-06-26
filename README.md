<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

## Overview

Hive|Mind is a full-stack knowledge graph dashboard and backend/cybersecurity
portfolio project. It connects knowledge sources, starting with Obsidian vault
content, into a normalized backend data model and presents that model through a
focused web interface: a source registry, an import workflow, a query console, a
read-only knowledge graph view, and a fixture-backed intelligence report demo.

The conceptual model is deliberately simple:

- **Obsidian** is the human writing and thinking layer, where notes, links, and
  ideas are authored.
- **Hive|Mind** is the layer above it: the registry, normalization, graph, and
  analysis surface that turns that writing into structured, queryable knowledge.

Obsidian is where you think; Hive|Mind is where that thinking becomes a graph you
can inspect and, over time, reason about.

## Current status

The project has moved beyond the initial foundation. The original Phase 1 app
shell is complete and has been built on through local JSON-backed backend
storage, the Hive Console, the Source Registry, the Obsidian import pipeline,
the Knowledge Graph API, and the read-only Knowledge Graph panel with its custom
SVG visualization.

- **Active phase:** `Phase 11C - Repo Cohesion + Demo Documentation Pass`.
- **QA note:** a Phase 14E evidence pass was requested, but this checkout does
  not contain the Phase 14C/14D backend-derived Dreaming Suggestions
  implementation. See
  [Phase 14E Dreaming Suggestions E2E Evidence](docs/qa/phase-14e-dreaming-suggestions-e2e-evidence.md).
- **Completed foundation:** React/FastAPI app shell, local JSON-backed
  `HiveStore`, Hive Console (API + panel), Source Registry (backend + frontend +
  inspector), Obsidian adapter and import pipeline with frontend import panel,
  the Knowledge Graph API, the read-only Knowledge Graph panel, the custom
  read-only SVG graph visualization, and the read-only Intelligence Report panel
  backed by deterministic demo fixtures.

The current Intelligence Report is **demo/fixture-only**. It shows stable sample
Dreaming, temporal decay, provenance, and query-trail entries for portfolio demos
and screenshots. It does **not** run real Dreaming logic, temporal decay
calculation, provenance-chain inference, query persistence, AI/LLM calls, or graph
mutation. See the [Intelligence Surface Plan](docs/intelligence-surface-plan.md),
[Roadmap](docs/roadmap.md), [Demo Guide](docs/demo-guide.md), and
[Screenshot Checklist](docs/screenshot-checklist.md).

## Stack

- **Frontend:** Vite, React, TypeScript, plain CSS.
- **Backend:** Python, FastAPI, Pydantic.
- **Tests:** pytest.
- **Storage / model foundation:** local JSON-backed `HiveStore` with explicit
  Pydantic contracts.
- **Source integration:** Obsidian adapter and import foundation.

## Completed phase summary

| Phase | Status | Summary |
| --- | ---: | --- |
| Phase 0 | Complete | Project initialization and planning foundation. |
| Phase 1 | Complete | Clean React/FastAPI app foundation with health/status endpoints. |
| Phase 2 | Complete | API contract and data model planning. |
| Phase 3A | Complete | Backend storage foundation and local JSON-backed HiveStore. |
| Phase 3C/3D | Complete | Store search helpers and Hive Console API. |
| Phase 4A | Complete | Frontend console panel wired to backend console execution. |
| Phase 4B | Complete | Console UX and result formatting improvements. |
| Phase 5A | Complete | Source Registry backend foundation. |
| Phase 5B | Complete | Source Registry frontend panel. |
| Phase 5C | Complete | Source Registry inspector and UX polish. |
| Phase 6A | Complete | Obsidian adapter contract. |
| Phase 6B | Complete | Obsidian import MVP. |
| Phase 6C | Complete | Obsidian import hardening and deterministic import summaries. |
| Phase 6D | Complete | Obsidian import API polish and Source Registry wiring. |
| Phase 6E | Complete | Obsidian metadata visibility in the frontend registry. |
| Phase 7A | Complete | Frontend Obsidian import action panel. |
| Phase 7B | Complete | Obsidian import UX hardening. |
| Phase 8A | Complete | Knowledge Graph API foundation. |
| Phase 8B | Complete | Frontend read-only Knowledge Graph panel. |
| Phase 8C | Complete | Knowledge Graph visualization-prep view model and README revamp. |
| Phase 9A | Complete | First read-only SVG graph visualization. |
| Phase 9B | Complete | Knowledge graph panel UX hardening and inspector sync. |
| Phase 9C | Complete | Knowledge graph viz QA, demo polish, and link safety. |
| Phase 10A | Complete | Intelligence surface planning (documentation only). |
| Phase 10B | Complete | Intelligence contract types / read-only schemas. |
| Phase 10C | Complete | Intelligence report endpoint foundation. |
| Phase 10D | Complete | Intelligence Report frontend read-only panel. |
| Phase 10E | Complete | Intelligence Report UX hardening and demo readiness. |
| Phase 11A | Complete | Deterministic intelligence demo/seed fixtures. |
| Phase 11B | Complete | Intelligence fixture UX review and screenshot readiness. |
| Phase 11C | Active | Repo cohesion and demo documentation pass. |
| Phase 14E | QA finding | Evidence pass added; this checkout is not the Phase 14C/14D backend-derived Dreaming Suggestions implementation. |

## Planned logic

Hive|Mind is built as a pipeline from raw source material to inspectable,
queryable knowledge. The stages below describe the intended architecture; some
are implemented today and some are planned (and labeled as such).

- **Source intake** *(implemented for Obsidian)* - read content from a
  connected source such as an Obsidian vault.
- **Normalization** *(implemented)* - map source content into the shared
  node/edge data model rather than storing raw, source-specific shapes.
- **Source Registry** *(implemented)* - track each connected source, its status,
  and its import metadata.
- **Knowledge Graph** *(implemented, read-only)* - project normalized records
  into a deterministic graph of nodes and relationships.
- **Console / query layer** *(implemented, foundational)* - run read-only
  queries against the store from the frontend console.
- **Graph visualization** *(implemented, read-only)* - a deterministic SVG graph
  canvas built on the Phase 8C view model, with a legend, summary stats, and
  selection-driven highlighting/dimming. No physics, mutation, or editing.
- **Node inspector** *(implemented, read-only)* - focused detail view for the
  selected node or edge and its immediate relationships.
- **Intelligence report contracts** *(implemented)* - shared backend/frontend
  shapes for Dreaming suggestions, decay statuses, provenance chains, query
  trails, and a summary rollup.
- **Intelligence Report panel** *(implemented, read-only demo)* - renders stable
  fixture data for the planned intelligence surfaces. Every fixture is marked as
  demo/seed data through metadata.
- **Real Dreaming logic** *(planned)* - future read-only suggestions generated
  from actual store/graph state.
- **Real Temporal Knowledge Decay** *(planned)* - future freshness/staleness
  calculations derived from timestamps and source context.
- **Real provenance chain inference** *(planned)* - future source/import/node
  chain construction from actual imported data.
- **Query memory / knowledge trails** *(planned)* - future persistence and review
  surfaces for past console/search activity.

The intelligence fixtures are illustrative. They are useful for explaining the
planned product direction, but they are not evidence that the real intelligence
engines exist.

## Roadmap

The next wave of work should keep the intelligence layer honest and reviewable:
contracts first, deterministic read-only derivation second, frontend surfaces
third. See the [full roadmap](docs/roadmap.md) and the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md) for detail.

| Planned / Active Phase | Focus |
| --- | --- |
| Phase 11C | Repo cohesion, demo docs, screenshot checklist, and API/docs consistency. |
| Future intelligence phases | Replace fixture sections with real deterministic read-only derivation. |
| Future provenance/query phases | Add real provenance and query-trail logic only after dedicated contracts and validation. |

> **Demo fixture note:** `GET /api/intelligence/report` currently returns
> deterministic **demo/seed fixtures** for every section so the Intelligence
> Report panel shows meaningful sample content for demos and screenshots. This is
> illustrative data only. No Dreaming engine, decay calculation, provenance
> engine, query persistence, or AI/LLM logic runs, and the endpoint remains
> read-only.

## Setup

Prerequisites: Node.js 20+ and Python 3.11+.

```bash
# from the repository root
npm install
python -m venv .venv
python -m pip install -r apps/backend/requirements-dev.txt
```

Activate the virtual environment before installing backend dependencies if your
shell does not do so automatically. Optionally copy `.env.example` to `.env` or
`apps/frontend/.env`; the frontend defaults to the local backend URL when the
variable is absent.

## Run

Run each service in a separate terminal from the repository root:

```bash
npm run dev:backend
npm run dev:frontend
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8787](http://localhost:8787)
- API health: [http://localhost:8787/api/health](http://localhost:8787/api/health)
- Interactive API docs: [http://localhost:8787/docs](http://localhost:8787/docs)

## Verification checklist

- [ ] `npm run check:frontend` completes successfully.
- [ ] `npm run check:backend` passes.
- [ ] `/api/health` returns `ok: true`.
- [ ] The frontend shows the backend as connected.
- [ ] Source Registry data renders.
- [ ] Obsidian import action panel renders.
- [ ] Knowledge Graph read-only panel renders.
- [ ] Graph view-model/prep data renders without runtime errors.
- [ ] Intelligence Report panel renders demo fixtures and labels them honestly.

## Documentation

- [Phase 1 foundation](docs/phase-1-foundation.md)
- [API contract](docs/api-contract.md)
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Demo Guide](docs/demo-guide.md)
- [Screenshot Checklist](docs/screenshot-checklist.md)
- [Phase 11 Demo Readiness](docs/phase-11-demo-readiness.md)
- [Phase 14E Dreaming Suggestions E2E Evidence](docs/qa/phase-14e-dreaming-suggestions-e2e-evidence.md)
- [Roadmap](docs/roadmap.md)
