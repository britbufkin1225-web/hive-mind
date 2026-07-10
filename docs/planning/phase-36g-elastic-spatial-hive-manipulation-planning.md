# Phase 36G — Elastic Spatial Hive Manipulation Planning

**Phase:** Phase 36G — Elastic Spatial Hive Manipulation Planning.
**Status:** Planning / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, screenshot, or runtime change. **No deformation implemented,
no camera change shipped, no persistence, no graph mutation, no new graph
engine, no true 3D, no WebGL, no physics engine, no new dependency.**
**Relationship:** Builds directly on the **Phase 36F revision 2 Spatial Hive
point-cloud foundation** (PR #148) — stable pseudo-3D node coordinates
(`spatialHiveProjection.ts`), the per-frame perspective projector, depth
sorting, camera yaw/pitch/zoom + drag orbit + cursor parallax + ambient sway
(`orbitalGraphControl.ts`), the deterministic particle shells
(`spatialHiveParticles.ts`), and the preserved living-Hive presentation in
`KnowledgeGraphPanel.tsx`. Complements the
[Phase 35A Spatial Hive Interaction State Planning](phase-35a-spatial-hive-interaction-state-planning.md),
the [2.5D Spatial Hive Visual Contract](../2-5d-spatial-hive-visual-contract.md),
the [roadmap](../roadmap.md), and the [README](../../README.md) phase table.

> **One-line framing.** Phase 36F revision 2 made the Hive a *spatial object
> you can look around*. Phase 36G plans the next capability level — making it
> a spatial object you can *handle*: spin it endlessly like a held artifact,
> and pull a node so its relationships visibly stretch and tug its neighbors
> with it, then let the web settle back. All of it presentation-only,
> deterministic, dependency-free, and read-only. This phase writes the
> contract; it changes no runtime behavior.

---

## 1. Executive summary

Phase 36G defines **Elastic Spatial Hive Manipulation**: the implementation
contract for two connected capabilities on top of the Phase 36F spatial
foundation.

1. **Infinite/freeform orbit.** Today every steering input (drag, parallax,
   sway, motion camera) composes under a hard total clamp of ±58° yaw / ±36°
   pitch. The user should instead be able to keep spinning the structure
   horizontally forever — like turning a globe — while vertical orbit stays
   controlled enough that the structure never flips and labels never invert.

2. **Elastic node-pull.** Dragging a node displaces it, and the displacement
   propagates along real graph relationships: direct neighbors follow at
   partial strength, second-degree neighbors follow weakly, unrelated nodes
   barely move. Edges stretch, particles ride their anchors, and on release
   the whole web springs back to rest. The feel target is *soft tension in
   connected tissue* — the graph's relationships made physically legible —
   not a physics toy.

Both capabilities are strictly **presentation-layer**: the source knowledge
graph (nodes, edges, source metadata, intelligence metadata) is never touched,
the deterministic layout and spatial coordinates remain the single source of
truth, and every displacement is a temporary offset that decays to zero. No
force simulation, no physics engine, no D3, no new dependency, no persistence.

The recommended path (§14) implements wrapped-yaw infinite orbit first
(Option A, §6), then the elastic deformation layer as a new pure module
(`spatialHiveElastic.ts`), then interaction wiring, and defers motion-gesture
drive and any arcball/roll exploration to later phases.

## 2. Current baseline after Phase 36F revision 2

What exists and is verified on `main` (PR #148):

- **Stable pseudo-3D coordinates.** `buildSpatialHiveNodes` lifts the
  deterministic ring layout into world space: per-node x/y from the layout
  plus bounded hash drift, z rank-stratified across ±240 viewBox units.
  Deterministic — same graph in, same cloud out.
- **Perspective projection.** `projectSpatialPoint` applies recentre → yaw →
  pitch → perspective divide (focal 560, camera distance 640/zoom, denominator
  floored at 90). Zoom is a dolly, so approach produces true parallax.
- **Composed camera pose.** `composeSpatialCameraPose` sums four inputs —
  opt-in motion camera (±32°/±24°), persistent drag orbit (±42°/±26°), eased
  cursor parallax (±16°/±11°), deterministic ambient sway (±10°/±5°) — under
  a total clamp of **±58° yaw / ±36° pitch**. This clamp is the "cannot spin
  freely" limitation Phase 36G plans to lift.
- **Depth presentation.** Per-frame depth sorting (painter's algorithm), depth
  fog for nodes and edges, depth-scaled synapse widths, camera-relative
  depth-of-field blur, depth-lit particle energy.
- **Living Hive preserved.** Breathing nodes, pulsing selected halo, related
  aura, hover-primary clarity, far/mid/near tiers, inspector, Escape stack,
  Recenter, read-only interactions, billboard labels (projection translates
  and scales but never rotates glyphs), reduced-motion stillness.
- **Interaction rules.** Drag anywhere orbits (with a 4px click-suppression
  threshold so orbiting never selects); click selects; double-click on empty
  space recenters; Recenter clears drag pose and parallax.

What does **not** exist yet:

- Any way to rotate past the total-orbit clamp.
- Any way to move an individual node, temporarily or otherwise.
- Any notion of displacement propagating along edges.

Motion tracking status: the camera/device path is live-validated (36F live
camera test), but **hand-motion control feel has not been user-tested** — no
human hand has driven the graph yet. Phase 36G therefore plans motion
*compatibility* (§9) without depending on motion testing.

## 3. Why evidence capture is deferred

The Phase 36F live-camera validation closed with screenshot/evidence capture
deferred until a human-in-frame session confirms gesture feel. Phase 36G keeps
that deferral, for three reasons:

1. **The presentation surface is still moving.** Infinite orbit and elastic
   deformation will visibly change how the graph looks and handles. Capturing
   a screenshot set now would freeze evidence of a surface the very next
   implementation phase intends to change — the same churn the evidence
   discipline exists to avoid.
2. **The strongest evidence for this feature set is interactive.** Elastic
   pull and infinite spin read as *feel*; static screenshots under-sell and
   under-verify them. Evidence should be captured once against the settled
   post-36G surface, ideally alongside the pending human-in-frame motion
   session, so one capture pass covers both.
3. **Planning-only phases do not produce evidence assets by rule.** Project
   guardrails scope screenshots to evidence phases; this phase touches
   `docs/` only.

Evidence capture remains a named, deferred obligation — it is sequenced in
§14 as the phase after the elastic implementation lands and is validated.

## 4. Definition: Elastic Spatial Hive Manipulation

**Elastic Spatial Hive Manipulation** is the capability level at which the
Spatial Hive behaves like a handled elastic object:

- an **infinite/freeform spatial orbit camera** — horizontal rotation
  accumulates without a hard stop; vertical rotation stays bounded;
- a **presentation-only deformation layer** — a per-node temporary
  displacement field applied between the world coordinates and the projector;
- **node-pull interaction** — dragging a node displaces it in world space
  following the pointer;
- **relationship-weighted elastic neighbor response** — displacement
  propagates along real edges with weights that decay by graph distance;
- **spring-back/settle behavior** — released displacement eases back to zero,
  optionally with a small overshoot for organic feel;
- **motion-tracking compatibility** — the same grab/pull/release contract can
  later be driven by pinch gestures without redesign;
- **zero mutation of underlying graph or source data** — no node position is
  ever edited, saved, or persisted; a reload (or Recenter) always restores
  the exact deterministic resting state.

The name is deliberate: *elastic* (displacement is temporary and restoring),
*spatial* (it operates in the 36F world space, not screen space), *Hive*
(every living-Hive behavior is preserved), *manipulation* (direct handling,
not passive viewing).

## 5. Layer separation: source data vs projection vs elastic interaction

The contract's load-bearing rule is that three layers stay strictly separated,
each consuming only the layer below and mutating nothing:

### Layer 1 — Source graph data (read-only, unchanged)

The real knowledge graph: nodes, edges, source metadata, intelligence
metadata, served by the backend graph API. **Nothing in Phase 36G's plan
reads more of it or writes any of it.** No new fields, no position
attributes, no persistence. The elastic layer needs only what the frontend
already has: node ids and the edge list (for adjacency).

### Layer 2 — Spatial projection layer (deterministic, unchanged in role)

The Phase 36F layer: `buildSpatialHiveNodes` (stable world x/y/z),
`projectSpatialPoint` (camera pose → screen position/scale/depth), depth
sorting, fog/DoF curves, particle shells. It remains **deterministic and
presentation-only**: same graph, same resting cloud, every reload. Phase 36G
modifies exactly one thing here — the yaw handling described in §6 — and adds
nothing else. The resting coordinates remain the single source of truth the
elastic layer displaces *from* and settles *back to*.

### Layer 3 — Elastic interaction layer (new, transient, in-memory)

A new pure module (working name `spatialHiveElastic.ts`) plus wiring in
`KnowledgeGraphPanel.tsx`'s existing per-frame driver. It owns:

- a **displacement field**: `Map<nodeId, {dx, dy, dz}>` in world units,
  starting empty and returning to empty;
- **grab state**: which node (if any) is held, and the pointer's current
  world-space target for it;
- **propagation weights**: per-node multipliers derived from graph distance
  to the grabbed node (§8), computed once per grab from the adjacency the
  frontend already holds;
- **release dynamics**: the per-frame decay that eases every displacement
  back to zero (§7);
- optional **inertia**: a small carried velocity on release, conservative and
  bounded (§7, optional).

The render pipeline becomes: resting world position **+ displacement** →
projector → screen. The displacement field is never serialized, never leaves
the component, and is cleared by release-settle, Recenter, graph-data change,
and unmount. Reduced motion collapses its dynamics (§11).

Rationale for a separate module (matching the 36F pattern): the deformation
math — weights, decay, clamps — stays pure, deterministic, auditable, and
unit-testable in one file, exactly like `spatialHiveProjection.ts` and the
pose helpers in `orbitalGraphControl.ts`. React owns only refs and event
wiring.

## 6. Infinite orbit design

### Current limitation

Yaw and pitch are clamped at three levels: per-input (drag ±42°/±26°, motion
±32°/±24°, parallax ±16°/±11°, sway ±10°/±5°) and in total
(`SPATIAL_TOTAL_MAX_YAW = 58`, `SPATIAL_TOTAL_MAX_PITCH = 36` inside
`composeSpatialCameraPose`). These were the right guardrails for first-flight
stability and screenshot sanity, but they mean the structure can only be
*tilted*, never *turned around*.

A key implementation fact: `projectSpatialPoint` feeds yaw straight into
`cos`/`sin`, so **the projector already handles any yaw value correctly** —
360°, 3600°, negative thousands. The clamp is purely a pose-composition
policy, not a projection limitation. Lifting it is a policy change, not a
math rewrite.

### Options considered

**Option A — Wrapped yaw + clamped pitch (recommended).**
Yaw accumulates endlessly; pitch keeps a clamp.

- The drag-yaw path drops its ±42° clamp and the total-yaw clamp; yaw becomes
  an unbounded accumulator, normalized into (-180°, 180°] after each
  composition step so float precision can never degrade over a long spin
  (wrapping is invisible: yaw θ and θ−360° project identically).
- Pitch keeps clamps at every level. The total-pitch bound can rise modestly
  (e.g. from ±36° toward ±60–70°) for a stronger look-over-the-top feel, but
  must stay short of ±90° so the structure never gimbal-flips and labels
  never read upside down.
- Parallax and sway keep their current small bounds and simply add on top of
  the unbounded yaw; the motion camera keeps its own bounds until §9 wiring
  revisits it.
- Cost: small — remove/rewrap one clamp, add a `wrapYawDegrees` helper,
  retune drag gain for sustained spins. Every existing safety property except
  the yaw bound is preserved verbatim.
- Risk: lowest of the three. Vertical orientation ("which way is up") is
  never lost, so users cannot get disoriented past recovery, and Recenter's
  job stays trivial.

**Option B — Arcball / virtual trackball.**
Drags apply rotations about the screen-relative axis of the drag, accumulated
as a full 3D orientation (quaternion-equivalent).

- Most "holding a real object" feel; any orientation reachable.
- Cost: replaces the yaw/pitch Euler pose with an orientation matrix through
  `projectSpatialPoint`, the pose-composition contract, the almost-equal
  rest check, and the recenter path. Sway/parallax/motion inputs must be
  re-expressed as small rotations composed onto the orientation.
- Risk: high for this surface. Arbitrary orientation means the structure can
  end up upside down or rolled; billboard labels stay unrotated glyphs but
  their *arrangement* inverts (top nodes at bottom), which reads as broken;
  users reliably lose "up" on trackballs without a horizon reference, and
  the Hive has none.

**Option C — Free yaw + pitch + roll (Euler, all unbounded).**
- Most expressive on paper, but inherits all of Option B's disorientation
  risk plus gimbal-lock artifacts near ±90° pitch that Option B avoids.
  Roll additionally breaks the one invariant that keeps labels readable
  (screen-vertical stays world-vertical-ish). Not a candidate for first
  implementation.

### Recommendation

**Implement Option A.** It delivers the actual user request — "spin the graph
infinitely" — at the lowest cost and risk, changes no projection math, and
keeps every readability invariant. Option B remains a documented future
exploration only if Option A's feel proves insufficient; Option C is
rejected (see §13). Conservative roll, if ever wanted, should arrive as a
*bounded cosmetic* (a few degrees tied to spin velocity, like banking) in a
later polish phase — never as a free axis.

### Behavior requirements (Option A contract)

- Horizontal drag keeps rotating with no hard stop, in either direction, at a
  consistent rate; crossing the wrap point is visually seamless.
- Vertical drag stays clamped; hitting the pitch bound feels like a soft
  limit (absorb, don't bounce).
- **Recenter** restores the exact neutral pose: yaw normalized to 0 (shortest
  path, e.g. 350° eases to 360° ≡ 0°, not backward through 350°), pitch 0,
  zoom 1 — and (once §7 lands) clears deformation too.
- Double-click on empty space keeps its existing recenter behavior.
- **Reduced motion:** no continuous/inertial spinning ever; drag still
  reorients (position-coupled, stops when the hand stops), sway stays
  disabled, and recenter snaps rather than glides — matching the existing
  reduced-motion stillness contract (§11).
- **Labels remain billboards:** the projection continues to translate/scale
  and never rotate glyphs, so text is readable at any yaw. At extreme pitch
  the *layout* of labels compresses vertically, which is another reason
  pitch stays clamped.
- Depth sorting, fog, DoF, and particle projection already recompute per
  frame from the pose, so they need no change to survive full rotations.

### Optional (implementer's discretion, still within Option A)

- **Spin inertia:** on release of a fast horizontal drag, let yaw coast
  briefly with exponential decay (same pattern as
  `ORBITAL_GRAPH_CAMERA_DECAY`), capped in speed and duration, disabled under
  reduced motion. This is the single cheapest "feels like a real object"
  win; it is optional, not required, for acceptance.

## 7. Node-pull deformation design

### Interaction shape

- **Grab:** pointerdown on a node, then movement past the existing
  `SPATIAL_DRAG_CLICK_THRESHOLD_PX` (4px), begins a node pull instead of a
  camera orbit (full disambiguation table in §10). The grabbed node id and
  its weight map (§8) are computed at grab time.
- **Pull:** each frame while held, the pointer position is mapped into a
  world-space displacement target for the grabbed node. Screen-to-world uses
  the inverse of the current projection at the node's depth: unscale by the
  node's projected perspective scale, then inverse-rotate through the current
  pitch/yaw so the node follows the cursor in its own depth plane. The
  grabbed node's displacement eases toward this target (a fast lerp, not a
  snap) so the pull feels like tension, not teleportation.
- **Displacement cap:** the grabbed displacement magnitude is clamped (order
  of ~120–160 viewBox units, tuned in implementation) so a node can never be
  yanked off-screen or through the camera plane; approaching the cap eases
  (soft limit), which *is* the "graph resists stretching" feel.
- **Neighbor response:** every other node's displacement is the grabbed
  node's displacement times its relationship weight (§8) — same direction,
  scaled magnitude. This "translate-with-falloff" model is deliberately the
  simplest thing that reads as connected tissue; per-neighbor directional
  variation is an optional refinement, not first scope.
- **Release:** the weight map is dropped and every displacement decays to
  zero with a per-frame exponential ease (retain-factor pattern like
  `ORBITAL_GRAPH_CAMERA_DECAY = 0.88`, plus a settle-epsilon snap so the
  loop can reach exact rest and the existing "pose unchanged → skip work"
  check can fire). Optional: a single small overshoot (damped, one visible
  oscillation at most) for organic spring feel — never a ringing spring.
- **Optional inertia:** a small fraction of the release-instant pull velocity
  may carry into the settle for liveliness; bounded, and off under reduced
  motion. Optional, not required.

### What renders during a pull

- **Nodes** render at resting position + displacement, through the normal
  projector — so fog, DoF, depth sorting, and perspective scale all react
  live if a pull moves a node in z (first implementation may keep pulls in
  the node's depth plane, making dz ≈ 0; the contract allows dz so a later
  motion input can pull nodes nearer/farther).
- **Edges** already re-project from their endpoint nodes every frame, so
  they stretch automatically — no new edge code beyond verifying the
  incident/hovered/selected width hierarchy survives.
- **Particles** anchor to their cluster node; a displaced anchor carries its
  dust shell with it (anchor position is already read per frame).
- **Labels** ride their node wrappers, unrotated, as today.
- **Hive effects continue:** breathing, glow, selected halo, related aura,
  hover states — all are wrappers/filters on the node element and are
  position-independent, so they ride the displaced positions untouched.

### Explicitly not a physics simulation

There is no integrator, no per-frame force accumulation, no velocity state per
node, no springs-between-nodes solved iteratively, no collision. The model is
**closed-form**: displacement = grab displacement × static weight, decay =
exponential ease. Given the same grab, pointer path, and frame times, the
deformation is identical — deterministic like everything else in the spatial
stack. This is why no D3 force layout, no physics engine, and no dependency
are needed, and why the behavior can be unit-tested as pure functions.

## 8. Relationship-weighted neighbor response

Weights are computed **once per grab** by breadth-first traversal over the
edge adjacency the frontend already holds (the same edge list the renderer
draws), keyed by hop distance from the grabbed node:

| Graph distance from grabbed node | Weight (contract range) | Feel |
| --- | --- | --- |
| 0 (grabbed node) | 1.0 | follows the pointer (eased) |
| 1 (direct neighbor) | 0.35–0.55 | clearly tugged along |
| 2 (second degree) | 0.12–0.25 | leans toward the pull |
| ≥3 / disconnected | 0 (or ≤0.04 optional ambient field) | still, or barely breathes toward it |

Contract rules:

- **Monotone decay:** weight strictly decreases with hop distance; a
  second-degree node never moves more than a first-degree node.
- **Deterministic:** same graph + same grabbed node → same weight map. Hash
  jitter, if any is added for organic variation, must come from the existing
  `hashUnit` id-hash pattern, never `Math.random()`.
- **Optional degree damping:** a very high-degree hub pulled directly could
  drag most of a small graph with it. The contract permits (does not
  require) scaling first-degree weight down as neighbor count grows, so
  pulling a hub reads as "heavy" — an honest structural cue. Tuned in
  implementation; start without it on the current 7-node graph.
- **The ≥3 tier defaults to zero.** The optional "subtle ambient field"
  (≤0.04) is a polish knob, off by default — unrelated stillness is itself
  information: it shows the user where relationships *end*.
- **Precomputation bound:** BFS is O(nodes + edges) once per grab —
  negligible at current scale and fine at any plausible future scale; no
  per-frame graph traversal ever happens.

Why relationship-weighted rather than radius-weighted: spatial proximity in
the ring layout is partly cosmetic, but *edges are real data*. Weighting by
graph distance means the deformation visualizes actual relationships — pulling
a source node visibly drags its documents and nothing else — which is the
entire point of making the knowledge web feel elastic.

## 9. Motion tracking compatibility

Nothing in this phase implements motion drive, but the contract is shaped so
the existing motion stack can adopt it without redesign:

- **Open hand / palm movement → orbit.** Already the shape of
  `OrbitalGraphControlCommand` (yaw/pitch/zoom deltas). Under Option A the
  motion camera's yaw integration can later switch from clamped to wrapped
  using the same accumulator; no contract change to `MotionCommand` or the
  orbital command needed.
- **Pinch near a node → grab.** The pinch gate with 0.40/0.52 ratio
  hysteresis (Phase 36E) already produces a stable engaged/released signal.
  Grab targeting can reuse hover-style hit-testing on the projected node
  positions — the elastic layer's `grab(nodeId, targetProvider)` entry point
  deliberately does not care whether the target comes from a pointer or a
  palm centroid.
- **Move pinched hand → pull.** The palm/pinch centroid maps to the same
  screen-to-world displacement target as the cursor. Because the contract
  already allows dz, a later phase could map hand depth cues to pull in z —
  scoped out for now.
- **Release pinch → spring back.** Identical release path as pointer-up; the
  hysteresis gate prevents flutter re-grabs.
- **Two-hand spin/zoom:** explicitly **not scoped**. Noted only so the
  single-hand contract doesn't preclude it (it doesn't: orbit and grab are
  independent channels).

Design rule that guarantees compatibility: the elastic module consumes
**abstract grab/pull/release events with a world-space target**, never raw
pointer or landmark data — the same separation that keeps
`OrbitalGraphControlCommand` independent of MediaPipe internals. Motion feel
testing remains pending (human-in-frame session, still deferred) and is not a
gate for the pointer implementation.

## 10. Hover / select / inspector interaction rules

The existing read-only interaction stack is preserved verbatim; node-pull
slots in via the same press-move-threshold pattern that already separates
clicks from orbits:

| Gesture | Today (36F) | After elastic phase |
| --- | --- | --- |
| Click a node (press+release under 4px travel) | selects, opens inspector | **unchanged** |
| Click an edge | selects edge | **unchanged** |
| Click empty space | clears per current stack | **unchanged** |
| Drag from empty space | orbits camera | **unchanged** (yaw now unbounded) |
| Drag from a node (past 4px) | orbits camera | **node pull** (new) |
| Release after node pull | n/a | spring-back settle; the trailing click is suppressed (same suppression rule drags already use), so a pull never accidentally selects |
| Hover | hover-primary emphasis | **unchanged**, including on displaced nodes (hit-testing uses projected = displaced positions, so the target is where the user sees it) |
| Esc | peels one surface per press (inspector → selection → …) | **one addition at the top of the stack:** if a pull is active or deformation is still settling, the first Esc cancels the grab and fast-settles deformation; subsequent presses peel as today |
| Recenter | resets camera pose, clears drag/parallax | also **clears deformation to zero** (fast settle, or snap under reduced motion) |
| Double-click empty space | recenters | **unchanged** (and now also clears deformation, via recenter) |

Additional rules:

- Pulling a node must not change selection state; pulling the *selected* node
  keeps its halo/aura running while displaced.
- The inspector stays open and correct during a pull (it reads graph data,
  which never changes).
- Selected/related/hover emphasis must remain readable mid-deformation —
  guaranteed structurally, since emphasis is attached to node elements, not
  to positions.
- Graph data remains read-only through every gesture; there is no gesture in
  this contract that writes anything.

## 11. Reduced-motion behavior

The existing contract is *stillness*: no loop, no parallax, no sway, no
shimmer — the static depth structure remains. Elastic manipulation extends it
without breaking it:

- **Orbit:** drag-to-reorient remains available (it is user-initiated,
  position-coupled motion, the accepted reduced-motion pattern), but there is
  **no spin inertia, no coasting, no ambient sway**, and recenter **snaps**
  instead of gliding.
- **Node pull:** two acceptable postures, to be decided at implementation
  with a live check: (a) pull works, position-coupled, but release **snaps**
  displacement to zero (no animated spring-back, no overshoot, no inertia);
  or (b) node pull is disabled entirely. The contract recommends (a) —
  reduced motion means no *autonomous* motion, and a node tracking the
  user's own hand is not autonomous — with (b) as the fallback if the
  neighbor-follow motion itself proves problematic, since neighbors moving
  is technically motion the user didn't directly command.
- **Never under reduced motion:** overshoot, oscillation, inertia, coasting,
  ambient field response, animated settle.

## 12. Accessibility / readability concerns

- **Label readability at all yaw:** billboards guarantee glyph orientation;
  the remaining risk is *overlap* when a spin brings near/far nodes into
  screen adjacency. Depth sorting already resolves paint order; the existing
  fog/DoF hierarchy keeps far labels recessive. Acceptance requires a
  spot-check at several yaw stops (§15).
- **Disorientation:** unbounded yaw can cost the user their bearings.
  Mitigations: pitch stays clamped (horizon never flips), Recenter is always
  one click, double-click recenter is preserved, and the neutral pose is a
  known constant. No mini-compass/axis widget is scoped — revisit only if
  live feel demands it.
- **Vestibular safety:** all continuous motion (inertia, spring-back
  animation, sway) is gated off under reduced motion (§11); nothing in the
  elastic layer introduces flashing or high-frequency oscillation (release
  overshoot is capped at a single damped swing).
- **Pointer-precision safety:** the grab threshold reuses the proven 4px
  click threshold, so selection (the core read-only function) never gets
  harder; users who never drag nodes lose nothing.
- **Keyboard users:** keyboard interaction (tab/enter selection, Esc stack)
  is position-independent and unaffected. No keyboard-driven pull is scoped;
  the feature is additive polish, not a gatekeeper to any information —
  everything the pull *reveals* (which nodes are related) is already
  available via the related-aura tier and the inspector.
- **Small-target concern:** far-tier nodes project small; grabbing them is
  harder. Acceptable: pull is an enhancement, and hit areas already include
  the node halo. No hit-area inflation is scoped for the first pass.

## 13. Non-goals and forbidden scope

Not in this phase (planning) nor in the next implementation phase:

- **No true physics:** no D3 force simulation, no physics engine, no
  iterative solver, no per-node velocity integration, no collision.
- **No new dependencies:** no Three.js, no React Three Fiber, no WebGL, no
  D3, no Cytoscape, no React Flow — the stack stays perspective-projected
  SVG + Canvas 2D.
- **No data mutation or persistence:** no editing of node positions in
  data, no saved layouts, no backend/API/schema/persistence change of any
  kind. Reload always restores the deterministic resting cloud.
- **No fake data:** deformation derives only from real edges and real user
  input.
- **No free roll / full arcball** (Option B/C, §6): rejected for first
  implementation; documented for possible later exploration only.
- **No two-hand gestures, no motion-driven z-pull, no motion feel tuning:**
  motion compatibility is contract-shaped (§9) but not implemented or tested
  in the next phase.
- **No layout editing UX:** node-pull is temporary display deformation, never
  a "move this node here permanently" feature — that would be a different
  product decision with persistence implications, and it is explicitly out.
- **No screenshots/evidence assets** in the planning phase (§3).

## 14. Recommended implementation sequence

Sequenced to keep every step small, verifiable, and independently revertable:

1. **Phase 36H-1 — Infinite yaw (Option A).** Wrap-normalize yaw, drop the
   drag/total yaw clamps, keep all pitch clamps (optionally widening the
   total pitch bound), shortest-path recenter, optional spin inertia behind
   the reduced-motion gate. Pure changes in `orbitalGraphControl.ts` +
   minimal wiring. Verify: endless smooth spin, seamless wrap, labels
   readable at all yaw stops, recenter exact, reduced-motion still.
2. **Phase 36H-2 — Elastic module (pure, unwired).** New
   `spatialHiveElastic.ts`: BFS weight map, displacement field,
   grab/pull/release transitions, decay/settle math, caps and sanitization —
   fully unit-testable with zero UI change. Verify: deterministic outputs,
   monotone weights, decay reaches exact zero.
3. **Phase 36H-3 — Pointer wiring + render integration.** Node-vs-empty
   pointerdown disambiguation, screen→world target mapping, displacement
   applied in the per-frame driver before projection, Esc/Recenter/
   reduced-motion rules from §10–§11. Verify live: pull feel, neighbor
   follow, edge stretch, particle follow, selection/inspector integrity,
   settle-to-rest, frame budget.
4. **Phase 36H-4 (or folded into 3) — Tuning + guardrail QA.** Weight/cap/
   decay tuning on the real graph; regression sweep of the living-Hive
   checklist (breathing, halo, aura, tiers, fog, DoF, labels, Escape stack).
5. **Phase 36I — Evidence capture.** The deferred screenshot/evidence pass
   against the settled surface — ideally combined with the pending
   human-in-frame motion-feel session so one session validates gesture orbit
   and (if it lands cleanly) pinch-grab.

Steps 1 and 2 are order-independent; everything else depends on 2. If the
implementation phase must be a single PR, the internal commit order should
still follow this sequence.

## 15. Acceptance criteria for the next implementation phase

Infinite orbit:

- [ ] Horizontal drag rotates the structure indefinitely in both directions
      with no hard stop and no visible seam at the wrap point.
- [ ] Pitch remains clamped; the bound absorbs softly; the structure never
      flips upside down; labels never invert or mirror.
- [ ] Recenter restores yaw 0 / pitch 0 / zoom 1 by the shortest path and
      clears all deformation; double-click-empty recenter still works.
- [ ] Depth sorting, fog, DoF, particle projection, and edge widths stay
      correct through full rotations (spot-check ≥4 yaw stops).
- [ ] Reduced motion: no inertia/coasting/sway; drag reorientation still
      works; recenter snaps.

Elastic node-pull:

- [ ] Dragging a node past the click threshold pulls it (eased) with the
      pointer; releasing settles every displacement back to exactly zero.
- [ ] Direct neighbors visibly follow at partial strength; second-degree
      neighbors follow weakly; unrelated nodes do not move (weights monotone
      in hop distance).
- [ ] Edges stretch with displaced endpoints and preserve the
      base < incident/hovered < selected width hierarchy; particles follow
      their displaced anchors.
- [ ] Pull never changes selection; click-select, edge-select, hover
      emphasis, inspector, and the Esc stack all behave per §10, including
      the new first-Esc cancel-pull rule.
- [ ] Displacement is capped; no input sequence can project a node through
      the camera plane or fling it off-screen (denominator floor still
      guarantees the projector, but the cap must hold in world space too).
- [ ] Deterministic: same graph + same grab + same pointer path → same
      deformation; no `Math.random()` anywhere in the layer.
- [ ] Graph data provably untouched: no network writes during any gesture;
      reload restores the identical resting cloud.
- [ ] Reduced motion follows §11 exactly.
- [ ] No new dependencies; `npm run check:frontend` passes; no backend / API
      / schema / package / persistence diff.
- [ ] Frame feel: interaction stays smooth on the dev machine at the current
      graph scale (qualitative check; the per-frame cost added is O(affected
      nodes), which is bounded by the weight map).

## 16. Risks and rollback strategy

| Risk | Likelihood | Mitigation | Rollback |
| --- | --- | --- | --- |
| Unbounded yaw exposes a projection edge case (precision, sorting flicker at wrap) | Low — projector is closed-form and wrap keeps yaw small | Wrap normalization each frame; spot-check yaw stops | Restore the two yaw clamps (a constants-level revert) |
| Pull feels like chaos, not tissue (over-propagation, jitter) | Medium — feel is tuning-sensitive | Weights/caps/decay are named constants in one pure module; tune live, start conservative (low weights, strong decay) | Zero the neighbor weights (grabbed-node-only pull) or disable the grab path; module is additive |
| Deformation fights the living-Hive emphasis (halo/aura mid-pull reads wrong) | Low — emphasis is element-attached, not position-attached | Regression checklist in QA step; emphasis rides wrappers | Same as above — disable grab path, camera work unaffected |
| Frame cost regression on weak hardware | Low — closed-form, O(affected nodes), skip-work check preserved | Settle-epsilon guarantees the loop reaches rest; deformation only computes while non-zero | Disable elastic layer; projection loop reverts to 36F cost |
| Disorientation from free spin in demos | Medium | Pitch clamp keeps horizon; Recenter always one click; demo script can pin a pose | Reinstate yaw clamp for a demo build via the same constants |
| Reduced-motion regression | Low | §11 rules are explicit; both features gate through the existing single reduced-motion flag | Gate elastic + infinite spin off under the flag entirely |
| Scope creep toward physics/persistence | Medium — "make it springier" pressure is predictable | §13 forbidden list; §7's closed-form rule is the contract line | n/a (prevented by contract) |

Global rollback posture: both capabilities are **additive layers over an
unchanged deterministic core**. The resting coordinates, projection math, and
living-Hive presentation do not move; reverting either feature is deleting an
offset (deformation → empty map) or restoring a clamp (yaw). No migration, no
data risk, no persistence to unwind — the worst case is a one-commit revert
back to the exact Phase 36F revision 2 surface.

---

*Phase 36G is complete when this contract, the roadmap, and the README are
merged. The next phase (36H per §14) implements against §15's checklist.*
