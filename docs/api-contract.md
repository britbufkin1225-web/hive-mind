# Hive|Mind API Contract

This is the project-facing API contract for Hive|Mind. It describes the stable
backend surface the current frontend uses and future dashboard work should plan
against.

Detailed backend-local model examples and implementation notes live in `apps/backend/app/contracts/api_contract.md`.

The contract began in Phase 2 and has since been implemented in layers. The app
now includes local JSON-backed storage, Source Registry persistence, a one-shot
Obsidian import path, a deterministic read-only knowledge graph projection, and
an intelligence report endpoint backed by demo fixtures.

## Base URL

Local backend: `http://localhost:8787`

Most frontend calls use the `/api` prefix, such as `GET /api/health`.

## Endpoint Summary

| Endpoint | Purpose | Current status |
| --- | --- | --- |
| `GET /health` | Process-level health check | Implemented |
| `GET /api/health` | Existing Phase 1 backend health check | Implemented |
| `GET /api/status` | Dashboard-ready backend status | Implemented |
| `GET /api/vault` | Backend vault/store counts | Implemented |
| `GET /api/sources` | List stored graph sources | Implemented |
| `GET /api/sources/:id` | Read one stored graph source | Implemented |
| `GET /api/graph` | Read stored graph nodes and edges together | Implemented |
| `GET /api/graph/nodes` | Read stored graph nodes only | Implemented |
| `GET /api/graph/edges` | Read stored graph edges only | Implemented |
| `GET /api/knowledge-graph` | Read deterministic graph projection (nodes, edges, summary) | Implemented (Phase 8A) |
| `GET /api/intelligence/report` | Read fixture-backed intelligence report rolling up the intelligence contracts | Implemented demo fixtures |
| `GET /api/activity` | Read dashboard activity events | Implemented |
| `GET /api/models` | Read local model metadata | Implemented |
| `GET /api/export` | Export the current store snapshot | Implemented |
| `POST /api/import` | Import a validated store snapshot | Implemented |
| `POST /api/console/execute` | Execute a safe Hive Console command | Implemented |
| `GET /api/registry/sources` | List Source Registry records | Implemented |
| `POST /api/registry/sources` | Create a Source Registry record | Implemented |
| `GET /api/registry/sources/:id` | Read one Source Registry record | Implemented |
| `PATCH /api/registry/sources/:id` | Update one Source Registry record | Implemented |
| `POST /api/obsidian/import` | One-shot local Obsidian vault import | Implemented |
| `GET /api/vault/summary` | Existing Phase 1 empty vault summary | Implemented placeholder |

## Contract Models

Phase 2 defines these shared data shapes:

- `HiveSource`
- `HiveGraphNode`
- `HiveGraphEdge`
- `HiveActivityEvent`
- `HiveSystemStatus`
- `HiveGraphResponse`
- `KnowledgeGraphResponse` / `KnowledgeGraphSummary` (Phase 8A)
- `DreamingSuggestion`, `DecayStatus`, `ProvenanceChain`, `QueryTrailEntry` (Phase 10B intelligence contracts)
- `IntelligenceReport` / `IntelligenceReportSummary` (Phase 10C)

The matching backend Pydantic models are in `apps/backend/app/models/hive_models.py`.

The matching frontend TypeScript interfaces are in `apps/frontend/src/types/api.ts`.

Development-only mock data is in `apps/backend/app/mock/mock_data.py`. Mock data must remain clearly labeled and must not pretend to be imported user content.

## Intelligence Report

`GET /api/intelligence/report` exposes the Phase 10B intelligence contracts through a single, stable, read-only endpoint. The response is an `IntelligenceReport` with:

- `generated_at` - request time (the only non-deterministic field).
- `report_version` / `read_only` - report metadata; `read_only` is always `true`.
- `dreaming_suggestions`, `decay_statuses`, `provenance_chains`, `query_trail_entries` - one section per Phase 10B contract area.
- `summary` - deterministic per-section counts (`IntelligenceReportSummary`).

Phase 15B aligns `ProvenanceChain` for later backend-derived chains while
preserving the existing response section. A chain may now carry additive
display and audit fields: `id`, `title`, `summary`, `status`
(`complete` | `partial` | `unknown`), `read_only`, and `source_name`, alongside
the existing `node_id`, `source_id`, `source_type`, `origin_path`, ordered
`links`, linked node ids, edge ids, timestamps, and metadata. These fields are
contract-only readiness for future deterministic provenance derivation; fixture
content remains illustrative.

This is a **fixture-backed demo surface**: no real Dreaming, Temporal Knowledge
Decay, provenance-engine, or query-persistence logic runs yet, and no LLM/AI
calls are made. The endpoint returns deterministic sample entries for each
section so the frontend can show meaningful portfolio/demo content. The sample
entries are illustrative only and must not be described as store-derived
intelligence. The endpoint never mutates store state.

## Compatibility Notes

Existing Phase 1 routes and response shapes remain valid. New work should keep
wire-shape changes additive and should update this document when implementation
status changes.
