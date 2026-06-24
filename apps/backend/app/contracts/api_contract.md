# Hive|Mind Backend API Contract Reference

This backend-local reference expands the project-facing contract in `docs/api-contract.md` with model examples, endpoint response shapes, and future implementation notes.

It is a planning and shape contract only: source ingestion, graph algorithms, authentication, file watching, and dashboard complexity are intentionally deferred.

Local API base URL: `http://localhost:8787`

Existing Phase 1 routes remain available. New Phase 2 routes are documented for future implementation and may be backed by development-only mock data while persistent storage is not present.

## Local Persistence (Phase 3B)

The backend store (`app/store/store.py`) keeps state in memory and persists it to
a local JSON document so data survives a backend/store restart. The API response
shapes are unchanged by persistence.

- **Format:** a `HiveExportSnapshot` JSON document (the same shape returned by
  `GET /api/export`).
- **Default path:** `apps/backend/data/hivemind-store.json`.
- **Override:** set the `HIVEMIND_STORE_PATH` environment variable to relocate the
  file (used by tests to point at throwaway temp files).
- **Seeding:** on first construction, if no valid file exists, the store seeds
  development data from `app/mock/mock_data.py` and writes the file.
- **Durability:** every mutating operation (`upsert_source`, `delete_source`,
  `upsert_node`, `delete_node`, `import_snapshot`) writes atomically — a temp file
  in the same directory is written, fsynced, then `os.replace`d into place.
- **Resilience:** a missing directory is created on demand; a missing, empty, or
  corrupt/malformed file never crashes the API — the store logs a warning, falls
  back to seed data, and rewrites a valid file.
- **Validation:** imports reject duplicate ids (source/node/edge/model) and edges
  that reference unknown nodes; loaded files are validated against the Pydantic
  models before use.
- **Git:** runtime data is ignored via `apps/backend/data/` in `.gitignore`.
  Generated store files must not be committed.

**Current limitation:** persistence is local-JSON only. There is still no
Obsidian vault scanning, markdown parsing, frontmatter extraction, filesystem
watching, or vault import in this phase — the Obsidian-mappable fields below
remain placeholders.

## Obsidian Forward-Compatibility (placeholders only)

The data shapes reserve optional fields so a future phase can map cleanly to an
Obsidian vault without changing the wire contract. Phase 3A does **not** scan a
filesystem, parse markdown/frontmatter, watch files, or run a vault import —
these fields exist for forward compatibility and default to `null`/empty.

- `Source.origin` — provider the source came from, e.g. `"obsidian"`.
- `Source.vault_path` — vault root or relative path for vault-backed sources.
- `Graph Node.file_meta` — a `VaultFileMeta` placeholder (see below), or `null`.
- `Activity Event.origin` — provider that emitted the event.
- `Vault.vault_path`, `Vault.last_indexed` — linked vault root and last index time.

`VaultFileMeta` placeholder shape:

```json
{
  "file_path": "/vault/Note.md",
  "vault_path": "Note.md",
  "file_name": "Note.md",
  "extension": ".md",
  "frontmatter": {},
  "tags": [],
  "backlinks": [],
  "outlinks": [],
  "last_modified": "2026-06-23T12:00:00Z",
  "content_hash": null,
  "origin": "obsidian"
}
```

## Shared Models

### Source

Represents an imported or registered knowledge source.

```json
{
  "id": "src-dev-markdown",
  "name": "Dev Markdown Notes",
  "type": "markdown",
  "path": "mock://sources/dev-markdown",
  "status": "active",
  "created_at": "2026-06-23T12:00:00Z",
  "updated_at": "2026-06-23T12:00:00Z",
  "metadata": { "mock": true }
}
```

Supported `type` values: `markdown`, `text`, `json`, `folder`, `unknown`.

Supported `status` values: `active`, `pending`, `error`, `disabled`.

### Graph Node

Represents one item in the Hive|Mind knowledge graph.

```json
{
  "id": "node-concept-contracts",
  "label": "API Contracts",
  "type": "concept",
  "source_id": "src-dev-markdown",
  "parent_id": "node-file-roadmap",
  "tags": ["backend", "contract"],
  "weight": 0.9,
  "position": { "x": -40, "y": 240 },
  "metadata": { "mock": true },
  "created_at": "2026-06-23T12:00:00Z",
  "updated_at": "2026-06-23T12:00:00Z"
}
```

Supported `type` values: `root`, `folder`, `file`, `concept`, `note`, `model`, `source`.

### Graph Edge

Represents a relationship between two graph nodes.

```json
{
  "id": "edge-roadmap-contracts",
  "source_node_id": "node-file-roadmap",
  "target_node_id": "node-concept-contracts",
  "relationship": "references",
  "weight": 0.7,
  "metadata": { "mock": true },
  "created_at": "2026-06-23T12:00:00Z"
}
```

Supported `relationship` values: `contains`, `references`, `related`, `generated_from`, `linked_to`.

### Activity Event

Represents a dashboard activity or feed item.

```json
{
  "id": "event-import-deferred",
  "timestamp": "2026-06-23T12:00:00Z",
  "event_type": "import",
  "severity": "warning",
  "message": "Real source ingestion is intentionally deferred.",
  "source_id": "src-dev-markdown",
  "node_id": null,
  "metadata": { "mock": true }
}
```

Supported `event_type` values: `system`, `source`, `graph`, `import`, `error`.

Supported `severity` values: `info`, `warning`, `error`, `success`.

### System Status

Represents lightweight backend status for dashboard consumers.

```json
{
  "service": "hivemind-backend",
  "status": "ok",
  "uptime_seconds": 0,
  "version": "0.1.0",
  "environment": "development",
  "sources_count": 3,
  "nodes_count": 7,
  "edges_count": 6,
  "last_updated": "2026-06-23T12:00:00Z"
}
```

Supported `status` values: `ok`, `degraded`, `error`.

## Endpoints

### `GET /health`

Purpose: confirms that the backend process is available. This is the planned non-API-prefixed health route. Phase 1 currently exposes the same shape at `GET /api/health`.

Response shape:

```json
{
  "ok": true,
  "service": "hivemind-backend",
  "version": "0.1.0"
}
```

Example response:

```json
{
  "ok": true,
  "service": "hivemind-backend",
  "version": "0.1.0"
}
```

Notes for future implementation: keep this route dependency-free so deployment, tests, and local tooling can probe the process without loading storage or graph services.

### `GET /api/status`

Purpose: returns dashboard-ready backend status. Phase 1 currently returns an application connection shape; future implementation should migrate to the `HiveSystemStatus` shape when the frontend is ready.

Response shape:

```json
{
  "service": "string",
  "status": "ok",
  "uptime_seconds": 0,
  "version": "string",
  "environment": "string",
  "sources_count": 0,
  "nodes_count": 0,
  "edges_count": 0,
  "last_updated": "ISO-8601 datetime"
}
```

Example response:

```json
{
  "service": "hivemind-backend",
  "status": "ok",
  "uptime_seconds": 0,
  "version": "0.1.0",
  "environment": "development",
  "sources_count": 3,
  "nodes_count": 7,
  "edges_count": 6,
  "last_updated": "2026-06-23T12:00:00Z"
}
```

Notes for future implementation: compute counts from storage only after persistence exists. Until then, use zero counts or clearly labeled dev mock data.

### `GET /api/sources`

Purpose: lists registered knowledge sources.

Response shape:

```json
{
  "sources": []
}
```

Example response:

```json
{
  "sources": [
    {
      "id": "src-dev-markdown",
      "name": "Dev Markdown Notes",
      "type": "markdown",
      "path": "mock://sources/dev-markdown",
      "status": "active",
      "created_at": "2026-06-23T12:00:00Z",
      "updated_at": "2026-06-23T12:00:00Z",
      "metadata": { "mock": true }
    }
  ]
}
```

Notes for future implementation: this endpoint should read source registry records, not scan the filesystem on request.

### `GET /api/sources/:id`

Purpose: returns one registered source by id.

Response shape: a single `Source` object.

Example response:

```json
{
  "id": "src-dev-markdown",
  "name": "Dev Markdown Notes",
  "type": "markdown",
  "path": "mock://sources/dev-markdown",
  "status": "active",
  "created_at": "2026-06-23T12:00:00Z",
  "updated_at": "2026-06-23T12:00:00Z",
  "metadata": { "mock": true }
}
```

Notes for future implementation: return `404` when the id is unknown.

### `GET /api/graph`

Purpose: returns graph nodes and edges together for dashboard consumers.

Response shape:

```json
{
  "nodes": [],
  "edges": [],
  "metadata": {}
}
```

Example response:

```json
{
  "nodes": [
    {
      "id": "node-root",
      "label": "Hive|Mind",
      "type": "root",
      "source_id": null,
      "parent_id": null,
      "tags": ["mock"],
      "weight": 1,
      "position": { "x": 0, "y": 0 },
      "metadata": { "mock": true },
      "created_at": "2026-06-23T12:00:00Z",
      "updated_at": "2026-06-23T12:00:00Z"
    }
  ],
  "edges": [],
  "metadata": { "mock": true, "graph_logic": "not_implemented" }
}
```

Notes for future implementation: this route should return stored graph state. It should not compute expensive layouts or perform source ingestion.

### `GET /api/graph/nodes`

Purpose: returns graph nodes without edges.

Response shape:

```json
{
  "nodes": []
}
```

Example response:

```json
{
  "nodes": [
    {
      "id": "node-concept-contracts",
      "label": "API Contracts",
      "type": "concept",
      "source_id": "src-dev-markdown",
      "parent_id": "node-file-roadmap",
      "tags": ["backend", "contract"],
      "weight": 0.9,
      "position": { "x": -40, "y": 240 },
      "metadata": { "mock": true },
      "created_at": "2026-06-23T12:00:00Z",
      "updated_at": "2026-06-23T12:00:00Z"
    }
  ]
}
```

Notes for future implementation: support filtering later, after baseline persistence exists.

### `GET /api/graph/edges`

Purpose: returns graph edges without nodes.

Response shape:

```json
{
  "edges": []
}
```

Example response:

```json
{
  "edges": [
    {
      "id": "edge-roadmap-contracts",
      "source_node_id": "node-file-roadmap",
      "target_node_id": "node-concept-contracts",
      "relationship": "references",
      "weight": 0.7,
      "metadata": { "mock": true },
      "created_at": "2026-06-23T12:00:00Z"
    }
  ]
}
```

Notes for future implementation: edge validation should ensure referenced nodes exist once storage is introduced.

### `GET /api/activity`

Purpose: returns recent backend activity for dashboard feed panels.

Response shape:

```json
{
  "events": []
}
```

Example response:

```json
{
  "events": [
    {
      "id": "event-system-ready",
      "timestamp": "2026-06-23T12:00:00Z",
      "event_type": "system",
      "severity": "success",
      "message": "Mock backend contract data loaded for development.",
      "source_id": null,
      "node_id": null,
      "metadata": { "mock": true }
    }
  ]
}
```

Notes for future implementation: activity should be append-only enough for observability, but no event bus is required in Phase 2.

### `GET /api/models`

Purpose: lists local model metadata available to future graph or dashboard features.

Response shape:

```json
{
  "models": []
}
```

Example response:

```json
{
  "models": []
}
```

Notes for future implementation: keep this as metadata only. Do not load or execute model runtimes through this endpoint.

## Existing Phase 1 Endpoint

### `GET /api/vault/summary`

Purpose: returns the Phase 1 empty vault state.

Response shape and example response:

```json
{
  "totalFiles": 0,
  "totalSources": 0,
  "totalModels": 0,
  "totalNodes": 0,
  "graphMode": "not_initialized",
  "message": "Vault foundation ready. Graph logic not implemented in Phase 1."
}
```

Notes for future implementation: this can be retired or mapped to the richer graph/status endpoints once dashboard panels consume the Phase 2 contract.
