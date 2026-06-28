# Phase 16B — Query Trails Contract Types / Schema Alignment

Parent label: **devdevbuilds**

Phase 16B is a **contract/schema alignment** pass for Query Trails / Query
Memory. It refines the `QueryTrailEntry` contract that the Intelligence Report
API (`GET /api/intelligence/report`) returns so a later phase can implement real
deterministic backend query-trail derivation and/or persistence against a stable
shape.

Phase 16A was planning-only. Phase 16B makes Query Trails **structurally ready**
without implementing query history persistence.

## Why contract-first

Query Trails are intended to become a real Hive|Mind intelligence surface that
records or derives useful query-memory patterns over time. Before adding backend
behavior, the project needs a stable contract so future logic has a clean shape
to return data through the existing Intelligence Report API.

Aligning the contract first prevents future persistence/derivation logic from
being coupled to unstable fixture shapes — it keeps planning text, fixture
assumptions, frontend display needs, and future persistence behavior from
getting mixed into one messy implementation pass. Build the pipe before turning
on the water.

This mirrors how Temporal Decay, Dreaming Suggestions, and Provenance Chains each
defined contract and derivation boundaries before expanding implementation
(e.g. Phase 15B aligned the Provenance Chain contract before the Phase 15C
derivation).

## Still not real query history

Query Trails are **still demo/seed fixtures**, not persisted query history. The
`query_trail_entries` section of the report is produced by
`app/services/intelligence_fixtures.py` and every entry is tagged
`metadata.fixture = true`. Phase 16B does **not**:

- persist queries or add database tables / storage mutation,
- add query logging middleware or browser/localStorage capture,
- add new API endpoints, AI/LLM logic, or autonomous memory mutation,
- mutate graph/source/store state,
- redesign the dashboard or add a new frontend panel,
- add dependencies.

Query Trails remain read-only and contract-aligned only.

## Contract changes

The backend `QueryTrailEntry` Pydantic model
(`apps/backend/app/models/hive_models.py`) and the matching frontend TypeScript
interface (`apps/frontend/src/types/api.ts`) gain these additive, default-safe
fields alongside the existing `id`, `query`, `kind` (`console` | `search`),
`status` (`resolved` | `unresolved`), `result_node_ids`, `result_count`,
`occurrence_count`, `pinned`, `last_executed_at`, and `metadata`:

| Field | Purpose | Notes |
| --- | --- | --- |
| `category` | Trail-type axis (`QueryTrailCategory`), separate from `kind` (the originating surface). | One of `repeated_query`, `unresolved_question`, `related_query_cluster`, `source_followup`, `knowledge_gap`, or `null`. Contract-only placeholders — no derivation assigns them yet; only fixtures may set them. |
| `result_source_ids` | Id-only links to Source Registry records the query surfaced. | References only; never resolved, mutated, or copied. |
| `provenance_chain_ids` | Id-only links to derived provenance chains. | References only; mirrors the Phase 16A relationship plan. |
| `confidence_hint` | Lightweight human-readable label (e.g. `high` / `low`). | Matches `DreamingSuggestion`; a numeric `confidence` model stays deferred (Tier 2), so the field is `confidence_hint`, never `confidence`. |
| `origin` | Surface/origin marker, defaults to `query_trail`. | Mirrors `DreamingSuggestion.origin`; advertises read-only query-trail output. |

Every added field is default-safe, so existing fixtures and any future persisted
record validate unchanged. Supporting evidence/reason metadata continues to
attach under `metadata` (e.g. `metadata.evidence`), keeping the contract
additive.

`unresolved_question` is the query-trail analogue of the still-blocked Dreaming
`unresolved_query` type and likewise does not imply persisted history.

## Fixture alignment

The two deterministic demo entries in
`app/services/intelligence_fixtures.py` are updated to populate the new fields
(category, source/provenance links, confidence hint) so the contract is
exercised end-to-end through the report. They remain frozen, byte-for-byte
deterministic, and tagged `metadata.fixture = true`.

## Validation

- Backend: `python -m pytest apps/backend` — contract-model defaults/serialization
  tests (`tests/test_intelligence_contracts.py`) and Intelligence Report tests
  (`tests/test_intelligence_report.py`) confirm the report returns contract-valid
  Query Trails records exposing the aligned fields, and that existing report
  sections still serialize correctly.
- Frontend: `npm --workspace apps/frontend run build` (`tsc -b && vite build`)
  confirms the TypeScript types stay build-compatible.

## What a later phase still owns

A future phase — not this one — would design and implement deterministic
query-trail derivation and/or local persistence: the query store, allowed
capture surfaces, retention/deletion policy, privacy rules for query text, and a
fixture-to-real-data migration for this report section. `unresolved_query_pattern`
remains deferred until query history is persisted and reviewed.
