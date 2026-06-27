# Phase 16A - Query Trails / Query Memory Foundation Planning

Parent label: **devdevbuilds**

Phase 16A is a **documentation-only** foundation for future Query Trails /
Query Memory work. It defines the intended concept, data boundaries,
implementation guardrails, and readiness checklist before any persistence,
backend APIs, frontend panels, or intelligence behavior are added.

No implementation is included in this phase.

## Purpose

Query Trails should eventually answer a simple dev-tool question:

> What did I ask Hive|Mind, what did it surface, and what unresolved knowledge
> gaps did that reveal?

For a developer using Hive|Mind as a source-aware knowledge graph, past queries
are not just command history. They are evidence of intent, investigation paths,
failed searches, repeated confusion, and useful entry points back into the graph.
That makes query memory potentially valuable, but also easy to overcollect or
misinterpret. Phase 16A exists to set the boundaries before the system starts
recording anything.

## What A Query Trail Is

In Hive|Mind, a **Query Trail** is a read-only record of a user-initiated
knowledge lookup and the local graph/source context that lookup interacted with.
It is not a chat transcript, not a reasoning trace, and not an autonomous memory
system.

A future query trail may include:

- The query text or normalized query label.
- The query surface that produced it, such as Hive Console or future search.
- The timestamp and local session context.
- The result summary, including result count and result types.
- Links to graph nodes, edges, sources, or provenance chains surfaced by the
  query.
- Whether the query returned no useful results.
- Whether the user saved, pinned, revisited, or dismissed the trail.

At first, Query Trails should remain local, read-only, and demo-safe. The current
static Query Trail fixtures may continue to explain the intended product
direction until real persistence is explicitly designed and implemented.

## Why Query Trails Matter

Hive|Mind is a dev-tool portfolio project built around source-aware knowledge
navigation. Query memory matters because developer questions often reveal the
shape of the work:

- Repeated searches can show where documentation is weak or concepts are hard to
  find.
- Empty-result queries can identify missing graph coverage without pretending to
  infer facts.
- Useful queries can become shortcuts back into important source and graph
  context.
- Query-to-source links can make demos more honest by showing why a displayed
  record appeared.
- Future Dreaming suggestions can use unresolved query patterns only after
  query history exists and is explicitly bounded.

The goal is not to monitor the user. The goal is to let a local project remember
the user's own investigation paths in a way that remains inspectable and
deletable.

## Event Shape To Plan For

Future implementation phases should define explicit backend-owned query record
models before storage or APIs are added. A useful first shape would likely
separate immutable query facts from derived display fields.

Candidate fields:

| Field | Purpose | Initial guidance |
| --- | --- | --- |
| `id` | Stable local identifier | Deterministic or generated locally; no remote identity. |
| `query_text` | User-entered query | Store only after privacy rules are defined. |
| `normalized_query` | Dedup/repeat key | Deterministic normalization; no semantic rewriting. |
| `surface` | Origin surface | Console/search/import-assist/etc. |
| `created_at` | Query time | Local timestamp. |
| `result_count` | Coarse outcome | Count only; avoid storing full payload copies by default. |
| `result_node_ids` | Graph links | References existing nodes; no graph mutation. |
| `result_edge_ids` | Graph links | References existing edges; no graph mutation. |
| `source_ids` | Source links | References existing source registry records. |
| `provenance_chain_ids` | Provenance links | References derived provenance records when available. |
| `status` | Review state | Examples: `resolved`, `unresolved`, `saved`, `dismissed`. |
| `metadata` | Evidence and flags | Must stay explicit, bounded, and non-secret by default. |

The first real implementation should prefer small records and references over
duplicating source content, node payloads, or full response bodies.

## Relationship To Existing Systems

### Sources

Query records may reference source ids when a query result comes from a known
source. They should not write source records, refresh imports, or imply source
quality. Missing source context should be represented honestly as unknown.

### Graph Nodes And Edges

Query records may reference node and edge ids returned by a query. They should
not create nodes, create edges, update weights, add tags, or mark graph records
as important. Query frequency may become a future signal only after a separate
planning step defines how to avoid popularity bias and noise.

### Provenance Chains

Query Trails should be able to link to provenance chains so a user can see why a
result appeared and where it came from. Provenance remains the evidence trail for
knowledge records; Query Trails are evidence of lookup activity. The two should
connect by id/reference, not by copying or fabricating lineage.

### Dreaming Suggestions

Future Dreaming behavior may use query history to propose
`unresolved_query_pattern` suggestions, but only after query persistence exists.
Dreaming should consume query records as read-only input and emit advisory
suggestions. It must not mutate query history or convert a query into a graph
fact.

### `unresolved_query_pattern`

`unresolved_query_pattern` must remain deferred until:

- Query records are persisted locally.
- Empty or weak-result queries are represented explicitly.
- Repeat detection is deterministic.
- Privacy and deletion behavior are defined.
- The UI can show the evidence without implying the system knows the answer.

Before those boundaries exist, unresolved-query behavior would be guesswork.

## Initial Local / Read-Only Scope

The first implementation phase after this plan should stay conservative:

- Local-only storage.
- Read-only display.
- Explicit fixture/demo labels until real records exist.
- No remote sync.
- No AI/LLM processing.
- No embeddings.
- No background capture.
- No graph/source/store mutation from query activity.
- No automatic Dreaming suggestions from query history until a later phase.
- No hidden collection outside intentional user query surfaces.

Users should be able to inspect what was captured and eventually clear it.

## Backend Boundaries Before Persistence Or APIs

Before adding persistence or endpoints, future phases should define:

- A Pydantic query record model and response model.
- The allowed query surfaces that may create records.
- A small write boundary for recording query events, separate from graph/source
  mutation helpers.
- A read boundary for summarizing query history.
- A retention/deletion policy.
- A fixture-to-real-data migration plan for the Intelligence Report section.
- Deterministic repeat/empty-result logic, with no semantic inference.
- Metadata rules that prevent raw source content or secrets from being copied
  into query history by default.

The query store should be treated as its own local evidence log, not as part of
the authoritative knowledge graph.

## Future Frontend Display Expectations

Later frontend work should make query memory useful without making it feel
surveillant or noisy.

Expected display behavior:

- Label Query Trails as local/read-only.
- Show recent queries with timestamps, result counts, and linked nodes/sources.
- Distinguish saved trails from passive history.
- Show empty-result or weak-result trails as review prompts, not errors.
- Link from a query trail to related graph nodes, sources, and provenance
  evidence where available.
- Keep fixture/demo entries visibly labeled until replaced by real records.
- Provide empty states for no history, disabled history, and cleared history.
- Avoid implying AI reasoning, hidden monitoring, or automatic graph edits.

Controls such as save, dismiss, clear, or export should be separately scoped.

## Risks

Query Trails are useful precisely because they sit close to user intent. That
creates risks:

- **Privacy:** Query text may contain secrets, names, credentials, internal
  project details, or sensitive debugging context.
- **Noise:** Many queries are exploratory, misspelled, duplicated, or
  low-signal.
- **Overcollection:** Full result payloads, source excerpts, or background
  capture would store more than the feature needs.
- **False inference:** Repeated searches do not automatically prove importance,
  missing knowledge, or user priority.
- **Demo confusion:** Fixture trails must not be mistaken for real persisted
  history.
- **Feedback loops:** Future suggestions based on query activity could amplify
  recent behavior over durable knowledge structure.

These risks are the reason Phase 16A is planning-first.

## Deferred Until Later Phases

Phase 16A does not authorize:

- Query persistence.
- Query-history APIs.
- Frontend Query Trail panels or controls.
- `unresolved_query_pattern` derivation.
- Dreaming integration with query history.
- AI/LLM query analysis.
- Embeddings or semantic clustering.
- Background/ambient capture.
- Remote sync.
- Graph/source/store mutation based on query activity.
- Import pipeline changes.
- Dependency changes.

## Why Planning Comes First

Temporal Decay, Dreaming Suggestions, and Provenance Chains all became safer
because Hive|Mind defined contract and derivation boundaries before expanding
implementation. Query Trails need the same discipline, with an extra privacy
constraint: once query text is captured, the system is holding user intent.

Planning first keeps Phase 16B from accidentally turning a useful local history
feature into an unclear memory system.

## Phase 16B Implementation-Readiness Checklist

Before Phase 16B starts, confirm:

- [ ] Query record model fields are explicitly approved.
- [ ] Local retention and deletion expectations are documented.
- [ ] Allowed capture surfaces are listed.
- [ ] Fixture/demo Query Trail behavior is preserved until real records exist.
- [ ] Query text privacy rules are documented.
- [ ] Backend write/read boundaries are named.
- [ ] No graph/source/store mutation is introduced by query recording.
- [ ] `unresolved_query_pattern` remains deferred unless query persistence is
      complete and reviewed.
- [ ] Frontend display expectations are scoped before UI work starts.
- [ ] Validation plan confirms docs-only vs. implementation behavior.
