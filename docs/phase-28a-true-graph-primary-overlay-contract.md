# Phase 28A — True Graph-Primary Surface Contract + Overlay Contract

Status: Planning / documentation only. No frontend, backend, CSS, API, schema,
package, dependency, runtime asset, or graph-logic changes. This phase defines
the contract Phase 28B must implement against.

**Visual correction lock addendum:** after an initial UI direction pass, this
contract was tightened with Section 6 (Visual correction lock), which locks
in stricter shell/chrome, color-discipline, navigation, overlay, and
graph-visual-identity rules and extends the Section 5 Phase 28B handoff.
See Section 6 below.

## Why this phase exists

Phase 27A–27E delivered a graph-first app shell: the Knowledge Graph became
the persistent, full-viewport primary surface, and the Source Registry,
Intelligence Report, Console, and Vault/status summary became contextual dock
panes opened from a compact control rail. That was real progress over the
prior dashboard-with-panels layout.

But "graph-first" is not the same guarantee as "graph-primary." A layout can
give the graph the most pixels and still read as a dashboard: a persistent
rail, docked panes with fixed columns, or panel chrome that visually competes
with the canvas all reintroduce the dashboard feel by degrees. Phase 28A exists
to close that gap **before** any further layout work, by writing a stricter,
harder-to-drift-from contract: the graph is not a panel among panels, it is
the application.

This document does not re-litigate whether the graph should be primary —
Phase 27A already decided that. It tightens *what "primary" means* so Phase
28B has no room to reintroduce sidebar/column thinking under a different name.

## 1. Graph dominance rules

The Knowledge Graph is the full application surface, not a region of it.

- The graph canvas occupies the **entire viewport** — full width, full
  height, edge-to-edge. There is no persistent margin reserved for other UI
  that is not itself an overlay.
- The graph is **not a content card**. It has no bordered container, no
  panel chrome, no "card" background distinct from the app background. The
  canvas *is* the background.
- The graph is **not one panel among many**. There is no layout in which the
  graph and another surface (Sources, Intelligence, Console, Vault) occupy
  parallel, simultaneously-visible regions of comparable visual weight.
- The graph is the **living workspace**: the default, at-rest, nothing-open
  state of the app is the graph alone, unobstructed, with no dock pane
  pre-opened and no chrome implying "there's more here, look at the sides."
- UI panels **must not visually compete** with the graph: no equal-or-greater
  surface area, no equal-or-greater contrast/elevation, no persistent panel
  that draws the eye before the graph does.

Visual hierarchy, in strict reading order, always:

1. Graph canvas (the map itself — nodes, edges, layout).
2. Selected-node context (what lights up when you click something).
3. Tool overlays (Source Registry, Intelligence Report, Console, etc., when
   summoned).
4. Utility controls/status (rail, command menu, filters, keyboard hints,
   connection/health status).

Explicitly rejected layouts (Phase 28B may not implement any of these, in
whole or in part):

- Permanent left sidebar + graph content area.
- Split-column dashboard layout (graph in one column, tools in another).
- SaaS admin shell (top nav + left nav + main content region).
- Card-grid dashboard (graph as one card in a grid of cards).
- Persistent panel walls around the graph (top bar + bottom bar + side rail
  all simultaneously chrome-heavy enough to frame the graph like a window).
- Graph trapped inside a bordered rectangle with visible padding/background
  distinguishing it from the app shell.
- "Premium dashboard" patterns (metric tiles, summary strips, stat cards)
  that make the graph feel like supporting content under a KPI header.

## 2. Overlay hierarchy

Every non-graph surface is an overlay: a contextual, temporary layer *over*
the graph, not a layout column beside it.

Hierarchy (highest to lowest precedence when surfaces could visually
conflict):

- **Primary** — graph canvas / viewfinder / intelligence map. Always
  present, always the base layer, never obscured by its own chrome.
- **Secondary** — node inspector / selected-node context. Appears only in
  response to a selection; it is about a specific node, not a mode the app
  is "in."
- **Tertiary** — Source Registry, Intelligence Report, Console,
  import/actions, and future intelligence tools (Dreaming, Decay,
  Provenance, Query Trails overlays). Summoned deliberately, dismissed
  deliberately.
- **Utility** — control rail, command menu, filters, status, keyboard
  hints. The smallest, quietest layer; present at rest but minimal.

Expected overlay behavior:

- Overlays float, slide, fade, collapse, or appear on command (click a rail
  icon, select a node, invoke a command) — they do not sit permanently
  mounted-and-visible as part of the default layout.
- Overlays feel temporary and contextual: opening one should feel like
  pulling up a layer, not switching to a different page/section of an app.
- Overlays preserve graph dominance: when an overlay is open, the graph
  remains visible (dimmed/pushed/behind is acceptable; fully replaced or
  scrolled-away is not).
- Docked panels (when a panel docks rather than floats) have strict
  max-width rules — a docked pane is a narrow strip anchored to an edge, not
  a resizable/growable column that competes for the graph's space.
- Docked panels must never turn the screen into columns: at most one dock
  pane open at a time, and it must read as "a drawer opened over the map,"
  not "the map got smaller to make room."
- Left-side permanent UI is minimized to the control rail only — no
  permanent left sidebar of links, sections, or panel content.
- Node lists, legends, filters, and tool menus become compact overlays or
  command surfaces (e.g., a small legend chip, a searchable command palette)
  rather than always-visible list panels.

## 3. Panel behavior contract

For each major surface, Phase 28B must follow this behavior:

**Node inspector**
- Appears when: a node is selected on the graph.
- Appears where: anchored near the selection or as a slide-in edge panel,
  conceptually "attached to" the clicked node, not a fixed sidebar slot.
- Mode: floating or lightly docked (narrow, edge-anchored); dismissible by
  deselecting or clicking elsewhere on the canvas.
- Avoids competing with the graph by: staying narrow, staying visually
  subordinate (lower elevation/contrast than the graph's own selected-node
  highlight), and never blocking the majority of the canvas.
- Must not become: a permanent always-open detail column.

**Source Registry**
- Appears when: summoned from the control rail or command menu.
- Appears where: a docked pane or floating panel over the graph, closable.
- Mode: command-triggered dock/overlay.
- Avoids competing with the graph by: strict max-width, dismiss-on-command,
  and not auto-opening on load.
- Must not become: a default-visible sidebar of sources.

**Intelligence Report**
- Appears when: summoned from the control rail or command menu.
- Appears where: docked pane or floating panel, scrollable within its own
  bounds so it never forces the app shell itself to scroll.
- Mode: command-triggered dock/overlay.
- Avoids competing with the graph by: staying a bounded, closable region,
  not a full-page section the user scrolls the whole app to reach.
- Must not become: a dashboard tab that replaces the graph view.

**Console**
- Appears when: summoned from the control rail or command menu.
- Appears where: docked pane (e.g., bottom or side drawer), closable.
- Mode: command-triggered dock/overlay.
- Avoids competing with the graph by: collapsing to a minimal strip when
  idle if retained at all in view; never persistently full-height.
- Must not become: an always-visible terminal pane framing the graph.

**Vault/status/system info**
- Appears when: summoned, or as a minimal always-present status chip (e.g.,
  connection/health) in the utility layer only.
- Appears where: utility strip (rail or a slim status bar), not a content
  panel.
- Mode: utility-level, mostly collapsed; expandable on command for detail.
- Avoids competing with the graph by: staying reduced to a glance-able
  chip/indicator by default.
- Must not become: a metrics dashboard header.

**Filters/search**
- Appears when: invoked via command menu or a small utility control.
- Appears where: utility layer, e.g. a compact filter chip row or a search
  affordance near the rail — not a persistent filter sidebar.
- Mode: command-triggered, collapsible.
- Avoids competing with the graph by: not reserving permanent screen space
  when not in use.
- Must not become: a left-hand facet/filter panel like a search UI.

**Command/menu surface**
- Appears when: invoked (keyboard shortcut, rail click) or shown minimally
  as the rail itself at rest.
- Appears where: overlays the graph centrally or anchors to the rail.
- Mode: command-triggered overlay.
- Avoids competing with the graph by: being transient — appears to act,
  then disappears.
- Must not become: a permanent top nav bar.

**Future Dreaming / Decay / Provenance / Query Trails overlays**
- Appears when: summoned from the Intelligence Report tertiary surface or a
  dedicated command, and/or triggered contextually from a relevant node
  selection.
- Appears where: as sub-surfaces within the Intelligence Report overlay, or
  as their own tertiary overlays if they grow complex enough to warrant it.
- Mode: command-triggered / selection-triggered overlay.
- Avoids competing with the graph by: inheriting the same bounded,
  dismissible, non-columnar treatment as the other tertiary surfaces.
- Must not become: standalone dashboard pages or a tab bar of "views."

## 4. Visual feel

Desired feel — the app should read as:

- A viewfinder.
- An intelligence map.
- A tactical graph surface.
- A premium cybernetic workspace.
- Dark metallic.
- A serious dev-tool product.
- A graph-first operating surface — the graph *is* the product, not a
  feature embedded in a product shell.

Undesired feel — the app must not read as:

- An admin dashboard.
- SaaS sidebar soup.
- A generic analytics dashboard.
- A card museum (rows of metric/content cards).
- Fake hacker wallpaper (surface-level "cyber" decoration with no
  functional grounding).
- Neon soup (color/glow without hierarchy or restraint).
- A dashboard with a graph widget embedded in it.

The test for any future layout decision: if a screenshot could be mistaken
for a generic SaaS admin panel with a chart swapped in, it fails this
contract.

## 5. Phase 28B implementation handoff

**Phase 28B scope:** "True Graph-Primary Surface Frontend Implementation
Pass."

Phase 28B should likely touch only:

- `apps/frontend/src/App.tsx`
- `apps/frontend/src/components/KnowledgeGraphPanel.tsx`
- `apps/frontend/src/styles.css`
- Existing frontend graph helper/view-model files, only if absolutely
  necessary to satisfy the contract above (no new files unless unavoidable).

Phase 28B should forbid:

- Backend changes.
- API/schema changes.
- Package/dependency changes.
- Fake data.
- Graph mutation or new graph logic.
- Runtime asset/icon additions.
- Screenshots/evidence docs (unless separately scoped as a follow-up QA
  phase, matching this project's established pattern of a QA phase after
  each implementation phase).
- 3D.
- D3/Cytoscape/React Flow or any new graph rendering dependency.
- Broad unrelated redesign (typography overhaul, rebrand, unrelated copy
  changes).

Phase 28B success criteria:

- The graph fills the app as the primary living surface at rest, with no
  persistent sidebar/column reserving space for other content.
- Panels (inspector, Source Registry, Intelligence Report, Console,
  Vault/status) behave as contextual overlays — they appear on command or
  selection and can be fully dismissed back to graph-only.
- The app no longer reads as a dashboard shell: no persistent multi-column
  layout, no card-grid summary strip competing with the canvas.
- Source/Intelligence/Console surfaces remain available and fully
  functional, but are visually subordinate to the graph whenever both are
  on screen.
- The graph remains legible and central whether overlays are open or
  closed — opening an overlay must not shrink, crop, or reflow the graph
  into a leftover column.
- The layout feels like a viewfinder/intelligence-map surface per the
  Section 4 visual-feel test, not a SaaS admin page.

## 6. Visual correction lock (addendum)

A review of the current UI direction found it closer to the contract above
but still drifting in ways the original five sections did not pin down
tightly enough — chrome that reads as a generic dark dashboard rather than a
graph-native surface, a persistent sidebar in spirit if not in name, and
overlays heavy enough to read as walls rather than glass. This addendum
locks in the corrections. It amends and tightens Sections 1–4; it does not
reopen the decisions already made there.

**6.1 Shell / chrome direction**

- The app shell reads as deep black / dark chrome / metallic — a serious
  dev-tool product, not a generic "dark mode" skin of a light dashboard.
- The overall background and shell are darker and more visually restrained
  than the current implementation: less midtone gray, more true dark
  chrome/metallic depth.
- The shell does not rely on colorful accents to establish identity. Its
  identity comes from material (metallic, chrome, depth) and restraint, not
  color.

**6.2 Color discipline**

- No color exists outside graph-related systems, with three narrow
  exceptions: white/off-white, grayscale metallic neutrals, and occasional
  functional color-coded text where consistency requires it (e.g., a status
  word that must stay red/green/amber for legibility).
- General UI chrome — rail, command surface, dock frames, headers, borders,
  labels — carries no decorative accent color. If a chrome element needs
  emphasis, it uses elevation, contrast, or metallic sheen, not hue.
- Nearly all visual color energy belongs to the graph itself: nodes, edges,
  pulses, halos, grouping/cluster color, and graph-state signals (selected,
  stale, connected, etc.). Color is how the graph communicates; it is not
  how the shell decorates itself.

**6.3 Navigation correction**

- The persistent left sidebar (control rail as currently built) does not
  remain as a standard, always-visible, screen-dividing sidebar — even a
  narrow one is still a permanent column and fails Section 1's dominance
  rule.
- The sidebar pattern is replaced conceptually with a translucent,
  icon-based hover/reveal/command-triggered utility surface: icons that sit
  quietly over the graph (not beside it), expand or reveal labels/tools on
  hover or invocation, and recede to near-invisible at rest.
- Navigation and tools feel **summoned over the graph**, not permanently
  dividing the screen into a nav region and a content region.

**6.4 Overlay correction**

- Overlays are glass-like: translucent, floating, and visually subordinate
  to the graph in both material and precedence — they read as a pane of
  glass laid over the map, not a solid card placed on top of it.
- Section surfaces/cards must not behave like fully blocking, opaque
  walls — no overlay should fully occlude the graph behind it, even when
  the overlay's own background has some transparency in name only (e.g., a
  95%+ opaque fill still reads as a wall and fails this rule).
- Overlays preserve visibility of the graph behind them at all times they
  are open, and must not cause the app to reflow into columns (the graph
  never shrinks, never gets pushed into a leftover region to make room).

**6.5 Graph visual identity**

The graph itself is the correction's center of gravity — it must visibly
earn the color and life budget the rest of the shell gives up:

- A living / breathing feel — subtle motion or animation cues that read as
  "alive," not static geometry.
- Pulsing node and edge energy — signal, not decoration; pulses should be
  legible as activity/emphasis, not random ambient noise.
- Aura / halo treatment around nodes, used to carry meaning (selection,
  status, emphasis) rather than purely for effect.
- Group / cluster presence — visually legible clustering so related nodes
  read as a group without needing a legend to explain it.
- Reactive selected-node focus — the graph itself visibly responds to
  selection (not just the inspector overlay opening).
- An intelligence-map / tactical-surface feel overall.

The graph must read as the app's core product identity — the thing the
product *is* — not as one panel inside an app whose identity lives in its
chrome. (This section describes the target visual language; the concrete
implementation of pulse/halo/cluster/motion mechanics belongs to Phase 28B
or a dedicated follow-on graph-visual phase — this addendum does not itself
add graph logic, mutation, physics, or new dependencies. See Section 5's
forbidden list, which still applies unchanged.)

**6.6 Explicit rejection (addendum to Section 1)**

In addition to the rejections already listed in Section 1, the following
are also rejected:

- Persistent sidebar navigation, including a narrow icon rail that is
  always visible and always occupies fixed screen space.
- Split-column dashboard structure, in any variant.
- Card walls around the graph — any arrangement of multiple simultaneously
  visible, opaque-feeling cards framing the canvas.
- Colorful chrome unrelated to graph semantics — accent colors on shell
  elements that exist for branding/decoration rather than to represent
  graph state.
- Dashboard-first composition — any layout where the eye is drawn to shell
  structure before the graph.
- Graph-as-widget composition — the graph rendered as if it were one
  embeddable component among several, rather than the surface everything
  else floats over.

**Amendment to Section 5 (Phase 28B handoff):** Phase 28B's forbidden list
and success criteria are extended by this addendum — Phase 28B must satisfy
Sections 6.1–6.6 in addition to the original Section 5 criteria. Where the
current implementation (post-27B/27D) conflicts with this addendum
(persistent rail, opaque/heavy overlays, shell accent color, flat/static
graph rendering), Phase 28B is expected to correct it, not preserve it for
compatibility.

## Relationship to prior phases

This contract sharpens, and does not contradict, the direction set in
[Phase 27A Graph-First App Shell Planning](ui/phase-27a-graph-first-app-shell-planning.md)
and implemented in Phase 27B/27D. Where Phase 27A defined the transition from
dashboard-with-panels to graph-first shell, Phase 28A defines the stricter
bar for what "graph-first" must mean in practice — full-viewport dominance,
overlay-only secondary surfaces, and an explicit rejection list — so Phase
28B has an unambiguous target and cannot drift back toward dashboard framing
under a graph-first label.
