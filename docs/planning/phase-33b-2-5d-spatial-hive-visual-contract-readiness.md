# Phase 33B — 2.5D Spatial Hive Visual Contract + Implementation Readiness

**Phase:** Phase 33B — 2.5D Spatial Hive Visual Contract + Implementation Readiness.
**Status:** Contract / implementation-readiness / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, or runtime change. **No graph engine, no true 3D, no WebGL, no
new dependency.**
**Relationship:** Converts the
[Phase 33A 2.5D Spatial Knowledge Surface Planning](phase-33a-2-5d-spatial-knowledge-surface-planning.md)
direction — including its living-colony Hive-State / Focus-State addendum — into a
concrete, reviewable frontend **visual contract**. Complements the concise reusable
[2.5D Spatial Hive Visual Contract](../2-5d-spatial-hive-visual-contract.md), the
[roadmap](../roadmap.md), and the [README](../../README.md) phase table. Builds on
the read-only SVG Knowledge Graph view model, the per-node idle-aura/pulse
groundwork (Phase 28B), and the orbital-control investment documented in the
[Motion Sandbox Control Contract](../motion-sandbox-control-contract.md).

> **One-line framing.** Phase 33A said *what* the 2.5D spatial hive should feel
> like. Phase 33B says *exactly how future frontend phases are allowed to build it*
> — the depth rules, the Hive-State and Focus-State emphasis rules, the determinism
> rules, the reduced-motion rules, the runtime boundaries, and the proposed
> class/state names — so implementation lands as one designed system instead of an
> append-only pile of depth hacks. This phase writes the contract; it changes no
> runtime behavior.

---

## 1. Executive summary

Phase 33B converts Phase 33A's approved direction into an **implementation-ready
frontend visual contract** for the future 2.5D Spatial Hive / living-colony graph
surface. Where 33A established the target experience (a layered, orbit-able
"knowledge constellation" that reads as a living colony of symbiotic
micro-organisms, with an ambient **Hive-State** and an inspection **Focus-State**),
33B turns that target into the specific constraints, tiers, rules, and naming that a
later implementation phase (33C onward) must satisfy.

Stated plainly and carried through the whole document:

- **No runtime implementation happens in this phase.** No React component change, no
  CSS, no new class actually added to the stylesheet, no state machine wired, no
  dependency added, no graph behavior changed.
- This is a **contract / readiness** artifact. It exists to make the future
  implementation diff auditable against a written spec instead of a moving target.
- Every rule here inherits 33A's honesty boundaries: the depth is a **well-composed
  illusion** built from CSS transforms / scale / opacity / layering over the
  existing SVG/React view model; it is **not** true 3D, **not** VR/AR, **not** a
  physics simulation, **not** AI-generated layout, and **not** a backend change. The
  graph stays **read-only**.

The deliverables of Phase 33B are this long-form readiness document plus the concise
reusable [2.5D Spatial Hive Visual Contract](../2-5d-spatial-hive-visual-contract.md),
and honest README/roadmap status updates.

---

## 2. Why this phase exists

A visual contract has to exist **before** implementation for three concrete reasons.

- **Depth/motion behavior is systemic, not a one-file tweak.** 2.5D depth, ambient
  breathing, focus response, parallax, and reduced-motion all interact. If they are
  added ad hoc — one hover effect here, one glow there — they will contradict each
  other (a node that is "near" by scale but "far" by opacity, a focus rule that
  fights the ambient rhythm). A contract fixes the relationships once, up front.

- **Avoiding another append-only CSS cascade mess.** The Phase 31G consolidation had
  to clean up an accumulated aura/overlay cascade where 31B–31F declarations were
  stacked on top of each other at the same specificity. Adding depth tiers,
  Hive-State, and Focus-State without a contract would rebuild exactly that debt at
  larger scale — a pile of `!important`-adjacent overrides nobody can safely edit.
  This contract defines authoritative class/state names and single-source rules so
  the implementation is edited *in place*, not appended to.

- **2.5D needs rules before motion/depth/hover/focus behavior gets added.** "Make it
  feel spatial and alive" is not implementable without bounds: how much scale
  difference reads as depth without looking cartoonish, how much motion reads as
  alive without becoming noise, how much a focused node lifts without hiding its
  neighbors. This phase sets those bounds so 33C implements *against numbers and
  named states*, not vibes.

The cost of skipping this phase is predictable: churny "tech-demo" depth effects,
cascade debt, inconsistent motion, and an un-reviewable implementation diff. The
cost of doing it is one docs phase.

---

## 3. Current baseline from main

Summarized **only from what is merged on `main`** (no branch-only work is claimed as
merged here):

- **Custom SVG knowledge graph surface.** The Knowledge Graph is rendered as a
  read-only, deterministic node-link **SVG** view model in
  `apps/frontend/src/components/KnowledgeGraphPanel.tsx`. There is **no** graph
  library (no D3/Cytoscape/React Flow), **no** canvas, and **no** WebGL/3D renderer.

- **Graph-primary shell.** Per the Phase 28A true-graph-primary contract, the graph
  is the full-viewport primary surface; Source Registry, Intelligence Report, Vault,
  Console, and inspector surfaces are contextual overlays / trays / docks, not
  permanent dashboard columns. The shell chrome (rail, masthead, dock frames) is
  dark/chrome/neutral and carries no decorative accent color.

- **Premium interaction + living-identity groundwork.** The graph has a
  `selected > related > ambient` emphasis model, type-owned aura rings, incident-edge
  energy, hover reveals, a subtle idle aura/breathing pulse per node, and a stronger
  pulsing glow on the selected node (Phase 28B through the Phase 31 series). The
  Phase 31G consolidation merged the accumulated aura/overlay CSS into authoritative
  rules with no computed-style change.

- **Orbital / motion-control investment.** An opt-in, off-by-default **orbital
  camera** exists: `apps/frontend/src/orbitalGraphControl.ts` defines the separate
  `OrbitalGraphControlCommand` contract and the pure `MotionCommand` → graph-intent
  mapping (`mapMotionCommandToOrbitalGraphControlCommand`, `integrateOrbitalCamera`),
  wired so motion adjusts **only** a CSS transform on a view wrapper around the graph
  SVG (yaw→rotateY, pitch→rotateX, zoom→scale), never graph data. It is
  confidence/deadzone/staleness gated, decays to neutral on stillness, and honors
  `prefers-reduced-motion`.

- **Honest posture on live motion + evidence.** Per Phases 32I–32K, the live
  hand-motion feel is **implemented but unverified** because the local camera stack
  is blocked outside the app; all evidence remains deferred. Nothing in 33B changes
  or relies on that being resolved.

- **Current depth posture: none.** The graph today is **flat** — a single plane.
  There is no `zDepth`, no depth tier, no Hive-State/Focus-State state machine. 33B
  is the contract for adding that later; it does not exist on `main` yet.

Branch-only caveat: Phase 31I (graph overlay legibility) is implemented on its
feature branch but **not merged into `main`**, so it is not treated as part of the
baseline here.

---

## 4. Relationship to Phase 33A

Phase 33A established the direction; 33B is bound by it and makes it enforceable.

**The Phase 33A 2.5D direction** (summarized): evolve the flat graph into a 2.5D
spatial knowledge surface using frontend-safe depth illusion only — simulated
`zDepth`, perspective scaling, opacity falloff, glow depth, restrained blur,
parallax offsets, selected-node foregrounding, related-node depth clustering, and
edge depth hierarchy — over the existing read-only SVG view model, with the orbital
camera extended to also drive depth intensity. Not true 3D; no new dependency; all
depth metadata frontend-derived and display-only.

**The living-colony model** (Phase 33A Addendum A) that 33B must honor:

- **Hive-State** — the ambient, resting, whole-system pose: the colony breathes,
  pulses, and drifts with coordinated, low-amplitude, cluster-organized rhythm so it
  reads as a living whole rather than a bag of blinking dots.
- **Focus-State** — the inspection pose: the selected node and its neighborhood come
  forward and organize into a legible local organism, unrelated nodes recede,
  ambient rhythm damps globally while the focused cluster gains a slightly livelier
  attentive rhythm.
- **Deterministic low-amplitude motion** — every oscillation/drift is tightly
  bounded and derived from stable ids/keys; no `Math.random()`, no unbounded random
  walk.
- **Deterministic grouping** — cluster families and sub-clusters derived from
  existing traits (source / topic / type / size) with stable keys; no invented
  taxonomy, no AI clustering.
- **Graph-only color discipline** — color, aura, glow, and energy live in the graph;
  the shell stays dark/chrome/neutral; overlays stay translucent neutral glass.
- **Reduced-motion protections** — `prefers-reduced-motion` clamps amplitude toward
  zero into a still-but-layered, fully usable presentation; emphasis carried by
  depth/opacity rather than movement.

**What 33B does with those ideas:** it turns each of them into an *implementation
constraint* — named depth tiers, named states, amplitude bounds, determinism rules,
reduced-motion rules, runtime boundaries, and proposed class/state names — so a
future Claude/Codex session can implement Hive-State and Focus-State against a spec
rather than re-deriving 33A's intent.

---

## 5. Visual contract principles

The non-negotiable rules the future frontend implementation must follow:

- **The graph dominates the surface.** The knowledge graph remains the full-viewport
  primary surface / viewfinder — the application *is* the graph, not a widget inside
  a card grid. Nothing added for depth or life may shrink the graph into a panel.
- **No persistent sidebar.** No permanent dashboard column, sidebar, or card-grid
  frame is reintroduced. Tools remain contextual overlays/trays/docks.
- **Minimal non-graph color.** The shell chrome stays dark, neutral, and restrained.
  No decorative accent color splashes into rail, masthead, dock frames, or overlays.
- **Color energy lives mainly in graph nodes/edges/aura.** Node/cluster hue, aura,
  glow, and depth are where the system's color and life concentrate; color should
  encode meaning (type/source/cluster family) where possible, not decorate.
- **Depth must feel spatial, not cartoonish.** Depth is a restrained illusion —
  believable near/far separation, not exaggerated drop-shadows, huge scale jumps, or
  toy-like layering.
- **Motion must feel alive but not random.** Ambient motion is coordinated,
  low-amplitude, and deterministic — a breathing colony, never jitter or a lava
  lamp.
- **Focus must clarify, not obscure.** Entering Focus-State must make the selected
  neighborhood *easier* to read. If a focus effect hides information or adds
  confusion, it is wrong.
- **Overlays orbit/support the graph rather than compete with it.** Inspector,
  Sources, Intelligence, Vault, and Console overlays stay translucent, bounded, and
  non-occluding; opening one must not flatten the spatial field back into a
  dashboard. They read as *around/behind* the living graph, not in front of a dead
  one.

---

## 6. 2.5D depth contract

How depth is represented **without true 3D**. Depth is a composed illusion from
frontend-safe properties; there is no camera frustum, no per-vertex occlusion, no
WebGL.

- **z-tier / depth-tier concept.** Every node resolves to a discrete **depth tier** —
  proposed set: **near** (foreground), **mid**, **far** (background). Tiers are the
  primary depth handle; continuous `zDepth` may drive within-tier nuance but tiers
  are what styling keys off, so behavior stays legible and QA-able.
- **Scale differences.** Nearer tiers render larger, farther tiers smaller, via a
  bounded scale ramp (e.g. near > mid > far). The ramp must stay restrained — enough
  to read as depth, not enough to look cartoonish. Exact ratios are tuned in the
  implementation pass; the contract requires *monotonic and bounded*.
- **Opacity falloff.** Farther tiers render at lower opacity so the field reads as
  receding — but never so low that a background node or its label becomes unreadable
  noise.
- **Shadow / aura strength.** Foreground nodes carry a stronger halo/glow; the
  selected node carries the strongest, reusing the existing per-type aura tokens.
  Background auras soften. Aura strength reinforces tier, not fights it.
- **Blur restraint (if used later).** A restrained `filter: blur()` on the farthest
  tier may mimic a shallow focal plane, but it is **optional, minimal, and guarded**
  — it must be performance-safe and disabled under reduced-motion / low-power
  conditions. Depth must remain fully legible with blur off.
- **Label priority.** Selected and related labels always stay legible; mid labels
  stay readable; far labels may reduce but must not become visual noise. Reuse the
  existing text-halo treatment for legibility over the denser depth field.
- **Edge visibility priority.** Edges inherit tier from their endpoints. Incident /
  foreground edges come forward (brighter, slightly heavier); background edges thin
  and dim. The far field recedes and calms; it must not become a glowing hairball.
- **Selected/focused node always rises visually.** The selection is promoted to the
  nearest tier — largest, sharpest, strongest glow — and stays legible through orbit.
- **Related cluster gets secondary lift.** The selection's direct neighbors cluster
  at near/mid depth so the neighborhood reads as one lit local organism.
- **Unrelated nodes recede but remain readable.** Non-related nodes drop to
  mid/far, dimmer and softer — **never removed, never fully hidden**.

Depth hierarchy exists to **improve readability**, not to decorate. The governing
test (from 33A §10): does depth make the selected neighborhood easier to read? If
not, dial it back.

---

## 7. Living-colony Hive-State contract

Ambient behavior for the **non-selected** graph (resting pose). Hive-State makes the
whole colony feel alive through subtle, coordinated motion while staying fully
legible.

- **Deterministic breathing.** A slow, low-amplitude scale/opacity oscillation on
  nodes and cluster halos. Period and phase derive from a stable key (see §9); the
  same graph breathes identically on every reload.
- **Phase-organized pulsing.** A gentle glow pulse organized by **cluster phase** so
  a cluster reads as one organism, not independently blinking dots. Different
  clusters may sit at slightly offset phases so the colony feels populated, not
  metronomic.
- **Aura / ring oscillation.** Resting halos expand and settle within a tight,
  clamped bound — a breathing ring, never a strobe.
- **Spring-to-home micro-movement.** Barely-perceptible positional drift within a
  clamped radius around each node's **deterministic home position**, modeled as a
  spring back to home. The node always returns to home; it never wanders away from
  it.
- **No random walk.** No `Math.random()` jitter, no cumulative drift, no unbounded
  movement. All apparent liveliness is deterministic oscillation around a fixed home.
- **No physics dependency.** No physics/force library, no simulation loop that
  integrates real forces. "Spring-to-home" is a bounded easing expression, not a
  physics engine.
- **No layout instability.** Node home positions do not change frame to frame; the
  graph's structural layout is stable. Only the tiny bounded display offset animates.
- **No data mutation.** Hive-State never mutates nodes, edges, selection semantics,
  or any data. It is display-only.
- **Idle graph should feel alive without becoming noise.** A user must be able to
  read the graph *while* it breathes. If ambient motion degrades legibility, its
  amplitude is reduced or it is removed.

---

## 8. Focus-State contract

Selected / inspected behavior. Focus-State is the colony leaning toward attention —
the same renderer and same colony as Hive-State, in its attentive pose.

- **Selected node becomes the spatial anchor.** It is promoted to the nearest depth
  tier (§6): largest, sharpest, strongest glow, always legible — including through
  orbit/tilt/zoom.
- **Related nodes form an illuminated local organism/cluster.** Direct neighbors come
  to near/mid depth and settle into a calmer, tighter, more readable local
  arrangement so the neighborhood reads as one lit cluster, not scattered dots.
- **Unrelated nodes recede.** Non-related nodes drop to background depth — dimmer,
  softer, smaller — but remain present and readable; never removed, never fully
  hidden.
- **Selected edge / relationship paths become legible.** Edges incident to the
  selection are promoted forward (brighter, slightly heavier); distant edges thin and
  recede so the selected relationships read clearly against a calmed far field.
- **Inspector / overlay feels connected to the selected node.** The inspector reads
  as inspecting the pulled-forward organism — the detail surface of the anchored node
  — not a disconnected sidebar. Overlays stay translucent so the anchored node reads
  through/behind them.
- **Ambient damps, focus energizes.** Global Hive-State rhythm damps down while the
  focused neighborhood gains a slightly livelier, attentive rhythm, so attention
  visibly concentrates energy where the user is looking rather than compounding
  motion everywhere.
- **Focus works with keyboard and pointer selection.** Focus-State must be reachable
  and behave identically whether the node was selected by pointer or keyboard;
  keyboard focus indicators are preserved.
- **Focus must not break current read-only graph behavior.** Selecting a node still
  only selects it — no mutation, no layout change, no data change. Deselecting
  returns the colony to Hive-State non-destructively.
- **Transition is smooth, bounded, brief, reversible.** Hive↔Focus is a short eased
  settle (reuse the existing easing discipline) — no snap, no long cinematic move —
  and fully reversible on deselect.

---

## 9. Determinism contract

How the future implementation must avoid randomness. Determinism is what keeps the
"living" surface reproducible and QA-able; the **same graph data must produce the
same visual structure on every reload**.

- **Stable id hash.** Per-node phase/period/home-offset derive from a stable hash of
  the node id — a pure function of the id, not of load order, time, or `Math.random()`.
- **Stable cluster / source / type hash.** Cluster-level rhythm and grouping derive
  from stable hashes of the grouping key (source / topic / type / size), so cluster
  coordination is reproducible.
- **Deterministic phase offsets.** Breathing/pulsing phase offsets are computed from
  (cluster key + node id) so a cluster shares a rhythm and different clusters sit at
  reproducible offset phases — never random offsets.
- **Deterministic depth-tier assignment.** Tier assignment is a pure function of
  (relationship-to-selection, then stable structural fallback such as an id/degree/
  type hash). With no selection, resting tiers fall back to a deterministic
  structural default so the field still reads layered — never randomized.
- **Deterministic aura rhythm.** Aura/ring oscillation period and phase derive from
  the same stable keys, so auras breathe reproducibly.
- **Deterministic grouping fallback.** If a preferred grouping trait is missing on a
  node, fall back to a defined deterministic order (e.g. type → source → degree
  banding). Never fabricate a trait to force a grouping; never randomize the
  fallback.
- **Same graph data ⇒ same visual structure every reload.** This is the acceptance
  invariant for the determinism contract. Any effect that cannot be derived
  deterministically from stable ids/keys or existing relationships does not get
  added.

---

## 10. Reduced-motion and accessibility contract

Required reduced-motion behavior (non-negotiable, inherited from 33A §12 and
tightened here).

- **Respect `prefers-reduced-motion`.** The orbital camera already honors it; the
  depth/Hive-State/Focus-State layer must too. This is a hard requirement, not a
  nice-to-have.
- **Disable or flatten colony motion.** Under reduced motion, ambient breathing,
  pulsing, ring oscillation, micro-movement, and parallax clamp toward zero — the
  colony becomes **still but still layered**. No idle drift, no perpetual animation.
- **Keep selected/focus visibility.** Focus-State still works under reduced motion:
  the selected node still lifts and its neighborhood still reads — emphasis is
  carried by **depth/opacity/scale**, not by movement. Hive↔Focus becomes a
  near-instant, low/no-motion change of emphasis.
- **Preserve keyboard focus indicators.** Every keyboard focus ring / indicator that
  works today keeps working; depth styling must not paint over or dim focus
  indicators below visibility.
- **Maintain readable labels / contrast.** Labels and interactive text stay legible
  at every tier that matters, and depth must never dim interactive text below the
  existing contrast/legibility bar.
- **Do not depend on motion alone to communicate state.** State (selected, related,
  receded, cluster membership) must be readable from static depth/opacity/scale/color
  cues, so a reduced-motion user loses no information. Motion is additive emphasis,
  never the sole signal.
- **Webcam control remains optional.** The surface is fully usable — orbit/focus/read
  — by pointer and keyboard without the webcam; motion control stays explicit opt-in,
  off by default.

---

## 11. Graph data and contract preservation

The future implementation must not require backend changes and must preserve the
existing contracts.

- **No backend schema change.** All depth/state metadata (`zDepth`, tier, phase,
  home-offset, cluster key, isSelected/isRelated/isReceded flags) is **frontend-
  derived at render time, display-only** — never persisted, never sent to the
  backend, never read from a new API field.
- **Preserve the existing graph node/edge view model.** The 2.5D layer computes its
  display projection *from* the existing node/edge view model; it does not replace or
  restructure it.
- **Preserve existing selected node/edge behavior.** Selection semantics stay
  identical — selecting a node/edge still only selects it. Focus-State styling layers
  on top of the existing selection state, not instead of it.
- **Preserve the existing read-only graph posture.** No mutation controls, no drag-to-
  move, no node/edge creation/deletion, no layout editing. The graph stays read-only.
- **Preserve the existing inspector relationship.** The inspector still opens for the
  selected node and reads its details; Focus-State makes it *feel* connected to the
  anchored node without changing what the inspector does.
- **Preserve the existing orbital camera control path.** Depth intensity rides the
  existing `integrateOrbitalCamera` → single shared CSS transform path; it does not
  fork a second camera or replace the orbital pose model.
- **Preserve the existing motion command bridge.** The `MotionCommand` →
  `OrbitalGraphControlCommand` → camera bridge stays intact and separate; the 2.5D
  layer consumes the camera pose, it does not rewrite the motion contract.

---

## 12. Future frontend touch map

Likely future implementation files, identified **without editing them now**. For
each: what a future phase *may* change and what it *must not*.

- **`apps/frontend/src/components/KnowledgeGraphPanel.tsx`**
  - *May later:* derive display-only depth tiers / phases / home-offsets from the
    existing view model + selection; apply depth-tier and Hive-State/Focus-State
    classes/attributes to node/edge/label elements; add reduced-motion-guarded
    ambient/focus styling hooks; consume the orbital camera pose to modulate depth
    intensity.
  - *Must not:* mutate graph data, change selection semantics, alter the node/edge
    data model, add a graph/physics/3D library, introduce a canvas/WebGL surface, or
    make the graph writable.

- **`apps/frontend/src/styles.css`**
  - *May later:* add the authoritative depth-tier / Hive-State / Focus-State rules
    (single-source, edited in place) using the proposed names in §13, with
    `prefers-reduced-motion` guards.
  - *Must not:* reintroduce a persistent sidebar/dashboard grid, splash accent color
    into shell chrome, or rebuild the Phase 31G cascade debt by appending
    same-specificity overrides instead of editing authoritative rules.

- **`apps/frontend/src/orbitalGraphControl.ts`** *(only if camera/orbit mapping needs
  later coordination)*
  - *May later:* expose or extend a display-only `depthIntensity` on the camera pose
    so depth separation dials up during active manipulation and settles at rest,
    riding the existing pure-helper/zero-re-render path.
  - *Must not:* mutate graph data, change the `MotionCommand` /
    `OrbitalGraphControlCommand` contracts, break the opt-in/off-by-default/gating/
    fail-safe-to-stillness safety model, or make helpers non-deterministic.

- **Existing graph helper / view-model files (if present)** — e.g. any current
  view-model or geometry helper alongside the panel.
  - *May later:* host the pure, deterministic depth/phase/cluster derivation helpers
    (stable-hash based), kept side-effect-free and unit-testable.
  - *Must not:* introduce randomness, fetch new backend fields, persist derived
    display state, or fabricate traits to force grouping.

No file in this map is edited in Phase 33B. This is a forward-looking map only.

---

## 13. Proposed class/state naming readiness

Proposed implementation-ready CSS/state names for future phases. **These are
proposals only — none are added to any stylesheet or component in Phase 33B.** They
exist so 33C implements against agreed names and avoids inventing conflicting ones.

Depth tiers:

- `graph-depth-tier-near`
- `graph-depth-tier-mid`
- `graph-depth-tier-far`

Colony / focus states:

- `graph-hive-state` — root/ambient state flag for the resting colony
- `graph-focus-state` — root/attentive state flag when a node is selected/inspected
- `graph-node-focus-anchor` — the selected spatial-anchor node
- `graph-node-focus-related` — a related node in the illuminated cluster
- `graph-node-receded` — an unrelated, receded background node
- `graph-colony-cluster` — a cluster-family / sub-cluster grouping container
- `graph-reduced-motion` — reduced-motion-clamped presentation flag

Naming intent (for the implementer): keep the `graph-` prefix so depth/colony
concerns are visibly graph-owned and never leak into shell chrome; keep tier and
state as separate orthogonal axes (a node has one depth tier *and* one focus role);
prefer a single authoritative rule per name over stacked overrides. Additional names
(e.g. an edge-tier or aura-strength modifier) may be introduced in 33C **as long as
they follow this prefix/orthogonality discipline** and are documented alongside the
existing ones rather than appended ad hoc.

---

## 14. Acceptance criteria for the future implementation pass

What **Phase 33C** (and the motion/focus pass that follows) must satisfy when
implementation begins:

- **Graph appears more spatial without becoming true 3D.** Believable near/far depth
  from scale/opacity/aura/tier — no WebGL, no Three.js, no physics.
- **Selected node visually lifts.** Focus-State promotes the selection to the near
  tier as the clear spatial anchor, legible through orbit.
- **Related cluster becomes more readable.** The neighborhood organizes into one
  illuminated, legible local cluster.
- **Ambient graph feels alive but calm.** Hive-State breathes/pulses with
  coordinated, low-amplitude, deterministic motion and stays fully readable while it
  does.
- **Reduced-motion mode remains stable.** Under `prefers-reduced-motion` the colony
  is still-but-layered, fully usable, with emphasis carried by depth/opacity and all
  focus indicators intact.
- **Determinism holds.** Same graph data ⇒ same visual structure every reload.
- **No new dependencies.** No graph/camera/gesture/physics/3D library added.
- **No backend / API / schema changes.** All depth/state metadata frontend-derived,
  display-only.
- **No graph mutation.** The graph stays read-only.
- **No fake data.** No fabricated nodes/edges/traits/evidence.
- **Frontend build must pass.** `npm run check:frontend` stays green with no
  bundle-size or dependency regression.

---

## 15. Deferred items

Explicitly deferred — not in 33B, and not implied by it:

- **True 3D.**
- **Three.js / React Three Fiber.**
- **Physics simulation / force layout.**
- **Graph data mutation** (the graph stays read-only).
- **AI layout generation / AI clustering** (grouping and depth are deterministic from
  existing structure).
- **Dual-camera gesture fusion.**
- **Screenshot / evidence capture** (still gated by the Phase 32K camera-blocked
  evidence policy — no fabricated or simulated evidence).
- **Logo / icon asset changes.**
- **Portfolio screenshot lock.**

---

## 16. Recommended next phases

- **Phase 33C — 2.5D Spatial Hive Frontend Foundation Pass.** First implementation
  pass: derive display-only depth tiers and apply the depth contract (§6) plus the
  base Hive-State/Focus-State emphasis over the existing view model, against the
  proposed names (§13). Reduced-motion guarded; no new dependency; graph read-only.

- **Phase 33D — Living-Colony Motion + Focus-State Frontend Pass.** Adds and tunes
  the ambient breathing/pulsing rhythm (§7), the Focus-State attentive response and
  Hive↔Focus transition (§8), and the depth-intensity coupling to the orbital camera
  — all deterministic, low-amplitude, reduced-motion-clamped.

- **Phase 33E — 2.5D Spatial Hive QA + Evidence Decision.** QA of the settled surface
  and a decision on evidence. **Evidence stays deferred** until the frontend is
  visually settled enough to justify capture, and remains gated by the Phase 32K
  camera-blocked evidence policy — no fabricated or simulated evidence.

---

## Appendix — scope confirmation

- Docs / contract / implementation-readiness only. No frontend implementation change.
- No backend, API, schema, or persistence change.
- No package / dependency change; no `package.json` / lockfile change.
- No CSS implementation; no React component change; the proposed names in §13 are
  **not** added to any stylesheet or component.
- No graph mutation; the graph stays read-only.
- No Three.js / React Three Fiber / D3 / Cytoscape / React Flow / physics engine /
  canvas / new camera or gesture library / true-3D renderer / WebGL requirement.
- No new dependency.
- No fake data, no fabricated or simulated evidence, no screenshot claims.
- Existing webcam/motion-control investment untouched — 33B only defines how the
  existing `MotionCommand` / `OrbitalGraphControlCommand` / `integrateOrbitalCamera`
  investment maps onto a future 2.5D spatial hive.
- Preserves the "2.5D first, not true 3D yet" decision.
