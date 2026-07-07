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
