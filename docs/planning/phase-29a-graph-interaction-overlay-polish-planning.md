# Phase 29A — Graph Interaction + Overlay Polish Planning

## Status

Planning phase. No implementation. This document defines the interaction and
overlay polish contract for Phase 29B; it changes no frontend, CSS, backend,
API, schema, package, dependency, runtime asset, or screenshot state.

## Purpose

Define the interaction and overlay polish contract for Phase 29B before any
frontend work begins, so Phase 29B is a bounded implementation pass against a
written contract rather than an open-ended CSS wander. This document inherits
the [Phase 28A True Graph-Primary Surface + Overlay Contract](../phase-28a-true-graph-primary-overlay-contract.md)
in full — including its Section 6 visual correction lock — and tightens the
*interaction* layer the same way Phase 28A tightened the *layout* layer.

## Current Baseline

After Phase 28B (implementation), Phase 28C (QA/screenshot evidence), and
Phase 28D (README/portfolio visual lock), the running frontend is a true
graph-primary surface:

- The Knowledge Graph SVG canvas fills the entire viewport edge-to-edge at
  every breakpoint; there is no persistent sidebar, dashboard column, or
  card-grid framing.
- The masthead and the compact icon-only bottom dock are floating translucent
  glass overlays; the dock reveals labels on hover/focus and recedes at rest.
- The Vault, Sources, Intelligence, and Console tools open as contextual
  glass overlays summoned from the dock; the graph stays visible behind them.
- The graph explorer (legend/groups/node/edge lists) is a summoned floating
  glass card, toggled from the graph surface, not an always-visible column.
- Selection exists today: clicking a node or edge selects it, incident edges
  pick up an energy-flow dash treatment, non-related elements dim, and a
  floating glass inspector card mounts showing the selection's details and
  relationships. Clearing the selection unmounts the inspector.
- Escape already closes the topmost summoned surface (selection/inspector or
  the explorer), scoped to the panel via `onKeyDown`.
- The graph carries the living-identity groundwork from Phase 28B: idle
  aura/breathing pulse on every node, per-type resting halo, a stronger
  pulsing glow on the selected node, and animated energy-flow edges incident
  to the selection.
- Shell chrome carries no decorative accent color; color energy belongs to
  the graph (Phase 28A §6.2).

What the baseline does *not* yet have — and what Phase 29B will polish:

- No dedicated hover treatment on nodes or edges beyond browser defaults.
- No defined contract for switching selection directly between elements.
- No defined stacking/exclusivity rules when multiple overlays are open.
- No keyboard/command-surface direction beyond Escape and list arrow keys.
- Group/community visual presence is limited to per-type halos; related-node
  and cluster emphasis rules are not written down.

## Design Principles

- The graph remains the primary application surface at all times.
- Overlays are secondary and contextual: summoned, bounded, dismissible.
- Persistent sidebar/dashboard/card-grid patterns remain rejected (Phase 28A
  Section 1 and §6.6 rejection lists apply unchanged).
- Visual energy belongs primarily to graph elements — nodes, edges, groups,
  auras, pulses, selection states. Chrome stays dark, metallic, and quiet.
- Utility surfaces must feel intentional, compact, and dismissible — a tool
  you summon, not a region you live in.
- Interaction states must form a legible hierarchy: at any moment the user
  can tell what is hovered, what is selected, what is related, and what is
  ambient — without a legend.
- Everything stays read-only. Interaction polish reveals and emphasizes; it
  never mutates the graph, the store, or the sources.

## Graph Interaction Behavior

Planning-level behavior contract for Phase 29B:

- **Hovering a node** — the node gains a subtle hover affordance (slightly
  brightened halo/aura and cursor change) that is clearly weaker than the
  selected state. Hover may lighten the node's incident edges slightly. Hover
  must not dim the rest of the graph, open any overlay, or move anything.
- **Hovering an edge** — the edge gains a modest emphasis (stroke lift), and
  its two endpoint nodes may brighten slightly. Same restraint rules as node
  hover: no dimming of the rest of the graph, no overlay, no motion burst.
- **Selecting a node** — click (or keyboard activation) selects the node: the
  selected-node pulsing glow applies, incident edges take the energy-flow
  treatment, directly related nodes read as related, non-related elements dim,
  and the inspector mounts as a floating glass card. Exactly one element is
  selected at a time.
- **Selecting an edge** — same pattern scoped to the edge: the edge takes the
  selected treatment, its two endpoints read as related, everything else
  dims, and the inspector shows the edge's details.
- **Deselecting** — clearing the selection (Escape, the inspector's close
  affordance, the existing clear-selection control, or clicking empty canvas)
  removes the selected/related/dimmed states and unmounts the inspector,
  returning the graph to its at-rest living state.
- **Clicking empty graph space** — deselects the current selection if one
  exists. If no selection exists, clicking empty space does nothing visible
  (it must not open, toggle, or shake anything).
- **Switching between selected nodes/edges** — clicking a different node or
  edge while something is selected moves the selection directly: no
  deselect-then-reselect flicker, no inspector unmount/remount flash — the
  inspector content swaps in place.
- **Maintaining graph-first visual hierarchy** — at every interaction moment
  the strict reading order from Phase 28A Section 1 holds: graph canvas
  first, selected context second, tool overlays third, utility last. No
  interaction state may make an overlay or chrome element the visually
  dominant object on screen.

## Hover / Select / Deselect Contract

- **What hover may reveal:** a lightweight affordance on the hovered element
  itself (halo lift, edge stroke lift, endpoint brightening) and optionally a
  small label/tooltip near the pointer identifying the element. Nothing more.
- **What selection may reveal:** the full selected treatment (glow, energy
  edges, related emphasis, ambient dimming) plus the inspector overlay with
  the element's details, relationships, and evidence/source context.
- **What deselection should close/reset:** the inspector, the
  selected/related/dimmed visual states, and any selection-anchored emphasis.
  The graph returns to the idle living-aura state.
- **What should persist:** deliberately summoned tertiary overlays (Vault /
  Sources / Intelligence / Console) and the explorer, if open, persist across
  selection changes and deselection — deselecting a node must not slam shut a
  tool the user opened on purpose. The camera/viewport position (such as it
  is in the static SVG layout) also persists.
- **What must never happen:**
  - Hover must never open, close, or resize an overlay.
  - Hover must never dim or restyle the rest of the graph.
  - Selection must never mutate data, trigger a network write, or re-fetch.
  - Deselection must never reset scroll position inside an open tertiary
    overlay or close it.
  - No interaction may cause layout reflow of the graph canvas.

## Overlay Behavior + Hierarchy

Overlay tiers (inherited from Phase 28A Section 2, restated for 29B):

- **Primary:** the graph surface. Always the base layer; never occluded by
  its own chrome.
- **Secondary:** the selected node/edge inspector. Selection-triggered only.
- **Tertiary:** the Vault, Sources, Intelligence, and Console tools.
  Summoned deliberately, dismissed deliberately.
- **Utility:** the explorer/legend, filters, status chip, dock, and any
  keyboard/command menu. Smallest and quietest layer.

Behavior rules for Phase 29B:

- **Open/close:** every overlay opens from an explicit trigger (dock icon,
  selection, keyboard command) and closes from an explicit dismissal (close
  affordance, Escape, its toggle, or — for the inspector — deselection).
  Nothing auto-opens on load.
- **Stacking:** at most one *tertiary* overlay is visible at a time — opening
  a second tool closes the first. The secondary inspector may coexist with
  one tertiary overlay and with utility surfaces, but when surfaces would
  collide, the later-summoned surface takes pointer precedence and Escape
  dismisses the topmost (most recently opened) surface first.
- **Size constraints:** overlays keep the Phase 28A bounded treatment — a
  narrow drawer or bounded glass card, internally scrollable, never a
  growable column, never a majority of the viewport on desktop widths.
- **Opacity/glass:** overlays remain translucent glass per Phase 28A §6.4 —
  the graph must stay visible through/behind every open overlay; near-opaque
  fills that read as walls fail the contract.
- **Mobile/narrow viewport:** on narrow viewports overlays may take more
  width (up to edge-to-edge sheets) but must remain dismissible, must not
  stack more than one deep above the graph, and the graph must remain the
  at-rest surface once they close. The dock stays reachable.
- **Avoiding graph blockage:** overlays anchor to edges or float compactly;
  they never center a full-screen modal wall over the graph, never dim the
  entire canvas behind a tertiary tool, and never cause the graph to shrink
  or reflow to make room.

## Inspector Behavior

- **Selected node inspector:** shows the node's identity (label, type,
  source), its immediate relationships, and its evidence/provenance context
  where the existing view model already provides it. It anchors as a
  floating glass card conceptually attached to the selection, staying narrow
  and visually subordinate to the graph's own selected-node highlight.
- **Selected edge inspector:** the same card, scoped to the edge — endpoint
  identities, relationship type, and any existing evidence metadata.
- **Empty inspector state:** there is none — the inspector does not exist
  on screen when nothing is selected. No placeholder "select a node" panel
  reserving space.
- **Evidence/source display:** only real, backend-derived data already in
  the graph payload/view model may be shown. Missing metadata renders
  honestly as absent/partial — never fabricated, never padded with
  placeholder intelligence.
- **Close/dismiss:** the inspector closes on deselection by any route
  (Escape, close affordance, clear-selection control, empty-canvas click)
  and swaps content in place when the selection moves to another element.
- **Relationship to overlays and graph selection:** the inspector is the
  secondary tier — above the graph, below nothing except transient utility
  popovers. It never converts into a docked permanent column, and opening a
  tertiary tool while a selection exists leaves the selection and inspector
  intact unless the viewport is too narrow to honor both, in which case the
  later-summoned surface wins visibility and the selection state persists
  underneath.

## Utility / Menu Behavior

- **Compact utility rail / icon-menu:** the bottom-docked icon capsule
  remains the pattern — icon-only at rest, labels on hover/focus, receding
  toward near-invisible when idle. It never grows into a persistent labeled
  navigation bar.
- **Hover-triggered vs click-triggered:** hover may *reveal* (labels, hints,
  affordances); only click/keyboard activation may *open or change state*
  (overlays, selection, toggles). Nothing state-changing hangs off hover.
- **Command/menu surface direction:** if Phase 29B adds a command surface,
  it is a transient, keyboard-summonable glass popover over the graph —
  appear, act, disappear. It must not become a permanent top nav or a
  persistent search bar.
- **Keyboard-first direction:** every overlay toggle and the
  selection-clearing action should be reachable without the mouse; the dock
  controls remain focusable and activatable via keyboard as they are today.
- **Escape key:** Escape always dismisses the topmost summoned surface, in
  most-recently-opened-first order: command surface (if any) → tertiary
  overlay → explorer → selection/inspector. Escape on a bare graph does
  nothing.
- **Focus management (planning level):** opening an overlay should move
  focus into it; dismissing it should return focus to the element that
  summoned it (dock icon, graph element). No focus traps that prevent
  Escape/Tab from working. Details are Phase 29B's to implement within
  existing patterns — no new focus-management library.

## Visual Pulse / Aura / Group Interaction Rules

- **Node hover aura:** a small, immediate halo lift — clearly weaker than
  the selected glow, applied only to the hovered node (and optionally a
  faint lift on incident edges).
- **Selected node aura:** the strongest single visual state on the canvas —
  the existing pulsing selection glow remains the ceiling; nothing else may
  pulse harder or brighter than the current selection.
- **Edge emphasis:** at-rest edges stay quiet; hovered edges lift modestly;
  edges incident to the selection carry the energy-flow treatment. Only
  selection-related edges animate.
- **Related-node highlighting:** nodes directly connected to the selection
  read as "related" — brighter than dimmed ambient nodes, dimmer than the
  selection itself. Exactly three tiers: selected > related > ambient/dimmed.
- **Group/community glow:** group/cluster identity may be reinforced with
  shared hue families and subtle shared aura tinting so clusters read as
  groups without a legend — but group treatment stays ambient (no group-wide
  pulsing, no animated cluster boundaries in this pass).
- **Status pulses:** any status-driven pulse (e.g., stale/decay signals, if
  surfaced on-canvas) must encode a real backend-derived state, be slower
  and subtler than the selection pulse, and never apply to more than a small
  minority of visible nodes at once.
- **Reduced motion:** all pulses, breathing auras, and energy-flow
  animations respect `prefers-reduced-motion` — reduced-motion users get
  static equivalents (steady halo, solid emphasized stroke) with the same
  informational hierarchy.
- **No Christmas-tree graph soup:** the animation budget is strictly
  tiered — idle breathing (subtle, global) < status pulse (rare, meaningful)
  < selection glow/energy edges (one selection at a time). If a screenshot
  of the idle graph looks like a festive light show, it fails this contract.
  Motion always encodes meaning; nothing animates purely for spectacle.

## Keyboard / Command Surface Direction

Planning-level direction — Phase 29B implements only what fits the allowed
scope, and may defer the rest to a later phase:

- **Keyboard shortcuts:** Escape (dismiss topmost, exists today), the
  existing list arrow-key navigation, and — candidate additions — shortcuts
  to toggle the explorer and the four dock tools. Shortcuts must be
  discoverable (e.g., revealed on the dock hover labels) and must not
  collide with browser/OS defaults.
- **Command palette / command surface:** a future keyboard-summoned glass
  surface for jump-to-node, tool toggles, and filters. Phase 29B may lay
  visual/interaction groundwork only if it fits the allowed file scope;
  a full palette with search is acceptable to defer entirely.
- **Overlay toggles:** every dock tool behaves as a true toggle — the same
  trigger opens and closes it, in addition to Escape.
- **Graph navigation concepts:** keyboard focus traversal across graph
  nodes/edges (Tab/arrow patterns) is a direction, not a 29B requirement;
  the existing focusable list rows in the explorer remain the keyboard path
  to selection in the near term.
- **Escape/dismiss:** the single most-recently-summoned surface closes per
  press; repeated presses walk down the stack to a bare graph.
- **Accessibility expectations:** interactive graph elements and overlay
  controls keep their existing ARIA affordances (`aria-pressed`, focusable
  targets); new interaction states must not become color-only signals —
  selected/related states keep a non-color cue (stroke weight, halo shape,
  or text) and contrast stays legible on the dark shell.

## Phase 29B Allowed Scope

Phase 29B — Graph Interaction + Overlay Polish Frontend Implementation
Pass — may touch:

- `apps/frontend/src/components/KnowledgeGraphPanel.tsx`
- `apps/frontend/src/components/App.tsx` (or `apps/frontend/src/App.tsx`,
  wherever the shell/overlay wiring actually lives) — only if overlay
  wiring/stacking rules require it
- `apps/frontend/src/styles.css`
- Existing frontend graph helper/view-model files, only if needed for
  presentation-safe state mapping (hover/related/dimmed derivation) with no
  data or contract changes
- `README.md` / `docs/roadmap.md` for minimal status updates only

## Phase 29B Forbidden Scope

Phase 29B must not touch or introduce:

- No backend changes
- No API/schema changes
- No package/dependency changes
- No new graph libraries — no D3, Cytoscape, React Flow, canvas-force, or 3D
- No fake data, fake states, or fabricated intelligence signals
- No graph mutation controls of any kind
- No persistence (no query history, no localStorage state capture)
- No auth/session work
- No Obsidian importer changes
- No AI/LLM integration
- No broad dashboard redesign or return of persistent sidebar/column layouts
- No branding/assets/icon dump; no new runtime assets
- No screenshots/evidence — that is Phase 29C's job

## Phase 29B Validation Expectations

- `npm run check:frontend` (frontend build/check) must pass.
- Existing frontend behavior must not regress: selection, inspector,
  explorer, the four dock overlays, Escape handling, and reduced-motion
  behavior all keep working.
- The backend must not be touched, and therefore needs no re-testing; if any
  backend/API file changes, Phase 29B has already failed its scope and the
  change must be reverted.
- Manual runtime checks (dev servers, no screenshots required) should
  verify: overlay open/close and stacking behavior, hover/select/deselect
  and selection-switching behavior, Escape dismissal order, narrow-viewport
  overlay behavior, and that the graph remains the dominant surface in every
  state.
- Formal screenshot evidence is deferred to Phase 29C, which re-runs the
  connected runtime and refreshes the evidence trail.

## Risks / Anti-Patterns

Specific failure modes Phase 29B must avoid:

- **The sidebar creeps back** — an inspector or tool overlay that becomes a
  permanent docked column under interaction-polish cover.
- **The graph becomes a card/widget again** — any framing, border, or
  chrome treatment that re-containerizes the canvas.
- **Overlay walls** — glass panels growing opaque, wide, or stacked until
  they block the app surface.
- **Color leaking into chrome** — hover/selection accent colors migrating
  onto the dock, masthead, or overlay chrome in violation of Phase 28A §6.2.
- **Random animation noise** — hover pulses, ambient flickers, or
  attention-seeking motion that breaks the tiered animation budget.
- **Interaction states without hierarchy** — hover, related, and selected
  states so similar (or so numerous) that the user cannot read the graph's
  state at a glance.
- **CSS-only polish that ignores behavior** — restyling states without
  implementing the open/close/stacking/Escape/focus contract, leaving the
  interactions as inconsistent as before but shinier.
- **Implementation exceeding contract** — new libraries, new persistence,
  mutation affordances, command-palette scope creep, or "while I'm here"
  redesigns beyond the allowed file list.

## Recommended Phase 29B Summary

Phase 29B should implement, as a frontend-only presentation/interaction
pass: a restrained hover affordance for nodes and edges; flicker-free
selection switching with in-place inspector content swaps; empty-canvas
click-to-deselect; the overlay stacking/exclusivity rules (one tertiary
overlay at a time, Escape dismissing topmost-first, deliberate overlays
persisting across selection changes); glass/size discipline on all overlays
per Phase 28A §6.4; the three-tier selected/related/ambient emphasis model
with group hue cohesion; tiered animation budgets with
`prefers-reduced-motion` equivalents; and keyboard toggles/focus-return
behavior for the dock overlays — all inside
`KnowledgeGraphPanel.tsx`, the app shell wiring, and `styles.css`, with no
backend, API, schema, package, data, or mutation changes, and no
screenshots (Phase 29C follows for QA/evidence).
