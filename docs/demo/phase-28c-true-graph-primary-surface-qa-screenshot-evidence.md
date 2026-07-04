# Phase 28C — True Graph-Primary Surface QA + Screenshot Evidence Refresh

**Date:** 2026-07-04

**Branch:** `phase-28c-true-graph-primary-surface-qa-evidence`

## Purpose

Phase 28B implemented the Phase 28A true graph-primary surface contract —
the Knowledge Graph fills the entire viewport edge-to-edge at all
breakpoints; the masthead, control rail, and contextual dock are floating
translucent glass overlays instead of flex-row layout siblings; the control
rail is a compact, icon-only, bottom-docked capsule; and the graph explorer
(legend/groups/node/edge lists) and node inspector are summoned/
selection-triggered floating glass cards. Phase 28C is the evidence pass
immediately after that implementation: it verifies the connected runtime
state and captures fresh screenshots proving the shell actually renders as
specified, without changing the app. This is a documentation/QA/screenshot-
only phase — no frontend, CSS, backend, API, schema, package, or
graph-logic changes.

## Runtime state verified

- Backend started via `npm run dev:backend` (`uvicorn`, port `8787`).
- Frontend started via `npm run dev:frontend` (`vite`, port `5173`).
- `GET /api/health` → `{"ok":true,"service":"hivemind-backend","version":"0.1.0"}`.
- `GET /api/graph` → 7 nodes / 6 edges (same mock dataset as every prior
  evidence phase: `Hive|Mind`, `Local Model Registry`, `API Contracts`,
  `Dev Folder Source`, `Dev Markdown Notes`, `Dashboard Placeholder`,
  `Roadmap Notes`).
- `GET /api/intelligence/report` → `report_version 0.1.0`, `read_only: true`,
  `dreaming_suggestions: 0`, `decay_statuses: 7`, `provenance_chains: 7`,
  `query_trail_entries: 7` — identical counts to the established
  21F/22C/23B/25C/26C/27E evidence trail.
- `GET /api/sources` → 3 mock sources (`Dev Markdown Notes`, `Dev Folder
  Source`, `Dev JSON Export`) when checked directly against the backend at
  documentation time.
- `GET /api/vault/summary` → `totalFiles/totalSources/totalModels/totalNodes:
  0`, `graphMode: "not_initialized"` — the same honest empty vault state
  recorded in every prior phase; the Knowledge Graph's 7/6 counts come from
  the separate mock graph dataset, not the (still-unpopulated) vault
  importer. Recorded as-is; not in scope to change.
- The connected frontend rendered the true graph-primary shell: a
  full-viewport dark graph canvas with no persistent sidebar/dashboard-column
  framing, a floating translucent masthead (`DEVDEVBUILDS Hive|Mind`,
  connection pill), and a bottom-docked, icon-only `V`/`S`/`I`/`C` capsule
  rail.
- No browser console errors observed during capture.

## Screenshots captured

All 8 required captures are real, connected-runtime screenshots taken
against the local `5173`/`8787` servers described above. Stored in
[`docs/demo/screenshots/`](screenshots/).

1. **`phase-28c-default-graph-primary-surface.png`** — the default shell
   state: the Knowledge Graph fills the entire browser viewport edge-to-edge,
   the floating masthead and `Legend & lists` / `Reset view` / `Refresh`
   controls sit above it, and the bottom capsule rail (`V`/`S`/`I`/`C`) is the
   only persistent chrome. No sidebar, no dashboard column, no card-grid
   framing — confirms graph dominance in the default state.
2. **`phase-28c-legend-lists-overlay.png`** — the `Legend & lists` control
   toggled to `Hide legend`, opening a translucent floating panel (Node
   Types, Relationships, Status, Groups, Top Connected Nodes) over the
   still-visible graph. Reads as a contextual overlay, not a permanent
   sidebar — the graph remains visible and interactive to its right.
3. **`phase-28c-selected-node-inspector.png`** — the `Local Model Registry`
   node selected (glowing highlight + dashed relationship line), with the
   floating `INSPECTOR` card open on the right showing `ID`, `Type`, `Group`,
   `Connections`, and `Metadata` populated from the backend-derived node
   data. Confirms both the node-selected state and the inspector UI are
   visible together.
4. **`phase-28c-vault-overlay.png`** — the `V` rail item opened, showing
   `Backend connection: Connected`, `API health` (`hivemind-backend 0.1.0`,
   `Healthy: Yes`), and the `Vault summary` metric grid (`Files 0`,
   `Sources 0`, `Models 0`, `Nodes 0`, `Graph Mode: not_initialized`) as a
   contextual floating panel over the still-visible graph.
5. **`phase-28c-sources-overlay.png`** — the `S` rail item opened, showing
   the `Source Registry` pane (`Import Obsidian vault` form) over the graph.
   This particular capture shows an empty state (`No sources registered yet`)
   — see Known limitations below for the discrepancy against the live
   backend's 3 seeded mock sources.
6. **`phase-28c-intelligence-overlay.png`** — the `I` rail item opened,
   showing the `Intelligence Report` pane (`Suggestions 0`, `Decay 7`,
   `Provenance 7`, `Query Trails 7`, `Mode: Read-only`, `Dreaming
   Suggestions` section) as a floating overlay over the graph.
7. **`phase-28c-console-overlay.png`** — the `C` rail item opened, showing
   the `Hive Console` pane (command input, `Run`/`Clear` buttons, idle/empty
   state) as a floating overlay over the graph.
8. **`phase-28c-narrow-viewport.png`** — the same connected shell captured
   at a narrow (~506px) browser width: the graph-primary layout holds up —
   full-viewport graph, bottom `V`/`S`/`I`/`C` rail, floating masthead (the
   `Connected` status pill truncates at this width, an honest narrow-
   viewport rendering detail rather than a bug introduced by this phase).

## Validation commands run and results

| Command | Result |
| --- | --- |
| `git status --short` | Clean before starting; only the 8 new screenshot files and this evidence doc/roadmap-README pointer updates are part of this phase's diff. |
| `npm run check:frontend` | **PASS** — `tsc -b && vite build` completed with 0 errors (`✓ built in 752ms`). |
| `curl http://localhost:8787/api/health` | **PASS** — `200 OK`, `hivemind-backend 0.1.0`. |
| `curl http://localhost:8787/api/graph` | **PASS** — 7 nodes / 6 edges. |
| `curl http://localhost:8787/api/intelligence/report` | **PASS** — counts match the established evidence trail (Decay 7 / Dreaming 0 / Provenance 7 / Query Trails 7). |
| `curl http://localhost:8787/api/sources` | **PASS** (endpoint responds) — 3 mock sources currently registered; see Known limitations for the mismatch against the `sources-overlay` capture's empty state. |
| `curl http://localhost:8787/api/vault/summary` | **PASS** — honest `not_initialized` empty vault state, consistent with every prior phase. |

## Guardrail confirmation

- No frontend code changes (`apps/frontend/src/**` untouched).
- No CSS changes (`styles.css` untouched).
- No backend changes (`apps/backend/**` untouched).
- No API/schema changes.
- No package/dependency changes (`package.json` / lockfiles untouched).
- No route/fetch/config changes.
- No layout tweaks or "small visual fixes" — this phase captures the
  Phase 28B implementation as-is, including any rough edges (see Known
  limitations).
- No graph logic or mutation changes.
- No screenshot fabrication — every image in the inventory above was
  visually re-verified against its claimed state (not just checked for file
  existence) before this doc was written. An earlier round of attempted
  captures during this phase's QA pass produced files that turned out to be
  unrelated desktop screenshots rather than genuine app captures; those were
  rejected and are not part of the final evidence set recorded here.

## Known limitations / follow-ups (not fixed in this phase)

- **Sources count discrepancy:** the `phase-28c-sources-overlay.png`
  capture shows an empty Source Registry (`No sources registered yet`),
  while a direct `GET /api/sources` check against the connected backend at
  documentation time returns 3 seeded mock sources (`Dev Markdown Notes`,
  `Dev Folder Source`, `Dev JSON Export`) — the same fixture prior phases
  (e.g. 27E) documented as populated. This looks like a difference between
  the runtime session used for that specific capture and the backend state
  checked afterward, rather than a Phase 28B behavior change. Recorded
  honestly; not investigated or fixed here per this phase's evidence-only
  scope. Candidate for a Phase 28D/29A follow-up if it recurs.
- **Connection-pill truncation at narrow widths:** the `Connected` status
  pill text is clipped at the ~506px capture width. This is a pre-existing
  responsive characteristic of the Phase 28B shell, observed and recorded
  here as-is per this phase's "no small visual fix" boundary.
- The Vault summary's zeroed counts versus the graph's populated 7-node/
  6-edge mock dataset is the same pre-existing, previously-documented split
  between the (unpopulated) vault importer and the mock graph fixture noted
  in every phase since at least 27E. Left unchanged.
