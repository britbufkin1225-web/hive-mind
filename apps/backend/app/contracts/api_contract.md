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

## Source Registry (Phase 5A)

An **additive** registry of future import connectors (Obsidian, local files,
GitHub, PDF, web, API), persisted independently of the graph store. It is
separate from the graph's `/api/sources` (`HiveSource`) resource and does **not**
implement any vault scanning, markdown parsing, filesystem watching, or import
logic — it only registers source *records*.

`SourceRecord` shape (snake_case, matching the rest of the API):

```json
{
  "id": "reg-...",
  "name": "My Vault",
  "type": "obsidian",
  "root_path": "/path/to/vault",
  "status": "pending",
  "last_imported_at": null,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "metadata": {}
}
```

- `type`: `obsidian` | `local_files` | `github` | `pdf` | `web` | `api`
- `status`: `active` | `inactive` | `error` | `pending` (defaults to `pending`)

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/registry/sources` | List source records → `{ "sources": [...] }` |
| `POST` | `/api/registry/sources` | Create a record (201). Requires `name` + `type`; rejects blank name / invalid enum with 422 |
| `GET` | `/api/registry/sources/{id}` | Get one record (404 if unknown) |
| `PATCH` | `/api/registry/sources/{id}` | Partial update (404 if unknown, 422 on invalid). Refreshes `updated_at` |

### Persistence

- **Default path:** `apps/backend/data/source-registry.json` (gitignored).
- **Override:** `HIVEMIND_REGISTRY_PATH` env var (tests use throwaway temp files).
- Starts empty; missing/empty/corrupt file falls back to an empty registry
  without crashing. Writes are atomic (temp file + `os.replace`).

## Search & Query Helpers (Phase 3C)

The store exposes deterministic, read-only helpers that operate against the
persisted data. They back the console commands but are independently usable:

- `stats()` — counts per collection (`sources`, `nodes`, `edges`, `models`, `activity`).
- `list_records(type)` — records of a type; accepts singular/plural/alias forms;
  raises `ValueError` on an unknown type.
- `get_record(id)` — finds a record by id across all collections, returning
  `(type, record)` or `None`.
- `search(query)` — case-insensitive match across source/model names, node labels
  and tags, activity messages, and ids; an empty query returns empty lists.
- `filter_nodes(tag=, node_type=)`, `filter_sources(status=, source_type=)` — schema-compatible filters.

Safe mutation helpers (validate, dedupe, persist atomically):

- `add_tag(node_id, tag)` — adds a tag to a node, deduplicating; validates the node id.
- `link_nodes(source_id, target_id)` — creates a `linked_to` edge between two
  existing nodes, deduplicating identical links; validates both ids.
- `create_note(text)` — creates a `note` graph node from text.

## Hive Console (Phase 3D)

The Hive Console is an **app-controlled command interface**, not a shell. It
parses a fixed whitelist of commands and executes them against the store. It
never spawns processes, never touches the filesystem directly, and never
evaluates arbitrary code. `shlex` is used only to split quoted arguments.

### `POST /api/console/execute`

Request:

```json
{ "command": "add note \"Phase 3B persistence completed\"" }
```

Response (success):

```json
{
  "ok": true,
  "command": "add note",
  "result": { "type": "note", "id": "note-...", "message": "Note created" },
  "error": null
}
```

Response (controlled error — unknown/malformed/unsafe/not-found):

```json
{ "ok": false, "command": "blocked", "result": null, "error": "Unsafe command 'rm' is not permitted. ..." }
```

Command-level problems return HTTP 200 with `ok: false` and an `error` message
(they are valid console interactions). A missing `command` field in the request
body returns HTTP 422 from request validation.

### Supported commands (first version)

| Command | Effect |
| --- | --- |
| `help` | List available commands |
| `status` | Backend status + store stats |
| `list <type>` | List records (`sources`/`nodes`/`edges`/`models`/`activity`) |
| `find <query>` | Text search across records |
| `show <id>` | Show one record by id |
| `tag <id> <tag>` | Add a tag to a node (deduped) |
| `link <sourceId> <targetId>` | Link two nodes (deduped) |
| `add note "<text>"` | Create a note node |

### Security boundary

- The console **never** executes OS/system commands. There is no shell,
  PowerShell, bash, cmd, git, npm, package install, file deletion, or arbitrary
  command execution.
- Commands whose first token is a known system/shell keyword (e.g. `rm`,
  `powershell`, `bash`, `git`, `npm`, `del`, `Remove-Item`, `sudo`, `curl`, ...)
  are rejected with a controlled `blocked` error and are **not** executed.
- Unknown commands return an `unknown` error; malformed commands return a
  `malformed` error or a `Usage:` hint. Nothing falls through to the OS.

**Current limitation:** there is no frontend console panel yet — this phase adds
the backend command API only. There is still no Obsidian import/scanning.

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
