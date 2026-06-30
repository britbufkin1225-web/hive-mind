# Phase 27A — Graph-First App Shell Planning

## 1. Phase Summary

Phase 27A formalizes the next major UI architecture direction for Hive|Mind: a transition from a
dashboard-with-panels layout toward a graph-first app shell, where the Knowledge Graph becomes the
primary full-app view and the remaining surfaces (Source Registry, Intelligence Report, Console,
inspectors, actions, and future overlays) become contextual UI layers around it.

This document is planning only. It defines the target shell direction, the surface model, the
interaction and layout principles, and the guardrails for the next implementation pass. It changes
no frontend, backend, or runtime behavior, and adds no assets, screenshots, or dependencies.

## 2. Current State

- The Phase 25 premium dark-metallic visual system is in place across the app shell.
- The Phase 26 graph visual identity work (constellation-leaning layout, focus tunnel selection,
  semantic node/edge styling, legend, command-surface inspector) has visibly improved the Knowledge
  Graph panel, and the 26B addendum already nudged the panel toward feeling like the dominant surface
  (legend docked as a compact strip, hero elevation, inspector promoted on selection).
- Despite that visual progress, the app is still structurally a **single-page dashboard**: hero,
  connection/health status, vault summary, Source Registry (including the nested Obsidian import
  form), Knowledge Graph, Intelligence Report, and Console are stacked top-to-bottom as scrollable
  sections, tied together by Phase 22's sticky in-page nav and scrollspy.
- The Knowledge Graph is visually the most distinctive panel, but structurally it is still "a panel
  among panels" — it shares the page with five other full-width sections rather than anchoring the
  whole app.
- The next direction, defined here, is to promote the graph from "important panel" to "primary
  workspace," with the other surfaces becoming contextual overlays the user opens on demand instead
  of sections they scroll past.

## 3. Target Graph-First Shell Direction

In the target shell:

- The Knowledge Graph occupies the full primary viewport as the persistent canvas/workspace.
- The graph is the visual and interaction anchor of the entire app, not one section of a longer page.
- Other UI panels are not removed — they become contextual layers that appear when invoked (by
  navigation, selection, or command) and recede when not needed.
- Source Registry, Intelligence Report, Console, node/edge details, provenance, query trails,
  dreaming, and decay all remain reachable, but are presented as trays, docks, drawers, floating
  inspectors, or command surfaces rather than stacked dashboard sections.
- The overall feel should be an intelligence map / workbench — a tool whose center of gravity is the
  graph itself — rather than a page of stacked widgets that happens to include a graph.
- All existing data, endpoints, and read-only behavior are preserved; only layout emphasis and
  navigation model change.

## 4. Surface Model

How each current surface is expected to behave in the graph-first shell:

| Surface | Current role | Graph-first role |
| --- | --- | --- |
| Knowledge Graph | One scrollable section among several | Persistent full-viewport primary canvas/workspace |
| Source Registry (incl. Obsidian import) | Stacked dashboard section | Contextual side tray or dock, opened on demand |
| Intelligence Report | Stacked dashboard section | Floating/report overlay or state-aware intelligence drawer |
| Console | Large permanent panel | Command-palette / terminal-like command surface, not a permanent fixture |
| Node/Edge Inspector | Already contextual (Phase 26) | Carries forward unchanged as a contextual inspector tied to selection state |
| Actions (import, refresh, etc.) | Inline buttons within sections | Compact controls, command surface, or contextual toolbar |
| Navigation (Phase 22 sticky nav) | Section-anchor table of contents | Reduced to shell-level controls — tabs, tray-toggle icons, or minimal glass overlays |
| Future overlays (decay, dreaming, provenance, query trails, source confidence, evidence chains) | Embedded within Intelligence Report section | Contextual overlay layers surfaced over or beside the graph, still backed by real data only |

No surface is deleted or demoted out of existence — every current capability remains reachable from
the graph-first shell.

## 5. Interaction Principles

These describe intended behavior patterns for the next implementation phase to follow; none are
implemented here.

- Hover reveals lightweight context (e.g., a node summary chip) without committing to a full panel.
- Selecting a node or edge opens deeper inspector state, consistent with the existing Phase 26 focus
  tunnel / command-surface inspector model.
- Deselecting returns visual and interaction focus to the graph itself.
- Contextual panels (Source Registry tray, Intelligence Report drawer, Console surface) should
  collapse, dock, or fade out when not actively in use rather than occupying permanent page space.
- The command surface (Console's future form) should be keyboard-friendly and reachable without
  requiring mouse-only interaction.
- Shell-level navigation should help the user reach a surface and then get out of the way — it should
  support graph focus, not compete with it for visual weight.
- Contextual surfaces (trays, drawers, overlays) must not obscure core graph comprehension when open;
  they should coexist with the graph rather than fully replace it from view where avoidable.
- The graph and its contextual surfaces must remain usable with both mouse and keyboard.
- Empty, loading, and error states must remain honest and visible in the new shell — contextual
  surfaces do not get to hide a real "no data" or "disconnected" state.

## 6. Layout Principles

- Full-viewport, graph-first composition: the graph is the base layer the rest of the shell is built
  on top of.
- Overlay surfaces (trays, drawers, command surface, inspector) continue to use the existing
  glass/metal/premium dark-metallic visual language established in Phase 25/26 — no new visual system
  is introduced here.
- Avoid recreating permanent dashboard clutter inside the overlay layer; overlays should behave like
  overlays, not like the old stacked sections relocated.
- Preserve readability and accessibility — overlay contrast, focus order, and `aria` semantics must
  remain at least as good as the current dashboard.
- Avoid neon soup and fake hacker wallpaper; the shell should stay legible and product-grade, per the
  existing [Graph Visual Identity](graph-visual-identity.md) non-goals.
- No 3D and no animation circus — motion stays subtle and purposeful, consistent with the existing
  motion rules and `prefers-reduced-motion` support.
- The overall target feel: premium, technical, and product-grade — an intelligence workbench, not a
  decorative surface.

## 7. Phase 27B Implementation Boundary

Recommended next phase: **Phase 27B — Graph-First App Shell Frontend Implementation Pass.**

Phase 27B is expected to be frontend-only and scoped to shell/layout restructuring, subject to final
scope approval at the start of that phase.

Allowed for 27B (subject to that approval):

- App shell layout changes (promoting the graph to the primary viewport).
- Converting existing panels (Source Registry, Intelligence Report, Console) into overlays/trays/docks
  where feasible.
- Reusing existing data and API calls as-is.
- Preserving existing graph functionality, including the Phase 26 visual identity work.
- Preserving existing source/intelligence/console features and data.
- CSS adjustments needed specifically to support the graph-first shell.

Forbidden for 27B:

- Backend, API, or schema changes.
- New graph logic or graph mutation.
- New data models or fake data.
- New dependencies unless explicitly approved separately.
- 3D, D3, Cytoscape, or React Flow.
- Asset/icon dumps.
- Intelligence logic changes.
- Obsidian importer changes.
- Persistence changes.

## 8. Sequencing After 27A

Suggested sequence (defined here, not implemented):

1. Phase 27A — Graph-First App Shell Planning (this document)
2. Phase 27B — Graph-First App Shell Frontend Implementation Pass
3. Phase 27C — Graph-First Shell QA + Screenshot Evidence Refresh
4. Phase 27D — Graph Overlay Interaction Planning
5. Phase 27E — Graph Overlay Interaction Frontend Pass
6. Phase 27F — Graph Overlay QA + Evidence Refresh

## 9. Risks / Constraints

- Losing easy access to existing panels if overlays are harder to discover than scrolled sections.
- Making the graph visually impressive but functionally less useful if overlay surfaces are not
  designed carefully.
- Overlapping overlays causing visual clutter or obscuring the graph.
- Breaking current connected runtime behavior (live health, graph data, Intelligence Report data)
  during shell restructuring.
- Creating inaccessible hover-only interactions that exclude keyboard or assistive-technology users.
- Over-polishing the shell before verifying that current state/behavior (connected, empty, loading,
  error) is preserved.
- Accidentally introducing fake/demo-only UI not backed by current data, especially for "future
  overlay" surfaces (decay, dreaming, provenance, query trails).
- Turning the app into decorative cyber wallpaper instead of a usable dev-tool product — the existing
  [Graph Visual Identity](graph-visual-identity.md) non-goals apply equally to the shell.

## 10. Acceptance Criteria

Phase 27A is complete when:

- A clear planning document exists (this document).
- The graph-first shell direction is documented.
- The current dashboard-to-shell transition is explained.
- Existing surfaces are mapped to future overlay/tray/dock/command roles.
- Phase 27B scope is clearly defined, with explicit allowed/forbidden lists.
- Guardrails are explicit.
- README/roadmap are updated only if needed, and only with minimal status-focused changes.
- No frontend/backend/runtime behavior changed.
- No assets/icons/screenshots were added.
- No implementation occurred.
