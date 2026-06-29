# Phase 23B — UI Surface Readability QA + Screenshot Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (QA / evidence / documentation only).** Phase 23B re-runs the
local backend and frontend and captures honest screenshot/runtime evidence that the
**Phase 23A** UI surface readability + panel-hierarchy polish renders correctly over
the **real, connected** app state. It is the evidence successor to the
[Phase 22C UI Navigation QA + Screenshot Evidence Refresh](phase-22c-ui-navigation-qa-screenshot-evidence.md)
and verifies the presentation polish merged in **Phase 23A** (PR #82) is **present
and correct** over the connected dashboard. Phase 23B adds **no** backend, frontend,
CSS, source-code, package, config, API, schema, dependency, or test change, and
changes no application behavior. It captures and documents what was observed; it
does not fix or alter anything in the application.

> **Authenticity rule (carried from Phase 20A/20D/21C–22C).** Evidence must reflect
> real app state produced by normal run behavior — no invented, mocked, hand-edited,
> or staged-beyond-real-behavior content. Where a surface shows an empty or baseline
> state, that real observed state is recorded honestly rather than dressed up. Where
> the scrollspy lands on a section other than the one targeted at a page extreme,
> that real behavior is recorded honestly too.

- **Phase name:** Phase 23B — UI Surface Readability QA + Screenshot Evidence Refresh
- **Date:** 2026-06-28
- **Branch:** `phase-23b-ui-readability-qa-screenshot-evidence`
- **Repo:** `britbufkin1225-web/hive-mind`

---

## Why this pass exists

[Phase 23A](https://github.com/britbufkin1225-web/hive-mind/pull/82) applied a
**presentation-only, CSS-only** readability and panel-hierarchy polish on top of the
Phase 21A token system (`apps/frontend/src/styles.css`, additive). It introduced:

- a shared **accent-tick identity** before every panel `<h2>` so the seven surfaces
  share one scannable start cue (`section h2::before`);
- a clearer **sub-section heading hierarchy** (`.graph-section-title` for Graph map /
  Groups / Nodes and the Intelligence Report sections);
- **unified card + container rounding** — list cards, inspectors, the graph canvas,
  the stat band, and the legend all adopt the shared small radius and the softened
  token hairline border;
- **Intelligence Report section separation** — a hairline divider plus extra air
  between the dense Dreaming / Decay / Provenance / Query Trails sub-sections;
- **lifted label/metadata contrast** onto the shared muted token; and
- **grouped Console output** — the echoed command rendered as a labeled inset chip
  with firmer result-key contrast.

This is purely color, spacing, rounding, and typography — no new data, no network /
API / contract change, and no panel behavior change. Phase 23B proves that polish is
**visible and correct** against a live backend and records a fresh
`phase-23b-connected-*` screenshot set, while preserving the earlier
`phase-22c-*` / `phase-21f-*` history.

## Runtime commands used

Two services were started locally, each per the documented run steps:

```bash
# Backend — canonical local dev port 8787
python -m uvicorn app.main:app --app-dir apps/backend --host 0.0.0.0 --port 8787
#   (the `npm run dev:backend` command, run without --reload for a stable capture)

# Frontend — Vite dev server on the canonical port 5173
npm run dev:frontend
#   → vite --host 0.0.0.0 --port 5173   (http://localhost:5173)
```

Capture session date: **2026-06-28**. The backend reported `report_version 0.1.0`
with a `generated_at` rendered in the Intelligence Report as `6/28/2026, 6:55:49 PM`
during the session.

> **Port note (the connectivity hinge, unchanged from 21C/21F/22C).** The backend
> CORS allowlist is `http://localhost:5173` / `http://127.0.0.1:5173`
> ([`apps/backend/app/main.py`](../../apps/backend/app/main.py)), and the frontend
> client defaults to `http://localhost:8787/api`
> ([`apps/frontend/src/api/client.ts`](../../apps/frontend/src/api/client.ts)). The
> connected state therefore requires the backend on `8787` and the frontend served
> from `5173` — exactly the canonical ports documented after Phase 21B. Serving the
> frontend from any other origin is rejected by CORS and reproduces the Phase 20D
> `Failed to fetch`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data. The
values match the Phase 21C/21F/22C sessions exactly, confirming **no backend / API /
schema behavior changed** between 22C and 23B (Phase 23A was frontend CSS-only):

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (a valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges. |
| `GET /api/intelligence/report` | `report_version 0.1.0`; summary counts — Dreaming `0`, Temporal Decay `7`, Provenance `7`, Query Trails `7`. |

## Connected readability evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`, with the **Phase 23A** readability/panel-hierarchy polish present.
Captures were produced by a headless system browser (Chrome, `--headless=new`,
`1280` CSS-px wide, device-scale 1) pointed at the running dev server — real rendered
runtime pixels, not mockups. The `-ui-top` and `-ui-full` images are direct headless
captures (viewport and full document); the four section images are **framed crops of
the same full-page connected capture**, scoped to each surface for readability. No
image is invented, mocked, or hand-edited.

| File | What it evidences |
| --- | --- |
| `phase-23b-connected-ui-top.png` | Page top (1280 × 900): the sticky section nav, the polished header band (`DEVDEVBUILDS`, `Hive\|Mind`, `READ-ONLY DEMO BUILD`) with its accent top border, and the first panels — **Backend connection** (accent-tick heading + green **Connected** pill), **API health** metric grid (`hivemind-backend` / `0.1.0` / `Yes`), **Vault summary** (zeros, `not_initialized`), and the start of **Sources**. Every panel heading shows the Phase 23A accent tick. |
| `phase-23b-connected-sources.png` | The **Source Registry** (`#sources`): accent-tick heading, the nested **Import Obsidian vault** form on a rounded inset surface (Vault path / Source name / Import), the rounded connected **empty state** ("No sources registered yet. Connectors will appear here once registered."), and the start of the **Knowledge Graph** panel with its rounded stat band and legend below. |
| `phase-23b-connected-knowledge-graph.png` | The **Knowledge Graph** (`#knowledge-graph`): accent-tick heading, the rounded summary band (7 nodes / 6 edges / 7 connected / 0 isolated), the rounded legend (node types, relationships, status), the `Graph map` sub-section heading, and the deterministic SVG graph map with named nodes (Hive\|Mind root, Local Model Registry, API Contracts, Dev Folder Source, …). |
| `phase-23b-connected-intelligence-report.png` | The **Intelligence Report** (`#intelligence-report`): accent-tick heading, the rounded summary band (Suggestions `0` / Decay `7` / Provenance `7` / Query Trails `7`), `Report version 0.1.0`, `Mode Read-only`, and the **hairline section dividers** separating the Dreaming Suggestions and Temporal Knowledge Decay sub-sections — with the Decay section's **BACKEND-DERIVED** badge — demonstrating the Phase 23A section separation. |
| `phase-23b-connected-console.png` | The tail of the **Query Trails** section (rounded `intel-row` cards with their Evidence-trail detail) flowing into the **Hive Console** (`#console`): accent-tick heading, the command input, Run/Clear buttons, and the connected baseline copy ("Enter a command to query the backend console. Nothing has run yet."). |
| `phase-23b-connected-ui-full.png` | Single full-page capture (1280 × 9824) of the entire connected dashboard end to end — sticky nav, header, status row, vault, sources, graph, intelligence report, and console — for an at-a-glance record of the polished panel hierarchy across every surface. |

The browser console reported **no errors** during the connected session
(`error`-level filter returned nothing), and no panel showed the `Failed to fetch` /
disconnected state recorded in Phase 20D.

> **Honest scrollspy note (recorded, not "fixed").** At the very top of the page the
> nav highlights **Status** rather than **Overview** — the same deterministic
> `IntersectionObserver` edge behavior captured in Phase 22C, unchanged here (Phase
> 23A touched only CSS). This is the real shipped behavior at the document edge,
> shown honestly.

## Phase 23A polish verified live (computed styles)

Because some of the Phase 23A polish is subtle, the rendered values were confirmed
directly in the running page (read-only inspection — no app change):

- **Panel accent tick** — `section h2` computes `display: flex`; the `::before` tick
  is `0.22rem` wide (≈ 3.5px), `border-radius: 999px`, filled with the accent token
  `rgb(107, 79, 187)`. Present on all seven panel headings.
- **Unified card rounding** — `.intel-row` computes `border-radius: 6px`
  (`var(--radius-sm)`) with `12px 13.6px` padding (`0.75rem 0.85rem`).
- **Intelligence Report section separation** — four `.intel-section` blocks, each
  with a `1px` top divider (`rgb(228, 228, 228)`, the soft border token).
- **Grouped Console output** — running a read-only `help` command produced a
  `.console-echo` chip ("Command help") with `border-radius: 6px`, a `1px` border, and
  the inset surface background (`rgb(244, 244, 244)`), inside a `.console-output`
  block, with `.result-key` lifted onto the dark text token (`rgb(31, 35, 40)`). This
  read-only console query is normal app behavior and changed no data.

## What was validated

- **Phase 23A readability polish is present and correct.** Every panel heading shows
  the accent tick; cards, inspectors, the stat band, and the legend share the small
  rounded radius and soft hairline; the Intelligence Report sub-sections are separated
  by hairline dividers; and the Console output groups the echoed command as a labeled
  chip. The connected screenshots and the computed-style checks above agree.
- **Frontend remains connected to the backend.** Every panel completed its fetch; the
  status pill read **Connected**, API health showed the real backend identity/version,
  the graph rendered 7 nodes / 6 edges, and the Intelligence Report showed
  backend-derived counts — no panel showed an error.
- **No backend / API / schema behavior changed.** The directly-exercised endpoints
  returned the same shape and values recorded in Phase 21C/21F/22C (health `0.1.0`;
  graph 7/6; report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7).
- **Screenshots reflect real app state.** All six images are honest captures of the
  live connected runtime — no invented, mocked, or hand-edited content. Empty and
  baseline surfaces (Sources empty, Vault Phase-1 zeros, Dreaming 0, Console "nothing
  has run yet") and the scrollspy edge behavior are shown as observed.

## Honest state of each surface (connected, polished)

- **Section nav:** present and sticky; seven anchor links; active item highlighted via
  `aria-current` (Status highlighted at the page top — honest edge behavior).
- **Connection (status pill):** "Connected", health `ok=true`.
- **API health:** real backend identity/version in the metric grid.
- **Vault summary:** connected **baseline** — Phase 1 zeros / `not_initialized`.
- **Source Registry:** connected **empty state** — `{"sources": []}`, "No sources
  registered yet", with the nested Obsidian import form on its rounded inset surface.
- **Knowledge Graph:** connected **data** (7 nodes / 6 edges) from `/api/graph`, with
  the rounded summary band and legend.
- **Intelligence Report:** connected **backend-derived data** (Decay 7, Provenance 7,
  Query Trails 7; Dreaming 0 with its honest empty-state copy); `Mode Read-only`; the
  hairline-separated sub-sections.
- **Console:** connected baseline — no command has run yet in the captured frame.

## Validation commands run

| Command | Result |
| --- | --- |
| `npm run dev:backend` / `npm run dev:frontend` | Backend up on `8787`, frontend on `5173`; connected runtime confirmed. |
| `curl http://localhost:8787/api/{health,registry/sources,vault/summary,graph,intelligence/report}` | Real data returned (table above). |
| `npm run check:frontend` (`tsc -b && vite build`) | **Pass** — production build succeeded. |

**Backend tests (`npm run check:backend`) were not run** in this phase, and this is
intentional. Phase 23B is QA/evidence-only and makes **zero** changes to backend code,
contracts, schema, or dependencies; backend confidence is established by the direct
live-endpoint verification above (the same data shape/values as Phase 21C/21F/22C).
The frontend build **was** run because the evidence concerns the frontend's connected,
production-buildable state after the Phase 23A CSS polish.

## Rationale for documentation placement

- The evidence document lives at
  [`docs/demo/phase-23b-ui-readability-qa-screenshot-evidence.md`](phase-23b-ui-readability-qa-screenshot-evidence.md),
  alongside the Phase 20D / 21C / 21F / 22C evidence docs, matching the established
  `docs/demo/` evidence convention.
- Screenshots use the existing `docs/demo/screenshots/` directory and the
  `phase-23b-connected-*` naming, mirroring the `phase-22c-connected-*` set so the
  refresh maps onto the prior evidence it builds on.
- The earlier `phase-22c-*`, `phase-21f-*`, `phase-21c-*`, and `phase-20d-*`
  screenshots are **preserved**, not deleted, keeping the evidence history intact.

## What is intentionally not done here

- **No code, config, dependency, or behavior change.** Phase 23B is QA/capture only.
  The Phase 22C/21F/21C/20D evidence and screenshots are preserved, not deleted.
- **No UI / CSS / frontend / fetch / API / schema work.** The readability polish landed
  in Phase 23A; this pass only photographs and documents the result. The honest
  scrollspy edge behavior is **recorded, not changed**.
- **No new surfaces, routing, mutation, AI/LLM, persistence, or production claims.**

## Honesty boundaries (unchanged)

- The Phase 23A polish is **presentation only** — color, spacing, rounding, and
  typography; it changes no data and no panel behavior, and adds no routes or pages.
- All Intelligence Report sections remain **backend-derived and read-only**; no section
  is fixture-backed and no AI/LLM runs.
- The evidence reflects a **local, single-user, demo-grade** runtime — not a production
  or hosted deployment.
- Evidence reflects the **recorded capture session**; it is not a CI guarantee.

## Confirmation

- **Screenshots are real captured runtime evidence, not mockups.** All six images are
  headless-browser captures of the live connected dev server (frontend `5173` →
  backend `8787`); the four section images are framed crops of the real full-page
  capture, scoped for readability.
- **No frontend / backend / API / package / config behavior changed.** Phase 23B's
  change set is documentation/evidence only: this evidence document, the saved
  connected screenshots, and narrow status/link updates to the README and roadmap.
  **No application behavior changed.**
