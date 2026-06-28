# Phase 21C — Connected UI Screenshot + Runtime Evidence Refresh

Parent label: **devdevbuilds**

**Status: complete (capture / documentation only).** Phase 21C refreshes the
runtime evidence trail by capturing the **connected** frontend/backend state after
the Phase 21A/21B runtime-config fixes. It is the honest successor to the
[Phase 20D evidence pass](phase-20d-demo-evidence.md), which truthfully recorded a
**disconnected / `Failed to fetch`** frontend during its capture session. Phase 21C
adds **no** backend, frontend, CSS, source-code, package, config, API, schema,
dependency, or test change, and changes no application behavior. It captures and
documents what was observed; it does not fix anything in the application.

> **Authenticity rule (carried from Phase 20A/20D).** Evidence must reflect real
> app state produced by normal run behavior — no invented, mocked, hand-edited, or
> staged-beyond-real-behavior content. Where a surface shows an empty or baseline
> state, that real observed state is recorded honestly rather than dressed up.

---

## Why this pass exists

Phase 20D documented the backend serving real data **and** an honestly-recorded
frontend fetch failure. That failure was a **run-configuration mismatch**, not an
application bug: the canonical local backend port is `8787` (started via
`npm run dev:backend`), while an off-script `uvicorn` launch binds `8000`, so the
frontend's `http://localhost:8787/api` requests reached nothing and surfaced as
`Failed to fetch`. Phase 21A (dashboard shell) and Phase 21B (`fix: align frontend
API base URL runtime config`, root `envDir`, documented canonical `8787`) closed
that gap. Phase 21C replaces the stale "known disconnected" demo evidence with
connected-app proof while preserving the earlier Phase 20D evidence history.

## Runtime commands used

Two services were started locally from the repository root, each per the
documented run steps:

```bash
# Backend — canonical local dev port 8787
npm run dev:backend
#   → python -m uvicorn app.main:app --app-dir apps/backend --host 0.0.0.0 --port 8787 --reload

# Frontend — Vite dev server on the canonical port 5173
npm run dev:frontend            # equivalent vite dev server on http://localhost:5173
```

Capture session date: **2026-06-28**. The backend reported `report_version 0.1.0`
with a `generated_at` of `2026-06-28T...` during the session.

> **Port note (the connectivity hinge).** The backend CORS allowlist is
> `http://localhost:5173` / `http://127.0.0.1:5173`, and the frontend client
> defaults to `http://localhost:8787/api`. The connected state therefore requires
> the backend on `8787` and the frontend served from `5173` — exactly the
> canonical ports documented after Phase 21B. Serving the frontend from any other
> origin is rejected by CORS and reproduces the Phase 20D `Failed to fetch`.

## Backend runtime verified directly

The live API was exercised on `http://localhost:8787` and returned real data:

| Endpoint | Observed result |
| --- | --- |
| `GET /api/health` | `ok=true`, `service=hivemind-backend`, `version=0.1.0`. |
| `GET /api/registry/sources` | `{"sources": []}` — empty registry (a valid connected empty state). |
| `GET /api/vault/summary` | `totalFiles/Sources/Models/Nodes = 0`, `graphMode=not_initialized`, Phase 1 foundation message. |
| `GET /api/graph` | 7 nodes, 6 edges (`node-root` "Hive\|Mind" plus source/concept/file/model/note nodes). |
| `GET /api/intelligence/report` | `report_version 0.1.0`; summary counts — Dreaming `0`, Temporal Decay `7`, Provenance `7`, Query Trails `7`. |

## Connected UI evidence captured

Screenshots are saved under [`docs/demo/screenshots/`](screenshots/). They were
captured from the live frontend served on `http://localhost:5173`, talking to the
backend on `8787`. Each is documented by what is actually visible in the image.

| File | What it evidences |
| --- | --- |
| `phase-21c-connected-ui-top.png` | Header band through the graph header: **Backend connection → "Connected"** (green pill, no error), API health (`Service hivemind-backend`, `Version 0.1.0`, `Healthy Yes`), the Vault summary Phase-1 baseline, and the Sources panel **connected empty state** ("No sources registered yet"). |
| `phase-21c-connected-knowledge-graph.png` | Knowledge Graph panel rendering **connected data**: 7 nodes / 6 edges / 7 connected / 0 isolated, the deterministic SVG graph map with named nodes (Hive\|Mind root, API Contracts, Dev Markdown Notes, Dev Folder Source, Roadmap Notes, Dashboard Placeholder, Local Model Registry), the legend, and the groups/top-connected lists. |
| `phase-21c-connected-intelligence-report.png` | Intelligence Report panel rendering **connected, backend-derived data**: Dreaming Suggestions (clean empty state), Temporal Knowledge Decay (7 rows, **BACKEND-DERIVED** badge, per-row reason/age), and Provenance Chains (7, BACKEND-DERIVED) with evidence metadata. |
| `phase-21c-connected-ui-full.png` | Single full-page capture of the entire connected dashboard end to end (header → connection → health → vault → sources → graph → intelligence report → console) for an at-a-glance connected-state record. |

The browser console reported **no errors** during the connected session, and no
panel showed the `Failed to fetch` / disconnected state recorded in Phase 20D.

## Honest state of each surface (connected)

The frontend was unambiguously **connected** — every panel completed its fetch and
none showed an error. Within that connected state, the surfaces show a mix of
seeded data and valid baseline/empty states, recorded here without dressing up:

- **Connected (status pill):** "Connected", health `ok=true`.
- **API health:** real backend identity/version.
- **Knowledge Graph:** connected **data** (7 nodes / 6 edges) from `/api/graph`.
- **Intelligence Report:** connected **backend-derived data** (Decay 7, Provenance
  7, Query Trails 7; Dreaming 0 with its honest empty-state copy).
- **Vault summary:** connected **baseline** — the Phase 1 `/api/vault/summary`
  foundation endpoint legitimately returns zeros and a `not_initialized` graph mode.
- **Source Registry:** connected **empty state** — `/api/registry/sources` returns
  `{"sources": []}`, so the panel shows "No sources registered yet" rather than an
  error. (The separate `/api/sources` mock-catalog endpoint and the seeded graph
  are distinct surfaces; this is existing app behavior, not a regression.)

## What is intentionally not done here

- **No code, config, dependency, or behavior change.** Phase 21C is capture-only.
  The earlier disconnected-state evidence and the Phase 20D document are preserved,
  not deleted.
- **No UI/CSS/fetch/API/schema work.** The runtime-config fix already landed in
  Phase 21A/21B; this pass only photographs the result.
- **No new surfaces, mutation, AI/LLM, persistence, or production claims.**

## Honesty boundaries (unchanged)

- All Intelligence Report sections remain **backend-derived and read-only**; no
  section is fixture-backed and no AI/LLM runs.
- The evidence reflects a **local, single-user, demo-grade** runtime — not a
  production or hosted deployment.
- Evidence reflects the **recorded capture session**; it is not a CI guarantee.

## Scope confirmation

Phase 21C did **not** change backend, frontend, CSS, source code, package files,
configs, schema, dependencies, tests, any API contract, or any runtime behavior;
did not modify, mock, hand-edit, or stage any response; and added no AI/LLM,
persistence, auth, or mutation. The change set is documentation/evidence only: this
evidence document, the saved connected-UI screenshots, and narrow status/link
updates to the README and roadmap. **No application behavior changed.**
