<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds***

## Overview

Hive|Mind is a full-stack knowledge graph dashboard. It connects knowledge
sources — starting with Obsidian vault content — into a normalized backend data
model and presents that model through a focused web interface: a source
registry, an import workflow, a query console, and a read-only knowledge graph
view.

The conceptual model is deliberately simple:

- **Obsidian** is the human writing and thinking layer — where notes, links, and
  ideas are authored.
- **Hive|Mind** is the layer above it — the registry, normalization, graph, and
  analysis surface that turns that writing into structured, queryable knowledge.

Obsidian is where you think; Hive|Mind is where that thinking becomes a graph you
can inspect and, over time, reason about.

## Current status

The project has moved well beyond its initial foundation. The original Phase 1
app shell is complete and has been built on through backend storage, the Hive
Console, the Source Registry, the Obsidian import pipeline, and the Knowledge
Graph API and read-only panel.

- **Active phase:** `Phase 8C — Knowledge Graph Read-Only Visualization Prep`.
- **Completed foundation:** React/FastAPI app shell, in-memory store, Hive
  Console (API + panel), Source Registry (backend + frontend + inspector),
  Obsidian adapter and import pipeline with frontend import panel, the Knowledge
  Graph API, and the read-only Knowledge Graph panel.

Phase 8C adds a typed, deterministic graph **view model** that normalizes the
graph API response into a render-ready shape, and updates the Knowledge Graph
panel to consume it — preparing the data for a future visual graph renderer
without yet adding a graph canvas.

## Stack

- **Frontend:** Vite, React, TypeScript, plain CSS.
- **Backend:** Python, FastAPI, Pydantic.
- **Tests:** pytest.
- **Storage / model foundation:** in-memory `HiveStore` with explicit Pydantic
  contracts (the current repo implementation).
- **Source integration:** Obsidian adapter and import foundation.

## Completed phase summary

| Phase | Status | Summary |
| --- | ---: | --- |
| Phase 0 | Complete | Project initialization and planning foundation. |
| Phase 1 | Complete | Clean React/FastAPI app foundation with health/status endpoints. |
| Phase 2 | Complete | API contract and data model planning. |
| Phase 3A | Complete | Backend storage foundation and in-memory HiveStore. |
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
| Phase 8C | Active | Knowledge Graph visualization-prep view model and README revamp. |

## Planned logic

Hive|Mind is built as a pipeline from raw source material to inspectable,
queryable knowledge. The stages below describe the intended architecture; some
are implemented today and some are planned (and labeled as such).

- **Source intake** *(implemented for Obsidian)* — read content from a
  connected source such as an Obsidian vault.
- **Normalization** *(implemented)* — map source content into the shared
  node/edge data model rather than storing raw, source-specific shapes.
- **Source Registry** *(implemented)* — track each connected source, its status,
  and its import metadata.
- **Knowledge Graph** *(implemented, read-only)* — project normalized records
  into a deterministic graph of nodes and relationships.
- **Console / query layer** *(implemented, foundational)* — run read-only
  queries against the store from the frontend console.
- **Graph visualization** *(planned)* — a read-only visual graph canvas built on
  top of the Phase 8C view model.
- **Node inspector** *(planned)* — focused, read-only detail view for a selected
  node and its immediate relationships.
- **Provenance chains** *(planned)* — trace where a piece of knowledge came from
  and how it connects back to its source.
- **Query memory / knowledge trails** *(planned)* — remember past queries and the
  paths taken through the graph.
- **Temporal Knowledge Decay** *(planned)* — surface read-only indicators of
  stale or aging knowledge over time.
- **Dreaming reports** *(planned)* — read-only, suggested connections generated
  for review; never applied automatically.

None of the planned items above are built yet; they describe direction, not
current capability.

## Roadmap

| Planned Phase | Focus |
| --- | --- |
| Phase 8D | First read-only visual graph canvas. |
| Phase 8E | Node inspector and edge detail UX. |
| Phase 8F | Graph filters, search, and highlighting. |
| Phase 9A | Knowledge provenance chains. |
| Phase 9B | Query memory and knowledge trails. |
| Phase 10A | Dreaming reports as read-only suggestions. |
| Phase 10B | Temporal Knowledge Decay indicators. |

## Setup

Prerequisites: Node.js 20+ and Python 3.11+.

```bash
cd hivemind
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

## Documentation

- [Phase 1 foundation](docs/phase-1-foundation.md)
- [API contract](docs/api-contract.md)
