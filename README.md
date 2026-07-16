<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

Hive|Mind is a local-first, graph-primary knowledge intelligence workspace that imports developer-owned sources, normalizes them into a graph, and derives deterministic, evidence-backed signals from their structure.

## Overview

Developer knowledge often starts in notes, source files, project docs, and repeated decisions that become hard to inspect as a whole. Hive|Mind treats that material as owned local data: sources are registered, imported explicitly, normalized into shared records, and projected into a Knowledge Graph that becomes the main workspace rather than a side panel.

The problem Hive|Mind is solving is not "generate more content." It is the quieter developer problem of remembering what exists, where it came from, how it connects, and which signals are trustworthy enough to review. Obsidian remains the writing and thinking layer; Hive|Mind is the structured layer above it, where imported knowledge becomes inspectable graph data.

The product direction is deliberately evidence-oriented. The app favors deterministic backend derivation, provenance, and read-only inspection before mutation or automation. The current Intelligence Report surfaces temporal decay, dreaming suggestions, provenance chains, and query trails as explainable outputs over existing store and graph structure.

Hive|Mind is also developing an **Active Memory and Verification** architecture: a contract-first layer for future tools and agents to read verified, evidence-linked project context before acting. Phase 37B implements the backend and frontend wire contracts for that layer, Phase 37C adds a deterministic, backend-only in-memory store over those contracts (insert, retrieve, deterministic listing/filtering, explicit lifecycle transitions, and a serialize/restore boundary), Phase 37D adds a backend-only, read-only contradiction-detection service that derives contract-valid contradiction records from stored fields without mutating anything or auto-resolving conflicts, and Phase 37E adds backend-only deterministic context packet generation. UI inspection is planned next.

## What Hive|Mind Does

### Knowledge Intake

- **Source Registry:** tracks local source metadata, status, and inspection details.
- **Obsidian import:** performs an explicit one-shot local import from developer-owned notes.
- **Normalization:** maps imported content into shared nodes, edges, sources, and metadata.
- **Source ownership:** keeps local source records visible rather than hiding imported material behind a black-box index.

### Graph Workspace

- **Knowledge Graph:** presents normalized knowledge as the full-surface primary interface.
- **Inspection:** supports node, relationship, source, and contextual overlay inspection.
- **Read-only interaction:** graph exploration does not mutate source records or graph data.
- **Console:** exposes controlled app commands for read-only inspection and status checks.

### Intelligence Report

- **Temporal Knowledge Decay:** derives freshness signals from stored timestamps.
- **Dreaming Suggestions:** derives conservative duplicate, orphan, and stale-link suggestions.
- **Provenance Chains:** traces source/import/node/edge lineage from existing records.
- **Query Trails:** derives structural follow-up, gap, and related-cluster trails.
- **Evidence posture:** every section returns honest empty states when the store does not support a claim.

### Active Memory Foundation

- **Implemented (contracts):** `active-memory.v1` backend Pydantic models and mirrored frontend TypeScript types for memory records, evidence records, verification state, lifecycle state, contradiction records, active-state results, and context packets.
- **Implemented (store):** a deterministic, backend-only in-memory Active Memory store over the `MemoryRecord` contract — insert with duplicate-id rejection, retrieve by id with explicit not-found behavior, deterministic `(created_at, record_id)` listing, contract-backed filtering, table-driven lifecycle transitions with evidence/provenance preservation, and a versioned serialize/restore snapshot boundary.
- **Implemented (contradiction detection):** a backend-only, read-only derivation service over the store that produces contract-valid contradiction records from stored fields alone — `pending_vs_merged`, `clean_vs_dirty_working_tree`, `duplicate_phase_status`, and `current_vs_superseded_decision` — with stable content-derived ids, conservative normalization (no ontology, fuzzy matching, or LLM), `active`-only eligibility, and preserved evidence. It mutates nothing and never auto-resolves a contradiction.
- **Implemented (context packets):** a backend-only, deterministic, read-only packet builder that assembles active records, unresolved contradiction results, lifecycle warnings, verification counts, and rigid prohibited-assumption strings without authorizing actions.
- **Planned:** active-state calculation and a read-only frontend inspector.
- **Boundary:** the store is in-memory with a serialize/restore boundary only, evidence resolution remains deferred, and packet generation has no API or frontend surface — no database, file persistence, endpoint, ingestion, runtime verification, repository observer, automatic resolution, action authorization, or UI exists yet.

### Experimental Interaction

- **Spatial Hive:** a 2.5D graph presentation with depth tiers, focus state, pointer orbit, momentum, and elastic node manipulation.
- **Motion sandbox:** an opt-in MediaPipe hand-tracking experiment derives hand orientation and gesture signals from all 21 landmarks.
- **Status:** the tracking foundation exists, but live gesture tuning remains paused and incomplete.

## How It Works

Current product pipeline:

```text
Source
  -> explicit import
  -> normalization
  -> local store
  -> graph projection
  -> deterministic intelligence
  -> read-only inspection
```

Active Memory and Verification pipeline under development:

```text
Evidence
  -> memory record
  -> verification and lifecycle state
  -> contradiction analysis
  -> bounded context packet
  -> planned active-state selection / inspection surfaces
```

The first pipeline is implemented across the current app surfaces. The second pipeline currently exists as merged contracts, a deterministic backend-only in-memory store, deterministic backend-only read-only contradiction detection, and backend-only context packet generation; later phases will add active-state selection, endpoint exposure, and inspector surfaces.

## Visual Evidence

These are real connected-runtime captures from `docs/demo/screenshots/`. They show implemented UI surfaces, not mockups.

**Graph-primary surface**

![Hive|Mind true graph-primary surface](./docs/demo/screenshots/phase-28c-default-graph-primary-surface.png)

The Knowledge Graph fills the viewport with the app chrome and tools presented as contextual overlays.

**Selected node with inspector**

![Hive|Mind selected-node inspector](./docs/demo/screenshots/phase-28c-selected-node-inspector.png)

Selecting a node keeps the graph primary while opening a focused inspector for details and relationships.

**Intelligence overlay**

![Hive|Mind Intelligence overlay](./docs/demo/screenshots/phase-28c-intelligence-overlay.png)

The Intelligence Report opens in context over the graph and shows backend-derived, read-only signals without claiming an Active Memory UI.

More screenshot history and QA notes live in the [Phase 28C graph-primary evidence](docs/demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md), [Phase 33E Spatial Hive evidence](docs/demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md), and [screenshots directory](docs/demo/screenshots/). The Spatial Hive evidence set shows implemented 2.5D depth, focus, and presentation behavior; it does not claim live gesture tuning.

## Current Implementation Status

| Area | Status | Notes |
| --- | --- | --- |
| Source Registry | Implemented | Local source metadata, status, and inspection. |
| Obsidian import | Implemented | Explicit one-shot local import; no watcher or write-back. |
| Knowledge Graph | Implemented | Graph-primary, read-only surface over normalized records. |
| Console | Implemented | Controlled app command surface, not arbitrary shell execution. |
| Intelligence Report | Implemented | Four deterministic backend-derived, read-only sections. |
| Spatial Hive | Implemented / experimental | Presentation-only 2.5D graph interaction. |
| Hand tracking | Experimental | Full-hand foundation exists; live tuning is paused. |
| Active Memory contracts | Implemented | Backend/frontend `active-memory.v1` contract parity. |
| Active Memory store | Implemented | Deterministic backend-only in-memory store: insert, retrieve, ordered listing/filtering, lifecycle transitions, serialize/restore. |
| Active Memory contradiction detection | Implemented | Backend-only, read-only derivation of four contract contradiction classes from stored fields; stable ids, `active`-only eligibility, no mutation or auto-resolution. |
| Active Memory context packets | Implemented | Backend-only deterministic packet builder; no endpoint, frontend surface, persistence, evidence resolver, action authorization, or automatic resolution. |
| Active Memory runtime | Planned | Active-state calculation, observer, endpoint, and UI are not implemented. |

## Architecture And Stack

- **Frontend:** React, TypeScript, Vite, plain CSS.
- **Backend:** Python, FastAPI, Pydantic.
- **Storage:** local JSON-backed `HiveStore` model and source records.
- **Contracts:** Pydantic models mirrored by TypeScript types; Phase 37B adds Active Memory contract parity tests.
- **Source integration:** Obsidian adapter and import service.
- **Visualization:** custom SVG and canvas-oriented graph presentation, without a graph-library dependency.
- **Motion experiment:** MediaPipe Hand Landmarker pinned through `@mediapipe/tasks-vision`.
- **Validation:** `pytest` for backend checks; frontend build/type checks through Vite/TypeScript.

The backend is the source of truth for contracts and deterministic derivation. The frontend consumes those shapes directly and keeps visualization state separate from graph data, so orbiting, selecting, focusing, and experimental gesture input remain presentation behavior unless a later phase explicitly adds a reviewed mutation path.

That separation is important: the app can become richer visually without confusing exploration with data change.

## Engineering Principles

- Local-first ownership of developer data.
- Contracts before runtime expansion.
- Deterministic and inspectable derivation.
- Evidence and provenance before automation.
- Read-only intelligence before mutation.
- Clear implemented-versus-planned boundaries.

The technical credibility of the project comes from those principles being visible in code and docs: API shapes are documented, Pydantic models carry validation boundaries, frontend types mirror backend contracts, intelligence sections are derived from existing records, and limitations are written down instead of hidden. The system is intentionally modest in runtime ambition today, but its contracts are built so later persistence, memory inspection, and verification work can land without pretending the runtime already exists.

## Quick Start

Prerequisites: Node.js 20+ and Python 3.11+.

```powershell
Set-Location "C:\path\to\hive-mind"

npm install

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r apps/backend/requirements-dev.txt
```

Run the backend:

```powershell
npm run dev:backend
```

Run the frontend in another terminal:

```powershell
npm run dev:frontend
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8787](http://localhost:8787)
- Health endpoint: [http://localhost:8787/api/health](http://localhost:8787/api/health)
- API documentation: [http://localhost:8787/docs](http://localhost:8787/docs)

The frontend uses `VITE_API_BASE_URL=http://localhost:8787/api` when configured from `.env.example`, and falls back to the same local backend URL when unset.

## Validation

```powershell
npm run check:frontend
npm run check:backend
```

The root `check` script runs both validation commands.

## Current Limitations

Hive|Mind is currently a local, single-user developer tool. It has no authentication, authorization, multi-user support, cloud sync, or production deployment hardening. Obsidian import is explicit and one-shot; there is no live vault watcher and no write-back. The Knowledge Graph and Intelligence Report are read-only, and suggestions are advisory only. Query-history persistence remains absent, so query-history-dependent categories stay deferred. The Active Memory store is deterministic but in-memory only (a serialize/restore boundary, no committed persistence medium); contradiction detection is backend-derived, read-only, and covers four of the five contract classes (`frontend_only_vs_backend_modification` is deferred, and no automatic resolution exists); context packet generation is backend service-only with no endpoint, frontend surface, evidence resolver, or action authorization; and the rest of the Active Memory runtime — active-state calculation, observer, endpoint, and UI — is not implemented yet. Gesture tracking remains experimental and needs live tuning. The product does not run autonomous agents or mutate repositories.

## Roadmap

The current controlled Track 2 sequence after the completed Phase 37E backend packet builder is:

```text
37F - Frontend memory inspector
37G - Agent session ingestion planning
```

Phase 36K remains paused, not canceled or completed. Gesture tuning can resume after the application's memory foundation reaches a usable state. The complete phase chronology belongs in the [roadmap](docs/roadmap.md).

## Documentation

- [Full roadmap](docs/roadmap.md)
- [API contract](docs/api-contract.md)
- [Active Memory and Verification reference](docs/active-agent-memory-verification-layer.md)
- [Phase 37A Active Memory planning](docs/planning/phase-37a-active-agent-memory-verification-layer-planning.md)
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Security threat model and vulnerability test plan](docs/security/threat-model-and-vulnerability-test-plan.md)
- [Demo guide](docs/demo-guide.md)
- [Final demo script](docs/demo/final-demo-script.md)
- [Portfolio presentation lock](docs/demo/portfolio-presentation-lock.md)
- [Frontend asset contract](docs/frontend-asset-contract.md)
- [Latest Spatial Hive evidence](docs/demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)

## Portfolio Framing

Hive|Mind demonstrates full-stack ownership across a React/FastAPI application, contract-driven backend design, local data handling, deterministic intelligence derivation, provenance modeling, graph visualization, security reasoning, and disciplined documentation. Its portfolio value is not that it claims to be a finished platform; it is that it keeps the product boundary honest while steadily turning developer knowledge into inspectable structure.
