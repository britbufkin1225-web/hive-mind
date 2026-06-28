<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

## Overview

Hive|Mind is a full-stack knowledge graph dashboard and backend/cybersecurity
portfolio project. It connects knowledge sources, starting with Obsidian vault
content, into a normalized backend data model and presents that model through a
focused web interface: a source registry, an import workflow, a query console, a
read-only knowledge graph view, and an intelligence report whose four sections
(Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails) are
all backend-derived and read-only.

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

- **Active phase:** `Phase 17A - Intelligence Report Cohesion + System Readiness
  Planning` (documentation/planning only — a cohesion pass over the four
  backend-derived Intelligence Report surfaces before any further intelligence
  logic). See the
  [Intelligence Report Cohesion + System Readiness Plan](docs/intelligence-report-cohesion-readiness-plan.md).
- **Completed foundation:** React/FastAPI app shell, local JSON-backed
  `HiveStore`, Hive Console (API + panel), Source Registry (backend + frontend +
  inspector), Obsidian adapter and import pipeline with frontend import panel,
  the Knowledge Graph API, the read-only Knowledge Graph panel, the custom
  read-only SVG graph visualization, and the read-only Intelligence Report panel
  with all four sections (Temporal Decay, Dreaming Suggestions, Provenance
  Chains, and Query Trails) backend-derived.

The current Intelligence Report is **fully backend-derived and read-only**. As of
Phase 13A the **Temporal Decay** section is backend-derived from real store
timestamps using deterministic thresholds; as of Phase 14C the **Dreaming
Suggestions** section is backend-derived from real store nodes/edges via
deterministic rules (duplicate labels, orphaned nodes, stale links); as of
Phase 15C **Provenance Chains** are backend-derived from existing
source/import/node/edge records with explicit evidence metadata; and as of
Phase 16C **Query Trails** are backend-derived from existing source/node/tag
structure (`source_followup` / `knowledge_gap` / `related_query_cluster`), with
the query-history-dependent categories deferred. No section is fixture-backed. It
does **not** run AI/LLM calls, semantic provenance inference, query persistence,
or any graph/source/store mutation. See the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md),
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
| Phase 11C | Complete | Repo cohesion and demo documentation pass. |
| Phase 12A | Complete | Demo freeze and release snapshot (documentation only). |
| Phase 13A | Complete | Temporal Decay backend-derived from store timestamps (read-only MVP). |
| Phase 13B | Complete | Temporal Decay frontend visibility and demo polish. |
| Phase 13C | Complete | Temporal Decay end-to-end QA and demo evidence pass. |
| Phase 14A | Complete | Dreaming suggestion backend derivation planning. |
| Phase 14B | Complete | Dreaming contract/schema alignment; `source_coverage_gap` remains deferred. |
| Phase 14C | Complete | Backend-derived deterministic Dreaming Suggestions MVP. |
| Phase 14D | Complete | Dreaming Suggestions frontend visibility in the Intelligence Report panel. |
| Phase 14E | Complete | Dreaming Suggestions QA/demo evidence lock pass (documentation only). |
| Phase 15A | Complete | Provenance Chains backend derivation planning and frontend readiness notes. |
| Phase 15B | Complete | Provenance Chains contract types / schema alignment. |
| Phase 15C | Complete | Backend-derived deterministic Provenance Chains MVP. |
| Phase 15D | Complete | Provenance Chains frontend visibility and demo polish. |
| Phase 15E | Complete | Provenance Chains QA/demo evidence lock pass. |
| Phase 16A | Complete | Query Trails / Query Memory foundation planning before persistence or APIs. |
| Phase 16B | Complete | Query Trails contract types / schema alignment (read-only `QueryTrailEntry` contract before persistence/derivation). |
| Phase 16C | Complete | Query Trails backend-derived MVP (`source_followup` / `knowledge_gap` / `related_query_cluster`) and frontend visibility; query-history categories deferred. |
| Phase 17A | Planned / Active | Intelligence Report cohesion + system readiness planning (documentation only). |

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
- **Intelligence Report panel** *(implemented, read-only)* - renders all four
  backend-derived sections: Temporal Decay, Dreaming Suggestions, Provenance
  Chains, and Query Trails.
- **Real Dreaming logic** *(implemented, read-only MVP — Phase 14C)* -
  deterministic, read-only suggestions derived from actual store nodes/edges:
  `duplicate` (shared normalized labels), `orphan` (no edges/source/parent), and
  `stale` (old links whose endpoints changed since). Each carries a
  `confidence_hint` and an explainable `metadata.evidence` trail; nothing is
  applied automatically. `source_coverage_gap` stays deferred/blocked (Phase 14B
  contract decision) and `unresolved_query` stays blocked until query history is
  persisted. No AI/LLM.
- **Temporal Knowledge Decay** *(implemented, read-only MVP — Phase 13A)* -
  freshness/staleness buckets derived from real store node/source timestamps via
  deterministic thresholds (fresh <= 30d, aging <= 90d, else stale). No graph
  mutation; indicators are advisory.
- **Provenance Chains** *(implemented, read-only MVP — Phase 15C)* -
  deterministic source/import/node/edge chains derived from existing store and
  source registry data. Each carries backend-owned `metadata.evidence`; missing
  source metadata is represented honestly as partial/unknown rather than
  fabricated.
- **Query trails** *(implemented, read-only MVP — Phase 16C)* - deterministic
  `source_followup` / `knowledge_gap` / `related_query_cluster` projections over
  existing source/node/tag structure, each with backend-owned `metadata.evidence`
  and a clean empty section. The query-history-dependent categories
  (`repeated_query` / `unresolved_question`) stay **deferred/blocked** until local
  query persistence exists.
- **Query memory persistence** *(planned)* - future local persistence and review
  surfaces for past console/search activity, which would unblock the deferred
  query-history categories above and Dreaming's `unresolved_query` pattern.

The Intelligence Report is now fully backend-derived; no section is fixture-backed.
The deterministic derivations are reproducible from store/source state, which is
what keeps the intelligence layer honest and reviewable as it grows.

## Roadmap

The next wave of work should keep the intelligence layer honest and reviewable:
contracts first, deterministic read-only derivation second, frontend surfaces
third. See the [full roadmap](docs/roadmap.md) and the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md) for detail.

| Planned / Active Phase | Focus |
| --- | --- |
| Phase 12A | Demo freeze + release snapshot; demo script, screenshot checklist, and README/API/docs consistency. |
| Future intelligence phases | Replace fixture sections with real deterministic read-only derivation. |
| Phase 16A | Query Trails / Query Memory foundation planning before persistence, APIs, or frontend display. |
| Phase 16B | Query Trails contract types / schema alignment — read-only `QueryTrailEntry` contract before any persistence or derivation logic. |
| Phase 16C | Query Trails backend-derived MVP and frontend visibility; query-history categories deferred. |
| Phase 17A | Intelligence Report cohesion + system readiness planning (documentation only). |
| Future query phases | Add query-persistence logic only after contracts, privacy boundaries, and validation. |

> **Intelligence data note:** `GET /api/intelligence/report` derives all four of
> its sections — **Temporal Decay** (Phase 13A), **Dreaming Suggestions**
> (Phase 14C), **Provenance Chains** (Phase 15C), and **Query Trails**
> (Phase 16C) — from existing store/source state, using deterministic rules,
> tagged `metadata.derived`, with a clean empty section when nothing is
> derivable. No section is fixture-backed. The query-history-dependent Query
> Trail categories (`repeated_query` / `unresolved_question`) stay deferred until
> local query persistence exists. No query persistence, AI/LLM logic, or
> graph/source/store mutation runs, and the endpoint remains read-only.

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
- [ ] Intelligence Report panel renders all four backend-derived sections: Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails.

## Documentation

- [Phase 1 foundation](docs/phase-1-foundation.md)
- [API contract](docs/api-contract.md)
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Intelligence Report Cohesion + System Readiness Plan](docs/intelligence-report-cohesion-readiness-plan.md)
- [Demo Guide](docs/demo-guide.md)
- [Demo Script](docs/demo-script.md)
- [Screenshot Checklist](docs/screenshot-checklist.md)
- [Phase 11 Demo Readiness](docs/phase-11-demo-readiness.md)
- [Phase 12A Demo Freeze + Release Snapshot](docs/releases/phase-12a-demo-freeze.md)
- [Phase 14E Dreaming Suggestions E2E Evidence](docs/qa/phase-14e-dreaming-suggestions-e2e-evidence.md)
- [Roadmap](docs/roadmap.md)

