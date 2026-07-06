# Phase 30C — Interaction Recovery QA + Screenshot Evidence Refresh

**Date:** 2026-07-05

**Branch:** `phase-30c-interaction-recovery-qa-screenshot-evidence`

## Purpose

Phase 30B implemented the two Phase 30A-triaged interaction defects as a
frontend-only pass (PR #109). Phase 30C is the evidence pass immediately after
that implementation: it verifies the connected runtime behavior against the
Phase 30B fixes and captures fresh screenshots, **without changing the app.**
This is a documentation / QA / screenshot-only phase — no frontend, CSS,
backend, API, schema, package, or graph-logic changes, and **no implementation
fixes** for anything observed. Anything still rough is recorded as a Known
limitation, not patched.

## What Phase 30B was expected to fix

Phase 29C recorded two honest interaction rough edges as Known limitations.
Phase 30B (per the Phase 30A contract) targeted exactly those two:

1. **Dock-close focus recovery.** In 29C, `closePanel` returned focus to the
   rail button that summoned the dock. That button sits *outside* the graph
   panel's Escape scope (`handlePanelKeyDown`), so after a dock closed the very
   next Escape was a dead key until the user re-entered the panel. Phase 30B
   returns focus into the graph panel section instead (`#knowledge-graph`, now
   `tabIndex={-1}` and programmatically focusable but never a tab stop), so the
   `dock → explorer → selection` dismissal stack keeps peeling **press-for-press**
   with no manual refocus and no page refresh. The section's focus outline is
   suppressed since it is programmatic-only chrome.

2. **Responsive rail containment.** In 29C, at ≤420px the focused rail's
   `:focus-within` revealed all four labels at once, widening the rail past the
   viewport edge and clipping the last label. Phase 30B, below the 760px narrow
   breakpoint, no longer reveals all four on `:focus-within`; only the
   hovered/focused button's label reveals, width-clamped to `min(8rem, 42vw)`,
   so the expanded rail always stays on-screen. At-rest icon-only and desktop
   (wider) rail behavior are unchanged, and the label text stays in the
   accessibility tree either way.

## Scope confirmation

Files changed in this phase, and nothing else:

- `README.md` (minimal phase-status/link update)
- `docs/roadmap.md` (minimal phase-status update)
- `docs/demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md` (this doc)
- `docs/demo/screenshots/phase-30c-connected-*.png` (8 new captures)

`apps/frontend/**`, `apps/backend/**`, `package.json`, lockfiles, and all
Vite/API/schema files are untouched.

## Runtime environment summary

- **Backend:** the existing local `uvicorn` instance on port `8787`
  (`npm run dev:backend` equivalent), verified live before QA began. All
  `/api/*` requests returned `200` throughout.
- **Frontend:** Vite dev server on port `5173` serving `apps/frontend`,
  connected to the backend at `http://localhost:8787/api` (the frontend's
  default `VITE_API_BASE_URL`).
- **QA + captures:** headless Chromium (Playwright, run from an out-of-repo
  scratch workspace so no dependency touches this repo) driving the real
  connected frontend at `http://localhost:5173/` — desktop viewport 1440×900,
  narrow viewport 420×850. All screenshots are unedited browser captures saved
  directly by the browser run.

> **Honest runtime note (harness, not an app defect).** The backend's CORS
> allow-list is `http://localhost:5173` / `http://127.0.0.1:5173`. When a second
> browser harness was first pointed at an auto-assigned alternate port (because
> `5173` was already bound by the running dev server), its cross-origin `/api`
> calls were rejected with `net::ERR_FAILED` and the app read `Disconnected`.
> This is purely an origin/port artifact of the capture harness, **not** a
> runtime bug: driven against the CORS-allowed `http://localhost:5173/` origin,
> the app connects cleanly with zero console errors and zero failed requests
> (see below). No backend/CORS change was made — the QA simply used the correct
> allowed origin.

## Connected endpoints verified

Queried directly against the live backend during this phase:

- `GET /api/health` → `{"ok":true,"service":"hivemind-backend","version":"0.1.0"}`.
- `GET /api/knowledge-graph` → **7 nodes / 6 edges** — the same mock dataset as
  every prior evidence phase (`Hive|Mind`, `Local Model Registry`,
  `API Contracts`, `Dev Folder Source`, `Dev Markdown Notes`,
  `Dashboard Placeholder`, `Roadmap Notes`).
- `GET /api/intelligence/report` → `report_version 0.1.0`, `read_only: true`,
  `dreaming_suggestions: 0`, `decay_statuses: 7`, `provenance_chains: 7`,
  `query_trail_entries: 7` — identical counts to the established
  21F/22C/23B/25C/26C/27E/28C/29C evidence trail.
- `GET /api/registry/sources` → `{"sources": []}` — the Source Registry is
  empty, consistent with the unpopulated-registry/vault-vs-mock-graph split
  documented since Phase 27E (the graph renders the mock fixture; the registry
  and vault importer are not populated).
- `GET /api/vault/summary` → `totalFiles/totalSources/totalModels/totalNodes: 0`,
  `graphMode: "not_initialized"` — the same honest empty vault state recorded in
  every prior phase.
- The connected frontend rendered the graph-primary shell with the `Connected`
  status pill; **no `Failed to fetch`, no console errors, and no failed / 4xx /
  5xx requests** were observed at any point during the full scripted QA run
  against the `5173` origin.

## Screenshot inventory

All 8 captures are real, connected-runtime browser screenshots taken against
the local `5173`/`8787` servers described above, each visually re-verified
against its claimed state before this doc was written. Stored in
[`docs/demo/screenshots/`](screenshots/).

| File | State shown |
| --- | --- |
| `phase-30c-connected-graph-default.png` | Default at-rest shell: full-viewport graph, floating masthead (`Connected` pill), icon-only `V`/`S`/`I`/`C` capsule rail (no labels revealed). No inspector, explorer, or dock auto-opened. |
| `phase-30c-connected-node-selected.png` | `Local Model Registry` selected: strongest glow on the selection, energy-dash edge to the related `Hive\|Mind` node, all other nodes/edges dimmed (three tiers legible at a glance), floating `INSPECTOR` card showing backend-derived data (`node-model-local`, Model, 0 in · 1 out, `mock: true`). Inspector is a bounded 352×262 card, not a viewport majority. |
| `phase-30c-connected-tools-overlay.png` | `Legend & lists` explorer summoned: bounded translucent pane (Node Types, Relationships, Status, Groups, Top Connected Nodes) over the still-visible graph; toggle reads `Hide legend`. |
| `phase-30c-connected-dock-open.png` | `Intelligence` rail item open: the `Intelligence Report` dock (Suggestions 0 / Decay 7 / Provenance 7 / Query Trails 7, `Mode: Read-only`) as a bounded 422px right-side glass drawer; graph remains the dominant surface. |
| `phase-30c-connected-dock-close-recovery.png` | Recovery mid-state — with a node selected, the explorer open, and a dock open, the **first Escape closed only the dock**: the dock is gone while the `LEGEND & LISTS` explorer (left) and the `INSPECTOR` selection card (right) both persist, and focus is back inside the graph panel. Proves the dock closes independently and focus recovers. |
| `phase-30c-connected-escape-recovery.png` | Fully recovered bare graph after the third Escape: no inspector, no explorer, all seven nodes at full brightness (no dimming = no selection). Reached purely by successive Escape presses with **no manual refocus and no page refresh**. |
| `phase-30c-connected-narrow-rail.png` | Narrow 420×850 viewport: full-viewport graph, floating masthead, and the bottom rail with **only the hovered `Sources` label revealed** (width-clamped), the rail fully within the screen edge — no overflow, no clipped label. The Phase 30B responsive-rail fix in situ. |
| `phase-30c-connected-full-view.png` | Full connected desktop view (1440×900): graph dominates the surface edge-to-edge, `Connected` pill, icon-only rail — the graph-primary visual contract intact. |

## Interaction recovery QA notes

The QA run drove the real app in a browser and asserted DOM/focus state per the
Phase 30A/30B contract. 20 scripted checks ran; **20/20 passed.** The
recovery-specific results:

| # | Check | Result |
| --- | --- | --- |
| 1 | Connected runtime: graph canvas rendered + `Connected` status pill | PASS |
| 2 | Backend-derived graph rendered (7 nodes / 6 edges) | PASS |
| 3 | Default state is a bare graph — no inspector/explorer/dock auto-opens on load | PASS |
| 4 | Node selection produces three-tier emphasis (1 selected, 1 related, 5 dimmed) + floating inspector | PASS |
| 5 | Inspector stays a bounded card (352×262 in 1440×900), graph remains primary | PASS |
| 6 | Tools overlay (explorer) opens as a bounded pane (386px of 1440), graph primary | PASS |
| 7 | Dock opens as a single bounded drawer (Intelligence Report, 422px of 1440) | PASS |
| 8 | **Dock CLOSE button returns focus into the graph panel** (`activeElement.id === "knowledge-graph"`) | PASS |
| 9 | Recovery setup: selection + explorer + dock all open simultaneously | PASS |
| 10 | **Escape #1 closes only the dock AND returns focus to the graph panel** (explorer + selection persist) | PASS |
| 11 | **Escape #2 (no manual refocus) closes the explorer**, selection persists | PASS |
| 12 | **Escape #3 (no manual refocus) clears selection + inspector → bare graph** | PASS |
| 13 | **Full recovery to bare graph via keyboard only — no page refresh needed** (0 overlays/selection left) | PASS |
| 14 | Graph remains the primary interaction target after recovery (node re-selectable) | PASS |

The two Phase 29C caveats — Escape #2 and Escape #3 previously required a manual
refocus into the panel — **both pass press-for-press this phase with no manual
refocus**, confirming the Phase 30B dock-close focus-return fix.

## Responsive rail QA notes

At the narrow 420×850 viewport (below the 760px breakpoint):

| # | Check | Result |
| --- | --- | --- |
| 15 | `:focus-within` no longer reveals all four labels — with the rail focused, revealed labels ≤ 1 and the rail is fully within the viewport (`railRight 329 ≤ 420`) | PASS |
| 16 | Hovering one rail button reveals **only that button's** width-clamped label (`Sources`, 128px) and the rail stays on-screen (`railRight 339 ≤ 420`) | PASS |
| 17 | Graph remains the dominant surface at 420px (`420×901` canvas visible) | PASS |

This is the direct inverse of the Phase 29C observation, where the focused rail
widened past the viewport edge and clipped the last label. The at-rest rail
stays icon-only (see `phase-30c-connected-graph-default.png`), matching the
compact contract.

## Graph-primary visual contract

| # | Check | Result |
| --- | --- | --- |
| 18 | Full view: connected, and the graph dominates the app surface (graph area > 50% of viewport) | PASS |

Across every captured state the graph is the full application surface; the
inspector (bounded card), explorer (386px pane), and dock (422px drawer) all
remain secondary, contextual overlays. No persistent sidebar, card-grid, or
SaaS-dashboard pattern returned, and the dark shell / glass-overlay direction is
intact.

## Browser console / network observations

| # | Check | Result |
| --- | --- | --- |
| 19 | No browser console errors during the whole QA run | PASS (0 errors) |
| 20 | No failed / 4xx / 5xx requests (no `Failed to fetch`) | PASS (0 failures) |

- Browser console: only Vite HMR debug lines and the React DevTools info notice;
  **zero errors** across page load and every interaction above.
- Network: all requests to `http://localhost:8787/api/*` returned `200`; no
  request failures of any kind against the `5173` origin, hence no
  `Failed to fetch` surfaces.
- The QA run exercised the app read-only throughout — only clicks/hovers/keys the
  UI offers; nothing was mutated.

## Validation commands and results

| Command | Result |
| --- | --- |
| `git status --short` | Clean before starting; after the phase, only this doc, README, roadmap, and the 8 new screenshots appear in the diff. |
| `git diff --name-only` | Confirms only docs/screenshot evidence files changed (see Scope confirmation). |
| `npm run check:frontend` | **PASS** — `tsc -b && vite build` completed with 0 errors. |
| `curl http://localhost:8787/api/health` | **PASS** — `200 OK`, `hivemind-backend 0.1.0`. |
| `curl http://localhost:8787/api/knowledge-graph` | **PASS** — 7 nodes / 6 edges. |
| `curl http://localhost:8787/api/intelligence/report` | **PASS** — Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7, `read_only: true`. |
| `curl http://localhost:8787/api/registry/sources` | **PASS** — `{"sources": []}` (empty registry, honest). |
| `curl http://localhost:8787/api/vault/summary` | **PASS** — honest `not_initialized` empty vault state. |

Backend tests were **not run** because no backend file was touched (per phase
scope).

## Pass/fail summary

**PASS.** 20/20 contract checks verified against the connected runtime, with the
two Phase 29C interaction caveats now passing press-for-press. All 8 required
screenshots captured, visually re-verified, and inventoried. Frontend build
check passes. No behavior, contract, or data change of any kind.

## Files changed

- `README.md` — minimal Phase 30C status/link update.
- `docs/roadmap.md` — minimal Phase 30B/30C status update.
- `docs/demo/phase-30c-interaction-recovery-qa-screenshot-evidence.md` — this doc.
- `docs/demo/screenshots/phase-30c-connected-*.png` — 8 new captures.

## Guardrails preserved

- No frontend source changes (`apps/frontend/src/**` untouched).
- No CSS changes (`styles.css` untouched).
- No backend changes (`apps/backend/**` untouched).
- No API/schema/contract changes.
- No package/dependency changes (`package.json` / lockfiles untouched; the
  Playwright capture harness lived entirely in an out-of-repo scratch workspace).
- No Vite/config changes.
- No fake or demo-only data — every value visible in the screenshots is the
  backend's own response.
- No graph mutation; the app was exercised read-only.
- No new graph library.
- No screenshot invention or post-capture editing — all 8 images are direct
  browser output from the connected runtime.
- No implementation fixes — nothing observed was patched in this phase.

## Known limitations

- **None new.** Both Phase 29C interaction limitations (Escape dead-key after
  dock close; focused-rail label overflow at ~420px) are resolved by Phase 30B
  and verified above. The only environment nuance is the CORS/origin harness
  note recorded under *Runtime environment summary* — a capture-harness
  characteristic, not an app defect, and not changed.
- The Source Registry (`{"sources": []}`) and Vault summary (`not_initialized`,
  zeroed counts) remain empty versus the graph's populated 7-node/6-edge mock
  dataset — the same pre-existing, previously-documented split between the
  unpopulated registry/vault importer and the mock graph fixture noted since
  Phase 27E. Left unchanged.

## Why this phase matters

Phase 30B fixed the two interaction defects that most directly undermined the
graph-primary promise: a keyboard user who opened a dock could get "stuck" one
dead Escape away from recovering, and a narrow-viewport user saw the rail break
its own compact contract. Phase 30C is the honest proof that those fixes hold
against the *real* connected app — a keyboard-only user can now peel every
summoned surface back to a bare graph press-for-press without a refresh, and the
rail stays contained at phone widths — while confirming nothing else regressed
and no data, contract, or behavior changed. Evidence, not assertion, is what
keeps the portfolio narrative trustworthy.

## Statement of scope

This phase produced documentation, QA verification, and screenshot evidence
only. No application code, style, configuration, dependency, API, schema, or
data behavior was changed.
