import { useCallback, useEffect, useRef, useState } from "react";

/* Phase 32B — Standalone Webcam Motion Sandbox.

   This is the first real implementation step toward future motion-controlled
   graph interaction, but it is deliberately isolated: it NEVER touches the
   knowledge graph, never requests the camera on mount, and never auto-starts
   the stream. It exists only to prove the frontend can (1) ask for webcam
   access after explicit user action, (2) run a browser-side frame/motion loop,
   (3) derive a normalized MotionCommand, and (4) surface those values for
   inspection — then stop the stream cleanly.

   Approach is intentionally dependency-free (Phase 32B safer default): raw
   getUserMedia + HTMLVideoElement + canvas frame-difference + requestAnimation-
   Frame. No MediaPipe, no package/dependency changes. The MotionCommand shape
   follows the Phase 32A planning contract so a later phase can lift the same
   object straight into a graph controller without reshaping it. */

/** The detection backend that produced a command. Phase 32B/32C ship only the
    dependency-free frame-difference estimator, but the field is modelled as a
    union so a later phase (e.g. MediaPipe hand landmarks) can tag its own output
    without breaking the consumer contract. */
type MotionSource = "frame-difference";

/** Phase 32C hardened motion-control contract.

    This is the single object a future graph controller will consume, so its
    semantics are fixed here. Phase 32C DEFINES the contract; it deliberately
    does NOT wire it to any graph behaviour — every field below describes intent
    only, and nothing in this file mutates the knowledge graph.

    Directional deltas are normalized to -1..1 and expressed as *intent*, not as
    applied transforms:

      yawDelta    Horizontal rotation intent.
                    Negative → rotate graph left.
                    Positive → rotate graph right.
                    Zero     → no horizontal rotation intent.
      pitchDelta  Vertical rotation intent.
                    Negative → rotate graph downward / backward.
                    Positive → rotate graph upward / forward.
                    Zero     → no vertical rotation intent.
      zoomDelta   Depth / zoom intent.
                    Negative → pull graph outward / zoom out.
                    Positive → push graph inward / zoom in.
                    Zero     → no zoom intent.
                  Frame-difference cannot infer depth, so this stays 0 in 32C.

      pinchActive Discrete "grab" gesture flag. No hand model in 32C → always
                  false; reserved for a landmark-based phase.
      confidence  0..1 strength of the detected motion signal.
      active      Idle/active bit: true once confidence clears MOTION_GATE. A
                  consumer would gate on this before applying any delta.
      source      Which estimator produced this command (frame-difference).
      timestamp   performance.now() of the frame this command was derived from,
                  so a consumer can rate-limit or measure staleness. */
type MotionCommand = {
  yawDelta: number;
  pitchDelta: number;
  zoomDelta: number;
  pinchActive: boolean;
  confidence: number;
  active: boolean;
  source: MotionSource;
  timestamp: number;
};

/** Lifecycle of the camera, surfaced to the user as a status chip. */
type CameraStatus =
  | "inactive" // never started (or fully reset) — no permission asked yet
  | "requesting" // getUserMedia in flight, waiting on the permission prompt
  | "active" // stream live, motion loop running
  | "stopped" // user stopped a previously-active stream
  | "error"; // permission denied / no device / stream failure

const ZERO_MOTION: MotionCommand = {
  yawDelta: 0,
  pitchDelta: 0,
  zoomDelta: 0,
  pinchActive: false,
  confidence: 0,
  active: false,
  source: "frame-difference",
  timestamp: 0,
};

// Direction hints in the readout only render once a delta clears this small
// magnitude, so near-zero jitter reads as "—" instead of flickering left/right.
const DIRECTION_HINT_EPS = 0.05;

// Downscaled processing resolution. Frame-difference is O(pixels) per frame, so
// we sample a tiny 4:3 buffer rather than the full preview — cheap enough for a
// 60fps loop while still resolving where motion happens in the frame.
const PROC_W = 96;
const PROC_H = 72;

// A per-pixel grayscale delta below this (0..255) is treated as sensor noise and
// ignored, so a perfectly still frame reads as zero motion instead of shimmer.
const NOISE_FLOOR = 18;

// Maps the fraction-of-frame-in-motion into a 0..1 confidence. Hand-waving lights
// up only a slice of the frame, so a small fraction should already read as high
// confidence; the result is clamped to 1.
const CONFIDENCE_GAIN = 8;

// Below this confidence the directional deltas are forced to zero — otherwise a
// still frame's noise centroid would jitter yaw/pitch around the origin.
const MOTION_GATE = 0.06;

// Exponential-moving-average factor for the emitted command. Lower = smoother /
// laggier. Keeps the inspected values readable instead of strobing each frame.
const SMOOTHING = 0.28;

// React re-render throttle for the readout. The RAF loop runs every frame, but
// pushing 60 setState/sec is wasteful and unreadable; ~12Hz is plenty for eyeball
// inspection while the debug canvas still repaints every frame.
const READOUT_INTERVAL_MS = 80;

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

function MotionSandboxPanel({ id }: { id?: string }) {
  const [status, setStatus] = useState<CameraStatus>("inactive");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [motion, setMotion] = useState<MotionCommand>(ZERO_MOTION);

  // Live-object refs: none of these should trigger a re-render when they change.
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const debugCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const procCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const prevGrayRef = useRef<Float32Array | null>(null);
  // Smoothed command carried across frames (the value we EMA toward).
  const smoothedRef = useRef<MotionCommand>(ZERO_MOTION);
  const lastReadoutRef = useRef<number>(0);

  // Tear down every live resource. Safe to call repeatedly (idempotent) — used
  // by the Stop button, error paths, and unmount cleanup alike.
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
  }, []);

  // The per-frame motion loop. Reads the (mirrored) video into the tiny proc
  // canvas, diffs it against the previous frame, and derives a MotionCommand
  // from where — and how much — the frame changed.
  const runFrame = useCallback(() => {
    const video = videoRef.current;
    const procCanvas = procCanvasRef.current;
    if (!video || !procCanvas || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(runFrame);
      return;
    }

    const procCtx = procCanvas.getContext("2d", { willReadFrequently: true });
    if (!procCtx) {
      rafRef.current = requestAnimationFrame(runFrame);
      return;
    }

    // Draw mirrored so the sampled pixels match the mirrored preview the user
    // sees — otherwise leftward hand motion would report as rightward yaw.
    procCtx.save();
    procCtx.scale(-1, 1);
    procCtx.drawImage(video, -PROC_W, 0, PROC_W, PROC_H);
    procCtx.restore();

    const { data } = procCtx.getImageData(0, 0, PROC_W, PROC_H);
    const pixelCount = PROC_W * PROC_H;
    const gray = new Float32Array(pixelCount);
    const prev = prevGrayRef.current;

    // Motion accumulators: total energy + intensity-weighted centroid.
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
      // Rec. 601 luma — cheap perceptual grayscale.
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
        // Heatmap: motion glows in the accent hue, still pixels stay dark.
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

    // Normalized motion energy: average per-pixel delta as a fraction of full
    // scale, amplified into a 0..1 confidence.
    const avgEnergy = motionSum / (pixelCount * 255);
    const confidence = clamp(avgEnergy * CONFIDENCE_GAIN, 0, 1);

    let yawDelta = 0;
    let pitchDelta = 0;
    if (motionSum > 0 && confidence >= MOTION_GATE) {
      // Centroid of motion in 0..1, then re-centered to -1..1.
      const cx = weightX / motionSum / PROC_W;
      const cy = weightY / motionSum / PROC_H;
      // Preview + sampling canvas are both mirrored, so a larger cx is the
      // user's right → positive yaw (matches the MotionCommand contract).
      yawDelta = clamp((cx - 0.5) * 2, -1, 1);
      // Image y grows downward, but the contract defines positive pitch as
      // "up". Invert here so upward hand motion (motion concentrated near the
      // top of the frame, small cy) reports as a positive pitchDelta — keeping
      // the sandbox output faithful to the documented semantics.
      pitchDelta = clamp((0.5 - cy) * 2, -1, 1);
    }

    const now = performance.now();

    // Phase 32C contract: zoom stays 0 (frame-difference has no depth proxy) and
    // pinch is always false (no landmark/hand model). Only yaw/pitch/confidence
    // are live signals; active/source/timestamp are metadata for a future
    // consumer. Nothing here touches the graph.
    const target: MotionCommand = {
      yawDelta,
      pitchDelta,
      zoomDelta: 0,
      pinchActive: false,
      confidence,
      active: confidence >= MOTION_GATE,
      source: "frame-difference",
      timestamp: now,
    };

    const prevCmd = smoothedRef.current;
    const smoothedConfidence =
      prevCmd.confidence + (target.confidence - prevCmd.confidence) * SMOOTHING;
    const smoothed: MotionCommand = {
      yawDelta: prevCmd.yawDelta + (target.yawDelta - prevCmd.yawDelta) * SMOOTHING,
      pitchDelta:
        prevCmd.pitchDelta + (target.pitchDelta - prevCmd.pitchDelta) * SMOOTHING,
      zoomDelta: 0,
      pinchActive: false,
      confidence: smoothedConfidence,
      // Metadata is discrete, not smoothed. `active` tracks the SMOOTHED
      // confidence so it agrees with the value shown in the readout.
      active: smoothedConfidence >= MOTION_GATE,
      source: "frame-difference",
      timestamp: now,
    };
    smoothedRef.current = smoothed;

    // Throttle the React readout so we render ~12Hz, not 60Hz.
    if (now - lastReadoutRef.current >= READOUT_INTERVAL_MS) {
      lastReadoutRef.current = now;
      setMotion(smoothed);
    }

    rafRef.current = requestAnimationFrame(runFrame);
  }, []);

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

    setErrorMessage(null);
    setStatus("requesting");
    setMotion(ZERO_MOTION);
    smoothedRef.current = ZERO_MOTION;
    prevGrayRef.current = null;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      streamRef.current = stream;

      const video = videoRef.current;
      if (!video) {
        // Component unmounted mid-request — don't leave the device on.
        for (const track of stream.getTracks()) {
          track.stop();
        }
        streamRef.current = null;
        return;
      }

      video.srcObject = stream;
      await video.play();

      setStatus("active");
      lastReadoutRef.current = 0;
      rafRef.current = requestAnimationFrame(runFrame);
    } catch (streamError: unknown) {
      teardown();
      setStatus("error");
      // Normalize the common getUserMedia rejections into plain language.
      const name =
        streamError instanceof DOMException ? streamError.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setErrorMessage(
          "Camera permission was denied. Allow camera access and try again.",
        );
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setErrorMessage("No camera device was found on this machine.");
      } else if (name === "NotReadableError") {
        setErrorMessage(
          "The camera is already in use by another application.",
        );
      } else {
        setErrorMessage(
          streamError instanceof Error
            ? streamError.message
            : "Could not start the camera.",
        );
      }
    }
  }, [runFrame, status, teardown]);

  const stopCamera = useCallback(() => {
    teardown();
    setStatus("stopped");
    setMotion(ZERO_MOTION);
  }, [teardown]);

  // Safety net: if the panel unmounts (or the app closes) while the camera is
  // live, release the device — a hung camera light is a trust-killer.
  useEffect(() => teardown, [teardown]);

  const isActive = status === "active";
  const isBusy = status === "requesting";

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

  return (
    <section className="motion-sandbox" id={id}>
      <h2>Motion Sandbox</h2>
      <p className="motion-sandbox-intro">
        Standalone webcam motion probe (Phase 32B, contract hardened in 32C).
        Nothing starts until you press <strong>Start Camera</strong>, and this
        surface never touches the knowledge graph — it only derives and displays
        a normalized <code>MotionCommand</code> for inspection. Source estimator:{" "}
        <code>frame-difference</code>.
      </p>

      <div className="motion-sandbox-statusrow">
        <p className={`status-pill ${statusChip.className}`}>
          <span className="status-dot" aria-hidden="true" />
          {statusChip.label}
        </p>
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
      </div>

      {/* Off-DOM sampling buffer — never displayed, just read from. */}
      <canvas
        ref={procCanvasRef}
        width={PROC_W}
        height={PROC_H}
        style={{ display: "none" }}
      />

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
