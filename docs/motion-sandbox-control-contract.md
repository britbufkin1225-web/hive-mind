# Motion Sandbox Control Contract + Phase 32C QA + Phase 32D MediaPipe

**Phase:** Phase 32D — MediaPipe / Hand Landmark Motion Detection (builds on the
Phase 32C contract hardening below).
**Scope:** Frontend-only. No backend, API, schema, or persistence change. **No
graph control wiring.** Phase 32D adds one pinned frontend dependency
(`@mediapipe/tasks-vision`); Phase 32C added none.
**Surface:** `apps/frontend/src/components/MotionSandboxPanel.tsx` (the isolated
"Motion" dock pane), the landmark-math helper
`apps/frontend/src/handLandmarkMotion.ts`, and scoped styles in
`apps/frontend/src/styles.css`.

This document is the durable home for the local `MotionCommand` contract, the
Phase 32C runtime-QA record, and the Phase 32D MediaPipe hand-landmark mode. It
complements the [roadmap](roadmap.md) and the [README](../README.md) phase table.

> **Phase 32D at a glance.** The frame-difference estimator is preserved as a
> zero-dependency fallback / debug visualiser; MediaPipe Hand Landmarker is added
> as the primary estimator. Both fill the *same* `MotionCommand` contract, with
> `source` as the discriminator. `zoomDelta` and `pinchActive` — structurally
> impossible under frame-difference — become live under the landmark estimator.
> The Phase 32D specifics live in §13–§17; §1–§12 remain the Phase 32C record.

---

## 1. Phase summary

Phase 32C verifies the standalone webcam motion sandbox that Phase 32B shipped,
tightens the local `MotionCommand` contract so its semantics are explicit and
predictable, and documents the expected yaw/pitch/zoom behaviour **before** any
future graph wiring.

It answers one practical question: **is the dependency-free frame-difference
detector good enough as a temporary motion-control prototype, or does Phase 32D
need MediaPipe / hand-landmark work?** Short answer:
frame-difference is a fine *signal visualiser* and a fine fallback, but it is not
trustworthy enough to drive the graph directly — see the recommendation in §10.

Phase 32C **defines the contract only**. It deliberately does not connect the
contract to any graph behaviour. Graph wiring remains future work.

## 2. What Phase 32B provided

- A standalone "Motion" dock pane (`MotionSandboxPanel`) reachable from the shell
  nav, fully isolated from the knowledge graph.
- Explicit, user-initiated camera lifecycle: nothing starts on mount; the camera
  is requested only after a **Start Camera** click, and **Stop Camera** tears the
  stream down.
- A dependency-free, browser-side detection loop: raw `getUserMedia` +
  `<video>` + a downscaled (96×72) canvas frame-difference diff run under
  `requestAnimationFrame`.
- A derived, normalized `MotionCommand` surfaced in a live readout, plus a debug
  "motion field" heatmap canvas.
- No MediaPipe, no package/dependency change, and no graph interaction.

## 3. What Phase 32C verified / changed

**Verified (runtime QA — see §6/§7):**

- Camera is off by default; starts only on explicit user action; stops cleanly;
  restart works after both a normal stop and an error.
- `track.stop()` runs on Stop, on error, and on unmount — the device track
  reaches `readyState: "ended"` (no lingering camera light).
- Permission-denied, no-device, and in-use error paths surface plain-language
  messages and leave the panel in a recoverable state.
- The frame-difference sign conventions match the documented contract
  (validated numerically — see §8).

**Changed (contract hardening, all inside the sandbox):**

- Extended the local `MotionCommand` with three explicit metadata fields:
  `active` (idle/active bit), `source` (`"frame-difference"`), and `timestamp`
  (frame time). Existing field names (`yawDelta`, `pitchDelta`, `zoomDelta`,
  `pinchActive`, `confidence`) are preserved.
- **Aligned the pitch sign to the contract.** The Phase 32B code emitted
  `pitchDelta = (cy - 0.5) * 2`, which — because image `y` grows downward — made
  *upward* hand motion report as a *negative* pitch. Phase 32C inverts it to
  `(0.5 - cy) * 2` so upward motion is positive, matching "positive = up". This
  is a sandbox-local correctness fix, not graph wiring.
- Readability: an Idle/Active state chip, per-axis direction hints
  (`← left` / `right →`, `down` / `up`, `out` / `in`), and a `source` readout
  row. Styles are scoped under `.motion-sandbox-*` only.

## 4. MotionCommand contract

The `MotionCommand` is the single object a future graph controller will consume.
Its shape is fixed here so a later phase can lift it straight into a controller
without a translation layer.

```ts
// Phase 32D extends the union with the hand-landmark estimator.
type MotionSource = "frame-difference" | "mediapipe-hand-landmarker";

type MotionCommand = {
  yawDelta: number;      // -1..1 horizontal rotation intent
  pitchDelta: number;    // -1..1 vertical rotation intent
  zoomDelta: number;     // -1..1 depth / zoom intent (0 in frame-difference)
  pinchActive: boolean;  // discrete "grab" gesture flag (false without a hand model)
  confidence: number;    // 0..1 strength of the detected motion signal
  active: boolean;       // idle/active bit: confidence >= MOTION_GATE
  source: MotionSource;  // which estimator produced this command
  timestamp: number;     // performance.now() of the source frame
};
```

Field notes:

- **Deltas are intent, not applied transforms.** They are normalized to `-1..1`
  and never mutate anything in Phase 32C.
- **`active`** tracks the *smoothed* confidence (the value shown in the readout),
  so the idle/active bit never disagrees with the displayed number. A consumer
  would gate on `active` before applying any delta.
- **`pinchActive`** is reserved. Frame-difference has no hand model, so it is
  always `false`; a landmark-based phase would drive it.
- **`zoomDelta`** is always `0` under frame-difference — the detector cannot infer
  depth (see §9). The field exists so the contract is stable across estimators.
- **`timestamp`** lets a consumer rate-limit or measure staleness of a command.

## 5. Expected yaw/pitch/zoom semantics

```text
yawDelta:
- Negative = rotate graph left
- Positive = rotate graph right
- Zero     = no horizontal rotation intent

pitchDelta:
- Negative = rotate graph downward / backward
- Positive = rotate graph upward / forward
- Zero     = no vertical rotation intent

zoomDelta:
- Negative = pull graph outward / zoom out
- Positive = push graph inward / zoom in
- Zero     = no zoom intent
```

**Mapping from the frame-difference detector to these semantics:**

- The preview and the sampling canvas are both mirrored (`scaleX(-1)`), so the
  motion centroid reads like a mirror. A centroid toward the mirrored-right of
  the frame (the user's right hand) → **positive** `yawDelta`. Mirrored-left →
  negative. This matches "positive = right".
- Image `y` grows downward, so the detector inverts it: motion concentrated near
  the **top** of the frame (hand moved up) → **positive** `pitchDelta`. Bottom →
  negative. This matches "positive = up".
- `zoomDelta` stays `0`: frame-difference gives a 2-D motion centroid with no
  reliable depth proxy.

## 6. Runtime QA checklist

All checks were run against the local Vite dev build (`npm run check:frontend`
passing) and driven through the browser preview runtime. Live per-frame motion
was validated numerically (§8) because the automated preview tab runs
backgrounded, which suspends `requestAnimationFrame` (see §7).

| # | Check | Result |
|---|-------|--------|
| 1 | Panel renders with camera **off** by default | PASS |
| 2 | Start button enabled, Stop disabled at rest | PASS |
| 3 | Readout shows `Idle`, `source: frame-difference`, direction hints `—` at rest | PASS |
| 4 | **Start Camera** → `Camera active`, preview live, Stop enabled | PASS |
| 5 | **Stop Camera** → `Camera stopped`, preview off, track `readyState: "ended"` | PASS |
| 6 | `track.stop()` invoked exactly once per stop (no leaked stream) | PASS |
| 7 | Restart after a normal stop works | PASS |
| 8 | Permission **denied** → `Camera error` + plain-language message, recoverable | PASS |
| 9 | **No device** (`NotFoundError`) → correct message | PASS |
| 10 | Restart after an error path clears the error and goes live | PASS |
| 11 | Unmount while active tears down the stream (`useEffect` cleanup) | PASS (code-verified) |
| 12 | Sign conventions (yaw right/left, pitch up/down) match the contract | PASS (numeric, §8) |

## 7. Browser / camera lifecycle notes

- **Explicit consent.** `getUserMedia` is only ever called from the Start
  handler. There is no mount-time or auto-start request.
- **Double-start guard.** Start is a no-op while `requesting`/`active`, so a
  double click cannot leak a second stream.
- **Teardown is idempotent** and shared by the Stop button, every error branch,
  and the unmount cleanup. It cancels the RAF loop, stops every track, clears
  `video.srcObject`, and resets the smoothing state.
- **Secure-context requirement.** `getUserMedia` requires a secure context —
  `https://` or `http://localhost`. The Vite dev server on `localhost` qualifies;
  a plain-HTTP LAN IP would not, and the browser would reject the request (the
  panel surfaces that as a camera error).
- **Backgrounded-tab behaviour.** `requestAnimationFrame` is suspended while the
  document is hidden (`document.visibilityState === "hidden"`). This is why the
  automated preview run showed an active stream but zero live motion — the RAF
  loop legitimately does not tick while backgrounded. In a foreground tab the
  loop runs every frame. This is desirable (no CPU burn when hidden), not a bug.

## 8. Numeric validation of the detector (sign conventions)

Because the automated preview tab is backgrounded (RAF suspended), the per-frame
motion pipeline was reproduced with the exact component constants
(`PROC_W/H`, `NOISE_FLOOR`, `CONFIDENCE_GAIN`, `MOTION_GATE`) against synthetic
frames with motion concentrated in a known region:

| Motion region (post-mirror) | Expected | `yawDelta` | `pitchDelta` | `confidence` |
|-----------------------------|----------|-----------|-------------|-------------|
| Right side (hand right)     | yaw +    | **+0.72** | ~0.01       | 0.76 |
| Left side (hand left)       | yaw −    | **−0.74** | ~0.01       | 0.76 |
| Top (hand up)               | pitch +  | ~−0.01    | **+0.74**   | 0.47 |
| Bottom (hand down)          | pitch −  | ~−0.01    | **−0.71**   | 0.47 |

All four match the documented semantics, confirming the mirrored-yaw and
inverted-pitch conventions and that confidence scales with motion area.

## 9. Frame-difference detection — strengths

- **Zero dependencies.** Pure `getUserMedia` + canvas + RAF; no model download,
  no package/lockfile change, no supply-chain surface.
- **Cheap.** Downscaled 96×72 diff runs comfortably in the RAF loop.
- **Good horizontal/vertical *presence* signal.** The intensity-weighted centroid
  gives a stable, correctly-signed yaw/pitch reading for deliberate lateral hand
  waves, and confidence tracks motion volume well.
- **Honest idle behaviour.** The noise floor + motion gate + EMA smoothing settle
  the command back to a clean idle when the frame is still — no origin jitter.
- **Great as a debug/visualiser.** The heatmap makes "what the browser thinks is
  moving" legible, which is exactly what a sandbox should do.

## 10. Frame-difference detection — limitations

- **No depth / no zoom.** A 2-D difference centroid cannot distinguish a hand
  moving closer from a hand getting brighter, so `zoomDelta` is unavoidably `0`.
  Push/pull zoom is not inferable from this technique.
- **No gesture / no pinch.** There is no hand model, so `pinchActive` can never
  be anything but `false` — no discrete "grab" affordance.
- **Position ≠ intent.** The centroid reports *where change is*, not *where a hand
  is* or *which way it moved*. A hand held still after moving produces no signal;
  fast full-frame lighting changes read as huge false motion.
- **Sensitive to background/lighting.** Anything that moves (a person walking
  behind, a flickering light, camera auto-exposure) contributes to the centroid.
  Low-light / low-contrast scenes both raise noise and weaken the true signal.
- **Not steering-grade.** Good enough to *visualise* a yaw/pitch tendency, but
  too noisy and too coupled to lighting to *drive* a graph camera directly
  without a real hand/pose model on top.

## 11. Recommendation for Phase 32D

**Add MediaPipe / hand-landmark detection, and keep frame-difference as a
dependency-free fallback / debug visualiser.**

Rationale:

- Frame-difference has proven it can produce a stable, correctly-signed
  `MotionCommand` for yaw/pitch presence, and it is valuable as a zero-dependency
  fallback and as the debug heatmap.
- But the two capabilities graph control actually needs — reliable **zoom
  (depth)** and a discrete **pinch/grab** — are structurally impossible with
  frame-difference. Those require landmark/pose data.
- Phase 32D should therefore be a **feasibility/implementation pass for MediaPipe
  hand landmarks**, populating the *same* `MotionCommand` shape (now hardened
  here) so the detector can be swapped behind the contract. `source` becomes the
  discriminator between estimators; `zoomDelta`/`pinchActive` become live.

Phase 32D remains responsible for any dependency decision. This phase adds **no**
package/dependency.

## 12. Graph-wiring boundary (explicit)

- **No graph control wiring was added in Phase 32C.** The sandbox does not read,
  mutate, rotate, zoom, pan, select, or lay out the knowledge graph.
- The `MotionCommand` is derived and displayed for inspection only.
- Connecting the contract to graph behaviour remains **future work**, gated
  behind a later phase — and deliberately kept out of 32C so the graph is not
  turned into a webcam-driven feedback loop before the detector is trustworthy.

---

# Phase 32D — MediaPipe / Hand Landmark Motion Detection

**Status:** Implemented. Frontend-only. Adds one pinned dependency
(`@mediapipe/tasks-vision`). **No graph control wiring.**

## 13. What Phase 32D adds

- A **MediaPipe Hand Landmarker** estimator running on the webcam stream, added
  as the *primary* detector and selectable via a **Detector** toggle in the
  panel. The Phase 32B/32C **frame-difference** estimator is preserved unchanged
  as a zero-dependency fallback / debug visualiser.
- A small, deterministic, side-effect-free landmark-math helper
  (`apps/frontend/src/handLandmarkMotion.ts`) that owns the shared
  `MotionCommand` contract and the geometry that turns 21 hand landmarks into a
  normalized command. The panel keeps camera lifecycle, the detection loop, and
  rendering; the helper keeps the math auditable in one place.
- A lightweight **landmark overlay** (a mirrored canvas skeleton over the
  preview) and a **Hand detection** readout block (MediaPipe status, hand
  detected, handedness, landmark count, score).
- The estimator populates the *same* `MotionCommand` shape hardened in 32C, so a
  future graph controller can consume either source without a translation layer.

## 14. Source values

`source` (the `MotionSource` union) is the discriminator between estimators:

- `"frame-difference"` — Phase 32B/32C 2-D motion-centroid estimator. No depth,
  no hand model → `zoomDelta` always `0`, `pinchActive` always `false`.
- `"mediapipe-hand-landmarker"` — Phase 32D hand-landmark estimator. Drives
  `zoomDelta` (approximate) and `pinchActive` (real) from hand geometry.

Existing readouts are unchanged; only the set of possible `source` values grew.

## 15. Landmark-derived command mapping

MediaPipe returns 21 normalized landmarks per hand (`x`,`y` in `0..1`, origin
top-left; `z` a relative depth). Detection runs on the **raw** (un-mirrored)
video; the derivation mirrors `x` (`mx = 1 − x`) so signs match the mirrored
preview and the 32C conventions. All math lives in `handLandmarkMotion.ts`:

| Field | Derivation | Convention |
|-------|-----------|------------|
| `yawDelta` | Palm-centre `mx`, re-centred: `(mx − 0.5) · 2`, clamped | user's right → **positive** |
| `pitchDelta` | Palm-centre `y`, inverted: `(0.5 − y) · 2`, clamped | hand-up → **positive** (matches 32C) |
| `zoomDelta` | `(palmSpan − NEUTRAL_PALM_SPAN) · ZOOM_GAIN`, clamped | hand closer/bigger → **positive** (zoom in) |
| `pinchActive` | `pinchRatio < PINCH_RATIO_THRESHOLD` | thumb-tip↔index-tip close → **true** |
| `confidence` | MediaPipe handedness score, clamped `0..1` | — |
| `active` | `confidence ≥ ACTIVE_CONFIDENCE` (0.5) | idle/active gate |

- **Palm centre** is the mean of the wrist + the four finger MCP joints
  (indices 0, 5, 9, 13, 17) — a subset that barely moves as fingers flex, so the
  centre stays stable during a pinch.
- **Palm span** is the wrist→middle-MCP distance (indices 0→9): rotation-stable,
  flexion-stable, and used both as the pinch denominator and the depth proxy.
- Continuous fields (`yaw`/`pitch`/`zoom`/`confidence`) are EMA-smoothed in the
  panel; the discrete `pinchActive` is passed through un-smoothed so the "grab"
  flag stays crisp instead of smearing across the threshold.

## 16. Threshold rationale

- **`PINCH_RATIO_THRESHOLD = 0.4`.** Pinch fires when the thumb-tip↔index-tip gap
  is below 0.4 × the reference palm length. Normalizing by palm length makes the
  threshold **distance-invariant** — a pinch reads the same whether the hand is
  near or far. A deliberate thumb/index touch drives the ratio well under 0.4,
  while a relaxed open hand sits comfortably above (typically > 0.8), giving a
  clean margin against false triggers.
- **`NEUTRAL_PALM_SPAN = 0.22`, `ZOOM_GAIN = 4`.** These map the apparent palm
  size to a zoom intent around a neutral arm's-length pose. They are **coarse and
  uncalibrated** (see §17) — a first-pass proxy, not metric depth.
- **`ACTIVE_CONFIDENCE = 0.5`.** A hand must clear a 0.5 handedness score to mark
  the command `active`; below it the readout stays idle even if landmarks came
  back.

## 17. Push/pull zoom limitation (single-camera depth)

`zoomDelta` under the landmark estimator is an **approximation**. A single webcam
has no true depth; the estimator infers "closer/farther" from the *apparent size*
of the palm (wrist→middle-MCP span) relative to a fixed neutral. This is:

- **Uncalibrated** — the neutral span assumes a typical hand at arm's length; a
  larger or smaller hand, or a different seating distance, shifts the zero point.
- **Orientation-sensitive** — tilting the palm away from the camera foreshortens
  the span and reads as "farther" even without moving.
- **Good enough to *visualise* a push/pull tendency**, not to drive a metric
  zoom. A future phase could calibrate against a captured neutral pose or use the
  landmark `z` channel; Phase 32D deliberately keeps it simple and documented.

## 18. Privacy model (unchanged, restated for 32D)

- **Local-only.** All detection — frame-difference and MediaPipe — runs in the
  browser. The MediaPipe wasm runtime and model execute client-side.
- **Explicit camera start.** `getUserMedia` is only ever called from the Start
  handler; nothing starts on mount.
- **No recording, no storage.** No video, frames, or landmarks are persisted;
  landmarks are derived per-frame and discarded.
- **No backend transmission.** Nothing from the camera or the detector leaves the
  browser. There is no network call carrying camera-derived data.
- **Model/runtime fetch.** The one network fetch is the MediaPipe wasm runtime
  (version-pinned CDN) and the hand-landmarker model (versioned Google model
  path) — code/weights *in*, no user data *out*. The wasm (~a few hundred KB) and
  model (~7 MB) are intentionally not committed to the repo, so they are fetched
  from a pinned URL rather than bundled. The CDN/model URLs are pinned to the
  installed `@mediapipe/tasks-vision` version and a versioned model path.

## 19. Performance & lifecycle guardrails (32D)

- **Single detector instance.** The Hand Landmarker is created once (cached in a
  ref) and reused across Start/Stop; it is `close()`d on unmount. Dynamic
  `import()` keeps the wasm glue out of the initial bundle until MediaPipe mode is
  used (it builds as a separate `vision_bundle` chunk).
- **GPU→CPU fallback.** Detector creation tries the GPU delegate, then falls back
  to CPU, so the sandbox still runs without WebGL2.
- **Frame guards.** Detection is skipped until `video.readyState ≥ 2`, skipped on
  an unchanged `video.currentTime` (stalled/throttled frames), and always called
  with a strictly-increasing millisecond timestamp (`detectForVideo` requires it).
- **Clean teardown.** Stop / error / unmount cancel the RAF loop, stop every
  track, clear `srcObject`, reset smoothing, and clear the overlay canvas.
- **No post-unmount state.** A `mounted` ref gates every state update after the
  async model load, and start aborts if the stream was replaced mid-load.
- **Error handling.** Permission denial, no-device, in-use, missing
  `getUserMedia`, missing WebAssembly (unsupported), and model/wasm load failure
  all surface plain-language messages; a MediaPipe load failure is non-fatal (the
  loop reports idle and suggests the frame-difference fallback).

## 20. Known limitations (32D)

- **Lighting/background sensitivity.** Landmark detection degrades in low light,
  heavy backlight, or busy backgrounds.
- **Webcam angle sensitivity.** Steep camera angles and palm tilt distort the
  derived yaw/pitch/zoom.
- **Single-camera depth approximation.** `zoomDelta` is an uncalibrated apparent-
  size proxy (see §17), not true depth.
- **Possible main-thread blocking.** `detectForVideo` runs synchronously on the
  main thread; heavy frames can cost frame time. Mitigated by single-hand
  detection, stalled-frame skipping, and the readState guard, but not moved to a
  worker in this phase.
- **Single hand.** The detector is configured for `numHands: 1` (MVP).
- **No graph wiring yet.** The `MotionCommand` is derived and displayed only;
  nothing steers the graph. Graph wiring is Phase 32E.
