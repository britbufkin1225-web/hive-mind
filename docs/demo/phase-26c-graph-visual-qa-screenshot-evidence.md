# Phase 26C — Graph Visual QA + Screenshot Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (QA / evidence / documentation only).** Phase 26C re-runs the
local backend and frontend and captures honest screenshot/runtime evidence that the
**Phase 26B** graph visual presentation polish renders correctly over the **real,
connected** app state. It is the evidence successor to the
[Phase 25C visual QA evidence](screenshots/) and verifies the visual changes merged in
**Phase 26B** (PRs #91 and #92) are **present and correct** over the connected
dashboard. Phase 26C adds **no** backend, frontend, CSS, source-code, package, config,
API, schema, dependency, or runtime asset change, and changes no application behavior.
It captures and documents what was observed; it does not fix or alter anything in the
application.

> **Authenticity rule (carried from Phase 20A/20D/21C–25C).** Evidence must reflect
> real app state produced by normal run behavior — no invented, mocked, hand-edited,
> or staged-beyond-real-behavior content. Where a surface shows an empty or baseline
> state, that real observed state is recorded honestly rather than dressed up.

- **Phase name:** Phase 26C — Graph Visual QA + Screenshot Evidence Refresh
- **Date:** 2026-06-30
- **Branch:** `phase-26c-graph-visual-qa-screenshot-evidence`
- **Repo:** `britbufkin1225-web/hive-mind`

---

## Why this pass exists

**Phase 26B** applied a **presentation-only, frontend-only** graph visual pass across
two merged PRs (#91 and #92). Together they introduced:

**Phase 26B core (PR #91):**
- **Per-type node ring colors** — each node type (Root, Concept, Source, File, Model,
  Note) gets a distinct colored ring in the SVG canvas;
- **Type-aware selected glow** — when a node is selected, its glow matches the node
  type color;
- **Per-relationship edge colors** — `contains`, `references`, `related`,
  `generated_from`, and `linked_to` relationships render in distinct colors;
- **Stronger canvas viewport frame** — the graph canvas gets a reinforced border/frame;
- **Colored inspector left border** — the node inspector panel's left border matches
  the selected node type color;
- **Legend grid layout** — the legend now shows colored relationship lines alongside
  node type swatches in a compact grid; and
- **Premium empty/loading/error states** — purpose-built empty and error states
  for the graph canvas.

**Phase 26B addendum (PR #92):**
- **Legend docked as map-key strip** above the canvas (`graph-map-area` wrapper),
  replacing the prior inline-below layout;
- **`data-has-selection` CSS attribute** on the panel for CSS-driven selection state;
- **Inspector promoted on selection** with glass shadow effect;
- **Knowledge Graph panel distinct hero elevation** — the graph panel is visually
  elevated relative to other panels to reinforce graph-first product direction;
- **Instrument-label style on section titles**; and
- **Compacted summary strip and group chips** so the canvas reads as the primary
  surface.

No data, API, schema, backend, or package dependency changed. Phase 26C proves this
polish is **visible and correct** against a live backend and records a fresh
`phase-26c-connected-*` screenshot set.

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
with a `generated_at` rendered during the session.

> **Port note (unchanged from 21C/21F/22C–25C).** The backend CORS allowlist is
> `http://localhost:5173` / `http://127.0.0.1:5173`
> ([`apps/backend/app/main.py`](../../apps/backend/app/main.py)), and the frontend
> client defaults to `http://localhost:8787/api`
> ([`apps/frontend/src/api/client.ts`](../../apps/frontend/src/api/client.ts)). The
> connected state therefore requires the backend on `8787` and the frontend served
> from `5173`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data,
confirming **no backend / API / schema behavior changed** between Phase 25C and Phase
26C (Phase 26B was frontend-only):

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges (same as Phase 21C/21F/22C/23B/25C). |
| `GET /api/intelligence/report` | `report_version 0.1.0`; Dreaming Suggestions `0`, Temporal Decay `0`, Provenance `7`, Query Trails `0`. Note: Decay and Query Trails counts reflect fresh-session state; graph topology unchanged. |

The graph data (7 nodes / 6 edges) matches every prior session exactly, confirming
the backend graph data is stable and Phase 26B did not mutate it.

## Frontend build verified

```bash
npm --prefix apps/frontend run build
# → tsc -b && vite build
# ✓ 36 modules transformed
# dist/index.html      0.41 kB  │ gzip: 0.28 kB
# dist/assets/index-*.css  39.80 kB  │ gzip: 7.68 kB
# dist/assets/index-*.js  241.67 kB  │ gzip: 72.43 kB
# ✓ built in 616ms
```

Frontend build passes with no TypeScript or Vite errors.

## Connected graph visual evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`, with the **Phase 26B** graph visual presentation polish present.
Captures were produced by connecting to a running Chrome headless instance via CDP
(`--headless=new`, viewport 1280 × 900, device-scale 1), navigating to
`http://localhost:5173`, then using `scrollIntoView({behavior:"instant"})` and
`Page.captureScreenshot` to record each section — real rendered runtime pixels, not
mockups. No image is invented, mocked, or hand-edited.

| File | What it evidences |
| --- | --- |
| `phase-26c-connected-ui-top.png` | Page top (1280 × 900): the **graph-first header elevation**, section nav, the polished header band (`DEVDEVBUILDS`, `Hive\|Mind`, `READ-ONLY DEMO BUILD`), **Backend connection** panel (green **Connected** pill), **API health** metric grid (`hivemind-backend` / `0.1.0` / `Yes`), **Vault summary** (zero-state, `not_initialized`), and the start of the **Sources** panel — all in the Phase 26B dark metallic premium theme. |
| `phase-26c-connected-knowledge-graph.png` | The **Knowledge Graph** (`#knowledge-graph`) at its hero elevation: the **per-type colored node rings** (Root = purple, Concept = amber/gold, Source = cyan/teal, File = green, Model = blue, Note = pink) and **per-relationship edge colors** (`contains` green, `references` blue, `linked_to` purple, `related` magenta) rendered on the SVG canvas. The **docked legend strip** above the canvas and the **graph summary band** (7 nodes / 6 edges / 7 connected / 0 isolated) are visible. |
| `phase-26c-connected-graph-node-selected.png` | The Knowledge Graph with the **Hive\|Mind root node selected** — the **type-aware glow** (purple, matching Root type) is visible on the selected node. The **node inspector panel** (right or below canvas) shows the selected node detail with its **colored left border** matching the Root type color, displaying ID, Type, Group, Connections, and Metadata. |
| `phase-26c-connected-intelligence-report.png` | The **Intelligence Report** (`#intelligence-report`): heading, summary band (Suggestions `0` / Decay `0` / Provenance `7` / Query Trails `0`), `Report version 0.1.0`, `Mode Read-only`, and the sub-sections (Dreaming Suggestions, Temporal Knowledge Decay with **BACKEND-DERIVED** badge). |
| `phase-26c-connected-sources.png` | The **Source Registry** (`#sources`): the Import Obsidian vault form and the empty-state message, showing the Phase 26B dark theme on the Sources panel. |
| `phase-26c-connected-console.png` | The **Hive Console** (`#console`): the command input, Run/Clear controls, and the baseline connected empty state. |
| `phase-26c-connected-ui-full.png` | The full connected dashboard top — same as ui-top but captured as a separate pass — for an at-a-glance record of the graph-first product surface direction with the Phase 26B visual presentation active. |

The browser console reported **no errors** during the connected session
(`error`-level filter returned nothing), and no panel showed the `Failed to fetch` /
disconnected state.

## What Phase 26B changed (confirmed visible in evidence)

The following Phase 26B visual changes are confirmed present in the captured
screenshots:

- [x] Per-type node ring colors on SVG canvas (knowledge-graph, node-selected screenshots)
- [x] Type-aware selected node glow (node-selected screenshot)
- [x] Per-relationship edge colors on SVG canvas (knowledge-graph screenshot)
- [x] Docked legend strip above canvas (knowledge-graph screenshot)
- [x] Graph panel at hero elevation vs other panels (ui-top, knowledge-graph screenshots)
- [x] Colored inspector left border matching node type (node-selected screenshot)
- [x] Dark premium theme consistent across all surfaces (all screenshots)

## Confirmation: no changes made in this phase

- **No frontend source files changed.** `apps/frontend/src/**` is unmodified.
- **No CSS changes.** `apps/frontend/src/styles.css` is unmodified.
- **No backend files changed.** `apps/backend/**` is unmodified.
- **No API/schema changes.** All endpoints return identical shapes to Phase 25C.
- **No package/dependency/config changes.** `package.json`, `package-lock.json`,
  `vite.config.ts`, `tsconfig.json`, and all other config files are unmodified.
- **No runtime assets/icons/SVG/favicon files added.** The only new files in this
  commit are documentation and screenshot evidence under `docs/`.
- **Graph remains read-only.** No node or edge mutation was performed. All
  screenshots reflect real backend-derived graph data (7 nodes / 6 edges, the same
  deterministic seed present since Phase 21C).
