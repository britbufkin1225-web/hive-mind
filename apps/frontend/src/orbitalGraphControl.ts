/* Phase 32F — Orbital graph control contract + helper stub.

   This module is the isolated, typed *bridge layer* between the Motion Sandbox's
   detector output (`MotionCommand`, owned by `handLandmarkMotion.ts`) and a future
   orbital graph-control system. It exists so a later phase (32G) can lift a small,
   stable, already-gated intent shape straight into the graph — instead of wiring
   raw camera/MediaPipe deltas into the renderer and growing gesture spaghetti.

   Phase 32F does NOT control the graph. It defines the contract shape, the
   normalization/deadzone/clamp behaviour, and the pure mapping helper. Nothing
   here touches React, the DOM, camera APIs, MediaPipe, graph rendering, or app
   state. Everything is deterministic and side-effect free: given the same input
   it always returns the same command, so the gating rules stay auditable and
   testable in one place — mirroring how `handLandmarkMotion.ts` isolates the
   landmark math.

   Rationale for a *separate* contract (see Phase 32E planning §4): `MotionCommand`
   describes what the camera saw; `OrbitalGraphControlCommand` describes what the
   graph should do after gating and conditioning. Keeping them apart stops the
   graph from ever depending on detector internals, and lets future input sources
   be added without rewriting graph controls. */

import type { MotionCommand } from "./handLandmarkMotion";

/** The input modality behind an orbital-graph command. Only motion exists today;
    modelled as a union so a future source (pose, gamepad, keyboard) can extend it
    without changing the command shape. */
export type OrbitalGraphControlSource = "motion";

/** What the graph is being asked to do this frame. `idle` means "no trusted,
    deadzone-surviving control" — the graph should hold still. */
export type OrbitalGraphControlIntent =
  | "idle"
  | "orbit"
  | "zoom"
  | "orbit-and-zoom";

/** Future graph-intent contract — the single object a later graph controller will
    consume. Deliberately separate from `MotionCommand` (detector output) and
    deliberately post-gating: every delta here is already deadzoned and clamped, so
    a consumer can apply it without re-deriving any safety logic.

      active       Whether this frame carries trusted, deadzone-surviving control.
                   Equivalent to `intent !== "idle"`; a consumer gates on it.
      source       Input modality that produced the command (only "motion" today).
      intent       Coarse orbit/zoom classification for UI + branch-free consumers.
      timestamp    Source-frame time carried through for staleness / rate-limiting.
      yawDelta     -1..1 orbit-horizontal intent (deadzoned + clamped). +right.
      pitchDelta   -1..1 orbit-vertical intent (deadzoned + clamped). +up.
      zoomDelta    -1..1 zoom intent (deadzoned + clamped). +in / -out.
      orbitActive  True when yaw or pitch survives the deadzone this frame.
      zoomActive   True when zoom survives the deadzone this frame.
      confidence   0..1 trust signal, carried through for display / extra gating.

    Note: this refines the Phase 32E §4 sketch. That sketch used
    `orbitYawDelta` / `orbitPitchDelta` / `isGestureEngaged` / `isMotionTrusted`;
    32F keeps the shorter `yawDelta` / `pitchDelta` axis names and encodes
    engagement/trust as explicit `active` + `orbitActive`/`zoomActive` flags plus a
    single `intent` discriminator, which reads more directly at the future call
    site. The idea — a separate, normalized, explicitly-gated graph-intent
    contract — is preserved. */
export type OrbitalGraphControlCommand = Readonly<{
  active: boolean;
  source: OrbitalGraphControlSource;
  intent: OrbitalGraphControlIntent;
  timestamp: number;
  yawDelta: number;
  pitchDelta: number;
  zoomDelta: number;
  orbitActive: boolean;
  zoomActive: boolean;
  confidence: number;
}>;

// --- Safety constants -------------------------------------------------------
//
// Deltas below the deadzone are treated as no-intent (kills idle-hand jitter);
// deltas are clamped to ±MAX_DELTA; a command below MIN_CONFIDENCE is dropped to
// idle rather than trusted. Values track the Phase 32E §6 planning defaults where
// that doc defined them.

/** Yaw/pitch/zoom magnitude at or below which motion is ignored. Phase 32H
    usability pass widened this from the Phase 32E §6 default of 0.08 to 0.10:
    live testing of the 32G wiring showed a lightly off-centre / trembling hand
    still leaked a small constant rate command, so the camera crept when the user
    believed they were holding still. A slightly larger dead zone trades a hair of
    low-end sensitivity for a much steadier "hands roughly centred = no drift"
    feel, which matters more for a read-only demo camera. */
export const ORBITAL_GRAPH_CONTROL_DEADZONE = 0.1;

/** Absolute clamp bound for every orbital delta; deltas live in `-1..1`. Phase
    32E did not define a max-delta, so this keeps the stub's normalized range. */
export const ORBITAL_GRAPH_CONTROL_MAX_DELTA = 1;

/** Minimum confidence a frame must clear to be trusted as control input; below it
    the mapping decays to idle. Set to the Phase 32E §6 minimum-confidence
    threshold (0.55) rather than the looser stub placeholder, per the phase
    instruction to prefer values Phase 32E already defined. */
export const ORBITAL_GRAPH_CONTROL_MIN_CONFIDENCE = 0.55;

/** Clamp a raw delta into the safe orbital range.

    - Non-finite input (`NaN`/`±Infinity`) → `0` (never leaks a bad number).
    - Magnitude inside the deadzone → `0` (idle-hand jitter is suppressed).
    - Otherwise clamped to `-MAX_DELTA..MAX_DELTA`, preserving sign. */
export function clampOrbitalDelta(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (Math.abs(value) < ORBITAL_GRAPH_CONTROL_DEADZONE) return 0;
  if (value > ORBITAL_GRAPH_CONTROL_MAX_DELTA) return ORBITAL_GRAPH_CONTROL_MAX_DELTA;
  if (value < -ORBITAL_GRAPH_CONTROL_MAX_DELTA) return -ORBITAL_GRAPH_CONTROL_MAX_DELTA;
  return value;
}

/** Sanitize a confidence reading into `0..1`; non-finite → `0`. */
function sanitizeConfidence(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/** A frame time that is always a finite number (defaults to `0`). Deterministic
    on purpose — the helper never reads a clock, so callers/tests stay stable. */
function sanitizeTimestamp(value: number | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/** A stable, all-idle orbital command. Used as the neutral result whenever there
    is no trusted, deadzone-surviving motion to apply.

    `timestamp` defaults to a deterministic `0`; a caller may pass a frame time so
    a downstream staleness check still sees when the idle was produced. This helper
    intentionally does NOT read `performance.now()` — determinism keeps it trivial
    to unit-test and free of environment fragility. */
export function createIdleOrbitalGraphControlCommand(
  timestamp?: number,
): OrbitalGraphControlCommand {
  return {
    active: false,
    source: "motion",
    intent: "idle",
    timestamp: sanitizeTimestamp(timestamp),
    yawDelta: 0,
    pitchDelta: 0,
    zoomDelta: 0,
    orbitActive: false,
    zoomActive: false,
    confidence: 0,
  };
}

/** Map a detector `MotionCommand` into an `OrbitalGraphControlCommand`.

    Pure and non-mutating: it reads the input, never writes it, and never reads or
    writes any graph state. The graph is NOT wired to this in Phase 32F.

    Gating (all fail *safe*, toward stillness):
    - Missing input (`null`/`undefined`) → idle.
    - Input not `active`, or confidence below `MIN_CONFIDENCE` → idle (carrying the
      input timestamp so staleness checks still have a frame time).
    - yaw/pitch/zoom are clamped + deadzoned via `clampOrbitalDelta`; if nothing
      survives the deadzone, the frame is idle even though it was trusted.
    - Otherwise the surviving, clamped deltas are emitted with the derived
      orbit/zoom flags and intent. */
export function mapMotionCommandToOrbitalGraphControlCommand(
  command: MotionCommand | null | undefined,
): OrbitalGraphControlCommand {
  if (!command) return createIdleOrbitalGraphControlCommand();

  const timestamp = sanitizeTimestamp(command.timestamp);
  const confidence = sanitizeConfidence(command.confidence);

  const trusted = command.active === true && confidence >= ORBITAL_GRAPH_CONTROL_MIN_CONFIDENCE;
  if (!trusted) return createIdleOrbitalGraphControlCommand(timestamp);

  const yawDelta = clampOrbitalDelta(command.yawDelta);
  const pitchDelta = clampOrbitalDelta(command.pitchDelta);
  const zoomDelta = clampOrbitalDelta(command.zoomDelta);

  // clampOrbitalDelta already zeroes anything inside the deadzone, so "survives
  // the deadzone" is exactly "non-zero after clamping".
  const orbitActive = yawDelta !== 0 || pitchDelta !== 0;
  const zoomActive = zoomDelta !== 0;

  // Trusted, but every axis was inside the deadzone: hold still.
  if (!orbitActive && !zoomActive) {
    return createIdleOrbitalGraphControlCommand(timestamp);
  }

  const intent: OrbitalGraphControlIntent =
    orbitActive && zoomActive
      ? "orbit-and-zoom"
      : orbitActive
        ? "orbit"
        : "zoom";

  return {
    active: true,
    source: "motion",
    intent,
    timestamp,
    yawDelta,
    pitchDelta,
    zoomDelta,
    orbitActive,
    zoomActive,
    confidence,
  };
}

// --- Phase 32G — orbital camera integration ---------------------------------
//
// The first opt-in graph wiring (Phase 32G) needs to turn the per-frame
// orbital-control *intent* above into an accumulated *camera pose* the graph can
// render as a pure visual transform. That integration is deterministic and
// side-effect free, so it lives here beside the contract it consumes rather than
// inside the React graph component — keeping the gains, bounds, and idle-decay
// behaviour testable and auditable in one place. Nothing here touches React, the
// DOM, or graph data; it maps (previous pose, control command) → next pose.

/** An accumulated, neutral-relative orbital camera pose. The graph applies this
    as a presentation-only transform (yaw → horizontal orbit, pitch → vertical
    tilt, zoom → scale). It never describes or mutates graph data.

      yaw    Degrees of horizontal orbit. 0 = face-on; signed.
      pitch  Degrees of vertical tilt. 0 = level; signed.
      zoom   Scale multiplier. 1 = neutral; >1 closer, <1 further. */
export type OrbitalGraphCameraTransform = Readonly<{
  yaw: number;
  pitch: number;
  zoom: number;
}>;

/** The rest pose: face-on, level, unscaled. The camera decays back to this
    whenever there is no trusted, active control. */
export const ORBITAL_GRAPH_CAMERA_NEUTRAL: OrbitalGraphCameraTransform = {
  yaw: 0,
  pitch: 0,
  zoom: 1,
};

// Per-frame integration gains: how much one active frame's clamped delta nudges
// the pose. Phase 32H trimmed these from the 32G values (yaw 0.9 / pitch 0.7 /
// zoom 0.012) after the first live pass read as twitchy — a small hand move
// swung the view faster than the eye could track, so the graph felt jumpy rather
// than steered. The lower gains keep a held axis orbiting/zooming at a calmer,
// more legible rate while still reaching the bounds below within a second or two.
// Pitch stays below yaw (vertical tilt is more disorienting than a horizontal
// orbit) and zoom stays deliberately gentle so depth changes never lurch.
export const ORBITAL_GRAPH_CAMERA_YAW_GAIN = 0.62;
export const ORBITAL_GRAPH_CAMERA_PITCH_GAIN = 0.48;
export const ORBITAL_GRAPH_CAMERA_ZOOM_GAIN = 0.009;

// Absolute pose bounds. The orbit stays a gentle presentation tilt (never a
// full spin), and zoom is clamped so the graph can never be scaled off-screen or
// inverted. Every integrated axis is clamped to these each frame.
export const ORBITAL_GRAPH_CAMERA_MAX_YAW = 32;
export const ORBITAL_GRAPH_CAMERA_MAX_PITCH = 24;
export const ORBITAL_GRAPH_CAMERA_MIN_ZOOM = 0.65;
export const ORBITAL_GRAPH_CAMERA_MAX_ZOOM = 1.7;

/** Retained fraction of the pose per idle frame. On any inactive/low-confidence
    frame the pose eases toward neutral by `1 - DECAY`, so the graph settles to
    stillness (and rights itself) when motion stops — the safe fallback. */
export const ORBITAL_GRAPH_CAMERA_DECAY = 0.88;

/** How old (ms) an *active* command may be before it is no longer trusted to
    drive the camera. Phase 32H safety guard: the graph camera loop reads the
    latest command from a ref every frame, but the Motion Sandbox only refreshes
    that ref while its own detection loop runs. If that loop ever stalls mid-motion
    (tab throttling, a wedged decode, the sandbox being torn down without pushing a
    final idle), a frozen *active* command would otherwise be re-integrated every
    frame and drift the camera to its clamp on its own. Treating a command older
    than this as idle makes the camera decay to neutral instead of running away —
    and stops a stale active frame from causing a jump when control is toggled back
    on. ~4 dropped frames at 60fps; normal operation refreshes every ~16–33ms. */
export const ORBITAL_GRAPH_CAMERA_STALE_MS = 250;

/** Snap a value that is within `epsilon` of `target` to `target`, so an easing
    pose settles exactly at rest instead of asymptotically hovering near it. */
function settle(value: number, target: number, epsilon: number): number {
  return Math.abs(value - target) <= epsilon ? target : value;
}

function clampRange(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

/** Integrate one orbital-control command into the running camera pose.

    Pure and deterministic: `(previous pose, command, now?) → next pose`. It reads
    nothing but its arguments and touches no graph data — the graph stays
    read-only; only its visual camera moves.

    - Inactive/low-confidence command → ease every axis toward
      `ORBITAL_GRAPH_CAMERA_NEUTRAL` by `1 - DECAY` (decay safely to stillness).
    - Active but *stale* command (see below) → treated exactly like inactive, so a
      frozen input decays to neutral rather than driving a runaway orbit.
    - Active, fresh command → add each clamped delta (scaled by `confidence`, so a
      less certain frame nudges more gently) and clamp the result to the bounds.

    `now` (optional, ms on the same `performance.now()` clock as
    `command.timestamp`) enables the staleness guard: when supplied and the command
    is older than `ORBITAL_GRAPH_CAMERA_STALE_MS`, the command is not trusted for
    integration. Omitting `now` preserves the original deterministic behaviour
    (staleness never triggers), keeping existing callers/tests stable.

    Non-finite fields in `prev` fail safe: they are treated as neutral via the
    clamps, so a corrupted pose can never leak into the transform. */
// --- Phase 36F — spatial pointer parallax + pose composition -----------------
//
// The Spatial Hive projection (spatialHiveProjection.ts) re-projects every node,
// edge, and particle per frame from a single camera pose. Two small, pure
// additions let that pose be steered by the cursor as well as by the opt-in
// motion camera, without either input source knowing about the other:
//
//   pointer parallax  A bounded yaw/pitch offset derived from where the cursor
//                     sits over the graph surface. Always-available, gentle
//                     (well inside the motion camera's own bounds), and eased
//                     so the structure feels suspended, not glued to the mouse.
//   pose composition  motion pose + pointer offset → one projection pose, with
//                     the summed angles clamped so the two sources can never
//                     stack past a safe orbit.
//
// Both are deterministic (same inputs → same outputs) and live here beside the
// camera integrator so every pose rule stays auditable in one module.

/** A pointer-driven yaw/pitch offset. Deliberately not a full camera pose:
    the cursor only tilts the orbit — zoom stays owned by the motion camera. */
export type SpatialPointerPose = Readonly<{
  yaw: number;
  pitch: number;
}>;

/** Rest offset: cursor centred or absent contributes no tilt. */
export const SPATIAL_POINTER_NEUTRAL: SpatialPointerPose = { yaw: 0, pitch: 0 };

/** Max cursor-driven orbit. Phase 36F revision: raised from the first pass's
    timid ±9°/±6.5° — the cursor is the manipulation input most users actually
    have, and at the old bounds the parallax read as a shimmer rather than a
    floating object being orbited. Still inside the motion camera's own range
    (±32°/±24°), which remains the authoritative deep-orbit input. */
export const SPATIAL_POINTER_MAX_YAW = 16;
export const SPATIAL_POINTER_MAX_PITCH = 11;

/** Per-frame easing toward the pointer target — the same "glide, don't snap"
    feel as the camera decay, tuned slightly quicker so parallax feels live. */
export const SPATIAL_POINTER_EASE = 0.14;

/** Map a cursor position over the graph surface (normalized to [-1, 1] from
    the surface centre) to its parallax target. Non-finite input reads as
    centred; inputs are clamped so an out-of-bounds pointer can't over-tilt.
    Signs: cursor right → positive yaw (the structure's right side swings
    toward the viewer); cursor up → positive pitch (top tips toward viewer) —
    the field gently faces the cursor, which is what sells "floating object". */
export function pointerParallaxTarget(nx: number, ny: number): SpatialPointerPose {
  const x = Number.isFinite(nx) ? clampRange(nx, -1, 1) : 0;
  const y = Number.isFinite(ny) ? clampRange(ny, -1, 1) : 0;
  return {
    yaw: x * SPATIAL_POINTER_MAX_YAW,
    pitch: -y * SPATIAL_POINTER_MAX_PITCH,
  };
}

/** Ease the current pointer offset toward its target by `ease` per frame,
    snapping once within epsilon so the loop can settle to exact rest (and the
    caller's "pose unchanged → stop work" check can fire). Pure. */
export function easePointerPose(
  current: SpatialPointerPose,
  target: SpatialPointerPose,
  ease: number = SPATIAL_POINTER_EASE,
): SpatialPointerPose {
  const a = clampRange(ease, 0, 1);
  return {
    yaw: settle(current.yaw + (target.yaw - current.yaw) * a, target.yaw, 0.005),
    pitch: settle(
      current.pitch + (target.pitch - current.pitch) * a,
      target.pitch,
      0.005,
    ),
  };
}

// --- Drag-to-orbit ------------------------------------------------------------
//
// Direct manipulation: press and drag on the graph surface to spin the spatial
// structure, exactly like orbiting a floating object. The drag pose *persists*
// (no decay) so the user can set a vantage and keep it; Recenter (or a
// double-click on empty space) clears it. Bounds are wide — this is the input
// that lets someone actually look around the structure — but still short of a
// flip-over, so labels never invert.

/** Max drag-accumulated orbit. */
export const SPATIAL_DRAG_MAX_YAW = 42;
export const SPATIAL_DRAG_MAX_PITCH = 26;

/** Orbit gain per full surface-width / surface-height of drag travel (deg). */
export const SPATIAL_DRAG_YAW_GAIN = 140;
export const SPATIAL_DRAG_PITCH_GAIN = 90;

/** Movement (px) below which a press-and-release still counts as a click on
    whatever it started on; beyond it the gesture is a drag and the trailing
    click is suppressed so orbiting never accidentally selects. */
export const SPATIAL_DRAG_CLICK_THRESHOLD_PX = 4;

/** Accumulate one drag movement (normalized to the surface size: dxNorm = px
    moved / surface width) into the persistent drag pose. Drag right swings the
    structure's right side toward the viewer (same sign convention as pointer
    parallax); drag up tips the top toward the viewer. Pure and clamped. */
export function applyDragDelta(
  drag: SpatialPointerPose,
  dxNorm: number,
  dyNorm: number,
): SpatialPointerPose {
  const dx = Number.isFinite(dxNorm) ? dxNorm : 0;
  const dy = Number.isFinite(dyNorm) ? dyNorm : 0;
  return {
    yaw: clampRange(
      drag.yaw + dx * SPATIAL_DRAG_YAW_GAIN,
      -SPATIAL_DRAG_MAX_YAW,
      SPATIAL_DRAG_MAX_YAW,
    ),
    pitch: clampRange(
      drag.pitch - dy * SPATIAL_DRAG_PITCH_GAIN,
      -SPATIAL_DRAG_MAX_PITCH,
      SPATIAL_DRAG_MAX_PITCH,
    ),
  };
}

// --- Ambient sway ---------------------------------------------------------------
//
// The floating-object tell: the spatial structure is never frozen. A slow,
// bounded, deterministic sway (two incommensurate sine periods, so the path
// never visibly loops) keeps a whisper of parallax alive at rest — depth is
// visible before the user touches anything. Purely time-based (like a CSS
// keyframe: no randomness, no state), gentle enough to sit far below the
// selection/motion emphasis, and dropped entirely under reduced motion.

export const SPATIAL_SWAY_MAX_YAW = 10;
export const SPATIAL_SWAY_MAX_PITCH = 5;
export const SPATIAL_SWAY_YAW_PERIOD_S = 26;
export const SPATIAL_SWAY_PITCH_PERIOD_S = 19;

/** The ambient sway offset at a moment in time. Pure: same t, same pose. */
export function ambientSwayPose(timeSec: number): SpatialPointerPose {
  const t = Number.isFinite(timeSec) ? timeSec : 0;
  return {
    yaw:
      SPATIAL_SWAY_MAX_YAW *
      Math.sin((t / SPATIAL_SWAY_YAW_PERIOD_S) * Math.PI * 2),
    pitch:
      SPATIAL_SWAY_MAX_PITCH *
      Math.sin((t / SPATIAL_SWAY_PITCH_PERIOD_S) * Math.PI * 2 + 1.7),
  };
}

/** Total-orbit clamp for the composed pose: motion + drag + parallax + sway
    may stack, so the sum is bounded well short of a flip-over — the structure
    can be examined from a steep angle but labels never invert. */
export const SPATIAL_TOTAL_MAX_YAW = 58;
export const SPATIAL_TOTAL_MAX_PITCH = 36;

/** Compose every steering input — the opt-in motion camera, the persistent
    drag orbit, the cursor parallax, and the ambient sway — into the single
    pose the spatial projection renders from. Additive on yaw/pitch with the
    total clamp above; zoom stays owned by the motion camera's own bounds.
    Pure. */
export function composeSpatialCameraPose(
  camera: OrbitalGraphCameraTransform,
  pointer: SpatialPointerPose,
  drag: SpatialPointerPose = SPATIAL_POINTER_NEUTRAL,
  sway: SpatialPointerPose = SPATIAL_POINTER_NEUTRAL,
): OrbitalGraphCameraTransform {
  return {
    yaw: clampRange(
      camera.yaw + pointer.yaw + drag.yaw + sway.yaw,
      -SPATIAL_TOTAL_MAX_YAW,
      SPATIAL_TOTAL_MAX_YAW,
    ),
    pitch: clampRange(
      camera.pitch + pointer.pitch + drag.pitch + sway.pitch,
      -SPATIAL_TOTAL_MAX_PITCH,
      SPATIAL_TOTAL_MAX_PITCH,
    ),
    zoom: clampRange(
      camera.zoom,
      ORBITAL_GRAPH_CAMERA_MIN_ZOOM,
      ORBITAL_GRAPH_CAMERA_MAX_ZOOM,
    ),
  };
}

/** True when two poses are visually indistinguishable — the projection loop's
    "nothing moved, skip the DOM writes / go to sleep" check. */
export function spatialPosesAlmostEqual(
  a: OrbitalGraphCameraTransform,
  b: OrbitalGraphCameraTransform,
): boolean {
  return (
    Math.abs(a.yaw - b.yaw) < 0.002 &&
    Math.abs(a.pitch - b.pitch) < 0.002 &&
    Math.abs(a.zoom - b.zoom) < 0.0005
  );
}

export function integrateOrbitalCamera(
  prev: OrbitalGraphCameraTransform,
  command: OrbitalGraphControlCommand,
  now?: number,
): OrbitalGraphCameraTransform {
  const yawNow = Number.isFinite(prev.yaw) ? prev.yaw : 0;
  const pitchNow = Number.isFinite(prev.pitch) ? prev.pitch : 0;
  const zoomNow = Number.isFinite(prev.zoom) ? prev.zoom : 1;

  // A command is stale when we were given a clock, the command carries a finite
  // source timestamp, and that timestamp is older than the trust window. Stale
  // input falls through to the same decay path as an inactive command.
  const stale =
    typeof now === "number" &&
    Number.isFinite(now) &&
    Number.isFinite(command.timestamp) &&
    now - command.timestamp > ORBITAL_GRAPH_CAMERA_STALE_MS;

  if (!command.active || stale) {
    // Ease toward neutral; snap once close enough so the loop can rest.
    return {
      yaw: settle(yawNow * ORBITAL_GRAPH_CAMERA_DECAY, 0, 0.01),
      pitch: settle(pitchNow * ORBITAL_GRAPH_CAMERA_DECAY, 0, 0.01),
      zoom: settle(1 + (zoomNow - 1) * ORBITAL_GRAPH_CAMERA_DECAY, 1, 0.001),
    };
  }

  const gain = command.confidence; // already 0..1, gates ensure >= MIN_CONFIDENCE

  return {
    yaw: clampRange(
      yawNow + command.yawDelta * ORBITAL_GRAPH_CAMERA_YAW_GAIN * gain,
      -ORBITAL_GRAPH_CAMERA_MAX_YAW,
      ORBITAL_GRAPH_CAMERA_MAX_YAW,
    ),
    pitch: clampRange(
      pitchNow + command.pitchDelta * ORBITAL_GRAPH_CAMERA_PITCH_GAIN * gain,
      -ORBITAL_GRAPH_CAMERA_MAX_PITCH,
      ORBITAL_GRAPH_CAMERA_MAX_PITCH,
    ),
    zoom: clampRange(
      zoomNow + command.zoomDelta * ORBITAL_GRAPH_CAMERA_ZOOM_GAIN * gain,
      ORBITAL_GRAPH_CAMERA_MIN_ZOOM,
      ORBITAL_GRAPH_CAMERA_MAX_ZOOM,
    ),
  };
}
