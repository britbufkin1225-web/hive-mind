<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

## Overview

Hive|Mind is a **local-first developer knowledge and coordination tool**. It
connects knowledge sources — starting with Obsidian vault content — into a
normalized backend data model and presents that model through a focused web
interface: a source registry, an import workflow, a query console, a read-only
knowledge graph view, and an intelligence report whose four sections (Temporal
Decay, Dreaming Suggestions, Provenance Chains, and Query Trails) are all
backend-derived and read-only.

It is built to improve everyday development work — organization, data provenance,
workflow speed, knowledge consistency, source tracking, and development
coordination — on top of a human-reviewed agent workflow and safer project memory
and reasoning surfaces. It is also a deliberately scoped backend/cybersecurity
portfolio project, and the two goals reinforce each other: the discipline that
makes it a credible portfolio piece (deterministic logic, read-only surfaces,
honest scope) is the same discipline that makes it a trustworthy tool.

> **What it is, in one line:** Hive|Mind is a local-first developer knowledge
> intelligence dashboard that organizes imported knowledge sources, visualizes
> their relationships, and derives deterministic, read-only intelligence signals —
> temporal decay, dreaming suggestions, provenance chains, and query trails — from
> existing structure rather than from any AI/LLM call.

The conceptual model is deliberately simple:

- **Obsidian** is the human writing and thinking layer, where notes, links, and
  ideas are authored.
- **Hive|Mind** is the layer above it: the registry, normalization, graph, and
  analysis surface that turns that writing into structured, queryable knowledge.

Obsidian is where you think; Hive|Mind is where that thinking becomes a graph you
can inspect and, over time, reason about.

**Agent-assisted, human-reviewed.** Hive|Mind's development is agent-assisted but
human-reviewed. Agents may propose structure, documentation, implementation, or
analysis; **devdevbuilds remains the human decision-maker and merge gate.** The
project intentionally relies on deterministic backend logic and read-only
intelligence surfaces *before* any mutation or automation — agents help draft,
humans decide what ships.

## Current status

The project has moved beyond the initial foundation. The original Phase 1 app
shell is complete and has been built on through local JSON-backed backend
storage, the Hive Console, the Source Registry, the Obsidian import pipeline,
the Knowledge Graph API, and the read-only Knowledge Graph panel with its custom
SVG visualization.

- **Active phase:** `Phase 22C - UI Navigation QA + Screenshot Evidence Refresh`
  (QA / evidence / documentation only). Phase 22C re-ran the local backend (`8787`)
  and frontend (`5173`) and captured honest screenshot/runtime evidence that the
  **Phase 22B** single-page section navigation is **present and usable** over the
  connected dashboard: a sticky section nav (Overview · Status · Vault · Sources ·
  Graph · Intelligence · Console), stable `id` anchors on every top-level surface,
  the scrollspy active-section highlight, and the skip link. The directly exercised
  endpoints returned the same shapes/values as Phase 21C/21F (health `0.1.0`; graph
  7 nodes / 6 edges; Intelligence Report Dreaming `0` / Decay `7` / Provenance `7` /
  Query Trails `7`), confirming **no backend/API/schema behavior changed** (22B was
  frontend-only), and `npm run check:frontend` passes. A new `phase-22c-connected-*`
  screenshot set records the sticky nav and its active-section highlight on every
  major surface — including the honest scrollspy edge behavior at the page top and
  bottom — while preserving the `phase-21f-*` history. It changes no application
  behavior. See the
  [Phase 22C UI Navigation QA + Screenshot Evidence Refresh](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md).
  The preceding **Phase 22B** implemented the locked navigation model as a
  **frontend-only** pass (PR #80): the sticky in-page section nav, `id` anchors on
  every surface, an `IntersectionObserver` scrollspy "you are here" cue, smooth
  anchor scrolling that respects `prefers-reduced-motion`, and a keyboard skip
  link — **no router, no new dependency, no new pages**, and no
  backend/API/schema/contract changes. It implemented the
  [Phase 22A UI Navigation + Demo Flow Planning](docs/planning/phase-22a-ui-navigation-demo-flow-planning.md),
  which inventoried the seven top-level dashboard surfaces, documented the
  scroll-only demo flow and its pain points, and proposed the controlled
  single-page section-navigation model while **deferring React Router and any route
  architecture** and forbidding fake pages.
  The preceding **Phase 21F** re-ran the local backend (`8787`) and frontend
  (`5173`), validated that the **Phase 21E**-polished dashboard is still
  **connected** (health `0.1.0`; graph 7 nodes / 6 edges; Intelligence Report
  Dreaming `0` / Decay `7` / Provenance `7` / Query Trails `7`), confirmed
  `npm run check:frontend` passes, and refreshed the screenshot trail with
  `phase-21f-connected-*` captures superseding the pre-polish `phase-21c-*` set
  while preserving that history — changing no application behavior. See the
  [Phase 21F UI Demo Polish QA + Screenshot Evidence Refresh](docs/demo/phase-21f-ui-demo-polish-qa-evidence.md).
  The preceding **Phase 21E** implemented the presentation-only UI demo polish pass
  (header band, `DEVDEVBUILDS` parent label, `READ-ONLY DEMO BUILD` badge,
  connection/health status row, card-style metric grids) against the
  [Phase 21D UI Demo Polish Planning / Dashboard Refinement Scope](docs/phase-21d-ui-demo-polish-planning.md),
  which documented the connected UI state and prioritized the dashboard refinement
  set. Before that, **Phase 21C** re-ran the local backend (`8787`) and frontend
  (`5173`) and captured the **connected** UI state after the Phase 21A/21B
  runtime-config fixes — the **"Connected"** status pill, live API health
  (`hivemind-backend` `0.1.0`), the rendered Knowledge Graph (7 nodes / 6 edges),
  and the backend-derived Intelligence Report — **replacing Phase 20D's honestly
  recorded `Failed to fetch` evidence while preserving that history**. See the
  [Phase 21C Connected UI Screenshot + Runtime Evidence Refresh](docs/demo/phase-21c-connected-ui-evidence.md).
  The preceding **Phase 21A** added the dashboard shell foundation and **Phase 21B**
  aligned the frontend API base-URL runtime config (root `envDir`, canonical backend
  port `8787`), together fixing the frontend/backend mismatch Phase 20D documented.
  Before that, **Phase 20D** executed the Phase 20A
  screenshot/evidence plan against **real, locally running app state**: it verified
  the backend runtime directly through `/api/health`, `/api/sources`, `/api/graph`,
  and `/api/intelligence/report`, and recorded the captured backend-runtime
  screenshots and an evidence doc; its frontend browser state showed a `Failed to
  fetch` (a run-configuration mismatch, since fixed), documented honestly as
  captured runtime evidence. See the
  [Phase 20D Final Demo Screenshot + Evidence Capture Pass](docs/demo/phase-20d-demo-evidence.md).
  The preceding **Phase 20C** packaged the existing project narrative into a
  canonical [Final Demo Script](docs/demo/final-demo-script.md) and locked the
  presentation spine via a [Portfolio Presentation Lock](docs/demo/portfolio-presentation-lock.md)
  — the one-line story, the data-flow surface order, and the honesty boundaries.
  The preceding **Phase 20B** aligned this README and the landing docs with
  the locked Phase 20A demo release-candidate story — tool-first overview, the
  locked one-line narrative, the implemented / intentionally-read-only / planned
  distinction, design-rationale notes, the agent-assisted/human-reviewed workflow,
  and a guardrails/non-goals section. Before that, **Phase 20A** locked the final
  demo release-candidate scope: the current
  demo story, the clean portfolio narrative — a local-first developer knowledge
  intelligence dashboard that organizes imported sources, visualizes relationships,
  and derives deterministic, read-only intelligence signals with **no AI/LLM** — the
  demo candidate surfaces with per-surface evidence and overstatement guards, a
  portfolio-readiness checklist, a screenshot/evidence plan (no screenshots created),
  the known limitations to disclose, the out-of-scope items, and the controlled
  next-phase sequence (20B–20E). Before that, Phase 19B verified and recorded the
  whole-project readiness posture as a controlled, demo-ready, release-readiness
  *candidate*, with a **Demo Evidence Checklist** and explicit **Release Readiness
  Boundaries**; Phase 19A consolidated the Phase 18A–18F security-hardening arc into
  a single release-readiness view. Hive|Mind has a stronger, evidence-backed
  **defensive API posture for a local/demo dev-tool** — it is **not**
  production-hardened. The next recommended phase is the **Final Portfolio Packaging
  / Public Presentation Pass**, drawing on the locked scope and the captured
  evidence. See the
  [Phase 20D Final Demo Screenshot + Evidence Capture Pass](docs/demo/phase-20d-demo-evidence.md),
  the
  [Final Demo Script](docs/demo/final-demo-script.md),
  the
  [Portfolio Presentation Lock](docs/demo/portfolio-presentation-lock.md),
  the
  [Phase 20B Final README + Portfolio Narrative Hardening](docs/release-readiness/phase-20b-final-readme-portfolio-narrative-hardening.md),
  the
  [Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](docs/release-readiness/phase-20a-demo-release-candidate-planning.md),
  the
  [Phase 19B Release Readiness QA + Demo Evidence Pass](docs/release-readiness/phase-19b-release-readiness-qa-demo-evidence.md),
  the
  [Phase 19A Security Cohesion + Release Readiness Planning](docs/security/phase-19a-security-cohesion-release-readiness-planning.md),
  and the
  [Security Threat Model + Vulnerability Test Plan](docs/security/threat-model-and-vulnerability-test-plan.md).
- **Completed foundation:** React/FastAPI app shell, local JSON-backed
  `HiveStore`, Hive Console (API + panel), Source Registry (backend + frontend +
  inspector), Obsidian adapter and import pipeline with frontend import panel,
  the Knowledge Graph API, the read-only Knowledge Graph panel, the custom
  read-only SVG graph visualization, and the read-only Intelligence Report panel
  with all four sections (Temporal Decay, Dreaming Suggestions, Provenance
  Chains, and Query Trails) backend-derived.

The current Intelligence Report is **fully backend-derived and read-only**. As of
Phase 13A the **Temporal Decay** section is backend-derived from real store
timestamps using deterministic thresholds; as of Phase 14C the **Dreaming
Suggestions** section is backend-derived from real store nodes/edges via
deterministic rules (duplicate labels, orphaned nodes, stale links); as of
Phase 15C **Provenance Chains** are backend-derived from existing
source/import/node/edge records with explicit evidence metadata; and as of
Phase 16C **Query Trails** are backend-derived from existing source/node/tag
structure (`source_followup` / `knowledge_gap` / `related_query_cluster`), with
the query-history-dependent categories deferred. No section is fixture-backed. It
does **not** run AI/LLM calls, semantic provenance inference, query persistence,
or any graph/source/store mutation. See the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md),
[Roadmap](docs/roadmap.md), [Demo Guide](docs/demo-guide.md), and
[Screenshot Checklist](docs/screenshot-checklist.md).

## Stack

- **Frontend:** Vite, React, TypeScript, plain CSS.
- **Backend:** Python, FastAPI, Pydantic.
- **Tests:** pytest.
- **Storage / model foundation:** local JSON-backed `HiveStore` with explicit
  Pydantic contracts.
- **Source integration:** Obsidian adapter and import foundation.

## Design rationale

A few deliberate choices shape the whole project. Each is a small bet that
foundations should be stable and honest before they are clever.

- **Local-first.** Hive|Mind runs entirely on one machine against local
  JSON-backed storage — no accounts, no cloud, no network exposure. The data stays
  the developer's own, every run is reproducible, and a whole class of security and
  privacy concerns never enters the demo surface.
- **Deterministic, backend-derived intelligence.** Every intelligence signal is
  computed by reviewable rules over the store, not by model inference. The same
  store state always produces the same report, which is what keeps the intelligence
  layer testable, auditable, and honest as it grows.
- **Read-only intelligence surfaces.** The graph and the Intelligence Report
  project existing structure; they never mutate the store, sources, or graph.
  Repeated reads are side-effect-free, so inspecting the system can never damage it.
- **Stable contracts before feature expansion.** New surfaces land as additive,
  documented API contracts first, so the frontend and backend evolve against a known
  shape instead of a moving target.
- **Source provenance before automation.** The system tracks where knowledge came
  from before it tries to act on that knowledge. Provenance is shown, never invented,
  and missing lineage is represented honestly as partial/unknown.
- **Security validation before release polish.** The request → API boundary was
  defended and evidenced (the Phase 18 arc) before any final demo polish, so the
  presentable surface sits on a checked foundation rather than the reverse.
- **No AI/LLM until the foundations are stable.** Model inference, embeddings, and
  vector search are deliberately out of scope until the deterministic core,
  contracts, and provenance are solid — adding "AI" earlier would trade a credible,
  auditable story for one a reviewer would immediately probe.
- **No graph/source mutation until review workflows exist.** Suggestions are
  advisory and never auto-applied; mutation waits until there is a human-reviewed
  workflow to gate it.

## Completed phase summary

| Phase | Status | Summary |
| --- | ---: | --- |
| Phase 0 | Complete | Project initialization and planning foundation. |
| Phase 1 | Complete | Clean React/FastAPI app foundation with health/status endpoints. |
| Phase 2 | Complete | API contract and data model planning. |
| Phase 3A | Complete | Backend storage foundation and local JSON-backed HiveStore. |
| Phase 3C/3D | Complete | Store search helpers and Hive Console API. |
| Phase 4A | Complete | Frontend console panel wired to backend console execution. |
| Phase 4B | Complete | Console UX and result formatting improvements. |
| Phase 5A | Complete | Source Registry backend foundation. |
| Phase 5B | Complete | Source Registry frontend panel. |
| Phase 5C | Complete | Source Registry inspector and UX polish. |
| Phase 6A | Complete | Obsidian adapter contract. |
| Phase 6B | Complete | Obsidian import MVP. |
| Phase 6C | Complete | Obsidian import hardening and deterministic import summaries. |
| Phase 6D | Complete | Obsidian import API polish and Source Registry wiring. |
| Phase 6E | Complete | Obsidian metadata visibility in the frontend registry. |
| Phase 7A | Complete | Frontend Obsidian import action panel. |
| Phase 7B | Complete | Obsidian import UX hardening. |
| Phase 8A | Complete | Knowledge Graph API foundation. |
| Phase 8B | Complete | Frontend read-only Knowledge Graph panel. |
| Phase 8C | Complete | Knowledge Graph visualization-prep view model and README revamp. |
| Phase 9A | Complete | First read-only SVG graph visualization. |
| Phase 9B | Complete | Knowledge graph panel UX hardening and inspector sync. |
| Phase 9C | Complete | Knowledge graph viz QA, demo polish, and link safety. |
| Phase 10A | Complete | Intelligence surface planning (documentation only). |
| Phase 10B | Complete | Intelligence contract types / read-only schemas. |
| Phase 10C | Complete | Intelligence report endpoint foundation. |
| Phase 10D | Complete | Intelligence Report frontend read-only panel. |
| Phase 10E | Complete | Intelligence Report UX hardening and demo readiness. |
| Phase 11A | Complete | Deterministic intelligence demo/seed fixtures. |
| Phase 11B | Complete | Intelligence fixture UX review and screenshot readiness. |
| Phase 11C | Complete | Repo cohesion and demo documentation pass. |
| Phase 12A | Complete | Demo freeze and release snapshot (documentation only). |
| Phase 13A | Complete | Temporal Decay backend-derived from store timestamps (read-only MVP). |
| Phase 13B | Complete | Temporal Decay frontend visibility and demo polish. |
| Phase 13C | Complete | Temporal Decay end-to-end QA and demo evidence pass. |
| Phase 14A | Complete | Dreaming suggestion backend derivation planning. |
| Phase 14B | Complete | Dreaming contract/schema alignment; `source_coverage_gap` remains deferred. |
| Phase 14C | Complete | Backend-derived deterministic Dreaming Suggestions MVP. |
| Phase 14D | Complete | Dreaming Suggestions frontend visibility in the Intelligence Report panel. |
| Phase 14E | Complete | Dreaming Suggestions QA/demo evidence lock pass (documentation only). |
| Phase 15A | Complete | Provenance Chains backend derivation planning and frontend readiness notes. |
| Phase 15B | Complete | Provenance Chains contract types / schema alignment. |
| Phase 15C | Complete | Backend-derived deterministic Provenance Chains MVP. |
| Phase 15D | Complete | Provenance Chains frontend visibility and demo polish. |
| Phase 15E | Complete | Provenance Chains QA/demo evidence lock pass. |
| Phase 16A | Complete | Query Trails / Query Memory foundation planning before persistence or APIs. |
| Phase 16B | Complete | Query Trails contract types / schema alignment (read-only `QueryTrailEntry` contract before persistence/derivation). |
| Phase 16C | Complete | Query Trails backend-derived MVP (`source_followup` / `knowledge_gap` / `related_query_cluster`) and frontend visibility; query-history categories deferred. |
| Phase 17A | Complete | Intelligence Report cohesion + system readiness planning (documentation only). |
| Phase 17B | Complete | Intelligence Report cohesion hardening + readiness QA (documentation only); rationale, decay thresholds, edge cases, evidence expectations, performance notes, and future adapter strategy. |
| Phase 18A | Complete | Security threat model + vulnerability test plan (documentation only); scope/authorization, system inventory, trust boundaries, attack-surface matrix, planned test categories, pass/fail criteria, and future hardening phases. |
| Phase 18B | Complete | Backend API defensive validation + error safety; global clean-JSON `500` handler (no traceback/path leak), malformed Obsidian vault-path normalization (→ `400`), and additive free-text length guards (→ `422`). |
| Phase 18C | Complete | Backend API security regression QA + evidence pass (QA/documentation only); verifies the 18B behaviors and records test evidence. |
| Phase 18D | Complete | API edge case hardening planning / deferred security scope triage (planning/documentation only); triages and risk-rates the deferred API edges and scopes Phase 18E. |
| Phase 18E | Complete | API edge case defensive validation MVP; additive per-model bounded nesting-depth guard (`MAX_REQUEST_NESTING_DEPTH = 32`) and explicit null-like / empty-value decisions, with regression tests. |
| Phase 18F | Complete | API edge case security regression QA + evidence pass (QA/documentation only); verifies the 18E guard/decisions and records test evidence (267 full backend tests passing). |
| Phase 19A | Complete | Security cohesion + release readiness planning (documentation only); consolidates the Phase 18A–18F arc into a demo-ready (not production-secure) release-readiness view with posture, checklist, deferred scope, and rationale. |
| Phase 19B | Complete | Release readiness QA + demo evidence pass (documentation/evidence only); records the whole-project readiness posture, the completed security/intelligence arcs, a Demo Evidence Checklist, and explicit Release Readiness Boundaries. Demo-ready candidate, not production-ready/secure. |
| Phase 20A | Complete | Demo release candidate planning + final portfolio readiness scope (planning/documentation only); defines the final demo release-candidate scope before any polish/screenshots/release work — current demo story, locked deterministic read-only narrative (no AI/LLM), demo candidate surfaces with evidence/overstatement guards, portfolio-readiness checklist, screenshot/evidence plan (no screenshots created), known limitations, out-of-scope items, and a recommended 20B–20E sequence. |
| Phase 20B | Complete | Final README + portfolio narrative hardening (documentation only); aligns the README and landing docs with the locked Phase 20A story — tool-first overview, locked one-line narrative, explicit implemented / read-only / planned distinction, design-rationale notes, agent-assisted/human-reviewed workflow, a guardrails/non-goals section, and the status advance to Phase 20B. No code, contract, or behavior changes. |
| Phase 20C | Complete | Final demo script + portfolio presentation lock (documentation / demo only); packages the existing narrative into a canonical [Final Demo Script](docs/demo/final-demo-script.md) and locks the presentation spine via a [Portfolio Presentation Lock](docs/demo/portfolio-presentation-lock.md) — one-line story, data-flow surface order, and honesty boundaries — before any further UI work. UI remains intentionally deferred. No code, contract, or behavior changes. |
| Phase 20D | Complete | Final demo screenshot + evidence capture pass (capture / documentation only); verifies the backend runtime directly via `/api/health`, `/api/sources`, `/api/graph`, and `/api/intelligence/report` and records the captured backend-runtime screenshots and an [evidence doc](docs/demo/phase-20d-demo-evidence.md). The frontend browser state showed a `Failed to fetch` (run-configuration mismatch, since fixed in 21A/21B), documented honestly as captured runtime evidence. No code, contract, or behavior changes. |
| Phase 21A | Complete | Dashboard shell foundation (frontend styling/scaffold); adds the dashboard shell layout/styles ahead of connected-UI evidence. |
| Phase 21B | Complete | Frontend API base-URL runtime config alignment; loads env from the repo root (`envDir`), documents the canonical backend port `8787`, and adds `.env.example` guidance — fixing the frontend/backend mismatch Phase 20D recorded. |
| Phase 21C | Complete | Connected UI screenshot + runtime evidence refresh (capture / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures the connected UI state — "Connected" status, live API health, the rendered Knowledge Graph (7 nodes / 6 edges), and the backend-derived Intelligence Report — replacing Phase 20D's `Failed to fetch` evidence while preserving that history. Records an [evidence doc](docs/demo/phase-21c-connected-ui-evidence.md) and connected-UI screenshots. No code, contract, or behavior changes. |
| Phase 21D | Complete | UI demo polish planning / dashboard refinement scope (planning / documentation only); documents the current connected UI state and a prioritized dashboard refinement set (visual hierarchy, spacing/density, connected-data readability, Intelligence Report, Knowledge Graph, Source Registry, console, responsive, screenshot friendliness), separates demo-readiness from future premium-UI ideas, locks read-only/non-mutating boundaries, and recommends a scoped Phase 21E implementation pass. See the [planning doc](docs/phase-21d-ui-demo-polish-planning.md). No code, contract, or behavior changes. |
| Phase 21E | Complete | UI demo polish implementation pass (frontend presentation only); adds a polished header band (`DEVDEVBUILDS` parent label, `READ-ONLY DEMO BUILD` badge), a connection/health status row, and card-style metric grids for API health and the Vault summary against the Phase 21D priorities. Frontend-only (`App.tsx`, `SourceRegistryPanel.tsx`, `styles.css`); no backend, contract, schema, data-value, or dependency changes. |
| Phase 21F | Complete | UI demo polish QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`), validates the Phase 21E-polished UI is still connected (health `0.1.0`, graph 7 nodes / 6 edges, backend-derived Intelligence Report — Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7), confirms `npm run check:frontend` passes, and refreshes the screenshot trail with `phase-21f-connected-*` captures that supersede the pre-polish `phase-21c-*` set while preserving that history. Records an [evidence doc](docs/demo/phase-21f-ui-demo-polish-qa-evidence.md). No code, contract, or behavior changes. |
| Phase 22A | Complete | UI navigation + demo flow planning (planning / documentation only); inventories the seven top-level dashboard surfaces (hero, connection + API health, vault, Source Registry incl. the nested Obsidian import form, Knowledge Graph, Intelligence Report, Console), documents the current scroll-only demo flow and its pain points (no nav, no anchors, long scroll, buried import controls, no active-section cue), and proposes a controlled single-page section-navigation model for Phase 22B — in-page anchor nav over stable section `id`s, scrollspy active-section cue, CSS-first smooth-scroll/anchor behavior, keyboard/`aria` usability, modest responsive nav, and a signposted demo walkthrough — deferring React Router/route architecture and forbidding fake pages. Defines Phase 22B acceptance criteria and locks read-only/non-mutating boundaries. See the [planning doc](docs/planning/phase-22a-ui-navigation-demo-flow-planning.md). No code, contract, or behavior changes. |
| Phase 22B | Complete | Single-page section navigation + demo flow (frontend presentation/structure only, PR #80); adds a sticky in-page section nav (table of contents) over the connected dashboard, stable `id` anchors on every top-level surface (`#overview` … `#console`), an `IntersectionObserver` scrollspy "you are here" cue with `aria-current`, smooth anchor scrolling that respects `prefers-reduced-motion`, and a keyboard skip link. Touches `App.tsx`, the four panel components (optional `id` prop), and `styles.css` only; no router, no new dependency, no new pages, and no backend/API/schema/contract or data-value changes. |
| Phase 22C | Active | UI navigation QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures honest evidence that the Phase 22B section navigation is visible and usable over the connected dashboard — sticky nav, `id` anchors, scrollspy active-section highlight, and skip link — with the directly exercised endpoints returning the same shapes/values as Phase 21C/21F (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-22c-connected-*` screenshot set (including the honest scrollspy edge behavior at the page top/bottom) and an [evidence doc](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md) while preserving the `phase-21f-*` history. No code, contract, or behavior changes. |

## Planned logic

Hive|Mind is built as a pipeline from raw source material to inspectable,
queryable knowledge. The stages below describe the intended architecture; some
are implemented today and some are planned (and labeled as such).

- **Source intake** *(implemented for Obsidian)* - read content from a
  connected source such as an Obsidian vault.
- **Normalization** *(implemented)* - map source content into the shared
  node/edge data model rather than storing raw, source-specific shapes.
- **Source Registry** *(implemented)* - track each connected source, its status,
  and its import metadata.
- **Knowledge Graph** *(implemented, read-only)* - project normalized records
  into a deterministic graph of nodes and relationships.
- **Console / query layer** *(implemented, foundational)* - run read-only
  queries against the store from the frontend console.
- **Graph visualization** *(implemented, read-only)* - a deterministic SVG graph
  canvas built on the Phase 8C view model, with a legend, summary stats, and
  selection-driven highlighting/dimming. No physics, mutation, or editing.
- **Node inspector** *(implemented, read-only)* - focused detail view for the
  selected node or edge and its immediate relationships.
- **Intelligence report contracts** *(implemented)* - shared backend/frontend
  shapes for Dreaming suggestions, decay statuses, provenance chains, query
  trails, and a summary rollup.
- **Intelligence Report panel** *(implemented, read-only)* - renders all four
  backend-derived sections: Temporal Decay, Dreaming Suggestions, Provenance
  Chains, and Query Trails.
- **Real Dreaming logic** *(implemented, read-only MVP — Phase 14C)* -
  deterministic, read-only suggestions derived from actual store nodes/edges:
  `duplicate` (shared normalized labels), `orphan` (no edges/source/parent), and
  `stale` (old links whose endpoints changed since). Each carries a
  `confidence_hint` and an explainable `metadata.evidence` trail; nothing is
  applied automatically. `source_coverage_gap` stays deferred/blocked (Phase 14B
  contract decision) and `unresolved_query` stays blocked until query history is
  persisted. No AI/LLM.
- **Temporal Knowledge Decay** *(implemented, read-only MVP — Phase 13A)* -
  freshness/staleness buckets derived from real store node/source timestamps via
  deterministic thresholds (fresh <= 30d, aging <= 90d, else stale). No graph
  mutation; indicators are advisory.
- **Provenance Chains** *(implemented, read-only MVP — Phase 15C)* -
  deterministic source/import/node/edge chains derived from existing store and
  source registry data. Each carries backend-owned `metadata.evidence`; missing
  source metadata is represented honestly as partial/unknown rather than
  fabricated.
- **Query trails** *(implemented, read-only MVP — Phase 16C)* - deterministic
  `source_followup` / `knowledge_gap` / `related_query_cluster` projections over
  existing source/node/tag structure, each with backend-owned `metadata.evidence`
  and a clean empty section. The query-history-dependent categories
  (`repeated_query` / `unresolved_question`) stay **deferred/blocked** until local
  query persistence exists.
- **Query memory persistence** *(planned)* - future local persistence and review
  surfaces for past console/search activity, which would unblock the deferred
  query-history categories above and Dreaming's `unresolved_query` pattern.

The Intelligence Report is now fully backend-derived; no section is fixture-backed.
The deterministic derivations are reproducible from store/source state, which is
what keeps the intelligence layer honest and reviewable as it grows.

## Roadmap

The next wave of work should keep the intelligence layer honest and reviewable:
contracts first, deterministic read-only derivation second, frontend surfaces
third. See the [full roadmap](docs/roadmap.md) and the
[Intelligence Surface Plan](docs/intelligence-surface-plan.md) for detail.

| Planned / Active Phase | Focus |
| --- | --- |
| Phase 12A | Demo freeze + release snapshot; demo script, screenshot checklist, and README/API/docs consistency. |
| Future intelligence phases | Replace fixture sections with real deterministic read-only derivation. |
| Phase 16A | Query Trails / Query Memory foundation planning before persistence, APIs, or frontend display. |
| Phase 16B | Query Trails contract types / schema alignment — read-only `QueryTrailEntry` contract before any persistence or derivation logic. |
| Phase 16C | Query Trails backend-derived MVP and frontend visibility; query-history categories deferred. |
| Phase 17A | Intelligence Report cohesion + system readiness planning (documentation only). |
| Phase 17B | Intelligence Report cohesion hardening + readiness QA (documentation only). |
| Phase 18A | Security threat model + vulnerability test plan (documentation only); scope, trust boundaries, attack surfaces, planned tests, and pass/fail criteria before any defensive testing. |
| Phase 18B–18F | Delivered API-hardening arc: defensive validation + error safety (18B), regression/evidence (18C), edge-case triage (18D), edge-case validation MVP (18E), and a second regression/evidence pass (18F). |
| Phase 19A | Security cohesion + release readiness planning (documentation only); consolidates the 18A–18F arc into a demo-ready (not production-secure) posture with a release-readiness checklist and deferred-scope carry-forward. |
| Phase 19B | Release readiness QA + demo evidence pass (documentation/evidence only); records the whole-project readiness posture and demo boundaries, with a Demo Evidence Checklist and explicit Release Readiness Boundaries. |
| Phase 20A | Demo release candidate planning + final portfolio readiness scope (planning/documentation only); locks the final demo release-candidate scope, surfaces, evidence/overstatement guards, readiness checklist, screenshot/evidence plan, limitations, and the recommended 20B–20E sequence. |
| Phase 20B | Final README + portfolio narrative hardening (documentation only); align README and landing docs with the locked Phase 20A story, status, setup, and links. **Complete.** |
| Phase 20C | Final demo script + portfolio presentation lock (documentation / demo only); package the narrative into a canonical demo script and lock the presentation spine before further UI work. **Complete.** |
| Phase 20D | Final demo screenshot + evidence capture pass (capture / documentation only); verify the backend runtime directly via `/api/health`, `/api/sources`, `/api/graph`, and `/api/intelligence/report` and record the captured backend-runtime screenshots and [evidence doc](docs/demo/phase-20d-demo-evidence.md). Frontend `Failed to fetch` documented honestly as captured evidence (run-configuration mismatch, since fixed). **Complete.** |
| Phase 21A / 21B | Dashboard shell foundation (21A) and frontend API base-URL runtime config alignment (21B, root `envDir` + canonical backend port `8787`), fixing the frontend/backend mismatch Phase 20D recorded. **Complete.** |
| Phase 21C | Connected UI screenshot + runtime evidence refresh (capture / documentation only); re-run the local backend (`8787`) and frontend (`5173`) and capture the connected UI state — "Connected" status, live API health, the rendered Knowledge Graph, and the backend-derived Intelligence Report — replacing Phase 20D's `Failed to fetch` evidence while preserving that history. See the [evidence doc](docs/demo/phase-21c-connected-ui-evidence.md). **Complete.** |
| Phase 21D | UI demo polish planning / dashboard refinement scope (planning / documentation only); document the current connected UI state, prioritize dashboard refinement targets, separate demo-readiness from future premium-UI ideas, lock read-only/non-mutating boundaries, and recommend a scoped Phase 21E implementation pass. See the [planning doc](docs/phase-21d-ui-demo-polish-planning.md). **Complete.** |
| Phase 21E | UI demo polish implementation pass (frontend presentation only); polished header band (`DEVDEVBUILDS` parent label, `READ-ONLY DEMO BUILD` badge), connection/health status row, and card-style metric grids against the Phase 21D priorities. Frontend-only; no backend, contract, logic, data-value, or dependency changes. **Complete.** |
| Phase 21F | UI demo polish QA + screenshot evidence refresh (QA / evidence / documentation only); re-run the local backend (`8787`) and frontend (`5173`), validate the Phase 21E-polished UI is still connected (live API health, Knowledge Graph 7 nodes / 6 edges, backend-derived Intelligence Report), confirm the frontend build passes, and refresh the screenshot trail with `phase-21f-connected-*` captures superseding the pre-polish `phase-21c-*` set while preserving that history. See the [evidence doc](docs/demo/phase-21f-ui-demo-polish-qa-evidence.md). **Complete.** |
| Phase 22A | UI navigation + demo flow planning (planning / documentation only); inventory the seven top-level dashboard surfaces, document the scroll-only demo flow and its pain points, and propose a controlled single-page section-navigation model for Phase 22B (in-page anchor nav over stable section `id`s, scrollspy active state, CSS-first scroll/anchor behavior, keyboard/`aria` usability, modest responsive nav, signposted walkthrough) while deferring React Router and forbidding fake pages; define Phase 22B acceptance criteria. See the [planning doc](docs/planning/phase-22a-ui-navigation-demo-flow-planning.md). **Complete.** |
| Phase 22B | Single-page section navigation + demo flow (frontend presentation/structure only); add a sticky in-page section nav over the connected dashboard, stable `id` anchors on every top-level surface, an `IntersectionObserver` scrollspy active-section cue, smooth anchor scrolling that respects `prefers-reduced-motion`, and a keyboard skip link; no router, no new dependency, no new pages, no backend/API/schema/contract changes. **Complete.** |
| Phase 22C | UI navigation QA + screenshot evidence refresh (QA / evidence / documentation only); re-run the local backend (`8787`) and frontend (`5173`) and capture honest evidence that the Phase 22B section navigation is visible and usable over the connected dashboard (sticky nav, `id` anchors, scrollspy active-section highlight, skip link), confirm the same connected backend data as Phase 21C/21F and a passing frontend build, and record a `phase-22c-connected-*` screenshot set. See the [evidence doc](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md). **Active.** |
| Future security phases | Obsidian import filesystem safety, intelligence evidence regression, frontend rendering safety, dependency/static baseline; production-security controls (auth, rate limiting, deployment hardening, secrets, audit logging, monitoring) stay out of scope until the runtime model changes. |
| Future query phases | Add query-persistence logic only after contracts, privacy boundaries, and validation. |

> **Intelligence data note:** `GET /api/intelligence/report` derives all four of
> its sections — **Temporal Decay** (Phase 13A), **Dreaming Suggestions**
> (Phase 14C), **Provenance Chains** (Phase 15C), and **Query Trails**
> (Phase 16C) — from existing store/source state, using deterministic rules,
> tagged `metadata.derived`, with a clean empty section when nothing is
> derivable. No section is fixture-backed. The query-history-dependent Query
> Trail categories (`repeated_query` / `unresolved_question`) stay deferred until
> local query persistence exists. No query persistence, AI/LLM logic, or
> graph/source/store mutation runs, and the endpoint remains read-only.

## Guardrails and non-goals

Hive|Mind is deliberately scoped. The following are **not** present and are not
implied to be — naming them is what keeps the project honest about what it is.

- **No AI/LLM integration.** Every signal is deterministic rule-based derivation;
  there is no model inference, embedding, or vector search.
- **No live Obsidian watcher or write-back.** Import is a one-shot read; there is no
  filesystem watcher and nothing is written back to the vault.
- **No graph or intelligence mutation from the UI.** The graph and the Intelligence
  Report are read-only; suggestions are advisory and never auto-applied.
- **No persisted query history yet.** The query-history-dependent Query Trail
  categories (`repeated_query` / `unresolved_question`) stay deferred until local
  query persistence exists; fabricating query-memory records would be dishonest.
- **No auth, users, or multi-user support.** There are no accounts, sessions, roles,
  or permissions — only the defensive API boundary from the Phase 18 arc.
- **Not production / SaaS-ready.** Single-user, local, no network exposure; a
  demo-grade defensive posture, **not** production-hardened security or operation.

These are constraints chosen on purpose, not a backlog to clear before the project
is "real." The full known-limitations and out-of-scope lists live in the
[Phase 20A Demo Release Candidate Planning](docs/release-readiness/phase-20a-demo-release-candidate-planning.md).

## Portfolio narrative

For a reviewer, Hive|Mind is meant to read as a small, complete, honest system
rather than a pile of half-features. What it demonstrates:

- **End-to-end ownership.** A React/FastAPI app with a local data model, an import
  pipeline, a graph visualization, and a derived intelligence layer — designed,
  built, documented, and QA'd across a recorded phase history.
- **Engineering judgment over feature count.** A bounded scope done well, with
  deferred work named explicitly instead of implied as present.
- **Security reasoning, evidenced.** A threat model, a defensive API-hardening arc,
  and regression evidence — security treated as something to reason about and test,
  not decorate.
- **Honesty as a feature.** The deterministic, read-only, local-first framing is
  precise about what the tool does and does not do, which is more credible than an
  inflated "AI platform" claim.

The per-surface evidence and overstatement guards behind this narrative live in the
[Phase 20A Demo Release Candidate Planning](docs/release-readiness/phase-20a-demo-release-candidate-planning.md)
and the
[Phase 20B Final README + Portfolio Narrative Hardening](docs/release-readiness/phase-20b-final-readme-portfolio-narrative-hardening.md).

## Setup

Prerequisites: Node.js 20+ and Python 3.11+.

```bash
# from the repository root
npm install
python -m venv .venv
python -m pip install -r apps/backend/requirements-dev.txt
```

Activate the virtual environment before installing backend dependencies if your
shell does not do so automatically. Optionally copy `.env.example` to `.env` or
`apps/frontend/.env`; the frontend defaults to the local backend URL when the
variable is absent.

## Run

Run each service in a separate terminal from the repository root:

```bash
npm run dev:backend
npm run dev:frontend
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8787](http://localhost:8787)
- API health: [http://localhost:8787/api/health](http://localhost:8787/api/health)
- Interactive API docs: [http://localhost:8787/docs](http://localhost:8787/docs)

## Verification checklist

- [ ] `npm run check:frontend` completes successfully.
- [ ] `npm run check:backend` passes.
- [ ] `/api/health` returns `ok: true`.
- [ ] The frontend shows the backend as connected.
- [ ] Source Registry data renders.
- [ ] Obsidian import action panel renders.
- [ ] Knowledge Graph read-only panel renders.
- [ ] Graph view-model/prep data renders without runtime errors.
- [ ] Intelligence Report panel renders all four backend-derived sections: Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails.

## Documentation

- [Phase 1 foundation](docs/phase-1-foundation.md)
- [API contract](docs/api-contract.md)
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Intelligence Report Cohesion + System Readiness Plan](docs/intelligence-report-cohesion-readiness-plan.md)
- [Phase 17B Intelligence Report Cohesion Hardening + Readiness QA](docs/phase-17b-intelligence-cohesion-hardening.md)
- [Security Threat Model + Vulnerability Test Plan](docs/security/threat-model-and-vulnerability-test-plan.md)
- [Phase 18A Security Threat Model + Vulnerability Test Plan (status)](docs/planning/phase-18a-security-threat-model-plan.md)
- [Phase 19A Security Cohesion + Release Readiness Planning](docs/security/phase-19a-security-cohesion-release-readiness-planning.md)
- [Phase 19B Release Readiness QA + Demo Evidence Pass](docs/release-readiness/phase-19b-release-readiness-qa-demo-evidence.md)
- [Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](docs/release-readiness/phase-20a-demo-release-candidate-planning.md)
- [Phase 20B Final README + Portfolio Narrative Hardening](docs/release-readiness/phase-20b-final-readme-portfolio-narrative-hardening.md)
- [Final Demo Script](docs/demo/final-demo-script.md)
- [Portfolio Presentation Lock](docs/demo/portfolio-presentation-lock.md)
- [Phase 20D Final Demo Screenshot + Evidence Capture Pass](docs/demo/phase-20d-demo-evidence.md)
- [Phase 21C Connected UI Screenshot + Runtime Evidence Refresh](docs/demo/phase-21c-connected-ui-evidence.md)
- [Phase 21D UI Demo Polish Planning / Dashboard Refinement Scope](docs/phase-21d-ui-demo-polish-planning.md)
- [Phase 21F UI Demo Polish QA + Screenshot Evidence Refresh](docs/demo/phase-21f-ui-demo-polish-qa-evidence.md)
- [Phase 22A UI Navigation + Demo Flow Planning](docs/planning/phase-22a-ui-navigation-demo-flow-planning.md)
- [Phase 22C UI Navigation QA + Screenshot Evidence Refresh](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md)
- [Demo Guide](docs/demo-guide.md)
- [Demo Script (earlier walkthrough)](docs/demo-script.md)
- [Screenshot Checklist](docs/screenshot-checklist.md)
- [Phase 11 Demo Readiness](docs/phase-11-demo-readiness.md)
- [Phase 12A Demo Freeze + Release Snapshot](docs/releases/phase-12a-demo-freeze.md)
- [Phase 14E Dreaming Suggestions E2E Evidence](docs/qa/phase-14e-dreaming-suggestions-e2e-evidence.md)
- [Roadmap](docs/roadmap.md)

