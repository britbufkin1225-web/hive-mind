# Hive|Mind Screenshot Checklist

Use this checklist when preparing portfolio screenshots or demo review notes.
Screenshots should show the implemented product clearly and avoid implying that
fixture-only intelligence is real derived logic. To narrate each screenshot,
follow the [Demo Script](demo-script.md), which walks the same surfaces in
order.

## Primary screenshots

- Full app overview with `devdevbuilds` / Hive|Mind visible.
- Backend connection and API health showing a healthy local backend.
- Source Registry list plus a selected source inspector state.
- Obsidian import action area, if available in the current viewport.
- Knowledge Graph panel with visible nodes, edges, legend, summary stats, and
  selected-node or selected-edge inspector detail.
- Intelligence Report overview showing summary counts and clearly read-only
  fixture sections.
- Console panel showing safe command output, such as `help` or `status`.
- API docs at `/docs` showing implemented backend routes.

## Intelligence Report screenshots

Capture enough context to make the fixture status clear:

- Summary counts.
- Dreaming-style suggestion examples.
- Temporal decay-style examples.
- Provenance-style chain examples.
- Query trail-style examples.
- Any visible read-only/demo wording.

Caption suggestion:

> Read-only Intelligence Report demo populated by deterministic fixtures. Real
> Dreaming, temporal decay, provenance inference, query persistence, and AI/LLM
> logic are planned future work.

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
- Intelligence fixture cards do not claim to be real generated output.
- Console output stays inside its panel.
- Screenshots include enough browser chrome or caption context to identify local
  demo state.

## Portfolio captions

Good caption:

> Hive|Mind normalizes local knowledge sources into a FastAPI-backed graph and
> presents read-only inspection, console, and fixture-backed intelligence demo
> surfaces.

Avoid captions that imply:

- Production deployment.
- Multi-user auth.
- Live filesystem watching.
- Real AI/LLM reasoning.
- Automated graph mutation.

