# Dreaming Suggestion Derivation Plan

Parent label: **devdevbuilds**

Phase 14A — Dreaming Suggestion Backend Derivation Planning.

This is a **documentation-only** plan. It defines how future Dreaming
suggestions should be deterministically derived from existing Hive|Mind data.
It implements **no** backend logic, **no** endpoints, **no** contract changes,
and **no** frontend. It is the leash, the map, and the tranquilizer dart for the
Dreaming work that follows.

For context, see the [Roadmap](roadmap.md), the
[Intelligence Surface Plan](intelligence-surface-plan.md) (Dreaming Surface
section), the [API Contract](api-contract.md), and the prior backend-derivation
precedent set by Temporal Decay
([Phase 13C QA note](releases/phase-13c-temporal-decay-qa.md)).

## Purpose

In Hive|Mind, **Dreaming** means the system passively reviews existing knowledge
and suggests possible useful follow-up actions. It is a quiet analysis layer, not
an agent with write permissions.

This document answers, for a future implementer:

- **What data** Dreaming suggestions may read.
- **What suggestion types** should exist.
- **How** each suggestion type should be deterministically derived.
- **What scoring / ranking** rules apply.
- **What guardrails** prevent mutation, hallucination, AI dependency, and unsafe
  automation.
- **What future phases** should build from this plan and in what order.

The goal is to prepare Dreaming to become the next **real, backend-derived**
intelligence surface — following exactly the path Temporal Decay took in Phase
13A–13C — without implementing any of it in Phase 14A.

## Current Status

- The Dreaming contract shapes already exist and are stable (Phase 10B):
  `DreamingSuggestion`, `DreamingSuggestionType`, and `DreamingSuggestionStatus`
  in `apps/backend/app/models/hive_models.py`.
- The Intelligence Report currently returns **deterministic demo fixtures** for
  Dreaming, produced by `demo_dreaming_suggestions()` in
  `apps/backend/app/services/intelligence_fixtures.py`. Every fixture is tagged
  `metadata.fixture = true` so its demo origin is unambiguous in the wire
  payload.
- **No real Dreaming derivation exists.** No heuristic, scoring, or dedup logic
  runs anywhere today.
- Temporal Decay is the only backend-derived section so far
  (`app/services/temporal_decay.py`, `metadata.derived = true`). Dreaming should
  follow the same pattern: a pure, read-only projection over store state with an
  explainable reason on every row.

This phase changes none of the above. It only writes this plan.

## Non-Goals

Phase 14A explicitly does **not**, and the plan does not authorize within 14A:

- Implementing any Dreaming derivation logic.
- Adding or modifying endpoints or routers.
- Changing any existing API wire shape or behavior.
- Adding frontend UI or CSS.
- Adding graph mutation, edge creation, tagging, or any write path.
- Adding Obsidian import / mutation behavior.
- Adding AI/LLM calls or embeddings.
- Adding dependencies, filesystem watchers, background workers, or schedulers.
- Adding any autonomous action.
- Renaming existing phases or rewriting unrelated docs.

These remain non-goals for the *implementation* phases too, except where a later
phase narrowly and explicitly authorizes one (e.g. a future "apply" action gated
behind explicit user confirmation, which is out of scope for the whole 14x
track).

## Data Inputs

Dreaming derivation may read **only** already-persisted store state, exactly as
`derive_decay_statuses` does. Available, real inputs:

| Input | Accessor | Useful fields |
| --- | --- | --- |
| Graph nodes | `store.get_nodes()` → `HiveGraphNode` | `id`, `label`, `type`, `source_id`, `parent_id`, `tags`, `weight`, `metadata`, `created_at`, `updated_at`, `file_meta.last_modified` |
| Graph edges | `store.get_edges()` → `HiveGraphEdge` | `source_node_id`, `target_node_id`, `relationship`, `metadata.origin` |
| Sources | `store.get_sources()` → `HiveSource` | `id`, `name`, `type`, `path`, `status`, `created_at`, `updated_at`, `origin`, `vault_path` |
| Decay statuses | `derive_decay_statuses(store=...)` → `DecayStatus` | `status` (`fresh`/`aging`/`stale`/`unknown`), `review_needed`, `last_imported_at`, `last_updated_at`, `source_reliability_hint` |

Notes on availability:

- **Reuse, don't recompute.** Stale follow-ups should consume the existing
  `DecayStatus` rows rather than re-deriving freshness, so Dreaming and Temporal
  Decay never disagree.
- **Query history is NOT yet persisted.** There is no query/search persistence
  in the store today (`QueryTrailEntry` is fixture-only). Any signal that depends
  on real query activity — *Unresolved Query Patterns*, query co-occurrence,
  "appears in recent query activity" — is **blocked** until query persistence
  ships in its own phase. The plan calls these out per-type so 14C does not pick
  a query-dependent type first.
- **Edge derivation provenance.** Edges carry `metadata.origin` (e.g.
  `knowledge_graph_builder`). Soft-connection suggestions must not propose an
  edge that already exists (stored or derived) between the same two nodes.

`generated_at` (request time) is the only non-deterministic value permitted, just
as in the existing report builder. All suggestion content must be deterministic.

## Suggestion Types

Six planned types. Each maps to an existing `DreamingSuggestionType` enum value
where one exists; gaps are flagged for Phase 14B contract alignment.

| # | Suggestion | Existing enum | Data dependency | Recommended 14C candidate |
| --- | --- | --- | --- | --- |
| 1 | Possible Duplicate Nodes | `DUPLICATE` | nodes, sources | **Yes** |
| 2 | Soft Connection Opportunities | `RELATED_NODES` (+ `MISSING_BACKLINK`) | nodes, edges, tags | Partial (non-query signals only) |
| 3 | Stale Knowledge Follow-Ups | `STALE` | decay statuses, edges | **Yes** |
| 4 | Orphaned / Underconnected Nodes | `ORPHAN` | nodes, edges | **Yes** |
| 5 | Unresolved Query Patterns | `UNRESOLVED_QUERY` | **query persistence (missing)** | No — blocked |
| 6 | Source Coverage Gaps | *none yet* | sources, nodes, edges | Possible (needs new enum) |

### 1. Possible Duplicate Nodes

Detect records that may represent the same concept. Output explains *why* two or
more nodes look duplicate-like; it never merges them.

### 2. Soft Connection Opportunities

Suggest a possible edge between two nodes that are not currently connected. Output
must never create the edge — it references both `node_ids` and explains the
shared signal. Co-occurrence-in-query signals are deferred (query persistence).

### 3. Stale Knowledge Follow-Ups

Suggest knowledge records that may need **review** (never deletion). Built on top
of existing `DecayStatus` rows, prioritizing nodes that are `stale`/`aging` yet
still highly connected or otherwise still relevant.

### 4. Orphaned / Underconnected Nodes

Find nodes that exist but are weakly connected (zero or very few edges, no tags,
no source metadata). Output suggests classification, tagging, or source review.

### 5. Unresolved Query Patterns

Identify repeated searches that do not produce strong results. **Blocked** until
query history is persisted; documented here so the type is reserved, not built
prematurely.

### 6. Source Coverage Gaps

Detect imported sources that appear incomplete or uneven (few nodes, high node
count but low edge count, missing description/type/status, not refreshed
recently). Output recommends source review or re-import consideration. There is
**no existing enum value** for this type — Phase 14B must decide whether to add
`SOURCE_COVERAGE_GAP` or model it under an existing value.

## Derivation Rules

All rules are pure functions over store state, deterministic, and explainable.
Each produces a stable `id`, a `rationale`, the referenced `node_ids` /
`edge_ids`, a `confidence_hint`, and an `evidence` list in `metadata`. Suggested
deterministic `id` scheme: `dream-<type>-<sorted-node-ids-or-source-id>` so the
same input always yields the same id (idempotent, screenshot-safe).

### 1. Possible Duplicate Nodes

Signals (each contributes to confidence; none alone is conclusive):

- Same or near-same **normalized title** — lowercase, trim, collapse whitespace.
  Start with exact normalized-equality only; defer fuzzy/edit-distance matching.
- Same `source_id` **and** same/overlapping `file_meta` path.
- Same external reference recorded in `metadata` (when present).
- Strong **tag overlap** (e.g. Jaccard over `tags` above a fixed threshold).
- Substantially overlapping **linked neighbors**.

Emit one suggestion per candidate pair/cluster of distinct node ids. Never emit a
node paired with itself; deduplicate symmetric pairs by sorting node ids.

### 2. Soft Connection Opportunities

Signals:

- Shared `tags` (overlap above a fixed threshold).
- Shared `source_id`.
- Common neighboring nodes (both link to the same third node).
- Similar normalized titles.
- Same imported vault area/folder (derived from `file_meta` path prefix).

Rules: only emit for node pairs with **no existing edge** between them (check both
directions, stored and derived). Use `MISSING_BACKLINK` specifically when a
directed edge A→B exists but B→A does not and the relationship is reciprocal-eligible.

### 3. Stale Knowledge Follow-Ups

Signals (consume `DecayStatus`, do not recompute freshness):

- `status` is `stale` or `aging`, or `review_needed` is true.
- Node is still highly connected (edge count above a fixed threshold) despite an
  old most-recent timestamp.
- Source has not refreshed recently (old `source.updated_at`).
- (Deferred) Node appears in recent query activity but has stale metadata —
  requires query persistence.

Output recommends **review**, never deletion or edit.

### 4. Orphaned / Underconnected Nodes

Signals:

- Zero edges (`ORPHAN`), or edge count at/below a small fixed threshold.
- No `source_id` / no source metadata.
- No `tags`.
- (Deferred) No recent query hits — requires query persistence.

Output suggests possible classification, tagging, or source review.

### 5. Unresolved Query Patterns *(deferred)*

When query persistence exists: repeated query strings, similar query terms,
empty/low-confidence results, queries repeatedly touching stale nodes, queries
implying a missing source area. Output suggests importing, tagging, or connecting
relevant knowledge. **Not derivable today.**

### 6. Source Coverage Gaps

Signals:

- Source has very few nodes (count below a fixed threshold).
- Source has high node count but low edge count (ratio below a fixed threshold).
- Source `metadata` lacks description/type/status.
- Source has not been imported/refreshed recently.

Output recommends source review or re-import consideration; never re-imports
automatically.

All thresholds above must be defined as **named module constants** (mirroring
`FRESH_MAX_DAYS` / `AGING_MAX_DAYS` in `temporal_decay.py`) so every rule is
trivially reviewable and stable.

## Scoring and Ranking Model

Keep it simple, deterministic, and explainable — no learned weights, no AI.

Each suggestion is assessed on lightweight, bounded factors:

| Factor | Meaning |
| --- | --- |
| `signal_strength` | How many independent signals fired and how strongly. |
| `confidence` | Overall likelihood the suggestion is correct/useful. |
| `impact` | How much acting on it would improve the knowledge base. |
| `recency` | How recently the involved records were active. |
| `explainability` | Whether the suggestion has clear, human-readable evidence (must always be high — a suggestion with no evidence is not emitted). |

**Buckets, not floats.** Surface a coarse `confidence_hint` of `low` / `medium`
/ `high`, matching the existing `confidence_hint` string field on
`DreamingSuggestion` and the demo fixtures. A simple deterministic rule maps the
count/weight of fired signals to a bucket (e.g. 1 signal → `low`, 2 → `medium`,
3+ → `high`), with the exact mapping fixed as named constants.

If numeric scores are later justified, they must remain deterministic, bounded
(e.g. 0–100), and accompanied by the bucket; the plan recommends buckets first.

**Ranking.** Sort most-actionable first, then by a stable tiebreaker (suggestion
`id`), exactly as Temporal Decay sorts most-stale-first then by `node_id`.
Recommended order: `high` before `medium` before `low`, then by type priority
(stale/orphan review value first), then by `id`.

## Explanation Requirements

Every suggestion must carry human-readable evidence in the wire payload — this is
the non-negotiable anti-hallucination rule. Required, per suggestion:

- A `rationale` sentence (already a required field on `DreamingSuggestion`).
- An `evidence` list in `metadata`: short, concrete, human-readable strings, each
  naming a real signal that fired.
- `metadata.derived = true` (mirroring Temporal Decay), so a consumer can
  distinguish real derivation from `metadata.fixture` demo data.

Illustrative shape (documentation only — **do not implement in Phase 14A**):

```json
{
  "suggestion_type": "possible_duplicate",
  "confidence": "medium",
  "reason": "Two nodes share the same normalized title and source path.",
  "evidence": [
    "Matching normalized title",
    "Same source path",
    "Both imported from Obsidian"
  ]
}
```

In the real contract this maps onto the existing `DreamingSuggestion` fields:
`type`, `confidence_hint`, `rationale`, and `metadata.evidence` (+
`metadata.derived`). No suggestion may be emitted without at least one evidence
entry.

## Read-Only Safety Guardrails

Dreaming derivation must, like `temporal_decay.py`:

- **Read only** via `store.get_nodes()` / `store.get_edges()` /
  `store.get_sources()` (and `derive_decay_statuses`). Never call any store
  mutator, never write the JSON store, never touch the filesystem or a vault.
- Be a **pure projection**: identical store state ⇒ byte-for-byte identical
  suggestions. The only non-deterministic value anywhere is the report's
  `generated_at`.
- **Inject `now`** wherever time is needed (default `datetime.now(tz=utc)`,
  overridable) so tests are fully deterministic — exactly as decay does.
- Be **idempotent**: calling the derivation repeatedly accumulates nothing and
  changes nothing.
- Emit **advisory suggestions only**. There is no "apply", merge, link, or tag
  action in this track. `status` stays a review-only lifecycle
  (`open` → `acknowledged`/`dismissed`). Any future "apply" is a separate,
  explicitly-authorized, user-confirmation-gated phase outside 14x.
- Use **no AI/LLM, no embeddings, no network, no randomness, no background
  workers, no watchers**.

## API Contract Considerations

- The existing `IntelligenceReport.dreaming_suggestions: list[DreamingSuggestion]`
  field is the delivery vehicle. No new endpoint is needed — Dreaming rides the
  existing `GET /api/intelligence/report`, exactly as Temporal Decay does.
- Changes must be **additive**: the swap from `demo_dreaming_suggestions()` to a
  real `derive_dreaming_suggestions(store=...)` keeps the same wire shape. The
  only payload difference is `metadata.derived = true` replacing
  `metadata.fixture = true`.
- **Enum gap:** *Source Coverage Gaps* has no `DreamingSuggestionType` value
  today. Phase 14B must decide between adding `SOURCE_COVERAGE_GAP` (additive
  enum extension) or mapping it onto an existing value. No enum change happens in
  14A.
- `evidence` should be standardized in `metadata` (rather than a new top-level
  field) to avoid a breaking contract change; 14B confirms this.

## Frontend Display Considerations

- Reuse the existing Intelligence Report panel
  (`apps/frontend/src/components/IntelligenceReportPanel.tsx`). The same
  `isDerivedRecord` / `isFixtureRecord` labelling Temporal Decay uses should mark
  Dreaming rows **"Backend-derived"** once real, and **"Demo data"** while still
  fixture-backed — so the transition is visible and honest.
- Surface per-suggestion: type, `confidence_hint` bucket, `rationale`, and the
  `evidence` list. Clearly label every suggestion **read-only / advisory**.
- No new UI system, no CSS refactor, no graph overlay in this track. Frontend
  visibility is its own later phase (14E), not part of 14A.

## Testing Strategy

Mirror the Temporal Decay test approach
(`apps/backend/tests/test_temporal_decay.py`):

- **Pure-function unit tests** per suggestion type with a fixed `now` and a small
  hand-built store fixture; assert exact suggestions and evidence.
- **Boundary tests** on every named threshold constant (tag-overlap, edge-count,
  node-count, ratio, age windows).
- **Determinism / idempotency test**: deriving twice over the same store yields
  byte-for-byte identical output and mutates nothing (assert node/edge/source
  counts unchanged) — the Dreaming analogue of
  `test_derivation_is_repeatable_and_read_only`.
- **Negative tests**: no suggestion emitted without evidence; no soft-connection
  emitted where an edge already exists; no duplicate emitted for a node vs.
  itself.
- **No-op safety**: empty store ⇒ empty suggestion list, no error.

## Future Phase Breakdown

A conservative, one-step-at-a-time sequence after 14A:

| Phase | Goal | Guardrail |
| --- | --- | --- |
| **14A** | This plan (documentation only). | No code, no contract change. |
| **14B** | Dreaming contract / schema alignment — confirm `metadata.evidence` convention, resolve the *Source Coverage Gaps* enum gap (additively). | No derivation logic. |
| **14C** | Dreaming backend derivation MVP — implement **one** read-only type first (recommend **Possible Duplicate Nodes**, **Orphaned / Underconnected Nodes**, or **Stale Follow-Ups**; do **not** start with a query-dependent type). | Read-only, deterministic, evidence-required. |
| **14D** | Dreaming API integration — expose the derived suggestions through the existing `GET /api/intelligence/report`. | Additive; contract-compatible. |
| **14E** | Dreaming frontend visibility — label backend-derived suggestions in the existing panel, clearly read-only. | No new UI system / CSS refactor. |
| **14F** | Dreaming QA + demo evidence — verify determinism, document evidence, update README/roadmap, confirm no mutation. | Verification + docs only. |

*Unresolved Query Patterns* and query co-occurrence signals stay deferred across
all of the above until a separate query-persistence phase lands.

## Acceptance Criteria

Phase 14A is complete when:

- `docs/dreaming-suggestion-derivation-plan.md` exists and contains every
  required section: Purpose, Current Status, Non-Goals, Data Inputs, Suggestion
  Types, Derivation Rules, Scoring and Ranking Model, Explanation Requirements,
  Read-Only Safety Guardrails, API Contract Considerations, Frontend Display
  Considerations, Testing Strategy, Future Phase Breakdown, Acceptance Criteria.
- The plan is grounded in the **real** contract fields and store accessors that
  exist today (verified against `hive_models.py`, `temporal_decay.py`,
  `intelligence.py`).
- The plan defines a deterministic, read-only, evidence-required derivation with
  no AI/LLM, no mutation, and no autonomous action.
- The query-persistence dependency is explicitly flagged so no query-dependent
  type is implemented prematurely.
- **No** backend, frontend, contract, endpoint, persistence, or app-behavior
  files are changed in this phase — documentation only.
