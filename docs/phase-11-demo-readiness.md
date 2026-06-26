# Phase 11 Demo Readiness

Phase 11 made the intelligence area demoable without implementing real
intelligence logic.

## Phase 11A

Added deterministic demo/seed fixtures for `GET /api/intelligence/report`.

The fixtures cover:

- Dreaming-style suggestions.
- Temporal decay-style statuses.
- Provenance-style chains.
- Query trail-style entries.

Guardrail: fixtures are illustrative data only. They are not derived from the
store, graph, queries, AI/LLM calls, or external sources.

## Phase 11B

Polished the frontend Intelligence Report fixture/demo UX for screenshot and
review readiness.

The result is a read-only panel that can communicate the future intelligence
direction while keeping current capability honest.

## Phase 11C

Documents the repo state after Phase 11B:

- README current status and phase table.
- Roadmap current-vs-future accuracy.
- Intelligence surface plan consistency.
- API contract consistency with implemented routes.
- Demo guide and screenshot checklist.
- Agent Lab coordination notes.

Phase 11C is docs-only. It does not add endpoints, persistence, frontend
components, CSS, AI/LLM logic, Dreaming logic, temporal decay calculations,
provenance logic, query memory, graph mutation, or Obsidian importer changes.

## Demo truth statement

Use this sentence in reviews:

> Hive|Mind has the contracts and read-only UI for intelligence report surfaces,
> but the current report content is deterministic fixture data for demo and
> screenshot readiness. Real intelligence derivation is planned future work.

