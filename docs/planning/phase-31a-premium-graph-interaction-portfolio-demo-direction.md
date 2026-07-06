# Phase 31A — Premium Graph Interaction + Portfolio Demo Direction Planning

## Status

**Planning / documentation only. This is not an implementation phase.**

This document defines the next premium frontend direction for Hive&#124;Mind —
how the surface moves from a *functional graph-primary interface* toward a
*portfolio-grade premium graph intelligence demo* — before any implementation
begins. It changes **no** runtime UI, CSS, backend, contract, data, screenshot,
package, or dependency state. It writes planning prose, a minimal README status
reference, and roadmap rows only.

No fix, no CSS, no focus wiring, no rail change, and no graph behavior is
smuggled in under a planning heading. The interaction and overlay direction
described here is *implemented* in the proposed Phase 31B and *verified* in the
proposed Phase 31C — not before.

This phase inherits, in full, the locked direction from:

- [Phase 28A True Graph-Primary Surface + Overlay Contract](../phase-28a-true-graph-primary-overlay-contract.md)
  (including its Section 6 visual correction lock),
- [Phase 28D Visual Direction Lock](../portfolio/phase-28d-visual-direction-lock.md),
- [Phase 29A Graph Interaction + Overlay Polish Planning](phase-29a-graph-interaction-overlay-polish-planning.md),
- [Phase 29C QA + Screenshot Evidence](../demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md),
- [Phase 30A Post-Polish Interaction Triage](../phase-30a-post-polish-interaction-triage.md).

---

## Context

An honest reading of the repository at the time this plan was written — not the
aspirational one:

- **The graph-first shell exists and holds.** Phases 27A–28D established, then
  locked, the true graph-primary surface: the Knowledge Graph SVG fills the
  viewport edge-to-edge with no persistent sidebar, dashboard column, or
  card-grid framing; the masthead, control rail, and contextual dock are
  floating translucent glass overlays; the graph carries a living-identity
  groundwork (idle aura/breathing pulse, per-type resting halo, selection glow,
  animated energy-flow edges incident to the selection).
- **Phase 29 landed the interaction/overlay contract cleanly.** Phase 29B
  implemented the three-tier `selected > related > ambient` emphasis model,
  additive hover lifts, empty-canvas click-to-deselect, the Escape dismissal
  order, and overlay focus management; Phase 29C verified all of it against the
  connected runtime across 28 scripted checks and captured a
  `phase-29c-connected-*` screenshot set, recording two honest rough edges
  (Escape focus-scoping after dock close; focused-rail label overflow at
  ~420px).
- **Phase 30A triaged those two rough edges** and locked a narrow Phase 30B
  contract (planning only).
- **Phase 30B's interaction-recovery fix landed in code** via
  [#109](https://github.com/) ("Fix graph interaction recovery and responsive
  rail") — a frontend-only change to `apps/frontend/src/App.tsx`,
  `apps/frontend/src/components/KnowledgeGraphPanel.tsx`, and
  `apps/frontend/src/styles.css` (Escape/focus wiring after dock close; a
  narrow-viewport responsive rule for the focused/expanded rail). The status
  language in `README.md` / `docs/roadmap.md` had **not** been advanced to
  reflect that the code landed; Phase 31A corrects that stale "Planned"
  status as part of its minimal roadmap/README housekeeping.

### Honest limitation of the predecessor state

- **Phase 30C has not run.** There is no Phase 30C QA/screenshot-evidence
  document, no `phase-30c-*` commit, and no `phase-30`-series screenshots in
  `docs/demo/screenshots/`. The Phase 30B interaction-recovery fix is therefore
  **implemented but not yet independently QA-verified against the connected
  runtime, and its screenshot evidence does not yet exist.** This plan does
  **not** claim otherwise. The connected-runtime screenshot evidence that *does*
  exist is the Phase 29C set; the fresh evidence proving the 30B recovery fix —
  and, later, the premium 31B interaction — is still owed.

### Where that leaves Phase 31A

The foundation (graph-primary surface, overlay hierarchy, base interaction
model) is sound and locked. The 30-series arc was repair work — closing two
keyboard/responsive defects. Phase 31A deliberately does **not** open more
repair work. It defines the next *visible leap*: making the graph feel
*premium and alive* under interaction, and defining a portfolio demo that
proves that leap honestly. It also acknowledges an outstanding evidence debt
(Phase 30C) that Phase 31C's evidence pass can absorb rather than duplicate.

---

## Goals

Premium graph interaction and portfolio demo readiness, specifically:

1. **A premium, legible interaction model.** Hover, focus, select, deselect,
   and keyboard behavior that feels intentional and high-craft — emphasis that
   tells a story about the selected node and its relationships without becoming
   noisy, decorative, or fake.
2. **Selected-node storytelling.** When a node is selected, the graph should
   communicate *what this is and what it connects to* — through neighbor/edge
   emphasis and a promoted inspector — using only real, backend-derived data.
3. **A graph that feels alive but honest.** Aura/pulse/grouping/relationship
   energy concentrated in the graph itself, tuned so motion reads as *living
   intelligence*, never as a screensaver or as fabricated telemetry.
4. **Overlays that support, never compete.** Source Registry, Intelligence
   Report, Console, inspectors, and tools appear as contextual glass surfaces —
   a serious black/chrome/dev-tool viewfinder — never as sidebars, dashboards,
   or card grids.
5. **A portfolio demo direction.** A 30–90-second story a recruiter/viewer can
   follow, backed by real connected runtime states, with defined hero evidence
   and explicit honesty boundaries.
6. **A controlled implementation path.** A scoped Phase 31B (frontend
   implementation) and Phase 31C (QA + portfolio screenshot evidence), each with
   allowed/forbidden lists and acceptance criteria, so the leap stays reviewable
   and honest.

---

## Non-goals

Phase 31A does **not**:

- Implement any interaction, animation, overlay, or CSS change.
- Touch frontend source, CSS, backend, API, schema, contracts, data, packages,
  dependencies, tests (beyond docs tooling if strictly required), screenshots,
  or generated assets.
- Introduce any graph mutation, editing, or write behavior — the graph stays
  read-only.
- Add or propose any new graph library (no D3, Cytoscape, React Flow, Three.js,
  canvas force-layout, or 3D). The existing deterministic inline-SVG view model
  remains the substrate.
- Add AI/LLM behavior, fake liveliness, fabricated telemetry, or invented
  relationships.
- Reintroduce a dashboard, sidebar, or card-grid shell in any form.
- Capture or produce screenshots (that is Phase 31C's job).
- Claim Phase 30C is complete or that Phase 30B/31B screenshot evidence exists
  when the repository does not support it.

---

## Premium Graph Interaction Direction

The interaction model, state by state. All of it must render over the existing
deterministic SVG view model and the real 7-node / 6-edge connected graph — no
new engine, no physics, no layout algorithm, no fabricated nodes/edges.

### Default (at-rest) state

- The full-viewport graph, all nodes/edges legible, with the existing subtle
  idle aura/breathing pulse and per-type resting halo.
- Ambient energy is *low and even* — the resting graph should feel calm and
  intentional, not busy. Nothing pulses aggressively at rest; the at-rest state
  is the baseline against which emphasis reads.
- No overlay is forced open. The rail is icon-only/compact; the masthead is
  quiet. The graph owns the screen.
- **Rationale.** A premium tool is quiet until you touch it. A loud resting
  state destroys the contrast that makes hover/selection feel responsive, and
  reads as "fake liveliness" — the exact anti-pattern the 25A/28A locks forbid.

### Hover / focus state

- Hovering (or keyboard-focusing) a node produces a *restrained additive lift*:
  the node brightens/scales slightly, its label becomes fully legible, and its
  incident edges lift (the Phase 29B behavior, kept). Hovering an edge lifts its
  stroke and both endpoints.
- Hover is **additive and non-destructive** — it previews relationships without
  committing a selection and without dimming the rest of the graph to the degree
  selection does. Hover is a *whisper*; selection is a *statement*.
- Focus (keyboard) must produce a visible, equivalent emphasis to hover, so a
  keyboard user sees exactly what a mouse user sees. Focus-visible styling is
  mandatory, not optional.
- **Rationale.** Hover/focus is the "is this thing alive?" moment a reviewer
  tests first. Making it immediate, legible, and identical across pointer and
  keyboard signals craft and accessibility at once, without over-committing the
  view.

### Selected node state

- Selection is the **primary storytelling act.** On select, the graph resolves
  into the three-tier emphasis model (kept and sharpened from Phase 29B):
  - **Selected** — the node is clearly the protagonist: strongest glow/aura,
    full label, promoted visual weight.
  - **Related** — its direct neighbors and incident edges are emphasized
    (highlighted, energy-flow edges animated toward/around the selection) so the
    *relationship story* is legible at a glance.
  - **Ambient** — everything else recedes (dims/desaturates) but never
    disappears, preserving the sense of the whole graph as context.
- The **node inspector** promotes into a bounded floating glass card carrying
  the node's real, backend-derived detail (type, tags, provenance/edges as
  already available) — never a fabricated dossier.
- Selecting a different node switches emphasis **in place, flicker-free** (the
  verified Phase 29C behavior).
- **Rationale.** "Selected-node storytelling" is the single most portfolio-legible
  behavior the graph can offer: it turns a static picture into *this concept →
  these connections*. Concentrating emphasis into selected/related/ambient tiers
  is how the graph tells that story without a wall of chrome, and it is far
  stronger than adding another panel to explain the same relationships in text.

### Selected edge / relationship state

- Selecting an edge emphasizes the relationship itself: the edge lifts, its two
  endpoint nodes promote to a "related" emphasis, and the inspector reflects the
  relationship (its endpoints/type) using real edge data.
- Edge selection and node selection share one coherent emphasis vocabulary so
  the two never fight visually.
- **Rationale.** Relationships are the whole point of a knowledge graph. Making
  edges first-class selectable subjects — not just decoration between nodes —
  communicates that Hive&#124;Mind reasons about *connections*, not just items.

### Deselect / Escape behavior

- Empty-canvas click deselects (verified Phase 29C). Escape peels the interaction
  stack in the locked order — tertiary dock → explorer → selection/inspector,
  one surface per press — returning ultimately to the bare at-rest graph.
- The Phase 30B recovery fix (predictable Escape after dock close; focus returned
  inside the Escape scope, no focus trap) is assumed present in code and is a
  *precondition* for the premium layer, not a target to redo. If Phase 31C's
  verification finds the 30B fix regressed or incomplete, that is a bug to fix in
  the 31B window — but 31A does not reopen it as new design.
- **Rationale.** A premium interaction that a keyboard user cannot cleanly back
  out of is not premium. The deselect/Escape stack is the "undo" of the
  interaction model; it must stay predictable as emphasis grows richer.

### Neighbor emphasis and dim / de-emphasis behavior

- Related-neighbor emphasis and ambient de-emphasis are the two halves of the
  same gesture: lift the story, recede the rest. De-emphasis must **dim, never
  delete** — the whole graph stays visible as context, so the viewer never loses
  the map.
- Emphasis transitions should be smoothly animated (short, eased) and must
  respect `prefers-reduced-motion` — reduced-motion users get the same emphasis
  *state* with minimal/instant transitions.
- **Rationale.** Dimming (not hiding) preserves spatial memory and keeps the
  graph honest — it is still showing the real, whole graph, just focusing
  attention. Hiding non-neighbors would fake a subgraph that isn't the data.

### Pulse / aura / group behavior

- The existing idle aura/breathing pulse and per-type halo are kept but must
  stay *subtle at rest* and *meaningfully stronger under selection* — the
  difference between resting and selected energy is what sells "alive."
- Type-based grouping may be expressed through the existing per-type halo/color
  language (grouping as *visual family*, not as new clustered layout). No new
  clustering/force layout — grouping is a read of existing node type/tag data,
  not a computed rearrangement.
- **Rationale.** Aura/pulse is where "alive vs. fake" is won or lost. Tied to
  real selection/type state and kept restrained, it reads as living
  intelligence. Untethered or maxed-out, it reads as a screensaver. Grouping via
  the existing visual family (not a new layout engine) keeps the change additive
  and honest.

### Keyboard / command direction

- Keyboard parity is a first-class goal: Tab/arrow traversal to nodes, Enter/Space
  to select, Escape to peel, focus-visible emphasis identical to hover. This
  extends the existing patterns; it does **not** build a new command-palette or
  keyboard framework in 31B.
- A future command surface (palette/quick-jump) may be *named as a direction* but
  is explicitly out of the 31B scope below.
- **Rationale.** Keyboard-navigable graph interaction is both an accessibility
  requirement and a portfolio signal of seriousness. Building it on the existing
  ARIA/focus patterns keeps risk low; deferring a command palette avoids scope
  creep into a feature the demo does not yet need.

### Accessibility considerations

- Every emphasis state must have a non-color, non-motion channel (label
  legibility, focus ring, ARIA state) so the interaction is usable with reduced
  motion, with color-vision differences, and with a keyboard alone.
- `prefers-reduced-motion` must gate all pulse/aura/transition motion down to a
  static-but-still-legible emphasis.
- **Rationale.** "Premium" and "accessible" are the same requirement here. A demo
  that only works for a mouse user under full motion is not portfolio-grade.

### Interaction rules that preserve graph dominance

- No interaction may spawn a persistent panel, sidebar, or column. Every
  summoned surface is a bounded, dismissible glass overlay.
- The graph remains the majority of the viewport in every interactive state; no
  overlay may occupy a viewport majority or dock permanently to an edge.
- Color energy stays graph-owned. Chrome (rail, masthead, overlay frames) stays
  neutral black/chrome/metal.

---

## Overlay / Command Surface Direction

Overlays exist to *support* the graph, never to become the interface.

### Inspector behavior

- Selection-triggered, bounded floating glass card. Promotes on select, carries
  only real backend-derived node/edge detail, dismisses on deselect/Escape, and
  never grows into a persistent side column.

### Source Registry behavior

- A contextual dock/drawer summoned from the rail, one tertiary overlay at a
  time. It lists real registered sources; it does not become a permanent
  left/right column and does not reintroduce a dashboard section.

### Intelligence Report behavior

- A contextual overlay presenting the four backend-derived sections (Temporal
  Decay, Dreaming, Provenance, Query Trails) exactly as they exist — read-only,
  honest empty-states preserved. It appears on demand and recedes; it is not a
  standing panel.

### Console / tools behavior

- The Console and any tool surfaces are summoned glass drawers, exclusive with
  the other tertiary overlays. They keep the existing safe, read-only behavior.

### Rail / menu behavior

- The compact, icon-only bottom-docked rail is preserved. Labels reveal on
  hover/focus and must stay within the viewport at narrow widths (the Phase 30B
  responsive rule). The rail is the launcher; it is never a persistent labeled
  navigation bar.

### Glass / chrome / translucency expectations

- Overlays are translucent, non-occluding glass with restrained blur — you can
  still sense the graph behind them. Chrome is black/chrome/metal with no
  decorative accent color. Overlays never fully black out the graph.

### Rules for maximum visual weight

- The graph is always the heaviest element on screen. No overlay, in any state,
  may out-weigh, fully occlude, or permanently frame the graph. If a surface
  needs more room than a bounded overlay allows, that is a signal the surface is
  wrong for this shell — not a reason to grow a panel.

**Rationale (overlays).** Every overlay that hardens into a permanent panel is a
step back toward the dashboard the project spent 27A–28D escaping. Keeping
supporting tools as summoned, bounded, exclusive glass surfaces is what makes the
interface read as a *serious viewfinder* rather than an "admin dashboard wearing
cyberpunk cologne." A recruiter sees the difference instantly.

---

## Portfolio Demo Story

The story a viewer should understand in 30–90 seconds.

### What Hive&#124;Mind is

A local-first, deterministic, **read-only** knowledge-intelligence tool whose
primary surface *is* a knowledge graph. It ingests structured knowledge (e.g.,
Obsidian import), stores it locally, and derives a read-only Intelligence Report
(Temporal Decay, Dreaming Suggestions, Provenance Chains, Query Trails) from the
real store — all presented through a graph-primary viewfinder, not a dashboard.

### What makes it different

- The graph is the *interface*, not a widget inside a dashboard.
- The intelligence is **deterministic and backend-derived** — no AI/LLM, no
  fabricated signals; every section is explainable from the store.
- The surface is a premium black/chrome/dev-tool viewfinder where interaction
  tells the relationship story.

### What is implemented vs. planned

- **Implemented:** the graph-primary shell; the three-tier interaction/emphasis
  model; contextual overlays for Sources/Intelligence/Console/inspector; the
  four backend-derived Intelligence Report sections; the Phase 30B
  interaction-recovery fix (in code).
- **Planned (this arc):** the premium interaction leap (31B) and its QA +
  portfolio screenshot evidence (31C).
- **Not claimed:** Phase 30C QA/evidence (not yet run); any AI/LLM; any graph
  mutation; any production-security posture.

### What screenshots / demo states should matter (eventual hero evidence)

Captured only in Phase 31C, from the real connected runtime:

1. **At-rest full-viewport graph** — calm, premium, graph-owns-the-screen.
2. **Selected-node storytelling** — one node selected, `selected > related >
   ambient` emphasis clearly legible, inspector promoted.
3. **Relationship/edge emphasis** — a selected edge (or neighbor highlight)
   showing the graph reasons about connections.
4. **A contextual overlay open** (e.g., Intelligence Report or Sources) proving
   tools are summoned glass, not a dashboard column.
5. **Narrow-viewport state** — the responsive rail behaving, graph still
   dominant.
6. **Keyboard-focus state** — focus-visible emphasis, proving accessibility.

### What to avoid in the portfolio narrative

- Do **not** overclaim: no "AI-powered," no "real-time," no "autonomous," no
  "production-ready/secure," no invented metrics.
- Do **not** show decorative mockups as if they were the running app. Every hero
  screenshot must be the real connected runtime.
- Do **not** imply the graph is editable or that suggestions are auto-applied.

**Rationale (demo).** The strongest portfolio signal is a *real, connected,
interactive* graph that tells a relationship story honestly — not a pile of
panels or a faked hero shot. Recruiters reward restraint and truth: a small,
real, well-crafted surface that clearly states what is and isn't implemented
reads as senior engineering judgment. Overclaiming or mockup-faking reads as the
opposite and is easy to catch.

---

## Phase 31B Candidate Scope

**Proposed title: Phase 31B — Premium Graph Interaction Frontend Implementation
Pass.**

A narrow, presentation/interaction-only frontend pass that implements the
premium interaction direction above over the existing SVG view model.

### Allowed files

- `apps/frontend/src/components/KnowledgeGraphPanel.tsx` — the primary
  interaction/emphasis surface.
- `apps/frontend/src/styles.css` — emphasis, aura/pulse, glass, and
  reduced-motion rules.
- Existing frontend graph helper / view-model files — **only if truly needed**
  for presentation-safe emphasis/focus state, with no data or contract change.
- `apps/frontend/src/App.tsx` — **only if** overlay/focus/keyboard wiring
  genuinely requires it.
- `README.md` / `docs/roadmap.md` — minimal status updates only.

### Allowed behavior / visual changes

- Sharpen the `selected > related > ambient` emphasis and neighbor/edge
  highlighting.
- Tune aura/pulse so at-rest is calm and selection is clearly stronger.
- Make edge selection a first-class, coherent behavior.
- Ensure keyboard focus produces emphasis identical to hover; strengthen
  focus-visible affordances.
- Add smooth, reduced-motion-respecting emphasis transitions.
- Preserve and, only if verification shows it regressed, repair the Phase 30B
  Escape/focus and responsive-rail behavior.

### Acceptance criteria (before 31B is considered done)

- At-rest, hover/focus, selected-node, selected-edge, deselect/Escape,
  neighbor-emphasis, and narrow-viewport states all behave as specified over the
  real connected graph.
- Keyboard parity holds; `prefers-reduced-motion` is honored.
- The graph remains the viewport majority in every state; no overlay hardens
  into a panel/sidebar/column.
- `npm run check:frontend` (`tsc -b && vite build`) passes.
- No backend/API/schema/contract/data/package/dependency change; graph stays
  read-only; no new graph library; no screenshots (deferred to 31C).

### Risk controls

- Narrow file scope and additive changes only; no layout re-architecture.
- No new dependency or engine — everything renders on the existing SVG model.
- Reduced-motion and keyboard paths are treated as required, not optional.
- Any temptation to add a command palette, clustering layout, or persistent
  panel is out of scope and deferred.

---

## Phase 31C Candidate Scope

**Proposed title: Phase 31C — Premium Graph Interaction QA + Portfolio
Screenshot Evidence Refresh.**

A QA / evidence / documentation-only pass after 31B.

### Screenshot states to capture

The six hero states listed under *Portfolio Demo Story*, each from the real
connected runtime (backend `8787`, frontend `5173`), visually re-verified.

### Runtime evidence expectations

- Re-run the connected backend/frontend; confirm the directly exercised
  endpoints return the established shapes/values (health `0.1.0`; graph 7 nodes /
  6 edges; Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails
  7).
- Verify the premium interaction states behave as specified, and confirm **no
  regression** across the Phase 29C interaction set.
- **Absorb the outstanding Phase 30C evidence debt:** because 30C never ran,
  31C's evidence pass should also confirm the Phase 30B interaction-recovery fix
  (Escape after dock close; narrow-viewport focused rail) against the connected
  runtime, so the recovery fix is finally verified rather than left assumed.

### Documentation evidence expectations

- Record a `phase-31c-connected-*` screenshot set (preserving prior history),
  an evidence doc under `docs/demo/`, and honest Known-limitation notes for
  anything that does not fully meet the target.

### Validation expectations

- `npm run check:frontend` passes; endpoint shapes/values match the trail;
  screenshots are real captures, not mockups; no fabricated data or states.

---

## Guardrails

Restated strictly for the 31B/31C implementation window:

- **Graph stays read-only.** No mutation, editing, or write controls of any kind.
- **No new graph library / engine.** No D3, Cytoscape, React Flow, Three.js,
  canvas force-layout, or 3D. Everything renders on the existing deterministic
  inline-SVG view model.
- **No AI/LLM, no fake liveliness, no fabricated telemetry, no invented
  relationships.** Every state maps to real store/graph data.
- **No dashboard, sidebar, or card-grid revival.** Every supporting surface is a
  summoned, bounded, exclusive, dismissible glass overlay.
- **Graph dominance is non-negotiable.** The graph is the heaviest element and
  the viewport majority in every state; color energy stays graph-owned; chrome
  stays neutral black/chrome/metal.
- **Accessibility is required, not optional.** Keyboard parity and
  `prefers-reduced-motion` support ship with the interaction, not after it.
- **Additive, narrow file scope.** No broad CSS rewrite, no "while I'm here"
  restyling of already-passing surfaces, no unplanned redesign.
- **No screenshots in 31B; no implementation in 31C.** The
  plan → build → QA cadence is preserved.
- **No false completion claims.** No document may state Phase 30C is complete or
  that 30B/31B screenshot evidence exists unless the repository supports it.

---

## Design Rationale

Why this direction, and why it beats the alternatives:

- **Why premium graph interaction over more panels.** The graph *is* the
  product. Every hour spent making selection tell a richer relationship story
  buys more portfolio signal than another dashboard panel would — panels are
  commodity; a real, interactive, story-telling knowledge graph is not. Adding
  ordinary panels would also directly contradict the most expensive, most-revised
  decision in the project (27A–28D graph-primary lock).

- **Why "alive but honest" over maxed-out motion.** Tying aura/pulse/emphasis to
  real selection/type state and keeping the resting state calm makes motion read
  as *living intelligence*. Untethered or constant motion reads as a screensaver
  and, worse, as fake liveliness — the specific anti-pattern the 25A/28A visual
  locks forbid. Restraint is the premium signal.

- **Why selected-node storytelling is the centerpiece.** It converts a static
  graph into `this concept → these connections` with a single click — the most
  legible possible demonstration that the tool reasons about relationships. No
  amount of text panels communicates that as fast.

- **Why overlays must stay summoned glass.** The moment a supporting tool
  hardens into a permanent panel, the surface slides back toward a dashboard and
  loses the viewfinder identity. Bounded, exclusive, dismissible glass keeps the
  graph dominant and the interface serious.

- **Why the demo must show real connected runtime states, not mockups.** A real
  connected graph telling an honest story is a far stronger portfolio artifact
  than a decorative mockup — and it cannot be faked or caught out. Honesty about
  implemented-vs-planned reads as senior judgment; overclaiming reads as the
  opposite.

- **Why keep the plan → build → QA split (31A/31B/31C).** Separating planning,
  implementation, and evidence preserves the honest, repeatable cadence the
  project has used since the 27/28/29 arcs, prevents mid-capture tweaks from
  conflating "changed code" with "verified behavior," and keeps each change
  reviewable.

- **Why acknowledge the Phase 30C debt instead of papering over it.** 30C never
  ran; pretending otherwise would bake a false claim into the repo. Folding the
  30B verification into 31C's evidence pass pays the debt honestly and avoids a
  throwaway phase, while keeping every document truthful.

---

## Acceptance Criteria

Phase 31A is complete only if:

- This planning doc exists under `docs/planning/` and clearly defines the
  premium graph interaction direction, the overlay/command-surface direction,
  the portfolio demo story, and the scoped Phase 31B and Phase 31C passes.
- `README.md` and `docs/roadmap.md` receive **minimal** updates: a Phase 31A
  status/reference and 31B/31C rows, plus correction of the stale Phase 30B
  status to reflect that its code landed via #109 (with 30C honestly recorded as
  not-yet-run).
- No runtime code changed. No CSS changed. No backend changed. No API/schema/
  contract changed. No package/dependency changed. No screenshots or generated
  assets were added.
- The next two phases, 31B and 31C, are clearly scoped with allowed/forbidden
  lists and acceptance criteria.
- No document introduced by this phase claims Phase 30C is complete or that
  screenshot evidence exists when the repository does not support it.

---

## Statement of Scope

This phase produced planning and documentation only. No application code, style,
configuration, dependency, API, schema, data, screenshot, or asset behavior was
changed. The premium graph interaction direction is *implemented* in the proposed
Phase 31B and *verified* — together with the still-outstanding Phase 30B
recovery-fix evidence — in the proposed Phase 31C, not before.
