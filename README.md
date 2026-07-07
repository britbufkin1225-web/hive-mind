<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

## Overview

Hive|Mind is a **local-first, graph-primary AI memory / intelligence workspace
for developers**. It connects knowledge sources — starting with Obsidian vault
content — into a normalized backend data model and presents that model with the
**Knowledge Graph as the primary application surface**: the graph fills the
viewport edge-to-edge like a viewfinder over an intelligence map, and the
supporting tools — the Source Registry, the Obsidian import workflow, the query
Console, and the Intelligence Report (Temporal Decay, Dreaming Suggestions,
Provenance Chains, and Query Trails, all backend-derived and read-only) —
appear as contextual overlays summoned over the graph rather than as permanent
dashboard columns.

The UI direction is dark, serious, and premium: a black/chrome/metal dev-tool
shell in which the shell chrome carries almost no color, and the visual energy
is concentrated in the graph itself — nodes, edges, groups, idle aura,
selection pulse. Hive|Mind is deliberately **not dashboard-first, not
card-grid-first, and not a SaaS sidebar shell**; there is no persistent sidebar
as the default pattern.

It is built to improve everyday development work — organization, data provenance,
workflow speed, knowledge consistency, source tracking, and development
coordination — on top of a human-reviewed agent workflow and safer project memory
and reasoning surfaces. It is also a deliberately scoped backend/cybersecurity
portfolio project, and the two goals reinforce each other: the discipline that
makes it a credible portfolio piece (deterministic logic, read-only surfaces,
honest scope) is the same discipline that makes it a trustworthy tool.

> **What it is, in one line:** Hive|Mind is a local-first, graph-primary
> knowledge intelligence workspace that organizes imported knowledge sources,
> presents them as a full-surface knowledge graph, and derives deterministic,
> read-only intelligence signals — temporal decay, dreaming suggestions,
> provenance chains, and query trails — from existing structure rather than
> from any AI/LLM call.

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

## Visual evidence

These are real captures of the running app — the local frontend (`5173`)
talking to the local backend (`8787`), not mockups. They were taken during the
Phase 28C QA pass on the **true graph-primary surface** shipped in Phase 28B,
so they show the current connected state. Three views tell the whole story:

**1. The graph-primary surface** — the graph *is* the app.

![Hive|Mind true graph-primary surface: the Knowledge Graph fills the entire viewport edge-to-edge on a dark black/chrome shell, with the masthead and icon dock as floating translucent overlays and no persistent sidebar](./docs/demo/screenshots/phase-28c-default-graph-primary-surface.png)

The Knowledge Graph fills the viewport edge-to-edge on the dark black/chrome
shell. The masthead and the compact bottom dock are floating translucent
overlays — there is no persistent sidebar, no dashboard columns, and no
card-grid framing. Color energy lives in the nodes and edges, not the chrome.

**2. Selection + inspector** — contextual, not permanent.

![Hive|Mind selected-node inspector: a selected graph node with a pulsing glow and energy-flow edges, with a floating glass inspector card showing the node's details and relationships](./docs/demo/screenshots/phase-28c-selected-node-inspector.png)

Selecting a node summons a floating glass inspector card over the graph — the
selected node glows, edges incident to it pick up the energy-flow dash
treatment, and the detail view appears only when asked for. The graph stays
read-only throughout.

**3. Intelligence overlay** — the differentiator, summoned in context.

![Hive|Mind Intelligence overlay: the backend-derived Intelligence Report (Temporal Decay, Dreaming Suggestions, Provenance Chains, Query Trails) rendered as a contextual overlay above the full-viewport graph](./docs/demo/screenshots/phase-28c-intelligence-overlay.png)

The four backend-derived, read-only Intelligence sections (Temporal Decay,
Dreaming Suggestions, Provenance Chains, Query Trails) open as a contextual
overlay above the graph rather than a permanent dashboard section. This is
deterministic rule-based derivation over the store — **no AI/LLM** — which is
what makes it auditable.

> The Vault, Sources, Console, legend/lists, and narrow-viewport captures from
> the same session are kept in
> [`docs/demo/screenshots/`](docs/demo/screenshots/), and the capture session is
> documented in the
> [Phase 28C True Graph-Primary Surface QA + Screenshot Evidence](docs/demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md)
> note. The Phase 29B interaction polish (hover lifts, three-tier selection
> emphasis, edge selection, overlay behavior) is captured in the
> `phase-29c-connected-*` set, documented in the
> [Phase 29C Graph Interaction + Overlay Polish QA + Screenshot Evidence](docs/demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md)
> note, and the newest **Phase 30B interaction-recovery + responsive-rail fixes**
> (dock-close focus recovery, the press-for-press Escape stack, and the
> contained narrow-viewport rail) are captured in the `phase-30c-connected-*`
> set, documented in the
> [Phase 30C Interaction Recovery QA + Screenshot Evidence](docs/demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md)
> note. The earlier dashboard-era `phase-23b-*` / `phase-25c-*` capture sets are
> preserved in `docs/demo/screenshots/` as history.

## Current status

The project has moved beyond the initial foundation. The original Phase 1 app
shell is complete and has been built on through local JSON-backed backend
storage, the Hive Console, the Source Registry, the Obsidian import pipeline,
the Knowledge Graph API, and the read-only Knowledge Graph panel with its custom
SVG visualization.

- **Current phase:** `Phase 32D - MediaPipe / Hand-Landmark Motion Detection`
  (**frontend-only**). Phase 32D adds a **MediaPipe Hand Landmarker** estimator to
  the Motion Sandbox as the primary detector, keeping the Phase 32B/32C
  **frame-difference** estimator as a zero-dependency fallback / debug visualiser.
  Both fill the *same* hardened `MotionCommand` contract (`source` discriminates),
  so `zoomDelta` (approximate single-camera proxy) and `pinchActive` (thumb/index
  distance) become live. A small typed helper owns the landmark math; a lightweight
  landmark overlay + hand-detection readout were added. It adds one **pinned**
  dependency (`@mediapipe/tasks-vision@0.10.35`) whose wasm/model are fetched from
  version-pinned URLs — never committed or transmitted — and the camera stays
  explicit-start, local-only, no-storage, no-backend. **No graph control wiring**
  (that is Phase 32E). See the
  [Motion Sandbox Control Contract + 32D doc](docs/motion-sandbox-control-contract.md).
  The preceding **Phase 32C** runtime-QA'd the sandbox and hardened the
  `MotionCommand` contract (explicit `active` / `source` / `timestamp` fields + a
  pitch-sign fix), **Phase 32B** (PR #118) landed the standalone webcam motion
  sandbox, and **Phase 32A.6** (docs-only) brought the roadmap current with `main`.
  The Phase 31
  premium-graph-interaction frontend series — **31A
  (planning) through 31H is complete and merged into `main`**: type-owned aura
  rings and the `selected > related > ambient` emphasis tiers (31B); overlay
  motion, overlay tooling, and graph-surface density/depth (31C–31E); the graph
  micro-interaction + command-surface refinement (31F); a no-computed-style
  CSS-cascade consolidation (31G); and related-node + label readability (31H).
  **Phase 31I** (graph overlay legibility + command-surface final polish) is
  **implemented on its feature branch but not yet merged into `main`**, so it is
  tracked as pending. The preceding **Phase 30-series** is complete: Phase 30A
  (planning) triaged the two Phase 29C interaction rough edges, **Phase 30B**
  landed the interaction-recovery + responsive-rail fix in code (PR #109), and
  **Phase 30C** completed the QA + screenshot-evidence pass (PR #110, the
  `phase-30c-connected-*` set). This refresh also resolved the stale roadmap Git
  conflict markers left when the earlier Phase 32A.5 cleanup never landed on
  `main`. The next phase is **Phase 32E — Orbital Graph Control Contract +
  Motion-to-Graph Wiring Planning**, which will define how the hardened
  `MotionCommand` maps to graph orbit/zoom behaviour. See the
  [Phase 31A planning doc](docs/planning/phase-31a-premium-graph-interaction-portfolio-demo-direction.md)
  and the [Phase 30A planning doc](docs/phase-30a-post-polish-interaction-triage.md).
  The preceding **Phase 29C** (complete) verified the Phase 29B implementation
  against the connected local runtime and refreshed the screenshot evidence
  trail — 28 scripted interaction checks (hover lifts, three-tier selection
  emphasis, in-place selection switching, edge selection, empty-canvas
  deselect, Escape dismissal order, overlay exclusivity/persistence, focus
  management, narrow viewport) plus a `phase-29c-connected-*` screenshot set,
  with no frontend/CSS/backend/API/schema/package change and no implementation
  fixes. See the
  [Phase 29C evidence doc](docs/demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md).
  The preceding **Phase 29B** (complete) implemented the Phase 29A interaction
  contract as a frontend-only pass: the graph canvas gained the three-tier
  selected > related > ambient emphasis model, restrained additive hover lifts
  for nodes and edges, empty-canvas click-to-deselect, the Phase 29A Escape
  dismissal order (tertiary dock → explorer → selection/inspector, one surface
  per press), and focus management for the summoned overlays — see the
  [Phase 29A planning doc](docs/planning/phase-29a-graph-interaction-overlay-polish-planning.md).
  Before that, **Phase 28D** (complete) locked the graph-primary
  visual/product direction in the portfolio-facing docs after the Phase 28B
  implementation and the Phase 28C evidence pass: the README now presents
  Hive|Mind as a graph-primary AI memory / intelligence workspace — the
  Knowledge Graph is the full application surface, supporting tools appear as
  contextual overlays, and the shell stays dark black/chrome/metal with the
  color energy concentrated in the graph. The current phase sequence is:
  - **Phase 28D** — README / portfolio visual lock *(complete)*.
  - **Phase 29A** — graph interaction + overlay polish planning *(complete)*.
  - **Phase 29B** — graph interaction + overlay polish frontend
    implementation pass *(complete)*.
  - **Phase 29C** — QA + screenshot evidence refresh *(complete)*.
  - **Phase 30A** — post-polish interaction triage + next frontend direction
    planning *(complete)*.
  - **Phase 30B** — interaction recovery + responsive rail frontend
    implementation *(complete, PR #109)*.
  - **Phase 30C** — interaction recovery QA + screenshot evidence
    *(complete, PR #110)*.
  - **Phase 31A–31H** — premium graph interaction planning + frontend polish
    *(complete and merged into `main`)*.
  - **Phase 31I** — graph overlay legibility + command-surface final polish
    *(implemented on branch; not yet merged into `main`)*.
  - **Phase 32A / 32A.5** — motion/orbital feasibility planning and roadmap
    conflict-marker cleanup *(docs-only)*.
  - **Phase 32A.6** — roadmap 31-series status refresh *(docs-only)*.
  - **Phase 32B** — standalone webcam motion sandbox *(complete, PR #118)*.
  - **Phase 32C** — motion sandbox QA + control-contract hardening
    *(frontend-only)*.
  - **Phase 32D** — MediaPipe / hand-landmark motion detection
    *(this phase, frontend-only)*.
  - **Phase 32E** — orbital graph control contract + motion-to-graph wiring
    planning *(next)*.
- **Preceding phases 28A–28C:** Phase 28A tightened the graph-first
  direction into a stricter true graph-primary contract; Phase 28B implemented
  it — the Knowledge Graph fills the entire viewport edge-to-edge with no
  persistent sidebar/dashboard-column framing, the masthead/rail/dock are
  floating translucent glass overlays, and the graph gained a living-identity
  groundwork (idle aura, per-type halo, selection glow, energy-flow edges).
  Phase 28C was the evidence pass immediately after that implementation: it
  re-ran the connected backend/frontend and captured visually re-verified
  screenshots of the default full-viewport graph, the legend/lists overlay,
  the selected-node inspector, each of the Vault/Sources/Intelligence/Console
  overlays, and a narrow viewport. See the
  [Phase 28C True Graph-Primary Surface QA + Screenshot Evidence](docs/demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md),
  the [Phase 28A True Graph-Primary Surface + Overlay Contract](docs/phase-28a-true-graph-primary-overlay-contract.md),
  and the [full roadmap](docs/roadmap.md) for the complete 25B–28D history.
  The remainder of this section (below) is preserved as the historical Phase
  25A-and-earlier narrative.
- **Phase 25A** (planning / documentation only) defined a **buildable visual design
  system** for the next UI implementation pass — a premium, dark metallic
  intelligence-console aesthetic with a graph-forward identity — **before** any
  frontend/CSS change. It documents the current (light-theme) visual baseline, the
  target visual identity, the design principles, a layered surface/panel system, the
  typography and hierarchy direction, a graph-centered experience direction (node/edge
  language, canvas framing, inspector relationship, legend/status, and *planned*
  read-only overlay concepts for Temporal Decay / Dreaming Suggestions / Provenance
  Chains / Query Trails), the Intelligence-Report visual direction (with a clear
  real-vs-planned visual contract), the navigation/demo-flow direction, and the exact
  implementation boundaries for **Phase 25B** plus the QA/evidence expectations for
  **Phase 25C**. The graph stays read-only; nothing is faked. See the
  [Phase 25A Premium Visual Design System / Frontend Presentation Direction](docs/ui/phase-25a-premium-visual-system-planning.md).
  It changes no UI/CSS/frontend/backend/API/schema/package/dependency or runtime
  behavior and creates no screenshots.
  The preceding **Phase 24A** reviewed the existing Phase 23B connected screenshot set,
  selected the three strongest surfaces for the README landing page (connected
  dashboard top, Knowledge Graph, Intelligence Report), added the **Visual evidence**
  section above with honest captions, and recorded the selection rationale — including
  which screenshots were intentionally left out — in the
  [Phase 24A Portfolio Screenshot + README Visual Lock](docs/demo/phase-24a-portfolio-screenshot-readme-visual-lock.md)
  note, using **only existing, real captured screenshots** with no image fabrication
  and no behavior change.
  The preceding **Phase 23B** re-ran the local backend (`8787`)
  and frontend (`5173`) and captured honest screenshot/runtime evidence that the
  **Phase 23A** UI surface readability + panel-hierarchy polish renders correctly
  over the still-connected dashboard: the per-panel accent-tick headings, unified
  card/inspector rounding, the Intelligence Report hairline section dividers, lifted
  muted-label contrast, and the grouped Console output. The directly exercised
  endpoints returned the same shapes/values as Phase 21C/21F/22C (health `0.1.0`;
  graph 7 nodes / 6 edges; Intelligence Report Dreaming `0` / Decay `7` / Provenance
  `7` / Query Trails `7`), confirming **no backend/API/schema behavior changed** (23A
  was frontend CSS-only), and `npm run check:frontend` passes. A new
  `phase-23b-connected-*` screenshot set records the polished panel hierarchy on every
  major surface while preserving the `phase-22c-*` history. It changes no application
  behavior. See the
  [Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](docs/demo/phase-23b-ui-readability-qa-screenshot-evidence.md).
  The preceding **Phase 23A** applied the presentation-only readability + panel-
  hierarchy polish as a **frontend CSS-only** pass (PR #82): a shared accent-tick
  identity on every panel heading, unified card/inspector/container rounding onto the
  shared token radius, hairline dividers separating the dense Intelligence Report
  sub-sections, lifted muted-label contrast, and grouped Console output — **no new
  data, network/API/contract, or panel-behavior change**.
  The preceding **Phase 22C** re-ran the local backend (`8787`) and frontend (`5173`)
  and captured honest screenshot/runtime evidence that the **Phase 22B** single-page
  section navigation is **present and usable** over the connected dashboard, with a
  new `phase-22c-connected-*` set recording the sticky nav and its active-section
  highlight. See the
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
| Phase 22C | Complete | UI navigation QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures honest evidence that the Phase 22B section navigation is visible and usable over the connected dashboard — sticky nav, `id` anchors, scrollspy active-section highlight, and skip link — with the directly exercised endpoints returning the same shapes/values as Phase 21C/21F (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-22c-connected-*` screenshot set (including the honest scrollspy edge behavior at the page top/bottom) and an [evidence doc](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md) while preserving the `phase-21f-*` history. No code, contract, or behavior changes. |
| Phase 23A | Complete | UI surface readability + panel hierarchy polish (frontend presentation only, PR #82); an additive `styles.css` pass on the Phase 21A token system — a shared accent-tick identity on every panel `<h2>`, sub-section heading hierarchy, unified card/inspector/container rounding onto the shared token radius with softened hairline borders, hairline dividers separating the dense Intelligence Report sub-sections, lifted muted-label/metadata contrast, and grouped Console output. CSS-only; no backend, contract, logic, data-value, dependency, or panel-behavior change. |
| Phase 23B | Complete | UI surface readability QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures honest evidence that the Phase 23A readability/panel-hierarchy polish renders over the still-connected dashboard, with the directly exercised endpoints returning the same shapes/values as Phase 21C/21F/22C (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-23b-connected-*` screenshot set and an [evidence doc](docs/demo/phase-23b-ui-readability-qa-screenshot-evidence.md) while preserving the `phase-22c-*` history. No code, contract, or behavior changes. |
| Phase 24A | Complete | Portfolio screenshot selection + README visual lock (docs / README / demo presentation only); reviews the existing Phase 23B connected screenshot set, selects the three strongest README surfaces (connected dashboard top, Knowledge Graph, Intelligence Report), adds a **Visual evidence** README section with honest captions, and records the selection rationale (including intentionally-omitted screenshots) in the [Phase 24A Portfolio Screenshot + README Visual Lock](docs/demo/phase-24a-portfolio-screenshot-readme-visual-lock.md) note. Uses only existing real screenshots; no image fabrication and no UI/CSS/frontend/backend/API/schema/package/dependency/runtime behavior changes. |
| Phase 25A | Complete | Premium visual design system / frontend presentation direction (planning / documentation only); defines a buildable premium dark-metallic intelligence-console visual system with a graph-forward identity before any UI/CSS change — current (light) visual baseline, target visual identity, design principles, a layered surface/panel system, typography/hierarchy direction, a graph-centered experience direction (node/edge language, canvas framing, inspector relationship, legend/status, and *planned* read-only overlay concepts for Temporal Decay / Dreaming / Provenance / Query Trails), the Intelligence-Report visual direction with a real-vs-planned visual contract, the navigation/demo-flow direction, the Phase 25B implementation boundaries, and the Phase 25C QA/evidence expectations. Graph stays read-only; nothing faked. See the [planning doc](docs/ui/phase-25a-premium-visual-system-planning.md). No code, contract, or behavior changes. |
| Phase 25B | Complete | Premium visual system implementation pass (frontend presentation only); applies the Phase 25A direction as a token-driven reskin in `apps/frontend/src/styles.css` — a dark metallic palette plus elevation/spacing/type/glow tokens (token names preserved so token-driven rules re-theme automatically) and per-surface restyling of header/panels/cards/section nav/graph framing/inspector/Intelligence Report/console onto those tokens. Presentation-only over the existing token system and SVG view model; graph stays read-only; no backend/API/schema/contract/data-value/package/dependency or runtime behavior change. |
| Phase 25B.5 | Complete | Frontend asset contract + icon usage planning (planning / documentation only); audits current repo asset usage (clean baseline — only the approved `docs/assets/branding/hivemind-readme-banner.png` brand image plus `docs/demo/screenshots/*` evidence; the running app ships no favicon/logo/static asset and the sole SVG is the inline data-driven Knowledge Graph render) and creates the first Hive&#124;Mind [frontend asset contract](docs/frontend-asset-contract.md): approved source authority (devdevbuilds parent → Hive&#124;Mind lockup), allowed/forbidden asset categories (no icon-library dependency, no CDN, no generated/random or screenshot-derived assets), file-location and naming conventions, SVG safety, accessibility, dark-metallic theming (monochrome/duotone/glow/metallic/status treatments), the app-mark-vs-decorative-icon line, and how future asset phases must reference the contract. Adds no asset and no dependency; no UI/CSS/frontend/backend/API/schema/package or behavior change. |

The later phases — 26A–26C (graph visual identity), 27A–27E (graph-first app
shell / full-viewfinder surface), and 28A–28C (true graph-primary surface
contract, implementation, and screenshot evidence) — are recorded in full in
the [roadmap phase history](docs/roadmap.md#phase-history); Phase 28D (the
README / portfolio visual lock), Phase 29A (graph interaction + overlay
polish planning), Phase 29B (the graph interaction + overlay polish frontend
implementation pass), Phase 29C (its QA + screenshot evidence refresh), Phase
30A (post-polish interaction triage + next frontend direction planning), and
Phase 30B (the interaction recovery + responsive rail frontend implementation
pass), and Phase 30C (its QA + screenshot evidence refresh) are complete; the
Phase 31 premium-graph-interaction series (31A–31H) is complete and merged into
`main`, with Phase 31I implemented on a feature branch but not yet merged. The
current phase is the docs-only **Phase 32A.6 — Roadmap 31-Series Status
Refresh**.

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

The current phase sequence:

| Phase | Status | Focus |
| --- | ---: | --- |
| Phase 28D | Complete | README / portfolio visual lock (documentation only). |
| Phase 29A | Complete | Graph interaction + overlay polish planning (planning only, before any implementation). |
| Phase 29B | Complete | Graph interaction + overlay polish frontend implementation pass (screenshot evidence deferred to Phase 29C). |
| Phase 29C | Complete | QA + screenshot evidence refresh; see the [evidence doc](docs/demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md). |
| Phase 30A | Complete | Post-polish interaction triage + next frontend direction planning (planning only, before any implementation); triages the two Phase 29C interaction limitations and locks the narrow Phase 30B contract. See the [planning doc](docs/phase-30a-post-polish-interaction-triage.md). |
| Phase 30B | Complete | Interaction Recovery + Responsive Rail Frontend Implementation Pass (frontend only, per the Phase 30A contract); landed in code via PR #109. |
| Phase 30C | Complete | Interaction Recovery QA + Screenshot Evidence Refresh (QA / evidence only, after Phase 30B); re-ran the connected runtime and verified the Phase 30B fixes (PR #110). See the [evidence doc](docs/demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md). |
| Phase 31A | Complete | Premium Graph Interaction + Portfolio Demo Direction Planning (planning only); defines the premium interaction model, overlay/command-surface direction, and portfolio demo story. Merged into `main` (PR #111). See the [planning doc](docs/planning/phase-31a-premium-graph-interaction-portfolio-demo-direction.md). |
| Phase 31B | Complete | Premium graph interaction frontend pass; type-owned aura rings and the `selected > related > ambient` emphasis tiers over the existing SVG view model. Merged into `main` (PR #112). Graph read-only. |
| Phase 31C | Complete | Premium graph interaction expansion + overlay motion pass (frontend CSS-only, merged into `main`); hover reveals local structure and the summoned overlays gain a premium contextual entrance. Reduced-motion guarded. |
| Phase 31D | Complete | Overlay tooling + graph-surface usability pass (frontend CSS-only, merged into `main`); interaction-aware Esc hint, clearer overlay structure, and a graph-owned active-overlay accent. |
| Phase 31E | Complete | Graph surface visual density + interaction depth (frontend CSS-only, merged into `main`); region glows + lattice and a deeper active-interaction hierarchy. Colour stays graph-owned. |
| Phase 31F | Complete | Graph micro-interaction + command-surface refinement (frontend only); unified node transition easing and a faint hovered-node aura tier. Merged into `main` (PR #116). |
| Phase 31G | Complete | Consolidate graph aura/overlay CSS cascade overrides (frontend only, merged into `main`); merges the stacked 31B–31F declarations into authoritative rules with **no computed-style change**. |
| Phase 31H | Complete | Improve graph related-node + label readability (frontend only); a brighter related-node ring and a subtle label halo. Merged into `main` (PR #117); current `main` HEAD. |
| Phase 31I | Pending (not merged) | Graph overlay legibility + command-surface final polish (frontend only); **implemented on branch `phase-31i-graph-overlay-legibility-command-surface-final-polish` (commit `6bba994`) but not yet merged into `main`.** |
| Phase 32A | Complete (docs) | Motion input + orbital graph feasibility planning (research / documentation only) for the future experimental track. Completed on its planning branch. |
| Phase 32A.5 | Complete (docs) | Roadmap conflict-marker cleanup (docs-only, commit `cd0fefc`); did not land on `main`, so the markers persisted until Phase 32A.6. |
| Phase 32A.6 | Complete | Roadmap 31-series status refresh (docs-only); reconciles the roadmap/README with actual repository history and resolves the stale roadmap conflict markers. |
| Phase 32B | Complete | Standalone Webcam Motion Sandbox (frontend-only, merged into `main` via **PR #118**); an isolated "Motion" dock pane that requests the webcam only on explicit user action and derives a normalized `MotionCommand` from a dependency-free frame-difference loop, purely for inspection. Never touches the graph; no MediaPipe/dependency/backend change. |
| Phase 32C | Complete | Motion Sandbox QA + Control Contract Hardening (frontend-only); runtime-QAs the sandbox and hardens the local `MotionCommand` contract (explicit `active` / `source` / `timestamp` fields, pitch-sign fix, Idle/Active chip + direction hints). See [Motion Sandbox Control Contract + QA](docs/motion-sandbox-control-contract.md). **No graph wiring, no MediaPipe.** |
| Phase 32D | In progress | MediaPipe / Hand-Landmark Motion Detection (frontend-only, this phase); adds a MediaPipe Hand Landmarker estimator as the primary detector, populating the same hardened `MotionCommand` shape (`source` discriminates) so `zoomDelta` (approximate single-camera proxy) and `pinchActive` (thumb/index distance) go live. Frame-difference kept as a zero-dependency fallback; adds a landmark overlay + hand-detection readout and a small typed landmark-math helper. One **pinned** dependency (`@mediapipe/tasks-vision@0.10.35`); wasm/model fetched from version-pinned URLs, never committed/transmitted; camera stays explicit-start, local-only, no-storage, no-backend. **No graph control wiring.** |
| Phase 32E | Planned (next) | Orbital Graph Control Contract + Motion-to-Graph Wiring Planning — define how the hardened `MotionCommand` maps to graph orbit/zoom behaviour and plan the first real motion-to-graph wiring. |

The historical planned-phase table below is preserved as recorded phase
history; the [full roadmap](docs/roadmap.md) is the canonical, up-to-date
version.

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
| Phase 22C | UI navigation QA + screenshot evidence refresh (QA / evidence / documentation only); re-run the local backend (`8787`) and frontend (`5173`) and capture honest evidence that the Phase 22B section navigation is visible and usable over the connected dashboard (sticky nav, `id` anchors, scrollspy active-section highlight, skip link), confirm the same connected backend data as Phase 21C/21F and a passing frontend build, and record a `phase-22c-connected-*` screenshot set. See the [evidence doc](docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md). **Complete.** |
| Phase 25A | Premium visual design system / frontend presentation direction (planning / documentation only); define a buildable premium dark-metallic intelligence-console visual system with a graph-forward identity before any UI/CSS change — visual baseline, target identity, design principles, surface/panel system, typography/hierarchy, graph-centered experience direction (with *planned* read-only overlay concepts), Intelligence-Report real-vs-planned visual contract, navigation/demo-flow direction, and the Phase 25B/25C boundaries. Graph stays read-only; nothing faked. See the [planning doc](docs/ui/phase-25a-premium-visual-system-planning.md). **Active.** |
| Phase 25B | Premium visual system implementation pass (frontend presentation only); apply the Phase 25A direction through the CSS token system (dark metallic palette, elevation/spacing/type/glow tokens) and per-surface restyle of header/command-bar, panels, cards, section nav, graph framing/visual language, inspector, Intelligence Report sections, and console — no backend/API/schema/contract/data/graph-logic/graph-mutation/dependency change; graph stays read-only. **Planned (next frontend implementation pass).** |
| Phase 25C | Premium visual system QA + screenshot evidence (QA / evidence / documentation only); re-run the local backend (`8787`) and frontend (`5173`), confirm the reskin changed appearance only by verifying the same connected backend data as the 21C/21F/22C/23B baseline and a passing frontend build, capture a `phase-25c-connected-*` set on the dark theme (preserving prior history), and record an evidence doc. **Planned.** |
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

- **End-to-end ownership.** A React/FastAPI app with a local data model, a
  Source Registry and import pipeline, a graph-primary Knowledge Graph surface,
  and a derived intelligence layer — designed, built, documented, and QA'd
  across a recorded phase history.
- **Deterministic, backend-derived intelligence surfaces.** Dreaming
  Suggestions, Temporal Knowledge Decay, Provenance Chains, and Query Trails
  are all computed by reviewable backend rules over real store state — read-only,
  reproducible, and auditable, with honest empty states.
- **Engineering judgment over feature count.** A bounded scope done well, with
  deferred work named explicitly instead of implied as present.
- **Security reasoning, evidenced.** A threat model, a defensive API-hardening arc,
  and regression evidence — security treated as something to reason about and test,
  not decorate.
- **Disciplined use of assisted development.** Hive|Mind is a human-directed
  devdevbuilds project that uses assisted development tooling ethically:
  agents may draft, but every change passes human review, validation, and
  merge control, and no AI mutates the project — or its data — unreviewed.
- **Honesty as a feature.** The deterministic, read-only, local-first framing is
  precise about what the tool does and does not do — a tool-first demo project,
  not a production platform — which is more credible than an inflated
  "AI platform" claim.

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
- [Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](docs/demo/phase-23b-ui-readability-qa-screenshot-evidence.md)
- [Phase 24A Portfolio Screenshot + README Visual Lock](docs/demo/phase-24a-portfolio-screenshot-readme-visual-lock.md)
- [Phase 25A Premium Visual Design System / Frontend Presentation Direction](docs/ui/phase-25a-premium-visual-system-planning.md)
- [Frontend Asset Contract + Icon Usage Planning](docs/frontend-asset-contract.md)
- [Phase 27E Full-Viewfinder Graph Surface QA + Screenshot Evidence Refresh](docs/demo/phase-27e-full-viewfinder-graph-surface-qa-screenshot-evidence.md)
- [Phase 28A True Graph-Primary Surface + Overlay Contract](docs/phase-28a-true-graph-primary-overlay-contract.md)
- [Phase 28C True Graph-Primary Surface QA + Screenshot Evidence Refresh](docs/demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md)
- [Phase 28D Visual Direction Lock](docs/portfolio/phase-28d-visual-direction-lock.md)
- [Phase 29C Graph Interaction + Overlay Polish QA + Screenshot Evidence Refresh](docs/demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md)
- [Demo Guide](docs/demo-guide.md)
- [Demo Script (earlier walkthrough)](docs/demo-script.md)
- [Screenshot Checklist](docs/screenshot-checklist.md)
- [Phase 11 Demo Readiness](docs/phase-11-demo-readiness.md)
- [Phase 12A Demo Freeze + Release Snapshot](docs/releases/phase-12a-demo-freeze.md)
- [Phase 14E Dreaming Suggestions E2E Evidence](docs/qa/phase-14e-dreaming-suggestions-e2e-evidence.md)
- [Roadmap](docs/roadmap.md)

