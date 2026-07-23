<!-- markdownlint-disable MD041 -->

![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

Hive|Mind is a local-first, graph-primary knowledge intelligence workspace that imports developer-owned sources, normalizes them into a graph, and derives deterministic, evidence-backed signals from their structure.

## Overview

Developer knowledge often starts in notes, source files, project docs, and repeated decisions that become hard to inspect as a whole. Hive|Mind treats that material as owned local data: sources are registered, imported explicitly, normalized into shared records, and projected into a Knowledge Graph that becomes the main workspace rather than a side panel.

The problem Hive|Mind is solving is not "generate more content." It is the quieter developer problem of remembering what exists, where it came from, how it connects, and which signals are trustworthy enough to review. Obsidian remains the writing and thinking layer; Hive|Mind is the structured layer above it, where imported knowledge becomes inspectable graph data.

The product direction is deliberately evidence-oriented. The app favors deterministic backend derivation, provenance, and read-only inspection before mutation or automation. The current Intelligence Report surfaces temporal decay, dreaming suggestions, provenance chains, and query trails as explainable outputs over existing store and graph structure.

Hive|Mind is also developing an **Active Memory and Verification** architecture: a contract-first layer for tools and agents to read verified, evidence-linked project context before acting. Its implemented foundation includes deterministic context packets and a read-only inspector, plus a Repository Observer with bounded snapshot and drift APIs, deterministic repository-evidence projection into candidate memory records, a persistent local repository-workspace registry, and a one-command managed local runtime. The most recent merged phase, Phase 39D, hardened the end-to-end Repository Observer workflow with a bounded transport timeout, an extracted error-classification module, a real end-to-end regression suite, and an [operator guide](docs/operator-repository-observer.md). Multi-agent contribution governance (Agent Lab) is defined and enforced locally through a dependency-free PowerShell preflight.

The next direction is the **Grounded Synthesis Layer** (historical planning label: *Create Layer*, now deprecated): Hive|Mind evolving from a read-only intelligence workspace into a *grounded synthesis workspace built on verified read-only intelligence*, where the grounded intelligence synthesizes proposals, drafts, plans, and bounded change artifacts that a human reviews before anything is applied. Phase 40B lands the backend `grounded-synthesis.v1` **contract and schema foundation**, Phase 40C the first service over it — a deterministic, read-only **grounding context assembly** that packages existing evidence into a bounded context packet and generates nothing — and Phase 40D the deterministic, read-only **validation guardrails** that decide whether such a packet is grounded, consistent, and provenance-complete enough to hand to a future synthesis capability. The synthesis capability itself remains **planned architecture**, not implemented functionality — see [Direction: the Grounded Synthesis Layer](#direction-the-grounded-synthesis-layer-contracts-grounding-assembly-and-validation-guardrails) and the [Grounded Synthesis Layer architecture](docs/create-layer-architecture.md).

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
- **Implemented (context packet API):** `POST /api/active-memory/context-packet`, a thin, read-only, stateless endpoint over the existing builder — a validated request (`project_id`, caller-supplied `generated_at`, optional exact `scope`, and the record set) returns the existing `ContextPacket` contract. It derives packets from request-supplied records only and mutates nothing.
- **Implemented (frontend inspector):** a read-only Active Memory dock panel where a human explicitly supplies `MemoryRecord` JSON, calls the stateless context-packet endpoint, and inspects the returned `ContextPacket` sections. It keeps entered data only in React state and provides no edit/delete/verify/supersede/retract/resolve controls.
- **Implemented (repository observer contracts):** backend-only `repo-observer.v1` Pydantic contract types for the planned Repository Observer, covering repository identity, conservative scope, snapshots, working-tree state, changed-file summaries, bounded evidence, evidence authority, warnings, limitations, overflow/truncation metadata, and completeness.
- **Implemented (deterministic Git adapter foundation):** backend-only read-only adapter code that runs an allowlisted, bounded Git command set with `shell=False`, parses NUL-delimited porcelain-v2 status evidence, and exposes deterministic low-level conversion helpers over the existing Phase 37I contracts.
- **Implemented (repository observation snapshot service):** backend-only, request-triggered snapshot orchestration over the Git adapter. The service owns the Phase 37K observation boundary, applies conservative `ObserverScope` limit handling, rejects deferred scope features, preserves caller-supplied timestamps, and returns the existing `RepositorySnapshot` contract without duplicating adapter parsing or conversion logic.
- **Implemented (repository observation API):** `POST /api/repository-observer/snapshot`, a thin read-only endpoint over the Phase 37K snapshot service. The request carries a local absolute `repository_root`, caller-supplied `observed_at`, bounded file/snapshot limits, and optional existing `ObserverScope`; the response is the existing `RepositorySnapshot` contract with repository identity, working-tree state, changed files, evidence authority, warnings, limitations, overflow/truncation metadata, and completeness preserved.
- **Implemented (repository observer frontend inspector):** a read-only contextual dock panel over `POST /api/repository-observer/snapshot`. A human submits one bounded local repository observation request and inspects the returned `RepositorySnapshot` sections, including repository identity, branch/HEAD, working-tree state, changed files, evidence, warnings, limitations, overflow/truncation, and completeness. Phase 37N verified and lightly hardened the integration for newest-request-only state updates, safe server-error display, exact endpoint presentation, and long-token wrapping. It keeps request data only in React state and adds no Git mutation controls, browser persistence, watcher, polling loop, ingestion, AI review, or dashboard replacement.
- **Implemented (repository drift analysis):** `POST /api/repository-observer/drift` remains the thin read-only API over the Phase 37O deterministic service, and the existing Repository Observer inspector provides an explicit **Analyze Drift** action. It presents status, baseline/current identity, change counts, bounded file observations, evidence, warnings, limitations, completeness, and overflow without persistence, watchers, background monitoring, or repository mutation.
- **Implemented locally (repository evidence projection, pending completed hardening and final review):** a backend-only, deterministic, request/input-driven projection service that transforms existing Repository Observer results (`RepositorySnapshot` plus optional `RepositoryDriftAnalysis`) into bounded, always-`inactive` candidate Active Memory `MemoryRecord`/`EvidenceRecord` objects with a closed repository-state claim vocabulary (including drift baseline commit and change-kind totals when drift input exists), claim-dependent verification states (observer evidence — including a complete-but-degraded drift analysis — is never automatically trusted), content-derived SHA-256 ids over all output-driving data, distinct input-owned observation and caller-supplied `recorded_at` timestamps, snapshot/drift identity consistency checks, credential-safe remote handling, referentially sound evidence bounding (no dangling evidence references), and explicit warnings/skipped observations/overflow. It is read-only and non-persistent: no endpoint, no watcher, no Active Memory store insertion, no ingestion, no active-state calculation, no contradiction resolution, no AI/LLM behavior, and no repository mutation.
- **Planned:** active-state calculation, evidence resolution, ingestion, and any persistent Active Memory runtime.
- **Boundary:** the store is in-memory with a serialize/restore boundary only, evidence resolution remains deferred, and the API/UI surfaces remain read-only and stateless over caller-supplied records or explicit local repository observation requests — no database, file persistence, write endpoint, ingestion, runtime verification API, repository watcher, automatic resolution, action authorization, AI interpretation, autonomous mutation, or hidden Active Memory store exists yet.

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
  -> read-only explicit-record frontend inspection
  -> read-only repository snapshot API
  -> read-only repository snapshot frontend inspection
  -> read-only repository drift analysis
  -> planned active-state selection
```

The first pipeline is implemented across the current app surfaces. The second pipeline currently exists as merged contracts, a deterministic backend-only in-memory store, deterministic backend-only read-only contradiction detection, backend-only context packet generation, a read-only stateless context-packet endpoint, a read-only frontend inspector for user-supplied records, backend-only Repository Observer schema contracts, a backend-only deterministic Git adapter foundation, a backend-only repository observation snapshot service, a thin read-only snapshot API, a contextual read-only frontend inspector for explicit repository snapshots, and backend-only deterministic drift analysis from the current `HEAD` baseline; later phases will add active-state selection and ingestion.

## Direction: the Grounded Synthesis Layer (Contracts, Grounding Assembly, and Validation Guardrails)

Hive|Mind is evolving from a **read-only intelligence workspace** into a
**grounded synthesis workspace built on verified read-only intelligence**. The
Intelligence Layer stays authoritative for observation, provenance, contradiction
detection, repository evidence, source inspection, and context assembly. A planned
**Grounded Synthesis Layer** (historical planning label: *Create Layer*, now
deprecated) would consume that grounded context and synthesize useful development
outputs — implementation proposals, scoped work packets, architecture and
documentation drafts, code-change and test plans, issue and pull-request drafts,
design briefs, repository patch proposals, agent contribution packets, and
low-authority *Musings*. Within the layer, *The Loom* is the internal capability
that assembles evidence, context, and intent into coherent synthesis outputs;
neither *Musings* nor *The Loom* is a name for the layer itself.

The synthesis capability itself is **still planned, not implemented.** Phase 40B
adds the backend `grounded-synthesis.v1` contract and schema foundation — the
typed shapes a future service will speak — and Phase 40C adds the first service
over them: a deterministic, read-only **grounding context assembly** that packages
evidence Hive|Mind already holds into a bounded `SynthesisContextPacket`. It
collects, normalizes, filters, deduplicates, ranks and bounds existing evidence,
and **generates nothing**: no summary spanning several records, no
recommendation, no drafted content. Assembling grounded *input* is not producing
an *output*.

Phase 40D adds the **validation guardrails** over that assembly — the trust
boundary before any generation exists. A deterministic, read-only validator
decides whether an assembled packet is grounded, internally consistent, and
provenance-complete enough to hand to a future synthesis capability: canonical
evidence identity checks, provenance integrity checking, packet metadata
reconciled against the packet's actual contents (including re-deriving the
content-addressed packet identifier, so an edited packet cannot present the id it
was assembled under), bounds and truncation validation that never clips, explicit
blocking and non-blocking diagnostics, and an explicit synthesis-readiness
determination. **Hive|Mind still does not generate Grounded Synthesis output** —
deciding that grounding is trustworthy is not producing anything from it.

No synthesis producer, API endpoint, frontend surface, persistence, packet cache
or history, database migration, repository write, graph mutation, Active Memory
insertion, or AI/LLM provider integration exists today. Constructing a contract,
assembling a packet, and validating one all perform no filesystem, Git, network,
store, clock, or randomness access; every identifier is content-derived and every
timestamp is caller-supplied.

The design is deliberately bounded by mandatory principles: evidence before
synthesis, proposal before mutation, human-reviewed execution (devdevbuilds remains
the merge gate), deterministic boundaries separated from any future generative
behavior, explicit confidence and limitations, no silent authority escalation,
reusable typed contracts, and auditability. Synthesis outputs are never
automatically accepted as truth and never automatically applied to a repository:
the contracts carry no accepted/approved/committed/applied state at all, pin
`human_review_required` and `read_only` to `True`, and require a proposed
artifact to cite evidence its provenance actually records.

See the [Grounded Synthesis Layer architecture](docs/create-layer-architecture.md), the
[Phase 40A plan](docs/planning/phase-40a-create-layer-foundation-project-cohesion.md),
the [Phase 40B plan](docs/planning/phase-40b-grounded-synthesis-contract-types-schema-foundation.md),
the [Phase 40C plan](docs/planning/phase-40c-grounding-context-assembly-service-mvp.md),
the [Phase 40D plan](docs/planning/phase-40d-synthesis-evidence-provenance-validation-guardrails.md),
and the [roadmap Grounded Synthesis track](docs/roadmap.md#grounded-synthesis-track-planned).

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
| Active Memory context packets | Implemented | Backend-only deterministic packet builder; no persistence, evidence resolver, action authorization, or automatic resolution. |
| Active Memory context packet API | Implemented | `POST /api/active-memory/context-packet`: read-only, stateless, non-mutating endpoint over the existing builder and `ContextPacket` contract. |
| Active Memory frontend inspector | Implemented | Read-only contextual dock panel over the stateless endpoint; records are explicitly supplied by the user and kept only in React state. |
| Repository Observer contracts | Implemented | Backend-only `repo-observer.v1` schema foundation; no filesystem scan, endpoint, or persistence. |
| Repository Git adapter | Implemented | Backend-only deterministic read-only Git command adapter and porcelain-v2 parser; no watcher, API, persistence, ingestion, or repository mutation. |
| Repository snapshot service | Implemented | Backend-only request-triggered service over the Git adapter; no watcher, persistence, ingestion, frontend, or mutation. |
| Repository observation API | Implemented | `POST /api/repository-observer/snapshot`: thin read-only endpoint over Phase 37K using the existing snapshot contract. |
| Repository observer frontend inspector | Implemented | Contextual graph-first dock panel over the snapshot API, verified and hardened in Phase 37N; no Git dashboard, watcher, persistence, ingestion, AI review, or mutation. |
| Repository drift analysis | Implemented / merged | `POST /api/repository-observer/drift` plus an explicit frontend inspector action over the Phase 37O service; no persistence, watcher, background monitoring, Active Memory ingestion, AI/LLM behavior, or mutation. |
| Agent Lab contribution governance | Implemented locally / pending independent audit | Phase 38A documentation contracts plus Phase 38B dependency-free, read-only PowerShell enforcement for repository, Git, session, and JSON composition-manifest state, and a Phase 38C documentation-only Agent Session Pack connecting the policy to the executable preflight. |
| Repository evidence projection | Implemented locally / pending completed hardening and final review | Phase 39A backend-only deterministic projection of Repository Observer results into bounded, always-inactive candidate Active Memory records with claim-dependent verification, distinct observation/recording timestamps, and referentially sound evidence bounding; no endpoint, persistence, ingestion, store insertion, watcher, active-state calculation, contradiction resolution, AI/LLM behavior, or repository mutation. |
| Repository workspace configuration | Implemented locally / pending independent audit | Phase 39B local-only, versioned `repository-workspaces.v1` registry with a deterministic configuration service (OS-appropriate path resolution, atomic corruption-resistant writes, credential-safe remotes, typed failure states, read-only availability diagnostics reusing the Git adapter), a narrow `resolve_active_repository_workspace` seam for a future Repository Observer phase, and a [PowerShell operator tool](scripts/workspaces/README.md); no watcher, polling, automatic observation, Active Memory ingestion, frontend editor, database, or repository mutation. |
| Managed local runtime | Implemented locally / pending independent audit | Phase 39C one-command [runtime launcher](scripts/runtime/README.md) that starts the backend and frontend together, verifies real readiness, and stops only its managed processes (identity-gated by PID + creation time + command-line signature). It resolves the repository through the Phase 39B workspace config and keeps bounded, secret-free runtime metadata/logs outside the repository; no service installer, container system, background daemon, dependency installation, or process termination by generic name. |
| Grounded Synthesis contracts | Implemented locally / pending independent audit | Phase 40B backend-only `grounded-synthesis.v1` contract and schema foundation: synthesis modes (`musings`, `loom` — capabilities within the layer, not layers), request, grounding evidence references, constraints, context packet, proposed artifact, mandatory provenance, validation results, and a bounded readiness vocabulary with no accepted/approved/committed/applied state. Deterministic and caller-clock-owned; no synthesis behavior, producer, endpoint, frontend, persistence, migration, repository write, graph mutation, Active Memory insertion, or AI/LLM integration. |
| Grounding context assembly | Implemented locally / pending independent audit | Phase 40C backend-only deterministic, read-only `GroundingContextAssemblyService` that assembles five existing evidence families (Active Memory evidence records, Repository Observer observations, repository drift findings, contradiction records, Active Memory records) into valid Phase 40B `SynthesisContextPacket` records: explicit eligibility filtering, canonical-identity deduplication with documented winner precedence, criticality-first stable ranking, per-family and packet bounds with represented truncation, surfaced-never-resolved conflicts, deterministic readiness, and bounded secret-free diagnostics. Contracts reused unchanged; raw provider payloads, absolute roots, and remote URLs are never copied. No endpoint, persistence, cache, packet history, frontend, dependency, mutation, or AI/LLM/synthesis generation. |
| Grounded Synthesis validation guardrails | Implemented locally / pending independent audit | Phase 40D backend-only deterministic, read-only `SynthesisContextPacketValidator` deciding whether an assembled packet is trustworthy enough for a future synthesis capability: canonical evidence identity guardrails reusing the assembler's own rule, provenance integrity and resolution checking, fail-closed repository/source safety, packet metadata reconciled against actual contents (evidence and coverage totals, conflict totals, readiness reasons, canonical ordering, and a re-derived content-addressed packet identity), bounds and truncation validation that never clips, blocking and non-blocking diagnostics with severity fixed by the code, and an explicit synthesis-readiness determination projected onto the canonical Phase 40B `SynthesisValidationResult`. Diagnostics carry counts, closed-enum literals, and packet-local identifiers only — never a path, remote, credential, or provider payload. Phase 40B and 40C contracts reused unchanged. No endpoint, persistence, frontend, dependency, mutation, or AI/LLM/synthesis generation. |
| Grounded Synthesis runtime | Planned | The deterministic producer, the read-only API and workspace, and the review/export/handoff workflow are not implemented. Hive\|Mind does not generate Grounded Synthesis output. |
| Active Memory runtime | Planned | Active-state calculation, write endpoints, durable memory, ingestion, and evidence resolver are not implemented. |

## Architecture And Stack

- **Frontend:** React, TypeScript, Vite, plain CSS.
- **Backend:** Python, FastAPI, Pydantic.
- **Storage:** local JSON-backed `HiveStore` model and source records.
- **Contracts:** Pydantic models mirrored by TypeScript types; Phase 37B adds Active Memory contract parity tests. Phase 40B adds the backend-only `grounded-synthesis.v1` contract family (no frontend mirror yet).
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

### One-command local runtime (optional)

Once you have [registered the Hive|Mind workspace](scripts/workspaces/README.md),
you can start both services with a single command instead of two terminals:

```powershell
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 start     # start backend + frontend, wait for readiness
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 status    # read-only health report
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 stop      # stop only the managed processes
```

It launches the same backend (`8787`) and frontend (`5173`), waits for both to
become reachable, and stops only the processes it started. See the
[managed local runtime guide](docs/operator-runtime.md) for details.

## Validation

```powershell
npm run check:frontend
npm run check:backend
```

The root `check` script runs both validation commands.

## Current Limitations

Hive|Mind is currently a local, single-user developer tool. It has no authentication, authorization, multi-user support, cloud sync, or production deployment hardening. Obsidian import is explicit and one-shot; there is no live vault watcher and no write-back. The Knowledge Graph and Intelligence Report are read-only, and suggestions are advisory only. Query-history persistence remains absent, so query-history-dependent categories stay deferred. The Active Memory store is deterministic but in-memory only (a serialize/restore boundary, no committed persistence medium); contradiction detection is backend-derived, read-only, and covers four of the five contract classes (`frontend_only_vs_backend_modification` is deferred, and no automatic resolution exists); the context packet endpoint and inspector are read-only and stateless — they derive packets from records explicitly supplied in the current request, with no server-side memory store, persistence, ingestion, evidence resolver, AI interpretation, action authorization, or mutation controls. The Repository Observer now has backend schema contracts, a deterministic read-only Git adapter foundation, a backend-only request-triggered snapshot service, a thin local API for explicit snapshot requests, a contextual frontend inspector for one-shot snapshot visibility, and backend-only drift analysis from the current `HEAD` baseline. It still has no watcher, polling loop, persistence, ingestion, Git write operation, AI review, or production-ready runtime. Gesture tracking remains experimental and needs live tuning. The product does not run autonomous agents or mutate repositories.

## Roadmap

The repository-intelligence sequence through Phase 39D is complete and merged on
`main`, and Phase 40A opened the Grounded Synthesis track. The active
contributions are the first implementation phases of that track:

```text
40A - Grounded Synthesis Foundation Planning + Project Cohesion (merged)
      (historical planning label: Create Layer Foundation Planning + Project Cohesion)
40B - Grounded Synthesis Contract Types + Schema Foundation
      (backend contracts only / pending independent audit)
40C - Grounding Context Assembly Service MVP
      (backend deterministic read-only assembly / pending independent audit)
40D - Synthesis Evidence, Provenance, and Validation Guardrails
      (backend deterministic read-only validation / pending independent audit)
```

Phases 38A–39D are merged: Agent Lab multi-agent [contribution contracts](docs/agent-lab/README.md) and a [local PowerShell governance preflight](scripts/governance/README.md); deterministic repository-evidence projection into candidate memory records; a persistent local [repository-workspace registry](scripts/workspaces/README.md); a one-command [managed local runtime](docs/operator-runtime.md); and Repository Observer [end-to-end workflow hardening and failure-state QA](docs/operator-repository-observer.md). Phase 40A defined the **Grounded Synthesis Layer** foundation, Phase 40B added its backend `grounded-synthesis.v1` contract and schema foundation, Phase 40C added the deterministic, read-only grounding context assembly service over those contracts, and Phase 40D adds the deterministic, read-only validation guardrails that decide whether an assembled packet is trustworthy enough to hand onward (see [Direction: the Grounded Synthesis Layer](#direction-the-grounded-synthesis-layer-contracts-grounding-assembly-and-validation-guardrails)); no synthesis generation, producer, endpoint, frontend, persistence, or AI/LLM integration exists. Phase 36K remains paused, not canceled or completed. Active Memory continues to govern project data and verification architecture while Agent Lab governs contribution workflow. The complete chronology and the Grounded Synthesis track belong in the [roadmap](docs/roadmap.md).

## Documentation

- [Full roadmap](docs/roadmap.md)
- [Grounded Synthesis Layer architecture (planned)](docs/create-layer-architecture.md)
- [Phase 40A Grounded Synthesis foundation planning](docs/planning/phase-40a-create-layer-foundation-project-cohesion.md)
- [Phase 40B Grounded Synthesis contract types and schema foundation](docs/planning/phase-40b-grounded-synthesis-contract-types-schema-foundation.md)
- [Phase 40C grounding context assembly service MVP](docs/planning/phase-40c-grounding-context-assembly-service-mvp.md)
- [Phase 40D synthesis evidence, provenance, and validation guardrails](docs/planning/phase-40d-synthesis-evidence-provenance-validation-guardrails.md)
- [Design-asset cohesion assessment](docs/design-asset-cohesion-assessment.md)
- [API contract](docs/api-contract.md)
- [Active Memory and Verification reference](docs/active-agent-memory-verification-layer.md)
- [Agent Lab contribution governance](docs/agent-lab/README.md)
- [Agent session launch guide](docs/agent-lab/agent-session-launch-guide.md)
- [Managed local runtime guide](docs/operator-runtime.md)
- [Phase 37A Active Memory planning](docs/planning/phase-37a-active-agent-memory-verification-layer-planning.md)
- [Phase 37H Repository Observer planning](docs/planning/phase-37h-repository-observer-planning.md)
- [Intelligence Surface Plan](docs/intelligence-surface-plan.md)
- [Security threat model and vulnerability test plan](docs/security/threat-model-and-vulnerability-test-plan.md)
- [Demo guide](docs/demo-guide.md)
- [Final demo script](docs/demo/final-demo-script.md)
- [Portfolio presentation lock](docs/demo/portfolio-presentation-lock.md)
- [Frontend asset contract](docs/frontend-asset-contract.md)
- [Latest Spatial Hive evidence](docs/demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)

## Project Framing

Hive|Mind is a real development tool. It is built to improve how a developer works
with their own project: organization, repository awareness, evidence quality,
provenance, workflow speed, knowledge consistency, agent coordination,
implementation planning, safe synthesis, and overall developer productivity. It is
a repository-aware development intelligence workspace, an active-memory and
verification layer, a human-reviewed multi-agent development environment, and — as
the Grounded Synthesis Layer lands — a grounded synthesis and coordination system.

It also stands as engineering evidence: full-stack ownership across a
React/FastAPI application, contract-driven backend design, local data handling,
deterministic intelligence derivation, provenance modeling, graph visualization,
security reasoning, and disciplined documentation. Its credibility comes from
keeping the product boundary honest — implemented-versus-planned is stated
plainly — while steadily turning developer knowledge into inspectable structure
and, next, into grounded, human-reviewed synthesis.
