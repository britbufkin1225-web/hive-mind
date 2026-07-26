# Obsidian Format Compatibility Matrix

**Status:** canonical reference (Phase 40E.5). Maps each **kepano/obsidian-skills**
skill to the relevant Hive|Mind system, its compatibility, and an adoption decision.
**Upstream:** `https://github.com/kepano/obsidian-skills` — MIT license, author
kepano (Steph Ango).
**Companions:**
[Phase 40E.5 evaluation](planning/phase-40e-5-obsidian-agent-skills-evaluation.md) ·
[Agent skills policy](obsidian-agent-skills-policy.md).

## Classification legend

| Class | Meaning |
| --- | --- |
| **ADOPT FOR AGENT TOOLING** | Approved for development-agent use (reference / authoring / validation / controlled developer tooling). Not runtime. |
| **REFERENCE ONLY** | Read for understanding/design. No producer/consumer in Hive|Mind now. |
| **DEFER** | Out of scope now; revisit in a specific future track. |
| **FUTURE CONTRACT CANDIDATE** | A plausible future Hive|Mind contract/format, not yet designed or approved. |
| **NOT APPLICABLE** | No current or near-term Hive|Mind relevance. |

**Runtime status** is `NONE` for every skill in this phase: nothing here is wired into
Hive|Mind runtime, and no dependency is added or vendored.

---

## Matrix

### obsidian-markdown

| Field | Value |
| --- | --- |
| Upstream purpose | Create/edit Obsidian Flavored Markdown: wikilinks, embeds `![[...]]`, callouts `> [!type]`, YAML properties, tags `#tag`/`#nested/tag`, comments `%%…%%`, highlights, LaTeX, Mermaid, footnotes. |
| Relevant Hive|Mind system | `apps/backend/app/adapters/markdown_parser.py` (dependency-free parser) and the Obsidian import pipeline (`vault_scanner.py`, `obsidian_import.py`). |
| Compatibility | **High for the subset Hive|Mind reads** (frontmatter subset, tags, wikilinks, markdown links, headings). Upstream documents a **superset**; the extra constructs are ignored body text today. |
| Adoption decision | **ADOPT FOR AGENT TOOLING** — reference + authoring/validation aid. |
| Runtime status | NONE. |
| Future opportunity | Optional, explicitly-scoped parser extensions (embeds, callouts, block refs) if a product need appears. |
| Risks / constraints | Agents must not assume Hive|Mind ingests every documented construct; do not introduce a new markdown parser or a third-party markdown/YAML dependency. |

### obsidian-bases

| Field | Value |
| --- | --- |
| Upstream purpose | `.base` (YAML) database-like views over notes: filters, formulas, views (table/cards/list/map), summaries; references frontmatter + file metadata; does not modify source notes. |
| Relevant Hive|Mind system | None today. Conceptually adjacent to a future saved-view/query surface over the Knowledge Graph. |
| Compatibility | Low today — Hive|Mind has no `.base` producer/consumer and the graph is not a property-table model. |
| Adoption decision | **REFERENCE ONLY** (also a **FUTURE CONTRACT CANDIDATE** for exporting saved graph views). |
| Runtime status | NONE. |
| Future opportunity | Export saved Knowledge Graph views as `.base` for Obsidian, much later. |
| Risks / constraints | Adopting Bases as a runtime format would introduce a second query model competing with graph projection. No runtime work without an approved phase. |

### json-canvas

| Field | Value |
| --- | --- |
| Upstream purpose | JSON Canvas 1.0 `.canvas` files: `nodes` (`text`/`file`/`link`/`group`) + `edges`; ids are "unique 16-char hex"; colors `1`–`6` or hex. |
| Relevant Hive|Mind system | `apps/backend/app/services/knowledge_graph.py` (nodes/edges/groups projection) and `HiveGraphNode`/`HiveGraphEdge` contracts. |
| Compatibility | **Structurally the closest match** to the Knowledge Graph. Credible **future bidirectional bridge**. |
| Adoption decision | **REFERENCE ONLY** now (strong future bridge; full design in the evaluation §6). |
| Runtime status | NONE. |
| Future opportunity | Deterministic **graph → Canvas** export projection; safe **Canvas → candidate relationships** parser under the candidate/review boundary. |
| Risks / constraints | Canvas ids carry no stability/provenance semantics — they must never become Hive|Mind ids; layout coordinates/colors are not knowledge; export must project (never write back), import must produce review-gated candidates; round-trips can drift. |

### obsidian-cli

| Field | Value |
| --- | --- |
| Upstream purpose | Command-line control of a **running** Obsidian instance: read/create/append notes, set properties, search, backlinks/tags, run JavaScript in app context, screenshots/DOM, reload plugins — via **shell invocation**. |
| Relevant Hive|Mind system | None as infrastructure. Comparable in spirit to the Phase 37J Git adapter, but that adapter is allowlisted and **shell-free**; the Obsidian CLI is neither. |
| Compatibility | **Incompatible as application infrastructure** — mutates vaults, executes arbitrary JS, requires shell + a live app. |
| Adoption decision | **ADOPT FOR AGENT TOOLING** — developer/operator only, human-confirmed for any mutation/JS/plugin-reload; **NOT APPLICABLE as runtime**. |
| Runtime status | NONE — **never** wired into backend, API, or any request path. |
| Future opportunity | Operator runbooks only. Any automation would still require per-action human confirmation and stay out of the backend. |
| Risks / constraints | Vault mutation, arbitrary code execution, shell execution, non-determinism, dependence on live app state. Do not wire CLI execution into Hive|Mind. |

### defuddle

| Field | Value |
| --- | --- |
| Upstream purpose | npm package `defuddle` (`npm install -g defuddle`): fetches a URL over the network and extracts clean markdown (`defuddle parse <url> --md`). |
| Relevant Hive|Mind system | None. A possible **future web-ingestion** helper — unrelated to the Obsidian **vault** adapter. |
| Compatibility | Not compatible now — requires **dependency installation** and **network access**, both prohibited in this phase and outside the Obsidian adapter's scope. |
| Adoption decision | **DEFER** to a future ingestion / source-adapter track. |
| Runtime status | NONE. |
| Future opportunity | One candidate web-ingestion helper behind an intake-safety gate analogous to `MemoryMigrationIntakeAssessor`. |
| Risks / constraints | Global npm install; arbitrary network egress; miscategorization if placed under the Obsidian adapter. Do not integrate now. |

---

## Decision summary

| Skill | Class | Runtime | Future track |
| --- | --- | --- | --- |
| obsidian-markdown | ADOPT FOR AGENT TOOLING | NONE | Optional parser-scope extensions |
| obsidian-bases | REFERENCE ONLY / FUTURE CONTRACT CANDIDATE | NONE | Graph-view export (later) |
| json-canvas | REFERENCE ONLY | NONE | Graph↔Canvas bridge (both directions) |
| obsidian-cli | ADOPT FOR AGENT TOOLING (dev/operator only) | NONE | Operator runbooks only; never runtime |
| defuddle | DEFER | NONE | Web-ingestion / source-adapter track |

**Canonical constraint:** every classification above is bounded by the
[Agent Skills Policy](obsidian-agent-skills-policy.md). Hive|Mind contracts remain
authoritative; these skills are subordinate development aids. No item here adds a
runtime dependency, mutation, watcher, shell execution, or persistence in Phase
40E.5.
