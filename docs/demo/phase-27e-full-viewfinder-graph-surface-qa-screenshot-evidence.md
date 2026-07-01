# Phase 27E — Full-Viewfinder Graph Surface QA + Screenshot Evidence Refresh

**Date:** 2026-06-30

## Purpose

Phase 27D corrected the Hive|Mind app shell into the intended full-viewfinder
graph surface (the Knowledge Graph fills the primary viewport; Vault, Sources,
Intelligence, and Console are contextual dock panes opened from a compact
control rail). Phase 27E is the evidence pass immediately after that
correction: it verifies the connected runtime state, captures fresh
screenshots of the corrected shell, and refreshes demo/roadmap evidence
without changing the app. This is a documentation/QA/screenshot-only phase —
no frontend, CSS, backend, API, schema, package, or graph-logic changes.

## Runtime state verified

- Backend started via `npm run dev:backend` (`uvicorn`, port `8787`).
- Frontend started via `npm run dev:frontend` (`vite`, port `5173`).
- `GET /api/health` → `{"ok":true,"service":"hivemind-backend","version":"0.1.0"}`.
- `GET /api/graph` → 7 nodes / 6 edges (same mock dataset as prior evidence
  phases: `node-root`, `node-source-markdown`, plus the Concept/File/Model/Note
  nodes seen in the graph canvas).
- `GET /api/intelligence/report` → `report_version 0.1.0`, `read_only: true`,
  `dreaming_suggestions: 0`, `decay_statuses: 7`, `provenance_chains: 7`,
  `query_trail_entries: 7` — identical counts to the Phase 21F/22C/23B/25C/26C
  evidence trail.
- `GET /api/sources` → 3 mock sources (`Dev Markdown Notes`, `Dev Folder
  Source`, `Dev JSON Export`).
- `GET /api/vault/summary` → `totalFiles/totalSources/totalModels/totalNodes:
  0`, `graphMode: "not_initialized"` — this is the same honest empty vault
  state recorded in prior phases; the Knowledge Graph's 7/6 counts come from
  the separate mock graph dataset, not the (still-unpopulated) vault importer.
  Recorded as-is; not in scope to change.
- The connected frontend rendered the graph-first shell: header band with the
  green **Connected** status pill, the persistent full-viewport
  `Knowledge Graph` canvas, the four-item control rail (`Vault`, `Sources`,
  `Intelligence`, `Console`), and the contextual dock that opens/closes over
  the graph without unmounting its panes (per the Phase 27B
  `shell-dock`/`inert` implementation in `App.tsx`).
- No browser console errors observed during capture.

## Screenshots captured

All captures are real, connected-runtime screenshots taken against the local
`5173`/`8787` servers described above (desktop viewport, `1280x900`). Stored
in [`docs/demo/screenshots/`](screenshots/).

1. **`phase-27e-connected-graph-full-viewfinder.png`** — the default shell
   state: dock closed, rail visible, the Knowledge Graph canvas filling the
   primary viewport as the persistent primary surface. This single capture
   satisfies both "full-viewfinder graph as primary experience" and "rail/dock
   closed", since dock-closed *is* the shell's default state.
2. **`phase-27e-connected-graph-node-selected.png`** — the same graph surface
   with the `API Contracts` node selected, showing the Inspector pane
   (`ID`, `Type`, `Group`, `Connections`, `Metadata`) populate from the
   backend-derived node data. Confirms existing inspector/contextual behavior
   still works post-27D.
3. **`phase-27e-connected-dock-vault.png`** — the `Vault` rail item opened,
   showing Backend connection, API health (`hivemind-backend 0.1.0`), and the
   Vault summary metric grid as a contextual dock over the still-visible graph.
4. **`phase-27e-connected-dock-sources.png`** — the `Sources` dock pane
   (Source Registry: Obsidian import form + registered-sources list, currently
   empty per the vault state above).
5. **`phase-27e-connected-dock-intelligence.png`** — the `Intelligence` dock
   pane (Intelligence Report summary band: Suggestions 0, Decay 7, Provenance
   7, Query Trails 7, `Mode Read-only`, `BACKEND-DERIVED` badge).
6. **`phase-27e-connected-dock-console.png`** — the `Console` dock pane (Hive
   Console command input, idle/empty state).

## Validation commands run and results

| Command | Result |
| --- | --- |
| `git status` | Clean before starting; only the new evidence doc/screenshots and this README/roadmap update are staged for this phase. |
| `npm run check:frontend` | **PASS** — `tsc -b && vite build` completed with 0 errors (`✓ built in 688ms`). |
| `curl http://localhost:8787/api/health` | **PASS** — `200 OK`, `hivemind-backend 0.1.0`. |
| `curl http://localhost:8787/api/graph` | **PASS** — 7 nodes / 6 edges. |
| `curl http://localhost:8787/api/intelligence/report` | **PASS** — counts match the established evidence trail (Decay 7 / Dreaming 0 / Provenance 7 / Query Trails 7). |

## Guardrail confirmation

- No frontend code changes (`apps/frontend/src/**` untouched).
- No CSS changes (`styles.css` untouched).
- No backend changes (`apps/backend/**` untouched).
- No API/schema changes.
- No package/dependency changes (`package.json` / lockfiles untouched in this
  repo; screenshot capture used a standalone, unrelated scratch tool outside
  the repository and outside `apps/frontend`/`apps/backend`, and made no
  change to any repo manifest).
- No route/fetch/config changes.
- No layout tweaks.
- No graph logic or mutation changes.
- No runtime asset/icon/SVG/favicon additions.
- No fake screenshots — every image above is a real capture against the
  connected local runtime described in "Runtime state verified."

## Notes on what was intentionally not changed

- The Vault summary's zeroed counts (`totalFiles`/`totalSources`/
  `totalModels`/`totalNodes`, `graphMode: not_initialized`) versus the graph's
  populated 7-node/6-edge mock dataset is a pre-existing, previously-documented
  split between the (unpopulated) vault importer and the mock graph fixture.
  It is recorded honestly above and left unchanged — fixing or reconciling it
  is out of scope for an evidence-only phase.
- `docs/roadmap.md`'s "Active phase" line and phase table had not yet been
  updated for Phases 27B–27D at the time of this pass; this phase adds the
  Phase 27E row and updates the "Active phase" pointer only. Backfilling
  27B–27D rows is left for a future, separate documentation pass so this
  phase's diff stays scoped to Phase 27E evidence.
- README's "Visual evidence" section still references the Phase 25C
  pre-graph-first-shell screenshots (dashboard-with-panels layout). Swapping
  those for graph-first captures is a presentation decision better suited to
  a dedicated portfolio-lock pass (as Phase 24A/25C did) rather than folding
  it into this QA/evidence phase; left unchanged here and called out for a
  future phase.
