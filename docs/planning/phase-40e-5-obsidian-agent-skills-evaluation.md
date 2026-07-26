# Phase 40E.5 — Obsidian Agent Skills Evaluation + Contract Alignment

**Status:** documentation / architecture / developer-agent tooling evaluation only —
implemented locally, pending independent audit and the devdevbuilds human merge gate.
**Type:** evaluation + policy phase. No backend, frontend, API, schema, persistence,
graph, Obsidian-import, dependency, package, or asset change. No screenshots.
**Relationship to the migration roadmap:** a **narrow parallel** evaluation. It does
**not** renumber, replace, supersede, or alter the approved Phase 40D.5–40K
memory-migration sequence. Phases 40A–40D remain completed foundations; memory
migration (Phase 40F active) remains the product-development direction.
**Baseline:** `60b9fc7cabb19939e501a341e29ce68acdceeb93` (`origin/main`).

Companion deliverables:

- [Obsidian Agent Skills Policy](../obsidian-agent-skills-policy.md)
- [Obsidian Format Compatibility Matrix](../obsidian-format-compatibility-matrix.md)

---

## 1. Objective

Evaluate the external open-source repository **kepano/obsidian-skills** against
Hive|Mind's existing Obsidian architecture and establish a canonical policy for
using those skills with development agents.

This phase does **not** create a new Obsidian integration. Hive|Mind already has an
established Obsidian foundation (adapter contract, import pipeline, import
hardening, Source Registry integration, frontend import surfaces, and Knowledge
Graph projection). The question here is narrower:

> Are the kepano/obsidian-skills useful as **developer-agent tooling and
> architectural reference material**, and under what rules — without becoming a
> Hive|Mind runtime dependency in this phase?

The evaluation answers the nine questions posed in the phase brief:

1. Which upstream skills are useful to Hive|Mind.
2. Which conventions align with existing Hive|Mind contracts.
3. Which conventions conflict with or duplicate Hive|Mind behavior.
4. Which skills should be approved for Claude Code / compatible agent use.
5. Which concepts should remain reference-only.
6. Whether JSON Canvas is a credible future bridge between the Knowledge Graph and
   Obsidian.
7. Whether Obsidian Bases has useful future applicability.
8. Whether Obsidian CLI should remain developer-agent tooling rather than
   application runtime infrastructure.
9. Whether Defuddle belongs in a separate future ingestion track.

---

## 2. Current Hive|Mind Obsidian architecture (as inspected)

This section records what actually exists in source, not README prose.

### 2.1 Adapter contract (Phase 6A)

- `apps/backend/app/adapters/obsidian.py` — `ObsidianVaultAdapter`, a **placeholder**
  adapter whose `discover()` **raises `NotImplementedError`**, plus
  `validate_obsidian_config()`, a pure, filesystem-free shape validator. It does
  **not** read vault files, scan the filesystem, parse markdown, or watch files.
- Contract models in `apps/backend/app/models/hive_models.py`:
  `ObsidianLinkStrategy` (`wikilink` / `markdown` / `both`), `ObsidianVaultConfig`
  (declared `root_path`, include/exclude patterns, `tag_prefix`, `link_strategy`),
  and `ObsidianDocumentCandidate` (the normalized shape an adapter *would* emit).

### 2.2 One-shot import pipeline (Phase 6B)

- `apps/backend/app/adapters/vault_scanner.py` — a **safe, read-only** scanner:
  `resolve_vault_root()` validates/normalizes an untrusted path into a single
  `ValueError` on bad input; `scan_markdown_files()` walks with `followlinks=False`,
  prunes hidden/system directories (`.obsidian`, `.git`, `node_modules`, any dotted
  dir), skips hidden files and symlinked files, and **never returns a path outside
  the vault root** (defensive `relative_to` check).
- `apps/backend/app/adapters/markdown_parser.py` — a **dependency-free** parser
  extracting a small normalized shape: title (frontmatter → first heading →
  fallback), a safe YAML-frontmatter subset (scalars, inline lists, block lists),
  tags (frontmatter + inline `#tag`), wikilinks (`[[Target|Alias]]`, `[[Target#Heading]]`
  reduced to the target), and markdown-link targets `[text](url)`. It has no
  dedicated semantics for embeds, callouts, block refs, comments, highlights,
  Mermaid, or LaTeX, but `![[embed]]` still matches the wikilink extractor and
  `![alt](url)` still matches the markdown-link extractor. No third-party
  markdown/YAML dependency is used.
- `apps/backend/app/services/obsidian_import.py` — `import_vault()`, a one-shot,
  **read-only-over-the-vault** import into the graph `HiveStore` and Source Registry.
  Node ids are **deterministic**: `obsidian-<sha1(relative_vault_path)[:12]>`, so
  re-importing the same vault **upserts** the same nodes. Per-file failures become
  counted warnings, never aborting the run; empty notes are skipped; a stable
  `ObsidianImportSummary` is returned. Wiki/markdown references are **captured on
  the node** (`metadata.wiki_links`, `metadata.markdown_links`) but **not yet
  materialized as edges** here.
- `apps/backend/app/routers/obsidian.py` — `POST /api/obsidian/import`; a bad path is
  a clean HTTP 400, per-file failures surface in the summary.

### 2.3 Knowledge Graph projection (Phase 8A)

- `apps/backend/app/services/knowledge_graph.py` — `build_knowledge_graph()`, a
  **pure, deterministic, read-only** projection of store state. Edges are the union
  of (a) persisted edges whose endpoints exist and (b) edges **derived** from
  captured Obsidian `wiki_links` that resolve (case-insensitively, by vault path /
  filename / label) to another node. Derived edges carry a deterministic id
  (`kg-edge-<sha1(...)[:12]>`), the marker `origin: knowledge_graph_builder`, and are
  **never written back to the store** — the builder accumulates no state.

### 2.4 Frontend + registry surfaces

- `apps/frontend/src/api/client.ts` exposes `importObsidianVault()` over
  `POST /obsidian/import`; `SourceRegistryPanel.tsx` surfaces Obsidian source
  visibility/actions. TypeScript mirrors live in `types/api.ts`.

### 2.5 Candidate-projection pattern already in the codebase (Phase 40E/40F)

The memory-migration track independently established the exact safety pattern this
evaluation recommends for any *future* Obsidian↔graph exchange: parsing produces
**inactive, unverified, human-review-required, non-persistable, provenance-linked
candidates** (`CANDIDATE_MEMORY_POLICY`), and parsing is treated as interpretation,
never verification, activation, or persistence. See
`apps/backend/app/services/memory_migration_projection.py` and
`apps/backend/app/models/memory_migration_projection.py`.

### 2.6 Architectural invariants that constrain any adoption

- **Read-only over user files.** Import never creates, modifies, or deletes a vault
  file. There is no watcher and no write-back.
- **Deterministic, dependency-free parsing.** No third-party markdown/YAML/canvas
  parser is a runtime dependency.
- **Stable, derived identity.** Obsidian node ids are hashes of stable
  vault-relative paths, while derived-edge ids hash stable endpoint/relationship
  inputs; re-runs address the same records.
- **Projection, not mutation.** The graph builder derives; it does not persist
  derived edges.
- **Explicit, one-shot, local, single-user.** No background sync, no network fetch,
  no shell execution in the request path.

---

## 3. Upstream repository summary

| Field | Value |
| --- | --- |
| Repository | `https://github.com/kepano/obsidian-skills` |
| Author | kepano (Steph Ango) |
| License | **MIT** |
| Format | Agent Skills specification (`skills/<name>/SKILL.md`) |
| Stated compatibility | Claude Code, Codex, Open Code |
| Skills | `obsidian-markdown`, `obsidian-bases`, `json-canvas`, `obsidian-cli`, `defuddle` |

The repository packages format knowledge and tool usage as agent skills. It is
**reference/tooling material**, not a library Hive|Mind imports. Treating it as
reference (documented syntax an agent already understands) is low-risk; wiring any
of its tools into the Hive|Mind runtime is the boundary this phase protects.

> **License note:** MIT permits reuse with attribution and license retention.
> This phase **does not vendor, copy, or redistribute** any upstream skill content.
> Skills, if adopted, are installed into an agent's own environment by the operator,
> not committed into this repository. Any future decision to vendor upstream text
> must retain the MIT license and attribution and is out of scope here.

---

## 4. Per-skill review

### 4.1 obsidian-markdown — **ADOPT FOR AGENT TOOLING**

Documents Obsidian Flavored Markdown: wikilinks (`[[Note]]`, aliases, headings,
block refs), embeds (`![[...]]`), callouts (`> [!type]`), YAML properties/frontmatter
(`title`, `date`, `tags`, `aliases`), inline/nested tags (`#tag`, `#nested/tag`),
comments (`%% %%`), highlights (`==text==`), LaTeX, Mermaid, footnotes.

- **Compatibility:** Strong overlap with what Hive|Mind's parser already extracts
  (frontmatter subset, tags, wikilink targets, markdown-link targets, and the first
  ATX heading as a title fallback). Useful as a reference so agents author/repair
  fixtures and docs in a form the existing parser handles cleanly.
- **Conflict/duplication:** The skill covers **more** syntax than the Hive|Mind
  parser extracts (embeds, callouts, block refs, comments, highlights, Mermaid,
  LaTeX). That is a **known parser scope gap**, not a defect — the parser is
  intentionally minimal. The risk is an agent assuming Hive|Mind *ingests* those
  constructs. It has no dedicated semantics for them; however, an embed target is
  still captured by the wikilink extractor and a Markdown image target by the
  markdown-link extractor.
- **Decision:** Approve as reference + authoring aid. Do **not** treat it as a spec
  Hive|Mind must implement. Record the parser scope gaps as deferred (see §9).

### 4.2 obsidian-bases — **FUTURE CONTRACT CANDIDATE / REFERENCE ONLY**

`.base` files are YAML database-like views (filters, formulas, views, summaries)
over note properties and file metadata; they do not modify source notes.

- **Compatibility:** Conceptually adjacent to a future *query/view* surface over the
  Knowledge Graph, but Hive|Mind has no `.base` producer or consumer today and the
  graph is not a property-table model.
- **Conflict/duplication:** None currently — nothing overlaps. Adopting Bases as a
  runtime format would introduce a second query model competing with the graph
  projection.
- **Decision:** Reference only now; **future contract candidate** if Hive|Mind ever
  wants to export saved graph views to Obsidian. No runtime work.

### 4.3 json-canvas — **REFERENCE ONLY (strong future-bridge candidate)**

JSON Canvas 1.0: `.canvas` files with `nodes` (`text`/`file`/`link`/`group`) and
`edges`. See the dedicated assessment in §6.

- **Compatibility:** The clearest structural match to the Knowledge Graph
  (nodes and edges). Canvas groups are visual containers; Hive|Mind has no
  graph-group contract today. This remains a credible **future** bidirectional
  bridge.
- **Conflict/duplication:** JSON Canvas ids are "unique 16-char hex" with no defined
  stability/provenance semantics; Hive|Mind ids are deterministic content/path
  hashes. Naively adopting Canvas identity would **break** Hive|Mind's idempotence
  and provenance guarantees.
- **Decision:** Reference only in this phase. Document the mapping and risks (§6) so a
  future phase can build a deterministic projection/parse pair correctly. **Do not
  implement either direction now.**

### 4.4 obsidian-cli — **ADOPT FOR AGENT TOOLING (developer/operator only) — NEVER RUNTIME**

Invokes the `obsidian` CLI binary against a **running** Obsidian instance. It can
**mutate vault files** (create/append/`property:set`), run **JavaScript in the app
context**, take screenshots/DOM snapshots, and reload plugins — all via **shell
invocation**. See §7.

- **Compatibility:** None as application infrastructure. It is a developer/operator
  tool, not a deterministic backend service.
- **Conflict/duplication:** Directly conflicts with core invariants — it mutates user
  vaults, executes arbitrary JS, and requires shell execution. Wiring it into the
  backend would violate read-only-over-vault, determinism, and no-shell-execution
  guarantees simultaneously.
- **Decision:** Permitted only as **developer-agent tooling under explicit,
  per-action human confirmation**, and **never** wired into the Hive|Mind backend,
  API, or any request path. See the policy's "controlled developer use" rules.

### 4.5 defuddle — **DEFER (separate future ingestion track)**

npm package `defuddle` (`npm install -g defuddle`) that fetches a URL over the
**network** and extracts clean markdown.

- **Compatibility:** A possible *future* web-ingestion helper, unrelated to the
  Obsidian **vault** adapter. It requires **dependency installation** and **network
  access**, both prohibited here.
- **Conflict/duplication:** Overlaps conceptually with a future source/ingestion
  adapter, **not** with the Obsidian adapter. Placing it under the Obsidian track
  would miscategorize it.
- **Decision:** **Defer** to a future **ingestion / source-adapter** phase, gated by
  the same intake-safety boundary the memory-migration track uses. Do not integrate.

---

## 5. Compatibility findings, conflicts, and duplication (summary)

| Theme | Finding |
| --- | --- |
| Markdown syntax | Upstream documents a **superset** of what the Hive|Mind parser extracts. Alignment is good for authoring; unsupported semantics are a documented deferred scope gap, not a contract conflict. Embed targets and Markdown image targets are still captured by the parser's broad link regexes. |
| Frontmatter/properties | Both use YAML frontmatter with `tags`/`title`/`aliases`. Hive|Mind reads a **safe subset**; the skill assumes full YAML. Agents must not assume Hive|Mind ingests arbitrary YAML structures. |
| Wikilinks | Consistent (`[[Target|Alias]]`, `[[Target#Heading]]`). Hive|Mind resolves them case-insensitively by path/filename/label in the graph builder. Strong alignment. |
| Identity | **Primary conflict.** Canvas/CLI assume opaque or app-managed ids; Hive|Mind requires deterministic, content/path-derived, idempotent ids with provenance. |
| Mutation | **Primary conflict.** obsidian-cli mutates vaults; Hive|Mind import is read-only over the vault with no write-back. |
| Dependencies | defuddle requires a global npm install; Hive|Mind parsing is dependency-free. |
| Query/view model | Bases introduces a second query model; Hive|Mind uses graph projection. No overlap today; potential future divergence. |

---

## 6. JSON Canvas assessment (bidirectional)

Neither direction is implemented in this phase. This documents the design so a
future phase can build it deterministically and safely.

### 6.1 Export direction — Knowledge Graph → JSON Canvas → Obsidian

```
Hive|Mind Knowledge Graph
        ↓  deterministic projection service (pure, read-only)
JSON Canvas document (.canvas)
        ↓
Obsidian Canvas
```

- **Node mapping:** each `HiveGraphNode` → a Canvas `node`. A `NOTE` node backed by a
  vault file maps naturally to a `file` node (`file` = vault-relative path, optional
  `subpath` for a heading); nodes without a file map to a `text` node carrying a
  bounded label/summary. `x`/`y`/`width`/`height` are **layout**, not knowledge — a
  deterministic layout function (e.g., derived from a stable ordering) must generate
  them so repeated exports are identical.
- **Edge mapping:** each `HiveGraphEdge` (including derived `references` edges) → a
  Canvas `edge` with `fromNode`/`toNode`. Relationship type maps to `label` and/or
  `color`; direction maps to `toEnd: arrow`.
- **Group mapping:** Hive|Mind has no graph-group contract. A future exporter may
  derive optional visual Canvas `group` nodes from existing node fields (for
  example source, tag, or type), but that is presentation metadata, not graph
  structure or a knowledge fact, and must be deterministic.
- **Stable identity concern:** Canvas ids are "unique 16-char hex". A compliant export
  must derive each Canvas id **deterministically** from the stable Hive|Mind id
  (e.g., a hash truncated/encoded to 16 hex chars) with explicit collision handling,
  so the same graph always exports byte-stable Canvas ids. Random ids would break
  round-trips and diffs.
- **Provenance:** the export is a **projection**, never authority. It must not be
  written back into the store, and the exported file should carry a provenance marker
  (analogous to `origin: knowledge_graph_builder`) so a later import recognizes
  Hive|Mind-originated content.
- **Mutation safety:** export **writes a new artifact**; it must never modify an
  existing user Canvas in place without explicit human confirmation, and must respect
  the same read-only-over-user-files posture as import (write only to an
  explicitly-chosen output path).
- **Determinism:** pure function of store state + a deterministic layout; identical
  store state ⇒ identical `.canvas` bytes.

### 6.2 Import direction — Obsidian Canvas → candidates → review → Knowledge Graph

```
Obsidian Canvas (.canvas)
        ↓  safe deterministic parser (bounded, read-only)
normalized relationship candidates
        ↓  human review / validation
        ↓
Hive|Mind Knowledge Graph
```

- **Node mapping:** Canvas `file` nodes resolve to existing graph nodes by
  vault-relative path (reusing the graph builder's resolver keys); `text`/`link`
  nodes become **candidate** nodes, never authoritative ones.
- **Edge mapping:** Canvas `edges` become **candidate relationships**, mirrored on the
  memory-migration candidate pattern: **inactive, unverified, human-review-required,
  provenance-linked**, and non-persistable until an approved phase.
- **Group mapping:** groups become advisory grouping hints on candidates, not
  authoritative structure.
- **Stable identity concern:** inbound Canvas ids are **untrusted** and must not
  become Hive|Mind ids. The parser derives its own deterministic candidate ids
  from normalized semantics plus stable source-artifact identity and a deterministic
  occurrence discriminator. Source Canvas-local ids are recorded as provenance only,
  never used as canonical Hive|Mind identity; two duplicate semantic mappings must
  remain separately reviewable rather than collapsing accidentally.
- **Provenance:** every candidate records that it originated from a specific Canvas
  file (path + source node/edge ids) so review is auditable.
- **Import/export boundary:** the parser is byte-in / candidate-out. It **persists
  nothing** and **inserts nothing** into the graph or Active Memory. Reviewed
  persistence is a separate, human-gated phase.
- **Mutation safety:** parsing a Canvas never mutates the Canvas, the store, or the
  graph. It fails closed on malformed input (bounded, typed errors), following the
  vault-scanner/parser precedent.
- **Unknown/unsupported constructs:** a future parser must apply an explicit,
  versioned policy. Unknown fields and unsupported node/edge constructs are either
  retained as bounded provenance for review or rejected with typed diagnostics;
  they are never silently promoted to knowledge, silently discarded in a claimed
  lossless round-trip, or allowed to drive graph action.
- **Round-trip risks:** export→edit→import can drift (layout coordinates carry no
  meaning, ids may be regenerated by Obsidian, users may hand-edit). The design must
  treat inbound Canvas as **candidates requiring review**, never as a source of truth
  that silently overwrites graph state. Coordinates and colors are **not** knowledge
  and must never be promoted to relationships.

### 6.3 JSON Canvas verdict

JSON Canvas is a **credible future bridge** in both directions **only** if built on
Hive|Mind's existing guarantees: deterministic derived identity, projection (not
mutation) on export, and the candidate/review boundary on import. It is the single
most promising upstream concept for future work. **It is reference-only now.**

---

## 7. Obsidian CLI trust-boundary assessment

| Dimension | Finding |
| --- | --- |
| Command execution trust boundary | Runs the external `obsidian` binary via **shell invocation** against a live app instance. This is outside Hive|Mind's allowlisted, shell-free command posture (cf. the Phase 37J Git adapter, which is allowlisted and shell-free). |
| Filesystem access | Full read/write access to the targeted vault. |
| Mutation capabilities | **Mutates** vault files: create, append, `property:set`. Can also run arbitrary **JavaScript in the app context** and reload plugins. |
| User confirmation requirements | The upstream skill states no permission restrictions. Hive|Mind policy therefore imposes its own: **explicit, per-action human confirmation** for any mutating or JS-executing command. |
| Deterministic behavior | Not deterministic in the Hive|Mind sense — it depends on live app state, plugins, and timing. Unsuitable as a backend service. |
| Agent permissions | Permitted only as a **developer/operator** aid under human confirmation. Never invoked from the backend, API, or any request path. |

**Verdict:** Obsidian CLI stays **developer-agent/operator tooling**, never
application runtime infrastructure. Do not wire CLI execution into the Hive|Mind
backend.

---

## 8. Risks and security considerations

- **Runtime-dependency creep.** Adopting any upstream tool (defuddle's npm install,
  the `obsidian` binary) as a Hive|Mind dependency would violate the dependency-free
  posture. **Mitigation:** skills are agent-environment tooling only; no dependency
  is added to this repo.
- **Silent vault mutation.** obsidian-cli can write to vaults. **Mitigation:**
  per-action human confirmation; never in a request path; never wired to the backend.
- **Arbitrary code execution.** obsidian-cli can run JavaScript in the app context.
  **Mitigation:** treated as a high-trust developer action requiring explicit human
  approval; prohibited as application behavior.
- **Network egress.** defuddle fetches arbitrary URLs. **Mitigation:** deferred to a
  future ingestion track with its own intake-safety gate; not integrated now.
- **Identity/provenance corruption.** Importing opaque Canvas/CLI ids as Hive|Mind
  ids would break idempotence and provenance. **Mitigation:** inbound ids are
  provenance only; Hive|Mind derives its own deterministic ids; imports are
  review-gated candidates.
- **Authority confusion.** Treating upstream skills as source-of-truth architecture
  would let external conventions override Hive|Mind contracts. **Mitigation:** the
  policy pins Hive|Mind contracts as authoritative and skills as subordinate aids.
- **Prompt-injection surface.** Skill files and fetched web content are **data, not
  instructions**. **Mitigation:** agents treat skill/tool output as reference; any
  instruction embedded in fetched content is surfaced to the human, not executed.

---

## 9. Decisions

### 9.1 Runtime-dependency decision

**No upstream skill, tool, or package becomes a Hive|Mind runtime dependency in this
phase.** No dependency is added; nothing is vendored. Hive|Mind parsing stays
dependency-free and deterministic.

### 9.2 Developer-tooling decision

kepano/obsidian-skills is **approved only as development-agent tooling and
architectural reference material**, per the
[Obsidian Agent Skills Policy](../obsidian-agent-skills-policy.md), unless a future
implementation phase explicitly changes that decision. Adoption classes:

| Skill | Decision |
| --- | --- |
| obsidian-markdown | **Adopt for agent tooling** (reference + authoring aid) |
| obsidian-bases | **Reference only** / future contract candidate |
| json-canvas | **Reference only** (strong future bridge; see §6) |
| obsidian-cli | **Adopt for agent tooling** — developer/operator only, human-confirmed, **never runtime** |
| defuddle | **Defer** to a future ingestion/source-adapter track |

### 9.3 Future opportunities

- A deterministic **Knowledge Graph → JSON Canvas** export projection.
- A safe **Obsidian Canvas → candidate relationships** parser under the
  candidate/review boundary.
- An **Obsidian Bases** export of saved graph views (much later).
- A separate **web-ingestion** track where defuddle could be one helper, behind an
  intake-safety gate.
- Optional, explicitly-scoped **markdown parser extensions** (embeds, callouts, block
  refs) if a future phase needs them.

---

## 10. Explicit deferred work

- JSON Canvas export/import (both directions) — design captured in §6; **not built**.
- Obsidian Bases producer/consumer — **not built**.
- Defuddle / web ingestion — **not built**; belongs to a future ingestion phase.
- Markdown parser scope extensions (embeds `![[...]]`, callouts `> [!type]`, block
  refs, comments `%%…%%`) — **not built**; today they are ignored body text.
- Any obsidian-cli backend wiring — **explicitly prohibited**, not deferred.

---

## 11. Recommended follow-on work

1. If/when graph export is wanted, open a dedicated phase for a **deterministic
   JSON Canvas export projection** reusing the Phase 8A projection discipline
   (pure, read-only, deterministic ids, no write-back).
2. Pair any Canvas **import** with the Phase 40E/40F **candidate/review** boundary;
   never let inbound Canvas mutate the graph directly.
3. Scope Defuddle under a future **ingestion/source-adapter** phase with an
   intake-safety assessor analogous to `MemoryMigrationIntakeAssessor`.
4. Keep obsidian-cli in operator runbooks only; if any automation is ever wanted,
   require per-action human confirmation and keep it out of the backend.
5. Revisit markdown parser scope gaps only when a concrete product need appears.

---

## 12. Validation

- Documentation-only phase: three new docs under `docs/`, plus narrow, accurate
  additions to `README.md` and `docs/roadmap.md` recording this evaluation/policy.
- No backend, frontend, API, schema, persistence, graph, Obsidian-import,
  dependency, package, or asset file changed.
- No upstream skill content vendored or copied. Upstream URL and MIT license
  recorded (§3).
- No screenshots captured; no evidence invented.

---

## 13. Canonical statement

> **kepano/obsidian-skills is approved only as development-agent tooling and
> architectural reference material unless a future implementation phase explicitly
> changes that decision. Hive|Mind contracts remain authoritative; external agent
> skills are subordinate development aids.**
