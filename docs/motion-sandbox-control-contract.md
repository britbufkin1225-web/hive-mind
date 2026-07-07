# Motion Sandbox Control Contract + Phase 32C QA

**Phase:** Phase 32C — Motion Sandbox QA + Control Contract Hardening
**Scope:** Frontend-only. No backend, API, schema, package, dependency, or
persistence change. **No graph control wiring.** No MediaPipe. No hand-landmark
dependency.
**Surface:** `apps/frontend/src/components/MotionSandboxPanel.tsx` (the isolated
"Motion" dock pane), plus scoped readability styles in
`apps/frontend/src/styles.css`.

This document is the durable home for the local `MotionCommand` contract and the
Phase 32C runtime-QA record. It complements the [roadmap](roadmap.md) and the
[README](../README.md) phase table.

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
type MotionSource = "frame-difference"; // union: extend for future estimators

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
