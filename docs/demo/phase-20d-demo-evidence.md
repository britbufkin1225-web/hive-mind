# Phase 20D — Final Demo Screenshot + Evidence Capture Pass

Parent label: **devdevbuilds**

**Status: complete (capture / documentation only).** Phase 20D executes the
[Phase 20A screenshot/evidence plan](../release-readiness/phase-20a-demo-release-candidate-planning.md#screenshot--demo-evidence-plan)
against **real, locally running app state** and records the captured evidence. It
adds **no** backend, frontend, CSS, source-code, package, config, schema,
dependency, or test change, and changes no application behavior. It captures and
documents what was observed; it does not fix anything.

This is the evidence companion to the [Final Demo Script](final-demo-script.md),
the [Portfolio Presentation Lock](portfolio-presentation-lock.md), and the
[Screenshot Checklist](../screenshot-checklist.md).

> **Authenticity rule (from Phase 20A).** Evidence must reflect real app state
> produced by normal demo/import behavior — no invented, mocked, hand-edited, or
> staged-beyond-real-behavior content. Where a surface did not render, the real
> observed state is recorded honestly rather than fabricated.

---

## What was captured

The **backend runtime was verified directly** by calling the live API and
capturing the responses. During this capture the backend was reached locally at
`http://127.0.0.1:8000`. Four endpoints were exercised and returned real data:

- `GET /api/health` — service identity and health.
- `GET /api/sources` — the Source Registry contents.
- `GET /api/graph` — the Knowledge Graph nodes/edges.
- `GET /api/intelligence/report` — the full Intelligence Report payload with all
  four backend-derived sections plus the summary rollup.

The captures are PowerShell `Invoke-RestMethod` / `Test-NetConnection` sessions
against the running backend — i.e. the system's own runtime, not fixtures or
mockups.

## Captured evidence

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). Each is
documented by the command and response actually visible in the image (filenames
are recorded as saved):

| File | Command shown | What it evidences |
| --- | --- | --- |
| `phase-20d-backend-health-response.png` | `Test-NetConnection 127.0.0.1 -Port 8000` | Backend TCP port reachable locally (`TcpTestSucceeded : True`). |
| `phase-20d-backend-port-8000-open.png` | `Invoke-RestMethod http://127.0.0.1:8000/api/health` | Health endpoint returns `ok=True`, `service=hivemind-backend`, `version=0.1.0`. |
| `phase-20d-backend-sources-graph-response.png` | `Invoke-RestMethod .../api/sources` and `.../api/graph` | Source Registry returns a real source (`src-dev-markdown`, "Dev Markdown Notes", `type=markdown`, `status=active`); graph returns nodes (`node-root`, label `Hive\|Mind`, `type=root`). |
| `phase-20d-backend-intelligence-report-top.png` | `Invoke-RestMethod .../api/intelligence/report` (top) | Report header (`report_version 0.1.0`, `generated_at`) and the backend-derived decay/dreaming/provenance sections with their evidence metadata. |
| `phase-20d-backend-intelligence-report-summary.png` | `Invoke-RestMethod .../api/intelligence/report` (continued) | Query-trail entries and the `summary` rollup, completing the four-section read-only report. |

Together these show the backend serving the Source Registry, the Knowledge Graph,
and a fully backend-derived, read-only Intelligence Report (Temporal Decay,
Dreaming Suggestions, Provenance Chains, and Query Trails) over real local state.

## Frontend runtime observation

During this capture, the **frontend browser state showed a fetch failure** — the
UI did not load the backend data into its panels. This is recorded here as honest,
captured runtime evidence of what was observed.

**Frontend troubleshooting is explicitly out of scope for Phase 20D.** This phase
is a capture/evidence pass, not a fix pass. No frontend, CSS, config, or source
change is made here, and the fetch failure is documented rather than diagnosed or
resolved. Because the UI did not render the data, the backend runtime was verified
**directly through the API** (the captures above), which is the authentic evidence
that the system's backend behaves as documented.

Any frontend rendering/connection work belongs to a separate, explicitly scoped
phase — it is deliberately not undertaken here.

## What is intentionally not captured here

- **Rendered frontend UI screenshots** of the dashboard, graph panel, and
  Intelligence Report panel — deferred, given the observed frontend fetch failure
  and the capture-only scope. Capturing a non-rendering UI as if it were a working
  surface would violate the authenticity rule.
- **Any fix** for the frontend fetch failure — out of scope (see above).
- **New surfaces, mutation, AI/LLM, persistence, or production claims** — out of
  scope, consistent with the locked demo narrative.

## Honesty boundaries (unchanged)

- All four Intelligence Report sections are **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- The backend evidence reflects a **local, single-user, demo-grade** runtime — not
  a production or hosted deployment.
- Evidence reflects the **recorded capture session**; it is not a CI guarantee or
  a coverage promise.

## Scope confirmation

Phase 20D did **not**:

- change backend, frontend, CSS, source code, package files, configs, schema,
  dependencies, or tests;
- change any API contract or runtime behavior;
- fix, diagnose, or work around the observed frontend fetch failure;
- invent, mock, hand-edit, or stage any screenshot or response;
- add AI/LLM, persistence, auth, or mutation.

The change set is documentation/evidence only: this evidence document, the saved
backend-runtime screenshots, and narrow status/link updates to the README and
roadmap. **No application behavior changed.**
