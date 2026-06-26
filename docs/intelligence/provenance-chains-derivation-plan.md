# Phase 15A Provenance Chains Derivation Plan

Date: 2026-06-26

## Purpose

Phase 15A defines how Hive|Mind should later derive Provenance Chains from
existing backend data. It is a planning-only phase. No backend provenance logic,
API endpoints, Pydantic models, frontend code, persistence, AI/LLM logic, graph
mutation, or source data mutation is implemented here.

The goal is to replace the remaining fixture-backed Provenance Chains section
of the Intelligence Report with deterministic, read-only backend derivation in a
later implementation phase.

## Definition

A backend-derived Provenance Chain is a read-only explanation of where an
existing knowledge record came from and which stored or derived relationships
support that explanation.

In Hive|Mind, "derived" means:

- The chain is calculated per request from current store, registry, import, and
  graph state.
- The same input data produces the same chain output, aside from enclosing
  report timestamps.
- The chain references existing records by id, path, or captured metadata.
- The chain does not invent lineage when source metadata is absent.
- The chain does not create, update, delete, or persist graph/source records.
- The chain uses deterministic service logic only; AI/LLM inference is out of
  scope.

## Existing Data Sources

Phase 15B should derive Provenance Chains only from data already present in the
backend:

| Data | Current provenance use |
| --- | --- |
| `HiveGraphNode.source_id` | Primary join from a knowledge node to a graph/source record. |
| `HiveGraphNode.file_meta` | Obsidian file path, vault-relative path, last modified time, and origin. |
| `HiveGraphNode.metadata` | Imported-note markers such as `origin`, `wiki_links`, and `markdown_links`. |
| `HiveGraphNode.created_at` / `updated_at` | Node creation and update history. |
| `HiveGraphEdge` ids and endpoints | Stored relationship evidence between nodes. |
| `HiveGraphEdge.metadata.origin` | Distinguishes derived graph-builder edges from stored edges. |
| `HiveGraphEdge.created_at` | Relationship evidence timestamp. |
| Source Registry `SourceRecord` | Source name, type, root path, status, timestamps, and metadata. |
| `SourceRecord.last_imported_at` | Import freshness and batch-level timing context. |
| Obsidian import summary metadata | Import counts, status, vault path, link counts, and last import summary. |
| Knowledge Graph projection | Deterministic union of stored edges and link-derived edges. |

The first implementation should prefer direct joins and captured metadata over
heuristic matching. If a node has no source id, no file metadata, and no graph
evidence, the chain should be sparse and explicit rather than speculative.

## Candidate Chain Shapes

The derivation service should support a small set of deterministic chain shapes.
Each shape may become one `ProvenanceChain` record or one ordered set of
`ProvenanceLink` entries inside a record.

### Source To Imported Note To Knowledge Node

Use when a node has `source_id` and Obsidian-style `file_meta`.

Shape:

```text
source registry record -> import/source metadata -> imported note path -> knowledge node
```

Evidence:

- `SourceRecord.id`, `name`, `type`, `root_path`, `last_imported_at`.
- `HiveGraphNode.file_meta.vault_path` or `file_path`.
- `HiveGraphNode.id`, `label`, `created_at`, `updated_at`.
- `HiveGraphNode.metadata.origin == "obsidian"` when present.

### Source To Node To Related Node

Use when a sourced node has graph neighbors.

Shape:

```text
source registry record -> knowledge node -> related node
```

Evidence:

- Node `source_id`.
- Stored or projected edges involving the node.
- Neighbor node ids and labels.
- Edge relationship type.

This shape should stay local to immediate neighbors in the first implementation.
Longer multi-hop provenance paths are future work unless Phase 15B explicitly
adds a bounded traversal rule.

### Source To Node To Edge Evidence

Use when an edge explains why a node is related to another node.

Shape:

```text
source registry record -> source node -> edge evidence -> target node
```

Evidence:

- Edge id, relationship, source node id, target node id.
- `metadata.origin` to classify the edge as derived or stored.
- For graph-builder edges, `metadata.link` can show the captured link text.
- Edge `created_at`, usually tied to source node update time for derived edges.

### Import Metadata To Derived Knowledge Records

Use when a source registry record has import batch metadata.

Shape:

```text
import batch/source metadata -> imported node ids -> derived knowledge records
```

Evidence:

- `SourceRecord.metadata.import_status`.
- `imported_count`, `updated_count`, `skipped_count`, `error_count`.
- `node_count`, `link_count`, `last_import_summary`.
- Node ids whose `source_id` matches the source record.

The first implementation should not require a new import-run persistence model.
It can present source-level import metadata as a batch context link, while
noting that detailed historical runs require a later schema/persistence phase.

## Expected Future Fields

The current `ProvenanceChain` and `ProvenanceLink` contracts already cover a
useful first backend-derived version:

| Field | Expected derivation |
| --- | --- |
| `node_id` | Required id of the node being explained. |
| `source_id` | Node `source_id` when it resolves to a source/registry record. |
| `source_type` | Source Registry type when available. |
| `origin_path` | Prefer `node.file_meta.vault_path`; fall back to `file_path`, source path, or metadata path. |
| `links` | Ordered source/import/node/edge references with labels and origin markers. |
| `linked_node_ids` | Deterministic sorted ids of immediate graph neighbors. |
| `derived_edge_ids` | Deterministic sorted ids of projected edges with derived origin metadata. |
| `stored_edge_ids` | Deterministic sorted ids of persisted store edges. |
| `created_at` | Node creation timestamp when available. |
| `updated_at` | Node update timestamp when available. |
| `last_imported_at` | Registry source `last_imported_at` when available. |
| `metadata` | Non-authoritative derivation details and quality flags. |

Recommended metadata keys for Phase 15B:

- `derivation_origin`: expected value `provenance_derivation`.
- `chain_shape`: one of the documented chain shape identifiers.
- `source_resolution`: `resolved`, `missing`, `ambiguous`, or `stale`.
- `timestamp_coverage`: `complete`, `partial`, or `missing`.
- `edge_counts`: counts for stored and derived edge evidence.
- `warnings`: stable machine-readable strings for edge cases.

## Contract And Schema Alignment

The current contracts appear sufficient for a first Phase 15B implementation
that derives node-centered Provenance Chains and emits sparse records when
metadata is incomplete.

Phase 15B should still perform a focused schema alignment check before code
changes. Possible additive alignment needs:

- A chain-level `status` or `quality` field if metadata warnings are not enough
  for frontend presentation.
- A dedicated chain `id` if consumers need stable item keys independent of
  `node_id`.
- A timestamp for derivation time if the report-level `generated_at` is not
  enough.
- A normalized import-run reference only if detailed import batch history is
  persisted in a later phase.

No contract changes are made in Phase 15A.

## Backend Service Boundaries

Phase 15B should keep provenance derivation as a pure backend service, close to
the existing intelligence and graph projection services.

Recommended boundary:

- Add a derivation helper under `apps/backend/app/services/` in the later
  implementation phase.
- Input: current graph store, source registry, and knowledge graph projection.
- Output: a list of `ProvenanceChain` contract objects.
- Sorting: deterministic by source id, node id, origin path, then label where
  applicable.
- Mutation: none.
- Persistence: none.
- Endpoint shape: reuse the existing Intelligence Report surface unless a later
  phase explicitly plans a new endpoint.

Responsibilities that should stay outside the provenance service:

- Obsidian vault scanning or importing.
- Source registry creation/update.
- Graph/node/edge mutation.
- Query Trails derivation.
- Dreaming Suggestions or Temporal Decay behavior.
- AI/LLM reasoning.

## Edge Cases

The implementation phase should handle these cases explicitly:

| Case | Expected behavior |
| --- | --- |
| Missing source metadata | Emit a sparse chain for the node with `source_id = null`, no invented source, and a warning. |
| Orphaned nodes | Emit node/source context if available; `linked_node_ids`, `derived_edge_ids`, and `stored_edge_ids` remain empty. |
| Missing timestamps | Leave timestamp fields null and add a timestamp coverage warning. |
| Imported notes without graph links | Emit source/import/node path without relationship evidence. |
| Duplicate source references | Prefer exact `node.source_id`; if registry duplicates exist for the same root path, mark ambiguity in metadata rather than guessing. |
| Stale source references | If `node.source_id` points to a missing registry/source record, keep the id, mark source resolution stale, and avoid source details. |
| Derived edge duplicates | Rely on the knowledge graph projection's de-duplication; keep output sorted and unique. |
| Path-only imported notes | Use captured `file_meta`/path evidence, but do not infer a source unless an id or registry match is deterministic. |
| Non-Obsidian nodes | Emit available source/node/edge evidence without assuming Obsidian metadata. |

## Testing Requirements For Phase 15B

The later implementation phase should include focused backend tests before any
frontend work:

- Derives a source -> imported note -> node chain from Obsidian-imported data.
- Derives linked node ids from stored graph edges.
- Separates stored edges from graph-builder-derived edges.
- Includes source registry timestamps and node timestamps when present.
- Emits sparse chains for nodes with missing source metadata.
- Handles orphaned nodes without failure.
- Handles missing timestamps without defaulting to fake dates.
- Does not duplicate chains, linked node ids, or edge ids.
- Produces deterministic ordering across repeated calls.
- Does not mutate graph store state or source registry state.
- Keeps Query Trails out of provenance derivation.
- Keeps Dreaming and Temporal Decay outputs unchanged.
- Confirms the Intelligence Report summary count reflects derived provenance
  records when fixtures are replaced.

Validation should include the existing backend test suite and any specific
intelligence contract tests updated in Phase 15B.

## Phase 15A Result

Phase 15A is complete when this plan exists and the roadmap points future
Provenance Chain work at deterministic, backend-derived, read-only derivation.
The phase intentionally leaves implementation, schema alignment, and frontend
presentation to later phases.
