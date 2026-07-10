/* Phase 36J — Full-hand spatial tracking foundation.

   This module derives a stable, typed hand-pose feature set from the complete
   21-landmark MediaPipe hand result, replacing the sparse wrist/thumb/index
   triangle as the basis for motion interpretation. It owns:

     1. the full landmark index map (all 21 named indices),
     2. per-frame feature extraction (`extractHandSpatialFeatures`) — palm
        coordinate frame, orientation, per-finger state, openness, scale, pinch,
     3. temporal stabilization (`advanceHandTracker`) — EMA smoothing with
        wrap-aware angles, bounded deltas, finger-state debounce, and
        reset-on-loss.

   Everything is pure and deterministic: no clock reads (time comes in as an
   explicit argument), no I/O, no mutation of inputs, and — critically — no
   `NaN`/`Infinity` on any output path. Degenerate geometry (overlapping
   landmarks, zero-length axes, non-finite inputs) collapses to an explicit
   `valid: false` feature set instead of unstable numbers.

   Coordinate conventions: landmarks are MediaPipe normalized image coords —
   x/y in 0..1 with the origin top-left (y grows DOWNWARD), z a relative depth
   in roughly the same scale as x with more-negative = closer to the camera.
   Extraction can mirror x (`mirrorX`) so features live in the same "control
   space" as the mirrored preview: +x = the user's right. MediaPipe supplies
   exactly one wrist landmark and no forearm — all additional spatial
   understanding here is derived from palm geometry, never invented joints. */

/** Minimal 3D point/vector. Structurally identical to the `Landmark` shape in
    handLandmarkMotion.ts (x/y normalized image coords, z relative depth), so
    the two modules interoperate without importing each other's types. */
export type Vec3 = { x: number; y: number; z: number };

/** Complete MediaPipe Hand Landmarker index map — all 21 landmarks, named.
    Single source of truth; `handLandmarkMotion.ts` re-exports this as `LM`. */
export const HAND_LANDMARKS = {
  WRIST: 0,
  THUMB_CMC: 1,
  THUMB_MCP: 2,
  THUMB_IP: 3,
  THUMB_TIP: 4,
  INDEX_MCP: 5,
  INDEX_PIP: 6,
  INDEX_DIP: 7,
  INDEX_TIP: 8,
  MIDDLE_MCP: 9,
  MIDDLE_PIP: 10,
  MIDDLE_DIP: 11,
  MIDDLE_TIP: 12,
  RING_MCP: 13,
  RING_PIP: 14,
  RING_DIP: 15,
  RING_TIP: 16,
  PINKY_MCP: 17,
  PINKY_PIP: 18,
  PINKY_DIP: 19,
  PINKY_TIP: 20,
} as const;

export const HAND_LANDMARK_COUNT = 21;

/** Deterministic per-finger state. `unknown` appears only on an invalid frame
    (missing/degenerate landmarks) — a valid frame always classifies. */
export type FingerState = "extended" | "curled" | "partial" | "unknown";

export type FingerName = "thumb" | "index" | "middle" | "ring" | "little";

export type FingerStates = Record<FingerName, FingerState>;

/** Continuous 0..1 per-finger extension (0 = fully curled, 1 = fully
    extended), the raw signal the discrete states threshold. */
export type FingerExtensions = Record<FingerName, number>;

/** Palm orientation estimate, radians. Estimated from the palm coordinate
    frame — single-camera, so these are stable *relative* signals for control
    mapping, not metrologically exact angles.

      rollRad   Rotation in the image plane. 0 = fingers pointing straight up;
                positive = fingertips leaning toward +x (the user's right in
                mirrored control space).
      pitchRad  Longitudinal tilt out of the image plane. Positive = fingers
                tipping toward the camera.
      yawRad    Lateral facing (rotation about the finger axis). Positive =
                index side of the palm turned toward the camera. Sign depends
                on which hand is shown (handedness is not consumed here). */
export type HandOrientation = {
  yawRad: number;
  pitchRad: number;
  rollRad: number;
};

/** The full derived hand-pose feature object — one per frame, pure.

    All positions/axes are in the (optionally mirrored) normalized landmark
    space. The palm coordinate frame is built from multiple palm landmarks
    (wrist + the four finger MCPs), not a single finger direction, so it stays
    usable while individual fingers bend. When `valid` is false every numeric
    field is a safe zero and every finger state is "unknown". */
export type HandSpatialFeatures = {
  /** False when landmarks are missing, non-finite, or geometrically
      degenerate. Consumers must gate on this before using any other field. */
  valid: boolean;
  /** Whether x was mirrored into control space during extraction. */
  mirrored: boolean;
  wrist: Vec3;
  /** Centroid of the palm anchor (wrist + 4 finger MCPs) — stable under
      finger flexion. */
  palmCenter: Vec3;
  /** Image-plane wrist→middle-MCP length (the legacy "palm span"). */
  palmHeight: number;
  /** Image-plane index-MCP→little-MCP knuckle width. */
  palmWidth: number;
  /** Normalized apparent hand size — max of palm height and aspect-compensated
      palm width, so it stays usable when one palm dimension foreshortens
      under pitch or yaw. Single-camera depth/zoom proxy. */
  handScale: number;
  /** Unit vector wrist → middle MCP (3D). */
  palmLongitudinalAxis: Vec3;
  /** Unit vector little-MCP → index-MCP (3D), orthogonalized against the
      longitudinal axis. */
  palmLateralAxis: Vec3;
  /** Unit palm-plane normal (longitudinal × lateral). Sign flips with
      handedness/facing; treat as an orientation signal, not "palm front". */
  palmNormal: Vec3;
  orientation: HandOrientation;
  fingers: FingerStates;
  fingerExtension: FingerExtensions;
  /** Mean of the five continuous finger extensions, 0 (fist) .. 1 (open). */
  openness: number;
  /** Thumb-tip↔index-tip image-plane gap / palm height. Same normalization as
      the legacy pinch ratio, so the 0.40 / 0.52 thresholds carry over. */
  pinchRatio: number;
  pinchMidpoint: Vec3;
};

const ZERO_VEC: Vec3 = { x: 0, y: 0, z: 0 };

const UNKNOWN_FINGERS: FingerStates = {
  thumb: "unknown",
  index: "unknown",
  middle: "unknown",
  ring: "unknown",
  little: "unknown",
};

const ZERO_EXTENSIONS: FingerExtensions = {
  thumb: 0,
  index: 0,
  middle: 0,
  ring: 0,
  little: 0,
};

/** The safe all-zero, all-unknown feature set returned for any invalid or
    degenerate frame. Frozen — never mutated, always a fresh reference-equal
    sentinel a consumer can compare against if useful. */
export const INVALID_HAND_FEATURES: HandSpatialFeatures = Object.freeze({
  valid: false,
  mirrored: false,
  wrist: ZERO_VEC,
  palmCenter: ZERO_VEC,
  palmHeight: 0,
  palmWidth: 0,
  handScale: 0,
  palmLongitudinalAxis: ZERO_VEC,
  palmLateralAxis: ZERO_VEC,
  palmNormal: ZERO_VEC,
  orientation: { yawRad: 0, pitchRad: 0, rollRad: 0 },
  fingers: UNKNOWN_FINGERS,
  fingerExtension: ZERO_EXTENSIONS,
  openness: 0,
  pinchRatio: 0,
  pinchMidpoint: ZERO_VEC,
});

// --- Extraction thresholds (centralized for live-camera tuning) --------------
//
// None of these have been validated against a live camera yet (Phase 36J is
// the foundation pass); they were chosen from MediaPipe landmark geometry and
// synthetic fixtures. Tune here, in one place, during the live pass.

/** Guard for degenerate geometry: any normalization denominator below this is
    treated as invalid rather than divided through. */
export const GEOMETRY_EPSILON = 1e-6;

/** A palm smaller than this (normalized units) is too degenerate to derive a
    stable frame from — overlapping landmarks, or a detection glitch. */
export const MIN_PALM_HEIGHT = 1e-3;

/** Typical palm height/width ratio; multiplies palm width so the two palm
    dimensions are comparable when taking the max for `handScale`. */
export const PALM_ASPECT_COMPENSATION = 1.25;

/** Finger counts as extended when its tip projects at least this fraction of
    the hand scale beyond its knuckle along the palm's longitudinal axis. */
export const FINGER_EXTENDED_MIN_RATIO = 0.6;

/** Finger counts as curled when its tip projects less than this fraction
    beyond its knuckle. Between the two bounds is "partial". */
export const FINGER_CURLED_MAX_RATIO = 0.3;

/** Thumb thresholds use a different metric — thumb-tip distance from the
    little-finger MCP, normalized by hand scale (a curled thumb lies across
    the palm, near the little-finger side). */
export const THUMB_EXTENDED_MIN_RATIO = 1.25;
export const THUMB_CURLED_MAX_RATIO = 0.85;

// --- Vector helpers (pure, allocation-light) ---------------------------------

function sub(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function dot(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

function length3(v: Vec3): number {
  return Math.hypot(v.x, v.y, v.z);
}

function distance2D(a: Vec3, b: Vec3): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/** Normalize, or return null when the vector is too short to trust. */
function normalizeOrNull(v: Vec3): Vec3 | null {
  const len = length3(v);
  if (!(len > GEOMETRY_EPSILON)) return null;
  return { x: v.x / len, y: v.y / len, z: v.z / len };
}

function isFiniteVec(v: Vec3): boolean {
  return Number.isFinite(v.x) && Number.isFinite(v.y) && Number.isFinite(v.z);
}

function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

/** Wrap an angle into [-PI, PI). */
export function wrapAngle(rad: number): number {
  if (!Number.isFinite(rad)) return 0;
  const twoPi = Math.PI * 2;
  let a = (rad + Math.PI) % twoPi;
  if (a < 0) a += twoPi;
  return a - Math.PI;
}

// --- Feature extraction -------------------------------------------------------

const PALM_ANCHOR_INDICES = [
  HAND_LANDMARKS.WRIST,
  HAND_LANDMARKS.INDEX_MCP,
  HAND_LANDMARKS.MIDDLE_MCP,
  HAND_LANDMARKS.RING_MCP,
  HAND_LANDMARKS.PINKY_MCP,
];

// Per-finger joint chains used for the extension metric (mcp + tip; the pip is
// listed for future curl refinement even though the current metric is
// projection-based).
const FINGER_CHAIN: Record<
  Exclude<FingerName, "thumb">,
  { mcp: number; pip: number; tip: number }
> = {
  index: {
    mcp: HAND_LANDMARKS.INDEX_MCP,
    pip: HAND_LANDMARKS.INDEX_PIP,
    tip: HAND_LANDMARKS.INDEX_TIP,
  },
  middle: {
    mcp: HAND_LANDMARKS.MIDDLE_MCP,
    pip: HAND_LANDMARKS.MIDDLE_PIP,
    tip: HAND_LANDMARKS.MIDDLE_TIP,
  },
  ring: {
    mcp: HAND_LANDMARKS.RING_MCP,
    pip: HAND_LANDMARKS.RING_PIP,
    tip: HAND_LANDMARKS.RING_TIP,
  },
  little: {
    mcp: HAND_LANDMARKS.PINKY_MCP,
    pip: HAND_LANDMARKS.PINKY_PIP,
    tip: HAND_LANDMARKS.PINKY_TIP,
  },
};

/** Map a raw metric into a continuous 0..1 extension using the curled/extended
    band, then classify. Shared so the continuous and discrete views can never
    disagree. */
function extensionFromRatio(
  ratio: number,
  curledMax: number,
  extendedMin: number,
): { extension: number; state: FingerState } {
  const extension = clamp((ratio - curledMax) / (extendedMin - curledMax), 0, 1);
  const state: FingerState =
    ratio >= extendedMin ? "extended" : ratio <= curledMax ? "curled" : "partial";
  return { extension, state };
}

/** Derive the full hand-pose feature set from one frame's 21 landmarks.

    `mirrorX` flips x (x → 1−x) before any geometry, putting every derived
    feature in the mirrored "control space" that matches the mirrored preview
    and the MotionCommand yaw convention (+x = user's right).

    Returns `INVALID_HAND_FEATURES` — never partial output, never NaN — when
    landmarks are missing, incomplete, non-finite, or geometrically degenerate
    (zero-length palm axes from overlapping landmarks). */
export function extractHandSpatialFeatures(
  landmarks: readonly Vec3[] | null | undefined,
  options?: { mirrorX?: boolean },
): HandSpatialFeatures {
  if (!landmarks || landmarks.length < HAND_LANDMARK_COUNT) {
    return INVALID_HAND_FEATURES;
  }
  const mirrorX = options?.mirrorX === true;

  // Sanitize + (optionally) mirror into control space in one pass.
  const pts: Vec3[] = new Array(HAND_LANDMARK_COUNT);
  for (let i = 0; i < HAND_LANDMARK_COUNT; i += 1) {
    const p = landmarks[i];
    if (!p || !isFiniteVec(p)) return INVALID_HAND_FEATURES;
    pts[i] = mirrorX ? { x: 1 - p.x, y: p.y, z: p.z } : { x: p.x, y: p.y, z: p.z };
  }

  const wrist = pts[HAND_LANDMARKS.WRIST];
  const indexMcp = pts[HAND_LANDMARKS.INDEX_MCP];
  const middleMcp = pts[HAND_LANDMARKS.MIDDLE_MCP];
  const pinkyMcp = pts[HAND_LANDMARKS.PINKY_MCP];
  const thumbTip = pts[HAND_LANDMARKS.THUMB_TIP];
  const indexTip = pts[HAND_LANDMARKS.INDEX_TIP];

  // Palm scale. Image-plane lengths on purpose: they are the same quantities
  // the legacy zoom/pinch tuning was calibrated against.
  const palmHeight = distance2D(wrist, middleMcp);
  const palmWidth = distance2D(indexMcp, pinkyMcp);
  if (palmHeight < MIN_PALM_HEIGHT) return INVALID_HAND_FEATURES;
  const handScale = Math.max(palmHeight, palmWidth * PALM_ASPECT_COMPENSATION);

  // Palm coordinate frame from multiple palm landmarks (not finger direction):
  // longitudinal = wrist → middle MCP; lateral = little MCP → index MCP,
  // Gram-Schmidt-orthogonalized against longitudinal; normal = their cross.
  const longitudinal = normalizeOrNull(sub(middleMcp, wrist));
  if (!longitudinal) return INVALID_HAND_FEATURES;
  const lateralRaw = sub(indexMcp, pinkyMcp);
  const lateralProj = dot(lateralRaw, longitudinal);
  const lateral = normalizeOrNull({
    x: lateralRaw.x - longitudinal.x * lateralProj,
    y: lateralRaw.y - longitudinal.y * lateralProj,
    z: lateralRaw.z - longitudinal.z * lateralProj,
  });
  if (!lateral) return INVALID_HAND_FEATURES;
  const normal = normalizeOrNull(cross(longitudinal, lateral));
  if (!normal) return INVALID_HAND_FEATURES;

  // Palm centroid over the anchor points (stable under finger flexion).
  let cx = 0;
  let cy = 0;
  let cz = 0;
  for (const idx of PALM_ANCHOR_INDICES) {
    cx += pts[idx].x;
    cy += pts[idx].y;
    cz += pts[idx].z;
  }
  const palmCenter: Vec3 = {
    x: cx / PALM_ANCHOR_INDICES.length,
    y: cy / PALM_ANCHOR_INDICES.length,
    z: cz / PALM_ANCHOR_INDICES.length,
  };

  // Orientation estimates from the frame axes (see HandOrientation docs).
  // Image y grows downward, so "fingers up" is longitudinal = (0, -1, 0).
  const rollRad = wrapAngle(Math.atan2(longitudinal.x, -longitudinal.y));
  const pitchRad = Math.atan2(
    -longitudinal.z,
    Math.max(Math.hypot(longitudinal.x, longitudinal.y), GEOMETRY_EPSILON),
  );
  const yawRad = Math.atan2(
    -lateral.z,
    Math.max(Math.hypot(lateral.x, lateral.y), GEOMETRY_EPSILON),
  );

  // Per-finger extension. For the four fingers: how far the tip projects
  // beyond its own knuckle ALONG THE PALM'S LONGITUDINAL AXIS, normalized by
  // hand scale. Projection onto the palm frame (not raw screen y) keeps the
  // classification stable under hand rotation. For the thumb: distance from
  // the little-finger MCP (a curled thumb folds across the palm toward it).
  const fingerExtension = { ...ZERO_EXTENSIONS };
  const fingers: FingerStates = { ...UNKNOWN_FINGERS };
  let opennessSum = 0;

  for (const name of ["index", "middle", "ring", "little"] as const) {
    const chain = FINGER_CHAIN[name];
    const tipReach = dot(sub(pts[chain.tip], wrist), longitudinal);
    const knuckleReach = dot(sub(pts[chain.mcp], wrist), longitudinal);
    const ratio = (tipReach - knuckleReach) / Math.max(handScale, GEOMETRY_EPSILON);
    const { extension, state } = extensionFromRatio(
      ratio,
      FINGER_CURLED_MAX_RATIO,
      FINGER_EXTENDED_MIN_RATIO,
    );
    fingerExtension[name] = extension;
    fingers[name] = state;
    opennessSum += extension;
  }

  const thumbSpread =
    Math.hypot(
      thumbTip.x - pinkyMcp.x,
      thumbTip.y - pinkyMcp.y,
      thumbTip.z - pinkyMcp.z,
    ) / Math.max(handScale, GEOMETRY_EPSILON);
  const thumb = extensionFromRatio(
    thumbSpread,
    THUMB_CURLED_MAX_RATIO,
    THUMB_EXTENDED_MIN_RATIO,
  );
  fingerExtension.thumb = thumb.extension;
  fingers.thumb = thumb.state;
  opennessSum += thumb.extension;

  const openness = clamp(opennessSum / 5, 0, 1);

  // Pinch — identical normalization to the legacy ratio (image-plane gap over
  // palm height) so the existing 0.40 engage / 0.52 release thresholds and the
  // temporal pinch gate carry over unchanged.
  const pinchRatio =
    distance2D(thumbTip, indexTip) / Math.max(palmHeight, GEOMETRY_EPSILON);
  const pinchMidpoint: Vec3 = {
    x: (thumbTip.x + indexTip.x) / 2,
    y: (thumbTip.y + indexTip.y) / 2,
    z: (thumbTip.z + indexTip.z) / 2,
  };

  return {
    valid: true,
    mirrored: mirrorX,
    wrist,
    palmCenter,
    palmHeight,
    palmWidth,
    handScale,
    palmLongitudinalAxis: longitudinal,
    palmLateralAxis: lateral,
    palmNormal: normal,
    orientation: { yawRad, pitchRad, rollRad },
    fingers,
    fingerExtension,
    openness,
    pinchRatio,
    pinchMidpoint,
  };
}

// --- Temporal stabilization ----------------------------------------------------
//
// Conservative, deterministic smoothing over the continuous pose signals so
// single-frame landmark noise, brief orientation sign flips, and finger-state
// chatter near thresholds don't reach consumers. Deliberately tunable and NOT
// syrupy: factors sit near the existing command SMOOTHING so the readouts trail
// a live hand closely. All state advances through a pure reducer that takes an
// explicit `now` — same architecture as the existing control/pinch gates.

/** EMA factor for the smoothed palm center (higher = snappier). */
export const PALM_CENTER_SMOOTHING = 0.4;

/** EMA factor for orientation angles (wrap-aware, bounded per frame). */
export const ORIENTATION_SMOOTHING = 0.35;

/** Max radians a smoothed angle may move in one frame — absorbs single-frame
    orientation spikes without hiding deliberate rotation. */
export const MAX_ORIENTATION_STEP_RAD = 0.35;

/** EMA factor for hand scale and openness. */
export const SCALE_SMOOTHING = 0.3;
export const OPENNESS_SMOOTHING = 0.35;

/** A raw finger state must persist this many consecutive frames before the
    debounced state adopts it — kills oscillation at classification borders. */
export const FINGER_STATE_CONFIRM_FRAMES = 3;

/** After this long without a valid frame the tracker resets completely, so a
    re-appearing hand snaps to live geometry instead of easing in from stale
    values (and control spikes from the blend are impossible). */
export const TRACKING_LOSS_RESET_MS = 250;

/** The temporally stabilized pose consumers read. `translation` is the
    smoothed palm center's per-frame delta (hand movement); `expansion` is the
    smoothed hand scale's per-frame delta (toward/away from the camera). */
export type TrackedHandPose = {
  /** False while the current frame had no valid features (the smoothed values
      then hold their last state briefly, pending the loss reset). */
  valid: boolean;
  palmCenter: Vec3;
  orientation: HandOrientation;
  handScale: number;
  openness: number;
  pinchRatio: number;
  translation: Vec3;
  expansion: number;
  fingers: FingerStates;
  /** Smoothed palm axes for display/debug (re-normalized each frame). */
  palmLongitudinalAxis: Vec3;
  palmLateralAxis: Vec3;
  palmNormal: Vec3;
};

type FingerPending = { candidate: FingerState; frames: number };

export type HandTrackerState = {
  pose: TrackedHandPose | null;
  lastValidTimestamp: number;
  pending: Record<FingerName, FingerPending>;
};

const NO_PENDING: Record<FingerName, FingerPending> = {
  thumb: { candidate: "unknown", frames: 0 },
  index: { candidate: "unknown", frames: 0 },
  middle: { candidate: "unknown", frames: 0 },
  ring: { candidate: "unknown", frames: 0 },
  little: { candidate: "unknown", frames: 0 },
};

export function createHandTrackerState(): HandTrackerState {
  return { pose: null, lastValidTimestamp: 0, pending: NO_PENDING };
}

function emaVec(prev: Vec3, target: Vec3, k: number): Vec3 {
  return {
    x: prev.x + (target.x - prev.x) * k,
    y: prev.y + (target.y - prev.y) * k,
    z: prev.z + (target.z - prev.z) * k,
  };
}

/** Wrap-aware, step-bounded angle EMA: the shortest angular difference is
    scaled by the factor, clamped to the max step, then re-wrapped — so a hand
    crossing the ±π roll seam can never produce a full-circle swing. */
function emaAngle(prev: number, target: number, k: number): number {
  const delta = clamp(
    wrapAngle(target - prev) * k,
    -MAX_ORIENTATION_STEP_RAD,
    MAX_ORIENTATION_STEP_RAD,
  );
  return wrapAngle(prev + delta);
}

/** Debounce one finger's state: adopt a differing raw state only after it has
    persisted FINGER_STATE_CONFIRM_FRAMES consecutive frames. */
function debounceFinger(
  current: FingerState,
  raw: FingerState,
  pending: FingerPending,
): { state: FingerState; pending: FingerPending } {
  if (raw === current) {
    return { state: current, pending: { candidate: current, frames: 0 } };
  }
  const frames = pending.candidate === raw ? pending.frames + 1 : 1;
  if (frames >= FINGER_STATE_CONFIRM_FRAMES) {
    return { state: raw, pending: { candidate: raw, frames: 0 } };
  }
  return { state: current, pending: { candidate: raw, frames } };
}

/** Build a fresh pose directly from one valid frame (snap, no blending). */
function snapPose(features: HandSpatialFeatures): TrackedHandPose {
  return {
    valid: true,
    palmCenter: features.palmCenter,
    orientation: { ...features.orientation },
    handScale: features.handScale,
    openness: features.openness,
    pinchRatio: features.pinchRatio,
    translation: ZERO_VEC,
    expansion: 0,
    fingers: { ...features.fingers },
    palmLongitudinalAxis: features.palmLongitudinalAxis,
    palmLateralAxis: features.palmLateralAxis,
    palmNormal: features.palmNormal,
  };
}

/** Advance the tracker one frame. Pure: returns a fresh state, never mutates.

    - Valid features after a gap (or first frame): snap to live geometry.
    - Valid features continuing a track: EMA-smooth continuous signals
      (wrap-aware for angles), debounce finger states, derive translation and
      expansion from the smoothed values.
    - Invalid/missing features: mark the pose invalid immediately (consumers
      must not act on it) and, once the loss outlasts TRACKING_LOSS_RESET_MS,
      reset completely so nothing stale can blend into a re-detection. */
export function advanceHandTracker(
  state: HandTrackerState,
  features: HandSpatialFeatures | null,
  now: number,
): HandTrackerState {
  if (!features || !features.valid) {
    if (
      state.pose === null ||
      now - state.lastValidTimestamp >= TRACKING_LOSS_RESET_MS
    ) {
      return createHandTrackerState();
    }
    return {
      ...state,
      pose: {
        ...state.pose,
        valid: false,
        translation: ZERO_VEC,
        expansion: 0,
      },
    };
  }

  const prev = state.pose;
  const stale = prev === null || now - state.lastValidTimestamp >= TRACKING_LOSS_RESET_MS;
  if (stale) {
    return {
      pose: snapPose(features),
      lastValidTimestamp: now,
      pending: NO_PENDING,
    };
  }

  const palmCenter = emaVec(prev.palmCenter, features.palmCenter, PALM_CENTER_SMOOTHING);
  const handScale =
    prev.handScale + (features.handScale - prev.handScale) * SCALE_SMOOTHING;
  const openness = clamp(
    prev.openness + (features.openness - prev.openness) * OPENNESS_SMOOTHING,
    0,
    1,
  );
  const pinchRatio =
    prev.pinchRatio + (features.pinchRatio - prev.pinchRatio) * OPENNESS_SMOOTHING;

  const orientation: HandOrientation = {
    yawRad: emaAngle(prev.orientation.yawRad, features.orientation.yawRad, ORIENTATION_SMOOTHING),
    pitchRad: emaAngle(prev.orientation.pitchRad, features.orientation.pitchRad, ORIENTATION_SMOOTHING),
    rollRad: emaAngle(prev.orientation.rollRad, features.orientation.rollRad, ORIENTATION_SMOOTHING),
  };

  // Smooth the axes then re-normalize; if a blend degenerates (opposed axes),
  // fall back to the frame's raw axis rather than emitting a zero vector.
  const longitudinal =
    normalizeOrNull(emaVec(prev.palmLongitudinalAxis, features.palmLongitudinalAxis, ORIENTATION_SMOOTHING)) ??
    features.palmLongitudinalAxis;
  const lateral =
    normalizeOrNull(emaVec(prev.palmLateralAxis, features.palmLateralAxis, ORIENTATION_SMOOTHING)) ??
    features.palmLateralAxis;
  const normal =
    normalizeOrNull(cross(longitudinal, lateral)) ?? features.palmNormal;

  const fingers: FingerStates = { ...prev.fingers };
  const pending: Record<FingerName, FingerPending> = { ...state.pending };
  for (const name of ["thumb", "index", "middle", "ring", "little"] as const) {
    const result = debounceFinger(prev.fingers[name], features.fingers[name], state.pending[name]);
    fingers[name] = result.state;
    pending[name] = result.pending;
  }

  return {
    pose: {
      valid: true,
      palmCenter,
      orientation,
      handScale,
      openness,
      pinchRatio,
      translation: sub(palmCenter, prev.palmCenter),
      expansion: handScale - prev.handScale,
      fingers,
      palmLongitudinalAxis: longitudinal,
      palmLateralAxis: lateral,
      palmNormal: normal,
    },
    lastValidTimestamp: now,
    pending,
  };
}
