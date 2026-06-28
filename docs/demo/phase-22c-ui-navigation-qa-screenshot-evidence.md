# Phase 22C — UI Navigation QA + Screenshot Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (QA / evidence / documentation only).** Phase 22C re-runs the
local backend and frontend and captures honest screenshot/runtime evidence that
the **Phase 22B** single-page section navigation + demo flow works in the **real,
connected** app state. It is the evidence successor to the
[Phase 21F UI Demo Polish QA + Screenshot Evidence Refresh](phase-21f-ui-demo-polish-qa-evidence.md)
and proves the navigation model locked in the
[Phase 22A UI Navigation + Demo Flow Planning](../planning/phase-22a-ui-navigation-demo-flow-planning.md)
and implemented in **Phase 22B** (PR #80) is **present and usable** over the
connected dashboard. Phase 22C adds **no** backend, frontend, CSS, source-code,
package, config, API, schema, dependency, or test change, and changes no
application behavior. It captures and documents what was observed; it does not
fix or alter anything in the application.

> **Authenticity rule (carried from Phase 20A/20D/21C–21F).** Evidence must
> reflect real app state produced by normal run behavior — no invented, mocked,
> hand-edited, or staged-beyond-real-behavior content. Where a surface shows an
> empty or baseline state, that real observed state is recorded honestly rather
> than dressed up. Where scrollspy lands on a section other than the one targeted
> at a page extreme, that real behavior is recorded honestly too.

---

## Why this pass exists

[Phase 22B](https://github.com/britbufkin1225-web/hive-mind/pull/80) implemented
the Phase 22A navigation model as a **frontend-only** pass: a sticky in-page
**section nav** (table of contents) over the existing connected dashboard, stable
`id` anchors on every top-level surface, an `IntersectionObserver` scrollspy "you
are here" cue, smooth anchor scrolling that respects `prefers-reduced-motion`, and
a keyboard **skip link**. It added no router, no new dependency, no new pages, and
no backend/API/schema/contract changes.

The existing connected-UI evidence (`phase-21f-connected-*`) was captured **before**
the navigation landed and therefore shows the dashboard with **no nav**. Phase 22C
closes that gap: it proves the navigation is **visible and usable** against a live
backend and records a fresh `phase-22c-connected-*` screenshot set that shows the
sticky nav and its active-section highlight on every major surface — while
preserving the earlier Phase 21F/21C history.

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
with a `generated_at` rendered in the Intelligence Report as `6/28/2026, 4:50:52 PM`
during the session.

> **Port note (the connectivity hinge, unchanged from 21C/21F).** The backend CORS
> allowlist is `http://localhost:5173` / `http://127.0.0.1:5173`
> ([`apps/backend/app/main.py`](../../apps/backend/app/main.py)), and the frontend
> client defaults to `http://localhost:8787/api`
> ([`apps/frontend/src/api/client.ts`](../../apps/frontend/src/api/client.ts)). The
> connected state therefore requires the backend on `8787` and the frontend served
> from `5173` — exactly the canonical ports documented after Phase 21B. Serving the
> frontend from any other origin is rejected by CORS and reproduces the Phase 20D
> `Failed to fetch`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data. The
values match the Phase 21C/21F sessions exactly, confirming **no backend/API/schema
behavior changed** between 21F and 22C (Phase 22B was frontend-only):

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (a valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges. |
| `GET /api/intelligence/report` | `report_version 0.1.0`; summary counts — Dreaming `0`, Temporal Decay `7`, Provenance `7`, Query Trails `7`. |

## Connected navigation evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`, with the **Phase 22B** navigation present. Each is documented by
what is actually visible in the image, including which nav item the scrollspy marks
active.

| File | What it evidences | Active nav item |
| --- | --- | --- |
| `phase-22c-connected-ui-top.png` | Page top: the **sticky section nav** (Overview · Status · Vault · Sources · Graph · Intelligence · Console), the polished header band (`DEVDEVBUILDS`, `Hive\|Mind`, `READ-ONLY DEMO BUILD`), the **Connected** pill, the API health metric grid (`hivemind-backend` / `0.1.0` / `Yes`), the Vault summary baseline (zeros, `not_initialized`), and the start of the Sources panel. | **Status** (honest scrollspy result — see note below) |
| `phase-22c-connected-sources.png` | The **Source Registry** anchored at `#sources`: the nested **Import Obsidian vault** form (Vault path / Source name / Import) and the connected **empty state** ("No sources registered yet"), with the Knowledge Graph header beginning below. Sticky nav shows **Sources** highlighted. | **Sources** |
| `phase-22c-connected-knowledge-graph.png` | The **Knowledge Graph** anchored at `#knowledge-graph`: summary 7 nodes / 6 edges / 7 connected / 0 isolated, the legend (node types, relationships, status), and the deterministic SVG graph map with named nodes (Hive\|Mind root, Local Model Registry, API Contracts, Dev Folder Source, …). Sticky nav shows **Graph** highlighted. | **Graph** |
| `phase-22c-connected-intelligence-report.png` | The **Intelligence Report** anchored at `#intelligence-report`: summary Dreaming `0` / Decay `7` / Provenance `7` / Query Trails `7`, `Report version 0.1.0`, `Mode Read-only`, the Dreaming Suggestions empty state, and the Temporal Knowledge Decay section with its **BACKEND-DERIVED** badge. Sticky nav shows **Intelligence** highlighted. | **Intelligence** |
| `phase-22c-connected-console.png` | The **Console** (`#console`) — the **Hive Console** panel with its command input and "Enter a command to query the backend console. Nothing has run yet." baseline — beneath the tail of the Query Trails section. Sticky nav remains present. | **Intelligence** (honest scrollspy result — see note below) |
| `phase-22c-connected-ui-full.png` | Single full-page capture (1280 × 9576) of the entire connected dashboard end to end with the sticky nav, header, status row, vault, sources, graph, intelligence report, and console, for an at-a-glance connected-state record. | — |

The browser console reported **no errors** during the connected session
(`error`-level filter returned nothing), and no panel showed the `Failed to fetch` /
disconnected state recorded in Phase 20D.

> **Honest scrollspy note (recorded, not "fixed").** The scrollspy uses a single
> `IntersectionObserver` with `rootMargin: "-40% 0px -55% 0px"` — it marks the
> section whose top crosses a band roughly in the upper-middle of the viewport.
> At the two **page extremes** this is visible: at the very top (`#overview`) the
> first section already inside the band is **Status**, so the nav highlights
> *Status* rather than *Overview*; at the very bottom the short **Console**
> section cannot scroll up into the band, so the nav still highlights
> **Intelligence**. This is the **real, deterministic** behavior of the shipped
> Phase 22B scrollspy at the document edges — captured honestly rather than staged.
> For the four interior sections (Status, Sources, Graph, Intelligence) the active
> highlight matches the targeted anchor exactly, as the screenshots show.

## What was validated

- **Phase 22B navigation is visible and usable.** The sticky section nav renders
  on the connected page in every capture; clicking/anchoring to a section scrolls
  to it and the scrollspy highlights the corresponding nav item (Sources, Graph,
  Intelligence each match their target anchor). The accessibility snapshot confirms
  the `nav[aria-label="Dashboard sections"]`, the seven anchor links, the
  `aria-current` active link, and the "Skip to main content" skip link.
- **Sticky navigation + anchor behavior are present.** The nav stays fixed at the
  top of every section screenshot, and each top-level surface is reachable by its
  stable `id` anchor (`#overview`, `#status`, `#vault`, `#sources`,
  `#knowledge-graph`, `#intelligence-report`, `#console`).
- **Frontend remains connected to the backend.** Every panel completed its fetch;
  the status pill read **Connected**, API health showed the real backend
  identity/version, the graph rendered 7 nodes / 6 edges, and the Intelligence
  Report showed backend-derived counts — no panel showed an error.
- **No backend / API / schema behavior changed.** The directly-exercised endpoints
  returned the same shape and values recorded in Phase 21C/21F (health `0.1.0`;
  graph 7/6; report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7).
- **Screenshots reflect real app state.** All six images are honest captures of the
  live connected runtime — no invented, mocked, or hand-edited content. Empty and
  baseline surfaces (Sources empty, Vault Phase-1 zeros, Dreaming 0, Console "nothing
  has run yet") and the scrollspy edge behavior are shown as observed.

## Honest state of each surface (connected, with navigation)

- **Section nav:** present and sticky; seven anchor links; active item highlighted
  via `aria-current`; "Skip to main content" skip link present.
- **Connection (status pill):** "Connected", health `ok=true`.
- **API health:** real backend identity/version in the metric grid.
- **Vault summary:** connected **baseline** — Phase 1 zeros / `not_initialized`.
- **Source Registry:** connected **empty state** — `{"sources": []}`, "No sources
  registered yet", with the nested Obsidian import form present.
- **Knowledge Graph:** connected **data** (7 nodes / 6 edges) from `/api/graph`.
- **Intelligence Report:** connected **backend-derived data** (Decay 7, Provenance
  7, Query Trails 7; Dreaming 0 with its honest empty-state copy); `Mode Read-only`.
- **Console:** connected baseline — no command has run yet.

## Validation commands run

| Command | Result |
| --- | --- |
| `npm run dev:backend` / `npm run dev:frontend` | Backend up on `8787`, frontend on `5173`; connected runtime confirmed. |
| `curl http://localhost:8787/api/{health,registry/sources,vault/summary,graph,intelligence/report}` | Real data returned (table above). |
| `npm run check:frontend` (`tsc -b && vite build`) | **Pass** — 36 modules transformed, production build succeeded. |

**Backend tests (`npm run check:backend`) were not run** in this phase, and this is
intentional. Phase 22C is QA/evidence-only and makes **zero** changes to backend
code, contracts, schema, or dependencies; backend confidence is established by the
direct live-endpoint verification above (the same data shape/values as Phase
21C/21F). The frontend build **was** run because the evidence concerns the
frontend's connected, production-buildable state.

## Rationale for documentation placement

- The evidence document lives at
  [`docs/demo/phase-22c-ui-navigation-qa-screenshot-evidence.md`](phase-22c-ui-navigation-qa-screenshot-evidence.md),
  alongside the Phase 20D / 21C / 21F evidence docs, matching the established
  `docs/demo/` evidence convention.
- Screenshots use the existing `docs/demo/screenshots/` directory and the
  `phase-22c-connected-*` naming, mirroring the `phase-21f-connected-*` set so the
  refresh maps onto the prior evidence it builds on.
- The earlier `phase-21f-*`, `phase-21c-*`, and `phase-20d-*` screenshots are
  **preserved**, not deleted, keeping the evidence history intact.

## What is intentionally not done here

- **No code, config, dependency, or behavior change.** Phase 22C is QA/capture
  only. The Phase 21F/21C/20D evidence and screenshots are preserved, not deleted.
- **No UI / CSS / frontend / fetch / API / schema work.** The navigation landed in
  Phase 22B; this pass only photographs and documents the result. The honest
  scrollspy edge behavior is **recorded, not changed**.
- **No new surfaces, routing, mutation, AI/LLM, persistence, or production claims.**

## Honesty boundaries (unchanged)

- The navigation is **presentation only** — it scrolls to and highlights existing
  surfaces; it changes no data and no panel behavior, and adds no routes or pages.
- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- The evidence reflects a **local, single-user, demo-grade** runtime — not a
  production or hosted deployment.
- Evidence reflects the **recorded capture session**; it is not a CI guarantee.

## Scope confirmation

Phase 22C did **not** change backend, frontend, CSS, source code, package files,
configs, schema, dependencies, tests, any API contract, routing, or any runtime
behavior; did not modify, mock, hand-edit, or stage any response; and added no
AI/LLM, persistence, auth, or mutation. The change set is documentation/evidence
only: this evidence document, the saved connected-navigation screenshots, and
narrow status/link updates to the README and roadmap. **No application behavior
changed.**
