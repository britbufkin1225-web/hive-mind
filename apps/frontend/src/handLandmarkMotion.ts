/* Phase 32D — MediaPipe hand-landmark motion derivation.

   This module is the small, typed home for (1) the shared MotionCommand
   contract and (2) the deterministic math that turns a set of MediaPipe hand
   landmarks into a normalized MotionCommand. It exists so MotionSandboxPanel
   does not grow into a "blob monster with a camera": the panel owns camera
   lifecycle, the detector loop, and rendering; this file owns the pure geometry.

   Everything here is deterministic and side-effect free. No AI/LLM, no training,
   no persistence, no I/O — given the same landmarks it always returns the same
   command. That makes the sign conventions and thresholds auditable in one place
   and keeps them identical to the frame-difference contract hardened in 32C. */

/** The detection backend that produced a command. Phase 32B/32C shipped only the
    dependency-free frame-difference estimator; Phase 32D adds a MediaPipe
    hand-landmark estimator. Modelled as a union so a consumer can branch on the
    source without the two paths diverging on shape. */
export type MotionSource = "frame-difference" | "mediapipe-hand-landmarker";

/** Phase 32C/32D motion-control contract — the single object a future graph
    controller will consume. Every field is *intent*, normalized, and never
    mutates a graph in this phase.

      yawDelta    -1..1 horizontal rotation intent. Negative → left, positive →
                  right, zero → none.
      pitchDelta  -1..1 vertical rotation intent. Negative → down/back, positive
                  → up/forward (hand-up is positive — matches 32C), zero → none.
      zoomDelta   -1..1 depth/zoom intent. Negative → pull out / zoom out,
                  positive → push in / zoom in, zero → none. Approximate under
                  the landmark estimator (single-camera scale proxy); always 0
                  under frame-difference.
      pinchActive Discrete "grab" flag. Frame-difference has no hand model → always
                  false. Landmark estimator drives it from thumb/index distance.
      confidence  0..1 strength of the detected signal (motion volume for
                  frame-difference; handedness score for the landmark estimator).
      active      Idle/active bit: true once confidence clears the gate. A
                  consumer would gate on this before applying any delta.
      source      Which estimator produced this command.
      timestamp   performance.now() of the source frame, for staleness checks. */
export type MotionCommand = {
  yawDelta: number;
  pitchDelta: number;
  zoomDelta: number;
  pinchActive: boolean;
  confidence: number;
  active: boolean;
  source: MotionSource;
  timestamp: number;
};

/** Neutral, all-zero command. `source` is a placeholder the caller overrides;
    both estimators reset to this shape when idle. */
export const ZERO_MOTION: MotionCommand = {
  yawDelta: 0,
  pitchDelta: 0,
  zoomDelta: 0,
  pinchActive: false,
  confidence: 0,
  active: false,
  source: "frame-difference",
  timestamp: 0,
};

/** Minimal normalized-landmark shape. MediaPipe returns `NormalizedLandmark`
    objects with more fields; we depend only on x/y (0..1, origin top-left) and
    the relative depth z, so the derivation stays decoupled from the package's
    exact types and remains trivially testable. */
export type Landmark = { x: number; y: number; z: number };

// MediaPipe Hand Landmarker index map (21 landmarks per hand). Only the subset
// the derivation uses is named here.
export const LM = {
  WRIST: 0,
  THUMB_TIP: 4,
  INDEX_MCP: 5,
  INDEX_TIP: 8,
  MIDDLE_MCP: 9,
  RING_MCP: 13,
  PINKY_MCP: 17,
} as const;

// Palm anchor: the wrist plus the four finger metacarpophalangeal joints. This
// subset barely moves as fingers flex, so the palm centre stays stable even
// during a pinch — unlike using the finger tips.
const PALM_POINTS = [LM.WRIST, LM.INDEX_MCP, LM.MIDDLE_MCP, LM.RING_MCP, LM.PINKY_MCP];

// Bone pairs for the overlay skeleton (wrist→fingers + knuckle bridge). Kept
// minimal and anatomical — a debug aid, not an AR showpiece.
export const HAND_CONNECTIONS: ReadonlyArray<readonly [number, number]> = [
  // Thumb
  [0, 1], [1, 2], [2, 3], [3, 4],
  // Index
  [0, 5], [5, 6], [6, 7], [7, 8],
  // Middle
  [9, 10], [10, 11], [11, 12],
  // Ring
  [13, 14], [14, 15], [15, 16],
  // Pinky
  [0, 17], [17, 18], [18, 19], [19, 20],
  // Knuckle bridge across the palm
  [5, 9], [9, 13], [13, 17],
];

// --- Derivation thresholds (documented in motion-sandbox-control-contract.md) ---

// Reference palm length: wrist → middle-finger MCP. Used as a scale-invariant
// denominator for the pinch ratio and as the single-camera depth proxy for zoom.
// It barely changes with finger flexion or wrist rotation, so it is a stable
// stand-in for "how big the hand appears" — i.e. how close it is to the camera.

// Pinch fires when the thumb-tip↔index-tip gap is below this fraction of the
// reference palm length. Normalizing by palm length makes the threshold
// distance-invariant: a pinch reads the same whether the hand is near or far.
// 0.4 was chosen so a deliberate thumb/index touch trips it while a relaxed open
// hand (ratio typically > 0.8) does not.
export const PINCH_RATIO_THRESHOLD = 0.4;

// Neutral reference palm length (as a fraction of frame height) at a comfortable
// arm's-length distance. A larger measured span → hand is closer → zoom in
// (positive); smaller → farther → zoom out. This is a coarse, UNCALIBRATED proxy
// (see the contract's push/pull limitation), not a metric depth.
export const NEUTRAL_PALM_SPAN = 0.22;

// Maps (measuredSpan − neutral) into the -1..1 zoom intent before clamping.
export const ZOOM_GAIN = 4;

// A hand must clear this handedness score to count as "active"; below it the
// command reads idle even if landmarks were returned.
export const ACTIVE_CONFIDENCE = 0.5;

function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

function distance(a: Landmark, b: Landmark): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

/** Intensity-free centroid of the palm anchor points, in normalized image
    coords (0..1). */
export function palmCenter(landmarks: Landmark[]): { x: number; y: number } {
  let sx = 0;
  let sy = 0;
  for (const idx of PALM_POINTS) {
    sx += landmarks[idx].x;
    sy += landmarks[idx].y;
  }
  return { x: sx / PALM_POINTS.length, y: sy / PALM_POINTS.length };
}

/** Reference palm length (wrist → middle MCP) in normalized units. Guarded to a
    small floor so downstream ratios never divide by zero on a degenerate hand. */
export function palmSpan(landmarks: Landmark[]): number {
  return Math.max(distance(landmarks[LM.WRIST], landmarks[LM.MIDDLE_MCP]), 1e-4);
}

/** Thumb-tip↔index-tip distance as a fraction of palm length. Scale-invariant, so
    the pinch threshold holds regardless of how close the hand is. */
export function pinchRatio(landmarks: Landmark[]): number {
  return distance(landmarks[LM.THUMB_TIP], landmarks[LM.INDEX_TIP]) / palmSpan(landmarks);
}

/** Derive a normalized MotionCommand from a single hand's landmarks.

    `landmarks`      21 normalized landmarks for one hand.
    `handednessScore` MediaPipe's 0..1 classification score (used as confidence).
    `timestamp`      performance.now() of the source frame.

    The preview and overlay are mirrored (CSS scaleX(-1)); MediaPipe runs on the
    RAW video, so we mirror x here (mx = 1 − x) to keep "user's right → positive
    yaw" consistent with the frame-difference path and the 32C contract. This is a
    raw, unsmoothed target — the panel applies EMA smoothing to the continuous
    fields and leaves the discrete ones (pinchActive) alone. */
export function deriveHandCommand(
  landmarks: Landmark[],
  handednessScore: number,
  timestamp: number,
): MotionCommand {
  const palm = palmCenter(landmarks);
  // Mirror x to match the mirrored preview: user's right hand → positive yaw.
  const mirroredX = 1 - palm.x;
  const yawDelta = clamp((mirroredX - 0.5) * 2, -1, 1);
  // Image y grows downward; invert so hand-up (small y) is a positive pitch,
  // matching the 32C "positive = up" convention.
  const pitchDelta = clamp((0.5 - palm.y) * 2, -1, 1);

  // Single-camera depth proxy: bigger apparent palm → closer → zoom in.
  const span = palmSpan(landmarks);
  const zoomDelta = clamp((span - NEUTRAL_PALM_SPAN) * ZOOM_GAIN, -1, 1);

  const pinchActive = pinchRatio(landmarks) < PINCH_RATIO_THRESHOLD;

  const confidence = clamp(handednessScore, 0, 1);

  return {
    yawDelta,
    pitchDelta,
    zoomDelta,
    pinchActive,
    confidence,
    active: confidence >= ACTIVE_CONFIDENCE,
    source: "mediapipe-hand-landmarker",
    timestamp,
  };
}

/* Phase 32M — Gesture-recognition stability + control-zone feedback helpers.

   The pieces below stay in this module for the same reason the derivation does:
   they are pure, deterministic, and side-effect free, so the thresholds and the
   small temporal state machines that make the control feel intentional (instead
   of flickering on single-frame noise) are auditable and testable in one place.
   The panel owns the timing/rendering; this file owns the classification math and
   the transition rules. None of it reads a clock — every time-based helper takes
   an explicit `now`, so the same inputs always produce the same output. */

// --- Hand range (too close / in range / too far) ---------------------------

/** Where the detected hand sits relative to the usable control band, derived
    from its apparent size (see `handBoundingSpan`). Informational only — the
    caller decides whether to surface it; `no-hand` is the caller's concern. */
export type HandRange = "too-far" | "in-range" | "too-close";

// Range-band edges on the bounding-box span (max of the box's normalized width
// and height, 0..1). Below TOO_FAR the hand is a small speck the tracker resolves
// poorly; above TOO_CLOSE it overflows the frame and the palm-span / pinch ratio
// get noisy. Between them tracking is comfortable. These sit inside the phase's
// suggested band, tuned toward the conservative end so the hint stays a calm cue
// rather than a nag.
export const HAND_RANGE_TOO_FAR = 0.18;
export const HAND_RANGE_TOO_CLOSE = 0.6;

/** Largest normalized extent of the hand's bounding box (max of width and height
    across all landmarks). A single-camera scale proxy for distance: a small box →
    hand far away; a box approaching 1 → hand filling the frame. Returns 0 for an
    empty landmark set so the caller reads it as "no hand". */
export function handBoundingSpan(landmarks: Landmark[]): number {
  if (landmarks.length === 0) return 0;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of landmarks) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return Math.max(maxX - minX, maxY - minY);
}

/** Classify a bounding-box span into the usable-range band. Conservative edges
    keep the hint calm: only a clearly tiny or clearly frame-filling hand trips
    "too far" / "too close". */
export function classifyHandRange(span: number): HandRange {
  if (span < HAND_RANGE_TOO_FAR) return "too-far";
  if (span > HAND_RANGE_TOO_CLOSE) return "too-close";
  return "in-range";
}

// --- Confidence quality tier ------------------------------------------------

/** Coarse tracking-confidence tier for the readout. `no-hand` whenever there is
    no usable hand this frame; otherwise Strong/Okay/Weak by the thresholds
    below, so a viewer can judge tracking strength without reading the raw
    number. */
export type ConfidenceQuality = "strong" | "okay" | "weak" | "no-hand";

export const CONFIDENCE_STRONG = 0.75;
export const CONFIDENCE_OKAY = 0.55;

/** Map a 0..1 confidence to a quality tier. `hasHand=false` (or a non-positive
    confidence) is always `no-hand`, so an idle frame reads as "no hand" rather
    than a misleading "weak". */
export function classifyConfidence(
  confidence: number,
  hasHand: boolean,
): ConfidenceQuality {
  if (!hasHand || !(confidence > 0)) return "no-hand";
  if (confidence >= CONFIDENCE_STRONG) return "strong";
  if (confidence >= CONFIDENCE_OKAY) return "okay";
  return "weak";
}

// --- Active/idle hysteresis -------------------------------------------------
//
// Raw confidence crosses any single threshold many times a second on a hand held
// near it, so gating "active" directly on it strobes the readout (and the graph
// camera). This small deterministic gate adds hysteresis: it enters active only
// after confidence stays at/above ENTER for ENTER_HOLD_MS, and leaves only after
// it stays below EXIT for EXIT_HOLD_MS. The band between EXIT and ENTER is a
// sticky zone where the current state simply persists — no flicker. A vanished
// hand (`hasSignal=false`) always takes the exit path so control can never latch
// on nothing.

export const ACTIVE_ENTER_CONFIDENCE = 0.6;
export const ACTIVE_EXIT_CONFIDENCE = 0.42;
export const ACTIVE_ENTER_HOLD_MS = 120;
export const ACTIVE_EXIT_HOLD_MS = 180;

/** Coarse control phase for display: warming up toward active, actively
    controlling, briefly uncertain while confidence drops, or idle. */
export type ControlPhase = "idle" | "warming" | "active" | "uncertain";

/** Hysteresis accumulator. `active` is the debounced gate a consumer reads;
    `phase` is the display tier; `pendingSince` timestamps an in-progress enter
    (from idle) or exit (from active) transition, or is null when settled. */
export type ControlGate = {
  active: boolean;
  phase: ControlPhase;
  pendingSince: number | null;
};

export function createControlGate(): ControlGate {
  return { active: false, phase: "idle", pendingSince: null };
}

/** Advance the gate one frame. `confidence` is the (smoothed) 0..1 signal;
    `hasSignal` is false when there is no usable hand — which forces the exit
    path, since a hand that left the frame must not stay latched active. Returns a
    fresh gate; never mutates the input. */
export function advanceControlGate(
  gate: ControlGate,
  confidence: number,
  hasSignal: boolean,
  now: number,
): ControlGate {
  if (!gate.active) {
    // Idle → warming → active. Only a present hand at/above ENTER can arm/enter.
    if (hasSignal && confidence >= ACTIVE_ENTER_CONFIDENCE) {
      const since = gate.pendingSince ?? now;
      if (now - since >= ACTIVE_ENTER_HOLD_MS) {
        return { active: true, phase: "active", pendingSince: null };
      }
      return { active: false, phase: "warming", pendingSince: since };
    }
    // Below ENTER (or no hand): drop the arming timer, hold idle.
    return { active: false, phase: "idle", pendingSince: null };
  }

  // Active → uncertain → idle. A missing hand or confidence below EXIT starts the
  // exit timer; anything at/above EXIT with a hand present re-confirms active.
  const dropping = !hasSignal || confidence < ACTIVE_EXIT_CONFIDENCE;
  if (dropping) {
    const since = gate.pendingSince ?? now;
    if (now - since >= ACTIVE_EXIT_HOLD_MS) {
      return { active: false, phase: "idle", pendingSince: null };
    }
    return { active: true, phase: "uncertain", pendingSince: since };
  }
  return { active: true, phase: "active", pendingSince: null };
}

// --- Pinch hold debounce ----------------------------------------------------
//
// Raw pinch (thumb/index gap under PINCH_RATIO_THRESHOLD) flickers on single
// noisy frames. This gate promotes it to a stable "held" only after the raw pinch
// persists for PINCH_HOLD_MS, and releases only after it stays open for
// PINCH_RELEASE_GRACE_MS — so a one-frame dropout doesn't drop the hold, but a
// deliberate release still lands promptly. Same pure, `now`-driven shape as the
// control gate above.

export const PINCH_HOLD_MS = 180;
export const PINCH_RELEASE_GRACE_MS = 120;

/** Pinch display tier: actively held, raw-detected but not yet held long enough,
    or idle. */
export type PinchPhase = "idle" | "ready" | "holding";

export type PinchGate = {
  held: boolean;
  phase: PinchPhase;
  pendingSince: number | null;
};

export function createPinchGate(): PinchGate {
  return { held: false, phase: "idle", pendingSince: null };
}

/** Advance the pinch gate one frame from the raw per-frame pinch flag. Returns a
    fresh gate; never mutates the input. */
export function advancePinchGate(
  gate: PinchGate,
  rawPinch: boolean,
  now: number,
): PinchGate {
  if (!gate.held) {
    // Idle → ready → holding once the raw pinch persists past the hold window.
    if (rawPinch) {
      const since = gate.pendingSince ?? now;
      if (now - since >= PINCH_HOLD_MS) {
        return { held: true, phase: "holding", pendingSince: null };
      }
      return { held: false, phase: "ready", pendingSince: since };
    }
    return { held: false, phase: "idle", pendingSince: null };
  }
  // Held: a sustained open releases; a brief single-frame dropout is tolerated.
  if (!rawPinch) {
    const since = gate.pendingSince ?? now;
    if (now - since >= PINCH_RELEASE_GRACE_MS) {
      return { held: false, phase: "idle", pendingSince: null };
    }
    return { held: true, phase: "holding", pendingSince: since };
  }
  return { held: true, phase: "holding", pendingSince: null };
}
