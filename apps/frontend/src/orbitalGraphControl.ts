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

/** Yaw/pitch/zoom magnitude at or below which motion is ignored. Matches the
    Phase 32E §6 yaw/pitch deadzone default. */
export const ORBITAL_GRAPH_CONTROL_DEADZONE = 0.08;

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
