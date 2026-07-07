# Hive|Mind Roadmap

This roadmap explains what Hive|Mind can do now, what is demo-only, and what
should remain future work. It complements the per-phase summary table in the
[README](../README.md), the [Intelligence Surface Plan](intelligence-surface-plan.md),
the portfolio-facing [Demo Guide](demo-guide.md), the canonical
[Final Demo Script](demo/final-demo-script.md) and
[Portfolio Presentation Lock](demo/portfolio-presentation-lock.md), and the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md),
and the [Phase 14E Dreaming Suggestions E2E Evidence](qa/phase-14e-dreaming-suggestions-e2e-evidence.md), and the [Phase 15E Provenance Chains QA Evidence](qa/phase-15e-provenance-chains-qa-evidence.md), and the [Phase 17A Intelligence Report Cohesion + System Readiness Plan](intelligence-report-cohesion-readiness-plan.md),
and the [Phase 17B Intelligence Report Cohesion Hardening + Readiness QA](phase-17b-intelligence-cohesion-hardening.md),
and the [Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md),
and the [Phase 18C Backend API Security Regression QA + Evidence](security/phase-18c-backend-api-security-regression-qa.md),
and the [Phase 18D API Edge Case Hardening Planning / Deferred Security Scope Triage](security/phase-18d-api-edge-case-hardening-planning.md),
and the [Phase 18E API Edge Case Defensive Validation MVP](security/phase-18e-api-edge-case-defensive-validation.md),
and the [Phase 18F API Edge Case Security Regression QA + Evidence](security/phase-18f-api-edge-case-security-regression-qa.md),
and the [Phase 19A Security Cohesion + Release Readiness Planning](security/phase-19a-security-cohesion-release-readiness-planning.md),
and the [Phase 19B Release Readiness QA + Demo Evidence Pass](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md),
and the [Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](release-readiness/phase-20a-demo-release-candidate-planning.md),
and the [Phase 20B Final README + Portfolio Narrative Hardening](release-readiness/phase-20b-final-readme-portfolio-narrative-hardening.md),
and the [Phase 21D UI Demo Polish Planning / Dashboard Refinement Scope](phase-21d-ui-demo-polish-planning.md),
and the [Phase 22A UI Navigation + Demo Flow Planning](planning/phase-22a-ui-navigation-demo-flow-planning.md),
and the [Phase 22C UI Navigation QA + Screenshot Evidence Refresh](demo/phase-22c-ui-navigation-qa-screenshot-evidence.md),
and the [Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](demo/phase-23b-ui-readability-qa-screenshot-evidence.md),
and the [Phase 24A Portfolio Screenshot + README Visual Lock](demo/phase-24a-portfolio-screenshot-readme-visual-lock.md),
and the [Phase 25A Premium Visual Design System / Frontend Presentation Direction](ui/phase-25a-premium-visual-system-planning.md),
and the [Frontend Asset Contract + Icon Usage Planning](frontend-asset-contract.md),
and the [Phase 26C Graph Visual QA + Screenshot Evidence Refresh](demo/phase-26c-graph-visual-qa-screenshot-evidence.md),
and the [Phase 27A Graph-First App Shell Planning](ui/phase-27a-graph-first-app-shell-planning.md),
and the [Phase 27E Full-Viewfinder Graph Surface QA + Screenshot Evidence Refresh](demo/phase-27e-full-viewfinder-graph-surface-qa-screenshot-evidence.md),
and the [Phase 28A True Graph-Primary Surface + Overlay Contract](phase-28a-true-graph-primary-overlay-contract.md),
and the [Phase 30A Post-Polish Interaction Triage + Next Frontend Direction Planning](phase-30a-post-polish-interaction-triage.md),
and the [Phase 30C Interaction Recovery QA + Screenshot Evidence Refresh](demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md),
and the [Phase 31A Premium Graph Interaction + Portfolio Demo Direction Planning](planning/phase-31a-premium-graph-interaction-portfolio-demo-direction.md),
and the [Motion Sandbox Control Contract + 32C QA + 32D MediaPipe](motion-sandbox-control-contract.md),
and the [Phase 32E Orbital Graph Control Contract + Motion-to-Graph Wiring Planning](planning/phase-32e-orbital-graph-control-contract-motion-wiring.md),
and the [Phase 32J Orbital Graph Control System-Camera Recovery Planning + Deferred Evidence Track](planning/phase-32j-orbital-graph-control-system-camera-recovery-planning-deferred-evidence.md).

## Current status

**Current phase:** Phase 32J — Orbital Graph Control System-Camera Recovery
Planning + Deferred Evidence Track (**planning / documentation only**, on branch
`phase-32j-orbital-graph-control-system-camera-recovery-planning-deferred-evidence`).
Phase 32J is a **planning-only recovery/evidence-track phase** after Phase 32I. It
does not change any code. It honestly records that the opt-in orbital graph
control feature is wired, hardened, and still **experimental / opt-in / read-only**,
while the **local camera stack remains blocked outside the Hive|Mind app**: native
Windows Camera still cannot produce a live preview, so no live hand-motion evidence
exists yet. The phase classifies the blocker as a **host/system camera stack
issue** (not proven to be a Hive|Mind frontend bug), defines a graded, non-
destructive **camera recovery checklist**, locks an **evidence gate** that must be
satisfied before any screenshot/video capture resumes, defines the **deferred
evidence track** to capture *later*, restates the feature guardrails and the
approved **portfolio wording**, and sets the two possible next tracks — **Phase 32K
Path A** (evidence capture, if the camera works) or **Phase 32K Path B** (alternate
camera input / fallback planning, if it stays blocked). The recommendation is to
**pause implementation changes** until the host camera is restored or an alternate
path is tested; the app is already hardened enough for this blocker. No source,
runtime, package, API, schema, or MediaPipe change; no screenshots or fabricated
evidence. See the
[Phase 32J planning doc](planning/phase-32j-orbital-graph-control-system-camera-recovery-planning-deferred-evidence.md).

The preceding **Phase 32I** — Orbital Graph Control Live Stabilization +
Evidence Decision (**frontend-only**, merged into `main` via PR #125).
Phase 32I set out to run the **first real webcam/hand feel test** of the opt-in
orbital control and then either capture portfolio evidence (if smooth) or
stabilize (if rough). The live test was **blocked before any hand-feel testing
could happen**: the Motion Sandbox failed to start the camera with a raw browser
error — *"Timeout starting video source"* — landing in a *Camera error* state
with an *Unavailable* preview, so opt-in graph control was never reached. Per the
decision gate this is **Path A — Stabilization**, but deliberately scoped to
**camera/video startup reliability and diagnostics first, not graph tuning** — you
cannot honestly tune the feel of a feature that will not start. The 32I pass
hardens the startup lifecycle in `MotionSandboxPanel.tsx`: (1) a **constraint
fallback** — try an explicit `640×480` source, then retry once with bare
`video: true`, since some webcams/drivers stall on a specific resolution but start
unconstrained; (2) a **retry classifier** so only "device wouldn't start" failures
(`NotReadableError`/`AbortError`/`TimeoutError`/`OverconstrainedError`) fall through
to that relaxed retry, while permission/no-device failures surface immediately;
(3) a **post-acquire readiness watchdog** (`waitForVideoReady`) that waits for an
actual decodable frame (`loadeddata`/`canplay`) before declaring the camera
active, so a stream that resolves but never delivers frames now fails cleanly with
a clear error instead of a permanently black preview and a loop spinning on a
never-ready video; (4) **cause-specific, actionable error copy** for permission
denied, no device, device busy, timeout, and over-constrained cases (replacing the
raw browser string); and (5) a **clean retry affordance** — the button relabels to
*Retry camera* and the panel returns to a usable state after any failure, with no
stale streams left attached. Both detectors (frame-difference fallback and
MediaPipe hand landmarks) share this hardened path; MediaPipe still loads *after*
video start, so it never blocks or races the preview. **No graph gains, dead zone,
smoothing, or orbital-control math were changed**, and there is **no** backend,
API, schema, package, dependency, MediaPipe-model, or Vite/routing change.
**Honesty note (no faked evidence):** the *failure-and-retry* lifecycle is
verified — in a headless browser with permission denied, startup now yields a
clear, classified, retryable *Camera error* instead of a stuck state — but a
*successful* live camera start with a real hand **could not be verified in the
build agent's environment** (no webcam available to it). The real webcam/hand
feel test, and any portfolio evidence capture, therefore remain **pending a human
retry** on a machine with a working camera; nothing here should be read as a
claim that live hand-motion control was observed working. Phase 32J (this planning
phase) records the resulting deferred-evidence posture and the host-camera recovery
plan. The next executable phase is **Phase 32K**, whose track depends on the host
camera: **Path A — Camera Recovery Verification + Evidence Capture** if the system
camera works again, or **Path B — Alternate Camera Input / Fallback Feasibility
Planning** if it remains blocked.

The preceding **Phase 32H** — Orbital Graph Control QA + Usability Hardening
(**frontend-only**, merged into `main` via PR #124) — was a QA/tuning pass over
the Phase 32G wiring — it added **no** new
control surface and kept motion-to-graph control **opt-in, off by default,
visual-only, and read-only**. It (1) calmed the camera: gentler yaw/pitch/zoom
integration gains and a slightly wider dead zone so a lightly off-centre hand no
longer makes the graph creep or feel twitchy; (2) adds a **staleness guard** —
`integrateOrbitalCamera` now optionally takes `now` and treats an *active but
stale* command (source loop stalled mid-motion) exactly like idle, so a frozen
frame decays to neutral instead of drifting to the clamp and cannot cause a jump
when control is re-enabled; (3) adds an explicit **Recenter camera** control in
the readout that snaps the pose back to face-on (visual only — never selection or
data), complementing the existing still-hands auto-recentre; and (4) sharpens the
opt-in copy (an *Experimental · off by default* pill on the switch, clearer
visual-only/read-only wording). No helper is made non-deterministic (the `now`
argument stays a pure input). Adds **no** backend, API, schema, package, or
dependency change, and **no** MediaPipe/webcam/Vite/routing change. Full detail in
the [Motion Sandbox Control Contract + 32G doc](motion-sandbox-control-contract.md)
(§22–§29) and the
[Phase 32E Orbital Graph Control Contract + Motion-to-Graph Wiring Planning](planning/phase-32e-orbital-graph-control-contract-motion-wiring.md)
doc.

The preceding **Phase 32F** (frontend-only, types + pure helper, merged into
`main` via PR #122) implemented the first typed piece of the Phase 32E plan: a
small, deterministic, side-effect-free bridge module
(`apps/frontend/src/orbitalGraphControl.ts`) that defines the **separate**
`OrbitalGraphControlCommand` graph-intent contract and a pure `MotionCommand` →
graph-intent mapping helper (deadzone / confidence gating / clamp, failing safe
toward stillness). It was a **contract + helper stub only** — nothing consumed it
yet — and touched no React, DOM, camera, MediaPipe, graph rendering, or app state,
and added no dependency, backend, API, schema, or CSS change. Phase 32G is its
first consumer.

The preceding **Phase 32E** (documentation only, merged into `main` via PR #121)
defined — as **planning only, with no wiring** — how the existing Motion Sandbox
output could eventually control the knowledge graph as an orbital / 3D-feeling
surface: the existing `MotionCommand` contract, a **separate** graph-intent contract
(`OrbitalGraphControlCommand`), the motion-to-graph mapping rules, a strict
opt-in/off-by-default engagement + safety model (confidence, deadzone, and staleness
gating; Escape/Stop kill path; read-only, no graph mutation), the UI/UX activation
contract, a future helper/module architecture, and the next-phase sequence.

The preceding **Phase 32D** (frontend-only, complete and merged into `main`)
added a **MediaPipe Hand Landmarker** estimator to the Motion Sandbox as the
primary detector while preserving the Phase 32B/32C **frame-difference** estimator
as a zero-dependency fallback / debug visualiser. Both fill the *same* hardened
`MotionCommand` contract, with `source` as the discriminator; the landmark
estimator makes `zoomDelta` (approximate, single-camera scale proxy) and
`pinchActive` (real, thumb/index distance) live. A small typed helper
(`apps/frontend/src/handLandmarkMotion.ts`) owns the deterministic landmark math,
and a lightweight landmark overlay + hand-detection readout were added. It added
one **pinned** dependency (`@mediapipe/tasks-vision@0.10.35`); the wasm runtime and
model are fetched from version-pinned URLs, never committed or transmitted. The
camera stays explicit-start, local-only, no-storage, no-backend-transmission. **No
graph control wiring was added.** Full detail in the
[Motion Sandbox Control Contract + 32D doc](motion-sandbox-control-contract.md)
(§13–§20).

The preceding **Phase 32C** (frontend-only) runtime-QA'd the Phase 32B sandbox and
hardened the `MotionCommand` contract (explicit `active` / `source` / `timestamp`
fields plus a pitch-sign fix); its QA recommended exactly this hand-landmark work
because frame-difference cannot infer depth or a pinch. The earlier **Phase 32B**
(PR #118) landed the standalone webcam motion sandbox, and **Phase 32A.6**
(docs-only) reconciled this roadmap with `main`: the Phase 31 premium-graph-
interaction frontend series (31A planning through 31H) is **complete and merged**,
Phase 31I is **implemented on its feature branch but not yet merged into `main`**,
and the Phase 30-series interaction-recovery work — including the Phase 30C QA +
screenshot-evidence pass (PR #110) — is complete. With Phase 32E (this planning
phase) defining the orbital graph-control contract, the next phase is **Phase 32F —
Orbital Graph Control Contract Types + Helper Stub**.

The preceding **Phase 31-series** delivered the premium graph-interaction
frontend polish, and **Phases 31A through 31H are complete and merged into
`main`.** Phase 31A (planning / docs only, PR #111) defined the premium
interaction model, the overlay/command-surface direction, and the portfolio demo
story. Phase 31B (PR #112) implemented it — type-owned aura rings, the
`selected > related > ambient` emphasis tiers, and incident-edge energy. Phases
31C, 31D, and 31E extended the surface (hover reveals local structure + overlay
motion; overlay tooling + graph-surface usability; and graph-surface visual
density / interaction depth). Phase 31F (PR #116) refined the graph
micro-interactions and command surface, Phase 31G consolidated the accumulated
aura/overlay CSS cascade with **no computed-style change**, and Phase 31H
(PR #117, current `main` HEAD) improved related-node and label readability. All
were frontend presentation/interaction only over the existing deterministic SVG
view model; the graph stayed read-only with no backend/API/schema/package
change. **Phase 31I** (graph overlay legibility + command-surface final polish)
is **implemented on its feature branch (commit `6bba994`) but not yet merged into
`main`**, so it is tracked as pending rather than complete.

The preceding **Phase 30-series** closed the two Phase 29C interaction rough
edges and is complete. Phase 30A (planning only) triaged them and locked a narrow
Phase 30B contract; **Phase 30B** landed the interaction-recovery +
responsive-rail fix in code (PR #109 — predictable Escape/focus after dock close
and a narrow-viewport rail rule, in `App.tsx` / `KnowledgeGraphPanel.tsx` /
`styles.css`; frontend only, graph read-only); and **Phase 30C** completed the QA
+ screenshot-evidence pass (PR #110) — a 20-check connected-runtime run recording
a `phase-30c-connected-*` screenshot set and an
[evidence doc](demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md).

The preceding **Phase 29C** — Graph Interaction + Overlay Polish QA +
Screenshot Evidence Refresh (QA / evidence / documentation only). Phase 29C
re-runs the connected local runtime (backend `8787`, frontend `5173`) after
the Phase 29B implementation and verifies the Phase 29A interaction contract
against the real app — hover lifts, the three-tier selected > related >
ambient emphasis model, in-place selection switching, edge selection,
empty-canvas deselect, the Escape dismissal order, overlay
exclusivity/persistence, focus management, and narrow-viewport behavior —
capturing a fresh `phase-29c-connected-*` screenshot set while preserving
prior evidence history. **Scope: QA/evidence/docs only** — no
frontend/CSS/backend/API/schema/package/runtime behavior change and no
implementation fixes. See the
[Phase 29C evidence doc](demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md).
Phase 29B (complete) implemented the
[Phase 29A](planning/phase-29a-graph-interaction-overlay-polish-planning.md)
interaction contract as a frontend-only presentation/interaction pass.

The sequence around Phase 29C:

- **Phase 28D** — README / portfolio visual lock (**complete**); locked the
  post-28B/28C graph-primary direction in the portfolio-facing docs — the
  Knowledge Graph is the full application surface / viewfinder, supporting
  tools (Vault, Sources, Intelligence, Console, legend/lists, inspector)
  appear as contextual overlays rather than permanent dashboard columns, and
  the shell stays dark black/chrome/metal with minimal non-graph color. See
  the [Phase 28D Visual Direction Lock](portfolio/phase-28d-visual-direction-lock.md).
- **Phase 29A** — graph interaction + overlay polish planning (**complete**;
  planning only).
- **Phase 29B** — Graph Interaction + Overlay Polish Frontend Implementation
  Pass (**complete**).
- **Phase 29C** — QA + screenshot evidence refresh (**complete**;
  QA/evidence/docs only).
- **Phase 30A** — post-polish interaction triage + next frontend direction
  planning (**complete**; planning only).
- **Phase 30B** — interaction recovery + responsive rail frontend
  implementation pass (**complete**).
- **Phase 30C** — interaction recovery QA + screenshot evidence refresh
  (**this phase**; QA/evidence/docs only).

The preceding **Phase 28C** verified the connected runtime after the Phase
28B implementation and captured fresh, visually re-verified screenshots of
the default full-viewport graph, the legend/lists overlay, the
selected-node inspector, each of the Vault/Sources/Intelligence/Console
overlays, and a narrow viewport — confirming the true graph-primary surface
renders as specified with no persistent sidebar/dashboard-column framing.
`npm run check:frontend` passes; no frontend/backend/API/schema/package
change. See the [evidence doc](demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md).
Phase 28B implemented the Phase 28A contract (including
its Section 6 visual correction lock) in the running frontend: the Knowledge
Graph now fills the entire viewport edge-to-edge at every breakpoint, with no
persistent sidebar, column, or card-grid framing left standing. The former
always-visible control rail is now a compact, icon-only, bottom-docked glass
capsule that recedes to near-invisible at rest and reveals labels on
hover/focus; the app masthead and the contextual dock (Vault/Sources/
Intelligence/Console) are translucent floating overlays rather than
layout-dividing flex-row siblings; and the graph's own legend/groups/lists
explorer and node inspector are now summoned/selection-triggered floating
glass cards instead of always-visible edge columns. Shell chrome (rail,
masthead, dock frame) carries no decorative accent color — all color energy
stays with the graph, which also gained a living-identity groundwork: a
subtle idle aura/breathing pulse on every node, a per-type resting halo, a
stronger pulsing glow on the selected node, and an animated "energy flow"
dash on edges incident to the current selection. No backend/API/schema/
dependency change, no graph mutation, no new runtime assets, no router/D3/
Cytoscape/React Flow/3D. `npm run check:frontend` passes. See the
[Phase 28A planning doc](phase-28a-true-graph-primary-overlay-contract.md).
Phase 27B implemented the direction defined in [Phase 27A](ui/phase-27a-graph-first-app-shell-planning.md):
the Knowledge Graph is now the persistent, full-viewport primary surface, and the Source Registry,
Intelligence Report, Console, and Vault/status summary are reachable as contextual dock panes opened
from a compact control rail instead of stacked dashboard sections. All existing data, endpoints, and
read-only behavior are unchanged — this phase is layout/composition only. Phase 27D corrected the
shell to the intended full-viewfinder surface, and Phase 27E is the QA/evidence pass that verifies
the connected runtime and records fresh screenshots of the corrected shell — see the
[Phase 27E evidence doc](demo/phase-27e-full-viewfinder-graph-surface-qa-screenshot-evidence.md).

Phase 25B.5 defines the **frontend asset contract**
for Hive&#124;Mind — how approved devdevbuilds/Hive&#124;Mind icons, marks, logos,
badges, SVGs, and screenshot evidence may be used in the frontend — **before** any
icon/asset is added. It audits the current repo (a clean baseline: the only static
image is the approved `docs/assets/branding/hivemind-readme-banner.png`, plus
`docs/demo/screenshots/*` evidence; the running app ships **no** favicon, logo, or
static asset, and the only SVG is the inline, data-driven Knowledge Graph render),
then sets the approved **source authority** (devdevbuilds parent → Hive&#124;Mind
lockup), the allowed/forbidden asset categories (no icon-library dependency, no CDN,
no generated/random or screenshot-derived assets), file-location and naming
conventions, SVG safety, accessibility, dark-metallic theming (monochrome/duotone/
glow/metallic/status treatments), the app-mark-vs-decorative-icon line, and how future
asset phases must reference the contract. It adds **no** asset and changes no
behavior. See the [Frontend Asset Contract](frontend-asset-contract.md).
The preceding **Phase 25A** defined a **buildable visual
design system** for the next UI implementation pass — a premium, dark metallic
intelligence-console aesthetic with a graph-forward product identity — **before** any
frontend/CSS change. It documents the current (light-theme) visual baseline, the
target visual identity and anti-pattern guardrails (no hacker cosplay, no fake
liveliness), the design principles, a layered surface/panel elevation system, the
typography/hierarchy direction, a graph-centered experience direction (node/edge
visual language, canvas framing, the canvas↔inspector relationship, the legend/status
strip, and *planned, read-only* overlay concepts for Temporal Decay / Dreaming
Suggestions / Provenance Chains / Query Trails), the Intelligence-Report visual
direction with an explicit **real-vs-planned visual contract**, the
navigation/demo-flow direction, the exact **Phase 25B** implementation boundaries, and
the **Phase 25C** QA/evidence expectations. The Knowledge Graph stays **read-only**;
no data, logic, or screenshots are fabricated. It is honest and buildable over the
existing Phase 21A token system and SVG graph view model without any architecture
change, and it changes no UI/CSS/frontend/backend/API/schema/package/dependency or
runtime behavior. See the
[Phase 25A Premium Visual Design System / Frontend Presentation Direction](ui/phase-25a-premium-visual-system-planning.md).
The preceding **Phase 24A** reviewed the existing Phase 23B
connected screenshot set and selected the three strongest surfaces for the README
landing page — the connected dashboard top (`phase-23b-connected-ui-top.png`), the
Knowledge Graph (`phase-23b-connected-knowledge-graph.png`), and the Intelligence
Report (`phase-23b-connected-intelligence-report.png`) — adding a **Visual evidence**
README section with honest captions and recording the selection rationale (including
the intentionally-omitted Sources / Console / full-page captures) in the
[Phase 24A Portfolio Screenshot + README Visual Lock](demo/phase-24a-portfolio-screenshot-readme-visual-lock.md)
note, reusing **only existing, real captured screenshots** with no image fabrication
and no behavior change.
The preceding **Phase 23B** re-ran the local backend
(`8787`) and frontend (`5173`) and captured honest screenshot/runtime evidence that
the **Phase 23A** UI surface readability + panel-hierarchy polish renders correctly
over the still-connected dashboard: the per-panel accent-tick headings, unified
card/inspector rounding, the Intelligence Report hairline section dividers, lifted
muted-label contrast, and the grouped Console output. The directly exercised
endpoints returned the same shapes/values as Phase 21C/21F/22C (health `0.1.0`;
graph 7 nodes / 6 edges; Intelligence Report Dreaming `0` / Decay `7` / Provenance
`7` / Query Trails `7`), confirming **no backend/API/schema behavior changed**
(Phase 23A was frontend CSS-only), and `npm run check:frontend` passes. A new
`phase-23b-connected-*` screenshot set records the polished panel hierarchy on every
major surface while preserving the `phase-22c-*` history. It changes no backend,
frontend, CSS, source-code, package, config, API, schema, dependency, or test
behavior. See the
[Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](demo/phase-23b-ui-readability-qa-screenshot-evidence.md).
The preceding **Phase 23A** applied the presentation-only readability +
panel-hierarchy polish as a **frontend CSS-only** pass (PR #82): a shared accent-tick
identity on every panel heading, unified card/inspector/container rounding onto the
shared token radius, hairline dividers separating the dense Intelligence Report
sub-sections, lifted muted-label contrast, and grouped Console output — no new data,
network/API/contract, or panel-behavior change.
The preceding **Phase 22C** re-ran the local backend (`8787`) and frontend (`5173`)
and captured honest screenshot/runtime evidence that the **Phase 22B** single-page
section navigation is **present and usable** over the connected dashboard, with a
new `phase-22c-connected-*` set recording the sticky nav and its active-section
highlight while preserving the `phase-21f-*` history. See the
[Phase 22C UI Navigation QA + Screenshot Evidence Refresh](demo/phase-22c-ui-navigation-qa-screenshot-evidence.md).
The preceding **Phase 22B** implemented the locked navigation model as a
frontend-only pass (PR #80): the sticky in-page section nav, `id` anchors on every
surface, an `IntersectionObserver` scrollspy "you are here" cue, smooth anchor
scrolling that respects `prefers-reduced-motion`, and a keyboard skip link — no
router, no new dependency, no new pages, and no backend/API/schema/contract
changes. It implemented the
[Phase 22A UI Navigation + Demo Flow Planning](planning/phase-22a-ui-navigation-demo-flow-planning.md),
which inventoried the seven top-level dashboard surfaces, documented the
scroll-only demo flow and its pain points, and proposed the controlled single-page
section-navigation model while **deferring React Router and any route
architecture** and forbidding fake pages.
The preceding **Phase 21F** re-ran the local backend (`8787`)
and frontend (`5173`), validated that the **Phase 21E**-polished dashboard is still
**connected** to the backend, and refreshed the screenshot/evidence trail so the
captured demo proof reflects the **current polished** app state. The directly
exercised endpoints returned the same shapes/values as Phase 21C (health `0.1.0`;
graph 7 nodes / 6 edges; Intelligence Report Dreaming `0` / Decay `7` / Provenance
`7` / Query Trails `7`), confirming **no backend/API/schema behavior changed**, and
`npm run check:frontend` passes. New `phase-21f-connected-*` screenshots supersede
the pre-polish `phase-21c-*` set while preserving that history. It changes no
backend, frontend, CSS, source-code, package, config, API, schema, dependency, or
test behavior. See the
[Phase 21F UI Demo Polish QA + Screenshot Evidence Refresh](demo/phase-21f-ui-demo-polish-qa-evidence.md).
The preceding **Phase 21E** implemented the presentation-only UI demo polish pass
(header band, `DEVDEVBUILDS` parent label, `READ-ONLY DEMO BUILD` badge,
connection/health status row, card-style metric grids) against the
**Phase 21D — UI Demo Polish Planning / Dashboard Refinement Scope**, which
documented the connected UI state and a prioritized set of dashboard refinement
targets (visual hierarchy, spacing/density, connected-data readability,
Intelligence Report, Knowledge Graph, Source Registry, console, responsive
behavior, screenshot friendliness) and locked read-only/non-mutating boundaries.
See the
[Phase 21D UI Demo Polish Planning / Dashboard Refinement Scope](phase-21d-ui-demo-polish-planning.md).
The preceding **Phase 21C** re-ran the local backend (`8787`) and frontend (`5173`)
and captured the **connected** UI state after the Phase 21A/21B runtime-config
fixes — the "Connected" status pill, live API health, the rendered Knowledge Graph
(7 nodes / 6 edges), and the backend-derived Intelligence Report — replacing Phase
20D's honestly-recorded `Failed to fetch` evidence while preserving that history.
See the
[Phase 21C Connected UI Screenshot + Runtime Evidence Refresh](demo/phase-21c-connected-ui-evidence.md).
The preceding **Phase 21A** added the dashboard shell foundation and **Phase 21B**
aligned the frontend API base-URL runtime config (root `envDir`, canonical backend
port `8787`), which together fixed the frontend/backend mismatch that Phase 20D had
documented. Before that, Phase 20D executed the Phase 20A screenshot/evidence plan
against **real, locally running app state**: it verified the backend runtime
directly through `/api/health`, `/api/sources`, `/api/graph`, and
`/api/intelligence/report`, and recorded the captured backend-runtime screenshots
and an evidence doc; its frontend browser state showed a `Failed to fetch` (a
run-configuration mismatch, since fixed), documented honestly as captured runtime
evidence. See the
[Phase 20D Final Demo Screenshot + Evidence Capture Pass](demo/phase-20d-demo-evidence.md).
The preceding Phase 20C packaged the existing project narrative into a canonical
[Final Demo Script](demo/final-demo-script.md) and locked the presentation spine via
a [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md) — the one-line
story, the data-flow surface order, and the honesty boundaries. The next recommended
phase is the **Final Portfolio Packaging / Public Presentation Pass**, drawing on the
locked scope and the captured evidence.

Phase 20A defined the **final demo release-candidate scope** for Hive|Mind before
any final polish, screenshot capture, README narrative hardening, UI tightening,
release tagging, or public-facing writeup. It states the current demo-ready story,
locks the clean portfolio narrative (a local-first, deterministic, read-only
knowledge intelligence dashboard with no AI/LLM), enumerates the demo candidate
surfaces with per-surface evidence and overstatement guards, defines a
portfolio-readiness checklist and a screenshot/evidence plan (no screenshots are
created there), lists the known limitations to disclose and the out-of-scope items,
and recommends a controlled next-phase sequence (20B–20E). It implements no code and
changes no behavior. See the
[Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](release-readiness/phase-20a-demo-release-candidate-planning.md).

Phase 19B verified and recorded the current
state of Hive|Mind as a controlled, demo-ready, release-readiness *candidate*
without changing application behavior. It documents the readiness posture across
backend API stability, the security hardening sequence, the four Intelligence
Report surfaces, Obsidian import/read-only behavior, the read-only Knowledge
Graph visualization, demo clarity, and documentation cohesion; records the
completed security arc (18A–19A) and intelligence arc (Temporal Decay, Dreaming,
Provenance, Query Trails); and adds a **Demo Evidence Checklist** (what may be
shown honestly, what is backend-derived, what stays read-only/non-mutating, what
is deferred, and what must not be overclaimed) plus explicit **Release Readiness
Boundaries**. It implements no code and changes no behavior. See the
[Phase 19B Release Readiness QA + Demo Evidence Pass](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md).

Phase 19A consolidated the completed Phase 18A–18F security-hardening arc into a
single release-readiness view: it summarizes the arc, states the current security
posture without overclaiming, distinguishes **demo readiness** from **production
security readiness**, assesses the release-readiness categories (API defensive
validation, error safety, request-body edge cases, deferred items, documentation,
test evidence, demo expectations, architecture cohesion, and future
production-hardening boundaries), carries the deferred/blocked scope forward
unchanged, and adds a release-readiness checklist. It implements no code and
changes no behavior. See the
[Phase 19A Security Cohesion + Release Readiness Planning](security/phase-19a-security-cohesion-release-readiness-planning.md).

The preceding security arc: Phase 18A delivered the security threat model +
vulnerability test plan; Phase 18B implemented the §5.1 API defensive-validation /
error-safety cases; Phase 18C verified those behaviors, mapped coverage to the
threat model, and recorded the regression evidence; Phase 18D triaged the API edge
cases 18C deferred (deep nesting / recursion, query-parameter safety, value
normalization, route-level validation) into handled / deferred / not-applicable /
blocked buckets and defined a narrow scope for **Phase 18E — API Edge Case
Defensive Validation MVP**; Phase 18E then implemented the selected subset (bounded
request-body nesting-depth guard + explicit null-like / empty-value decisions) as
additive, per-model guards with 18 regression tests; and Phase 18F verifies that
18E behaves as documented — re-running the suite (18 targeted + 23 Phase 18B
regression + 267 full backend tests passing), mapping the coverage back to the
18A threat model and 18D triage, and confirming the intentionally-deferred scope.
Phase 18F implements no code and changes no behavior.

With Phase 16C merged, all four Intelligence Report surfaces (Temporal Decay,
Dreaming Suggestions, Provenance Chains, Query Trails) are backend-derived and
frontend-visible. Phase 17A was the cohesion/readiness *planning* pass and
Phase 17B was the readiness *hardening* pass that documented, without changing
behavior, the design rationale, explicit Temporal Decay thresholds, edge cases,
evidence expectations, performance considerations, and a future source-adapter
strategy. Phase 18A is the security-readiness pass: a documentation-only threat
model and vulnerability test plan that defines scope/authorization, the system
inventory, trust boundaries, the attack-surface matrix, planned test categories,
pass/fail criteria, and recommended future hardening phases — before any
owner-authorized, local-only defensive testing or hardening begins. It implements
no security fix and changes no behavior. See
[Phase 17B Intelligence Report Cohesion Hardening + Readiness QA](phase-17b-intelligence-cohesion-hardening.md)
and the
[Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md).

Phase 16A (planning) and Phase 16B (contract/schema alignment) prepared a stable
`QueryTrailEntry` shape. See
[Phase 16A Query Trails / Query Memory Foundation Planning](phase-16a-query-trails-foundation-planning.md)
and
[Phase 16B Query Trails Contract Types / Schema Alignment](phase-16b-query-trails-contract-schema.md).

Phase 16C made the Query Trails section **backend-derived** from existing
store structure (`app/services/query_trails.py`), replacing the demo fixture as
the report's primary source. Rationale: derivation is backend-owned (not
fixtures, not client capture) so the trail logic stays deterministic, reviewable,
and testable against the same store the rest of the report reads.

Only the categories existing data supports are derived — `source_followup`
(a source with linked nodes), `knowledge_gap` (an unsourced node or uncovered
source), and `related_query_cluster` (2+ nodes sharing a tag). The query-history-
dependent categories `repeated_query` and `unresolved_question` stay **blocked
and deferred** because Hive|Mind has **no persisted query history**; fabricating
query-memory records would be dishonest. Phase 16C adds no query persistence,
storage tables, query logging, browser/localStorage capture, new endpoints,
AI/LLM, dependencies, graph/source mutation, or frontend/dashboard changes — the
derived trails are a read-only projection of structural data, not query memory.

## Implemented foundation

- React/Vite frontend and FastAPI backend app shell.
- Local JSON-backed `HiveStore` and Pydantic API models.
- Safe Hive Console API and frontend panel.
- Source Registry backend, frontend panel, and inspector.
- Obsidian adapter/import pipeline and frontend import action surface.
- Knowledge Graph API and read-only Knowledge Graph panel.
- Deterministic SVG graph visualization with inspector sync and demo polish.
- Intelligence report contracts and `GET /api/intelligence/report`.
- Read-only Intelligence Report panel with every section backend-derived
  (Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails).

## Backend-derived intelligence surface

The Intelligence Report is a **fully backend-derived, read-only surface** as of
Phase 16C. As of Phase 13A the **Temporal Decay** section, as of Phase 14C the
**Dreaming Suggestions** section, as of Phase 15C the **Provenance Chains**
section, and as of Phase 16C the **Query Trails** section are derived
(read-only) from existing store/source state. No section is fixture-backed.

Backend-derived sections (read-only):

- Temporal decay statuses (Phase 13A — deterministic timestamp thresholds).
- Dreaming suggestions (Phase 14C — deterministic `duplicate`/`orphan`/`stale`
  rules over store nodes/edges; conservative, with an explainable
  `metadata.evidence` trail and a clean empty section when nothing is derivable).
- Provenance chains (Phase 15C — deterministic source/import/node/edge chains
  from existing store and source registry data, with backend-owned evidence and a
  clean empty section when no graph data exists).
- Query trails (Phase 16C — deterministic `source_followup` / `knowledge_gap` /
  `related_query_cluster` projections over store source/node/tag structure, with
  backend-owned evidence and a clean empty section when nothing is derivable).
  Query-history-dependent categories stay deferred.

Current non-capabilities:

- No `source_coverage_gap` derivation — deferred/blocked pending a future
  contract-expansion phase (Phase 14B contract decision).
- No `unresolved_query` derivation — blocked until query history is persisted.
- No `repeated_query` / `unresolved_question` Query Trail derivation — blocked
  until real persisted query history exists (Phase 16C defers these).
- No semantic provenance inference engine beyond existing source/node/import/edge
  records.
- No query persistence or query-memory logic.
- No AI/LLM calls.
- No automatic graph/source/store mutation.

## Phase history

| Phase | Status | Notes |
| --- | ---: | --- |
| 0 | Complete | Project initialization and planning foundation. |
| 1 | Complete | React/FastAPI foundation with health/status routes. |
| 2 | Complete | API contract and shared data model planning. |
| 3A-3D | Complete | Store, persistence, search helpers, and backend console. |
| 4A-4B | Complete | Frontend console panel and UX polish. |
| 5A-5C | Complete | Source Registry backend, frontend, inspector, and UX polish. |
| 6A-6E | Complete | Obsidian adapter/import pipeline and registry wiring. |
| 7A-7B | Complete | Frontend Obsidian import action panel and UX hardening. |
| 8A-8C | Complete | Knowledge Graph API, panel, and view-model prep. |
| 9A-9C | Complete | Read-only SVG graph visualization and QA polish. |
| 10A | Complete | Intelligence surface planning. |
| 10B | Complete | Intelligence contract types / read-only schemas. |
| 10C | Complete | Intelligence report endpoint foundation. |
| 10D | Complete | Intelligence Report frontend read-only panel. |
| 10E | Complete | Intelligence Report UX hardening / demo readiness. |
| 11A | Complete | Deterministic intelligence demo/seed fixtures. |
| 11B | Complete | Intelligence fixture UX review and screenshot readiness. |
| 11C | Complete | Repo cohesion, API/docs consistency, and demo documentation. |
| 12A | Complete | Demo freeze and release snapshot planning/status documentation. |
| 12B | Complete | Screenshot and demo script polish. |
| 13A | Complete | Temporal Decay section backend-derived from store timestamps (read-only MVP). |
| 13B | Complete | Intelligence Report frontend visibility for backend-derived Temporal Decay. |
| 13C | Complete | Temporal Decay end-to-end QA + demo evidence and status-language pass. |
| 14A | Complete | Dreaming Suggestion backend-derivation planning documentation. |
| 14B | Complete | Dreaming contract/schema alignment. |
| 14B.5 | Complete | Temporal Decay contract QA and edge-case hardening. |
| 14B.6 | Complete | Dreaming logic implementation readiness / defensive backend scope alignment. |
| 14C | Complete | Dreaming Suggestions backend-derived MVP for `duplicate_signal`, `orphaned_node`, and `stale_knowledge_link`. |
| 14D | Complete | Dreaming Suggestions frontend visibility and demo polish. |
| 14E | Complete | Dreaming Suggestions end-to-end QA and demo evidence pass. |
| 15A | Complete | Provenance Chains backend derivation planning and frontend readiness notes. |
| 15B | Complete | Provenance Chains contract types / schema alignment. |
| 15C | Complete | Provenance Chains backend-derived MVP for existing source/import/node/edge records. |
| 15D | Complete | Provenance Chains frontend visibility and demo polish. |
| 15E | Complete | Provenance Chains end-to-end QA and demo evidence pass. |
| 16A | Complete | Query Trails / Query Memory foundation planning before persistence or APIs. |
| 16B | Complete | Query Trails contract types / schema alignment (read-only contract before persistence/derivation). |
| 16C | Complete | Query Trails backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster`; `repeated_query` / `unresolved_question` deferred until query history is persisted. |
| 17A | Complete | Intelligence Report cohesion + system readiness planning (documentation only); aligns the four backend-derived surfaces and recommends a conservative, foundation-first next phase. |
| 17B | Complete | Intelligence Report cohesion hardening + readiness QA (documentation only); design rationale, explicit Temporal Decay thresholds, edge-case matrix, evidence expectations, performance/readiness notes, and future source-adapter strategy. |
| 18A | Complete | Security threat model + vulnerability test plan (documentation only); scope/authorization, system inventory, trust boundaries, attack-surface matrix, planned test categories, pass/fail criteria, and recommended future hardening phases (18B–18F). |
| 18B | Complete | Backend API defensive validation + error safety; global clean-JSON `500` handler (no traceback/path leak), malformed Obsidian vault-path normalization (→ `400`), and additive upper-bound length guards on client free-text fields (→ `422`), with regression coverage in `test_api_error_safety.py`. |
| 18C | Complete | Backend API security regression QA + evidence pass (QA/documentation only); verifies the Phase 18B §5.1/§5.3 behaviors, maps coverage to the threat model, and records test evidence (23 targeted + 249 full backend tests passing). |
| 18D | Complete | API edge case hardening planning / deferred security scope triage (planning/documentation only); triages the edge cases 18C deferred (deep nesting / uncontrolled recursion, query-parameter safety, value normalization, route-level validation) into handled / deferred / not-applicable / blocked buckets, risk-rates them against the local single-user runtime, and defines a narrow scope + readiness checklist for Phase 18E. Implements no code. |
| 18E | Complete | API edge case defensive validation MVP (backend implementation); implements the selected Phase 18D edges as additive, per-model guards with 18 regression tests and error-shape conformance: a bounded request-body nesting-depth guard (`MAX_REQUEST_NESTING_DEPTH = 32`) on the free-form body models (`HiveImportRequest`, `SourceRecordCreate`, `SourceRecordUpdate`) → clean `422` over-depth / at-limit still accepted, plus locked null-like / empty-whitespace value decisions. The route inventory found zero query-reading routes, so no query-param guard target and no justified global middleware — no middleware rewrite, no auth/rate-limit/persistence/dependency changes. |
| 18F | Complete | API edge case security regression QA + evidence pass (QA/documentation only); independently verifies the Phase 18E nesting-depth guard and value-handling decisions, maps coverage back to the Phase 18A threat model and Phase 18D triage, confirms the intentionally-deferred scope (no global middleware, no broad query-param validation, no auth/rate-limit/persistence/frontend expansion), and records test evidence (18 targeted + 23 Phase 18B regression + 267 full backend tests passing). Implements no code and changes no behavior. |
| 19A | Complete | Security cohesion + release readiness planning (planning/documentation only); consolidates the Phase 18A–18F arc into one release-readiness view, states the current security posture without overclaiming, distinguishes demo readiness from production security readiness, assesses the release-readiness categories, carries the deferred/blocked scope forward unchanged, and adds a release-readiness checklist plus rationale notes. Implements no code and changes no behavior. |
| 19B | Complete | Release readiness QA + demo evidence pass (QA/documentation/evidence only); verifies and records the current readiness posture across backend API stability, the security hardening sequence (18A–19A), the four backend-derived Intelligence Report surfaces, Obsidian import/read-only behavior, the read-only Knowledge Graph visualization, demo clarity, and documentation cohesion; adds a Demo Evidence Checklist and explicit Release Readiness Boundaries; frames Hive&#124;Mind as a controlled, local/dev, demo-ready release-readiness candidate (not production-ready/secure). Implements no code and changes no behavior. |
| 20A | Complete | Demo release candidate planning + final portfolio readiness scope (planning/documentation only); defines the final demo release-candidate scope before any polish/screenshots/release work — states the current demo-ready story, locks the deterministic, read-only, local-first portfolio narrative (no AI/LLM), enumerates the demo candidate surfaces with per-surface evidence and overstatement guards, defines a portfolio-readiness checklist and a screenshot/evidence plan (no screenshots created), lists known limitations to disclose and out-of-scope items, and recommends a controlled 20B–20E sequence. Implements no code and changes no behavior. |
| 20B | Complete | Final README + portfolio narrative hardening (documentation only); aligns the README and landing docs with the locked Phase 20A story — tool-first overview, locked one-line narrative, explicit implemented / intentionally-read-only / planned distinction, design-rationale notes, agent-assisted/human-reviewed workflow (devdevbuilds as merge gate), a guardrails/non-goals section, and the status advance to Phase 20B. Implements no code and changes no behavior. |
| 20C | Complete | Final demo script + portfolio presentation lock (documentation / demo only); packages the existing narrative into a canonical [Final Demo Script](demo/final-demo-script.md) and locks the presentation spine via a [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md) — one-line story, data-flow surface order, and honesty boundaries — before any further UI work. UI work remains intentionally deferred until the presentation spine is locked. Implements no code and changes no behavior. |
| 20D | Complete | Final demo screenshot + evidence capture pass (capture / documentation only); executes the Phase 20A screenshot/evidence plan against real, locally running app state — verifies the backend runtime directly via `/api/health`, `/api/sources`, `/api/graph`, and `/api/intelligence/report` and records the captured backend-runtime screenshots and an [evidence doc](demo/phase-20d-demo-evidence.md). The frontend browser state showed a `Failed to fetch` (a run-configuration mismatch, since fixed in 21A/21B), documented honestly as captured runtime evidence. Implements no code and changes no behavior. |
| 21A | Complete | Dashboard shell foundation (frontend styling/scaffold); adds the dashboard shell layout/styles ahead of connected-UI evidence. |
| 21B | Complete | Frontend API base-URL runtime config alignment; loads env from the repo root (`envDir`), documents the canonical backend port `8787`, and adds `.env.example` guidance — fixing the frontend/backend mismatch Phase 20D recorded. |
| 21C | Complete | Connected UI screenshot + runtime evidence refresh (capture / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures the connected UI state — "Connected" status, live API health, the rendered Knowledge Graph (7 nodes / 6 edges), and the backend-derived Intelligence Report — replacing Phase 20D's `Failed to fetch` evidence while preserving that history. Records an [evidence doc](demo/phase-21c-connected-ui-evidence.md) and connected-UI screenshots. Implements no code and changes no behavior. |
| 21D | Complete | UI demo polish planning / dashboard refinement scope (planning / documentation only); documents the current connected UI state and a prioritized dashboard refinement set (visual hierarchy, spacing/density, connected-data readability, Intelligence Report, Knowledge Graph, Source Registry, console, responsive, screenshot friendliness), separates demo-readiness from future premium-UI ideas, locks read-only/non-mutating boundaries, and recommends a scoped Phase 21E implementation pass. See the [planning doc](phase-21d-ui-demo-polish-planning.md). Implements no code and changes no behavior. |
| 21E | Complete | UI demo polish implementation pass (frontend presentation only); polished header band (`DEVDEVBUILDS` parent label, `READ-ONLY DEMO BUILD` badge), connection/health status row, and card-style metric grids against the Phase 21D priorities. Frontend-only (`App.tsx`, `SourceRegistryPanel.tsx`, `styles.css`); no backend, contract, logic, data-value, or dependency changes. |
| 21F | Complete | UI demo polish QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`), validates the Phase 21E-polished UI is still connected (live API health `0.1.0`, Knowledge Graph 7 nodes / 6 edges, backend-derived Intelligence Report — Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7), confirms `npm run check:frontend` passes, and refreshes the screenshot trail with `phase-21f-connected-*` captures superseding the pre-polish `phase-21c-*` set while preserving that history. See the [evidence doc](demo/phase-21f-ui-demo-polish-qa-evidence.md). Implements no code and changes no behavior. |
| 22A | Complete | UI navigation + demo flow planning (planning / documentation only); inventories the seven top-level dashboard surfaces (hero, connection + API health, vault, Source Registry incl. the nested Obsidian import form, Knowledge Graph, Intelligence Report, Console), documents the current scroll-only demo flow and its pain points (no nav, no anchors, long scroll, buried import controls, no active-section cue), and proposes a controlled single-page section-navigation model for Phase 22B — in-page anchor nav over stable section `id`s, scrollspy active-section cue, CSS-first smooth-scroll/anchor behavior, keyboard/`aria` usability, modest responsive nav, and a signposted demo walkthrough — deferring React Router/route architecture and forbidding fake pages. Defines Phase 22B acceptance criteria and locks read-only/non-mutating boundaries. See the [planning doc](planning/phase-22a-ui-navigation-demo-flow-planning.md). Implements no code and changes no behavior. |
| 22B | Complete | Single-page section navigation + demo flow (frontend presentation/structure only, PR #80); adds a sticky in-page section nav (table of contents) over the connected dashboard, stable `id` anchors on every top-level surface (`#overview` … `#console`), an `IntersectionObserver` scrollspy "you are here" cue with `aria-current`, smooth anchor scrolling that respects `prefers-reduced-motion`, and a keyboard skip link. Touches `App.tsx`, the four panel components (optional `id` prop), and `styles.css` only; no router, no new dependency, no new pages, and no backend/API/schema/contract or data-value changes. |
| 22C | Complete | UI navigation QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures honest evidence that the Phase 22B section navigation is visible and usable over the connected dashboard — sticky nav, `id` anchors, scrollspy active-section highlight, and skip link — with the directly exercised endpoints returning the same shapes/values as Phase 21C/21F (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-22c-connected-*` screenshot set (including the honest scrollspy edge behavior at the page top/bottom) and an [evidence doc](demo/phase-22c-ui-navigation-qa-screenshot-evidence.md) while preserving the `phase-21f-*` history. Implements no code and changes no behavior. |
| 23A | Complete | UI surface readability + panel hierarchy polish (frontend presentation only, PR #82); an additive `styles.css` pass on the Phase 21A token system — a shared accent-tick identity on every panel `<h2>`, sub-section heading hierarchy, unified card/inspector/container rounding onto the shared token radius with softened hairline borders, hairline dividers separating the dense Intelligence Report sub-sections, lifted muted-label/metadata contrast, and grouped Console output (labeled echo chip + firmer result-key contrast). CSS-only; no backend, contract, logic, data-value, dependency, or panel-behavior change. |
| 23B | Complete | UI surface readability QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures honest evidence that the Phase 23A readability/panel-hierarchy polish renders over the still-connected dashboard — per-panel accent-tick headings, unified card rounding, Intelligence Report hairline section dividers, lifted label contrast, and grouped Console output — with the directly exercised endpoints returning the same shapes/values as Phase 21C/21F/22C (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-23b-connected-*` screenshot set and an [evidence doc](demo/phase-23b-ui-readability-qa-screenshot-evidence.md) while preserving the `phase-22c-*` history. Implements no code and changes no behavior. |
| 24A | Complete | Portfolio screenshot selection + README visual lock (docs / README / demo presentation only); reviews the existing Phase 23B connected screenshot set and selects the three strongest README surfaces (connected dashboard top, Knowledge Graph, Intelligence Report), adds a **Visual evidence** README section with honest connected-runtime captions, and records the selection rationale — including the intentionally-omitted Sources / Console / full-page captures and the no-fabrication confirmation — in the [Phase 24A Portfolio Screenshot + README Visual Lock](demo/phase-24a-portfolio-screenshot-readme-visual-lock.md) note. Reuses only existing real screenshots; no image fabrication and no UI/CSS/frontend/backend/API/schema/package/dependency/runtime behavior change. |
| 25A | Complete | Premium visual design system / frontend presentation direction (planning / documentation only); defines a buildable premium dark-metallic intelligence-console visual system with a graph-forward identity **before** any UI/CSS change — current (light) visual baseline, target visual identity + anti-pattern guardrails, design principles, a layered surface/panel elevation system, typography/hierarchy direction, a graph-centered experience direction (node/edge visual language, canvas framing, canvas↔inspector relationship, legend/status strip, and *planned, read-only* overlay concepts for Temporal Decay / Dreaming / Provenance / Query Trails), the Intelligence-Report visual direction with an explicit real-vs-planned visual contract, the navigation/demo-flow direction, the Phase 25B implementation boundaries, and the Phase 25C QA/evidence expectations. Honest and buildable over the existing Phase 21A token system and SVG graph view model; graph stays read-only; nothing faked. See the [planning doc](ui/phase-25a-premium-visual-system-planning.md). Implements no code and changes no behavior. |
| 25B | Complete | Premium visual system implementation pass (frontend presentation only); applies the Phase 25A direction as a token-driven reskin in `apps/frontend/src/styles.css` — a dark metallic palette + elevation/spacing/type/glow tokens (token *names* preserved so token-driven rules re-theme automatically) and per-surface restyling of header/panels/cards/nav/graph framing/inspector/Intelligence Report/console onto those tokens. Presentation-only over the existing token system and SVG view model; the graph stays read-only; no backend/API/schema/contract/data-value/package/dependency or runtime behavior change. |
| 25B.5 | Complete | Frontend asset contract + icon usage planning (planning / documentation only); audits current repo asset usage (clean baseline — only the approved `docs/assets/branding/hivemind-readme-banner.png` brand image plus `docs/demo/screenshots/*` evidence; the running app ships no favicon/logo/static asset and the sole SVG is the inline data-driven Knowledge Graph render) and creates the first Hive&#124;Mind [frontend asset contract](frontend-asset-contract.md): approved source authority (devdevbuilds parent → Hive&#124;Mind lockup), allowed/forbidden asset categories (no icon-library dependency, no CDN, no generated/random or screenshot-derived assets), file-location and naming conventions, SVG safety, accessibility, dark-metallic theming (monochrome/duotone/glow/metallic/status treatments), the app-mark-vs-decorative-icon line, screenshot-evidence and replacement/removal rules, and how future asset phases must reference the contract. Adds no asset and no dependency; changes no UI/CSS/frontend/backend/API/schema/package or runtime behavior. |
| 26A | Complete | Graph visual identity planning (planning / documentation only); see [Graph Visual Identity](ui/graph-visual-identity.md). |
| 26B | Complete | Graph Visual Presentation frontend pass, plus a 26B addendum docking the legend, promoting the inspector on selection, and giving the Knowledge Graph panel hero elevation so the canvas reads as the primary surface. Frontend presentation only; graph stays read-only. |
| 26C | Complete | Graph visual QA + screenshot evidence refresh (QA / evidence / documentation only); see the [evidence doc](demo/phase-26c-graph-visual-qa-screenshot-evidence.md). |
| 27A | Complete | Graph-first app shell planning (planning / documentation only); defines the transition from the current dashboard-with-panels layout to a graph-first app shell where the Knowledge Graph is the primary full-app view and the Source Registry, Intelligence Report, Console, and inspectors become contextual overlays/trays/docks/command surfaces. Maps each current surface to its future role, defines interaction and layout principles, and scopes Phase 27B (frontend-only shell restructuring) with explicit allowed/forbidden lists. See the [planning doc](ui/phase-27a-graph-first-app-shell-planning.md). Implements no code and changes no behavior. |
| 27B | Complete | Graph-first app shell frontend implementation pass (frontend presentation/structure only, PR #95); implements the Phase 27A direction — the Knowledge Graph becomes the persistent, full-viewport primary surface in `App.tsx`, and the Source Registry, Intelligence Report, Console, and Vault/status summary become contextual dock panes opened from a compact control rail, staying mounted (`inert`) while hidden so reopening never re-fetches data. No backend/API/schema/dependency change. |
| 27D | Complete | Correct the graph-first shell to a full-viewfinder surface (PR #97); a follow-up frontend-only pass that fixes the Phase 27B shell so the graph canvas genuinely fills the primary viewport as intended. No backend/API/schema/dependency change. |
| 27E | Complete | Full-viewfinder graph surface QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) after the Phase 27D correction and captures honest evidence of the connected full-viewfinder graph shell — the default dock-closed graph viewport, node-selection/inspector behavior, and each contextual dock pane (Vault, Sources, Intelligence, Console) — with the directly exercised endpoints returning the same shapes/values as the established evidence trail (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-27e-connected-*` screenshot set and an [evidence doc](demo/phase-27e-full-viewfinder-graph-surface-qa-screenshot-evidence.md). Implements no code and changes no behavior. |
| 28A | Complete | True graph-primary surface planning + overlay contract (planning / documentation only); tightens the Phase 27A–27E graph-first shell direction into a stricter contract before further layout work — graph dominance rules (full-viewport, no sidebar/column/card-grid framing, explicit rejection list), an overlay hierarchy (primary graph canvas, secondary node inspector, tertiary Source Registry/Intelligence Report/Console/future intelligence overlays, utility rail/command/status), a per-surface panel behavior contract, a desired-vs-undesired visual-feel test, and a scoped Phase 28B handoff (True Graph-Primary Surface Frontend Implementation Pass) with explicit allowed/forbidden files and success criteria. A **visual correction lock addendum** (Section 6) further locks deep-black/metallic chrome with color reserved almost entirely for the graph itself, a translucent hover/command-triggered nav surface replacing any persistent sidebar, glass-like non-occluding overlays, and a living/pulsing/aura/cluster graph visual identity, and extends the Phase 28B handoff accordingly. See the [planning doc](phase-28a-true-graph-primary-overlay-contract.md). Implements no code and changes no behavior. |
| 28B | Complete | True graph-primary surface frontend implementation pass (frontend presentation/structure only); implements the Phase 28A contract in `App.tsx`, `KnowledgeGraphPanel.tsx`, and `styles.css` — the graph now fills the entire viewport edge-to-edge at all breakpoints; the app masthead, the control rail, and the contextual dock are floating translucent glass overlays instead of flex-row layout siblings; the persistent control rail is replaced with a compact, icon-only, bottom-docked capsule that reveals labels on hover/focus; the graph explorer (legend/groups/node/edge lists) and node inspector are now summoned/selection-triggered floating glass cards (not always-visible edge columns); shell chrome carries no decorative accent color (Phase 28A §6.2); and the graph gained a living-identity groundwork — a subtle idle aura/breathing pulse on every node, a per-type resting halo, a stronger pulsing glow on the selected node, and an animated "energy flow" dash on edges incident to the selection. No backend/API/schema/dependency change, no graph mutation, no new runtime assets, no router/D3/Cytoscape/React Flow/3D. `npm run check:frontend` passes. |
| 28C | Complete | True graph-primary surface QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) after the Phase 28B implementation and captures honest, visually re-verified evidence of the true graph-primary shell — the default full-viewport graph (no sidebar/dashboard-column framing), the legend/lists overlay, the selected-node inspector, each of the Vault/Sources/Intelligence/Console overlays, and a narrow (~506px) viewport — with the directly exercised endpoints returning the same shapes/values as the established evidence trail (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a `phase-28c-*` screenshot set and an [evidence doc](demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md), including an honestly-recorded Sources-count discrepancy as a Known limitation rather than a fix. Implements no code and changes no behavior. |
| 28D | Complete | README / portfolio visual lock (documentation / portfolio only); locks the post-28B/28C graph-primary direction in the portfolio-facing docs — the README and roadmap now present Hive&#124;Mind as a graph-primary AI memory / intelligence workspace where the Knowledge Graph is the full application surface, supporting tools (Vault, Sources, Intelligence, Console, legend/lists, inspector) are contextual overlays, and the shell stays dark black/chrome/metal with minimal non-graph color — updates the README visual-evidence section to the existing Phase 28C captures, sharpens the portfolio narrative (deterministic backend-derived intelligence, human-directed assisted development with human review/merge control), and records the Phase 29A–29C sequence. **Docs-only:** no frontend/CSS/backend/API/schema/package/runtime behavior change and no new screenshots. See the [Phase 28D Visual Direction Lock](portfolio/phase-28d-visual-direction-lock.md). |

## Upcoming phases

| Phase | Status | Notes |
| --- | ---: | --- |
| 29A | Complete | Graph interaction + overlay polish planning (**planning / documentation only**, before any implementation); scopes the next graph interaction + overlay polish pass against the Phase 28A contract — hover/select/deselect behavior, overlay hierarchy/stacking, inspector/utility behavior, pulse/aura/group rules, keyboard/command-surface direction, and the Phase 29B allowed/forbidden scope. **Scope: docs/planning only — no code changes in this phase.** See the [planning doc](planning/phase-29a-graph-interaction-overlay-polish-planning.md). |
| 29B | Complete | Phase 29B — Graph Interaction + Overlay Polish Frontend Implementation Pass (frontend presentation/interaction only); implements the Phase 29A contract in `KnowledgeGraphPanel.tsx`, `App.tsx`, and `styles.css` — the canvas gains the three-tier selected > related > ambient emphasis model, additive hover lifts (hovered node lightens incident edges; hovered edge lifts its stroke and endpoints), empty-canvas click-to-deselect, the Phase 29A Escape dismissal order (tertiary dock → explorer → selection/inspector, one surface per press), and overlay focus management (summoned panes take focus and return it on dismissal). No backend/API/schema/package change; graph stays read-only; screenshots/evidence deferred to Phase 29C. |
| 29C | Complete | QA + screenshot evidence refresh (QA / evidence / documentation only); re-runs the connected local runtime (backend `8787`, frontend `5173`) after the Phase 29B implementation and verifies the Phase 29A interaction contract against the real app via 28 scripted checks — additive hover lifts on nodes/edges, the three-tier selected > related > ambient/dimmed emphasis, flicker-free in-place selection switching, edge selection, empty-canvas deselect (and its no-op with nothing selected), the Escape dismissal order (tertiary dock → explorer → selection/inspector), one-tertiary-overlay-at-a-time exclusivity, deliberate-overlay persistence across deselection, summon/dismiss focus management, and narrow-viewport (420px) behavior — with the directly exercised endpoints returning the same shapes/values as the established evidence trail (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7) and `npm run check:frontend` passing. Records a visually re-verified `phase-29c-connected-*` screenshot set and an [evidence doc](demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md), including two honestly-recorded interaction rough edges (Escape focus scoping after dock close; focused-rail label overflow at very narrow widths) as Known limitations rather than fixes. Implements no code and changes no behavior. |
| 30A | Complete | Post-polish interaction triage + next frontend direction planning (**planning / documentation only**, before any implementation); reviews the Phase 29C QA outcome (graph-primary surface confirmed, overlays/tools functioning, evidence captured, frontend check passed, backend untouched, remaining issues are interaction polish not foundational), triages the two known limitations — Escape/focus behavior after dock close and focused-rail label overflow at ~420px — each with current behavior / why it matters / user-facing effect / recommended fix direction / risk level, and locks a narrow contract for **Phase 30B — Interaction Recovery + Responsive Rail Frontend Implementation Pass** (allowed: `KnowledgeGraphPanel.tsx`, `styles.css`, graph helper/view-model files only if truly needed, `App.tsx` only if focus/overlay wiring requires; forbidden: backend/API/schema/package/dependency changes, new graph libs, fake data, graph mutation, new dashboard/card shell, persistent sidebar, asset dump, broad CSS rewrite, unplanned redesign, screenshots) plus the 30A→30B→30C sequence, per-decision rationale, and a guardrail lock re-affirming the graph-primary direction. **Scope: docs/planning only — no code changes in this phase.** See the [planning doc](phase-30a-post-polish-interaction-triage.md). |
| 30B | Complete | Interaction Recovery + Responsive Rail Frontend Implementation Pass (frontend presentation/interaction only, per the Phase 30A contract); `closePanel` returns focus into the graph panel (`#knowledge-graph`, `tabIndex={-1}`) instead of the summoning rail button so the dock → explorer → selection Escape stack keeps peeling press-for-press, and below the 760px breakpoint `:focus-within` no longer reveals all four rail labels at once — only the hovered/focused button's label reveals, width-clamped (`min(8rem, 42vw)`) — so the expanded rail stays within a narrow viewport while at-rest icon-only and desktop behavior are unchanged. Touched `App.tsx`, `KnowledgeGraphPanel.tsx`, and `styles.css` only (PR #109); no backend/API/schema/package change; graph stays read-only. |
| 30C | Complete | Interaction Recovery QA + Screenshot Evidence Refresh (QA / evidence / documentation only, after Phase 30B); re-ran the connected runtime (backend `8787`, frontend `5173`) and verified the Phase 30B fixes via a 20-check scripted QA run — dock-close focus recovery into the graph panel, the dock → explorer → selection Escape stack peeling press-for-press with no manual refocus and no page refresh, graph-primary re-selection after recovery, three-tier selection + bounded overlays, and narrow-viewport (420px) rail containment (one clamped label, no overflow) — with the endpoints returning the established trail (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7), zero console errors, zero failed requests, and `npm run check:frontend` passing. Records a `phase-30c-connected-*` screenshot set and an [evidence doc](demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md). Docs/screenshots/evidence only; no code or behavior change. |
| 31A | Complete | Premium Graph Interaction + Portfolio Demo Direction Planning (**planning / documentation only**); defines the premium interaction model (`selected > related > ambient` emphasis, first-class edge selection, restrained aura/pulse, keyboard parity, `prefers-reduced-motion`), the summoned/bounded overlay + command-surface direction, and the portfolio demo story, and scopes the Phase 31B implementation pass. Merged into `main` (PR #111). See the [planning doc](planning/phase-31a-premium-graph-interaction-portfolio-demo-direction.md). Docs/planning only. |
| 31B | Complete | Premium graph interaction frontend pass (frontend presentation/interaction only); implements the Phase 31A direction — type-owned aura rings, the `selected > related > ambient` emphasis tiers, and incident-edge energy — in `KnowledgeGraphPanel.tsx` / `styles.css`. Merged into `main` (PR #112). No backend/API/schema/package change; graph read-only. |
| 31C | Complete | Premium graph interaction expansion + overlay motion pass (frontend presentation only, merged into `main`); hover now reveals local structure (a hovered node illuminates its direct neighbours), the selected node's neighbourhood reads as one illuminated cluster, and the summoned overlays gain a more premium contextual entrance while staying translucent. CSS-only, reduced-motion guarded; no data/API/layout/selection-behaviour change. |
| 31D | Complete | Overlay tooling + graph-surface usability pass (frontend presentation only, merged into `main`); interaction-aware surface hint that surfaces the Esc shortcut once a selection is active, clearer overlay internal structure (hairline header divider), a graph-owned active-overlay accent, and small focus/label/narrow-viewport safeguards. CSS-only; no data/API/layout/selection change. |
| 31E | Complete | Graph surface visual density + interaction depth (frontend presentation only, merged into `main`); gives the graph surface more density and depth (region glows + lattice) so it reads as a living intelligence field, and deepens the active-interaction hierarchy a step further. CSS-only; colour stays graph-owned; no data, fake nodes, graph mutation, or new library. |
| 31F | Complete | Graph micro-interaction + command-surface refinement (frontend presentation only); unifies the node paint/weight transition on one easing curve, adds a faint hovered-node aura tier, and refines the command surface. Merged into `main` (PR #116). No data/API/schema/package change; graph read-only. |
| 31G | Complete | Consolidate graph aura/overlay CSS cascade overrides (frontend only, merged into `main`); merges the same-specificity aura/overlay declarations stacked across 31B–31F into single authoritative rules and removes dead superseded blocks, with **no computed-style change** (runtime cascade verified identical before/after). `npm run check:frontend` passes. |
| 31H | Complete | Improve graph related-node + label readability (frontend only); lifts the related-node ring onto a brighter cool-neutral so a selected node's neighbourhood reads as one illuminated cluster, and adds a subtle dark text halo so labels stay legible over the denser 31E canvas. Edits existing rules in place; reduced-motion unchanged. Merged into `main` (PR #117); current `main` HEAD. |
| 31I | Pending (not merged) | Graph overlay legibility + command-surface final polish (frontend only); darkens the frosted backdrop behind each floating overlay for text contrast without raising fill opacity, and brightens the keyboard-focused rail label to full contrast. **Implemented on branch `phase-31i-graph-overlay-legibility-command-surface-final-polish` (commit `6bba994`) but not yet merged into `main`** — tracked as pending rather than complete until it lands on `main`. |
| 32A | Complete (docs) | Motion input + orbital graph feasibility planning (**research / documentation only**); explores webcam/MediaPipe motion-input and orbital-graph feasibility for the future experimental track. Docs/research-only, no implementation. Completed on its planning branch (not yet on `main`). |
| 32A.5 | Complete (docs) | Roadmap conflict-marker cleanup (**docs-only**); resolved roadmap Git conflict markers on branch `phase-32a-5-roadmap-conflict-marker-cleanup` (commit `cd0fefc`). That cleanup did **not** land on `main`, so the markers persisted in `main`'s roadmap until Phase 32A.6 resolved them here. |
| 32A.6 | Complete | Roadmap 31-series status refresh (**docs-only**); reconciles the roadmap with actual repository history — marks 31A–31H complete/merged and 31I pending (branch-only, not merged), records the completed Phase 30-series and the Phase 32A / 32A.5 docs work, and resolves the stale roadmap conflict markers. No frontend/backend/source/package/API/schema/config change; no screenshots. |
| 32B | Complete | Standalone Webcam Motion Sandbox (frontend-only, merged into `main` via **PR #118**); an isolated "Motion" dock pane that requests the webcam only on explicit user action and derives a normalized `MotionCommand` from a dependency-free `getUserMedia` + canvas frame-difference loop, purely for inspection. Never touches the knowledge graph; no MediaPipe, no package/dependency/backend/API/schema change. |
| 32C | Complete | Motion Sandbox QA + Control Contract Hardening (**frontend-only**, this phase); runtime-QAs the Phase 32B sandbox (camera lifecycle, permission/no-device error paths, teardown, sign conventions) and hardens the local `MotionCommand` contract — adds explicit `active` / `source` / `timestamp` fields, fixes the pitch sign so upward motion reads positive, and adds an Idle/Active chip + per-axis direction hints. New [Motion Sandbox Control Contract + QA doc](motion-sandbox-control-contract.md). **No graph control wiring, no MediaPipe, no package/dependency/backend/API/schema change.** |
| 32D | Complete | MediaPipe / Hand-Landmark Motion Detection (**frontend-only**, merged into `main`); adds a MediaPipe Hand Landmarker estimator to the Motion Sandbox as the primary detector, populating the same hardened `MotionCommand` shape (with `source` as the discriminator) so `zoomDelta` (approximate single-camera proxy) and `pinchActive` (thumb/index distance) become live. Keeps frame-difference as a zero-dependency fallback / debug visualiser; adds a landmark overlay + hand-detection readout and a small typed landmark-math helper. Adds one **pinned** dependency (`@mediapipe/tasks-vision@0.10.35`); wasm/model fetched from version-pinned URLs, never committed/transmitted. Camera stays explicit-start, local-only, no-storage, no-backend. **No graph control wiring.** See [Motion Sandbox Control Contract + 32D doc](motion-sandbox-control-contract.md). |
| 32E | Complete (docs) | Orbital Graph Control Contract + Motion-to-Graph Wiring Planning (**documentation only**, merged into `main` via **PR #121**); defines — with **no wiring** — how the hardened `MotionCommand` could drive an orbital/3D-feeling graph surface: a **separate** `OrbitalGraphControlCommand` graph-intent contract, the motion-to-graph mapping rules, a strict opt-in/off-by-default engagement + safety model, the UI/UX activation contract, and the future phase sequence. **Motion does not control the graph today.** |
| 32F | Complete | Orbital Graph Control Contract Types + Helper Stub (**frontend-only**, merged into `main` via **PR #122**); adds `apps/frontend/src/orbitalGraphControl.ts` — the typed `OrbitalGraphControlCommand` graph-intent contract (kept **separate** from `MotionCommand`) plus a deterministic, side-effect-free `MotionCommand` → graph-intent mapping helper with `clampOrbitalDelta` (non-finite → 0, deadzone, ±1 clamp) and a fail-safe idle mapping (missing/inactive/low-confidence/deadzoned → idle). Constants track the Phase 32E §6 defaults (deadzone `0.08`, min confidence `0.55`). **No graph wiring, no React/state integration, no dependency/backend/API/schema/CSS change, no MediaPipe/webcam change.** See [Motion Sandbox Control Contract + 32F doc](motion-sandbox-control-contract.md) (§21). |
| 32G | Complete | First Opt-In Orbital Graph Control Wiring (**frontend-only**, merged into `main` via **PR #123**); wires the Motion Sandbox output to the Knowledge Graph camera through the 32F helper (`MotionCommand` → `mapMotionCommandToOrbitalGraphControlCommand` → new pure `integrateOrbitalCamera` → CSS transform on a view wrapper around the graph SVG). A single **“Motion controls graph”** switch (owned by `App.tsx`, **off by default**) opts in; a shared `motionCommandRef` carries per-frame motion with **zero** React re-renders. Motion adjusts **only** the orbital camera (yaw→rotateY, pitch→rotateX, zoom→scale); the graph stays **read-only** (no node/edge/data/layout/selection/API mutation). Idle/low-confidence gates to idle, pose is clamped, camera decays to neutral on stillness, `prefers-reduced-motion` holds it neutral, and a compact **Motion camera** readout reports state. **No backend/API/schema/package/dependency change; no new graph/state/physics library; no telemetry/recording/screenshot pass.** See [Motion Sandbox Control Contract + 32G doc](motion-sandbox-control-contract.md) (§22–§29). |
| 32H | Complete | Orbital Graph Control QA + Usability Hardening (**frontend-only**, this phase); QA/tuning pass over the 32G wiring — no new control surface, still **opt-in / off by default / visual-only / read-only**. Calms the camera (gentler yaw/pitch/zoom integration gains + a wider dead zone `0.08` → `0.10` so a lightly off-centre hand no longer creeps or feels twitchy); adds a **staleness guard** (`integrateOrbitalCamera` optionally takes `now` and treats an *active-but-stale* command like idle, so a frozen source frame decays to neutral instead of drifting to the clamp — and cannot jump on re-enable); adds an explicit **Recenter camera** control in the readout (snaps the pose face-on; visual only, never selection/data); and sharpens the opt-in copy (an *Experimental · off by default* pill + clearer visual-only/read-only wording). Helpers stay deterministic (the `now` arg is a pure input). **No backend/API/schema/package/dependency change; no MediaPipe/webcam/Vite/routing change; no new library.** Live hand-motion → camera behaviour not immortalised as screenshots this phase (deferred to 32I). See [Motion Sandbox Control Contract + 32G doc](motion-sandbox-control-contract.md) (§22–§29). |

## Future roadmap

| Future track | Goal | Guardrail |
| --- | --- | --- |
| Intelligence derivation | Dreaming `duplicate_signal` / `orphaned_node` / `stale_knowledge_link` suggestions shipped backend in Phase 14C and frontend-visible in Phase 14D. Remaining: `source_coverage_gap` deferred by the pinned Phase 14B contract/schema state and `unresolved_query_pattern` blocked until query-history persistence exists. | Read-only; no AI/LLM until separately planned. |
| Temporal decay | Backend-derived MVP shipped in Phase 13A, frontend visibility/demo polish shipped in Phase 13B, and end-to-end QA shipped in Phase 13C. Remaining: richer reference/last-seen signals. | No graph mutation; indicators remain advisory. |
| Provenance chains | Backend-derived MVP (Phase 15C), frontend visibility/demo polish (Phase 15D), and QA evidence pass (Phase 15E) complete. Remaining: selected-node inspector extension, per-section error state. | Present existing evidence only; do not invent lineage; read-only. |
| Query trails | Persist and present useful console/search history. Phase 16A defined local/read-only boundaries and relationships; Phase 16B aligned the `QueryTrailEntry` contract; Phase 16C shipped a backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster` from existing source/node/tag structure and made it frontend-visible. Remaining: local query persistence to unblock `repeated_query` / `unresolved_question`. | Read-only structural projection; no query persistence/logging/capture; `repeated_query` / `unresolved_question` stay blocked until real query history exists. |
| Intelligence cohesion | Keep the four backend-derived surfaces (decay, dreaming, provenance, trails) aligned on terminology, evidence shape, empty-state parity, and readiness before adding a fifth. Phase 17A is the planning pass; Phase 17B is the readiness-hardening pass (rationale, thresholds, edge cases, evidence expectations, performance, adapter strategy). | Documentation/cohesion first; no new intelligence logic until the readiness review justifies it. |
| Premium visual system | Move the connected dashboard from a competent light dashboard toward a premium dark-metallic intelligence-console aesthetic with a graph-forward identity. Phase 25A ([planning doc](ui/phase-25a-premium-visual-system-planning.md)) defines the visual system (baseline, identity, principles, surface/panel elevation, typography, graph-centered direction with planned read-only overlay concepts, Intelligence-Report real-vs-planned contract, navigation/demo flow). Phase 25B is the frontend presentation-only implementation pass (token system + per-surface restyle + graph visual language); Phase 25C is the QA + dark-theme screenshot evidence pass. | Presentation-only over the existing token system and SVG view model; graph stays read-only (no mutation/physics/layout-algorithm change); no backend/API/schema/contract/data/package/dependency change; no fake AI/liveliness/telemetry; honest empty-states; planned overlays must be backed by real backend-derived data or labeled planned. |
| Graph-first app shell | Move the app from a dashboard-with-panels layout to a graph-first shell where the Knowledge Graph is the persistent primary viewport and the Source Registry, Intelligence Report, Console, and inspectors become contextual overlays/trays/docks/command surfaces. Phase 27A ([planning doc](ui/phase-27a-graph-first-app-shell-planning.md)) defined the surface model; Phase 27B–27D implemented and corrected the full-viewfinder shell; Phase 27E verified it. Phase 28A ([planning doc](phase-28a-true-graph-primary-overlay-contract.md)) tightens the contract further — full graph dominance, a stricter overlay hierarchy, per-surface panel behavior rules, and an explicit desired/undesired visual-feel test — scoping Phase 28B as the next implementation pass. | Planning before implementation; preserve all existing surfaces and data; no backend/API/schema/dependency change; no 3D/D3/Cytoscape/React Flow; no fake overlays not backed by real data. |
| Agent Ops | Expose governed agent/source registry data in the app. | Start read-only from `docs/agent-lab/` shapes. |
| Security hardening | Owner-authorized, local-only defensive testing and hardening per the [threat model + vulnerability test plan](security/threat-model-and-vulnerability-test-plan.md): API validation/error safety shipped (18B) and regression-verified (18C, [evidence](security/phase-18c-backend-api-security-regression-qa.md)); deferred API edge cases triaged and scoped in 18D ([planning](security/phase-18d-api-edge-case-hardening-planning.md)); the selected edge-case subset (bounded nesting-depth guard + value decisions) shipped in 18E and regression-verified in 18F. Phase 19A ([release-readiness planning](security/phase-19a-security-cohesion-release-readiness-planning.md)) consolidates the arc into a demo-ready (not production-secure) posture and a release-readiness checklist, and Phase 19B ([release-readiness QA + demo evidence](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md)) records the whole-project readiness/demo-evidence posture and boundaries. Remaining: Obsidian import filesystem safety (likely next track), intelligence evidence regression, frontend rendering safety, dependency/static baseline; production-security controls (auth, authorization, rate limiting, deployment hardening, secrets management, audit logging, threat monitoring) stay out of scope until the runtime model changes. | Plan-first; narrow per-route guards over middleware rewrites; demo readiness ≠ production security; no third-party targets; document findings before fixing; preserve read-only intelligence guardrails. |

## Standing guardrails

- Read-only surfaces first.
- Suggestions are advisory and never silently applied.
- Deterministic logic before any AI/LLM integration.
- Additive contracts only.
- No dashboard redesign or branding churn inside backend/API phases.
- Demo fixtures must stay labeled as demo data.
- Human merge gate remains with devdevbuilds.


