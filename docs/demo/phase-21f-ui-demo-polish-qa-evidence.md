# Phase 21F — UI Demo Polish QA + Screenshot Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (QA / evidence / documentation only).** Phase 21F re-runs the
local backend and frontend, validates that the **Phase 21E**-polished dashboard is
still **connected** to the backend, and refreshes the screenshot/evidence trail so
the captured demo proof reflects the **current polished** app state. It is the
honest successor to the
[Phase 21C connected-UI evidence pass](phase-21c-connected-ui-evidence.md), whose
screenshots were captured **before** the Phase 21E polish landed and therefore no
longer match the live UI. Phase 21F adds **no** backend, frontend, CSS,
source-code, package, config, API, schema, dependency, or test change, and changes
no application behavior. It captures and documents what was observed; it does not
fix or alter anything in the application.

> **Authenticity rule (carried from Phase 20A/20D/21C).** Evidence must reflect
> real app state produced by normal run behavior — no invented, mocked,
> hand-edited, or staged-beyond-real-behavior content. Where a surface shows an
> empty or baseline state, that real observed state is recorded honestly rather
> than dressed up.

---

## Why this pass exists

[Phase 21E](../phase-21d-ui-demo-polish-planning.md) implemented the first
presentation-only UI demo polish pass (PR #77) — a header band with the
`DEVDEVBUILDS` parent label, a `READ-ONLY DEMO BUILD` badge, a two-column
connection/health status row, card-style **metric grids** for API health and the
Vault summary, and refined connection/empty-state styling — **without** touching
backend, API, schema, data values, or dependencies. That pass changed only three
frontend files (`App.tsx`, `SourceRegistryPanel.tsx`, `styles.css`).

Because Phase 21E merged **after** the Phase 21C capture session, the existing
`phase-21c-*` screenshots show the connected UI in its **pre-polish** styling. The
demo evidence trail therefore lagged the actual app. Phase 21F closes that gap: it
proves the polished UI is **still connected** to a live backend and replaces the
stale demo proof with screenshots of the **current** polished, connected state —
while preserving the earlier Phase 21C history.

## Runtime commands used

Two services were started locally from the repository root, each per the
documented run steps:

```bash
# Backend — canonical local dev port 8787
npm run dev:backend
#   → python -m uvicorn app.main:app --app-dir apps/backend --host 0.0.0.0 --port 8787 --reload

# Frontend — Vite dev server on the canonical port 5173
npm run dev:frontend
#   → vite --host 0.0.0.0 --port 5173   (http://localhost:5173)
```

Capture session date: **2026-06-28**. The backend reported `report_version 0.1.0`
with a `generated_at` of `2026-06-28T20:33:52Z` during the session.

> **Port note (the connectivity hinge, unchanged from 21C).** The backend CORS
> allowlist is `http://localhost:5173` / `http://127.0.0.1:5173`, and the frontend
> client defaults to `http://localhost:8787/api` (confirmed in
> [`apps/frontend/src/api/client.ts`](../../apps/frontend/src/api/client.ts)). The
> connected state therefore requires the backend on `8787` and the frontend served
> from `5173` — exactly the canonical ports documented after Phase 21B. Serving the
> frontend from any other origin is rejected by CORS and reproduces the Phase 20D
> `Failed to fetch`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data. The
values match the Phase 21C session exactly, confirming **no backend/API/schema
behavior changed** between 21C and 21F:

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (a valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges. |
| `GET /api/intelligence/report` | `report_version 0.1.0`; summary counts — Dreaming `0`, Temporal Decay `7`, Provenance `7`, Query Trails `7`. |

## Connected polished UI evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`, in the **Phase 21E-polished** styling. Each is documented by
what is actually visible in the image.

| File | What it evidences |
| --- | --- |
| `phase-21f-connected-ui-top.png` | Polished header band (accent top border, `DEVDEVBUILDS` parent label, `Hive\|Mind` title, "Local-first knowledge graph over your sources" tagline, `READ-ONLY DEMO BUILD` badge), the connection/health **status row** with the green **"Connected"** pill, the API health **metric grid** (`SERVICE hivemind-backend`, `VERSION 0.1.0`, `HEALTHY Yes`), the Vault summary metric grid (Files/Sources/Models/Nodes `0`, `GRAPH MODE not_initialized`, Phase-1 message), and the Sources panel connected **empty state** ("No sources registered yet"). |
| `phase-21f-connected-knowledge-graph.png` | Knowledge Graph panel rendering **connected data**: 7 nodes / 6 edges / 7 connected / 0 isolated, the deterministic SVG graph map with named nodes (Hive\|Mind root, API Contracts, Dev Markdown Notes, Dev Folder Source, Roadmap Notes, Dashboard Placeholder, Local Model Registry), the legend (node types / relationships / status), and the groups, top-connected, nodes, and relationships lists. |
| `phase-21f-connected-intelligence-report.png` | Intelligence Report panel rendering **connected, backend-derived data**: Dreaming Suggestions (clean empty state, count 0), Temporal Knowledge Decay (7, **Backend-derived** badge), Provenance Chains (7, Backend-derived), and Query Trails (7, Backend-derived), each with evidence metadata. |
| `phase-21f-connected-ui-full.png` | Single full-page capture of the entire connected, polished dashboard end to end (header → status row → vault → sources → graph → intelligence report → console) for an at-a-glance connected-state record. |

The browser console reported **no errors** during the connected session
(`error`-level log filter returned nothing), and no panel showed the
`Failed to fetch` / disconnected state recorded in Phase 20D.

## What was validated

- **Frontend connected to backend.** Every panel completed its fetch; the status
  pill read **"Connected"**, API health showed the real backend identity/version,
  and no panel showed an error.
- **UI polish visible in the current runtime.** The Phase 21E header band, parent
  label, demo badge, status-row layout, and metric-grid cards are all present in
  the live capture (see `phase-21f-connected-ui-top.png`).
- **No backend / API / schema behavior changed.** The directly-exercised endpoints
  returned the same shape and values recorded in Phase 21C (health `0.1.0`; graph
  7/6; report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7).
- **Screenshots reflect real app state.** All four images are honest captures of
  the live connected runtime — no invented, mocked, or hand-edited content. Empty
  and baseline surfaces (Sources empty, Vault Phase-1 zeros, Dreaming 0) are shown
  as observed.

## Honest state of each surface (connected, polished)

- **Connection (status pill):** "Connected", health `ok=true`.
- **API health:** real backend identity/version in the polished metric grid.
- **Knowledge Graph:** connected **data** (7 nodes / 6 edges) from `/api/graph`.
- **Intelligence Report:** connected **backend-derived data** (Decay 7, Provenance
  7, Query Trails 7; Dreaming 0 with its honest empty-state copy).
- **Vault summary:** connected **baseline** — the Phase 1 `/api/vault/summary`
  endpoint legitimately returns zeros and a `not_initialized` graph mode.
- **Source Registry:** connected **empty state** — `/api/registry/sources` returns
  `{"sources": []}`, so the panel shows "No sources registered yet" rather than an
  error.

## Validation commands run

| Command | Result |
| --- | --- |
| `npm run dev:backend` / `npm run dev:frontend` | Backend up on `8787`, frontend on `5173`; connected runtime confirmed. |
| `curl http://localhost:8787/api/{health,registry/sources,vault/summary,graph,intelligence/report}` | Real data returned (table above). |
| `npm run check:frontend` (`tsc -b && vite build`) | **Pass** — 36 modules transformed, production build succeeded. |

**Backend tests (`npm run check:backend`) were not run** in this phase, and this is
intentional. Phase 21F is QA/evidence-only and makes **zero** changes to backend
code, contracts, schema, or dependencies; backend confidence is established by the
direct live-endpoint verification above (the same data shape/values as Phase 21C).
Re-running `pytest` would validate code this phase never touches. The frontend
build **was** run because the evidence concerns the frontend's connected,
production-buildable state.

## Rationale for documentation placement

- The evidence document lives at
  [`docs/demo/phase-21f-ui-demo-polish-qa-evidence.md`](phase-21f-ui-demo-polish-qa-evidence.md),
  alongside the Phase 20D and 21C evidence docs, matching the established
  `docs/demo/` evidence convention.
- Screenshots use the existing `docs/demo/screenshots/` directory and the
  `phase-21f-connected-*` naming, mirroring the `phase-21c-connected-*` set so the
  refresh maps one-to-one onto the prior evidence it supersedes.
- The earlier `phase-21c-*` and `phase-20d-*` screenshots are **preserved**, not
  deleted, keeping the evidence history intact.

## What is intentionally not done here

- **No code, config, dependency, or behavior change.** Phase 21F is QA/capture
  only. The Phase 21C/20D evidence and screenshots are preserved, not deleted.
- **No UI / CSS / frontend / fetch / API / schema work.** The polish landed in
  Phase 21E; this pass only photographs and documents the result.
- **No new surfaces, mutation, AI/LLM, persistence, or production claims.**

## Honesty boundaries (unchanged)

- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- The evidence reflects a **local, single-user, demo-grade** runtime — not a
  production or hosted deployment.
- Evidence reflects the **recorded capture session**; it is not a CI guarantee.

## Scope confirmation

Phase 21F did **not** change backend, frontend, CSS, source code, package files,
configs, schema, dependencies, tests, any API contract, or any runtime behavior;
did not modify, mock, hand-edit, or stage any response; and added no AI/LLM,
persistence, auth, or mutation. The change set is documentation/evidence only: this
evidence document, the saved connected polished-UI screenshots, and narrow
status/link updates to the README and roadmap. **No application behavior changed.**
