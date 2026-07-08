# Phase 33E — 2.5D Spatial Hive QA + Screenshot Evidence Refresh

**Date:** 2026-07-07

**Branch:** `phase-33e-2-5d-spatial-hive-qa-screenshot-evidence-refresh`

**Commit (before this evidence commit):** `ed3b8ec` — *frontend: harden 2.5d
spatial hive ux and motion compatibility (#132)* — the tip of `main` this branch
was cut from. The after-hash is this doc's own evidence commit (see `git log`).

## Purpose

Phase 33C (spatial-depth foundation, PR #131) introduced the 2.5D Spatial Hive
graph, and Phase 33D (UX + motion compatibility, PR #132) hardened it. Phase 33E
is the **evidence-only** pass immediately after those two: it validates,
launches, and visually QA's the **current** 2.5D Spatial Hive surface against the
real connected local runtime, then refreshes the screenshot evidence — **without
changing the app.** This is a documentation / QA / screenshot-only phase: no
frontend, CSS, React, backend, API, schema, package, dependency, or graph-logic
changes, and **no implementation fixes** for anything observed. Anything rough is
recorded as a Known limitation, not patched.

## The 2.5D Spatial Hive under test

From `apps/frontend/src/components/KnowledgeGraphPanel.tsx` (Phase 33C model),
each node resolves to **one discrete depth tier** — `near`, `mid`, or `far` —
applied as a `graph-depth-tier-<tier>` class on the node `<g>` and scaling its
whole visual mass (`near 1.12 > mid 1.0 > far 0.9`, a monotonic, tightly-bounded
ramp that reads as believable depth, not a cartoon zoom):

- **Hive-State (at rest):** the tier is **structural** — degree-ranked so busy
  hubs come forward, id-hash spread so equal-degree nodes layer across tiers, so
  the idle field already reads as layered space rather than a flat band.
- **Focus-State (a node selected):** the tier becomes **relationship-driven** —
  the selected node lifts to `near`, its related cluster to `mid`, everything
  else recedes to `far`, so attention reads spatially.
- **Edges** inherit the nearer endpoint's tier (`graph-depth-edge-<tier>`), so
  the connective tissue fades front-to-back coherently with the nodes.

## Scope confirmation

Files added/changed in this phase, and nothing else:

- `README.md` — minimal current-phase / evidence-link update.
- `docs/roadmap.md` — minimal phase-status update (33C/33D marked shipped, 33E
  evidence status).
- `docs/demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md` — this doc.
- `docs/demo/screenshots/phase-33e-spatial-hive-*.png` — 5 new captures.

`apps/frontend/**`, `apps/backend/**`, `package.json`, lockfiles, and all
Vite/API/schema/MediaPipe files are **untouched**. `git status` before the
evidence commit showed only the 5 new screenshots as changes; no source or
runtime file appears in the diff.

## Runtime environment summary

- **Backend:** the repo's documented local `uvicorn` app on port `8787`
  (`npm run dev:backend` equivalent — `python -m uvicorn app.main:app --app-dir
  apps/backend --host 0.0.0.0 --port 8787 --reload`), launched from the existing
  `.claude/launch.json` `backend` config. Verified live before QA began; all
  `/api/*` requests returned `200` throughout.
- **Frontend:** the repo's documented Vite dev server on port `5173` serving
  `apps/frontend` (`.claude/launch.json` `frontend` config), connected to the
  backend at `http://localhost:8787/api` (the frontend's default
  `VITE_API_BASE_URL`). No port, env, API base URL, or app-wiring change was made.
- **QA + captures:** headless Chromium (Playwright, run from an **out-of-repo**
  scratch workspace so no dependency touches this repo) driving the real
  connected frontend at `http://localhost:5173/` — desktop viewport 1440×900. A
  second Chromium context emulated `prefers-reduced-motion: reduce` for the
  reduced-motion check. All screenshots are unedited browser captures saved
  directly by the browser run.

## Connected endpoints verified

Queried directly against the live backend during this phase:

- `GET /api/health` → `{"ok":true,"service":"hivemind-backend","version":"0.1.0"}`.
- `GET /api/knowledge-graph` → **7 nodes / 6 edges** — the same mock dataset as
  every prior evidence phase (`Hive|Mind`, `Local Model Registry`, `API
  Contracts`, `Dev Folder Source`, `Dev Markdown Notes`, `Dashboard Placeholder`,
  `Roadmap Notes`).
- `GET /api/intelligence/report` → `report_version 0.1.0`, `read_only: true`.

## Validation commands and results

| Command | Result |
| --- | --- |
| `npm run check:frontend` | **PASS** — `tsc -b && vite build` completed with 0 errors (41 modules transformed, built in ~0.9s). |
| `git diff --check` | **PASS** — no whitespace/conflict errors. |
| conflict-marker scan (`<<<<<<< / ======= / >>>>>>>`) on touched docs | **PASS** — none found. |
| `git status --short` (before evidence commit) | Only the 5 new `phase-33e-spatial-hive-*.png` screenshots; **no source/runtime files**. |

Backend tests (`npm run check:backend`) were **not run** — no backend file was
touched (per phase scope).

## Browser QA — automated checks

The QA run drove the real connected app in a browser and asserted DOM / depth /
focus / console state. **16 scripted checks ran; 16/16 passed.**

| # | Check | Result | Detail |
| --- | --- | --- | --- |
| 1 | Connected runtime: graph canvas rendered + `Connected` status pill | PASS | |
| 2 | Backend-derived graph is the primary surface | PASS | 7 nodes / 6 edges |
| 3 | **2.5D near/mid/far depth tiers ALL present at rest** (structural depth) | PASS | nodes near=3 mid=3 far=1 |
| 4 | Edges carry inherited depth tiers coherently across the field | PASS | edges near=5 mid=1 far=0 (6 total) |
| 5 | Depth scale ramp is monotonic `near > mid > far` (believable depth) | PASS | `{near:1.12, mid:1, far:0.9}` |
| 6 | Node labels legible — every node renders visible label text | PASS | 7/7 visible, 0 empty |
| 7 | Default state is a bare 2.5D graph (no inspector/explorer/dock auto-open) | PASS | inspector=0 explorer=false dock=0 |
| 8 | Selected node: three-tier emphasis (selected > related > dimmed) + inspector | PASS | selected=1 related=1 dimmed=5 inspector=true |
| 9 | **Focus-State depth: the selected node lifts to the NEAR tier** | PASS | selected node has `graph-depth-tier-near` |
| 10 | Inspector stays a bounded card; graph remains dominant | PASS | inspector 352×262 in 1440×900 |
| 11 | Explorer overlay opens bounded; graph remains > 50% of surface | PASS | explorer 386px of 1440; graph primary |
| 12 | Selection/inspection smoke: node re-selects, inspector shows, Escape clears | PASS | reselect + inspector + Esc-clear all true |
| 13 | Full view: connected, 2.5D graph dominates the app surface (> 50%) | PASS | graph 1440×951 of 1440×900 viewport |
| 14 | **Reduced-motion:** graph renders, depth tiers persist, selection works | PASS | 7 nodes, tiers 3/3/1, selectable, 0 console errors |
| 15 | No browser console errors during the whole QA run | PASS | 0 errors |
| 16 | No failed / 4xx / 5xx requests (no `Failed to fetch`) | PASS | 0 failures |

## Browser QA — narrative observations

- **Graph is the primary visual surface.** In every captured state the SVG graph
  fills the app surface (> 50% of the viewport); the inspector (bounded 352×262
  card), the Legend & Lists explorer (386px pane), and the workspace dock all
  remain secondary, contextual overlays. No persistent sidebar, card-grid, or
  SaaS-dashboard pattern returned — the dark-shell / graph-owns-color direction is
  intact.
- **2.5D depth tiers are visible.** At rest the seven nodes spread across all
  three tiers (near ×3 / mid ×3 / far ×1); node visual mass scales with tier
  (`Hive|Mind` and other near hubs read forward, `Dashboard Placeholder` recedes),
  and edges fade front-to-back with their nearer endpoint. The depth reads as
  layered space, not a flat map.
- **Selected-node state is readable.** Selecting `Local Model Registry` lifts it
  to the near tier with the strongest glow, draws the energy-dash edge to the
  related `Hive|Mind` node (mid), and recedes/dims the rest to far — a clear
  three-tier emphasis at a glance, with the bounded INSPECTOR card showing the
  backend-derived data (`node-model-local`, Model, 0 in · 1 out, `mock: true`).
- **Node labels are legible** across tiers (7/7 render visible text), and **edges
  remain visually coherent** across depth tiers (all 6 carry a tier class and fade
  consistently).
- **Reduced-motion compatibility is not obviously broken.** Under an emulated
  `prefers-reduced-motion: reduce` context the graph still renders, the depth
  tiers still resolve (near ×3 / mid ×3 / far ×1 — the depth *read* is preserved
  while animation is calmed), a node still selects and opens its inspector, and no
  console errors appear. This is a compatibility smoke test, not a full
  motion-reduction audit.
- **No console / network errors.** Across page load and every interaction the
  console showed only Vite HMR debug lines and the React DevTools info notice —
  **zero errors** — and every `/api/*` request returned `200` (zero failures).
- The QA run exercised the app **read-only** throughout — only the clicks, hovers,
  and keys the UI already offers; nothing was mutated.

## Screenshot inventory

All 5 captures are real, connected-runtime browser screenshots taken against the
local `5173` / `8787` servers described above, each visually re-verified against
its claimed state before this doc was written. Stored in
[`docs/demo/screenshots/`](screenshots/).

| File | State shown / what it proves |
| --- | --- |
| `phase-33e-spatial-hive-default.png` | Idle **Hive-State**: full-viewport 2.5D graph, `Connected` pill, `V/S/I/C/M` rail. Nodes are visibly depth-scaled across near/mid/far tiers; edges fade front-to-back. Graph is the primary surface with no overlay auto-opened. |
| `phase-33e-spatial-hive-node-selected.png` | **Focus-State**: `Local Model Registry` selected — lifted to the near tier with the strongest glow, energy-dash edge to the related `Hive\|Mind` node, all others receded/dimmed to far. Bounded INSPECTOR card (352×262) shows backend data; graph stays dominant. |
| `phase-33e-spatial-hive-inspector-overlay.png` | Overlay coherence: the **Legend & Lists** explorer (left) and the **INSPECTOR** card (right) both open while the 2.5D graph remains the dominant center surface — no sidebar/dashboard/card-grid regression. |
| `phase-33e-spatial-hive-full-view.png` | Full connected desktop view (1440×900): the 2.5D graph dominates the surface edge-to-edge, `Connected` pill, icon-only rail — the graph-primary visual contract intact. |
| `phase-33e-spatial-hive-reduced-motion.png` | `prefers-reduced-motion: reduce` context: the graph renders with depth tiers intact and a node selected/inspected, proving reduced-motion compatibility is not obviously broken. |

## Scope / guardrails preserved

- **Evidence-only:** YES. No implementation fixes were made — nothing observed
  required (or received) a source/runtime change.
- No frontend logic changes (`apps/frontend/src/**` untouched).
- No CSS changes (`styles.css` untouched).
- No React component behavior changes.
- No backend / API / schema changes (`apps/backend/**` untouched).
- No dependency / package-lock changes.
- No graph mutation; the app was exercised read-only.
- No new visualization library; **no Three.js / R3F / D3 / Cytoscape / React Flow
  / WebGL / physics / true 3D** — the 2.5D depth is the existing frontend-derived,
  display-only SVG illusion.
- No dashboard / sidebar / card-grid redesign; no "tiny polish."
- No screenshot invention or post-capture editing — all 5 images are direct
  browser output from the connected runtime.

## Webcam / live motion testing

**Not performed.** Live webcam / hand-motion control of the graph was **not**
tested this phase — there is no camera in the build environment, consistent with
the Phase 32K camera-blocked evidence policy (no fabricated or simulated
motion-control evidence). **No live hand-motion / motion-control liveness is
claimed.** The reduced-motion check above is a `prefers-reduced-motion` media
emulation, not a webcam test. The opt-in orbital motion-control remains
implemented-but-unverified-by-live-hand-motion, exactly as recorded since Phase
32I/32J/32K.

## Known limitations

- **Live motion-control evidence still deferred** (see above) — unchanged from the
  Phase 32K posture; not a regression, not a Phase 33E defect.
- The Source Registry and Vault summary remain empty versus the graph's populated
  7-node / 6-edge mock dataset — the same pre-existing, previously-documented split
  between the unpopulated registry/vault importer and the mock graph fixture noted
  since Phase 27E. Left unchanged.
- The reduced-motion check is a compatibility **smoke test** (renders + depth read
  + selection intact under emulation), not an exhaustive motion-reduction audit.

## Pass/fail summary

**PASS.** Frontend build passes; 16/16 connected-runtime QA checks verified,
including the 2.5D near/mid/far depth tiers at rest, the selected-node near-tier
lift, legible labels, coherent edges, graph-primary dominance with bounded
overlays, and reduced-motion compatibility. All 5 required screenshots captured,
visually re-verified, and inventoried. No behavior, contract, or data change of
any kind, and no live-motion evidence claimed.

## Statement of scope

This phase produced documentation, QA verification, and screenshot evidence only.
No application code, style, configuration, dependency, API, schema, or data
behavior was changed.
