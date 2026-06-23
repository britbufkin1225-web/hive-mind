# Hive|Mind API Contract

This is the project-facing Phase 2 API contract for Hive|Mind. It describes the stable backend surface future frontend and dashboard work should plan against.

Detailed backend-local model examples and implementation notes live in `apps/backend/app/contracts/api_contract.md`.

Phase 2 remains contract-only. It intentionally does not add persistent storage, source ingestion, graph algorithms, authentication, file watching, or dashboard UI complexity.

## Base URL

Local backend: `http://localhost:8787`

Current Phase 1 frontend calls use the `/api` prefix, such as `GET /api/health`.

## Endpoint Summary

| Endpoint | Purpose | Phase 2 status |
| --- | --- | --- |
| `GET /health` | Process-level health check | Planned alias for future deployment checks |
| `GET /api/health` | Existing Phase 1 backend health check | Implemented |
| `GET /api/status` | Dashboard-ready backend status | Planned richer shape; Phase 1 shape preserved for now |
| `GET /api/sources` | List registered knowledge sources | Contracted, not fully implemented |
| `GET /api/sources/:id` | Read one registered source | Contracted, not fully implemented |
| `GET /api/graph` | Read graph nodes and edges together | Contracted, not fully implemented |
| `GET /api/graph/nodes` | Read graph nodes only | Contracted, not fully implemented |
| `GET /api/graph/edges` | Read graph edges only | Contracted, not fully implemented |
| `GET /api/activity` | Read dashboard activity events | Contracted, not fully implemented |
| `GET /api/models` | Read local model metadata | Contracted, not fully implemented |
| `GET /api/vault/summary` | Existing Phase 1 empty vault summary | Implemented placeholder |

## Contract Models

Phase 2 defines these shared data shapes:

- `HiveSource`
- `HiveGraphNode`
- `HiveGraphEdge`
- `HiveActivityEvent`
- `HiveSystemStatus`
- `HiveGraphResponse`

The matching backend Pydantic models are in `apps/backend/app/models/hive_models.py`.

The matching frontend TypeScript interfaces are in `apps/frontend/src/types/api.ts`.

Development-only mock data is in `apps/backend/app/mock/mock_data.py`. Mock data must remain clearly labeled and must not pretend to be imported user content.

## Compatibility Notes

Existing Phase 1 routes and response shapes remain valid during Phase 2. Future phases may migrate `GET /api/status` and dashboard consumers to the richer `HiveSystemStatus` shape after the frontend is ready.
