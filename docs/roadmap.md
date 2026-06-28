# Hive|Mind Roadmap

This roadmap explains what Hive|Mind can do now, what is demo-only, and what
should remain future work. It complements the per-phase summary table in the
[README](../README.md), the [Intelligence Surface Plan](intelligence-surface-plan.md),
the portfolio-facing [Demo Guide](demo-guide.md), and the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md),
and the [Phase 14E Dreaming Suggestions E2E Evidence](qa/phase-14e-dreaming-suggestions-e2e-evidence.md), and the [Phase 15E Provenance Chains QA Evidence](qa/phase-15e-provenance-chains-qa-evidence.md), and the [Phase 17A Intelligence Report Cohesion + System Readiness Plan](intelligence-report-cohesion-readiness-plan.md).

## Current status

**Active phase:** Phase 17A - Intelligence Report cohesion + system readiness
planning (documentation/planning only).

With Phase 16C merged, all four Intelligence Report surfaces (Temporal Decay,
Dreaming Suggestions, Provenance Chains, Query Trails) are backend-derived and
frontend-visible. Phase 17A is a cohesion/readiness planning pass over the
Intelligence Report as a whole before any further intelligence logic is added.
It explains why cohesion comes before more implementation, reviews what is
demo-stable vs. what should be hardened next, and recommends a conservative,
foundation-first next phase. See
[Phase 17A Intelligence Report Cohesion + System Readiness Plan](intelligence-report-cohesion-readiness-plan.md).

Phase 16A (planning) and Phase 16B (contract/schema alignment) prepared a stable
`QueryTrailEntry` shape. See
[Phase 16A Query Trails / Query Memory Foundation Planning](phase-16a-query-trails-foundation-planning.md)
and
[Phase 16B Query Trails Contract Types / Schema Alignment](phase-16b-query-trails-contract-schema.md).

Phase 16C made the Query Trails section **backend-derived** from existing
store structure (`app/services/query_trails.py`), replacing the demo fixture as
the report's primary source. Rationale: derivation is backend-owned (not
fixtures, not client capture) so the trail logic stays deterministic, reviewable,
and testable against the same store the rest of the report reads.

Only the categories existing data supports are derived — `source_followup`
(a source with linked nodes), `knowledge_gap` (an unsourced node or uncovered
source), and `related_query_cluster` (2+ nodes sharing a tag). The query-history-
dependent categories `repeated_query` and `unresolved_question` stay **blocked
and deferred** because Hive|Mind has **no persisted query history**; fabricating
query-memory records would be dishonest. Phase 16C adds no query persistence,
storage tables, query logging, browser/localStorage capture, new endpoints,
AI/LLM, dependencies, graph/source mutation, or frontend/dashboard changes — the
derived trails are a read-only projection of structural data, not query memory.

## Implemented foundation

- React/Vite frontend and FastAPI backend app shell.
- Local JSON-backed `HiveStore` and Pydantic API models.
- Safe Hive Console API and frontend panel.
- Source Registry backend, frontend panel, and inspector.
- Obsidian adapter/import pipeline and frontend import action surface.
- Knowledge Graph API and read-only Knowledge Graph panel.
- Deterministic SVG graph visualization with inspector sync and demo polish.
- Intelligence report contracts and `GET /api/intelligence/report`.
- Read-only Intelligence Report panel with every section backend-derived
  (Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails).

## Backend-derived intelligence surface

The Intelligence Report is a **fully backend-derived, read-only surface** as of
Phase 16C. As of Phase 13A the **Temporal Decay** section, as of Phase 14C the
**Dreaming Suggestions** section, as of Phase 15C the **Provenance Chains**
section, and as of Phase 16C the **Query Trails** section are derived
(read-only) from existing store/source state. No section is fixture-backed.

Backend-derived sections (read-only):

- Temporal decay statuses (Phase 13A — deterministic timestamp thresholds).
- Dreaming suggestions (Phase 14C — deterministic `duplicate`/`orphan`/`stale`
  rules over store nodes/edges; conservative, with an explainable
  `metadata.evidence` trail and a clean empty section when nothing is derivable).
- Provenance chains (Phase 15C — deterministic source/import/node/edge chains
  from existing store and source registry data, with backend-owned evidence and a
  clean empty section when no graph data exists).
- Query trails (Phase 16C — deterministic `source_followup` / `knowledge_gap` /
  `related_query_cluster` projections over store source/node/tag structure, with
  backend-owned evidence and a clean empty section when nothing is derivable).
  Query-history-dependent categories stay deferred.

Current non-capabilities:

- No `source_coverage_gap` derivation — deferred/blocked pending a future
  contract-expansion phase (Phase 14B contract decision).
- No `unresolved_query` derivation — blocked until query history is persisted.
- No `repeated_query` / `unresolved_question` Query Trail derivation — blocked
  until real persisted query history exists (Phase 16C defers these).
- No semantic provenance inference engine beyond existing source/node/import/edge
  records.
- No query persistence or query-memory logic.
- No AI/LLM calls.
- No automatic graph/source/store mutation.

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
| 12A | Complete | Demo freeze and release snapshot planning/status documentation. |
| 12B | Complete | Screenshot and demo script polish. |
| 13A | Complete | Temporal Decay section backend-derived from store timestamps (read-only MVP). |
| 13B | Complete | Intelligence Report frontend visibility for backend-derived Temporal Decay. |
| 13C | Complete | Temporal Decay end-to-end QA + demo evidence and status-language pass. |
| 14A | Complete | Dreaming Suggestion backend-derivation planning documentation. |
| 14B | Complete | Dreaming contract/schema alignment. |
| 14B.5 | Complete | Temporal Decay contract QA and edge-case hardening. |
| 14B.6 | Complete | Dreaming logic implementation readiness / defensive backend scope alignment. |
| 14C | Complete | Dreaming Suggestions backend-derived MVP for `duplicate_signal`, `orphaned_node`, and `stale_knowledge_link`. |
| 14D | Complete | Dreaming Suggestions frontend visibility and demo polish. |
| 14E | Complete | Dreaming Suggestions end-to-end QA and demo evidence pass. |
| 15A | Complete | Provenance Chains backend derivation planning and frontend readiness notes. |
| 15B | Complete | Provenance Chains contract types / schema alignment. |
| 15C | Complete | Provenance Chains backend-derived MVP for existing source/import/node/edge records. |
| 15D | Complete | Provenance Chains frontend visibility and demo polish. |
| 15E | Complete | Provenance Chains end-to-end QA and demo evidence pass. |
| 16A | Complete | Query Trails / Query Memory foundation planning before persistence or APIs. |
| 16B | Complete | Query Trails contract types / schema alignment (read-only contract before persistence/derivation). |
| 16C | Complete | Query Trails backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster`; `repeated_query` / `unresolved_question` deferred until query history is persisted. |
| 17A | Planned / Active | Intelligence Report cohesion + system readiness planning (documentation only); aligns the four backend-derived surfaces and recommends a conservative, foundation-first next phase. |

## Future roadmap

| Future track | Goal | Guardrail |
| --- | --- | --- |
| Intelligence derivation | Dreaming `duplicate_signal` / `orphaned_node` / `stale_knowledge_link` suggestions shipped backend in Phase 14C and frontend-visible in Phase 14D. Remaining: `source_coverage_gap` deferred by the pinned Phase 14B contract/schema state and `unresolved_query_pattern` blocked until query-history persistence exists. | Read-only; no AI/LLM until separately planned. |
| Temporal decay | Backend-derived MVP shipped in Phase 13A, frontend visibility/demo polish shipped in Phase 13B, and end-to-end QA shipped in Phase 13C. Remaining: richer reference/last-seen signals. | No graph mutation; indicators remain advisory. |
| Provenance chains | Backend-derived MVP (Phase 15C), frontend visibility/demo polish (Phase 15D), and QA evidence pass (Phase 15E) complete. Remaining: selected-node inspector extension, per-section error state. | Present existing evidence only; do not invent lineage; read-only. |
| Query trails | Persist and present useful console/search history. Phase 16A defined local/read-only boundaries and relationships; Phase 16B aligned the `QueryTrailEntry` contract; Phase 16C shipped a backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster` from existing source/node/tag structure and made it frontend-visible. Remaining: local query persistence to unblock `repeated_query` / `unresolved_question`. | Read-only structural projection; no query persistence/logging/capture; `repeated_query` / `unresolved_question` stay blocked until real query history exists. |
| Intelligence cohesion | Keep the four backend-derived surfaces (decay, dreaming, provenance, trails) aligned on terminology, evidence shape, empty-state parity, and readiness before adding a fifth. Phase 17A is the planning pass. | Documentation/cohesion first; no new intelligence logic until the readiness review justifies it. |
| Agent Ops | Expose governed agent/source registry data in the app. | Start read-only from `docs/agent-lab/` shapes. |

## Standing guardrails

- Read-only surfaces first.
- Suggestions are advisory and never silently applied.
- Deterministic logic before any AI/LLM integration.
- Additive contracts only.
- No dashboard redesign or branding churn inside backend/API phases.
- Demo fixtures must stay labeled as demo data.
- Human merge gate remains with devdevbuilds.


