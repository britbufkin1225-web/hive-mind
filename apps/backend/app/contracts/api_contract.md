# Hive|Mind Backend API Contract Reference

This backend-local reference expands the project-facing contract in
`docs/api-contract.md` with model examples, endpoint response shapes, and
implementation notes.

It began as a planning and shape contract. Several routes are now implemented,
including local JSON persistence, Source Registry persistence, one-shot Obsidian
import, graph reads, knowledge graph projection, console execution, and the
fixture-backed intelligence report. Authentication, file watching, background
sync, AI/LLM logic, and dashboard mutation flows are still deferred.

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

**Current limitation:** persistence is local-JSON only. One-shot Obsidian import
exists through `POST /api/obsidian/import`, but there is still no filesystem
watching, background sync, external database, auth boundary, or multi-user
storage.

## Source Registry (Phase 5A)

An **additive** registry of future import connectors (Obsidian, local files,
GitHub, PDF, web, API), persisted independently of the graph store. It is
separate from the graph's `/api/sources` (`HiveSource`) resource. The registry
itself only stores source *records*; the Obsidian import service writes/updates
registry records as part of a one-shot import, but the registry API does not scan
files or watch the filesystem on request.

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

## Obsidian Adapter Contract

Phase 6A defined the adapter contract for Obsidian vault integration. Later
phases added a one-shot import service and API.

Adapter-layer support:
- Obsidian source configuration shape
- Pure validation
- Adapter interface placeholder
- Source registry compatibility

Adapter-layer non-support:
- Filesystem scanning
- Filesystem watching

### Shapes

`ObsidianVaultConfig` (snake_case, matching the rest of the API):

```json
{
  "vault_id": "vault-1",
  "name": "My Vault",
  "root_path": "/vaults/my-vault",
  "include_patterns": ["**/*.md"],
  "exclude_patterns": [".obsidian/**"],
  "tag_prefix": "#",
  "link_strategy": "both",
  "metadata": {}
}
```

- `vault_id`, `name`, `root_path`: required, non-empty strings.
- `include_patterns` / `exclude_patterns`: optional lists of strings (default `[]`).
- `tag_prefix`: optional string.
- `link_strategy`: one of `wikilink` | `markdown` | `both` (defaults to `both`).
- `metadata`: optional object (default `{}`).

`ObsidianDocumentCandidate` — the normalized shape an adapter can emit:

```json
{
  "source_id": "reg-...",
  "source_path": "notes/a.md",
  "title": "A",
  "content_preview": null,
  "tags": [],
  "links": [],
  "metadata": {}
}
```

### Validation

`app.adapters.obsidian.validate_obsidian_config(data)` is a **pure** helper that
returns a list of human-readable error strings (empty = valid). It checks field
presence and types only. It does **not** check whether `root_path` exists on the
host machine — verifying a real location is a future import-phase concern.

### Adapter interface

`app.adapters.base.SourceAdapter` is an abstract base describing the contract:
*config in → normalized document candidates out* via `discover()`.
`app.adapters.obsidian.ObsidianVaultAdapter` is a placeholder that holds a
validated config and raises `NotImplementedError` from `discover()`; it performs
no filesystem traversal or parsing in this phase. The `obsidian` source type is
already recognized by the source registry (`RegistrySourceType.OBSIDIAN`).

## Obsidian Import (Phase 6B / 6C)

A single one-shot, backend-only import endpoint. It scans an explicit local
vault path and imports markdown notes into the graph store. The import is
**read-only over the vault** — it never creates, modifies, or deletes vault
files. There is no watcher, background sync, or edge generation in this phase.

### `POST /api/obsidian/import`

Request (`ObsidianImportRequest`, snake_case):

```json
{
  "vault_path": "/abs/path/to/vault",
  "source_name": "My Vault"
}
```

- `vault_path` (required) — local directory of the vault.
- `source_name` (optional) — defaults to the vault folder name.

A bad `vault_path` (empty/blank, missing, or not a directory) is a client error
→ **HTTP 400**. A missing `vault_path` field is **HTTP 422** (schema). Per-file
read/parse failures never fail the request; they are reported in the summary.

Response (`ObsidianImportSummary`):

```json
{
  "source_id": "reg-...",
  "source_name": "My Vault",
  "source": {
    "id": "reg-...",
    "name": "My Vault",
    "type": "obsidian",
    "status": "active",
    "root_path": "/abs/path/to/vault",
    "last_imported_at": "2026-06-24T12:00:00Z"
  },
  "vault_path": "/abs/path/to/vault",
  "imported_count": 3,
  "updated_count": 0,
  "skipped_count": 0,
  "duplicate_count": 0,
  "error_count": 0,
  "link_count": 4,
  "imported_node_ids": ["obsidian-abc123def456"],
  "warnings": [],
  "notes": ["Imported 3, updated 0, skipped 0, errors 0."]
}
```

Counts are **mutually exclusive** per scanned `.md` file — each note lands in
exactly one of: `imported_count` (new node), `updated_count` (existing node
refreshed on re-import), `skipped_count` (e.g. empty content), `duplicate_count`
(a file resolving to an already-seen node id within one run), or `error_count`
(read/parse failure, with a `warnings` entry). `imported_node_ids` lists every
node written (new + updated). `link_count` totals the wiki/markdown references
captured across imported notes (not yet materialized as edges in this phase).
`notes` are human-readable, deterministic summary lines; `warnings` carry
per-file problems.

### Source Registry linkage (Phase 6D)

Every successful import is wired into the **Source Registry** (`/api/registry/sources`):

- The run upserts a single Obsidian `SourceRecord`, keyed on the resolved
  `root_path` so **re-importing the same vault updates the existing record
  instead of duplicating it**. The `source` block in the response is the stable
  linkage back to that record (`id` matches `source_id`).
- `source.status` reflects the run outcome: `active` when at least one node was
  written (or the vault scanned cleanly), `error` when the run wrote nothing but
  hit per-file errors. An **invalid/rejected vault path raises before any record
  is created**, so a failed import never leaves a misleading registry entry.
- The record's `metadata` carries useful, bounded import detail:
  `origin`, `vault_path`, `import_status`, `imported_count`, `updated_count`,
  `skipped_count`, `duplicate_count`, `error_count`, `node_count`, `link_count`,
  and `last_import_summary` (the human-readable summary line). `last_imported_at`
  is refreshed on every run.

### Hardening guarantees (Phase 6C)

- **Stable node ids** — derived from the relative vault path
  (`obsidian-<sha1[:12]>`), so re-importing upserts the same nodes across runs
  and OSes rather than creating duplicates.
- **Stable source handling** — re-importing the same resolved `root_path` reuses
  its existing Obsidian source record (refreshing name/status) instead of
  registering a duplicate source.
- **Defensive parsing** — frontmatter/markdown parsing never raises; tags and
  links are order-preserving de-duplicated; notes with no tags/links still
  import; empty-content notes are skipped; a blank title falls back to
  `"Untitled"`. One bad note never aborts the run.

## Knowledge Graph API (Phase 8A)

The backend foundation for graph-shaped reads. A deterministic builder
(`app/services/knowledge_graph.py`) projects the existing stored/imported
records into nodes, edges, and summary counts. This is **read-only**: it scans
no filesystem, runs no import, writes nothing back to the store, and produces no
speculative/AI ("dreaming") connections.

### `GET /api/knowledge-graph`

Returns a stable `KnowledgeGraphResponse`:

```json
{
  "nodes": [],
  "edges": [],
  "summary": { "node_count": 0, "edge_count": 0 }
}
```

The shape is stable even when there is no graph data — `nodes`/`edges` are empty
lists and `summary` is zeroed.

- **Nodes** are the stored graph nodes (`HiveGraphNode`), de-duplicated by stable
  id with insertion order preserved. Imported Obsidian notes are included as
  nodes; repeated imports reuse stable ids, so no duplicate nodes appear.
- **Edges** are the union of (a) edges already persisted in the store
  (`HiveGraphEdge`) whose endpoints are present, and (b) link edges **derived**
  from imported Obsidian notes whose captured `wiki_links` resolve to another
  node. Derived edges:
  - use `relationship: "references"`,
  - carry a deterministic id (`kg-edge-<sha1[:12]>`) and
    `metadata.origin = "knowledge_graph_builder"` (with the originating `link`),
  - are never duplicated against an existing stored edge (or each other) with the
    same `(source, target, relationship)`,
  - skip unresolved links and self-links.
- **summary** mirrors the returned collections: `node_count == len(nodes)` and
  `edge_count == len(edges)`.

Wiki links resolve case-insensitively against a node's vault-relative path
(with/without `.md`), file name (with/without `.md`), and label; on a key
collision the first node wins, keeping resolution deterministic. The builder is
pure for a given store state — calling it repeatedly yields identical output and
never mutates the store.

**Current limitation:** edges are derived only from already-captured Obsidian
wiki links and pre-existing stored edges. There is no markdown-link resolution,
backlink inference, AI-suggested edges, graph mutation, or backend layout
calculation. The frontend has a deterministic read-only SVG graph visualization;
the backend only returns graph data.

## Intelligence Report API

The backend foundation for the read-only intelligence report. It rolls up the
intelligence contract shapes into one stable response consumed by the frontend
Intelligence Report panel.

### `GET /api/intelligence/report`

Returns an `IntelligenceReport`:

```json
{
  "generated_at": "2026-06-25T12:00:00Z",
  "report_version": "0.1.0",
  "read_only": true,
  "dreaming_suggestions": [],
  "decay_statuses": [],
  "provenance_chains": [],
  "query_trail_entries": [],
  "summary": {
    "dreaming_suggestion_count": 0,
    "decay_status_count": 0,
    "provenance_chain_count": 0,
    "query_trail_entry_count": 0
  }
}
```

Current behavior: the endpoint returns deterministic demo/seed fixtures for
every section so the UI has meaningful sample content for demos and screenshots.
The fixtures are static illustrative data, not store-derived intelligence.

Guardrails:

- No Dreaming heuristics.
- No temporal decay calculation.
- No provenance inference engine.
- No query persistence or query-memory logic.
- No AI/LLM calls.
- No graph mutation.

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

The frontend includes a read-only console panel wired to this endpoint. The
console remains app-controlled and cannot execute system commands.

## Obsidian Metadata Fields

The data shapes reserve optional fields for Obsidian-backed records. They began
as forward-compatible placeholders in Phase 3A and are now populated when the
one-shot Obsidian import path has source/file metadata available. Records that do
not come from Obsidian still default these fields to `null`/empty. There is still
no filesystem watcher or background sync.

- `Source.origin` - provider the source came from, e.g. `"obsidian"`.
- `Source.vault_path` - vault root or relative path for vault-backed sources.
- `Graph Node.file_meta` - a `VaultFileMeta` object (see below), or `null`.
- `Activity Event.origin` - provider that emitted the event.
- `Vault.vault_path`, `Vault.last_indexed` - linked vault root and last index time.

`VaultFileMeta` shape:

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
