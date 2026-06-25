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
Console, the Source Registry, the Obsidian import pipeline, the Knowledge Graph
API, and the read-only Knowledge Graph panel with its custom SVG visualization.

- **Active phase:** `Phase 10A — Intelligence Surface Planning`.
- **Completed foundation:** React/FastAPI app shell, in-memory store, Hive
  Console (API + panel), Source Registry (backend + frontend + inspector),
  Obsidian adapter and import pipeline with frontend import panel, the Knowledge
  Graph API, the read-only Knowledge Graph panel, and the custom read-only SVG
  graph visualization with inspector sync and UX hardening.

Phase 10A is **documentation and architecture planning only**. It defines how the
future intelligence layer — Dreaming, temporal knowledge decay, provenance
chains, query memory, and later-tier ideas — will surface in the product, without
implementing any intelligence logic. See the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md) and
[roadmap](docs/roadmap.md).

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
| Phase 8C | Complete | Knowledge Graph visualization-prep view model and README revamp. |
| Phase 9A | Complete | First read-only SVG graph visualization. |
| Phase 9B | Complete | Knowledge graph panel UX hardening and inspector sync. |
| Phase 9C | Complete | Knowledge graph viz QA, demo polish, and link safety. |
| Phase 10A | Active | Intelligence surface planning (documentation only). |

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
- **Graph visualization** *(implemented, read-only)* — a deterministic SVG graph
  canvas built on the Phase 8C view model, with a legend, summary stats, and
  selection-driven highlighting/dimming. No physics, mutation, or editing.
- **Node inspector** *(implemented, read-only)* — focused detail view for the
  selected node or edge and its immediate relationships.
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

The next wave of work builds the read-only **intelligence layer** on top of the
existing foundations. Each step stays small and read-only: contract → backend
scoring/stub → frontend surface. See the
[full roadmap](docs/roadmap.md) and the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md) for detail.

| Planned Phase | Focus |
| --- | --- |
| Phase 10B | Intelligence contract types / read-only schemas. |
| Phase 10C | Dreaming suggestions backend stub. |
| Phase 10D | Dreaming suggestions frontend read-only panel. |
| Phase 11A–11C | Temporal Knowledge Decay (contract, scoring, indicators). |
| Phase 12A–12B | Provenance chain contract and inspector surface. |
| Phase 13A–13B | Query memory / knowledge trails (contract, surface). |

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
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Roadmap](docs/roadmap.md)
