# Phase 32J — Orbital Graph Control System-Camera Recovery Planning + Deferred Evidence Track

> **Status:** Planning / documentation only. No implementation, no webcam code
> changes, no graph tuning, no screenshots, no fabricated evidence.
> **Parent branch:** `main` · **Owner label:** devdevbuilds · **Project:** Hive|Mind

---

## 1. Executive summary

Phase 32J is a **planning-only recovery and evidence-track phase** that follows
Phase 32I. Its job is not to build anything. Its job is to record, honestly, the
state of the opt-in orbital graph control feature after Phase 32I hardened the
app-side camera startup lifecycle — and to define the plan for restoring the
**host operating system's camera stack** so that real, connected runtime evidence
can eventually be captured.

The feature direction is preserved and unchanged: motion-controlled, opt-in,
read-only orbital navigation of the Knowledge Graph. What has changed is only our
understanding of the blocker. After Phase 32I we can say with confidence that the
remaining obstacle is **outside the Hive|Mind app** — the local camera stack does
not currently produce a live preview even in a trusted, non-Hive camera consumer
(native Windows Camera). Because of that, this phase deliberately avoids any
further tuning of the app against a broken camera baseline, and it defines the
gate that must be satisfied before evidence capture resumes.

Nothing in this document should be read as a claim that live hand-motion control
was observed working. It has not been. This phase preserves the direction while
being explicit about what is still deferred.

---

## 2. Current known state

The following is a factual record of where the feature stands. It intentionally
does not overclaim.

- **Phase 32D** — added **MediaPipe Hand Landmarker** support to the Motion
  Sandbox as the primary detector, keeping the earlier frame-difference estimator
  as a zero-dependency fallback. Both fill the same hardened `MotionCommand`
  contract. (frontend-only, merged into `main`)
- **Phase 32G** — wired the **first opt-in orbital graph control**: a single
  off-by-default switch routes Motion Sandbox output through the pure Phase 32F
  helper to a CSS-transform orbital camera around the graph SVG. The graph stays
  read-only. (frontend-only, merged into `main` via PR #123)
- **Phase 32H** — **tuned usability** and added recovery controls/copy: gentler
  yaw/pitch/zoom gains, a wider dead zone, a staleness guard, an explicit
  *Recenter camera* control, and clearer *experimental / opt-in / read-only*
  wording. (frontend-only, merged into `main` via PR #124)
- **Phase 32I** — **hardened camera startup diagnostics and retry handling**: a
  constraint fallback (explicit resolution → bare `video: true`), a retry
  classifier that only relaxes for "device wouldn't start" failures, a post-acquire
  readiness watchdog that waits for a decodable frame before declaring the camera
  active, cause-specific actionable error copy, and a clean *Retry camera*
  affordance. (frontend-only, merged into `main` via PR #125)
- **Native Windows Camera still cannot produce a live preview locally.** The host
  camera stack — independent of Hive|Mind — does not deliver frames.
- **No final orbital graph hand-motion evidence exists yet.** The
  failure-and-retry lifecycle is verified; a *successful* live camera start with a
  real hand has **not** been verified on this host.

There is no "it works" claim here, because there is no real live camera evidence
to support one.

---

## 3. System-camera blocker classification

The remaining blocker is classified as follows:

- **Host / system camera stack issue.** The camera does not produce a live
  preview at the operating-system level, ahead of and independent of any browser
  or Hive|Mind involvement.
- **Not currently proven to be a Hive|Mind frontend bug.** Phase 32I hardened the
  app-side lifecycle and confirmed the app now fails cleanly and retryably. There
  is no evidence pointing at a Hive|Mind-side defect as the cause of the missing
  preview.
- **Evidence is blocked** until **native Windows Camera — or another trusted local
  camera consumer — can produce a live preview.** Until a non-Hive camera app can
  show live video, the app cannot be exercised end-to-end, and no honest evidence
  can be captured.

**The app should not be tuned further against a broken camera baseline.** Tuning
gains, dead zones, smoothing, or orbital math against a camera that never delivers
frames would be tuning against noise. The correct next move is host-side recovery,
not more app changes.

---

## 4. Recovery checklist

A practical, non-destructive recovery checklist for the host camera, grouped by
level. Work top to bottom; stop as soon as a trusted app (e.g. native Windows
Camera) shows a live preview.

### Level 1 — Basic OS checks

- Check **Windows privacy camera permissions** (Settings → Privacy & security →
  Camera): confirm camera access is on for the system, for apps, and for desktop
  apps.
- Check the **browser's camera permission** at the OS level (the browser must be
  allowed to use the camera).
- **Confirm the correct camera is selected** in the browser's site settings /
  device picker.
- **Restart the browser** fully (all windows/processes).
- **Restart the machine.**
- **Test the native Windows Camera app** — this is the trusted baseline. If it
  cannot show live video, the problem is below the browser and below Hive|Mind.

### Level 2 — Windows services / device stack

- Check **Windows Camera Frame Server** behavior (the `FrameServer` service that
  brokers camera access); confirm it is running and not stuck.
- In **Device Manager**, disable then re-enable the camera device to reset it.
- Consider a **driver update or rollback** for the camera device (use a known-good
  driver source; roll back if a recent update correlates with the failure).
- Check for **competing apps holding the camera** — Discord, Teams, Zoom, OBS, or
  a background browser tab. Only one consumer may need exclusive capture.
- **Confirm no camera process is monopolizing capture** (close background apps and
  re-test the native camera).

### Level 3 — Browser-specific checks

- **Reset Chrome's camera permission** for the local app origin and re-grant on
  the next prompt.
- **Test in Edge** as a second Chromium-based browser to isolate profile/browser
  issues.
- **Test a clean browser profile** (fresh profile with default permissions).
- **Test the local app URL's permissions** explicitly (allow camera for the dev
  origin).
- **Do not assume a Vite / app failure** until a non-Hive camera app (native
  Camera or a neutral WebRTC test page) works. The browser layer is only worth
  debugging once the OS layer is proven healthy.

### Level 4 — Hardware / alternate capture path

- Try an **external USB webcam** as an alternate device.
- Try a **different USB port** (and avoid unpowered hubs).
- Consider **phone-as-webcam or a virtual camera** only as a *later* fallback, not
  a first move.
- If available, try **another machine** to confirm whether the issue is host-bound.

> None of these steps are destructive. Do not run risky registry edits, forced
> driver deletions, or system-file operations as part of this checklist.

---

## 5. Evidence gate

Screenshot / video evidence capture may resume **only** when **all** of the
following are true:

- **Native Windows Camera — or another trusted app — shows a live preview.**
- The **browser permission prompt works** (appears and can be granted).
- The **Motion Sandbox receives live video** (a real preview, not a black frame).
- The **MediaPipe hand landmark mode initializes** without error.
- **Hand landmarks are visible**, or command values update in the readout.
- **Orbital graph control remains opt-in** (off by default; enabled explicitly).
- The **graph remains read-only / non-mutating** (no node/edge/data/layout/
  selection/API change).

If any one of these is not satisfied, the gate is closed and evidence remains
deferred.

---

## 6. Deferred evidence track

Once the camera works and the gate in §5 is satisfied, the following evidence
should be captured. **None of this is to be created in Phase 32J.**

- Motion Sandbox **idle / off** state.
- Motion Sandbox **camera active** state.
- **MediaPipe landmark detection** state.
- **Open-hand gesture** command readout.
- **Pinch / zoom** command readout — *only if reliable*.
- **Graph control disabled** state.
- **Graph control enabled (opt-in)** state.
- **Orbital graph moved / rotated** state.
- **Recenter camera** control state.
- Any **limitation notes** (jitter, latency, false detections, lighting
  sensitivity).

> Explicitly: these captures must **not** be produced during Phase 32J. This phase
> defines *what* to capture later; it captures nothing.

---

## 7. Feature guardrails

These guardrails hold for this phase and forward until deliberately revised:

- **No graph mutation.** The graph stays read-only; only the orbital camera moves.
- **No AI / LLM hand interpretation.** Motion mapping stays deterministic.
- **No automatic camera start.** The camera is explicit-start only.
- **No camera capture storage.** No frames are recorded, saved, or transmitted.
- **No screenshot / video fabrication.** Evidence must be real or absent.
- **No portfolio claim without real evidence.** See §9.
- **No dashboard / sidebar / card-grid redesign.**
- **No new graph library.**
- **No dependency changes.**

---

## 8. Recommended next-phase decision

Two mutually exclusive tracks are defined for **Phase 32K**. The choice depends on
whether the host camera recovers.

### Path A — Phase 32K: Camera Recovery Verification + Evidence Capture

Use this **only if the system camera works again** (the §5 gate opens).

Scope:

- Capture **real connected runtime evidence** per the §6 deferred track.
- **Verify the Motion Sandbox** end-to-end with live video.
- **Verify the orbital graph control feel** with real hand motion.
- **Document limitations honestly** (jitter, latency, lighting, false positives).

### Path B — Phase 32K: Alternate Camera Input / Fallback Feasibility Planning

Use this **if the system camera remains blocked**.

Scope:

- **Research a second webcam** (external USB device) as an alternate capture path.
- **Test an alternate browser** to isolate browser-layer issues.
- **Consider phone-as-webcam** as a last-resort input path.
- **Keep app source untouched** unless a confirmed app-side bug is found.

---

## 9. Portfolio wording lock

Safe, approved wording for portfolio / demo docs while evidence is deferred:

**Approved:**

```text
Hive|Mind includes an experimental opt-in motion-control path for orbital graph
navigation. App-side camera diagnostics and read-only graph control wiring are
implemented, while live hand-motion evidence remains deferred pending host camera
recovery.
```

**Disallowed:**

```text
Fully working gesture control.
Production-ready camera navigation.
Live hand-tracked graph control verified.
```

Until the §5 gate opens and real evidence exists, only the approved wording may be
used.

---

## 10. Final recommendation

**Pause implementation changes** until the host camera is restored or an alternate
camera path is tested. The app has already been hardened enough for the current
blocker: Phase 32I gave the startup lifecycle a clean, classified, retryable
failure path, and there is nothing more to tune honestly against a camera that
does not deliver frames.

The correct next action is **host-side recovery** (the §4 checklist), followed by
the appropriate Phase 32K track — **Path A** if the camera works, **Path B** if it
remains blocked. Do not fabricate evidence, and do not make a working-gesture claim
until the §5 evidence gate is genuinely satisfied.
