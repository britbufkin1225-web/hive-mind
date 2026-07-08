# Phase 33A — 2.5D Spatial Knowledge Surface Planning

**Phase:** Phase 33A — 2.5D Spatial Knowledge Surface Planning.
**Status:** Planning / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, or runtime change. **No graph engine, no true 3D, no WebGL.**
**Relationship:** Builds on the read-only SVG Knowledge Graph view model and the
orbital-control investment documented in the
[Motion Sandbox Control Contract](../motion-sandbox-control-contract.md) and the
[Phase 32E Orbital Graph Control Contract + Motion-to-Graph Wiring Planning](phase-32e-orbital-graph-control-contract-motion-wiring.md)
doc; complements the [roadmap](../roadmap.md) and the [README](../../README.md)
phase table.

> **One-line framing.** The graph, the motion input (`MotionCommand`), and the
> orbital-camera wiring (`OrbitalGraphControlCommand` → `integrateOrbitalCamera`)
> already exist. Phase 33A defines how to evolve the *flat* graph surface into a
> **2.5D spatial knowledge surface** — a layered, orbit-able constellation — using
> only frontend-safe depth illusion, **without** adopting a 3D engine, a physics
> layout, or any new dependency. This phase writes the direction; it changes no
> runtime behavior.

---

## 1. Executive summary

Hive|Mind currently renders knowledge as a flat, read-only node-link SVG graph.
The Phase 32 motion-control arc (32B → 32K) added a webcam/MediaPipe motion
pipeline that emits a normalized `MotionCommand` and an opt-in orbital camera that
already tilts, rotates, and scales the whole graph via a CSS transform. That work
revealed the real target: the graph should not feel like a 2D chart being pushed
around — it should feel like a **spatial knowledge object** the user is handling.

This phase plans the pivot:

- **From** a flat graph-primary surface.
- **To** a **2.5D spatial knowledge surface** — a layered "knowledge
  constellation" with simulated depth, foreground/background tiers, perspective
  scaling, and depth-aware node/edge styling.
- **Preserving** the existing graph data and contracts — no backend, schema, or
  API change; all depth metadata is **frontend-derived, display-only**.
- **Preserving** the webcam/motion-control investment — the same yaw/pitch/zoom
  intent maps naturally onto orbiting a spatial field.
- **Avoiding** true-3D dependency risk for now — no Three.js, no React Three
  Fiber, no WebGL requirement, no physics engine.

Honesty boundaries, stated up front and carried through every later phase this
doc sequences:

- This is **not true 3D**. It is a 2.5D depth *illusion* built from CSS
  transforms, scale, opacity, blur, and layering over the existing SVG/React view
  model.
- It is **not VR/AR**, not a physics simulation, not AI-generated layout, not a
  new graph engine, and not a backend graph rewrite.
- The graph stays **read-only**. Nothing here mutates nodes, edges, or data.
- True 3D remains *possible later* but is **deliberately deferred** — see §2 and
  §14.

---

## 2. Why 2.5D before true 3D

A 2.5D depth illusion buys most of the "spatial object" feel at a fraction of the
cost and risk of true 3D. The point of doing 2.5D first is not to reject 3D
forever — it is to earn a real visual/depth contract and a working interaction
model *before* taking on the dependency, complexity, and QA burden of a WebGL
renderer.

| Direction            | Benefits                                                                                                   | Risks                                                                                                          | Recommendation    |
| -------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------- |
| 2.5D spatial surface | Controlled, fast, no major dependency risk; reuses existing SVG/React view model, tokens, and motion wiring; easy to QA and reduced-motion-guard; incremental and reversible | Less physically real; no true occlusion/parallax-per-vertex; depth is simulated, not computed from a camera frustum | **Recommended first** |
| True 3D / WebGL      | More powerful, physically real depth; genuine perspective, occlusion, and camera; richer future gesture interaction | Bigger dependency (Three.js / R3F / WebGL), more complexity, harder QA, accessibility/reduced-motion harder, larger bundle, GPU/perf variance, higher risk of "tech-demo" churn | **Defer** |

**Why order matters.** Jumping straight to 3D would mean designing the depth
language, the motion mapping, the selection/inspector model, and the
accessibility story *simultaneously* with fighting a new renderer. Doing 2.5D
first lets the project lock the depth contract (Phase 33B) and prove the feel
(33C–33E) cheaply. If and when true 3D is justified, it inherits a settled visual
grammar instead of inventing one under renderer pressure. True 3D stays on the
table — it is simply **not the next immediate move**.

---

## 3. Intended user experience

The desired feel:

- The user sees a floating **knowledge constellation**, not a flat diagram.
- Nodes appear **layered in depth** — some near, some far — rather than all on one
  plane.
- The **selected node feels pulled forward** toward the viewer, clearly the
  focus.
- **Related nodes glow or align** around the selected context, reading as one
  neighborhood cluster at a near/mid depth.
- **Edges feel dimensional** through opacity, scale, blur, and layering — incident
  edges come forward; distant edges recede.
- **Webcam controls feel like manipulating the constellation** — orbiting and
  tilting a structure in space — rather than dragging a flat chart around.

Recommended framing phrase (carry into 33B/33C copy):

> The user should feel like they are handling a knowledge structure, not dragging
> a diagram.

This must remain honest: the "depth" is a well-composed illusion. The goal is
that the *interaction* — orbit, tilt, zoom, focus — feels spatial, not that the
renderer is physically 3D.

---

## 4. Visual model

The 2.5D illusion is built entirely from frontend-safe techniques already
compatible with the existing SVG/React surface and token system — **no WebGL
required**:

- **Simulated `zDepth`** — a per-node display-only depth scalar (see §5) that
  drives the rest of the treatment.
- **Perspective scaling** — nearer nodes render larger, farther nodes smaller
  (CSS `transform: scale()` / SVG size), giving parallax-free but convincing
  depth.
- **Opacity falloff** — background depth tiers render at lower opacity so the
  field reads as receding.
- **Blur / focus falloff** — optional, restrained `filter: blur()` on the
  farthest tier so depth mimics a shallow focal plane (must be reduced-motion and
  performance guarded — see §12/§13).
- **Shadow / glow depth** — foreground nodes carry a stronger halo/glow; the
  selected node carries the strongest, reusing the existing per-type aura tokens.
- **Parallax offsets** — during orbit, depth tiers shift by slightly different
  amounts so the field feels layered rather than rigid (a single shared transform
  with tier-scaled offsets, not a physics sim).
- **Selected-node foregrounding** — the selected node is promoted to the nearest
  depth tier, largest and sharpest.
- **Related-node depth clustering** — the selection's direct neighbors cluster at
  a near/mid depth so the neighborhood reads as one lit cluster.
- **Edge depth hierarchy** — edges inherit depth from their endpoints; incident
  edges come forward, distant edges recede (see §10).

The visual model layers *on top of* the existing view model. It does not replace
the SVG renderer or introduce a canvas/WebGL surface.

---

## 5. Data model compatibility

**Existing graph data stays unchanged.** The 2.5D view derives all depth metadata
on the frontend, at render time, from the graph nodes/edges the app already has.
No backend, schema, API, or persistence change is required or permitted.

The 2.5D layer computes a **display-only** projection from each node/edge. Possible
derived display fields (frontend-only, never persisted, never sent to the backend):

```text
x            # existing/derived planar position
y            # existing/derived planar position
zDepth       # simulated depth scalar (display-only)
scale        # perspective scale derived from zDepth
opacity      # depth/relationship-derived opacity
depthTier    # discrete tier: foreground | near | mid | background
isForeground # convenience flag
isBackground # convenience flag
isRelated    # direct neighbor of the selected node
isSelected   # current selection
```

Rules:

- These are **frontend-derived only**. They are computed from existing graph
  structure + current selection/hover state, not read from or written to the
  backend.
- They are **display-only**. They never feed back into graph data, selection
  semantics, or any API call.
- Deriving them must be **deterministic** (see §6) so the same graph + same
  selection always yields the same layout — no random jitter.

---

## 6. Depth placement strategy

Depth assignment must be **deterministic** and driven by *relationship to the
current selection* first, with stable structural fallbacks. No random layout, no
fake intelligence.

Suggested deterministic strategy:

- **Selected node → foreground.** Nearest tier, largest, sharpest, strongest glow.
- **Directly related nodes → near / mid depth.** The selection's immediate
  neighbors cluster just behind the selected node so the neighborhood reads as one
  lit cluster.
- **Secondary nodes (2+ hops) → mid / background.** Present but subdued.
- **Unrelated nodes → background.** Smaller, dimmer, softer; never removed.
- **Source / type groups → depth clusters.** Nodes of the same type/source may be
  nudged toward a shared depth band so groups read as strata (deterministic from
  the type/source key).
- **Stale / low-confidence nodes → dimmer or farther back**, *only if* such a
  signal is already available from existing frontend data (e.g. the existing
  Temporal Decay / intelligence-derived fields). Do **not** invent a
  staleness/confidence signal for this.

When no node is selected (resting state), depth falls back to a deterministic
structural default — e.g. a stable hash of the node id, or degree/type banding —
so the field still reads as layered rather than flat, without randomness. Any
pseudo-depth **must** be deterministic from stable ids or existing graph
relationships. If it can't be derived honestly, it doesn't get added.

---

## 7. Camera and orbit model

The camera is **visual-only** and reuses the orbital-camera concept already wired
in Phase 32G/32H (`integrateOrbitalCamera` → a CSS transform on the graph view
wrapper). The 2.5D surface extends that camera to also drive depth intensity — it
does **not** replace it and does **not** mutate graph data.

- **yaw** rotates / parallax-shifts the constellation horizontally.
- **pitch** tilts / parallax-shifts the constellation vertically.
- **zoom** scales the whole field (depth approach — the field comes toward the
  viewer).
- **recenter** returns to a neutral, face-on pose (reuse the existing *Recenter
  camera* affordance from Phase 32H).
- **selected node stays legible during motion** — foregrounding and label
  legibility hold through orbit; the selected node never blurs or dims below
  readable.
- **reduced-motion users receive a calmer version** — reduced or no parallax,
  reduced or no per-frame depth animation, static-but-still-layered presentation
  (see §12).

Suggested display-only camera state (extends the existing orbital pose; all
frontend-only, never persisted):

```text
yaw            # horizontal orbit, existing
pitch          # vertical tilt, existing
zoom           # field scale, existing
depthIntensity # how pronounced the 2.5D depth separation is (new, display-only)
motionActive   # whether live motion input is currently driving the camera
```

`depthIntensity` lets the surface dial the depth illusion up during active
manipulation and settle it down at rest, and lets reduced-motion clamp it low.
The camera **never** mutates graph data — it only transforms presentation.

---

## 8. Webcam motion-control mapping

Phase 33A only **plans** this mapping. No wiring changes here. The existing
`MotionCommand` (yaw/pitch/zoom intent, pinch, confidence, active bit) maps onto
the 2.5D surface exactly as it already maps onto the orbital camera, with depth as
the new dimension:

| Motion command | 2.5D behavior                                         |
| -------------- | ----------------------------------------------------- |
| `yawDelta`     | orbit / horizontal parallax of the constellation      |
| `pitchDelta`   | tilt / vertical parallax of the constellation         |
| `zoomDelta`    | scale / depth approach (field comes toward the viewer)|
| `pinchActive`  | future focus / hold / select mode (planned, not wired)|
| `confidence`   | control quality / dampening (low confidence → damp)   |
| `active`       | camera input active / inactive (gate to idle when off)|

Notes:

- This preserves the Phase 32E/32F safety model: opt-in, off by default,
  confidence/deadzone/staleness gating, fail-safe toward stillness, read-only.
- `pinchActive` remains **deferred** as a focus/hold/select gesture — Phase 33A
  reserves the mapping slot but does not implement gesture selection (see §14).
- Implementation of this mapping onto the 2.5D depth model comes in a later phase
  (33D — Motion-to-Spatial-Surface Tuning). 33A only records the intended mapping.

---

## 9. Node behavior

How nodes behave in the 2.5D field:

- **Foreground nodes** are larger, sharper, brighter.
- **Background nodes** are smaller, dimmer, softer.
- **The selected node** has the strongest visual priority — nearest, largest,
  strongest glow.
- **Related nodes** form a visible neighborhood cluster at near/mid depth.
- **Unrelated nodes** remain present but subdued — never removed, never fully
  hidden.
- **Labels never become unreadable.** Depth may dim/soften a node, but selected
  and related labels must stay legible; background labels may reduce but must not
  become noise. Reuse the existing text-halo treatment for legibility over the
  denser field.
- **Hover / focus still work with keyboard and pointer.** Depth is additive over
  the existing interaction model, not a replacement — hover lifts and keyboard
  focus continue to function, and focus should momentarily promote a node's depth
  legibility.
- **Reduced-motion preserves usability** — a calmer, less animated depth
  presentation that is still layered and still fully interactive.

No mutation controls are added. Nodes remain read-only.

---

## 10. Edge behavior

Edge styling in the 2.5D field:

- **Edges connected to the selected node appear brighter and closer** — promoted
  toward the foreground with the selection cluster.
- **Background edges become thinner / dimmer** — receding edges drop weight and
  opacity.
- **Distant edges may use lower opacity** so the far field doesn't compete with
  the foreground.
- **Edges must not create a tangled glowing hairball.** Depth hierarchy exists to
  *improve readability* — the far field should recede and calm down, not add
  sci-fi glitter. If depth styling makes the graph busier rather than clearer, it
  is wrong.
- **Depth hierarchy should improve readability, not just decorate.** The test:
  does depth make the selected neighborhood easier to read? If not, dial it back.

No new graph engine, no edge-routing/physics library. Edges inherit depth from
their endpoints deterministically.

---

## 11. Overlay and inspector behavior

The spatial surface stays dominant; existing overlays remain contextual:

- **The knowledge surface remains the dominant, full-viewport primary surface** —
  consistent with the Phase 28A true-graph-primary contract.
- **Source Registry, Intelligence Report, Vault, Console, and inspector surfaces
  remain contextual overlays / trays / docks** — summoned, translucent, bounded,
  non-occluding glass panes, exactly as today.
- **Overlays must not flatten the spatial surface back into a dashboard.** Opening
  an overlay should not collapse the constellation into a flat panel-grid; the
  spatial field stays behind/around the overlay.
- **The inspector should feel like it is inspecting the selected spatial object** —
  the selected node reads as pulled-forward and the inspector reads as its detail
  surface, not a disconnected sidebar.
- **Existing command / rail behavior remains** unless a later implementation phase
  explicitly scopes changes. 33A changes nothing here.

---

## 12. Accessibility and reduced motion

Required rules (non-negotiable, carried into every later phase):

- **Respect existing reduced-motion patterns** (`prefers-reduced-motion`). The
  orbital camera already honors this; the 2.5D depth layer must too.
- **Avoid constant motion** for users who prefer reduced motion — no idle
  parallax drift, no perpetual depth animation. Reduced-motion gets a calm,
  static-but-layered presentation.
- **Keep labels readable** at all depth tiers that matter (selected/related), and
  never let depth dim interactive text below legibility.
- **Keep keyboard and pointer interaction intact.** Depth is additive; every
  existing keyboard/pointer path keeps working.
- **Webcam control is never required.** It stays an explicit opt-in; the surface
  is fully usable without it.
- **The camera remains explicit opt-in** — off by default, no auto-start.
- **The graph remains usable without the webcam** — orbit/tilt/zoom/focus all
  remain reachable by pointer/keyboard where already supported; the spatial
  surface degrades gracefully to a still, layered, fully navigable graph.

---

## 13. Performance constraints

Planning must acknowledge, and every later phase must respect:

- **No true 3D engine yet** — no WebGL, no Three.js/R3F.
- **No expensive per-frame layout recalculation** — depth metadata derives from
  stable structure + selection, computed once per selection/hover change, not
  every frame.
- **No physics simulation.**
- **No large dependency** — no new graph/camera/gesture/layout library.
- **Use CSS transforms / SVG / React state carefully** — prefer a single shared
  transform with tier-scaled offsets over per-node animated transforms; prefer
  compositor-friendly properties (`transform`, `opacity`) over layout-triggering
  ones; use `blur` sparingly and guard it.
- **Avoid re-render storms during webcam input** — continue the Phase 32G pattern
  of carrying per-frame motion through a ref (`motionCommandRef`) with **zero**
  React re-renders per frame; depth intensity should ride the same transform path,
  not trigger React state updates every frame.
- **Keep the frontend build stable** — `npm run check:frontend` must stay green;
  no bundle-size or dependency regressions.

---

## 14. Deferred items

Explicitly deferred (not in 33A, and not implied by it):

- **True 3D / WebGL implementation.**
- **Three.js / React Three Fiber.**
- **Physics layout / force simulation.**
- **Gesture-based selection.**
- **Pinch-to-grab graph behavior** (the `pinchActive` focus/hold/select gesture —
  mapping slot reserved in §8, not implemented).
- **Multi-camera gesture fusion.**
- **Backend layout persistence** (all depth metadata stays frontend-derived,
  display-only).
- **AI-generated spatial clustering** (depth is deterministic from existing
  structure, never AI-invented).
- **New graph mutation behavior** (the graph stays read-only).
- **Portfolio screenshot / evidence capture** (deferred; also still gated by the
  Phase 32K camera-blocked evidence policy — no fabricated or simulated evidence).

---

## 15. Proposed next phases

Recommended sequence:

```text
Phase 33B — 2.5D Spatial Surface Visual Contract + Implementation Readiness
Phase 33C — 2.5D Knowledge Constellation Frontend MVP
Phase 33D — Motion-to-Spatial-Surface Tuning Pass
Phase 33E — Live Webcam Spatial Control QA + Evidence Capture
```

**Why 33B must come before 33C:**

- The project needs a concrete **visual / depth contract** — exact depth tiers,
  scale/opacity/blur curves, glow tokens, parallax offsets, and the derived-field
  shape (§5) — *before* anyone writes implementation code.
- It avoids **hacking 3D-ish effects into the current graph without a system** —
  ad-hoc depth tweaks would accumulate into the same kind of cascade debt the
  Phase 31G consolidation had to clean up.
- It keeps the repo timeline **honest and reviewable** — a locked contract makes
  the 33C MVP diff auditable against a written spec instead of a moving target.

**Note on 33E and the camera-blocked evidence policy.** 33E (live webcam QA +
evidence) inherits the Phase 32K Path B posture: the local camera stack is
currently blocked outside Hive|Mind app logic, and **no live-gesture success may be
claimed and no evidence captured until a real working camera session verifies it.**
33E should only run once that blocker is resolved (or via the Phase 32K decision
tree's external-camera / synthetic-harness paths), and must never fabricate or
simulate evidence.

---

## Appendix — scope confirmation

- Docs / planning only. No frontend implementation changes.
- No backend, API, schema, or persistence change.
- No package / dependency change; no `package.json` / lockfile change.
- No graph mutation; the graph stays read-only.
- No Three.js / React Three Fiber / D3 / Cytoscape / React Flow / physics engine /
  new camera or gesture library / true-3D renderer / WebGL requirement.
- No fake data, no fabricated or simulated evidence, no screenshot claims.
- Existing webcam/motion-control source files are untouched — this phase only
  plans how the existing `MotionCommand` / `OrbitalGraphControlCommand` /
  `integrateOrbitalCamera` investment maps onto a future 2.5D surface.
