# Hive|Mind Demo Script

Parent label: **devdevbuilds**

A spoken-walkthrough script for presenting Hive|Mind in a portfolio review, a
recorded demo, or a live screen-share. It pairs with the
[Demo Guide](demo-guide.md) (framing and honesty rules) and the
[Screenshot Checklist](screenshot-checklist.md) (what to capture). Every claim
here matches the frozen, read-only demo state recorded in the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md).

> **Honesty rule:** Hive|Mind's intelligence surfaces are currently
> **read-only and fixture-backed**. When the script says a section is "planned"
> or "demo data," say that out loud. Never narrate fixtures as live derived
> output. See [What to avoid saying](#what-to-avoid-saying).

Estimated length: ~4–6 minutes spoken, or ~8 screenshots for a written
walkthrough.

---

## Opening pitch

> "This is Hive|Mind — a local-first knowledge graph dashboard I built as a
> full-stack backend and cybersecurity portfolio project. It takes the notes I
> write in Obsidian and turns them into a normalized, inspectable graph behind a
> FastAPI backend and a React frontend."

Keep it to two sentences. The goal is to set the frame: *source material in,
structured queryable knowledge out.*

## Problem statement

> "Personal knowledge tools like Obsidian are great for writing, but the
> structure stays locked inside markdown files. There's no governed data model,
> no API, and no way to reason over the whole corpus. Hive|Mind is the layer
> that sits above the notes and turns that writing into structured knowledge you
> can register, normalize, query, and inspect."

The contrast to land: **Obsidian is where you think; Hive|Mind is where that
thinking becomes a graph you can inspect.**

## What Hive|Mind is

> "Concretely, it's five surfaces: a Source Registry, an Obsidian import flow, a
> read-only Knowledge Graph with a custom SVG visualization, a read-only
> Intelligence Report, and a safe app console. Everything is local-first and
> read-only by design — nothing mutates stored state automatically."

## Architecture explanation

> "The backend is FastAPI with Pydantic contracts over a local JSON-backed
> store I call `HiveStore`. Source content is normalized into a shared
> node/edge model rather than stored as raw markdown. The frontend is Vite,
> React, and TypeScript talking to that API. There's no database server, no
> auth layer, and no AI calls — it's a clean, inspectable foundation."

Point to `/docs` (the FastAPI interactive docs) here if you have the backend
running — it makes the contract-first design concrete.

## Source Registry walkthrough

> "This is the Source Registry. Each connected knowledge source is tracked here
> with its status and import metadata. Selecting a source opens an inspector
> with its details — this is the governance layer that knows where every piece
> of knowledge entered the system."

Screenshot target: the source list plus a selected-source inspector state.

## Obsidian Import walkthrough

> "Hive|Mind's first source adapter is Obsidian. The import flow reads markdown
> content and normalizes it into the node/edge model, then records the import
> metadata back on the source. To be clear, this is a one-shot import — there's
> no live filesystem watcher yet; that's intentionally deferred."

Screenshot target: the import action area and the resulting source metadata.

## Knowledge Graph walkthrough

> "Here's the Knowledge Graph. It's a deterministic, read-only projection of the
> normalized records — a custom SVG visualization with a legend, summary stats,
> and a node/edge inspector. Selecting a node highlights it and everything it
> connects to, and dims the rest. There's no physics simulation and no editing;
> it's a faithful map of the data, not an interactive canvas."

Screenshot targets: the full graph with legend and summary, and a selected-node
(or selected-edge) inspector state.

## Intelligence Report walkthrough

> "This is the Intelligence Report — and this is the part I'm most careful to
> frame honestly. It shows four planned intelligence surfaces: Dreaming
> suggestions, Temporal Knowledge Decay, Provenance Chains, and Query Trails.
> Right now these are populated by **deterministic demo fixtures**, labeled with
> a 'Demo data' badge. The contracts and the UI are real and read-only; the real
> derivation engines are future work. This panel shows where the product is
> headed, not logic that runs today."

Screenshot target: the overview summary counts, the "Demo data" badge, and at
least one fixture section with its read-only labeling visible.

## Console walkthrough

> "The Hive Console is a safe app-command interface — not a shell. It runs
> read-only commands like `help`, `status`, and `list nodes` against the store.
> Shell-style or unsafe commands are rejected. It's a controlled query surface,
> not arbitrary code execution."

Screenshot target: console output for `help` or `status`.

## Current implemented features

Say plainly what is real today:

- FastAPI backend with health/status routes and a local JSON-backed `HiveStore`.
- Source Registry: backend, frontend panel, and inspector.
- Obsidian one-shot import with source-metadata visibility.
- Read-only Knowledge Graph API, panel, and custom SVG visualization with
  node/edge inspector.
- Read-only Intelligence Report API and panel (fixture-backed).
- Safe Hive Console API and panel.

## Planned intelligence features

Say plainly what is *not* built yet:

- Real Dreaming logic — suggestions derived from actual graph/store state.
- Real Temporal Knowledge Decay — freshness/staleness from real timestamps.
- Real Provenance inference — lineage built from real import records.
- Query memory / knowledge trails — persisted, reviewable query history.
- Any AI/LLM integration — only after a separate plan and guardrail review.

See the [Roadmap](roadmap.md) and
[Intelligence Surface Plan](intelligence-surface-plan.md) for the intended order.

## Portfolio / dev explanation

> "From a development standpoint, this was built in tightly scoped, reviewable
> phases — contracts first, then deterministic read-only surfaces, then UI.
> Every phase has a guardrail doc, and the intelligence layer is deliberately
> kept honest: read-only fixtures clearly labeled as demo data, so the project
> never overclaims. The coordination model for the AI-assisted build lives in
> `docs/agent-lab/`."

This is the part that signals engineering judgment: scoped phases, honest
labeling, contracts before logic.

## Closing summary

> "So that's Hive|Mind: a local-first knowledge graph that normalizes Obsidian
> notes into a governed, inspectable data model behind a clean FastAPI/React
> stack. The foundation is real and read-only today, and the intelligence layer
> has honest contracts and fixtures pointing at where it's headed next."

---

## What to avoid saying

Pulled from the [Demo Guide](demo-guide.md) — do not say:

- "The app uses AI to find connections."
- "Temporal decay is implemented."
- "The provenance engine traces every fact."
- "Query trails are persisted."
- "It watches my vault live."

Instead, use:

> "The Intelligence Report is a deterministic fixture demo that shows where
> Hive|Mind is headed. The contracts and UI exist, but real Dreaming, temporal
> decay, provenance inference, query memory, and AI/LLM logic are future work."

## Pre-demo checklist

Run before presenting (see the [Demo Guide](demo-guide.md) for detail):

```bash
npm run check:frontend
npm run check:backend
npm run dev:backend
npm run dev:frontend
```

Then confirm:

- Backend connection shows **Connected**.
- Source Registry renders records and inspector details.
- Knowledge Graph renders nodes/edges, the legend, and selected-item details.
- Intelligence Report renders every fixture section with its **Demo data** badge.
- Console accepts `help` / `status` and rejects unsafe commands.
