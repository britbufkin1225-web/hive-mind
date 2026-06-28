# Phase 17A - Intelligence Report Cohesion + System Readiness Plan

Parent label: **devdevbuilds**

Phase 17A is a **documentation/planning-only** phase. It does not add backend
logic, frontend components, endpoints, contracts, schema, persistence, or
dependencies. It evaluates the Intelligence Report as a whole now that its first
full pass of surfaces is backend-derived and frontend-visible, and it prepares
the project for the next stage of intelligence work.

## Why cohesion comes before more implementation

Hive|Mind has just finished building out four intelligence surfaces in sequence:
Temporal Knowledge Decay (Phase 13A-13C), Dreaming Suggestions (Phase 14A-14E),
Provenance Chains (Phase 15A-15E), and Query Trails (Phase 16A-16C). Each was
shipped contract-first, then backend-derived, then made frontend-visible. The
Intelligence Report panel now carries enough read-only intelligence surface area
that the next correct move is **alignment, not addition**.

Adding a fifth moving part before aligning the four that exist would let
terminology, readiness criteria, demo framing, and documentation drift apart.
This phase aligns those before the next feature so future phases inherit a
coherent system instead of a pile of independently-correct parts. Boring and
correct: architecture wearing a seatbelt.

**Why this supports Hive|Mind as a real dev-tool product, not just a portfolio
asset:** a developer tool earns trust by being consistent about what it knows and
honest about what it does not. A cohesion pass keeps terminology, provenance
labeling, and readiness honest across every surface, which is what makes the
intelligence layer usable for real knowledge organization, workflow speed, and
unified development coordination rather than a demo that looks smart once.

## 1. Intelligence Report cohesion

### How the four surfaces relate

The Intelligence Report is a single read-only projection over the same store and
source-registry state the rest of the app reads. The four surfaces are different
**lenses on the same graph**, not independent subsystems:

- **Temporal Decay** answers *how fresh is this knowledge?* (time lens).
- **Dreaming Suggestions** answers *what looks wrong or worth reviewing?*
  (hygiene lens).
- **Provenance Chains** answers *where did this knowledge come from?*
  (lineage lens).
- **Query Trails** answers *what does looking-up activity reveal about gaps and
  follow-ups?* (navigation lens).

They share design DNA: deterministic pure functions over current store state,
read-only output, backend-owned `metadata.evidence`, a clean empty section when
nothing is derivable, and no AI/LLM. They also reference each other by id rather
than by copying: Query Trails can point at the nodes/sources/provenance a lookup
touched, Dreaming can point at stale links that overlap with Temporal Decay's
time signals, and Provenance is the shared evidence trail the other lenses link
back to.

### What each surface currently does

| Surface | Derives | First derived | Status |
| --- | --- | --- | --- |
| Temporal Decay | `fresh` / `aging` / `stale` (implicit `unknown`) buckets from node/source timestamps via deterministic thresholds (<= 30d, <= 90d, else stale). | Phase 13A | Backend-derived, read-only |
| Dreaming Suggestions | `duplicate` (shared normalized label), `orphan` (no edges/source/parent), `stale` (old link whose endpoint changed since), each with `confidence_hint` and evidence. | Phase 14C | Backend-derived, read-only |
| Provenance Chains | source -> import -> node -> edge chains from existing source/import/node/edge records, with backend-owned evidence. | Phase 15C | Backend-derived, read-only |
| Query Trails | `source_followup` (source with linked nodes), `knowledge_gap` (unsourced node / uncovered source), `related_query_cluster` (2+ nodes sharing a tag), with evidence. | Phase 16C | Backend-derived, read-only |

### What each surface intentionally does *not* do yet

- **Temporal Decay** — no graph overlays/tints, no richer reference/last-seen
  signals beyond existing timestamps; indicators are advisory only.
- **Dreaming Suggestions** — no `source_coverage_gap` (deferred by the pinned
  Phase 14B contract decision), no `unresolved_query` (blocked on query history),
  no related-node/missing-backlink/source-conflict inference, and no "apply"
  action that would write graph data.
- **Provenance Chains** — no semantic lineage inference beyond stored
  source/import/node/edge records, no selected-node inspector extension, no
  per-section error state.
- **Query Trails** — no `repeated_query` / `unresolved_question` derivation
  (blocked: Hive|Mind persists no query history), no query capture/logging, no
  pinning/saving controls.

### Which surfaces are backend-derived / read-only

**All four**, as of Phase 16C. No Intelligence Report section is fixture-backed
anymore. Every section is a deterministic read-only projection of store/source
state, tagged with derived evidence, returning cleanly empty when nothing is
derivable. The endpoint (`GET /api/intelligence/report`) performs no mutation,
no persistence, and no AI/LLM calls.

### Deferred capabilities still blocked by missing foundations

| Deferred capability | Blocked on | Lens |
| --- | --- | --- |
| Query Trail `repeated_query` / `unresolved_question` | Persisted local query history | Navigation |
| Dreaming `unresolved_query` pattern | Persisted local query history | Hygiene |
| Dreaming `source_coverage_gap` | A future additive contract-expansion phase (Phase 14B intentionally omitted the enum) | Hygiene |
| Provenance selected-node inspector + per-section error state | Frontend inspector extension (out of scope for derivation phases) | Lineage |
| Temporal Decay graph overlays / richer last-seen signals | Graph-overlay rendering work + richer reference signals | Time |
| Confidence / uncertainty badges (Tier 2) | A confidence model that does not yet exist | All |

The common foundation gap is **persistence**: the two query-history-dependent
capabilities cannot be honest until Hive|Mind actually records query activity.
Fabricating query-memory records would violate the layer's "no demo data
presented as real intelligence" guarantee.

## 2. System readiness review

### Stable enough for demo / read-only presentation

- The full Intelligence Report panel: all four sections render backend-derived
  content with clean empty states.
- `GET /api/intelligence/report` as a deterministic, read-only endpoint.
- The shared contract types and `metadata.evidence` convention across surfaces.
- The surrounding read-only foundation (store, Source Registry, Obsidian import,
  Knowledge Graph API + SVG panel, Console).

### Should be hardened before the next backend intelligence implementation

- **Cross-surface evidence consistency** — confirm `metadata.evidence`
  field naming (`node_ids`, `source_ids`, `edge_ids`, `reason`, `derivation`,
  `fields_used`) is uniform across all four derivers so future surfaces copy one
  shape, not four near-variants. *(Audit/doc task; no code change in 17A.)*
- **Empty-state parity** — confirm every section renders an honest empty state,
  not a hidden section, when nothing is derivable.
- **Terminology lock** — pick one canonical name per surface and per category and
  use it everywhere (see drift list below).
- **Derivation determinism notes** — ensure each surface documents its inputs and
  thresholds so reviewers can reproduce output from store state.

### Terminology / docs / expectation drift to correct

Phase 17A corrects the following stale language as part of its roadmap/README
alignment (item 5):

- **README active phase was stale** — it read "Phase 16B" while 16C had merged.
- **Query Trails described as fixture-backed** — README overview/status,
  the roadmap, and the Intelligence Surface Plan still described Query Trails as
  demo/seed fixtures after Phase 16C made them backend-derived.
- **Roadmap active phase** — listed Phase 16C as "Planned / Active" after it
  merged.
- **"Partially backend-derived"** — the Intelligence Report is now *fully*
  backend-derived (read-only); language implying a remaining fixture section is
  stale.

Honest-language rule for future phases: *implemented* means merged and exercised;
*planned* means scoped but not built; *deferred* / *blocked* must name the
missing foundation; any remaining fixture/demo data must stay explicitly labeled.

## 3. Next-phase planning

**Recommended next major phase (Phase 17B candidate): an Intelligence Report
cohesion-hardening + cross-surface evidence/contract consistency pass —
conservative, foundation-first, and still derivation-only.** Concretely, the
recommended next step is to do the smallest implementation work that makes the
*existing* four surfaces more uniform and robust before any new surface is added:
align `metadata.evidence` shapes, confirm empty-state parity, and add a shared
summary-rollup readiness check — not a new intelligence engine.

The first net-new capability after that should be the one with the clearest
foundation: **a dedicated, conservative local query-persistence foundation
phase** (planning-first, mirroring how 16A preceded 16B/16C), because two
separate deferred capabilities (`repeated_query` / `unresolved_question` and
Dreaming's `unresolved_query`) are both blocked on the same missing foundation.
Unblocking one foundation unblocks two lenses.

**What not to do next:** do not jump into flashy logic — no AI/LLM, no
embeddings, no semantic provenance inference, no confidence model, no graph
overlays — none of those are justified by the current readiness state. The docs
do not yet show the system is ready for them, so they stay Tier 2 / future.

## 4. Rationale notes ("why")

- **Why cohesion-hardening before a new surface:** four surfaces built in
  sequence accumulate small inconsistencies. Locking evidence shape and
  terminology once is cheaper than reconciling five later, and it keeps the
  intelligence layer's provenance trustworthy — the core value proposition for a
  dev tool is *consistent, inspectable knowledge*, not feature count.
- **Why query persistence is the next foundation, not a feature:** it is the
  single blocker behind two deferred capabilities. Building the foundation first
  (with privacy/retention boundaries already drafted in Phase 16A) means later
  query features ship honestly instead of via fixtures. This directly serves
  workflow speed and developer productivity: query memory turns repeated
  investigation into reusable entry points back into the graph.
- **Why no AI/LLM yet:** the layer's standing guardrail is deterministic before
  clever. Deterministic derivation is reviewable and reproducible from store
  state; an LLM layer added now would make the report's output unverifiable and
  undercut data-provenance honesty. AI stays a separately-planned future phase.
- **Why read-only stays the default:** every surface observes and suggests; none
  mutate the graph. This keeps Hive|Mind safe to point at real knowledge and is
  what lets it act as unified development coordination without risking the
  authoritative store.
- **Why honest labeling matters commercially:** a dev tool that conflates demo
  data with real output cannot be trusted for organization or knowledge
  consistency. The fixture-to-derived transition (now complete for all four
  surfaces) is the credibility that turns this from a portfolio asset into a tool
  someone would actually run against their own vault.

## 5. Roadmap / README alignment performed in 17A

- `docs/roadmap.md` — set active phase to 17A, mark Phase 16C complete, add the
  17A row, and add an intelligence-cohesion note.
- `README.md` — correct the stale active phase, describe the Intelligence Report
  as fully backend-derived (Query Trails included), and add the 17A entry.
- `docs/intelligence-surface-plan.md` — update the Query Trails / status language
  that still described that surface as fixture-only.

See those files for the applied changes. No application behavior is modified by
this phase.

## Guardrails honored

This phase added **no** backend intelligence logic, frontend components, UI/CSS
redesigns, endpoints, contract/schema changes, persistence/database changes,
query logging, AI/LLM, embeddings, graph/source/store mutation, Obsidian
watcher/live sync, dependencies, or branding/assets changes. It is planning and
documentation only.
