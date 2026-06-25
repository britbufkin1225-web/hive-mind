# Intelligence Surface Plan (Phase 10A)

This document plans the first **intelligence-facing surfaces** for Hive|Mind. It
is a planning and architecture document only. **No intelligence logic, backend
endpoint, database model, or frontend panel is implemented as part of Phase
10A.** The goal is to define *how* future intelligence features will appear in
the product so that later phases can build them safely on top of the existing
foundations.

## What already exists (do not rewrite)

These systems are the foundation the intelligence layer builds on. Phase 10A
does not change any of them.

- FastAPI backend foundation and in-memory `HiveStore`
  (`apps/backend/app/store/store.py`).
- Source Registry backend + frontend
  (`apps/backend/app/store/registry.py`, `apps/backend/app/routers/registry.py`,
  `apps/frontend/src/components/SourceRegistryPanel.tsx`).
- Obsidian adapter and import MVP
  (`apps/backend/app/adapters/`, `apps/backend/app/services/obsidian_import.py`).
- Hive Console API + frontend panel
  (`apps/backend/app/console/console.py`,
  `apps/frontend/src/components/ConsolePanel.tsx`).
- Knowledge Graph API foundation
  (`apps/backend/app/services/knowledge_graph.py`,
  `GET /api/knowledge-graph`).
- Read-only Knowledge Graph frontend panel + custom SVG visualization
  (`apps/frontend/src/components/KnowledgeGraphPanel.tsx`,
  `apps/frontend/src/lib/graphLayout.ts`,
  `apps/frontend/src/lib/graphViewModel.ts`).

## Core principles for the intelligence layer

Every future intelligence phase must honor these principles. They are the
non-negotiable contract for the whole layer.

1. **Read-only by default.** Intelligence surfaces *observe and suggest*. They do
   not mutate the knowledge graph, the source registry, or imported content.
2. **Suggestions, never silent edits.** Any derived output (a Dreaming
   suggestion, a decay flag, an inferred backlink) is a *proposal*. It is shown
   for review and requires explicit user action to ever become real graph data.
3. **Deterministic before clever.** Mirror the existing knowledge graph builder:
   pure functions over current store state, identical output for identical
   input. Scoring and heuristics come first; AI/LLM integration is explicitly out
   of scope until a much later, separately-planned phase.
4. **Additive, not destructive.** New contract types and fields are added
   alongside existing ones. No existing wire shape changes meaning.
5. **Clearly labeled provenance.** Anything the system derives is tagged with its
   origin (e.g. `metadata.origin = "dreaming"`), exactly as the graph builder
   already tags derived edges with `origin = "knowledge_graph_builder"`.

## Surface map (where intelligence appears in the UI)

The current app (`apps/frontend/src/App.tsx`) renders a vertical stack of
sections: backend connection, API health, vault summary, Source Registry,
Knowledge Graph, Console. The intelligence layer adds **read-only surfaces** to
this stack and to the existing graph/inspector — it does not redesign the
dashboard.

| Surface | Planned location | Tier | First building phase |
| --- | --- | --- | --- |
| Intelligence summary panel | New top-level read-only section | Tier 1 | 10D |
| Dreaming suggestions panel | New read-only section / drawer | Tier 1 | 10D |
| Knowledge decay indicators | Overlay/badges on graph + inspector | Tier 1 | 11C |
| Provenance chain inspector | Extension of node/edge inspector | Tier 1 | 12B |
| Query trail / history surface | New read-only section near Console | Tier 1 | 13B |
| Confidence / uncertainty badges | Inline badges on nodes/edges | Tier 2 | TBD |
| Session snapshots | Read-only history list | Tier 2 | TBD |
| Intent-driven graph layouts | Layout mode selector on graph | Tier 2 | TBD |
| Ambient capture | CLI-only, no UI surface initially | Tier 2 | TBD |

---

## Tier 1 surfaces

Tier 1 is the first wave: the surfaces that deliver visible intelligence value
while staying strictly read-only and deterministic.

### 1. Intelligence Dashboard Surface

A single read-only summary area that aggregates the other intelligence surfaces
at a glance. It answers "what does the system currently think about my
knowledge?" without the user opening each panel.

Planned contents:

- **Intelligence summary panel** — counts and rollups (e.g. number of open
  Dreaming suggestions, number of stale nodes, number of unresolved query
  trails). Pure derived counts, same spirit as `KnowledgeGraphSummary`.
- **Dreaming suggestions entry point** — a compact list/preview that links into
  the full Dreaming panel.
- **Decay/staleness indicators** — a top-level "N nodes need review" rollup.
- **Query trail entry point** — recent and saved query links.
- **Provenance entry point** — surfaced contextually from a selected node rather
  than as a standalone list.
- **Confidence/uncertainty badges** — *Tier 2*; reserved space only.

This surface reads from the other intelligence contracts; it owns no logic of its
own beyond aggregation.

### 2. Dreaming Surface

Dreaming is a **read-only suggestion engine**. It inspects current store/graph
state and proposes things a human might want to act on. It never mutates graph
data automatically; every output is a suggestion requiring user review or
confirmation.

Dreaming should eventually be able to suggest:

- Possible related nodes (nodes that look connected but are not linked).
- Potential duplicate knowledge (near-identical notes/labels).
- Stale or aging knowledge (overlaps with the Temporal Decay surface).
- Missing backlinks (one-directional links that could be reciprocal).
- Unresolved query patterns (repeated searches with no matching node).
- Orphaned ideas (nodes with no edges).
- Possible source conflicts (notes from different sources that disagree).

UI behavior:

- Each suggestion renders as a card with: a type, a human-readable rationale,
  the node(s)/edge(s) it references, and a confidence hint.
- Actions are **review-only** at first: *dismiss* and *acknowledge*. "Apply"
  (which would create real graph data) is explicitly deferred and, when it
  arrives, must go through the existing safe mutation helpers
  (`link_nodes`, `add_tag`, etc.) under explicit user action — never
  automatically.
- Suggestions are derived per-request and are not persisted as graph data.

Guardrail: **Dreaming output is advisory.** It is generated for review and is
never applied to the graph by the engine itself.

### 3. Temporal Knowledge Decay Surface

A read-only representation of how *fresh* a piece of knowledge is. Phase 10A does
**not** implement decay calculations — it only defines how staleness will be
represented.

Planned representation:

- **Status buckets:** `fresh` / `aging` / `stale` (plus an implicit `unknown`
  when timestamps are missing).
- **Timestamps surfaced:** last imported (`last_imported_at` already exists on
  source records / import metadata), last referenced, last updated.
- **Source reliability hints:** lightweight, derived from source type/status, not
  a trust engine.
- **Review-needed flag:** a boolean derived from status, feeding the dashboard
  rollup.
- **Visual graph overlays:** later phases may tint or badge graph nodes by decay
  status. Phase 10A reserves this as future work — no overlay is built now.

Decay status is a *derived view* over existing timestamps; it adds no new
authoritative state.

### 4. Provenance Surface

Lets the user inspect **where a piece of knowledge came from** and how it
connects back to its source. It extends the existing read-only node/edge
inspector rather than adding a separate system.

Planned contents (per selected node/edge):

- **Source chain** — registry source → import run → node.
- **Import source** — the `SourceRecord` and its type (e.g. `obsidian`).
- **Origin file/path** — vault-relative path / `file_meta` already captured at
  import.
- **Linked notes** — immediate graph neighbors.
- **Derived relationships** — which edges were *derived* (e.g. graph-builder
  `references` edges) vs. stored, using the existing `metadata.origin` marker.
- **Relationship confidence** — *Tier 2*; reserved.
- **Last update history** — from existing `created_at` / `updated_at` /
  `last_imported_at` fields.

Phase 10A makes **no provenance engine changes**. It documents how existing,
already-captured fields will be presented together.

### 5. Query Memory / Knowledge Trails

Turns previous Console actions and searches into navigable trails — "what have I
been asking, and where did it lead?"

Planned contents:

- **Recent queries** — last N console/search interactions.
- **Saved useful queries** — user-pinned queries.
- **Query-to-node links** — which nodes a query surfaced.
- **Repeated question detection** — the same query asked multiple times (feeds
  Dreaming's "unresolved query patterns").
- **Unresolved search trail** — queries that returned nothing.
- **Future "why did I ask this?" context view** — reconstructed context around a
  past query.

Phase 10A introduces **no persistence changes**. Persistence of query history is
deferred to its contract phase (13A). This section only documents the planned
contract so later phases have a target shape.

---

## Tier 2 surfaces (later, clearly future)

Tier 2 is explicitly future. These are documented so direction is captured, but
none are scheduled into the immediate phase order and none should be built before
Tier 1 lands.

- **Uncertainty Tagging** — confidence/uncertainty values on nodes, edges, and
  derived relationships, surfaced as badges. Requires a confidence model that
  does not yet exist.
- **Session Snapshots** — capture a read-only point-in-time view of the graph and
  surfaces so the user can compare "then vs. now." Builds on the existing
  `HiveExportSnapshot` export shape.
- **Intent-Driven Graph Layouts** — alternate deterministic layouts selected by
  user intent (e.g. "show provenance," "show clusters," "show stale"). Extends
  the existing `graphLayout.ts` rather than adding a physics engine.
- **CLI-only Ambient Capture** — a CLI path for capturing notes/ideas into the
  store without a UI surface. Deliberately CLI-only and out of the web app at
  first.

---

## Guardrails for future agents

Future intelligence phases **must not**, unless a later phase explicitly and
narrowly authorizes it:

- Mutate graph data automatically from any intelligence surface.
- Apply Dreaming suggestions without explicit user action.
- Implement decay calculations, a provenance engine, or query persistence ahead
  of their dedicated contract phase.
- Add AI/LLM integration (intelligence stays deterministic until a separately
  planned phase).
- Add ambient capture to the web UI.
- Redesign the dashboard, change branding/assets, or perform large CSS refactors.
- Add new dependencies casually.
- Break existing API wire shapes (changes must be additive).

These extend, and do not replace, the existing read-only guarantees of the
Knowledge Graph API and Console.

## Suggested next phase after 10A

**Phase 10B — Intelligence Contract Types / Read-Only Schemas.** Define the
shared TypeScript interfaces and Pydantic models for the intelligence surfaces
(Dreaming suggestion, decay status, provenance chain, query trail) as
*contract-only* shapes — mirroring how Phase 2 defined the API contract before
any logic. No endpoints, no logic, no persistence; just the agreed shapes that
10C+ will implement against.

See [roadmap.md](roadmap.md) for the full phased plan.
