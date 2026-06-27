# Hive|Mind Screenshot Checklist

Use this checklist when preparing portfolio screenshots or demo review notes.
Screenshots should show the implemented product clearly and avoid implying that
the fixture-backed Query Trails section is real derived logic. Temporal Decay,
Dreaming Suggestions, and Provenance Chains are backend-derived logic and can be
shown as such. To narrate each screenshot, follow the
[Demo Script](demo-script.md), which walks the same surfaces in order.

## Primary screenshots

- Full app overview with `devdevbuilds` / Hive|Mind visible.
- Backend connection and API health showing a healthy local backend.
- Source Registry list plus a selected source inspector state.
- Obsidian import action area, if available in the current viewport.
- Knowledge Graph panel with visible nodes, edges, legend, summary stats, and
  selected-node or selected-edge inspector detail.
- Intelligence Report overview showing summary counts, the backend-derived
  Temporal Decay, Dreaming, and Provenance sections, and the clearly read-only
  Query Trail fixture section.
- Console panel showing safe command output, such as `help` or `status`.
- API docs at `/docs` showing implemented backend routes.

## Intelligence Report screenshots

Capture enough context to make each section's status clear:

- Summary counts.
- Temporal Decay rows with the **Backend-derived** badge, a per-row "reason,"
  and the age/review chips (real derived data).
- Dreaming-style suggestion examples (backend-derived).
- Provenance-style chain examples (backend-derived).
- Query trail-style examples (fixture).
- The visible read-only wording plus the "Backend-derived" / "Demo data" badges.

Caption suggestion:

> Read-only Intelligence Report. Temporal Knowledge Decay is backend-derived from
> real store timestamps (deterministic thresholds, no AI); Dreaming Suggestions
> and Provenance Chains are backend-derived from existing graph/source records;
> Query Trails remain deterministic fixtures pending query persistence.

## Backend/API screenshots

Useful API screenshots:

- `GET /api/health`
- `GET /api/status`
- `GET /api/knowledge-graph`
- `GET /api/intelligence/report`
- `POST /api/console/execute`
- `POST /api/obsidian/import` route visible in API docs

Do not screenshot local secrets, personal vault paths, or private note content.

## Visual QA checks

- Text is readable at desktop and mobile widths.
- No panel overlaps another panel.
- Graph nodes/edges are visible and not cropped into illegibility.
- Selected graph item state is visible.
- Query Trail fixture cards do not claim to be real generated output; Temporal
  Decay, Dreaming, and Provenance are correctly shown as backend-derived.
- Console output stays inside its panel.
- Screenshots include enough browser chrome or caption context to identify local
  demo state.

## Portfolio captions

Good caption:

> Hive|Mind normalizes local knowledge sources into a FastAPI-backed graph and
> presents read-only inspection, a console, and an intelligence report whose
> Temporal Decay, Dreaming Suggestions, and Provenance Chains are
> backend-derived while Query Trails remain labeled demo fixtures.

Avoid captions that imply:

- Production deployment.
- Multi-user auth.
- Live filesystem watching.
- Real AI/LLM reasoning.
- Automated graph mutation.

