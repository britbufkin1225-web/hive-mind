/* Phase 36J — Gesture-control foundation.

   A small, typed gesture layer on top of the full-hand feature set in
   handSpatialTracking.ts. It deliberately separates two ideas:

     1. a RAW POSE OBSERVATION (`classifyHandPose`) — a per-frame, stateless
        reading of what the hand looks like right now, and
     2. a CONFIRMED GESTURE (`advanceGestureResolver`) — a pose that has held
        long enough to be an intentional signal, with held-duration and a
        0..1 stability value.

   Phase 36J implements only the smallest set that proves the architecture:
   open palm, closed fist, pointing (index only), and pinch — pinch is passed
   in as the already-debounced hold from the existing pinch gate so this layer
   can never disagree with the preserved pinch pipeline. These are exposed as
   derived states (Motion Sandbox readout); none of them is wired to a new
   graph action in this phase. Later phases add kinds (grab, release, swipe,
   recenter pose) by extending `HandPoseKind` and `classifyHandPose` — the
   resolver is kind-agnostic.

   Pure and deterministic throughout: no clock reads (explicit `now`), no
   mutation, centralized thresholds. */

import type { FingerStates } from "./handSpatialTracking.ts";

/** The pose vocabulary this phase recognizes. "unknown" is the honest default
    for anything ambiguous — the resolver never confirms it. */
export type HandPoseKind =
  | "open-palm"
  | "fist"
  | "pointing"
  | "pinch"
  | "unknown";

/** Resolver output state for the current candidate:
      none       no hand / nothing recognizable
      possible   a pose is being observed but hasn't held long enough
      confirmed  the pose persisted past GESTURE_CONFIRM_MS — treat as intent */
export type GestureCandidateState = "none" | "possible" | "confirmed";

export type GestureCandidate = {
  kind: HandPoseKind;
  state: GestureCandidateState;
  /** How long the current kind has been continuously observed. */
  heldMs: number;
  /** heldMs / GESTURE_CONFIRM_MS clamped to 0..1 — a display-friendly
      "how close to confirmed" value. Stays 1 while confirmed. */
  stability: number;
};

// --- Thresholds (centralized for live-camera tuning) -------------------------

/** A pose must persist this long to be confirmed as intentional. */
export const GESTURE_CONFIRM_MS = 250;

/** A DIFFERENT raw pose must persist this long before it replaces the current
    candidate — brief single-frame misclassifications don't reset the timer. */
export const GESTURE_SWITCH_MS = 120;

/** Minimum smoothed openness for an open palm (finger states must also all
    read extended; this guards borderline half-open hands). */
export const OPEN_PALM_MIN_OPENNESS = 0.65;

/** Maximum smoothed openness for a fist ("closed or mostly closed"). */
export const FIST_MAX_OPENNESS = 0.35;

/** Classify one frame's (debounced) finger states + smoothed openness into a
    raw pose observation. `pinchHeld` is the existing pinch gate's debounced
    hold and takes priority — the preserved pinch pipeline stays the single
    source of truth for pinching.

    Priority order matters: a pinch usually also reads as "mostly closed", and
    pointing is a special case of "not open", so the more specific pose wins. */
export function classifyHandPose(
  fingers: FingerStates,
  openness: number,
  pinchHeld: boolean,
): HandPoseKind {
  if (pinchHeld) return "pinch";

  const { thumb, index, middle, ring, little } = fingers;
  if (
    thumb === "unknown" ||
    index === "unknown" ||
    middle === "unknown" ||
    ring === "unknown" ||
    little === "unknown"
  ) {
    return "unknown";
  }

  const restCurled =
    middle === "curled" && ring === "curled" && little === "curled";
  if (index === "extended" && restCurled) return "pointing";

  if (index === "curled" && restCurled && thumb !== "extended" && openness <= FIST_MAX_OPENNESS) {
    return "fist";
  }

  const allExtended =
    index === "extended" &&
    middle === "extended" &&
    ring === "extended" &&
    little === "extended";
  if (allExtended && thumb !== "curled" && openness >= OPEN_PALM_MIN_OPENNESS) {
    return "open-palm";
  }

  return "unknown";
}

// --- Temporal resolver ---------------------------------------------------------

export type GestureResolverState = {
  /** The current candidate kind (may be "unknown"). */
  kind: HandPoseKind;
  /** When the current kind started being observed. */
  sinceTimestamp: number;
  /** A differing raw kind waiting out GESTURE_SWITCH_MS, or null. */
  pendingKind: HandPoseKind | null;
  pendingSince: number;
};

export function createGestureResolverState(): GestureResolverState {
  return { kind: "unknown", sinceTimestamp: 0, pendingKind: null, pendingSince: 0 };
}

/** Advance the resolver one frame with the raw pose observation. Returns the
    next state plus the display-ready candidate. Pure — never mutates.

    Behavior: the current kind keeps accumulating held time while the raw
    observation matches it. A pose observed while nothing is held ("unknown")
    is adopted immediately — there is no candidate to protect. Between two
    real candidates (including pose → unknown), the differing observation must
    persist GESTURE_SWITCH_MS before it replaces the current one, so a
    single-frame misclassification can't drop or swap a held pose; the
    replacement's held clock starts from when it first appeared, so genuinely
    held poses aren't taxed by the debounce. "unknown" is reported as state
    "none" and never confirms. */
export function advanceGestureResolver(
  state: GestureResolverState,
  rawKind: HandPoseKind,
  now: number,
): { state: GestureResolverState; candidate: GestureCandidate } {
  let next: GestureResolverState;
  if (rawKind === state.kind) {
    next =
      state.pendingKind === null
        ? state
        : { ...state, pendingKind: null, pendingSince: 0 };
  } else if (state.kind === "unknown") {
    next = { kind: rawKind, sinceTimestamp: now, pendingKind: null, pendingSince: 0 };
  } else if (state.pendingKind === rawKind) {
    if (now - state.pendingSince >= GESTURE_SWITCH_MS) {
      next = {
        kind: rawKind,
        sinceTimestamp: state.pendingSince,
        pendingKind: null,
        pendingSince: 0,
      };
    } else {
      next = state;
    }
  } else {
    next = { ...state, pendingKind: rawKind, pendingSince: now };
  }

  const heldMs = Math.max(0, now - next.sinceTimestamp);
  const isPose = next.kind !== "unknown";
  const confirmed = isPose && heldMs >= GESTURE_CONFIRM_MS;
  const candidate: GestureCandidate = {
    kind: next.kind,
    state: !isPose ? "none" : confirmed ? "confirmed" : "possible",
    heldMs,
    stability: isPose ? Math.min(1, heldMs / GESTURE_CONFIRM_MS) : 0,
  };
  return { state: next, candidate };
}
