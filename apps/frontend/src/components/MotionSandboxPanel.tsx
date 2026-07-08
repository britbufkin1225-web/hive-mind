import { useCallback, useEffect, useRef, useState } from "react";
import type {
  HandLandmarker as HandLandmarkerInstance,
  HandLandmarkerResult,
} from "@mediapipe/tasks-vision";
import {
  advanceControlGate,
  advancePinchGate,
  classifyConfidence,
  classifyHandRange,
  createControlGate,
  createPinchGate,
  deriveHandCommand,
  handBoundingSpan,
  HAND_CONNECTIONS,
  LM,
  palmCenter,
  ZERO_MOTION,
  type ConfidenceQuality,
  type ControlGate,
  type ControlPhase,
  type HandRange,
  type Landmark,
  type MotionCommand,
  type PinchGate,
  type PinchPhase,
} from "../handLandmarkMotion";

/* Phase 32D — Standalone Webcam Motion Sandbox (MediaPipe hand landmarks).

   This surface is still deliberately isolated: it NEVER touches the knowledge
   graph, never requests the camera on mount, never auto-starts the stream, and
   never stores or transmits video/frames/landmarks. It exists to derive a
   normalized MotionCommand from the webcam and surface it for inspection.

   Phase 32D adds a MediaPipe Hand Landmarker detector as the primary estimator
   and keeps the dependency-free frame-difference estimator from Phase 32B/32C as
   a fallback / debug visualiser. The two estimators fill the SAME MotionCommand
   contract (see ../handLandmarkMotion.ts); `source` is the discriminator. The
   landmark math and thresholds live in that helper so this file stays focused on
   camera lifecycle, the detection loop, and rendering. */

// Pinned to the installed @mediapipe/tasks-vision version. The wasm glue (~a few
// hundred KB) and the hand-landmarker model (~7 MB) are intentionally NOT
// committed to the repo, so they are fetched from a version-pinned CDN / the
// versioned Google model path rather than bundled. See the control contract doc.
const MP_VERSION = "0.10.35";
const MP_WASM_ROOT = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}/wasm`;
const HAND_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

/** Which estimator the sandbox runs. User-selectable; defaults to MediaPipe. */
type DetectorMode = "mediapipe-hand-landmarker" | "frame-difference";

/** Lifecycle of the camera, surfaced to the user as a status chip. */
type CameraStatus =
  | "inactive" // never started (or fully reset) — no permission asked yet
  | "requesting" // getUserMedia in flight, waiting on the permission prompt
  | "active" // stream live, detection loop running
  | "stopped" // user stopped a previously-active stream
  | "error"; // permission denied / no device / stream failure

/** Lifecycle of the MediaPipe detector, independent of the camera. */
type MediaPipeStatus =
  | "idle" // not loaded yet (frame-difference mode, or camera off)
  | "loading" // FilesetResolver + model download / detector creation in flight
  | "ready" // detector created; detection can run
  | "unsupported" // WebAssembly missing → MediaPipe cannot run in this browser
  | "error"; // wasm / model load or detector creation failed

/** Live hand-detection readout, updated (throttled) from the detection loop. */
type HandInfo = {
  handDetected: boolean;
  handedness: string | null;
  landmarkCount: number;
  score: number;
};

const NO_HAND: HandInfo = {
  handDetected: false,
  handedness: null,
  landmarkCount: 0,
  score: 0,
};

// Direction hints in the readout only render once a delta clears this small
// magnitude, so near-zero jitter reads as "—" instead of flickering left/right.
const DIRECTION_HINT_EPS = 0.05;

// Downscaled processing resolution for the frame-difference fallback. It is
// O(pixels) per frame, so we sample a tiny 4:3 buffer rather than the full
// preview — cheap enough for a 60fps loop while still resolving where motion is.
const PROC_W = 96;
const PROC_H = 72;

// A per-pixel grayscale delta below this (0..255) is treated as sensor noise and
// ignored, so a perfectly still frame reads as zero motion instead of shimmer.
const NOISE_FLOOR = 18;

// Maps the fraction-of-frame-in-motion into a 0..1 confidence. Clamped to 1.
const CONFIDENCE_GAIN = 8;

// Below this confidence the frame-difference directional deltas are forced to
// zero — otherwise a still frame's noise centroid would jitter yaw/pitch.
const MOTION_GATE = 0.06;

// Exponential-moving-average factor for the emitted command. Lower = smoother /
// laggier. Keeps the inspected values readable instead of strobing each frame.
const SMOOTHING = 0.28;

// React re-render throttle for the readout. The RAF loop runs every frame, but
// pushing 60 setState/sec is wasteful and unreadable; ~12Hz is plenty.
const READOUT_INTERVAL_MS = 80;

// Overlay canvas resolution (4:3, matches the preview box). Landmarks are
// normalized 0..1, so this only sets draw crispness, not alignment. Phase 36D
// doubled it (320×240 → 640×480) so the thin diagnostic skeleton lines stay
// crisp instead of smearing when the canvas is CSS-stretched over the preview.
const OVERLAY_W = 640;
const OVERLAY_H = 480;

// Video-source constraints, tried in order. A modest explicit resolution first
// (keeps the preview + downscaled sampling cheap and predictable), then a bare
// `video: true` fallback — some webcams/drivers stall or reject a specific
// resolution yet start fine when left unconstrained.
const CAMERA_CONSTRAINTS: MediaStreamConstraints[] = [
  {
    video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
    audio: false,
  },
  { video: true, audio: false },
];

// How long (ms) to wait for an acquired stream to actually deliver a decodable
// frame before treating startup as failed. getUserMedia can resolve with a
// stream that never produces frames (wedged driver, or a privacy shutter that
// engaged mid-start) — the classic "camera on, preview black, no error" trap.
// Deliberately generous: a healthy local webcam fires `loadeddata` in well under
// a second, so this only ever trips on a real stall. It starts counting AFTER
// permission is granted, so it never races the user deciding on the prompt.
const VIDEO_READY_TIMEOUT_MS = 10000;

// getUserMedia failures worth retrying with a looser constraint set: the device
// was found and permitted but would not start (busy, over-constrained, or a
// transient driver timeout). Permission denials and "no device" are NOT here — a
// looser request cannot recover them, so they surface immediately.
const RETRYABLE_CAMERA_ERRORS = new Set<string>([
  "NotReadableError",
  "TrackStartError",
  "AbortError",
  "TimeoutError",
  "OverconstrainedError",
]);

function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

// DOMException name for a camera failure, or "" for a non-DOMException throw.
function cameraErrorName(error: unknown): string {
  return error instanceof DOMException ? error.name : "";
}

// Map a raw getUserMedia / readiness failure to actionable, cause-specific copy.
// Every branch says what to do next (retry, free the device, grant permission, or
// switch detector) instead of leaking a terse browser string like "Timeout
// starting video source".
function describeCameraError(error: unknown): string {
  switch (cameraErrorName(error)) {
    case "NotAllowedError":
    case "SecurityError":
      return "Camera permission was denied. Allow camera access for this site (the camera icon in the address bar), then press Start Camera again.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "No camera was found. Connect a webcam — and check it isn't disabled in your OS camera/privacy settings — then try again.";
    case "OverconstrainedError":
      return "No camera matched the requested video settings. Press Start Camera again to retry with default settings.";
    case "NotReadableError":
    case "TrackStartError":
      return "The camera could not start — it is usually held by another app (Zoom, Teams, Meet, OBS) or a privacy shutter. Close anything else using the webcam, then press Start Camera again.";
    case "AbortError":
    case "TimeoutError":
      return "Timed out starting the camera. This is usually transient — press Start Camera again. If it keeps happening, close other apps using the webcam, unplug/replug it, or reload the page.";
    default:
      return error instanceof Error && error.message
        ? `Could not start the camera: ${error.message}. Press Start Camera to retry, or switch detectors.`
        : "Could not start the camera. Press Start Camera to retry, or switch detectors.";
  }
}

// Resolve once the attached stream has produced a decodable frame, or reject with
// a TimeoutError after `ms`. Listens for both `loadeddata` and `canplay` (browsers
// disagree on which fires first for a live MediaStream) and short-circuits if the
// element is already ready. Always detaches its listeners/timer so it cannot leak.
function waitForVideoReady(video: HTMLVideoElement, ms: number): Promise<void> {
  if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
    return Promise.resolve();
  }
  return new Promise<void>((resolve, reject) => {
    let done = false;
    const finish = (ok: boolean) => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      video.removeEventListener("loadeddata", onReady);
      video.removeEventListener("canplay", onReady);
      if (ok) {
        resolve();
      } else {
        reject(
          new DOMException(
            "The camera stream did not produce a frame in time.",
            "TimeoutError",
          ),
        );
      }
    };
    const onReady = () => finish(true);
    const timer = window.setTimeout(() => finish(false), ms);
    video.addEventListener("loadeddata", onReady);
    video.addEventListener("canplay", onReady);
  });
}

// Acquire a camera stream, trying each constraint set in turn. A retryable
// "device wouldn't start" failure on the first (specific) request falls through
// to the bare `video: true` request; a permission / no-device failure throws
// immediately, since a looser request cannot recover it. The first request
// triggers the permission prompt; once granted, the fallback reuses that grant
// without re-prompting.
async function openCameraStream(): Promise<MediaStream> {
  let lastError: unknown;
  for (let i = 0; i < CAMERA_CONSTRAINTS.length; i += 1) {
    try {
      return await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS[i]);
    } catch (error) {
      lastError = error;
      const isLast = i === CAMERA_CONSTRAINTS.length - 1;
      if (isLast || !RETRYABLE_CAMERA_ERRORS.has(cameraErrorName(error))) {
        throw error;
      }
    }
  }
  throw lastError;
}

// Human-readable direction hint for the readout, so a viewer can sanity-check
// the sign convention without decoding the raw number. Returns "—" inside the
// dead zone so idle jitter doesn't flicker between the two labels.
function describeDelta(
  value: number,
  negativeLabel: string,
  positiveLabel: string,
): string {
  if (value <= -DIRECTION_HINT_EPS) return negativeLabel;
  if (value >= DIRECTION_HINT_EPS) return positiveLabel;
  return "—";
}

// A mediapipe-flavoured idle command (source tagged, all zero). Used when the
// detector is live but no hand is currently in frame.
const MEDIAPIPE_IDLE: MotionCommand = {
  ...ZERO_MOTION,
  source: "mediapipe-hand-landmarker",
};

/* Phase 32M — live control-feedback readout.

   The throttled snapshot of the "is my hand doing the right thing" cues: where
   the hand sits in range, how strong tracking is, whether control is
   warming/active/uncertain/idle (post-hysteresis), and whether a pinch is being
   held intentionally. Kept as one object so the ~12Hz readout updates in a single
   batched setState alongside the existing HandInfo/MotionCommand pushes. */
type ControlFeedback = {
  range: HandRange | "no-hand";
  quality: ConfidenceQuality;
  controlPhase: ControlPhase;
  pinchPhase: PinchPhase;
};

const NEUTRAL_FEEDBACK: ControlFeedback = {
  range: "no-hand",
  quality: "no-hand",
  controlPhase: "idle",
  pinchPhase: "idle",
};

// UI copy + status-pill class for each feedback dimension. Kept as small pure
// maps (not scattered ternaries in JSX) so the honest, concise labels live in one
// place. `neutral`/`pending`/`success`/`error` reuse the existing status-pill
// hues — no new colour tokens.
type PillTone = "neutral" | "pending" | "success" | "error";

function rangeLabel(range: ControlFeedback["range"]): { label: string; tone: PillTone } {
  switch (range) {
    case "in-range":
      return { label: "Hand in range", tone: "success" };
    case "too-close":
      return { label: "Hand too close", tone: "pending" };
    case "too-far":
      return { label: "Hand too far", tone: "pending" };
    default:
      return { label: "No hand", tone: "neutral" };
  }
}

function qualityLabel(quality: ConfidenceQuality): { label: string; tone: PillTone } {
  switch (quality) {
    case "strong":
      return { label: "Strong", tone: "success" };
    case "okay":
      return { label: "Okay", tone: "pending" };
    case "weak":
      return { label: "Weak", tone: "error" };
    default:
      return { label: "No hand", tone: "neutral" };
  }
}

function controlPhaseLabel(phase: ControlPhase): { label: string; tone: PillTone } {
  switch (phase) {
    case "active":
      return { label: "Active", tone: "success" };
    case "warming":
      return { label: "Warming up", tone: "pending" };
    case "uncertain":
      return { label: "Uncertain", tone: "pending" };
    default:
      return { label: "Idle", tone: "neutral" };
  }
}

function pinchPhaseLabel(phase: PinchPhase): { label: string; tone: PillTone } {
  switch (phase) {
    case "holding":
      return { label: "Holding", tone: "success" };
    case "ready":
      return { label: "Ready", tone: "pending" };
    default:
      return { label: "Idle", tone: "neutral" };
  }
}

/* Phase 32G — optional wiring props.

   The panel is still self-contained: with none of these passed (or graph control
   left off) it behaves exactly as the Phase 32D sandbox. `onMotionCommand` is a
   pure sink — the panel forwards its already-derived MotionCommand to it every
   frame so an opt-in consumer (the Knowledge Graph camera) can read live motion
   without this panel knowing anything about the graph. The toggle only reflects
   and flips a boolean owned by App; this panel never controls the graph itself. */
type MotionSandboxPanelProps = {
  id?: string;
  /** Sink for the freshest derived MotionCommand, called once per detection
      frame. Ref-write only in App — safe to call at frame rate. */
  onMotionCommand?: (command: MotionCommand) => void;
  /** Whether the user has opted the graph camera into motion control. */
  graphControlEnabled?: boolean;
  /** Flip the opt-in graph-control switch (owned by App). */
  onToggleGraphControl?: (enabled: boolean) => void;
};

function MotionSandboxPanel({
  id,
  onMotionCommand,
  graphControlEnabled = false,
  onToggleGraphControl,
}: MotionSandboxPanelProps) {
  const [mode, setMode] = useState<DetectorMode>("mediapipe-hand-landmarker");
  const [status, setStatus] = useState<CameraStatus>("inactive");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [motion, setMotion] = useState<MotionCommand>(ZERO_MOTION);
  const [mpStatus, setMpStatus] = useState<MediaPipeStatus>("idle");
  const [handInfo, setHandInfo] = useState<HandInfo>(NO_HAND);
  // Phase 32M — throttled live control-feedback cues (range / quality / control
  // phase / pinch phase). MediaPipe mode only; frame-difference has no hand model.
  const [feedback, setFeedback] = useState<ControlFeedback>(NEUTRAL_FEEDBACK);

  // Live-object refs: none of these should trigger a re-render when they change.
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const debugCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const procCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const prevGrayRef = useRef<Float32Array | null>(null);
  // Smoothed command carried across frames (the value we EMA toward).
  const smoothedRef = useRef<MotionCommand>(ZERO_MOTION);
  const lastReadoutRef = useRef<number>(0);
  // Phase 32M — temporal gates carried across frames. `controlGate` debounces
  // active/idle (hysteresis); `pinchGate` debounces the pinch hold. Both are pure
  // reducers advanced with `performance.now()`; they live in refs so the RAF loop
  // updates them without re-rendering.
  const controlGateRef = useRef<ControlGate>(createControlGate());
  const pinchGateRef = useRef<PinchGate>(createPinchGate());

  // Phase 32G: keep the (optional) command sink in a ref so the detection loop
  // can forward every frame without `publishReadout`/`teardown` re-binding when
  // the prop identity changes. Ref-write only — never a React re-render here.
  const onMotionCommandRef = useRef(onMotionCommand);
  useEffect(() => {
    onMotionCommandRef.current = onMotionCommand;
  }, [onMotionCommand]);

  // MediaPipe detector, cached so we never re-initialise it (guard against the
  // costly wasm+model load on every Start). `modeRef` lets the RAF loop read the
  // active estimator without recreating itself.
  const handLandmarkerRef = useRef<HandLandmarkerInstance | null>(null);
  const modeRef = useRef<DetectorMode>(mode);
  const lastVideoTimeRef = useRef<number>(-1);
  const lastDetectTsRef = useRef<number>(0);
  // Prevent state updates after unmount (async model load can resolve late).
  const mountedRef = useRef<boolean>(true);

  // Keep the loop's view of the mode in sync. Mode is locked while the camera is
  // active (the toggle is disabled), so this only changes between sessions.
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // Lazily create (once) and return the MediaPipe Hand Landmarker. Dynamic import
  // keeps the wasm glue out of the initial bundle until the user opts in. Tries
  // the GPU delegate first, then falls back to CPU so the sandbox still works on
  // machines without WebGL2.
  const ensureHandLandmarker =
    useCallback(async (): Promise<HandLandmarkerInstance> => {
      if (handLandmarkerRef.current) {
        return handLandmarkerRef.current;
      }
      if (typeof WebAssembly === "undefined") {
        setMpStatus("unsupported");
        throw new Error("WebAssembly is unavailable in this browser.");
      }

      setMpStatus("loading");
      const { FilesetResolver, HandLandmarker } = await import(
        "@mediapipe/tasks-vision"
      );
      const vision = await FilesetResolver.forVisionTasks(MP_WASM_ROOT);

      const create = (delegate: "GPU" | "CPU") =>
        HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: HAND_MODEL_URL, delegate },
          runningMode: "VIDEO",
          numHands: 1,
        });

      let landmarker: HandLandmarkerInstance;
      try {
        landmarker = await create("GPU");
      } catch {
        // GPU delegate can fail on machines without WebGL2 — retry on CPU.
        landmarker = await create("CPU");
      }

      handLandmarkerRef.current = landmarker;
      return landmarker;
    }, []);

  // Tear down every live resource. Safe to call repeatedly (idempotent) — used by
  // the Stop button, error paths, and unmount cleanup alike. Note: it does NOT
  // close the cached MediaPipe detector (that is reused across Start/Stop and
  // only closed on unmount).
  const teardown = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const stream = streamRef.current;
    if (stream) {
      for (const track of stream.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    prevGrayRef.current = null;
    smoothedRef.current = ZERO_MOTION;
    lastVideoTimeRef.current = -1;
    // Phase 32M — reset the temporal gates so a new session starts idle rather
    // than inheriting a previous run's latched active/pinch state.
    controlGateRef.current = createControlGate();
    pinchGateRef.current = createPinchGate();
    // Phase 32G: forward a final idle command so a graph consumer decays to
    // stillness the moment the camera stops (no frozen last-frame deltas).
    onMotionCommandRef.current?.(ZERO_MOTION);
    // Clear the landmark overlay so a stale skeleton doesn't linger.
    const overlay = overlayCanvasRef.current;
    const octx = overlay?.getContext("2d") ?? null;
    if (overlay && octx) {
      octx.clearRect(0, 0, overlay.width, overlay.height);
    }
  }, []);

  /* Phase 36D — full-hand landmark diagnostic overlay.

     Draw the complete 21-landmark MediaPipe hand model onto the overlay canvas,
     layered so the diagnostic skeleton stays subtle while the control-relevant
     geometry stays unmissable:

       1. bones            very thin translucent cyan lines (full skeleton)
       2. landmark dots    small faint cyan dots — every detected landmark
       3. wrist ring       hollow ring: the skeleton's anchor joint
       4. palm-centre ring smaller ring at the derived palm centroid — the point
                           yaw/pitch actually track (see deriveHandCommand)
       5. pinch line       thumb-tip↔index-tip gesture line: faint dashed while
                           open, solid bright green while the debounced hold is on
       6. thumb/index tips always brighter + larger than the diagnostic dots;
                           green while pinch-held, cyan otherwise

     Purely visual: it reads the same landmarks/pinch state the command pipeline
     already produced and feeds nothing back into it. Coords are normalized; the
     canvas is CSS-mirrored to match the mirrored preview. */
  const drawOverlay = useCallback(
    (landmarks: Landmark[], pinchActive: boolean) => {
      const overlay = overlayCanvasRef.current;
      const octx = overlay?.getContext("2d") ?? null;
      if (!overlay || !octx) return;

      const w = overlay.width;
      const h = overlay.height;
      octx.clearRect(0, 0, w, h);
      // No hand this frame → leave the canvas clear (idle state unchanged).
      if (landmarks.length === 0) return;

      // 1. Full skeleton bones — thin and translucent so they read as a
      //    diagnostic layer over the video, not a mask on top of it.
      octx.lineWidth = 1.5;
      octx.strokeStyle = "rgba(103, 232, 249, 0.4)";
      octx.beginPath();
      for (const [a, b] of HAND_CONNECTIONS) {
        const pa = landmarks[a];
        const pb = landmarks[b];
        if (!pa || !pb) continue;
        octx.moveTo(pa.x * w, pa.y * h);
        octx.lineTo(pb.x * w, pb.y * h);
      }
      octx.stroke();

      // 2. Every detected landmark as a small faint dot, so partial or jittery
      //    tracking is visible joint-by-joint. The two control tips are skipped
      //    here and drawn brighter on top (step 6).
      octx.fillStyle = "rgba(134, 239, 220, 0.6)";
      for (let i = 0; i < landmarks.length; i += 1) {
        if (i === LM.THUMB_TIP || i === LM.INDEX_TIP) continue;
        const p = landmarks[i];
        octx.beginPath();
        octx.arc(p.x * w, p.y * h, 3, 0, Math.PI * 2);
        octx.fill();
      }

      // 3./4. Orientation anchors — hollow rings so they mark position without
      // covering pixels: the wrist joint, and the palm centroid the yaw/pitch
      // derivation actually follows. Diagnostic only; commands are unchanged.
      const wrist = landmarks[LM.WRIST];
      if (wrist) {
        octx.lineWidth = 1.5;
        octx.strokeStyle = "rgba(103, 232, 249, 0.65)";
        octx.beginPath();
        octx.arc(wrist.x * w, wrist.y * h, 8, 0, Math.PI * 2);
        octx.stroke();
      }
      if (landmarks.length > LM.PINKY_MCP) {
        const palm = palmCenter(landmarks);
        octx.lineWidth = 1.25;
        octx.strokeStyle = "rgba(103, 232, 249, 0.5)";
        octx.beginPath();
        octx.arc(palm.x * w, palm.y * h, 5, 0, Math.PI * 2);
        octx.stroke();
      }

      // 5. Pinch gesture line between the two control tips: dashed and faint
      //    while open (the gap the pinch ratio measures), solid bright green
      //    while the debounced hold is engaged.
      const thumbTip = landmarks[LM.THUMB_TIP];
      const indexTip = landmarks[LM.INDEX_TIP];
      if (thumbTip && indexTip) {
        octx.lineWidth = pinchActive ? 2.5 : 1.25;
        octx.strokeStyle = pinchActive
          ? "rgba(122, 240, 170, 0.9)"
          : "rgba(165, 243, 252, 0.5)";
        octx.setLineDash(pinchActive ? [] : [5, 5]);
        octx.beginPath();
        octx.moveTo(thumbTip.x * w, thumbTip.y * h);
        octx.lineTo(indexTip.x * w, indexTip.y * h);
        octx.stroke();
        octx.setLineDash([]);
      }

      // 6. Active control tips — always brighter and larger than the diagnostic
      //    dots, with a dark outline so they hold up over bright video.
      const tipFill = pinchActive
        ? "rgba(122, 240, 170, 0.95)"
        : "rgba(165, 243, 252, 0.95)";
      for (const tip of [thumbTip, indexTip]) {
        if (!tip) continue;
        octx.beginPath();
        octx.arc(tip.x * w, tip.y * h, 6, 0, Math.PI * 2);
        octx.fillStyle = tipFill;
        octx.fill();
        octx.lineWidth = 1.5;
        octx.strokeStyle = "rgba(10, 24, 22, 0.65)";
        octx.stroke();
      }
    },
    [],
  );

  // Push a smoothed command to the throttled React readout (~12Hz). Phase 32G:
  // the freshest command is also forwarded to the optional sink every frame
  // (unthrottled) so a graph consumer gets per-frame motion; only the on-screen
  // readout stays throttled. The forward is a ref write in App, so it never
  // re-renders anything here regardless of whether graph control is on.
  //
  // Returns true on the frames where the throttle actually fired, so callers can
  // batch their own readout setStates (hand detection, control feedback) onto the
  // same ~12Hz tick. Phase 32M: this also fixes a latent throttle bug — the old
  // code re-checked `lastReadoutRef` *after* this method had already advanced it,
  // so those secondary setStates could never run.
  const publishReadout = useCallback(
    (smoothed: MotionCommand, now: number): boolean => {
      onMotionCommandRef.current?.(smoothed);
      if (now - lastReadoutRef.current >= READOUT_INTERVAL_MS) {
        lastReadoutRef.current = now;
        setMotion(smoothed);
        return true;
      }
      return false;
    },
    [],
  );

  // --- Frame-difference estimator (Phase 32B/32C, preserved) -----------------
  // Reads the (mirrored) video into the tiny proc canvas, diffs it against the
  // previous frame, and derives a MotionCommand from where — and how much — the
  // frame changed. Also paints the debug "motion field" heatmap.
  const runFrameDifference = useCallback((now: number) => {
    const video = videoRef.current;
    const procCanvas = procCanvasRef.current;
    if (!video || !procCanvas) return;

    const procCtx = procCanvas.getContext("2d", { willReadFrequently: true });
    if (!procCtx) return;

    // Draw mirrored so the sampled pixels match the mirrored preview.
    procCtx.save();
    procCtx.scale(-1, 1);
    procCtx.drawImage(video, -PROC_W, 0, PROC_W, PROC_H);
    procCtx.restore();

    const { data } = procCtx.getImageData(0, 0, PROC_W, PROC_H);
    const pixelCount = PROC_W * PROC_H;
    const gray = new Float32Array(pixelCount);
    const prev = prevGrayRef.current;

    let motionSum = 0;
    let weightX = 0;
    let weightY = 0;

    const debugCtx = debugCanvasRef.current?.getContext("2d") ?? null;
    const debugImage = debugCtx
      ? debugCtx.createImageData(PROC_W, PROC_H)
      : null;

    for (let i = 0; i < pixelCount; i += 1) {
      const r = data[i * 4];
      const g = data[i * 4 + 1];
      const b = data[i * 4 + 2];
      const luma = 0.299 * r + 0.587 * g + 0.114 * b;
      gray[i] = luma;

      let delta = prev ? Math.abs(luma - prev[i]) : 0;
      if (delta < NOISE_FLOOR) {
        delta = 0;
      }
      if (delta > 0) {
        motionSum += delta;
        const x = i % PROC_W;
        const y = (i / PROC_W) | 0;
        weightX += x * delta;
        weightY += y * delta;
      }

      if (debugImage) {
        const intensity = clamp(delta * 2.4, 0, 255);
        debugImage.data[i * 4] = 90 + intensity * 0.5;
        debugImage.data[i * 4 + 1] = 60 + intensity * 0.2;
        debugImage.data[i * 4 + 2] = 120 + intensity * 0.5;
        debugImage.data[i * 4 + 3] = 40 + intensity;
      }
    }

    if (debugCtx && debugImage) {
      debugCtx.putImageData(debugImage, 0, 0);
    }

    prevGrayRef.current = gray;

    const avgEnergy = motionSum / (pixelCount * 255);
    const confidence = clamp(avgEnergy * CONFIDENCE_GAIN, 0, 1);

    let yawDelta = 0;
    let pitchDelta = 0;
    if (motionSum > 0 && confidence >= MOTION_GATE) {
      const cx = weightX / motionSum / PROC_W;
      const cy = weightY / motionSum / PROC_H;
      yawDelta = clamp((cx - 0.5) * 2, -1, 1);
      pitchDelta = clamp((0.5 - cy) * 2, -1, 1);
    }

    const prevCmd = smoothedRef.current;
    const smoothedConfidence =
      prevCmd.confidence + (confidence - prevCmd.confidence) * SMOOTHING;
    const smoothed: MotionCommand = {
      yawDelta: prevCmd.yawDelta + (yawDelta - prevCmd.yawDelta) * SMOOTHING,
      pitchDelta: prevCmd.pitchDelta + (pitchDelta - prevCmd.pitchDelta) * SMOOTHING,
      zoomDelta: 0,
      pinchActive: false,
      confidence: smoothedConfidence,
      active: smoothedConfidence >= MOTION_GATE,
      source: "frame-difference",
      timestamp: now,
    };
    smoothedRef.current = smoothed;
    publishReadout(smoothed, now);
  }, [publishReadout]);

  // Phase 32M — emit one MediaPipe idle frame: no usable hand this tick (detector
  // still loading, or hand out of frame). The confidence eases toward zero and
  // both gates are advanced with "no signal", so a hand that blinks out doesn't
  // instantly drop control (hysteresis) but a sustained absence decays it to idle.
  // `active` follows the debounced gate, not a hard false, for the same reason.
  const emitIdleFrame = useCallback(
    (now: number) => {
      const prevCmd = smoothedRef.current;
      const decayedConfidence = prevCmd.confidence + (0 - prevCmd.confidence) * SMOOTHING;
      const controlGate = advanceControlGate(
        controlGateRef.current,
        decayedConfidence,
        false,
        now,
      );
      controlGateRef.current = controlGate;
      const pinchGate = advancePinchGate(pinchGateRef.current, false, now);
      pinchGateRef.current = pinchGate;

      const smoothed: MotionCommand = {
        ...MEDIAPIPE_IDLE,
        confidence: decayedConfidence,
        active: controlGate.active,
        timestamp: now,
      };
      smoothedRef.current = smoothed;

      const published = publishReadout(smoothed, now);
      if (!published) return;
      setHandInfo(NO_HAND);
      setFeedback({
        range: "no-hand",
        quality: "no-hand",
        controlPhase: controlGate.phase,
        pinchPhase: pinchGate.phase,
      });
    },
    [publishReadout],
  );

  // --- MediaPipe hand-landmarker estimator (Phase 32D) -----------------------
  // Runs the detector on the raw video (never mirrored input; x is mirrored in
  // the derivation to match the preview). Skips stalled/duplicate frames and
  // guarantees strictly-increasing timestamps for detectForVideo.
  const runMediaPipe = useCallback((now: number) => {
    const video = videoRef.current;
    const landmarker = handLandmarkerRef.current;
    // Detector not ready (still loading or failed) — emit a tagged idle command
    // so the readout stays honest instead of freezing on stale values. Advance
    // the gates with no signal so any latched active/pinch decays out too.
    if (!video || !landmarker) {
      emitIdleFrame(now);
      return;
    }

    // Skip detection on an unchanged frame (tab throttling / paused decode).
    if (video.currentTime === lastVideoTimeRef.current) {
      return;
    }
    lastVideoTimeRef.current = video.currentTime;

    // detectForVideo requires a strictly-increasing millisecond timestamp.
    let ts = now;
    if (ts <= lastDetectTsRef.current) {
      ts = lastDetectTsRef.current + 1;
    }
    lastDetectTsRef.current = ts;

    let result: HandLandmarkerResult;
    try {
      result = landmarker.detectForVideo(video, ts);
    } catch {
      // A transient detection failure shouldn't kill the loop; treat as no hand.
      result = { landmarks: [], worldLandmarks: [], handedness: [], handednesses: [] };
    }

    const hasHand = result.landmarks.length > 0 && result.landmarks[0].length > 0;

    if (!hasHand) {
      emitIdleFrame(now);
      drawOverlay([], false);
      return;
    }

    const landmarks = result.landmarks[0] as Landmark[];
    const category = result.handedness[0]?.[0];
    const handedness = category?.categoryName ?? null;
    const score = category?.score ?? 0;

    const target = deriveHandCommand(landmarks, score, now);

    // Smooth the continuous fields; the discrete pinch/active come from the
    // temporal gates below (not straight from `target`) so both are debounced.
    const prevCmd = smoothedRef.current;
    const smoothedConfidence =
      prevCmd.confidence + (target.confidence - prevCmd.confidence) * SMOOTHING;

    // Phase 32M — hysteresis on active/idle and debounce on pinch. The control
    // gate reads the *smoothed* confidence (steadier than the raw score); the
    // pinch gate reads the raw per-frame pinch and promotes it to a held state.
    const controlGate = advanceControlGate(
      controlGateRef.current,
      smoothedConfidence,
      true,
      now,
    );
    controlGateRef.current = controlGate;
    const pinchGate = advancePinchGate(pinchGateRef.current, target.pinchActive, now);
    pinchGateRef.current = pinchGate;

    const smoothed: MotionCommand = {
      yawDelta: prevCmd.yawDelta + (target.yawDelta - prevCmd.yawDelta) * SMOOTHING,
      pitchDelta: prevCmd.pitchDelta + (target.pitchDelta - prevCmd.pitchDelta) * SMOOTHING,
      zoomDelta: prevCmd.zoomDelta + (target.zoomDelta - prevCmd.zoomDelta) * SMOOTHING,
      pinchActive: pinchGate.held,
      confidence: smoothedConfidence,
      active: controlGate.active,
      source: "mediapipe-hand-landmarker",
      timestamp: now,
    };
    smoothedRef.current = smoothed;

    // Overlay highlights the pinch on the debounced hold, so it stops strobing.
    drawOverlay(landmarks, pinchGate.held);

    const published = publishReadout(smoothed, now);
    if (!published) return;
    setHandInfo({
      handDetected: true,
      handedness,
      landmarkCount: landmarks.length,
      score,
    });
    setFeedback({
      range: classifyHandRange(handBoundingSpan(landmarks)),
      quality: classifyConfidence(smoothedConfidence, true),
      controlPhase: controlGate.phase,
      pinchPhase: pinchGate.phase,
    });
  }, [drawOverlay, emitIdleFrame, publishReadout]);

  // The single RAF loop. Dispatches to the active estimator each frame and
  // reschedules itself. Guards against running before video metadata is ready.
  const runFrame = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(runFrame);
      return;
    }
    const now = performance.now();
    if (modeRef.current === "mediapipe-hand-landmarker") {
      runMediaPipe(now);
    } else {
      runFrameDifference(now);
    }
    rafRef.current = requestAnimationFrame(runFrame);
  }, [runMediaPipe, runFrameDifference]);

  const startCamera = useCallback(async () => {
    // Guard: never double-start (would leak a second stream).
    if (status === "requesting" || status === "active") {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setErrorMessage(
        "This browser does not expose camera access (getUserMedia unavailable).",
      );
      return;
    }

    const activeMode = mode;
    setErrorMessage(null);
    setStatus("requesting");
    setMotion(activeMode === "mediapipe-hand-landmarker" ? MEDIAPIPE_IDLE : ZERO_MOTION);
    setHandInfo(NO_HAND);
    setFeedback(NEUTRAL_FEEDBACK);
    smoothedRef.current =
      activeMode === "mediapipe-hand-landmarker" ? MEDIAPIPE_IDLE : ZERO_MOTION;
    controlGateRef.current = createControlGate();
    pinchGateRef.current = createPinchGate();
    prevGrayRef.current = null;
    lastVideoTimeRef.current = -1;

    let stream: MediaStream;
    try {
      stream = await openCameraStream();
    } catch (streamError: unknown) {
      teardown();
      if (!mountedRef.current) return;
      setStatus("error");
      setErrorMessage(describeCameraError(streamError));
      return;
    }

    streamRef.current = stream;
    const video = videoRef.current;
    if (!video || !mountedRef.current) {
      // Component unmounted mid-request — don't leave the device on.
      for (const track of stream.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
      return;
    }

    video.srcObject = stream;
    try {
      await video.play();
    } catch {
      // Autoplay can reject if the element isn't ready; the RAF loop tolerates a
      // not-yet-playing video (readyState guard) and picks up once it decodes.
    }

    // A Stop/unmount during play() must abort startup cleanly — don't leave a
    // stream on, and don't flip to "active".
    if (!mountedRef.current || streamRef.current !== stream) return;

    // Confirm the stream actually delivers a frame before declaring the camera
    // active. This closes the "getUserMedia resolved but no frames ever arrive"
    // gap (wedged driver / privacy shutter mid-start): on timeout we tear down
    // and surface a clear, retryable error instead of a permanently black preview
    // and a loop spinning on a never-ready video.
    try {
      await waitForVideoReady(video, VIDEO_READY_TIMEOUT_MS);
    } catch (readyError: unknown) {
      teardown();
      if (!mountedRef.current) return;
      setStatus("error");
      setErrorMessage(describeCameraError(readyError));
      return;
    }

    if (!mountedRef.current || streamRef.current !== stream) return;
    setStatus("active");

    // In MediaPipe mode, load the detector (once) before the loop leans on it.
    // Failure is non-fatal: the loop runs, reports idle, and the error surfaces.
    if (activeMode === "mediapipe-hand-landmarker") {
      try {
        await ensureHandLandmarker();
        if (!mountedRef.current || streamRef.current !== stream) return;
        setMpStatus("ready");
      } catch (loadError: unknown) {
        if (!mountedRef.current || streamRef.current !== stream) return;
        setMpStatus((prev) => (prev === "unsupported" ? prev : "error"));
        setErrorMessage(
          loadError instanceof Error
            ? `MediaPipe failed to initialise: ${loadError.message}. Switch to the frame-difference fallback, or retry.`
            : "MediaPipe failed to initialise. Switch to the frame-difference fallback, or retry.",
        );
      }
    }

    lastReadoutRef.current = 0;
    lastDetectTsRef.current = 0;
    rafRef.current = requestAnimationFrame(runFrame);
  }, [ensureHandLandmarker, mode, runFrame, status, teardown]);

  const stopCamera = useCallback(() => {
    teardown();
    setStatus("stopped");
    setMotion(mode === "mediapipe-hand-landmarker" ? MEDIAPIPE_IDLE : ZERO_MOTION);
    setHandInfo(NO_HAND);
    setFeedback(NEUTRAL_FEEDBACK);
    if (mpStatus === "loading") {
      setMpStatus(handLandmarkerRef.current ? "ready" : "idle");
    }
  }, [mode, mpStatus, teardown]);

  // Safety net: on unmount release the stream AND close the MediaPipe detector.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      teardown();
      if (handLandmarkerRef.current) {
        handLandmarkerRef.current.close();
        handLandmarkerRef.current = null;
      }
    };
  }, [teardown]);

  const isActive = status === "active";
  const isBusy = status === "requesting";
  const isMediaPipe = mode === "mediapipe-hand-landmarker";

  const statusChip = (() => {
    switch (status) {
      case "requesting":
        return { className: "status-pill-pending", label: "Requesting permission…" };
      case "active":
        return { className: "status-pill-success", label: "Camera active" };
      case "error":
        return { className: "status-pill-error", label: "Camera error" };
      case "stopped":
        return { className: "status-pill-pending", label: "Camera stopped" };
      default:
        return { className: "status-pill-pending", label: "Camera inactive" };
    }
  })();

  const mpChip = (() => {
    switch (mpStatus) {
      case "loading":
        return { className: "status-pill-pending", label: "MediaPipe loading…" };
      case "ready":
        return { className: "status-pill-success", label: "MediaPipe ready" };
      case "unsupported":
        return { className: "status-pill-error", label: "MediaPipe unsupported" };
      case "error":
        return { className: "status-pill-error", label: "MediaPipe error" };
      default:
        return { className: "status-pill-pending", label: "MediaPipe idle" };
    }
  })();

  // Phase 32M — resolve the live control cues to copy + tone for the readout.
  const rangeCue = rangeLabel(feedback.range);
  const qualityCue = qualityLabel(feedback.quality);
  const controlCue = controlPhaseLabel(feedback.controlPhase);
  const pinchCue = pinchPhaseLabel(feedback.pinchPhase);

  return (
    <section className="motion-sandbox" id={id}>
      <h2>Motion Sandbox</h2>
      <p className="motion-sandbox-intro">
        Standalone webcam motion probe (Phase 32B, contract hardened in 32C,
        MediaPipe hand landmarks added in 32D). Nothing starts until you press{" "}
        <strong>Start Camera</strong>, and this surface never touches the
        knowledge graph — it only derives and displays a normalized{" "}
        <code>MotionCommand</code> for inspection. All processing is browser-local;
        no video, frames, or landmarks are stored or transmitted.
      </p>

      <fieldset className="motion-sandbox-modes" disabled={isActive || isBusy}>
        <legend>Detector</legend>
        <label>
          <input
            type="radio"
            name="motion-detector-mode"
            value="mediapipe-hand-landmarker"
            checked={isMediaPipe}
            onChange={() => setMode("mediapipe-hand-landmarker")}
          />
          Hand landmarks (MediaPipe)
        </label>
        <label>
          <input
            type="radio"
            name="motion-detector-mode"
            value="frame-difference"
            checked={!isMediaPipe}
            onChange={() => setMode("frame-difference")}
          />
          Frame difference (fallback)
        </label>
      </fieldset>

      <div className="motion-sandbox-statusrow">
        <p className={`status-pill ${statusChip.className}`}>
          <span className="status-dot" aria-hidden="true" />
          {statusChip.label}
        </p>
        {isMediaPipe && (
          <p className={`status-pill ${mpChip.className}`}>
            <span className="status-dot" aria-hidden="true" />
            {mpChip.label}
          </p>
        )}
      </div>

      <div className="motion-sandbox-actions">
        <button
          type="button"
          className="motion-sandbox-start"
          onClick={startCamera}
          disabled={isBusy || isActive}
        >
          {isBusy
            ? "Starting…"
            : status === "error"
              ? "Retry camera"
              : "Start Camera"}
        </button>
        <button
          type="button"
          className="motion-sandbox-stop"
          onClick={stopCamera}
          disabled={!isActive && status !== "requesting"}
        >
          Stop Camera
        </button>
      </div>

      {/* Phase 32M — practical camera + placement guidance. Copy only: it never
          selects or forces a device (the browser's own picker still applies once
          permission is granted), and it stays honest about what has actually been
          validated versus what remains experimental. */}
      <div className="motion-sandbox-guidance">
        <p className="motion-sandbox-guidance-line">
          <span className="motion-sandbox-guidance-key">Recommended camera</span>
          <span>HD Pro Webcam C920 — validated for live graph-control testing.</span>
        </p>
        <p className="motion-sandbox-guidance-line">
          <span className="motion-sandbox-guidance-key">Backup camera</span>
          <span>iC1200 2K QUAD HD.</span>
        </p>
        <p className="motion-sandbox-guidance-line">
          <span className="motion-sandbox-guidance-key">Recommended distance</span>
          <span>12–30 inches — keep your hand inside the control zone.</span>
        </p>
        <p className="motion-sandbox-guidance-note">
          Experimental. A built-in laptop camera may be unavailable; pick your
          webcam in the browser prompt after granting access. No camera frames are
          stored.
        </p>
      </div>

      {/* Phase 32G — explicit, opt-in graph wiring. Off by default; the webcam
          never drives the graph just because this panel is open. Enabling it
          routes the derived MotionCommand to the Knowledge Graph's camera as a
          read-only, visual-only transform (the graph's nodes, edges, data, and
          selection are never touched). */}
      <div className="motion-sandbox-graphctrl">
        <div className="motion-sandbox-graphctrl-head">
          <label className="motion-sandbox-graphctrl-toggle">
            <input
              type="checkbox"
              checked={graphControlEnabled}
              onChange={(event) =>
                onToggleGraphControl?.(event.target.checked)
              }
              disabled={!onToggleGraphControl}
            />
            <span>Motion controls graph</span>
          </label>
          <span className="motion-sandbox-graphctrl-tag">Experimental · off by default</span>
        </div>
        <p className="motion-sandbox-graphctrl-hint">
          {graphControlEnabled
            ? "Enabled — hand motion orbits, tilts, and zooms the graph camera only (visual, read-only). Your nodes, edges, and data are never changed. Uncheck to disable instantly; still hands recentre it, or use Recenter on the graph."
            : "Off — the graph ignores webcam motion entirely. Enable to let hand motion move the graph camera as a visual-only, read-only view; it changes no graph data and can be turned off at any time."}
        </p>
      </div>

      {errorMessage && (
        <p className="error motion-sandbox-error" role="alert">
          {errorMessage}
        </p>
      )}

      <div className="motion-sandbox-stage">
        <div className="motion-sandbox-preview">
          <span className="motion-sandbox-preview-label">Preview</span>
          {/* Mirrored preview (scaleX(-1) in CSS) so it reads like a mirror.
              Muted + playsInline + no controls; only shown when live. */}
          <video
            ref={videoRef}
            className="motion-sandbox-video"
            muted
            playsInline
            data-live={isActive ? "true" : "false"}
          />
          {/* Landmark overlay — mirrored to match the preview; only in MP mode. */}
          <canvas
            ref={overlayCanvasRef}
            className="motion-sandbox-overlay"
            width={OVERLAY_W}
            height={OVERLAY_H}
            data-live={isActive && isMediaPipe ? "true" : "false"}
          />
          {/* Phase 32M — control-zone guide. A centred, rounded frame with inner
              bounds that reads over live video without covering the hand. Its
              tint follows the live range cue (in-range vs too close/far) so the
              frame itself signals whether the hand is well placed. Purely
              decorative (pointer-events none, aria-hidden) — the pills below carry
              the accessible status. */}
          {isActive && isMediaPipe && (
            <div
              className="motion-sandbox-zone"
              data-range={feedback.range}
              aria-hidden="true"
            >
              <span className="motion-sandbox-zone-frame" />
              <span className="motion-sandbox-zone-label">
                {feedback.range === "no-hand"
                  ? "Control zone"
                  : rangeCue.label}
              </span>
            </div>
          )}
          {!isActive && (
            <p className="motion-sandbox-preview-empty">
              {status === "inactive"
                ? "Camera off"
                : status === "requesting"
                  ? "Waiting for permission…"
                  : status === "error"
                    ? "Unavailable"
                    : "Stopped"}
            </p>
          )}
        </div>

        {!isMediaPipe && (
          <div className="motion-sandbox-debug">
            <span className="motion-sandbox-preview-label">Motion field</span>
            {/* Debug heatmap: the frame-difference buffer, upscaled by CSS. */}
            <canvas
              ref={debugCanvasRef}
              className="motion-sandbox-debug-canvas"
              width={PROC_W}
              height={PROC_H}
            />
          </div>
        )}
      </div>

      {/* Phase 32M — live control cues. Sits directly under the preview so the
          "is my hand doing the right thing" feedback is next to the video: hand
          range, tracking-confidence quality, the debounced control phase
          (warming/active/uncertain/idle), and the debounced pinch hold. MediaPipe
          mode only — the frame-difference fallback has no hand model. */}
      {isMediaPipe && (
        <div className="motion-sandbox-control" aria-live="polite">
          <h3 className="motion-sandbox-readout-title">Control status</h3>
          <div className="motion-sandbox-cues">
            <div className="motion-sandbox-cue" data-tone={rangeCue.tone}>
              <span className="motion-sandbox-cue-key">Range</span>
              <span className="motion-sandbox-cue-val">{rangeCue.label}</span>
            </div>
            <div className="motion-sandbox-cue" data-tone={qualityCue.tone}>
              <span className="motion-sandbox-cue-key">Confidence</span>
              <span className="motion-sandbox-cue-val">{qualityCue.label}</span>
            </div>
            <div className="motion-sandbox-cue" data-tone={controlCue.tone}>
              <span className="motion-sandbox-cue-key">Control</span>
              <span className="motion-sandbox-cue-val">{controlCue.label}</span>
            </div>
            <div className="motion-sandbox-cue" data-tone={pinchCue.tone}>
              <span className="motion-sandbox-cue-key">Pinch</span>
              <span className="motion-sandbox-cue-val">{pinchCue.label}</span>
            </div>
          </div>
        </div>
      )}

      {/* Off-DOM sampling buffer — never displayed, just read from. */}
      <canvas
        ref={procCanvasRef}
        width={PROC_W}
        height={PROC_H}
        style={{ display: "none" }}
      />

      {isMediaPipe && (
        <div className="motion-sandbox-detection" aria-live="polite">
          <h3 className="motion-sandbox-readout-title">Hand detection</h3>
          <dl className="motion-sandbox-metrics">
            <div>
              <dt>hand</dt>
              <dd>{handInfo.handDetected ? "detected" : "—"}</dd>
            </div>
            <div>
              <dt>handedness</dt>
              <dd>{handInfo.handedness ?? "—"}</dd>
            </div>
            <div>
              <dt>landmarks</dt>
              <dd>{handInfo.landmarkCount}</dd>
            </div>
            <div>
              <dt>score</dt>
              <dd>{handInfo.score ? handInfo.score.toFixed(3) : "—"}</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="motion-sandbox-readout" aria-live="polite">
        <div className="motion-sandbox-readout-head">
          <h3 className="motion-sandbox-readout-title">MotionCommand</h3>
          <span
            className={`motion-sandbox-state ${
              motion.active ? "is-active" : "is-idle"
            }`}
          >
            {motion.active ? "Active" : "Idle"}
          </span>
        </div>
        <dl className="motion-sandbox-metrics">
          <div>
            <dt>yawDelta</dt>
            <dd>
              {motion.yawDelta.toFixed(3)}
              <span className="motion-sandbox-hint">
                {describeDelta(motion.yawDelta, "← left", "right →")}
              </span>
            </dd>
          </div>
          <div>
            <dt>pitchDelta</dt>
            <dd>
              {motion.pitchDelta.toFixed(3)}
              <span className="motion-sandbox-hint">
                {describeDelta(motion.pitchDelta, "down", "up")}
              </span>
            </dd>
          </div>
          <div>
            <dt>zoomDelta</dt>
            <dd>
              {motion.zoomDelta.toFixed(3)}
              <span className="motion-sandbox-hint">
                {describeDelta(motion.zoomDelta, "out", "in")}
              </span>
            </dd>
          </div>
          <div>
            <dt>pinchActive</dt>
            <dd>{motion.pinchActive ? "true" : "false"}</dd>
          </div>
          <div>
            <dt>confidence</dt>
            <dd>{motion.confidence.toFixed(3)}</dd>
          </div>
          <div>
            <dt>source</dt>
            <dd>{motion.source}</dd>
          </div>
        </dl>
        {/* A tiny confidence meter so the value is legible at a glance. */}
        <div
          className="motion-sandbox-confidence"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={1}
          aria-valuenow={Number(motion.confidence.toFixed(2))}
          aria-label="Motion confidence"
        >
          <span
            className="motion-sandbox-confidence-fill"
            style={{ width: `${clamp(motion.confidence, 0, 1) * 100}%` }}
          />
        </div>
      </div>
    </section>
  );
}

export default MotionSandboxPanel;
