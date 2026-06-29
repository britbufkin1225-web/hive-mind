# Hive|Mind Graph Visual Identity

## Purpose

This document defines the graph-forward visual direction for Hive|Mind after the Phase 25 premium dark-metallic frontend work.

The goal is to make the Knowledge Graph feel like a living intelligence map while preserving the project’s core principles:

- truthful runtime behavior
- read-only graph presentation
- no fake intelligence
- no unsupported visual states
- no graph mutation
- no full 3D

Hive|Mind should look visually spectacular, but the spectacle must communicate real structure, selection, relationship, provenance, or future-labeled product direction.

## Visual Direction

Hive|Mind should use a 2.5D living intelligence map.

This means:

- depth
- glow
- layering
- visual hierarchy
- clustered spatial composition
- premium dark-metallic atmosphere

This does not mean:

- full 3D navigation
- camera controls
- React Three Fiber
- physics spectacle
- unreadable spinning nodes
- fake intelligence animation

The graph should feel like an intelligence console, not cyber wallpaper.

## Constellation Layout

The graph should move toward deterministic constellation-style clustering.

Nodes should appear as related knowledge systems instead of a flat diagram.

Cluster behavior should be based on real graph structure only:

- source type
- node type
- relationship type
- degree/connectedness
- selected neighborhood
- available backend-provided metadata

No random layouts should be used for demo-critical presentation.

## Focus Tunnel

The graph should support a Focus Tunnel selection model.

When a node is selected:

- the selected node becomes the visual anchor
- directly related nodes remain emphasized
- incident edges remain emphasized
- unrelated nodes and edges dim
- the inspector presents selected-node detail as the command surface

This should make graph traversal understandable without mutating graph data.

## Pulse Propagation

Pulse Propagation should only appear when it communicates a meaningful action.

Allowed examples:

- selecting a node
- showing relationship traversal from a selected node
- emphasizing connected neighborhood paths

Forbidden examples:

- ambient fake activity
- fake agent traces
- random glowing motion
- simulated intelligence that is not backed by actual data or interaction

Motion must respect reduced-motion preferences.

## Semantic Node Aura / Ring System

Nodes may use aura/ring styling to communicate real or clearly future-labeled states.

Possible real-backed states:

- selected
- related
- dimmed
- source-backed
- high connectedness
- known node type
- known source type

Possible future states, only if clearly labeled as future:

- confidence
- provenance strength
- decay risk
- conflict/uncertainty
- agent trail involvement
- query memory activity

Do not display future states as active runtime behavior until supported by real data.

## Semantic Edge Personalities

Edges should visually communicate relationship type.

Possible styling dimensions:

- line weight
- glow intensity
- dash pattern
- curvature
- arrow marker treatment
- selected/incident emphasis
- dimmed state

Edge styling must be based on existing relationship types.

Do not invent relationship semantics.

## Intelligence Legend

The Knowledge Graph should include a visual grammar panel or legend.

The legend should explain:

- node type styling
- selected state
- related state
- dimmed state
- edge relationship styling
- any supported aura/ring meanings
- any intentionally deferred future states

The legend should keep the graph understandable instead of making users decode a neon crime scene.

## Inspector as Command Surface

The graph inspector should feel like a command surface for the selected record.

It should clearly show:

- selected node identity
- node type
- connected relationships
- source/model/provenance metadata where available
- relationship context
- read-only status

It should not imply mutation, editing, or hidden AI behavior unless those features are explicitly implemented later.

## Zoom-as-Meaning

Future graph work may use progressive disclosure.

At different viewport or density levels, the graph may reveal:

- high-level clusters
- node labels
- relationship labels
- metadata badges
- provenance/decay/query overlays

This should be treated as future direction unless implemented in a scoped frontend phase.

## Agent Trails

Agent Trails should only appear where real workflow, query, provenance, or audit data supports them.

Do not fabricate:

- agent actions
- reasoning paths
- workflow execution
- query history
- provenance trails

If unsupported, Agent Trails remain future product direction only.

## Thought Formation

Thought Formation may be a future knowledge-intake animation concept.

It should represent a real intake/import/query event only after such event data exists.

It is not current runtime behavior.

## Conflict Visualization

Conflict Visualization should only appear when Hive|Mind has real contradictory, uncertain, or competing knowledge states.

Until supported by backend data, conflict visuals remain future direction.

## Motion Rules

Motion should be cinematic but meaningful.

Allowed:

- selection transition
- relationship pulse
- hover/focus emphasis
- reduced visual movement for dimmed context
- subtle graph breathing only if not misleading

Forbidden:

- meaningless ambient animation
- fake live intelligence
- fake telemetry
- fake agent traces
- visual noise that reduces readability

Reduced-motion support is required for implementation phases.

## Library Posture

The first implementation pass should use current SVG/CSS.

Reason:

- the graph is currently small
- SVG is already in use
- SVG supports labels, rings, filters, markers, paths, states, and selection animation
- CSS can handle depth, glow, dimming, and reduced-motion behavior

Future library evaluation:

- D3 may be considered for more complex deterministic layout helpers.
- React Flow may be considered if the graph becomes an editable workflow surface.
- PixiJS may be considered if rendering volume exceeds SVG performance.
- Sigma.js may be considered for large network exploration.
- Cytoscape.js may be considered for graph algorithms and advanced layouts.

No graph library should be added until the current SVG/CSS approach is insufficient.

## Explicit Non-Goals

This visual direction explicitly rejects:

- full 3D graph
- React Three Fiber as the next milestone
- graph mutation
- drag persistence
- physics simulation as a product gimmick
- fake runtime intelligence
- fake screenshots
- fake agent traces
- fake confidence/provenance/conflict indicators
- animation without meaning
- visual spectacle that reduces auditability

## Phase Direction

Recommended sequence:

1. Phase 26A — Graph Visual Identity Planning
2. Phase 26B — Living Intelligence Map Foundation
3. Phase 26C — Living Intelligence Map QA + Evidence

Phase 26B should be frontend-only and should preserve the existing graph data contract.

Phase 26C should capture real connected runtime evidence only after implementation exists.
