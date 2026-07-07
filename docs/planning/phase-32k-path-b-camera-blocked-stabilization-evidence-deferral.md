# Phase 32K Path B — Orbital Graph Control Camera-Blocked Stabilization + Evidence Deferral

> **Status:** Planning / documentation only. No implementation, no webcam code
> changes, no graph tuning, no screenshots, no fabricated evidence.
> **Parent branch:** `main` · **Owner label:** devdevbuilds · **Project:** Hive|Mind
> **Branch:** `phase-32k-path-b-camera-blocked-stabilization-evidence-deferral`

---

## 1. Executive summary

**Phase 32K Path B was selected because the host camera remains blocked.** After
Phase 32J defined the two possible Phase 32K tracks — Path A (evidence capture if
the camera works) or Path B (alternate input / continued deferral if it stays
blocked) — the deciding condition was tested and the host camera is still down:
native Windows Camera still cannot produce a live preview locally. That closes
Path A for now and selects **Path B**.

**The app's orbital graph control path exists, but live hand-motion feel is not
verified.** The opt-in, off-by-default, read-only orbital graph control is wired
and hardened in the frontend (Phases 32F → 32I). What has never happened is a
real, connected, hand-in-front-of-a-working-camera session that would let anyone
honestly say the gesture-to-graph feel is smooth. That verification is still
outstanding.

**No screenshot / video / live demo evidence should be captured until the system
camera works.** This is a blocker-isolation, documentation, and evidence-deferral
phase — not an implementation phase, not a screenshot phase, and not a
"pretend the webcam works" phase. It records the camera-blocked state honestly,
preserves the implemented work as *implemented-but-unverified*, and defines the
safest next recovery/evidence path without claiming any demo success.

---

## 2. Why this phase exists

**Preserving evidence integrity matters more than forcing a demo.** A portfolio
project's credibility comes from the fact that what it shows is real. Capturing a
staged, simulated, or "close enough" gesture-control clip to fill the evidence gap
would trade the one thing this project has consistently protected — honesty — for
a screenshot. A deferred-but-honest evidence posture is worth far more than a
fabricated success. So the correct move while the camera is down is to document
the gap, not paper over it.

**The blocker appears to be outside Hive|Mind app logic, because native Windows
Camera also fails.** If the failure were a Hive|Mind bug, a trusted, unrelated
camera consumer (the native Windows Camera app) would still work. It does not. A
camera stack that cannot produce a live preview even for a first-party OS app is
failing *below* the browser and *below* Hive|Mind. Phase 32I already hardened the
app-side startup lifecycle (constraint fallback, retry classifier, readiness
watchdog, actionable error copy, clean retry), and it now fails cleanly and
retryably — there is no evidence pointing at a Hive|Mind-side defect as the cause.

**A docs-only stabilization pass is the right move before further
implementation.** Tuning gains, dead zones, smoothing, or orbital math against a
camera that never delivers a frame is tuning against noise — you cannot honestly
tune the feel of a feature you cannot run. The responsible next step is to stop
implementing, record the blocker precisely, and define the recovery/evidence path,
so that when a working camera is available the team knows exactly what to verify
and capture. This phase does that and nothing more.

---

## 3. Current blocker state

A factual record of the blocker as it stands. It intentionally does not overclaim.

- **Native Windows Camera cannot produce a live preview.** The trusted OS baseline
  camera app does not deliver frames on this host.
- **Browser webcam access remains unreliable / blocked.** Because the OS-level
  camera stack is down, the browser layer (and therefore the Motion Sandbox) cannot
  obtain a live stream either.
- **Previous app-side diagnostics / retry handling were already hardened
  (Phase 32I).** A constraint fallback (explicit resolution → bare `video: true`),
  a retry classifier that only relaxes for "device wouldn't start" failures, a
  post-acquire readiness watchdog that waits for a decodable frame, cause-specific
  error copy, and a clean *Retry camera* affordance are all in place. The
  failure-and-retry lifecycle is verified; a *successful* live start is not.
- **No current proof that hand-motion graph control feels smooth in live use.**
  There is no real session in which a hand controlled the orbital camera through a
  working webcam.
- **No demo evidence should claim successful live gesture control.** Until a real
  camera session verifies it, any evidence claiming working live gesture control
  would be false. None is to be produced here.

There is no "it works" claim in this document, because there is no real live camera
evidence to support one.

---

## 4. What is already implemented

Summarized accurately, without overclaiming. These landed in prior phases and are
preserved as-is by this phase:

- **Standalone Motion Sandbox exists.** An isolated "Motion" dock pane that requests
  the webcam only on explicit user action (Phase 32B, merged).
- **MediaPipe Hand Landmarker mode exists.** A hand-landmark estimator as the
  primary detector, populating the hardened `MotionCommand` contract (Phase 32D,
  merged; pinned `@mediapipe/tasks-vision@0.10.35`).
- **Frame-difference fallback exists.** A zero-dependency `getUserMedia` + canvas
  frame-difference estimator, kept as a fallback / debug visualiser filling the same
  `MotionCommand` shape.
- **MotionCommand contract exists.** A hardened, normalized motion contract with
  explicit `active` / `source` / `timestamp` fields (Phase 32C).
- **Orbital graph control helper exists.** A separate, typed
  `OrbitalGraphControlCommand` graph-intent contract plus a deterministic,
  side-effect-free `MotionCommand` → graph-intent mapping helper with deadzone /
  confidence gating / clamp and fail-safe idle mapping (Phase 32F).
- **Opt-in graph camera transform wiring exists.** A single, off-by-default
  "Motion controls graph" switch routes motion through the helper to a pure
  `integrateOrbitalCamera` and a CSS transform on a view wrapper around the graph
  SVG (yaw→rotateY, pitch→rotateX, zoom→scale) (Phase 32G, merged via PR #123).
- **Recenter camera and stale-command safeguards exist.** An explicit *Recenter
  camera* control (snaps the pose face-on; visual only) and a staleness guard that
  treats an active-but-stale command like idle so a frozen frame decays to neutral
  instead of drifting (Phase 32H). Startup diagnostics/retry hardening followed in
  Phase 32I.
- **Graph data remains read-only.** Motion adjusts only the orbital camera; there
  is no node / edge / data / layout / selection / API mutation.
- **Motion control is experimental / off by default.** It is opt-in, clearly
  labeled experimental, and does nothing until a user explicitly enables it.

---

## 5. What remains unverified

These are the things a working-camera session would need to establish. None of them
are verified today:

- **Real camera startup on this host** — a live preview actually appearing.
- **Real hand landmark stream stability** — MediaPipe initializing and tracking a
  hand steadily rather than flickering.
- **Gesture comfort** — whether the required hand poses are comfortable to hold.
- **Gesture-to-graph feel** — whether motion maps to orbital movement intuitively.
- **Push / pull zoom feel** — whether the zoom axis reads naturally.
- **Orbital rotation feel** — whether yaw/pitch rotation feels smooth and
  controllable rather than twitchy or drifting.
- **Demo recording viability** — whether the interaction is stable enough to record.
- **Portfolio-ready evidence capture** — whether any of it is presentable as honest
  portfolio evidence.

---

## 6. Blocker decision tree

The next step depends entirely on the local camera state.

### Path A — Windows Camera begins working

If native Windows Camera can produce a live preview again, proceed to **live
hand-motion QA and evidence capture**: exercise the Motion Sandbox and opt-in
orbital control end-to-end with a real hand, verify the feel, and capture honest
connected-runtime evidence per the deferred track.

### Path B — Windows Camera remains blocked *(current state)*

If native Windows Camera remains blocked, **keep evidence deferred and continue
system-level recovery** (see §7). Do not tune the app further against a broken
camera baseline, and do not capture or claim any live gesture evidence.

### Path C — Built-in camera blocked but an external USB webcam works

If the built-in camera stays blocked but an **external USB webcam** produces a live
preview, proceed with **external-camera live QA**, clearly documenting the exact
device used and that the built-in camera remained unavailable.

### Path D — All physical webcams remain blocked

If every physical webcam remains blocked, consider a future **non-camera synthetic
input harness** strictly for **dev testing only** — never for portfolio or demo
evidence. Any synthetic input must be labeled synthetic/dev-only wherever it
appears.

---

## 7. System-level recovery checklist

A practical, non-destructive checklist. **These steps are not claimed to have been
completed** — they are the recovery path to work through. Stop as soon as a trusted
app (native Windows Camera) shows a live preview.

- [ ] **Windows Camera app test** — the trusted baseline; if it cannot show live
      video, the problem is below the browser and below Hive|Mind.
- [ ] **Windows privacy camera permissions** — Settings → Privacy & security →
      Camera: confirm camera access is on for the system, for apps, and for desktop
      apps.
- [ ] **Browser site permissions reset** — reset and re-grant the camera permission
      for the local app origin on the next prompt.
- [ ] **Close apps that may hold the camera** — Discord, Teams, Zoom, OBS, and stray
      browser tabs; only one consumer may hold exclusive capture.
- [ ] **Device Manager disable / enable** — disable then re-enable the camera device
      to reset it.
- [ ] **Driver update / reinstall** — update or roll back the camera driver from a
      known-good source (roll back if a recent update correlates with the failure).
- [ ] **Windows Camera app reset / repair** — via Settings → Apps → Camera →
      Advanced options → Repair / Reset.
- [ ] **Windows Frame Server / camera service review** — confirm the camera
      `FrameServer` service is running and not stuck.
- [ ] **Test with a different browser** — e.g. Edge as a second Chromium-based
      browser, and/or a clean browser profile, to isolate profile/browser issues.
- [ ] **Test with an external USB webcam** — an alternate device on a direct port
      (avoid unpowered hubs); if it works, this is Path C.
- [ ] **Optional: Windows update / OEM driver review** — check for pending OS updates
      or an OEM-provided camera driver.

> None of these steps are destructive. Do not run risky registry edits, forced
> driver deletions, or system-file operations as part of this checklist.

---

## 8. Evidence policy

While the camera is blocked and forward until a real camera session verifies the
feature:

- **No fake screenshots.** Do not stage, mock, or composite gesture-control imagery.
- **No simulated hand-motion evidence labeled as real.** Any synthetic or replayed
  input must never be presented as a live camera session.
- **No claim that live gesture control works** until a real camera session verifies
  it end-to-end.
- **If an external camera is used later, the evidence must say so** — naming the
  device and noting that the built-in camera was unavailable.
- **If synthetic input is added later, it must be labeled synthetic / dev-only**
  wherever it appears, and never counted as portfolio/demo evidence.

---

## 9. Recommended next phase

Depending on the local camera state at the start of the next phase, recommend one
of:

- **Phase 32L Path A — Live Camera Restored Orbital Control QA + Portfolio Evidence
  Capture** — if the built-in Windows camera is working again.
- **Phase 32L Path B — External USB Webcam Validation Pass** — if the built-in
  camera remains blocked but external-camera testing is viable.
- **Phase 32L Path C — Dev-Only Synthetic Motion Harness Planning** — if all
  physical webcams remain blocked.

**Preferred recommendation while the camera remains blocked:**
**Phase 32L Path B — External USB Webcam Validation Pass.** An external USB webcam
is the least invasive way to obtain a real live camera session without waiting on
host-camera-stack recovery, and it keeps any resulting evidence honest as long as
the device used is documented.

---

## 10. Guardrails

Held for this phase and forward until deliberately revised:

- **No frontend / source behavior changes.**
- **No backend / API / schema / persistence changes.**
- **No package / dependency changes.**
- **No MediaPipe changes.**
- **No graph mutation.** The graph stays read-only; only the orbital camera moves.
- **No fake data.**
- **No screenshots / videos unless real and verified.**
- **No portfolio success claim for live hand-motion control.**
- **No broad README rewrite.**
- **No dashboard / sidebar / card-grid redesign.**
