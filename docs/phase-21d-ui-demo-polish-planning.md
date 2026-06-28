# Phase 21D — UI Demo Polish Planning / Dashboard Refinement Scope

Parent label: **devdevbuilds**

**Status: complete (planning / documentation only).** Phase 21D defines the next
UI demo-polish direction for Hive|Mind **before** any UI implementation resumes.
It is a scoping pass: it states what the next polish work should improve, why each
refinement matters, and what must stay out of scope. It adds **no** backend,
frontend, CSS, source-code, package, config, API, schema, dependency, or test
change, and changes no application behavior. It is the planning successor to the
[Phase 21C Connected UI Screenshot + Runtime Evidence Refresh](demo/phase-21c-connected-ui-evidence.md),
which confirmed the app is now genuinely connected.

> **Authenticity rule (carried from Phase 20A/20D/21C).** Any future polish must
> keep the UI an honest reflection of real, deterministic, read-only app behavior.
> Polish improves how implemented features *read*; it never invents AI, automation,
> persistence, mutation, or production readiness that does not exist.

---

## Why this phase exists (before touching UI code)

Earlier UI thinking risked optimizing a dashboard whose connected runtime behavior
was unverified — Phase 20D honestly recorded a `Failed to fetch` frontend. Phases
21A (shell), 21B (runtime-config alignment), and 21C (connected evidence) closed
that gap, so polish can now be planned against **observed connected behavior**
instead of disconnected assumptions.

**Why connected runtime evidence matters before UI polish.** Polishing a
disconnected shell bakes guesses into layout and copy. With 21C's connected
evidence (real "Connected" pill, live health, a rendered 7-node / 6-edge graph, a
backend-derived Intelligence Report), every refinement below can target a surface
we have actually seen render with real data.

**Why this is split from implementation.** Locking scope and rationale first keeps
the implementation phase (21E) small, reviewable, and honest — it prevents
scope-creep into redesigns, new panels, or invented behavior under the banner of
"polish," and preserves the human merge gate.

---

## 1. Current UI state

| Aspect | State entering 21D |
| --- | --- |
| Dashboard shell | Exists (Phase 21A foundation: layout/scaffold/styles). |
| Connected runtime | Fixed (Phase 21B aligned the frontend API base-URL config; canonical backend `8787`, frontend `5173`). |
| Connected evidence | Captured (Phase 21C: "Connected" pill, live API health, rendered Knowledge Graph, backend-derived Intelligence Report). |
| Planning basis | Real observed connected behavior, not disconnected assumptions. |

Observed connected surfaces (from 21C evidence), in render order: header band →
**Backend connection** status → **API health** → **Vault summary** (Phase-1
baseline) → **Source Registry** (connected empty state) → **Knowledge Graph**
(7 nodes / 6 edges) → **Intelligence Report** (Dreaming empty; Temporal Decay 7,
Provenance 7, Query Trails 7 — all BACKEND-DERIVED) → **Console**.

> **Why list the real surfaces.** The refinement priorities below name only
> surfaces that already exist and already render — so polish stays additive to what
> ships, never aspirational.

---

## 2. Dashboard refinement priorities

Priority order is roughly "what most improves a first-glance read" first. Each
target says *what* to refine and *why it matters*; none prescribes specific
markup, classes, or values (that is 21E's job, within its guardrails).

### 2.1 Visual hierarchy
- **Refine:** Establish a clear primary→secondary→tertiary read across the page so
  the eye lands on connection status and the two headline surfaces (Knowledge
  Graph, Intelligence Report) before the supporting panels.
- **Why:** A reviewer scanning a screenshot for three seconds should grasp "what
  this app is" without reading every label. Hierarchy is the highest-leverage,
  lowest-risk polish — **why it should come before advanced animation:** motion
  decorates a layout that already reads; it cannot rescue one that does not.

### 2.2 Panel spacing and density
- **Refine:** Normalize inter-panel spacing, padding, and grouping so related
  panels (connection + health; graph + intelligence) read as cohesive blocks
  rather than a flat stack.
- **Why:** The connected dashboard has many panels; consistent rhythm reduces
  visual noise and makes the full-page capture legible instead of crowded.

### 2.3 Connected data readability
- **Refine:** Improve how real connected values (counts, versions, badges, empty
  vs. populated states) are typeset and labeled so they read as *data*, not chrome.
- **Why:** The whole point of 21A–21C was proving the app shows real data; polish
  should make that data the visual focus. **Why it stays read-only:** readability
  is presentation; the values themselves remain backend-derived and untouched.

### 2.4 Intelligence Report presentation
- **Refine:** Tighten the four-section layout (Dreaming, Temporal Decay,
  Provenance, Query Trails) for consistent section headers, BACKEND-DERIVED
  badging, row density, and empty-state parity.
- **Why:** This is the project's signature surface. Consistent section treatment
  reinforces the honest "deterministic, read-only intelligence" story and prevents
  any section from looking more "AI-magic" than it is.

### 2.5 Knowledge Graph presentation
- **Refine:** Improve legibility of the SVG graph map, legend, node labels, and the
  groups / top-connected lists at typical capture sizes.
- **Why:** The graph is the most visually distinctive panel; a clean, readable
  graph is the strongest single screenshot for portfolio impact.

### 2.6 Source Registry presentation
- **Refine:** Make the connected **empty state** ("No sources registered yet") read
  as an intentional baseline rather than a defect.
- **Why:** An honest empty state is fine, but it should *look* deliberate so
  reviewers read "ready, nothing imported yet" instead of "broken." **Why honest
  framing matters:** it preserves the authenticity rule — no fake seeded sources.

### 2.7 Console placement / readability
- **Refine:** Confirm console position and typography support readability without
  pulling focus from the headline surfaces.
- **Why:** The console is supporting context; it should be present and legible but
  not compete with the graph/report for first-glance attention. **Console behavior
  must not change** — placement/readability only.

### 2.8 Responsive behavior
- **Refine:** Verify and tidy how the layout reflows at common widths so panels
  remain readable rather than collapsing awkwardly.
- **Why:** Reviewers open portfolios on varied screens; predictable reflow protects
  the first impression. Kept low in priority because **screenshot legibility at the
  canonical capture size matters more than full responsive polish for a demo.**

### 2.9 Screenshot / demo friendliness
- **Refine:** Ensure the dashboard composes cleanly into the established capture
  set (top band, knowledge graph, intelligence report, full page).
- **Why:** Screenshots are the portfolio artifact. If the layout captures well, the
  [21C evidence set](demo/phase-21c-connected-ui-evidence.md) can be refreshed with
  stronger images in a later evidence pass — without restaging anything.

---

## 3. Demo polish goals

- **Make the app easier to understand in screenshots.** A reviewer should infer the
  data flow (sources → graph → intelligence) from the images alone.
- **Improve first-glance portfolio impact.** Hierarchy + readable headline surfaces
  do most of this work before any decorative effort.
- **Preserve honest representation of implemented features.** Every polished surface
  must map to behavior that actually exists and is read-only.
- **Avoid implying fake capability.** No visual choice may suggest fake AI/LLM
  reasoning, fake automation, fake persistence, or fake production readiness.

> **Why demo polish must not imply production readiness.** Hive|Mind is honestly
> scoped as a local-first, single-user, demo-grade tool. Polish that reads as
> "deployed product" (uptime badges, fake user data, success toasts for actions
> that do not persist) would break the authenticity rule and undercut the
> credibility the disciplined scope earns. Demo readiness ≠ production readiness.

---

## 4. Refinement boundaries

**What should be improved (visual / presentation only):**
- Visual hierarchy, spacing/density, typography, labeling, badge/empty-state
  presentation, graph/report legibility, responsive reflow, screenshot composition.

**What must NOT change (logic / behavior):**
- Backend code, API clients, API contracts, schemas, runtime/build/package config.
- Intelligence derivation, Knowledge Graph logic, Source/import logic, Obsidian
  importer behavior, console behavior.
- The data values shown (they stay backend-derived and read-only).
- No new dependencies, panels, fake data, mocked intelligence, AI/LLM, persistence,
  auth, mutation, live sync, or dashboard redesign.

> **Why dashboard refinement stays read-only and non-mutating.** The project's
> core promise is deterministic, read-only surfaces before any mutation/automation.
> Polish that introduced an action which appeared to change state would either lie
> (no persistence) or quietly cross the read-only boundary — both are out of scope.

**What must wait for later phases:**
- Advanced animation/motion, theming systems, new panels or inspectors, any
  feature that needs new backend data, and any UI that implies persistence/auth.

---

## 5. Recommended next phase

**`Phase 21E — UI Demo Polish Implementation Pass`** — a scoped, frontend-only
implementation of the priorities above, in priority order, with screenshot
verification.

**21E should be allowed to touch:**
- Frontend presentation only: dashboard layout/markup for hierarchy and grouping,
  CSS/styles for spacing/density/typography/legibility, label and empty-state copy
  that stays factually accurate, and responsive/screenshot-composition tweaks.

**21E must NOT touch:**
- Backend code, API clients/contracts, schemas, intelligence/graph/source/import
  logic, console behavior, Obsidian importer, runtime/build/package config, tests,
  branding/assets, or the displayed data values. No new dependencies, panels, fake
  data, AI/LLM, persistence, auth, mutation, live sync, or redesign.

**Suggested 21E sequencing (smallest honest steps first):**
1. Visual hierarchy + spacing/density (2.1–2.2).
2. Connected data + Intelligence Report + Knowledge Graph readability (2.3–2.5).
3. Source Registry empty-state and Console readability (2.6–2.7).
4. Responsive + screenshot-friendliness pass (2.8–2.9), then an optional follow-up
   evidence-refresh phase to re-capture stronger connected screenshots.

> **Why a separate implementation phase.** Keeping scope here and implementation in
> 21E keeps each diff small and reviewable, preserves the human merge gate, and
> guarantees polish is measured against this locked scope rather than improvised.

---

## Honesty boundaries (unchanged)

- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- Plans reflect a **local, single-user, demo-grade** runtime — not a production or
  hosted deployment.
- This document is planning intent, not a guarantee that 21E ships exactly as
  sequenced; the human merge gate decides what lands.

## Scope confirmation

Phase 21D did **not** change backend, frontend, CSS, source code, package files,
configs, schema, dependencies, tests, any API contract, or any runtime behavior;
added no AI/LLM, persistence, auth, or mutation; and added no UI implementation.
The change set is documentation/planning only: this planning document plus narrow
status/link updates to the README and roadmap. **No application behavior changed.**
