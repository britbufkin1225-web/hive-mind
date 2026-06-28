# Phase 22A — UI Navigation + Demo Flow Planning

Parent label: **devdevbuilds**

**Status: complete (planning / documentation only).** Phase 22A defines how
Hive|Mind should handle UI **navigation, section ordering, demo flow, and
presentation sequencing** **before** any UI implementation resumes. It is a
scoping pass: it inventories the dashboard sections that exist today, documents
the current demo flow, names the navigation/demo pain points, and proposes a
controlled navigation model plus acceptance criteria for a future
implementation phase (Phase 22B). It adds **no** backend, frontend, CSS,
source-code, package, config, API, schema, dependency, or test change, and
changes no application behavior. It is the planning successor to the
[Phase 21F UI Demo Polish QA + Screenshot Evidence Refresh](../demo/phase-21f-ui-demo-polish-qa-evidence.md),
which confirmed the Phase 21E-polished dashboard is still connected to the
backend, and it builds on the
[Phase 21D UI Demo Polish Planning / Dashboard Refinement Scope](../phase-21d-ui-demo-polish-planning.md).

> **Authenticity rule (carried from Phase 20A/20D/21C–21F).** Any future
> navigation work must keep the UI an honest reflection of real, deterministic,
> read-only app behavior. Navigation improves how the *existing* surfaces are
> reached and read; it never invents pages, AI, automation, persistence,
> mutation, or production readiness that does not exist.

---

## Why this phase exists (before touching UI code)

The dashboard is a single connected page that has grown to **seven** stacked
top-level surfaces. Phase 21D/21E/21F made each surface read well in isolation,
but nobody has yet decided how a reviewer is meant to **move** through them. The
risk is that Phase 22B improvises a nav — or worse, reaches for React Router and
splits a working single-page dashboard into route architecture it does not need
— without a locked model to build against.

**Why decide navigation before implementing it.** Navigation is structural: it
touches section ordering, anchors, scroll behavior, and the page's top-level
layout. Deciding the model first keeps the 22B diff small and reviewable, keeps
the human merge gate meaningful, and prevents "while I was here" routing
complexity from landing under the banner of "navigation polish."

**Why this is split from implementation.** Locking scope and rationale here lets
22B be a narrow, frontend-only pass measured against this document rather than
improvised at the keyboard.

---

## 1. Current dashboard section inventory

Read directly from [`apps/frontend/src/App.tsx`](../../apps/frontend/src/App.tsx)
and the panel components. The app is a single React page: one `<main>`, rendered
top-to-bottom, **no router, no nav element, and no section anchors** today.

| # | Surface (render order) | DOM / component | Notes |
| --- | --- | --- | --- |
| 1 | **Hero / system identity** | `header.app-header` | `devdevbuilds` parent label, `Hive|Mind` title, tagline, `read-only demo build` badge. |
| 2 | **Backend connection** | `section.panel-connection` (in `.status-row`) | Connected / Disconnected / Checking status pill. |
| 3 | **API health** | `section.panel-health` (in `.status-row`) | Service / Version / Healthy metric grid. Sits beside #2 in a two-up row. |
| 4 | **Vault summary** | `section.panel-vault` | Files / Sources / Models / Nodes / Graph mode + message. |
| 5 | **Source Registry** | `<SourceRegistryPanel />` | Source list **and** the nested **Obsidian import** form (`ObsidianImportPanel`). |
| 6 | **Knowledge Graph** | `<KnowledgeGraphPanel />` | Read-only SVG graph, legend, groups, top-connected lists. |
| 7 | **Intelligence Report** | `<IntelligenceReportPanel />` | Four backend-derived sections: Dreaming, Temporal Decay, Provenance, Query Trails. |
| 8 | **Console** | `<ConsolePanel />` | Safe local query surface. |

> **Important structural fact for the demo flow.** The **Obsidian import
> controls are not a top-level section** — they live *inside* the Source Registry
> panel (`ObsidianImportPanel`). The suggested demo sequence's "Obsidian Import
> controls" step therefore maps to a **sub-section of Source Registry**, not a
> separate panel. Any nav must reflect the real DOM, not an idealized one.

**Current navigation state, stated honestly:**

- No navigation bar, no menu, no in-page links.
- No `id` anchors on any section, so nothing is directly linkable or jump-to-able.
- Movement is **manual vertical scroll only**.
- No active-section indication, no scroll memory, no keyboard jump targets.
- Connection + API health share one horizontal `.status-row`; everything else is
  a full-width vertical stack.

---

## 2. Current dashboard / demo flow

How a reviewer experiences the app **today**:

1. Page loads; `App.tsx` fires `getHealth()` + `getVaultSummary()` on mount; the
   connection pill resolves to **Connected** and health/vault populate.
2. The reviewer reads the hero, then scrolls down through connection → health →
   vault → sources (with the import form) → graph → report → console.
3. There is no signpost for "how far down does this go" or "what should I look at
   first" — the reviewer infers the data-flow story (sources → graph →
   intelligence) only by scrolling far enough to see all of it.

This order already roughly matches the locked data-flow narrative from the
[Portfolio Presentation Lock](../demo/portfolio-presentation-lock.md) and
[Final Demo Script](../demo/final-demo-script.md): **identity → trust the
connection → see the sources → see the graph → see the derived intelligence →
try a query.** The *ordering* is sound; what's missing is a way to **navigate**
and **signpost** it.

---

## 3. Navigation / demo-flow pain points

| Pain point | Effect on a demo / review |
| --- | --- |
| **No nav and no anchors** | A reviewer cannot jump to "Knowledge Graph" or "Intelligence Report" — the two headline surfaces — without scrolling past everything above them. |
| **Long single scroll** | Eight surfaces stacked vertically make the page feel long; the payoff surfaces (graph, report) are near the bottom. |
| **No "you are here" cue** | Nothing tells the reviewer how many sections exist or where they are in the flow, so they may stop scrolling early and miss the report/console. |
| **Import controls are buried** | Because Obsidian import lives inside Source Registry, a reviewer scanning top-level surfaces may not realize import exists. |
| **No demo-driven entry order** | Presenter and reviewer have no shared, signposted path; each demo improvises the scroll. |
| **No deep-linkable sections** | Screenshots/docs can't link to a specific surface (e.g. `#intelligence-report`) because no anchors exist. |

> **Why these are real (not cosmetic).** Phase 21 made each surface *read* well;
> this is about whether a reviewer can *find and traverse* them in a 60–90s
> portfolio look. Discoverability and traversal are exactly what a single
> long-scroll page is weakest at.

---

## 4. Proposed navigation model for Phase 22B

**Recommended direction: keep the single page; add an in-page section nav with
anchored sections. Do not introduce React Router.**

### 4.1 Single-page section navigation (recommended)

- Keep the app as **one connected page**. Add a lightweight **section nav** (a
  sticky/top nav of in-page anchor links) plus a stable `id` on each top-level
  surface.
- Nav links scroll to the matching section; the connected dashboard behavior is
  otherwise unchanged.

**Why single-page section nav fits this project:**

- The app **is** one connected dashboard telling one linear data-flow story; that
  is a natural fit for anchored section navigation, not multi-page routing.
- It is **additive and low-risk**: `id` anchors + a nav list + scroll behavior,
  with **no new dependency** and no change to any panel's logic or data.
- It preserves the **connected runtime** exactly — all panels still mount on the
  same page and fetch the same backend data.
- It keeps the page **honest**: every nav item points to a surface that already
  exists and already renders real data.

### 4.2 Defer React Router / route-based navigation (recommended)

**Defer routing.** Do **not** add React Router or split the app into routes in
22B.

**Why defer routing:**

- There are **no second pages** to route to. Routing would either create empty
  shells or **fake pages** — both violate the authenticity rule.
- React Router is a **new dependency** and an **architectural commitment**
  (route tree, history, layout split) that this single-surface tool does not yet
  justify.
- Premature routing **fragments** a dashboard whose whole value is showing the
  data-flow on one connected surface.
- A future phase can revisit routing **if and when** genuinely separate
  pages/inspectors exist (e.g. a dedicated source-detail or graph-detail view) —
  but that is a deliberate later decision, not 22B's job.

### 4.3 Suggested nav items

Mirror the real top-level surfaces (import stays *inside* Source Registry, so it
is **not** its own nav item):

| Nav label | Target section `id` (suggested) |
| --- | --- |
| Overview | `#overview` (hero / identity) |
| Status | `#status` (connection + API health row) |
| Vault | `#vault` |
| Sources | `#sources` (Source Registry incl. import) |
| Graph | `#knowledge-graph` |
| Intelligence | `#intelligence-report` |
| Console | `#console` |

> **Why labels are short and surface-named.** Nav labels should match what the
> reviewer sees as section headers, so the nav reads as a table of contents for
> the page rather than marketing copy. Keep them honest and literal.

### 4.4 Suggested active-section behavior

- Highlight the nav item for the section currently in view (a simple scrollspy).
- **Why:** the "you are here" cue is the single biggest fix for the long-scroll
  problem — it tells the reviewer how far through the flow they are and that more
  remains below.
- **Recommended technique (for 22B to implement, not now):** a single
  `IntersectionObserver` over the section `id`s, toggling an `aria-current` /
  active class on the matching nav link. No new dependency required.
- **Honesty/scope note:** scrollspy is presentation only — it observes scroll
  position and toggles a class; it changes no data and no panel behavior.

### 4.5 Suggested scroll / anchor behavior

- Each top-level surface gets a stable `id`; nav links are anchor links to those
  ids.
- Use smooth in-page scrolling (CSS `scroll-behavior: smooth`) and
  `scroll-margin-top` on sections so a sticky nav does not overlap the section
  heading after a jump.
- **Why CSS-first:** anchors + CSS scroll behavior need **no JavaScript and no
  dependency**, keeping the change minimal and robust. Respect
  `prefers-reduced-motion` so smooth scroll degrades to an instant jump.

### 4.6 Suggested keyboard / demo usability notes

- Nav items should be real, focusable anchor links (keyboard-tabbable, activatable
  with Enter), not click-only handlers.
- Add a **"skip to content"** affordance and ensure each section heading is a
  reachable focus target after a nav jump (`tabindex="-1"` on the section or
  heading where needed) so keyboard and screen-reader users land correctly.
- Mark the active nav link with `aria-current="true"` for assistive tech.
- **Why:** a demo is often driven by keyboard; predictable focus and jump targets
  let a presenter move surface-to-surface without hunting with the mouse, and
  keep the nav accessible rather than mouse-only.

### 4.7 Suggested mobile / responsive considerations

- On narrow widths the nav should collapse gracefully — e.g. a horizontally
  scrollable nav strip or a stacked/compact list — rather than wrapping into a
  tall block that pushes the hero off-screen.
- The underlying section stack already reflows to a single column; the nav must
  not regress that.
- **Why kept modest:** consistent with Phase 21D, **screenshot legibility at the
  canonical capture size matters more than full responsive nav polish for a
  demo** — so a clean, simple responsive nav is enough; an elaborate mobile menu
  is out of scope.

### 4.8 Suggested demo walkthrough sequence

Evaluated against the **actual** structure. The suggested reviewer path maps
cleanly onto the current section order, with the import step correctly nested
under Sources:

1. **Hero / system identity** (`#overview`) — what this is: a local-first,
   read-only knowledge-graph dev tool by devdevbuilds.
2. **Runtime status / connection confidence** (`#status`) — the **Connected**
   pill + live API health prove it is genuinely talking to the backend.
3. **Source Registry** (`#sources`) — the registered sources, **and** the nested
   Obsidian **import controls** (call these out explicitly, since they are not a
   top-level surface).
4. **Knowledge Graph** (`#knowledge-graph`) — the read-only graph derived from
   those sources (the strongest single screenshot).
5. **Intelligence Report** (`#intelligence-report`) — the four backend-derived,
   read-only sections (the signature surface).
6. **Console** (`#console`) — a safe local query against the same data.
7. **Evidence / demo-readiness framing** — close on the honesty boundaries
   (deterministic, read-only, no AI/LLM, local single-user, demo-grade) and point
   to the captured evidence docs.

> **Why this order (and why it already nearly matches the page):** it follows the
> locked data-flow narrative — **identity → trust → sources → graph → derived
> intelligence → query.** The current render order already encodes it; the nav
> simply makes that order **navigable and signposted** instead of scroll-only.
> The one honest adjustment vs. the generic suggested flow: **Vault summary**
> sits between Status and Sources today and can either keep that position or be
> folded visually near Status — 22B may decide, but it must not be deleted or
> faked.

---

## 5. How a reviewer should move through the UI

The intended demo traversal once 22B lands:

1. Land on the hero; confirm identity and the `read-only demo build` badge.
2. Click **Status** (or scroll) — confirm **Connected** + live health.
3. Click **Sources** — show the registry; point out the **Obsidian import** form
   nested inside it.
4. Click **Graph** — let the read-only graph carry the visual.
5. Click **Intelligence** — walk the four backend-derived sections.
6. Click **Console** — run one safe local query.
7. Close on the evidence/honesty framing.

The active-section highlight should make each step obvious in screenshots and in
a live walkthrough, so a reviewer never wonders whether more remains below.

---

## 6. Acceptance criteria for the Phase 22B implementation pass

22B is **frontend-only**. It is acceptable when **all** of the following hold:

**Functional**

- [ ] A section nav lists the real top-level surfaces (§4.3) and each link scrolls
      to the matching section.
- [ ] Every top-level surface has a stable `id` anchor.
- [ ] The active section is indicated in the nav while scrolling (§4.4).
- [ ] Anchor jumps land with the heading visible (no sticky-nav overlap) and
      respect `prefers-reduced-motion`.
- [ ] Nav is keyboard-navigable with correct focus/`aria-current`; a skip-to-
      content affordance exists (§4.6).
- [ ] Nav reflows acceptably at narrow widths without breaking the hero (§4.7).

**Honesty / non-regression**

- [ ] **No new pages and no fake content** — every nav item targets an existing,
      real surface.
- [ ] **No React Router / routing dependency** added.
- [ ] **No new dependency** of any kind.
- [ ] The **connected dashboard behavior is preserved** — all panels still mount
      on one page and fetch the same backend data; no data values change.
- [ ] **No backend, API, contract, schema, persistence, source-registry, graph,
      intelligence, Obsidian-import, or console behavior changes.**
- [ ] No dashboard redesign; the change is **additive** nav + anchors + scroll
      behavior over the existing layout.

**Verification**

- [ ] `npm run check:frontend` passes (and `npm run build` if used by the 22B
      diff).
- [ ] The demo walkthrough (§4.8) is reproducible against the locally running
      connected app, with screenshots refreshed **only if** the existing evidence
      pattern requires it.

---

## 7. Recommended next phase

**`Phase 22B — UI Section Navigation Implementation Pass`** — a scoped,
frontend-only implementation of the model above.

**22B should be allowed to touch:**

- Frontend presentation/structure only: a nav component/markup, `id` anchors on
  existing sections, CSS for sticky nav + scroll behavior + active state, and the
  scrollspy wiring — within the acceptance criteria in §6.

**22B must NOT touch:**

- Backend code, API clients/contracts, schemas, persistence, intelligence / graph
  / source / import logic, console behavior, the Obsidian importer, runtime /
  build / package config, or the displayed data values. No new dependencies, no
  React Router, no new panels, no fake pages, no fake data, no redesign.

---

## Honesty boundaries (unchanged)

- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- Plans reflect a **local, single-user, demo-grade** runtime — not a production
  or hosted deployment.
- This document is planning intent, not a guarantee that 22B ships exactly as
  described; the human merge gate (devdevbuilds) decides what lands.

## Scope confirmation

Phase 22A did **not** change backend, frontend, CSS, source code, package files,
configs, schema, dependencies, tests, any API contract, or any runtime behavior;
added no AI/LLM, persistence, auth, mutation, routing, or UI implementation. The
change set is documentation/planning only: this planning document plus narrow
status/link updates to the README and roadmap. **No application behavior
changed.**
