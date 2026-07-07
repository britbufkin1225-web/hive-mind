# Phase 32E — Orbital Graph Control Contract + Motion-to-Graph Wiring Planning

**Phase:** Phase 32E — Orbital Graph Control Contract + Motion-to-Graph Wiring
Planning.
**Status:** Planning / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, or runtime change. **No graph wiring.**
**Relationship:** Builds on the hardened `MotionCommand` contract documented in
the [Motion Sandbox Control Contract + 32C QA + 32D MediaPipe](../motion-sandbox-control-contract.md)
doc; complements the [roadmap](../roadmap.md) and the [README](../../README.md)
phase table.

> **One-line framing.** Motion input already exists (the Motion Sandbox emits a
> `MotionCommand`). Graph control does **not** exist yet. Phase 32E defines the
> contract, mapping rules, safety gates, UX behaviour, and implementation
> boundaries *between* them, so a later implementation phase can wire motion into
> the graph deliberately instead of improvising gesture spaghetti with a webcam
> garnish.

---

## 1. Executive summary

The Motion Sandbox (Phases 32B → 32D) produces a normalized, detector-agnostic
`MotionCommand` every frame: yaw/pitch/zoom intent, a pinch flag, a confidence
score, an active bit, a `source` discriminator, and a timestamp. That command is
currently **derived and displayed for inspection only** — nothing reads it into
the knowledge graph.

Phase 32E is a **planning-only** phase. It does **not** wire motion into the
graph. It defines:

- The **control contract** a future graph-control layer will consume
  (`OrbitalGraphControlCommand`), kept deliberately separate from the detector's
  `MotionCommand`.
- The **mapping rules** from motion input to graph-orbit/zoom intent.
- The **safety gates** (opt-in, off-by-default, confidence/deadzone/staleness
  gating, escape/stop, read-only) that keep the feature from hijacking the graph.
- The **UX behaviour** (explicit arming, visible status, no auto-start).
- The **implementation boundaries** (soft orbital illusion first; no 3D engine,
  no physics rewrite, no graph data mutation).

Three things must stay true through every later phase this doc sequences:

1. **Motion input exists** — the `MotionCommand` contract is stable.
2. **Graph control does not exist yet** — this phase creates the plan, not the
   wiring.
3. **Later implementation must be gated, reversible, and read-only** — the graph
   is never mutated; motion control is always opt-in and can be turned off
   instantly.

## 2. Why this phase exists

A contract *before* wiring is not bureaucracy — it is the cheapest place to
prevent the most likely failure modes. Concretely:

- **Avoiding accidental graph hijacking.** A raw detector signal fed straight
  into the graph transform would let a person walking behind the user, a lighting
  flicker, or an idle hand nudge the whole surface. The contract forces an
  explicit engagement gate, confidence gating, and deadzones so only *intended*
  motion moves the graph.
- **Keeping gesture logic separate from graph rendering.** If the graph renderer
  reaches into detector internals (landmark indices, frame-difference centroids),
  every detector change ripples into the graph. A separate graph-intent contract
  keeps the renderer depending on a small, stable shape it fully understands.
- **Preserving demo stability.** The knowledge graph is the portfolio's primary
  surface. It must render and behave exactly as it does today when motion control
  is off (the default). Planning the off-by-default, instantly-disable model up
  front guarantees the demo can never regress into a twitchy webcam toy.
- **Preventing sandbox experiments from leaking into production graph
  behaviour.** The Motion Sandbox is an isolated dock pane. Without a contract,
  the first "let's just try it" wiring pass tends to smear detector code across
  the graph component. The contract draws the boundary so experiments stay
  contained behind an explicit, typed seam.
- **Maintaining portfolio-grade architecture instead of novelty chaos wearing
  sunglasses.** The goal is an intentional, legible control layer that reads as
  deliberate engineering — not a gimmick. Planning-first keeps the MVP
  conservative and the architecture reviewable.

## 3. Existing MotionCommand contract

This is the **existing** detector-output contract, unchanged by Phase 32E. It is
documented in full in the
[Motion Sandbox Control Contract](../motion-sandbox-control-contract.md) (§4,
§13–§17); restated here for reference.

```ts
type MotionCommand = {
  yawDelta: number
  pitchDelta: number
  zoomDelta: number
  pinchActive: boolean
  confidence: number
  active: boolean
  source: "frame-difference" | "mediapipe-hand-landmarker"
  timestamp: number
}
```

Plain-language meaning of each field, with its current intended interpretation:

- **`yawDelta`** — horizontal hand motion / left-right steering. Normalized
  `-1..1`. Negative = left, positive = right (post-mirror, so the user's right
  hand reads positive).
- **`pitchDelta`** — vertical hand motion / up-down steering. Normalized `-1..1`.
  Positive = up, negative = down (the image-y inversion is already applied in the
  detector).
- **`zoomDelta`** — push-pull depth proxy. Normalized `-1..1`. Positive = hand
  closer / zoom in, negative = hand farther / zoom out. Always `0` under
  frame-difference; live (approximate, single-camera scale proxy) under the
  hand-landmarker.
- **`pinchActive`** — intentional-gesture gate candidate. A discrete "grab" flag.
  Always `false` under frame-difference (no hand model); driven by thumb-tip ↔
  index-tip distance under the hand-landmarker.
- **`confidence`** — `0..1` strength of the detected signal; whether the input
  should be trusted this frame.
- **`active`** — whether motion is currently meaningful (confidence cleared the
  detector's active gate). A consumer would gate on this before applying any
  delta.
- **`source`** — which detector produced the command
  (`"frame-difference"` or `"mediapipe-hand-landmarker"`).
- **`timestamp`** — `performance.now()` of the source frame; used for smoothing
  and stale-command checks.

## 4. Proposed OrbitalGraphControl contract

Phase 32E proposes a **future, frontend-only** graph-intent contract, deliberately
**separate** from `MotionCommand`. This type does not exist yet; it is a plan for
Phase 32F.

```ts
type OrbitalGraphControlCommand = {
  orbitYawDelta: number
  orbitPitchDelta: number
  zoomDelta: number
  isGestureEngaged: boolean
  isMotionTrusted: boolean
  confidence: number
  source: "frame-difference" | "mediapipe-hand-landmarker"
  timestamp: number
}
```

Field intent:

- **`orbitYawDelta` / `orbitPitchDelta`** — *graph-orbit* intent (already
  deadzoned, smoothed, and clamped), not raw detector deltas.
- **`zoomDelta`** — *graph-zoom* intent, likewise conditioned.
- **`isGestureEngaged`** — whether an intentional engagement gesture is currently
  held (e.g. a pinch, or an explicit "arm" toggle). Motion should only move the
  graph while this is `true`.
- **`isMotionTrusted`** — whether this frame's motion passed confidence +
  staleness gating and should be applied at full weight.
- **`confidence`** — passed through for UI display and for optional additional
  gating in the consumer.
- **`source`** — carried through for UI display / debugging only; the graph must
  **not** branch its behaviour on `source`.
- **`timestamp`** — for the consumer's own staleness / rate-limit checks.

Why this must be separate from `MotionCommand`:

- **`MotionCommand` is detector output.** It describes *what the camera saw*.
- **`OrbitalGraphControlCommand` is graph-intent output.** It describes *what the
  graph should do*, after gating and conditioning.
- **The separation keeps the graph from depending directly on detector
  internals.** The graph consumes a small, stable intent shape and never touches
  landmark math, centroids, or `pinchActive` semantics.
- **Future sources can be added without rewriting graph controls.** A new detector
  (a second hand, a pose model, a gamepad, a keyboard fallback) only has to fill
  `MotionCommand` (or feed the mapping helper); the graph-side contract and the
  graph consumer stay untouched.

## 5. Motion-to-graph mapping rules

Proposed mapping from detector output to graph-control result. These are planning
rules for the future helper (§9), not current behaviour.

| Motion input             | Graph control result              |
| ------------------------ | --------------------------------- |
| `yawDelta`               | Orbit graph left/right            |
| `pitchDelta`             | Orbit graph up/down               |
| `zoomDelta > 0`          | Zoom/pull graph closer            |
| `zoomDelta < 0`          | Push graph farther away           |
| `pinchActive === true`   | Optional engagement/gating signal |
| `confidence < threshold` | Ignore or decay input             |
| `active === false`       | Do not update graph control       |

**Note on the current graph surface.** The knowledge graph is currently a
**2D / SVG-based** deterministic render (no 3D engine, no WebGL, no physics
layout). The first implementation should therefore **fake "orbital" motion**
through a controlled transform layer — perspective / rotate / translate / scale on
a wrapper — rather than adding a real 3D engine. "Orbital" here is a *soft
illusion*, not literal 3D camera orbit around a scene graph.

## 6. Engagement and safety model

The safety model is strict by design. A gesture-driven graph must fail *safe* —
toward stillness and toward the user keeping control.

Required points:

- **Camera remains opt-in.** No camera access without an explicit user Start,
  exactly as in the sandbox today.
- **Motion control is off by default.** The graph never listens to motion until
  the user turns motion control on.
- **Graph motion control requires explicit user activation.** A distinct "enable
  graph control" step, separate from starting the camera.
- **No gesture mutates graph data.** Motion control is read-only view control
  only.
- **No gesture selects, deletes, or creates nodes** in the MVP. Motion moves the
  *view*, never the *data*.
- **No camera state persists beyond the session** unless a later phase explicitly
  scopes persistence. No silent re-arming on reload.
- **Escape or Stop immediately disables motion control.** A single, always-available
  kill path returns the graph to plain manual control at once.
- **Low confidence decays motion to zero.** Below the trust threshold, control
  eases toward no-motion rather than snapping or holding stale intent.
- **Stale timestamps are ignored.** A command older than the stale cutoff is
  dropped, not applied.

Proposed thresholds — **MVP planning defaults only, not final tuned values:**

- Minimum confidence threshold: `0.55`
- Strong confidence threshold: `0.75`
- Deadzone for yaw/pitch: `0.08`
- Deadzone for zoom: `0.05`
- Stale command cutoff: `500ms`
- Suggested smoothing window: `3–5 frames`

These are starting points to be tuned against real runtime behaviour in a later
implementation + QA pass. They are intentionally conservative (favouring
stability over responsiveness) for a first MVP.

## 7. Graph behaviour model

Desired future behaviour, by state:

- **Motion disabled (default):** the graph behaves **exactly as it does now** —
  the same manual pan/zoom/select/read-only interactions, with no motion
  listening and no transform applied.
- **Motion enabled, no engaged gesture:** the graph **remains stable**. Arming
  the feature does not, by itself, move anything; the graph waits for an engaged,
  trusted gesture.
- **Engaged gesture + trusted motion:**
  - hand left/right → orbit/rotate the graph horizontally,
  - hand up/down → orbit/rotate the graph vertically,
  - hand push/pull → zoom the graph.
- **Gesture ends:** the graph either **holds its last transform** or **gently
  eases back** to a neutral view — an implementation choice for a later phase. The
  MVP should prefer whichever reads as *stable* rather than *springy*.
- **MVP posture:** prefer **stability over spectacle**. Subtle, clamped, smoothed
  motion beats dramatic, jittery orbit.

**Recommendation — soft orbital illusion, not real 3D physics.** For the first
implementation, use a controlled transform layer over the existing SVG, not a new
rendering engine.

Allowed future implementation approach:

- A CSS / SVG transform layer wrapping the existing graph.
- Controlled `rotateX`, `rotateY`, `scale`, and `translate`.
- **Clamp** all values to bounded ranges.
- **Smooth** all values (EMA / short window).
- A **Reset** control that returns the transform to neutral.

Forbidden future implementation approach unless separately planned and approved:

- A real 3D graph engine.
- A force-directed physics rewrite.
- D3 / Cytoscape / React Flow.
- WebGL / Three.js.
- Any graph **data mutation**.
- Gesture-based **node editing**.

## 8. UI/UX contract

Motion control must present as a **deliberate graph-control mode**, not a hidden
behaviour.

The user must be able to clearly see:

- camera status (off / requesting / active / error),
- detector source (`frame-difference` vs `mediapipe-hand-landmarker`),
- confidence (the trust signal),
- whether graph control is **armed**,
- whether a gesture is currently **engaged**.

Motion controls must include:

- **Start camera**
- **Stop camera**
- **Enable graph control**
- **Disable graph control**
- **Reset graph view**

Hard UX constraints:

- **No hidden auto-start** (no camera on mount, no auto-arm).
- **No graph movement before activation.**
- **No full-screen hijack** — the graph-control mode must not seize the whole
  viewport or trap the user.
- **No permanent sidebar / dashboard regression** — the control surface must fit
  the existing floating-overlay shell and must not reintroduce a persistent
  dashboard column.

## 9. Architecture recommendation

Recommended future architecture (described, **not** implemented in Phase 32E):

```text
MotionSandboxPanel
  emits MotionCommand
motionToGraphControl helper
  converts MotionCommand -> OrbitalGraphControlCommand
KnowledgeGraphPanel / GraphCanvas
  consumes OrbitalGraphControlCommand only when graph motion mode is enabled
```

Possible future helper module:

`apps/frontend/src/orbitalGraphControl.ts`

Possible future responsibilities of that helper:

- Deadzone handling (yaw/pitch/zoom).
- Confidence gating (min + strong thresholds).
- Smoothing (short window / EMA).
- Clamp logic (bounded orbit + zoom ranges).
- Motion-to-orbit mapping (`MotionCommand` → `OrbitalGraphControlCommand`).
- Stale-command rejection (timestamp cutoff).

Keeping this logic in a small, deterministic, side-effect-free helper — mirroring
how `handLandmarkMotion.ts` isolates the landmark math — makes the gating rules
auditable and testable in one place, and keeps `KnowledgeGraphPanel` free of
detector or gating internals.

**Do not create `orbitalGraphControl.ts` (or any helper/component) in Phase
32E.** This section is planning only.

## 10. Implementation sequence recommendation

The likely next phases, in order:

### Phase 32F — Orbital Graph Control Contract Types + Helper Stub

Potential scope:

- Add the typed `OrbitalGraphControlCommand` and a helper for converting a
  `MotionCommand` into graph-control intent.
- Deterministic, unit-testable helper behaviour if the project has a frontend
  test path (deadzone / gating / clamp / staleness are all pure functions).
- **No graph wiring yet** — the helper exists and is tested in isolation; nothing
  consumes it in the graph.

### Phase 32G — Motion-to-Graph Wiring Frontend MVP

Potential scope:

- Wire trusted graph-control commands into a graph transform state.
- Add explicit **Enable / Disable / Reset** controls (per §8).
- Keep the graph **read-only** — view transform only, no data mutation.
- Preserve every existing manual interaction unchanged when motion is off.

### Phase 32H — Motion Graph Control QA + Demo Evidence

Potential scope:

- Browser runtime verification of the wired behaviour.
- Camera lifecycle verification (start/stop/error/teardown under graph-control
  mode).
- Connected UI screenshots / video notes — **only if** the frontend direction is
  approved and the evidence is real runtime capture.

## 11. Risks and mitigations

| Risk                               | Mitigation                                             |
| ---------------------------------- | ------------------------------------------------------ |
| Motion feels noisy                 | Deadzones, confidence gates, smoothing                 |
| User loses graph control           | Disable/reset controls, Escape behavior                |
| Graph becomes gimmicky             | Read-only, opt-in, subtle transform limits             |
| Detector internals leak into graph | Separate MotionCommand from OrbitalGraphControlCommand |
| Low-confidence frames cause jitter | Ignore/decay low-confidence input                      |
| Feature hurts portfolio polish     | Planning-first, conservative MVP, no 3D engine detour  |

## 12. Acceptance criteria

Phase 32E is complete only when:

- This new planning doc exists.
- The existing `MotionCommand` fields are documented (§3).
- The future `OrbitalGraphControlCommand` is proposed (§4).
- The motion-to-graph mapping rules are documented (§5).
- The safety / activation model is documented (§6).
- The UI/UX requirements are documented (§8).
- The future phase sequence is documented (§10).
- The README and roadmap reflect Phase 32E planning status (without overstating
  implementation — motion does **not** control the graph today).
- **No** runtime / source / package / backend files are changed.
- The working tree is clean after commit.
