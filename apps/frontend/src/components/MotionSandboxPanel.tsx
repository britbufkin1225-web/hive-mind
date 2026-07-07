import { useCallback, useEffect, useRef, useState } from "react";
import type {
  HandLandmarker as HandLandmarkerInstance,
  HandLandmarkerResult,
} from "@mediapipe/tasks-vision";
import {
  deriveHandCommand,
  HAND_CONNECTIONS,
  LM,
  PINCH_RATIO_THRESHOLD,
  ZERO_MOTION,
  type Landmark,
  type MotionCommand,
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
// normalized 0..1, so this only sets draw crispness, not alignment.
const OVERLAY_W = 320;
const OVERLAY_H = 240;

function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
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

  // Draw the detected hand skeleton onto the overlay canvas. Lightweight debug
  // aid: bone lines + landmark dots, with thumb/index tips highlighted when a
  // pinch is active so the derivation is easy to eyeball. Coords are normalized;
  // the canvas is CSS-mirrored to match the mirrored preview.
  const drawOverlay = useCallback(
    (landmarks: Landmark[], pinchActive: boolean) => {
      const overlay = overlayCanvasRef.current;
      const octx = overlay?.getContext("2d") ?? null;
      if (!overlay || !octx) return;

      const w = overlay.width;
      const h = overlay.height;
      octx.clearRect(0, 0, w, h);

      octx.lineWidth = 2;
      octx.strokeStyle = "rgba(139, 124, 240, 0.85)";
      octx.beginPath();
      for (const [a, b] of HAND_CONNECTIONS) {
        const pa = landmarks[a];
        const pb = landmarks[b];
        if (!pa || !pb) continue;
        octx.moveTo(pa.x * w, pa.y * h);
        octx.lineTo(pb.x * w, pb.y * h);
      }
      octx.stroke();

      for (let i = 0; i < landmarks.length; i += 1) {
        const p = landmarks[i];
        const isTip = i === LM.THUMB_TIP || i === LM.INDEX_TIP;
        octx.beginPath();
        octx.arc(p.x * w, p.y * h, isTip ? 4 : 2.5, 0, Math.PI * 2);
        octx.fillStyle =
          isTip && pinchActive ? "rgba(122, 240, 170, 0.95)" : "#c9c2ff";
        octx.fill();
      }
    },
    [],
  );

  // Push a smoothed command to the throttled React readout (~12Hz). Phase 32G:
  // the freshest command is also forwarded to the optional sink every frame
  // (unthrottled) so a graph consumer gets per-frame motion; only the on-screen
  // readout stays throttled. The forward is a ref write in App, so it never
  // re-renders anything here regardless of whether graph control is on.
  const publishReadout = useCallback((smoothed: MotionCommand, now: number) => {
    onMotionCommandRef.current?.(smoothed);
    if (now - lastReadoutRef.current >= READOUT_INTERVAL_MS) {
      lastReadoutRef.current = now;
      setMotion(smoothed);
    }
  }, []);

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

  // --- MediaPipe hand-landmarker estimator (Phase 32D) -----------------------
  // Runs the detector on the raw video (never mirrored input; x is mirrored in
  // the derivation to match the preview). Skips stalled/duplicate frames and
  // guarantees strictly-increasing timestamps for detectForVideo.
  const runMediaPipe = useCallback((now: number) => {
    const video = videoRef.current;
    const landmarker = handLandmarkerRef.current;
    // Detector not ready (still loading or failed) — emit a tagged idle command
    // so the readout stays honest instead of freezing on stale values.
    if (!video || !landmarker) {
      const prevCmd = smoothedRef.current;
      const smoothed: MotionCommand = {
        ...MEDIAPIPE_IDLE,
        confidence: prevCmd.confidence + (0 - prevCmd.confidence) * SMOOTHING,
        timestamp: now,
      };
      smoothedRef.current = smoothed;
      publishReadout(smoothed, now);
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
      const prevCmd = smoothedRef.current;
      const smoothed: MotionCommand = {
        ...MEDIAPIPE_IDLE,
        confidence: prevCmd.confidence + (0 - prevCmd.confidence) * SMOOTHING,
        timestamp: now,
      };
      smoothedRef.current = smoothed;
      publishReadout(smoothed, now);
      drawOverlay([], false);
      if (now - lastReadoutRef.current < READOUT_INTERVAL_MS) return;
      setHandInfo(NO_HAND);
      return;
    }

    const landmarks = result.landmarks[0] as Landmark[];
    const category = result.handedness[0]?.[0];
    const handedness = category?.categoryName ?? null;
    const score = category?.score ?? 0;

    const target = deriveHandCommand(landmarks, score, now);

    // Smooth the continuous fields; keep the discrete pinch/active from target so
    // the "grab" flag stays crisp rather than smearing across the threshold.
    const prevCmd = smoothedRef.current;
    const smoothed: MotionCommand = {
      yawDelta: prevCmd.yawDelta + (target.yawDelta - prevCmd.yawDelta) * SMOOTHING,
      pitchDelta: prevCmd.pitchDelta + (target.pitchDelta - prevCmd.pitchDelta) * SMOOTHING,
      zoomDelta: prevCmd.zoomDelta + (target.zoomDelta - prevCmd.zoomDelta) * SMOOTHING,
      pinchActive: target.pinchActive,
      confidence: prevCmd.confidence + (target.confidence - prevCmd.confidence) * SMOOTHING,
      active: target.active,
      source: "mediapipe-hand-landmarker",
      timestamp: now,
    };
    smoothedRef.current = smoothed;

    drawOverlay(landmarks, target.pinchActive);
    publishReadout(smoothed, now);

    if (now - lastReadoutRef.current < READOUT_INTERVAL_MS) return;
    setHandInfo({
      handDetected: true,
      handedness,
      landmarkCount: landmarks.length,
      score,
    });
  }, [drawOverlay, publishReadout]);

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
    smoothedRef.current =
      activeMode === "mediapipe-hand-landmarker" ? MEDIAPIPE_IDLE : ZERO_MOTION;
    prevGrayRef.current = null;
    lastVideoTimeRef.current = -1;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
    } catch (streamError: unknown) {
      teardown();
      if (!mountedRef.current) return;
      setStatus("error");
      const name = streamError instanceof DOMException ? streamError.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setErrorMessage(
          "Camera permission was denied. Allow camera access and try again.",
        );
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setErrorMessage("No camera device was found on this machine.");
      } else if (name === "NotReadableError") {
        setErrorMessage("The camera is already in use by another application.");
      } else {
        setErrorMessage(
          streamError instanceof Error ? streamError.message : "Could not start the camera.",
        );
      }
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
          {isBusy ? "Starting…" : "Start Camera"}
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

      {/* Phase 32G — explicit, opt-in graph wiring. Off by default; the webcam
          never drives the graph just because this panel is open. Enabling it
          routes the derived MotionCommand to the Knowledge Graph's camera as a
          read-only, visual-only transform (the graph's nodes, edges, data, and
          selection are never touched). */}
      <div className="motion-sandbox-graphctrl">
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
        <p className="motion-sandbox-graphctrl-hint">
          {graphControlEnabled
            ? "Enabled — hand motion orbits, tilts, and zooms the graph camera only. The graph stays read-only; it recentres when motion stops."
            : "Off — the graph ignores motion entirely. Enable to let hand motion move the graph camera (visual only)."}
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
