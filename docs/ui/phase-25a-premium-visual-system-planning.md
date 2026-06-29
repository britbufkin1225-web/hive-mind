# Phase 25A — Premium Visual Design System / Frontend Presentation Direction

Parent label: **devdevbuilds**

**Status: active (planning / documentation only).** Phase 25A defines a buildable
visual design system and frontend presentation direction for Hive&#124;Mind's next
implementation pass — **before** any UI code, CSS, or component is touched. It is a
scoping/design pass: it states the target visual identity, the design principles,
the surface/panel system, the typography and graph-centered direction, and exactly
what the follow-up implementation phase (25B) may and may not build. It adds **no**
frontend, CSS, backend, API, schema, package, dependency, or runtime change, and
changes no application behavior. It is the design successor to the
[Phase 24A Portfolio Screenshot + README Visual Lock](../demo/phase-24a-portfolio-screenshot-readme-visual-lock.md)
and builds on the connected, captured baseline from
[Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](../demo/phase-23b-ui-readability-qa-screenshot-evidence.md).

- **Phase name:** Phase 25A — Premium Visual Design System / Frontend Presentation Direction
- **Date:** 2026-06-28
- **Branch:** `phase-25a-premium-visual-system-planning`
- **Repo:** `hive-mind` (Hive&#124;Mind under devdevbuilds)

> **Authenticity rule (carried from Phase 20A/21D/24A).** Every visual choice below
> must keep the UI an honest reflection of real, deterministic, read-only app
> behavior. A premium look improves how the *implemented* features read; it never
> invents AI, automation, persistence, mutation, live telemetry, or production
> readiness that does not exist. "Cinematic" is a treatment of real surfaces, not a
> costume over fake ones.

---

## Why this phase exists (before touching UI code)

The Phase 21–24 arc made the dashboard **connected, readable, navigable, and
honestly captured**: a token system (21A), runtime-config fix (21B), connected
evidence (21C), demo polish (21E), section navigation (22B), readability/panel
hierarchy (23A), and a locked README visual story (24A). That work earned a
credible baseline — but it was deliberately *incremental polish*, not a coherent
visual identity. The risk now is a series of uncoordinated "premium" tweaks that
each look fine in isolation and add up to noise.

Phase 25A exists to **lock the visual direction once**, so the 25B implementation
pass is coherent rather than random polish, and so each diff can be measured
against an agreed target instead of improvised taste. Locking scope and rationale
first keeps 25B small, reviewable, and honest, and preserves the human merge gate.

**Why a design system, not a redesign.** The app does not need new panels, new
data, or a new architecture — it needs the *existing* surfaces to read as one
serious, premium product. A design system (tokens, hierarchy, surface rules,
graph language) is the cheapest, most reviewable way to get there: it reskins what
ships without changing what it does.

---

## 1. Current visual baseline

The honest starting point, drawn from the real Phase 23B connected captures and the
current frontend source (`apps/frontend/src/styles.css`, `App.tsx`, the four panel
components, and the SVG graph in `KnowledgeGraphPanel.tsx` /
`lib/graphViewModel.ts` / `lib/graphLayout.ts`).

| Aspect | State entering 25A |
| --- | --- |
| Theme | **Light.** `--bg: #eef0f3`, white panel surfaces (`--surface: #ffffff`), grey borders, single purple accent (`--accent: #6b4fbb`). |
| Token system | Present (Phase 21A): color, radius (`--radius: 10px`), shadow, and one spacing token (`--space-panel`) in `:root`; many per-panel rules track those neutrals. |
| Layout | Single-column `main` capped at `min(880px, …)`, vertical panel stack, sticky in-page section nav (Phase 22B). |
| Panel identity | Shared accent-tick `<h2>` headings, unified card/inspector rounding, hairline dividers, lifted muted-label contrast (Phase 23A). |
| Graph | Custom deterministic **SVG** map: summary band (7 nodes / 6 edges / 7 connected / 0 isolated), type/relationship/status legend, node/edge lists with roving-keyboard inspector sync. Read-only; no physics, no mutation. |
| Intelligence Report | Four backend-derived read-only sections with a `BACKEND-DERIVED` badge, `Mode Read-only`, and honest empty-states (Dreaming `0`). |
| Overall read | Clean, legible, **competent developer-dashboard** — but visually closer to a default admin panel than to a premium intelligence console. |

**Honest gap statement.** The baseline is *good and honest*; it is not yet
*visually impressive*. It reads as a tidy light dashboard, not as the serious,
graph-forward intelligence console the product intends to be. The biggest single
lever is the theme + surface treatment; the second is the graph's visual weight.

---

## 2. Target visual identity

Hive&#124;Mind should read as a **serious intelligence-console / developer-tool
product with a graph-centered identity** — premium, dark, and deliberate, without
"hacker cosplay."

- **Premium dark metallic interface.** Move from the current light theme to a dark,
  layered surface system with controlled metallic neutrals (graphite/slate/gunmetal),
  restrained accent color, and depth that comes from elevation and hairline borders
  rather than heavy drop shadows.
- **Serious intelligence-console aesthetic.** The feel of a focused analysis tool:
  dense-but-calm, information-first, with a clear command/inspection hierarchy. It
  should look like something a developer would *trust*, not a dashboard template.
- **Graph-forward product identity.** The Knowledge Graph is the signature surface
  and should become the primary visual anchor of the product in future phases.
- **High visual impact, honestly earned.** Impact from typography, spacing,
  contrast, and a strong graph — **not** from fake terminals, fake "scanning"
  animations, neon matrix rain, fake AI thinking states, or fabricated telemetry.
- **Controlled, not loud.** Glow, depth, borders, and contrast are *tuned* and
  consistent. One accent family, one or two functional status hues, restrained
  luminance — the opposite of a rainbow cyber dashboard.

**Anti-pattern guardrails (what "premium" is NOT here):**

- Not neon/hacker cosplay (no matrix rain, no fake CRT, no green-on-black terminal cosplay).
- Not fake liveliness (no invented activity feeds, pulsing "live" dots on static data, or motion that implies work that is not happening).
- Not contrast-for-drama at the cost of readability — this is a tool to be *read*.
- Not a redesign of behavior — same panels, same data, same read-only guarantees.

---

## 3. Design principles

The principles that should govern every 25B decision, in priority order.

1. **Honesty over spectacle.** No visual may imply capability that does not exist
   (AI, automation, persistence, mutation, multi-user, production telemetry). Real
   backend-derived data is styled as *data*; planned surfaces are clearly labeled.
2. **Hierarchy before decoration.** A reviewer should grasp "graph-centered
   intelligence console" within three seconds. Motion and glow decorate a layout
   that already reads; they cannot rescue one that does not.
3. **Depth through layering, not noise.** Establish surface elevation levels
   (background → panel → raised card → inspector/overlay) so depth is systematic,
   not ad-hoc shadows.
4. **One accent, disciplined status hues.** A single accent family for identity and
   focus; a small fixed set of functional colors (success / warning / error /
   neutral-derived) for status. No decorative color.
5. **Controlled glow and contrast.** Glow is a *focus and emphasis* tool (selected
   node, active nav, key metric), used sparingly and consistently — never ambient
   wash.
6. **Readability is non-negotiable.** Dark surfaces must hold WCAG-reasonable text
   contrast; dense Intelligence Report rows must stay scannable. A premium tool that
   is hard to read has failed.
7. **Token-first, additive.** Every change flows through the existing token system
   so it is consistent and reversible. No bespoke one-off colors scattered across
   components.
8. **Graph is the anchor.** When trade-offs arise, the choice that strengthens the
   graph's clarity and prominence wins.

---

## 4. Surface / panel system

Define a layered surface model the dark theme can express through tokens. The
current single `--surface` becomes a small elevation scale; this is a **token
expansion, not a structural rewrite** — the panels and DOM stay as they are.

**Elevation scale (target concept):**

| Level | Role | Treatment direction |
| --- | --- | --- |
| L0 — Canvas | App background | Deep metallic graphite; subtle vertical luminance, no busy texture. |
| L1 — Panel | Section surfaces (header, panels) | Slightly raised slate with hairline border; the default reading surface. |
| L2 — Card | Metric cards, legend, summary bands | A touch brighter/raised within a panel; clear grouping without boxing everything. |
| L3 — Inspector / Overlay | Node inspector, future overlays | Most-raised surface with the strongest border and the only place ambient glow is allowed. |

**Panel rhythm direction:**

- Consistent panel padding and inter-panel spacing driven by spacing tokens (extend
  the single `--space-panel` into a small scale).
- Hairline borders + elevation do the separation work; reduce reliance on heavy
  shadow.
- Group related surfaces visually (connection + health; graph + inspector;
  report sections) so the page reads as blocks, not a flat stack.
- Headers get a stronger "command bar" treatment (parent label, status pills, build
  badge) as the top of the hierarchy.

**Border / depth / glow rules:**

- Borders: hairline, two weights (soft divider vs. structural edge).
- Depth: elevation tokens (background tint + border + restrained shadow), not
  per-component shadows.
- Glow: reserved for **focus and selection** (active nav item, selected graph node,
  primary metric) — one accent glow token, used consistently.

---

## 5. Typography and hierarchy direction

- **Type scale.** Establish a deliberate scale (display / section / sub-section /
  body / metric / label/caption) instead of the current near-flat sizing. Metrics
  (counts, versions) should read as confident data, labels as quiet support.
- **Monospace as a deliberate accent.** Use a monospaced face for IDs, counts,
  versions, evidence keys, and console/graph metadata — the "instrument readout"
  texture of a serious tool — while keeping prose in the humanist UI font. This is
  treatment, not a new dependency assumption; the implementation phase decides the
  exact stack.
- **Weight and letter-spacing.** Reserve heavier weight + tight tracking for the few
  true headlines; widen tracking on small uppercase labels (already partly present)
  for the console-instrument feel.
- **Numeric emphasis.** The headline numbers (graph 7/6, report 0/7/7/7, health
  version) are the proof the app is real — give them typographic weight so they
  anchor each surface.
- **Hierarchy contract.** Primary → the connection proof + the two headline surfaces
  (Graph, Intelligence Report); secondary → supporting panels; tertiary → console
  and metadata. Typography must encode that ranking.

---

## 6. Graph-centered experience direction

The Knowledge Graph should become the **primary visual anchor** of the product. All
of the following are *visual-language and framing* targets over the existing
read-only SVG view model — **no graph logic, layout algorithm, or mutation behavior
changes**.

**Node / edge visual language:**

- A clearer node visual system: type-driven shape/color treatment with consistent
  borders, calmer fills, and a legible label treatment at capture sizes.
- Edge treatment that reads as relationship (weight/opacity/relationship color)
  without clutter; directional cue kept legible.
- A defined **selected / related / dimmed** visual language (the existing
  highlight/dim behavior), with the *only* sanctioned graph glow on the selected
  node and its neighborhood.

**Graph canvas framing:**

- Frame the SVG canvas as a deliberate "console viewport": a defined plotting area,
  subtle grid/backdrop treatment (controlled, not busy), and clear inset from the
  surrounding panel so it reads as the centerpiece, not a thumbnail.
- Give the graph more visual weight in the page hierarchy (size, framing, contrast)
  consistent with it being the anchor.

**Node inspector relationship:**

- Strengthen the canvas ↔ inspector relationship so selection feels like one
  coherent instrument: the inspector as the L3 raised surface, with a clear visual
  tie between the selected node and its detail panel.

**Legend / status treatment:**

- Promote the legend and summary band to a confident, readable "status strip"
  (node/edge counts, connected/isolated, type/relationship/status keys) that frames
  the graph rather than floating beside it.

**Future overlay concepts (planned, clearly non-implemented in 25B unless explicitly scoped):**

These are *visual-direction placeholders* for how existing backend-derived
intelligence could eventually be expressed **on or beside** the graph. They are
documented here so the visual system reserves space for them — they are **not**
authorized for build in 25B and must never be faked as live:

- **Temporal Decay overlay** — express the existing decay buckets (fresh/aging/stale)
  as a node freshness treatment or a toggleable overlay legend.
- **Dreaming Suggestions overlay** — surface existing duplicate/orphan/stale
  suggestions as advisory, dismissible annotations near the implicated nodes
  (advisory only; never auto-applied).
- **Provenance Chains overlay** — highlight an existing source→import→node→edge chain
  as a traceable path when a node is selected.
- **Query Trails overlay** — express existing trail projections as a lightweight
  path/breadcrumb treatment over the graph.

> **Overlay honesty rule.** Every overlay above maps to data the backend *already*
> derives, read-only. None introduces new derivation, query persistence, AI/LLM, or
> graph mutation. Any overlay that cannot be backed by real backend-derived data
> stays a documented future concept and is **not** drawn as if live.

**Graph stays read-only** unless a later, explicitly-scoped phase changes that. No
phase in the 25 series authorizes graph mutation.

---

## 7. Intelligence-report visual direction

The Intelligence Report is the product's differentiator and must look auditable, not
"magic."

- **Section system.** Treat the four sections (Temporal Decay, Dreaming Suggestions,
  Provenance Chains, Query Trails) as a consistent, scannable system: uniform section
  headers, the persistent `BACKEND-DERIVED` badge, `Mode Read-only`, and equal-weight
  empty-states so no section looks more "AI" than another.
- **Evidence as a first-class texture.** Style the `metadata.evidence` trails as a
  readable, monospaced "why" — the visible proof the signals are derived, not
  guessed. This is the single most credibility-building detail.
- **Honest empty-states.** A premium empty-state (e.g. Dreaming `0`) should read as a
  deliberate, designed baseline ("nothing derivable right now"), never as a defect or
  a teaser for fake content.
- **Real vs. planned distinction (visual contract).** Establish a clear, consistent
  visual treatment that distinguishes **real backend-derived data** from any
  **planned intelligence surface**. Real, derived sections carry the
  `BACKEND-DERIVED` badge; any future/planned surface must carry an unmistakable
  "planned / not yet derived" treatment so a reviewer can never mistake intent for
  implementation.
- **Summary band.** Promote the report summary (Suggestions 0 / Decay 7 / Provenance
  7 / Query Trails 7, version, mode) to a confident status strip that mirrors the
  graph's status strip — two anchored "instrument readouts" on the two headline
  surfaces.

---

## 8. Navigation / demo-flow direction

Build on the Phase 22B single-page section navigation; do not replace it.

- **Command-bar header.** Treat the top band as the product's command bar: parent
  label (`DEVDEVBUILDS`), product mark, connection + health pills, and the
  `READ-ONLY DEMO BUILD` badge, styled as the top of the hierarchy.
- **Premium section nav.** Restyle the existing sticky section nav as a refined dark
  rail/strip with a clear active-section state and the existing scrollspy cue — more
  "console navigator," same behavior (no router, no new pages).
- **Signposted demo flow.** Keep the established data-flow order (connection → sources
  → graph → intelligence → console) and make the visual hierarchy guide the eye along
  it, so the scroll itself tells the sources → graph → intelligence story.
- **Screenshot composition.** The dark theme should compose cleanly into the locked
  Phase 24A landing set (connected top, graph, intelligence report); 25B should keep
  those three frames as the strongest captures and improve, not disrupt, them.

---

## 9. Implementation boundaries for Phase 25B

**`Phase 25B — Premium Visual System Implementation Pass`** is the next frontend
implementation phase: a scoped, presentation-only application of this direction, in
priority order, with screenshot verification.

**25B may touch (frontend presentation only):**

- The CSS token system (`:root`) — introduce the dark metallic palette, elevation
  scale, spacing scale, type scale, and glow/border tokens.
- `styles.css` per-surface rules — restyle header/command bar, panels, cards,
  section nav, graph framing, inspector, Intelligence Report sections, and console to
  the new tokens.
- Presentational markup/class adjustments in `App.tsx` and the panel/graph components
  **only** where needed to express hierarchy, grouping, and the graph canvas framing
  — without changing data flow, props semantics, or behavior.
- Graph **visual language** over the existing view model (node/edge styling, selected/
  related/dimmed treatment, canvas framing, legend/status strip).
- Label/caption/heading copy that stays factually accurate, and responsive/screenshot
  composition tuning.

**25B must NOT touch:**

- Backend code, API clients, API contracts, schemas, runtime/build/package config.
- Intelligence derivation, Knowledge Graph **logic / layout algorithm / view model
  computation**, Source/import logic, Obsidian importer, console behavior.
- The displayed data values (they stay backend-derived and read-only).
- Graph mutation/editing/physics, node-position persistence, or any read-only
  boundary.
- New dependencies, new panels, new pages, a router, fake data, mocked intelligence,
  AI/LLM, persistence, auth, mutation, live sync/telemetry, or animated "liveliness."

**Suggested 25B sequencing (smallest honest steps first):**

1. **Token foundation** — dark metallic palette, elevation/spacing/type tokens,
   glow/border tokens (purely token-level; verify nothing breaks).
2. **Surface + command-bar pass** — apply elevation to header/panels/cards and the
   command-bar header.
3. **Graph anchor pass** — canvas framing, node/edge visual language, selected/
   related/dimmed treatment, legend/status strip.
4. **Intelligence Report pass** — section system, evidence texture, real-vs-planned
   visual contract, summary status strip.
5. **Nav + console + responsive/screenshot pass** — premium section rail, console
   readability, capture composition.

> Each step is an independent, reviewable diff measured against this document. The
> human merge gate decides what lands; this plan is intent, not a guarantee of exact
> implementation.

---

## 10. Explicit non-goals

The following are **out of scope** for the entire 25 series unless a later phase
explicitly and separately authorizes them:

- **No behavior changes.** No new features, no changed data flow, no new endpoints.
- **No graph logic / mutation.** No editing, physics, node-drag persistence, or
  layout-algorithm changes; the graph stays read-only.
- **No fake intelligence or AI.** No simulated AI reasoning, no fabricated activity
  feeds, no fake "live" telemetry, no invented suggestions.
- **No fabricated data or screenshots.** Real backend-derived values only; captures
  reflect the app exactly as built.
- **No production-readiness signaling.** No uptime badges, deploy status, multi-user,
  auth, or anything implying a hosted/SaaS product. It remains local-first,
  single-user, demo-grade.
- **No dependency/package changes** for visuals (no UI framework, CSS-in-JS, icon
  package, font package, or animation library is assumed by this plan; 25B works in
  plain CSS over the existing tokens).
- **No "tiny tweak" smuggling.** This planning phase ships **zero** UI/CSS/source
  change; 25B ships only what its boundaries allow.

---

## 11. QA / evidence expectations for Phase 25C

**`Phase 25C — Premium Visual System QA + Screenshot Evidence`** should, after 25B
lands:

- Re-run the local backend (`8787`) and frontend (`5173`) and verify the app is still
  **connected** with the **same** backend-derived values as the 21C/21F/22C/23B
  baseline: health `0.1.0`; graph **7 nodes / 6 edges / 7 connected / 0 isolated**;
  Intelligence Report **Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7**,
  `Mode Read-only`. The reskin must change *appearance only* — identical data proves
  no behavior changed.
- Confirm `npm run check:frontend` passes (and the backend check remains green).
- Capture a new `phase-25c-connected-*` screenshot set on the dark premium theme,
  superseding the `phase-24a` / `phase-23b-connected-*` landing images while
  **preserving** that history — no deletions.
- Re-verify the locked Phase 24A landing three-beat (connected top → graph →
  intelligence report) still reads as the strongest set on the new theme, and update
  the README **Visual evidence** captions if the surfaces moved.
- Spot-check readability/contrast on dark surfaces (Intelligence Report rows, graph
  labels, console output) so "premium" did not cost legibility.
- Record an evidence doc with honest captions and an explicit confirmation that the
  pass changed **presentation only** — no backend / API / schema / contract / data /
  graph-logic / package / dependency / runtime behavior change, and no fabricated
  screenshots.

---

## Honesty boundaries (unchanged)

- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- The Knowledge Graph stays **read-only** — no mutation, editing, physics, or layout
  changes are authorized by this plan.
- Plans reflect a **local, single-user, demo-grade** runtime — not a production or
  hosted deployment.
- This document is design intent, not a guarantee that 25B/25C ship exactly as
  sequenced; the human merge gate (devdevbuilds) decides what lands.

## Scope confirmation

Phase 25A did **not** change frontend source, CSS, backend, source code, package
files, configs, schema, dependencies, tests, any API contract, or any runtime
behavior; added no AI/LLM, persistence, auth, mutation, graph-logic, or graph
mutation; created no screenshots; and added no UI implementation. The change set is
documentation/planning only: this planning document plus narrow status/link updates
to the README and roadmap. **No application behavior changed.**
