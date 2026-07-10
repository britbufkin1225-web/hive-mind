/* Phase 36J — dependency-free self-test for the pure tracking/gesture math.

   The frontend has no unit-test framework and this phase may not add
   dependencies, so this file is a plain executable assertion script over the
   pure modules. Run it with Node's built-in TypeScript type stripping
   (Node >= 22.18, enabled by default on the repo's Node 24):

     node apps/frontend/src/handSpatialTracking.selftest.ts

   It exits 0 with a summary on success and throws (non-zero exit) on the
   first failure. The `.ts` import extensions are what let Node execute the
   chain directly; `allowImportingTsExtensions` keeps tsc happy.

   IMPORTANT HONESTY NOTE: every fixture below is SYNTHETIC. Passing this file
   proves the math is deterministic, classification fires where the constants
   say it should, and no input can produce NaN/Infinity. It is NOT live-camera
   evidence and says nothing about real-world gesture feel. */

import {
  advanceHandTracker,
  createHandTrackerState,
  extractHandSpatialFeatures,
  FINGER_STATE_CONFIRM_FRAMES,
  HAND_LANDMARK_COUNT,
  INVALID_HAND_FEATURES,
  TRACKING_LOSS_RESET_MS,
  wrapAngle,
  type HandSpatialFeatures,
  type Vec3,
} from "./handSpatialTracking.ts";
import {
  advanceGestureResolver,
  classifyHandPose,
  createGestureResolverState,
  GESTURE_CONFIRM_MS,
  GESTURE_SWITCH_MS,
} from "./gestureRecognition.ts";
import {
  deriveHandCommand,
  deriveHandCommandFromFeatures,
  PINCH_RATIO_THRESHOLD,
} from "./handLandmarkMotion.ts";

let passed = 0;

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`SELFTEST FAILED: ${message}`);
  }
  passed += 1;
}

function approx(a: number, b: number, eps: number, message: string): void {
  assert(Math.abs(a - b) <= eps, `${message} (got ${a}, expected ~${b})`);
}

/** Recursively assert every number in a value is finite. */
function assertAllFinite(value: unknown, path: string): void {
  if (typeof value === "number") {
    assert(Number.isFinite(value), `non-finite number at ${path}: ${value}`);
    return;
  }
  if (value === null || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    assertAllFinite(child, `${path}.${key}`);
  }
}

// --- Synthetic fixtures --------------------------------------------------------
// An upright right-ish hand, palm to camera, fingers up, in RAW (unmirrored)
// normalized image coordinates (y grows downward). z = 0 except where a test
// perturbs it. Indices follow the MediaPipe map.

function v(x: number, y: number, z = 0): Vec3 {
  return { x, y, z };
}

function openHand(): Vec3[] {
  return [
    v(0.5, 0.72), // 0 wrist
    v(0.455, 0.68), // 1 thumb cmc
    v(0.41, 0.64), // 2 thumb mcp
    v(0.355, 0.585), // 3 thumb ip
    v(0.3, 0.53), // 4 thumb tip
    v(0.42, 0.51), // 5 index mcp
    v(0.415, 0.43), // 6 index pip
    v(0.41, 0.37), // 7 index dip
    v(0.405, 0.3), // 8 index tip
    v(0.48, 0.5), // 9 middle mcp
    v(0.475, 0.41), // 10 middle pip
    v(0.47, 0.34), // 11 middle dip
    v(0.465, 0.26), // 12 middle tip
    v(0.54, 0.51), // 13 ring mcp
    v(0.545, 0.42), // 14 ring pip
    v(0.55, 0.36), // 15 ring dip
    v(0.555, 0.29), // 16 ring tip
    v(0.59, 0.52), // 17 pinky mcp
    v(0.6, 0.45), // 18 pinky pip
    v(0.605, 0.4), // 19 pinky dip
    v(0.61, 0.35), // 20 pinky tip
  ];
}

function fist(): Vec3[] {
  const h = openHand();
  h[2] = v(0.43, 0.62); // thumb mcp
  h[3] = v(0.47, 0.6); // thumb ip
  h[4] = v(0.52, 0.6); // thumb tip folded across the palm
  h[6] = v(0.43, 0.47); // index pip
  h[7] = v(0.435, 0.53); // index dip folded back
  h[8] = v(0.44, 0.58); // index tip near the palm
  h[10] = v(0.478, 0.46);
  h[11] = v(0.479, 0.54);
  h[12] = v(0.48, 0.6); // middle tip
  h[14] = v(0.542, 0.47);
  h[15] = v(0.544, 0.54);
  h[16] = v(0.545, 0.6); // ring tip
  h[18] = v(0.592, 0.48);
  h[19] = v(0.594, 0.55);
  h[20] = v(0.595, 0.6); // pinky tip
  return h;
}

function pointing(): Vec3[] {
  const h = fist();
  const open = openHand();
  h[6] = open[6];
  h[7] = open[7];
  h[8] = open[8]; // only the index chain extends
  return h;
}

function pinchHand(): Vec3[] {
  const h = openHand();
  h[4] = v(0.42, 0.4); // thumb tip and index tip touch
  h[8] = v(0.42, 0.4);
  h[3] = v(0.39, 0.47);
  h[7] = v(0.418, 0.44);
  return h;
}

/** Rotate a fixture about (0.5, 0.5) in the image plane by `rad`. */
function rotated(hand: Vec3[], rad: number): Vec3[] {
  const c = Math.cos(rad);
  const s = Math.sin(rad);
  return hand.map((p) => {
    const dx = p.x - 0.5;
    const dy = p.y - 0.5;
    return v(0.5 + dx * c - dy * s, 0.5 + dx * s + dy * c, p.z);
  });
}

/** Shrink a fixture toward (0.5, 0.5) by `factor`. */
function scaled(hand: Vec3[], factor: number): Vec3[] {
  return hand.map((p) =>
    v(0.5 + (p.x - 0.5) * factor, 0.5 + (p.y - 0.5) * factor, p.z * factor),
  );
}

function extract(hand: Vec3[]): HandSpatialFeatures {
  return extractHandSpatialFeatures(hand, { mirrorX: true });
}

// --- 1. Open hand ---------------------------------------------------------------
{
  const f = extract(openHand());
  assert(f.valid, "open hand extracts as valid");
  assertAllFinite(f, "openHand");
  for (const finger of ["thumb", "index", "middle", "ring", "little"] as const) {
    assert(f.fingers[finger] === "extended", `open hand: ${finger} extended (got ${f.fingers[finger]})`);
  }
  assert(f.openness > 0.9, `open hand openness high (got ${f.openness})`);
  assert(f.pinchRatio > PINCH_RATIO_THRESHOLD, "open hand does not read as pinch");
  approx(f.palmHeight, 0.2209, 0.005, "open hand palm height");
  assert(f.handScale >= f.palmHeight, "hand scale >= palm height");
  assert(
    classifyHandPose(f.fingers, f.openness, false) === "open-palm",
    "open hand classifies as open-palm",
  );
  // Axes are unit-length and mutually orthogonal.
  const lon = f.palmLongitudinalAxis;
  const lat = f.palmLateralAxis;
  const nrm = f.palmNormal;
  approx(Math.hypot(lon.x, lon.y, lon.z), 1, 1e-6, "longitudinal axis unit");
  approx(Math.hypot(lat.x, lat.y, lat.z), 1, 1e-6, "lateral axis unit");
  approx(Math.hypot(nrm.x, nrm.y, nrm.z), 1, 1e-6, "normal unit");
  approx(lon.x * lat.x + lon.y * lat.y + lon.z * lat.z, 0, 1e-6, "axes orthogonal");
  // Upright fingers → roll near 0, flat palm → pitch/yaw near 0.
  assert(Math.abs(f.orientation.rollRad) < 0.2, `upright roll near 0 (got ${f.orientation.rollRad})`);
  approx(f.orientation.pitchRad, 0, 1e-6, "flat hand pitch 0");
  approx(f.orientation.yawRad, 0, 1e-6, "flat hand yaw 0");
}

// --- 2. Fist ---------------------------------------------------------------------
{
  const f = extract(fist());
  assert(f.valid, "fist extracts as valid");
  assertAllFinite(f, "fist");
  for (const finger of ["thumb", "index", "middle", "ring", "little"] as const) {
    assert(f.fingers[finger] === "curled", `fist: ${finger} curled (got ${f.fingers[finger]})`);
  }
  assert(f.openness < 0.2, `fist openness low (got ${f.openness})`);
  assert(classifyHandPose(f.fingers, f.openness, false) === "fist", "fist classifies as fist");
}

// --- 3. Pointing -------------------------------------------------------------------
{
  const f = extract(pointing());
  assert(f.valid, "pointing extracts as valid");
  assert(f.fingers.index === "extended", "pointing: index extended");
  assert(f.fingers.middle === "curled" && f.fingers.ring === "curled" && f.fingers.little === "curled", "pointing: rest curled");
  assert(
    classifyHandPose(f.fingers, f.openness, false) === "pointing",
    "pointing classifies as pointing",
  );
}

// --- 4. Pinch engaged / released ---------------------------------------------------
{
  const engaged = extract(pinchHand());
  assert(engaged.valid, "pinch hand extracts as valid");
  assert(engaged.pinchRatio < PINCH_RATIO_THRESHOLD, `pinch ratio engages (got ${engaged.pinchRatio})`);
  const cmd = deriveHandCommandFromFeatures(engaged, 0.9, 123);
  assert(cmd.pinchActive, "pinch hand derives pinchActive=true");
  const released = extract(openHand());
  const cmd2 = deriveHandCommandFromFeatures(released, 0.9, 124);
  assert(!cmd2.pinchActive, "open hand derives pinchActive=false");
  // Pinch classification is driven by the debounced hold flag, and wins.
  assert(classifyHandPose(engaged.fingers, engaged.openness, true) === "pinch", "held pinch classifies as pinch");
}

// --- 5. Rotated hand ---------------------------------------------------------------
{
  const base = extract(openHand());
  for (const deg of [90, -90, 45, 180]) {
    const rad = (deg * Math.PI) / 180;
    const f = extract(rotated(openHand(), rad));
    assert(f.valid, `rotated ${deg}° extracts as valid`);
    assertAllFinite(f, `rotated${deg}`);
    for (const finger of ["thumb", "index", "middle", "ring", "little"] as const) {
      assert(
        f.fingers[finger] === "extended",
        `rotated ${deg}°: ${finger} still extended (finger states are rotation-invariant)`,
      );
    }
    // Roll tracks the image-plane rotation. Fixture is extracted MIRRORED, so
    // an image-plane rotation by +rad appears as -rad in control space.
    const rollDelta = wrapAngle(f.orientation.rollRad - base.orientation.rollRad);
    approx(Math.abs(rollDelta), Math.abs(rad) > Math.PI ? 2 * Math.PI - Math.abs(rad) : Math.abs(rad), 0.05, `rotated ${deg}° roll delta magnitude`);
  }
}

// --- 6. Mirrored input ----------------------------------------------------------------
{
  const raw = extractHandSpatialFeatures(openHand(), { mirrorX: false });
  const mir = extractHandSpatialFeatures(openHand(), { mirrorX: true });
  assert(raw.valid && mir.valid, "both mirror modes valid");
  approx(mir.palmCenter.x, 1 - raw.palmCenter.x, 1e-9, "mirroring flips palm-center x");
  approx(mir.palmCenter.y, raw.palmCenter.y, 1e-9, "mirroring preserves palm-center y");
  approx(mir.orientation.rollRad, -raw.orientation.rollRad, 1e-9, "mirroring negates roll");
  approx(mir.openness, raw.openness, 1e-9, "mirroring preserves openness");
  approx(mir.pinchRatio, raw.pinchRatio, 1e-9, "mirroring preserves pinch ratio");
  for (const finger of ["thumb", "index", "middle", "ring", "little"] as const) {
    assert(mir.fingers[finger] === raw.fingers[finger], `mirroring preserves ${finger} state`);
  }
}

// --- 7. Tiny hand scale -----------------------------------------------------------------
{
  const f = extract(scaled(openHand(), 0.05));
  assert(f.valid, "tiny hand still extracts (above the degeneracy floor)");
  assertAllFinite(f, "tinyHand");
  for (const finger of ["thumb", "index", "middle", "ring", "little"] as const) {
    assert(f.fingers[finger] === "extended", `tiny hand: ${finger} extended (scale-invariant)`);
  }
  assert(f.openness > 0.9, "tiny hand openness preserved");
}

// --- 8. Degenerate / missing / invalid landmarks ----------------------------------------
{
  const overlapping = Array.from({ length: HAND_LANDMARK_COUNT }, () => v(0.5, 0.5));
  const f1 = extract(overlapping);
  assert(!f1.valid, "fully overlapping landmarks are invalid");
  assertAllFinite(f1, "overlapping");

  assert(!extract([]).valid, "empty landmark list is invalid");
  assert(!extract(openHand().slice(0, 20)).valid, "20 landmarks are invalid");
  assert(!extractHandSpatialFeatures(null).valid, "null input is invalid");
  assert(!extractHandSpatialFeatures(undefined).valid, "undefined input is invalid");

  const withNaN = openHand();
  withNaN[9] = v(Number.NaN, 0.5);
  assert(!extract(withNaN).valid, "NaN landmark is invalid");
  const withInf = openHand();
  withInf[0] = v(0.5, Number.POSITIVE_INFINITY);
  assert(!extract(withInf).valid, "Infinity landmark is invalid");

  // A degenerate frame yields a safe idle command — no NaN reaches the contract.
  const cmd = deriveHandCommandFromFeatures(f1, 0.9, 55);
  assertAllFinite(cmd, "idleCommandFromInvalid");
  assert(!cmd.active && cmd.yawDelta === 0 && cmd.pitchDelta === 0 && cmd.zoomDelta === 0, "invalid features derive an inactive zero command");
  assert(INVALID_HAND_FEATURES.valid === false, "INVALID_HAND_FEATURES is invalid");
}

// --- 9. Legacy landmark → command path (mirrors internally) ------------------------------
{
  const cmd = deriveHandCommand(openHand(), 0.9, 42);
  assertAllFinite(cmd, "deriveHandCommand");
  assert(cmd.active, "confident hand is active");
  assert(cmd.source === "mediapipe-hand-landmarker", "source tag preserved");
  assert(cmd.timestamp === 42, "timestamp passes through");
  assert(Math.abs(cmd.yawDelta) <= 1 && Math.abs(cmd.pitchDelta) <= 1 && Math.abs(cmd.zoomDelta) <= 1, "deltas clamped to -1..1");
  // Fixture palm centroid x ≈ 0.506 raw → mirrored ≈ 0.494 → slightly negative yaw.
  assert(cmd.yawDelta < 0.05, "yaw sign matches mirrored convention");
}

// --- 10. Tracker: smoothing, loss invalidation, reset-on-loss ----------------------------
{
  let state = createHandTrackerState();
  const f0 = extract(openHand());
  state = advanceHandTracker(state, f0, 0);
  assert(state.pose !== null && state.pose.valid, "tracker snaps on first valid frame");
  approx(state.pose!.palmCenter.x, f0.palmCenter.x, 1e-9, "snap uses live geometry");
  approx(state.pose!.translation.x, 0, 1e-9, "no translation on snap");

  // Move the hand right by 0.02 (mirrored space): smoothed step = 0.02 * 0.4.
  const moved = openHand().map((p) => v(p.x - 0.02, p.y, p.z)); // raw left = mirrored right
  const f1 = extract(moved);
  state = advanceHandTracker(state, f1, 16);
  approx(state.pose!.translation.x, 0.02 * 0.4, 1e-6, "translation is the smoothed per-frame delta");
  assertAllFinite(state, "trackerAfterMove");

  // Brief loss: pose is invalidated immediately but retained.
  state = advanceHandTracker(state, null, 32);
  assert(state.pose !== null && !state.pose.valid, "brief loss invalidates the pose without resetting");

  // Sustained loss past the reset window: full reset.
  state = advanceHandTracker(state, null, 16 + TRACKING_LOSS_RESET_MS + 1);
  assert(state.pose === null, "sustained loss resets the tracker");

  // Re-detection after reset snaps to live geometry (no stale blend).
  state = advanceHandTracker(state, f0, 600);
  approx(state.pose!.palmCenter.x, f0.palmCenter.x, 1e-9, "post-reset re-detection snaps");

  // Invalid features behave like loss.
  state = advanceHandTracker(state, INVALID_HAND_FEATURES, 616);
  assert(state.pose !== null && !state.pose.valid, "invalid features invalidate the pose");
}

// --- 11. Tracker: finger-state debounce ----------------------------------------------------
{
  let state = createHandTrackerState();
  state = advanceHandTracker(state, extract(openHand()), 0);
  // A single fist frame must NOT flip the debounced states…
  state = advanceHandTracker(state, extract(fist()), 16);
  assert(state.pose!.fingers.index === "extended", "one differing frame does not flip a finger state");
  // …but persisting for the confirm window does.
  for (let i = 2; i <= FINGER_STATE_CONFIRM_FRAMES + 1; i += 1) {
    state = advanceHandTracker(state, extract(fist()), i * 16);
  }
  assert(state.pose!.fingers.index === "curled", "persistent state change is adopted");
}

// --- 12. Gesture resolver: confirm, blip tolerance, switch debounce ------------------------
{
  let rs = createGestureResolverState();
  let out = advanceGestureResolver(rs, "open-palm", 1000);
  rs = out.state;
  assert(out.candidate.kind === "open-palm" && out.candidate.state === "possible", "new pose starts as possible");

  out = advanceGestureResolver(rs, "open-palm", 1000 + GESTURE_CONFIRM_MS);
  rs = out.state;
  assert(out.candidate.state === "confirmed", "held pose confirms");
  approx(out.candidate.stability, 1, 1e-9, "confirmed stability is 1");

  // One-frame misread does not un-confirm or reset the held clock.
  out = advanceGestureResolver(rs, "unknown", 1000 + GESTURE_CONFIRM_MS + 16);
  rs = out.state;
  assert(out.candidate.kind === "open-palm" && out.candidate.state === "confirmed", "single-frame blip is absorbed");

  // A sustained different pose replaces the candidate after the switch window.
  out = advanceGestureResolver(rs, "fist", 2000);
  rs = out.state;
  assert(out.candidate.kind === "open-palm", "switch does not happen instantly");
  out = advanceGestureResolver(rs, "fist", 2000 + GESTURE_SWITCH_MS);
  rs = out.state;
  assert(out.candidate.kind === "fist", "sustained new pose takes over");
  assert(out.candidate.state === "possible", "new pose must re-confirm");
  out = advanceGestureResolver(rs, "fist", 2000 + GESTURE_CONFIRM_MS + 50);
  rs = out.state;
  assert(out.candidate.state === "confirmed", "new pose confirms after holding");

  // "unknown" never confirms.
  let rs2 = createGestureResolverState();
  const idle = advanceGestureResolver(rs2, "unknown", 5000 + GESTURE_CONFIRM_MS * 10);
  assert(idle.candidate.state === "none" && idle.candidate.stability === 0, "unknown reports none and never confirms");
}

// --- 13. Wrap helper ------------------------------------------------------------------------
{
  approx(wrapAngle(Math.PI * 3), -Math.PI, 1e-9, "wrapAngle wraps 3π to -π");
  approx(wrapAngle(-Math.PI * 3), -Math.PI, 1e-9, "wrapAngle wraps -3π to -π");
  assert(wrapAngle(Number.NaN) === 0, "wrapAngle sanitizes NaN to 0");
  assert(wrapAngle(Number.POSITIVE_INFINITY) === 0, "wrapAngle sanitizes Infinity to 0");
}

console.log(`handSpatialTracking selftest: all ${passed} assertions passed.`);
