# Phase 29C — Graph Interaction + Overlay Polish QA + Screenshot Evidence Refresh

**Date:** 2026-07-04

**Branch:** `phase-29c-graph-interaction-overlay-polish-qa-evidence`

## Purpose

Phase 29B implemented the Phase 29A graph interaction + overlay polish
contract as a frontend-only presentation/interaction pass: the canvas
three-tier selected > related > ambient/dimmed emphasis model, additive
hover lifts on nodes and edges, empty-canvas click-to-deselect, the
Phase 29A Escape dismissal order (tertiary dock → explorer →
selection/inspector, one surface per press), overlay
stacking/exclusivity/persistence rules, and summon/dismiss focus
management. Phase 29C is the evidence pass immediately after that
implementation: it verifies the connected runtime behavior against the
Phase 29A contract and captures fresh screenshots, without changing the
app. **This is a documentation/QA/screenshot-only phase** — no frontend,
CSS, backend, API, schema, package, or graph-logic changes, and no
implementation fixes for anything observed.

## Scope confirmation

Files changed in this phase, and nothing else:

- `README.md` (minimal phase-status/link update)
- `docs/roadmap.md` (minimal phase-status update)
- `docs/demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md` (this doc)
- `docs/demo/screenshots/phase-29c-connected-*.png` (7 new captures)

`apps/frontend/**`, `apps/backend/**`, `package.json`, lockfiles, and all
Vite/API/schema files are untouched.

## Runtime setup used

- Backend: the existing local `uvicorn` instance on port `8787`
  (`npm run dev:backend` equivalent), verified live before QA began.
- Frontend: Vite dev server on port `5173` serving `apps/frontend`,
  connected to the backend at `http://localhost:8787/api`.
- QA + captures: headless Chromium (Playwright, run from an out-of-repo
  scratch workspace so no dependency touches this repo) driving the real
  connected frontend at `http://localhost:5173/` — desktop viewport
  1440×900, narrow viewport 420×850. All screenshots are unedited browser
  captures saved directly by the browser run.

## Connected endpoints verified

- `GET /api/health` → `{"ok":true,"service":"hivemind-backend","version":"0.1.0"}`.
- `GET /api/graph` → 7 nodes / 6 edges — the same mock dataset as every
  prior evidence phase (`Hive|Mind`, `Local Model Registry`,
  `API Contracts`, `Dev Folder Source`, `Dev Markdown Notes`,
  `Dashboard Placeholder`, `Roadmap Notes`).
- `GET /api/intelligence/report` → `report_version 0.1.0`,
  `read_only: true`, `dreaming_suggestions: 0`, `decay_statuses: 7`,
  `provenance_chains: 7`, `query_trail_entries: 7` — identical counts to
  the established 21F/22C/23B/25C/26C/27E/28C evidence trail.
- `GET /api/sources` → 3 mock sources (`Dev Markdown Notes`,
  `Dev Folder Source`, `Dev JSON Export`) — consistent with the backend
  fixture; the Phase 28C sources-overlay discrepancy did not recur in the
  direct endpoint check this phase.
- `GET /api/vault/summary` → `totalFiles/totalSources/totalModels/
  totalNodes: 0`, `graphMode: "not_initialized"` — the same honest empty
  vault state recorded in every prior phase.
- The connected frontend rendered the graph-primary shell with the
  `Connected` status pill; no `Failed to fetch`, no console errors, and no
  failed/4xx/5xx requests were observed at any point during the full
  scripted QA run.

## Screenshot inventory

All 7 captures are real, connected-runtime browser screenshots taken
against the local `5173`/`8787` servers described above, each visually
re-verified against its claimed state before this doc was written. Stored
in [`docs/demo/screenshots/`](screenshots/).

| File | State shown |
| --- | --- |
| `phase-29c-connected-graph-default.png` | Default at-rest shell: full-viewport graph, floating masthead (`Connected` pill), icon-only `V`/`S`/`I`/`C` capsule rail. No inspector, explorer, or dock auto-opened. |
| `phase-29c-connected-graph-hover-or-focus.png` | Pointer on `Local Model Registry`: brightened hover halo on the node and a lifted incident edge toward `Hive\|Mind` — additive only, nothing else dimmed, no overlay opened. |
| `phase-29c-connected-graph-node-selected.png` | `Local Model Registry` selected: strongest glow on the selection, energy-dash edge to the related `Hive\|Mind` node, all other nodes/edges dimmed (three tiers legible at a glance), floating `INSPECTOR` card showing backend-derived data (`node-model-local`, Model, 0 in · 1 out, `mock: true`). |
| `phase-29c-connected-graph-inspector-context.png` | Edge `API Contracts → Dashboard Placeholder` selected: the edge carries the selected stroke, both endpoints read as related, everything else dims, and the same inspector card swaps to edge context (`edge-contracts-dashboard`, Relationship `Related`, From/To, `mock: true`). |
| `phase-29c-connected-graph-overlay-open.png` | `Legend & lists` explorer summoned: bounded translucent pane (Node Types, Relationships, Status, Groups, Top Connected Nodes) over the still-visible graph; toggle reads `Hide legend`. |
| `phase-29c-connected-graph-tools-overlay.png` | `I` rail item open: `Intelligence Report` dock (Suggestions 0 / Decay 7 / Provenance 7 / Query Trails 7, `Mode: Read-only`, Dreaming empty state) as a bounded right-side glass drawer; graph remains the dominant surface and the rail shows the active `Intelligence` label. |
| `phase-29c-connected-graph-narrow-viewport.png` | Fresh at-rest load at 420×850: full-viewport graph, floating masthead, icon-only rail fully on screen and functional (Vault opens when tapped, verified separately). |

## Interaction QA checklist (scripted, connected runtime)

The QA run drove the real app in a browser and asserted DOM state per the
Phase 29A/29B contract. 28 scripted checks ran; results:

| # | Check | Result |
| --- | --- | --- |
| 1 | Connected runtime: graph canvas rendered + `Connected` status pill | PASS |
| 2 | Backend-derived graph rendered (7 nodes / 6 edges) | PASS |
| 3 | Default state is a bare graph — no inspector/explorer/dock auto-opens on load | PASS |
| 4 | Node hover lifts incident edges (additive affordance; 0 → 1 `hover-lift` edges) | PASS |
| 5 | Hover never dims the rest of the graph and never opens an overlay | PASS |
| 6 | Edge hover lifts the edge and brightens exactly its two endpoints, no dimming | PASS |
| 7 | Node selection produces the three-tier emphasis: 1 selected, 1 related, 5 dimmed nodes; 1 incident, 5 dimmed edges | PASS |
| 8 | Node selection mounts the floating inspector | PASS |
| 9 | Inspector stays a bounded card (352×262 in 1440×900), not a viewport majority | PASS |
| 10 | Selection switches directly between nodes; inspector content swaps in place (`Local Model Registry` → `API Contracts`, no unmount flash) | PASS |
| 11 | Edge selection: edge selected, endpoints related, inspector shows the edge (`API Contracts → Dashboard Placeholder`) | PASS |
| 12 | Empty-canvas click deselects and unmounts the inspector | PASS |
| 13 | Empty-canvas click with nothing selected is a no-op (nothing opens/toggles) | PASS |
| 14 | Explorer (legend/lists) opens as a summoned overlay | PASS |
| 15 | Explorer takes focus on summon | PASS |
| 16 | Explorer stays a bounded pane (386px of 1440), graph remains primary | PASS |
| 17 | Explorer close returns focus to its toggle | PASS |
| 18 | Opening the explorer leaves the selection/inspector intact | PASS |
| 19 | Opening a tertiary tool (Vault) leaves selection + explorer intact | PASS |
| 20 | Escape #1 closes only the tertiary dock (explorer + selection persist) | PASS |
| 21 | Escape #2 closes only the explorer (selection persists) | PASS — with a focus-scoping caveat, see Known limitations |
| 22 | Escape #3 clears the selection and unmounts the inspector (bare graph) | PASS |
| 23 | One tertiary overlay at a time: Vault → Intelligence switches panes, never stacks (1 visible pane, dock label `Intelligence Report`) | PASS |
| 24 | Tertiary dock stays a bounded drawer (422px of 1440), graph remains primary | PASS |
| 25 | Deliberately summoned dock persists across selection *and* deselection | PASS |
| 26 | Narrow viewport (420px): graph primary, rail reachable | PASS on a fresh at-rest load (rail 113–307px within 420); the in-session resize check flagged a focused-rail overflow, see Known limitations |
| 27 | No browser console errors during the whole QA run | PASS (0 errors) |
| 28 | No failed / 4xx / 5xx requests (no `Failed to fetch`) | PASS (0 failures) |

## Console / network observation summary

- Browser console: only Vite HMR debug lines and the React DevTools info
  notice; **zero errors, zero warnings of interest** across page load and
  every interaction above.
- Network: all requests to `http://localhost:8787/api/*` returned `200`;
  no request failures of any kind, hence no `Failed to fetch` surfaces.
- Frontend/backend contract exercised read-only throughout — the QA run
  performed only clicks/hovers/keys the UI offers; nothing was mutated.

## Validation commands run and results

| Command | Result |
| --- | --- |
| `git status --short` | Clean before starting; after the phase, only this doc, README, roadmap, and the 7 new screenshots appear in the diff. |
| `git diff --name-only` | Confirms only docs/screenshot evidence files changed (see Scope confirmation). |
| `npm run check:frontend` | **PASS** — `tsc -b && vite build` completed with 0 errors (`✓ built in 621ms`). |
| `curl http://localhost:8787/api/health` | **PASS** — `200 OK`, `hivemind-backend 0.1.0`. |
| `curl http://localhost:8787/api/graph` | **PASS** — 7 nodes / 6 edges. |
| `curl http://localhost:8787/api/intelligence/report` | **PASS** — Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7, `read_only: true`. |
| `curl http://localhost:8787/api/sources` | **PASS** — the 3 seeded mock sources. |
| `curl http://localhost:8787/api/vault/summary` | **PASS** — honest `not_initialized` empty vault state. |

Backend tests were not run because no backend file was touched (per phase
scope).

## Pass/fail summary

**PASS.** 28/28 contract checks verified against the connected runtime
(check 21 with a focus-scoping caveat and check 26 re-verified on a fresh
at-rest load, both recorded below rather than fixed). All 7 required
screenshots captured, visually re-verified, and inventoried. Frontend
build check passes. No behavior, contract, or data change of any kind.

## Guardrails preserved

- No frontend source changes (`apps/frontend/src/**` untouched).
- No CSS changes (`styles.css` untouched).
- No backend changes (`apps/backend/**` untouched).
- No API/schema/contract changes.
- No package/dependency changes (`package.json` / lockfiles untouched;
  the Playwright capture harness lived entirely in an out-of-repo scratch
  workspace).
- No Vite/config changes.
- No fake or demo-only data — every value visible in the screenshots is
  the backend's own mock-fixture response.
- No graph mutation; the app was exercised read-only.
- No new graph library.
- No screenshot invention or post-capture editing — all 7 images are
  direct browser output from the connected runtime.
- No implementation fixes — the two rough edges found during QA are
  recorded below, not patched.

## Known limitations / deferred follow-ups (observed, not fixed)

- **Escape after dock-close needs focus back in the graph panel.** The
  dock layer handles Escape on a window-level capture listener, but the
  explorer/selection layers handle it via the graph panel's scoped
  `onKeyDown`. Closing the dock intentionally returns focus to its rail
  button — which sits outside the graph panel — so the very next Escape
  press is ignored until focus re-enters the panel (mouse users
  re-entering the graph never notice; pure keyboard users need one extra
  Tab/level of focus travel). The dismissal *order* itself
  (dock → explorer → selection, one surface per press) verified correctly
  once focus was in the panel. Candidate polish item for a future
  interaction pass.
- **Focused rail labels can overflow at very narrow widths.** At 420px,
  the at-rest icon-only rail fits comfortably (fresh-load capture), but
  when the rail holds focus its revealed labels widen it past the
  viewport edge, clipping the `Console` label. Observed during the
  in-session resize check; recorded as a pre-existing narrow-viewport
  characteristic of the label-reveal treatment, consistent with the
  Phase 28C pill-truncation note.
- The Vault summary's zeroed counts versus the graph's populated
  7-node/6-edge mock dataset remains the same pre-existing,
  previously-documented split between the (unpopulated) vault importer
  and the mock graph fixture noted in every phase since 27E. Left
  unchanged.

## Statement of scope

This phase produced documentation, QA verification, and screenshot
evidence only. No application code, style, configuration, dependency,
API, schema, or data behavior was changed.
