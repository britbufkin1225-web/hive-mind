# Phase 27C — Graph-First App Shell QA + Screenshot Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (QA / evidence / documentation only).** Phase 27C re-runs the
local backend and frontend and captures honest screenshot/runtime evidence that the
**Phase 27B** graph-first app shell (merged in
[PR #95](https://github.com/britbufkin1225-web/hive-mind/pull/95)) renders and
functions correctly over the **real, connected** app state. It is the evidence
successor to the [Phase 26C graph visual QA evidence](phase-26c-graph-visual-qa-screenshot-evidence.md)
and verifies that promoting the Knowledge Graph to the persistent, full-viewport
primary surface — with Vault/status, Source Registry, Intelligence Report, and
Console now opening as contextual dock panes from a compact control rail — is
**present and correct** in a live, connected runtime. Phase 27C adds **no** backend,
frontend, CSS, source-code, package, config, API, schema, dependency, or runtime
asset change, and changes no application behavior. It captures and documents what
was observed; it does not fix or alter anything in the application.

> **Authenticity rule (carried from Phase 20A/20D/21C–26C).** Evidence must reflect
> real app state produced by normal run behavior — no invented, mocked, hand-edited,
> or staged-beyond-real-behavior content. Where a surface shows an empty or baseline
> state, that real observed state is recorded honestly rather than dressed up.

- **Phase name:** Phase 27C — Graph-First App Shell QA + Screenshot Evidence Refresh
- **Date:** 2026-06-30
- **Branch:** `phase-27c-graph-first-app-shell-qa-evidence`
- **Repo:** `britbufkin1225-web/hive-mind`

---

## Why this pass exists

**Phase 27A** ([planning doc](../ui/phase-27a-graph-first-app-shell-planning.md))
defined the transition from the dashboard-with-panels layout to a graph-first app
shell. **Phase 27B** ([PR #95](https://github.com/britbufkin1225-web/hive-mind/pull/95))
implemented that shell as a frontend-only pass:

- The **Knowledge Graph** is promoted to the persistent, full-viewport primary
  surface (`<main id="graph-viewport">`), replacing the prior stacked-sections
  dashboard.
- **Vault & Status, Source Registry, Intelligence Report, and Console** become
  contextual **dock panes**, opened and closed from a compact **control rail**
  (`Vault` / `Sources` / `Intelligence` / `Console` buttons) instead of scrolled
  dashboard sections.
- All four dock panes stay **mounted at all times** (toggled visible/hidden via the
  `hidden` attribute on each pane and the `inert` attribute on the closed dock), so
  switching between panes never re-triggers a data fetch — only the active pane is
  visible and focusable.
- The dock is a non-modal contextual surface: it can be closed via its `Close`
  button or the `Escape` key, and the graph underneath remains interactive while a
  dock pane is open.

No data, API, schema, backend, or package dependency changed. Phase 27C proves this
restructuring is **visible and functionally correct** against a live backend and
records a new `phase-27c-connected-*` screenshot set covering the default shell
state and every dock pane.

## Runtime commands used

Two services were started locally, each per the documented run steps:

```bash
# Backend — canonical local dev port 8787
python -m uvicorn app.main:app --app-dir apps/backend --host 0.0.0.0 --port 8787

# Frontend — Vite dev server on the canonical port 5173
npm run dev:frontend
#   → vite --host 0.0.0.0 --port 5173   (http://localhost:5173)
```

Capture session date: **2026-06-30**. The backend reported `report_version 0.1.0`
with a `generated_at` timestamp rendered live during the session
(`2026-06-30T...` / `6/30/2026, 7:31:35 PM` as shown in the Intelligence dock
capture).

> **Port note (unchanged from 21C/21F/22C–26C).** The backend CORS allowlist is
> `http://localhost:5173` / `http://127.0.0.1:5173`
> ([`apps/backend/app/main.py`](../../apps/backend/app/main.py)), and the frontend
> client defaults to `http://localhost:8787/api`
> ([`apps/frontend/src/api/client.ts`](../../apps/frontend/src/api/client.ts)). The
> connected state therefore requires the backend on `8787` and the frontend served
> from `5173`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data,
confirming **no backend / API / schema behavior changed** since Phase 26C (Phase
27B was frontend-only):

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges (same as Phase 21C/21F/22C/23B/25C/26C). |
| `GET /api/intelligence/report` | `report_version 0.1.0`; Dreaming Suggestions `0`, Temporal Decay `7`, Provenance `7`, Query Trails `7`. |

The graph data (7 nodes / 6 edges) matches every prior session exactly, confirming
the backend graph data is stable and Phase 27B did not mutate it.

## Frontend build verified

```bash
npm run check:frontend
# → npm --workspace apps/frontend run build
# → tsc -b && vite build
# ✓ 36 modules transformed
# dist/index.html                 0.41 kB │ gzip:  0.28 kB
# dist/assets/index-CD2KeHl1.css  44.04 kB │ gzip:  8.34 kB
# dist/assets/index-xhSQxgas.js  243.10 kB │ gzip: 72.66 kB
# ✓ built in 623ms
```

Frontend build passes with no TypeScript or Vite errors.

## Connected graph-first shell evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`, with the **Phase 27B** graph-first app shell active. Captures
were produced by connecting to a running Chrome headless instance via CDP
(`--headless=new`, viewport 1280 × 900, device-scale 1), navigating to
`http://localhost:5173`, then using the Chrome DevTools Protocol
(`Runtime.evaluate` to click each rail button, `Page.captureScreenshot` to record
each resulting state) — real rendered runtime pixels, not mockups. No image is
invented, mocked, or hand-edited.

| File | What it evidences |
| --- | --- |
| `phase-27c-connected-app-shell-default.png` | The **default app shell state** on load: the topbar (`DEVDEVBUILDS`, `Hive\|Mind`, `READ-ONLY DEMO BUILD` badge, green **Connected** pill), the compact control rail (`Vault` / `Sources` / `Intelligence` / `Console`, none active), and the **Knowledge Graph as the full-viewport primary surface** — summary band (7 nodes / 6 edges / 7 connected / 0 isolated), legend, and the rendered SVG graph. No dock pane is open. |
| `phase-27c-connected-graph-viewport.png` | The **graph viewport as the primary product surface** — same default state, confirming the Knowledge Graph panel occupies the main content area with no panel stacking above or below it. |
| `phase-27c-connected-rail-closed.png` | The **control rail in its closed/idle state** — all four rail buttons unpressed, no `shell-rail-button-active` class, no dock visible, confirming the rail-closed baseline described in the QA scope. |
| `phase-27c-connected-vault-dock.png` | The **Vault & Status dock pane** opened via the `Vault` rail button — `Backend connection` (green Connected pill), `API health` (`hivemind-backend` / `0.1.0` / `Yes`), and `Vault summary` (zero-state, Files/Sources/Models/Nodes all `0`), rendered in the dock over the still-visible graph canvas. |
| `phase-27c-connected-sources-dock.png` | The **Source Registry dock pane** opened via the `Sources` rail button — the `Import Obsidian vault` form (vault path + optional source name fields, `Import` button) and the honest empty-state message ("No sources registered yet."), with the graph canvas still visible to its left. |
| `phase-27c-connected-intelligence-dock.png` | The **Intelligence Report dock pane** opened via the `Intelligence` rail button — the summary band (Suggestions `0` / Decay `7` / Provenance `7` / Query Trails `7`), `Report version 0.1.0`, `Mode Read-only`, a live `Generated` timestamp, and the `Dreaming Suggestions` sub-section with its honest empty state and the `source_coverage_gap` / `unresolved_query_pattern` deferred-scope note. |
| `phase-27c-connected-console-dock.png` | The **Console dock pane** opened via the `Console` rail button — the Hive Console command input (placeholder `Try: help, status, list nodes, find note, add note "`), `Run` / `Clear` controls, and the baseline "Nothing has run yet" empty state. |
| `phase-27c-connected-ui-full.png` | A full-page capture (viewport height expanded to the page's full content height) of the default shell state — rail, topbar, and the complete Knowledge Graph surface (summary band, legend, canvas) in one frame, for an at-a-glance record of the graph-first product surface. |

The browser console reported **no runtime errors** during the connected session —
only expected dev-mode Vite HMR connection messages and the React DevTools
informational hint. No panel showed a `Failed to fetch` / disconnected state, and
the status pill remained **Connected** throughout every capture.

## QA checks performed

- [x] Frontend loads successfully at `http://localhost:5173`.
- [x] Backend is reachable at `http://localhost:8787` (`/api/health` returns `ok: true`).
- [x] No visible "Failed to fetch" state at any point in the session.
- [x] The **Knowledge Graph** renders as the persistent, full-viewport primary
      surface with no dock pane open (default state).
- [x] The **control rail** exposes all four contextual panes (`Vault`, `Sources`,
      `Intelligence`, `Console`) and each opens the correct dock content.
- [x] Existing data panels (Vault/Status, Source Registry, Intelligence Report,
      Console) load without being repositioned, rewritten, or having their content
      changed — only their container moved from a stacked section to a dock pane.
- [x] The browser console shows no runtime-breaking errors (only Vite HMR / React
      DevTools informational messages).
- [x] Screenshot evidence reflects actual, real-time rendered app state — not
      planned or mocked state.

## What Phase 27B changed (confirmed visible/functional in evidence)

- [x] Knowledge Graph promoted to the persistent full-viewport primary surface
      (`app-shell-default`, `graph-viewport`, `rail-closed`, `ui-full` screenshots)
- [x] Compact control rail (`Vault` / `Sources` / `Intelligence` / `Console`)
      replacing the prior stacked-section navigation (all screenshots)
- [x] Vault & Status opens as a contextual dock pane over the graph canvas
      (`vault-dock` screenshot)
- [x] Source Registry opens as a contextual dock pane over the graph canvas,
      including the Obsidian import form (`sources-dock` screenshot)
- [x] Intelligence Report opens as a contextual dock pane over the graph canvas,
      with the same four backend-derived sections intact (`intelligence-dock`
      screenshot)
- [x] Console opens as a contextual dock pane over the graph canvas
      (`console-dock` screenshot)
- [x] Rail button active-state styling (pressed/highlighted) reflects which pane is
      open, and only one pane is open/visible at a time
- [x] Graph canvas remains visible and rendered behind each open dock pane,
      confirming the dock is a contextual overlay and not a full-screen modal

## Confirmation: no changes made in this phase

- **No frontend source files changed.** `apps/frontend/src/**` is unmodified.
- **No CSS changes.** `apps/frontend/src/styles.css` is unmodified.
- **No backend files changed.** `apps/backend/**` is unmodified.
- **No API/schema changes.** All endpoints return identical shapes to Phase 26C.
- **No package/dependency/config changes.** `package.json`, `package-lock.json`,
  `vite.config.ts`, `tsconfig.json`, and all other config files are unmodified.
- **No runtime assets/icons/SVG/favicon files added.** The only new files in this
  commit are documentation (this evidence doc) and screenshot evidence under
  `docs/demo/screenshots/`.
- **Graph remains read-only.** No node or edge mutation was performed. All
  screenshots reflect real backend-derived graph data (7 nodes / 6 edges, the same
  deterministic seed present since Phase 21C).
- **No layout, graph, menu, dock, or intelligence-surface implementation change.**
  This phase captured and documented existing Phase 27B behavior; it did not adjust
  spacing, styling, interaction, or content in any surface.

## Scope confirmation

Changed in this phase:

- `README.md` — status/roadmap pointer update only.
- `docs/roadmap.md` — Phase 27C status entry.
- `docs/demo/phase-27c-graph-first-app-shell-qa-evidence.md` — this evidence doc (new).
- `docs/demo/screenshots/phase-27c-connected-*.png` — eight new screenshots (new).

Not touched: `apps/frontend/src/App.tsx`, `apps/frontend/src/styles.css`, any
frontend component file, any backend file, any API/schema/contract file,
`package.json`, lockfiles, build configuration, graph logic, source registry
logic, intelligence report logic, console behavior, routing/fetch/client behavior,
or any asset/icon/SVG/favicon file.

## Guardrails confirmation

- Evidence reflects real, connected runtime state captured via CDP screenshots of
  a live browser session — no fabricated or staged content.
- No AI/LLM behavior introduced or implied; the Intelligence Report remains
  deterministic and backend-derived.
- The Knowledge Graph and Intelligence Report remain read-only; no mutation was
  performed or observed.
- Human merge gate remains with devdevbuilds.

**No frontend/backend behavior was changed in this phase.** This is a QA and
evidence-capture pass only, verifying that the Phase 27B graph-first app shell
(merged into `main`) runs correctly in a connected runtime and documenting its
current visual/functional state before any further layout, graph, menu, dock, or
intelligence-surface work continues.
