# Hive|Mind Roadmap

This roadmap summarizes the current product state, the active implementation
direction, completed capability groups, paused work, and known limitations. It is
the status overview for Hive|Mind; detailed phase rationale remains in the linked
planning, QA, release, and architecture documents.

## Current State

Hive|Mind is a local-first, graph-primary knowledge intelligence workspace. The
implemented product imports developer-owned sources explicitly, normalizes them
into a local store, projects them into a read-only Knowledge Graph, and derives
deterministic intelligence surfaces from existing records.

Implemented runtime capabilities include:

- Source Registry metadata and explicit Obsidian import.
- Normalized local store records and read-only graph projection.
- Graph-primary frontend shell with contextual overlays, inspector behavior, and
  console command surface.
- Intelligence Report sections for temporal decay, dreaming suggestions,
  provenance chains, and query trails, all bounded by available store evidence.
- Spatial Hive presentation behavior: graph-first shell, 2.5D depth tiers,
  deterministic living-hive motion, focus state, transient interaction state,
  pointer orbit, momentum, and elastic node manipulation.
- Motion sandbox foundation using MediaPipe hand landmarks, with live gesture
  tuning still paused.
- Active Memory foundation through Phase 37P: contract types, deterministic
  backend-only in-memory store, deterministic backend-only read-only
  contradiction detection, backend-only deterministic context packet
  generation, a read-only context-packet API endpoint, and a read-only frontend
  inspector over user-supplied records, plus backend-only Repository Observer
  contract/schema types, a deterministic read-only Git adapter foundation, a
  backend-only request-triggered repository observation snapshot service, and a
  thin read-only Repository Observer snapshot API with a contextual read-only
  frontend inspector hardened by frontend integration QA, plus backend-only
  deterministic drift analysis from the current `HEAD` baseline and an
  on-demand frontend drift inspector. No watcher, persistence, mutation, AI
  review, background monitoring, or ingestion exists.

The product remains local, single-user, and review-oriented. It does not run
autonomous agents, mutate repositories, persist Active Memory beyond the current
serialize/restore boundary, or authorize actions from packet data. The context
packet endpoint is read-only and stateless: it derives a packet from
request-supplied records and mutates nothing. The frontend inspector keeps
entered records only in React state and adds no persistence, ingestion,
evidence resolver, AI interpretation, action authorization, or mutation
controls. The Repository Observer frontend inspector is also stateless over one
explicit request and keeps repository paths only in React state.

## Active Phase

### Phase 40D.5 — Roadmap Reconciliation + Memory Migration Pivot (documentation-only dependency gate)

Phase 40D.5 is a **documentation-only** phase and the current dependency gate for
the track. It changes no backend or frontend code, contract, schema, API,
dependency, asset, or test. It records one decision: **memory migration now
precedes Grounded Synthesis production**, and reconciles this active roadmap to a
single authoritative Phase 40D.5–40K sequence (see the
[Grounded Synthesis + Memory Migration Track](#grounded-synthesis--memory-migration-track-planned)
below).

The pivot inserts a memory-migration track — a safe, explicit, provenance-
preserving way to bring a user's own history into Active Memory as reviewable
**candidates** — ahead of building any synthesis *producer*, because the Grounded
Synthesis Layer synthesizes over grounded evidence and broadening that evidence
base safely is a prerequisite to production, not a follow-on. The previously
documented active sequence (a provisional Phase 40E "Grounded Synthesis API and
Read-Only Workspace", Phase 40F "Review, Approval, Export, and Agent Handoff
Workflow", Phase 40G "End-to-End QA") is **superseded**: that work is not
cancelled, only renumbered later (Phase 40I, 40J, 40K) so migration can land
first.

**Memory migration, ChatGPT export parsing, candidate projection, reviewed
persistence, verified import, the Grounded Synthesis producer, the read-only API
and workspace, and the review/export/handoff workflow all remain planned.** No
migration capability exists today. Hive|Mind claims **no direct access to private
ChatGPT system memory**; migration will rely on **user-controlled exports or
curated bundles** the user provides explicitly. See the
[Phase 40D.5 decision record](planning/phase-40d-5-roadmap-reconciliation-memory-migration-pivot.md).

### Phase 40D — Synthesis Evidence, Provenance, and Validation Guardrails (merged)

Phase 40D is a **backend service phase only**, now **merged on `main`**. It adds
the deterministic, read-only guardrail layer of the Grounded Synthesis Layer in
`apps/backend/app/services/grounding_validation.py`, with its result contracts in
`apps/backend/app/models/grounded_synthesis_validation.py`. It answers one
question — *is this `SynthesisContextPacket` sufficiently grounded, internally
consistent, and provenance-complete to be passed into a future synthesis
capability?* — and establishes the **trust boundary** between grounding assembly
and any future generation.

Phase 40D introduces:

- **Deterministic packet validation** — a pure function from packet to typed
  report. It never mutates the packet, rewrites or removes an evidence record,
  repairs a provenance reference, re-ranks evidence, re-assembles context, or
  persists a verdict, and it reads no clock, filesystem, Git, store, or network.
- **Evidence identity guardrails** — canonical `(family, NFC-normalized source
  record id)` identity reusing the Phase 40C rule unchanged. Duplicate
  identifiers, materially conflicting duplicates, and conflicting source
  identities block; identical copies are advisory. Records sharing a provider id
  across *different* families are never collapsed, and validation is independent
  of input ordering.
- **Provenance integrity checking** — unresolvable source-record identifiers,
  malformed pointers, subsystem evidence with no declared producer, dangling
  conflict/summary references, and unattributed context summaries block; a
  pointer kind outside the set Hive|Mind's own producers emit for a family is
  advisory, because the Phase 37A contract permits every pointer kind.
- **Packet consistency validation** — declared evidence totals, family coverage
  totals, critical-conflict totals, readiness reasons, canonical ordering, and
  the content-derived packet identifier are all **recomputed from the packet's
  actual contents** rather than trusted. A tampered or assembler-declared packet
  whose summary fields merely look plausible does not pass.
- **Explicit synthesis-readiness determination** — readiness is computed, never
  read off the packet. Any blocking condition blocks, whatever the packet claims;
  an honestly `context_required` packet is not upgraded, and a clean `ready`
  packet is not downgraded by advisory findings.
- **Blocking and non-blocking diagnostics** — a closed code taxonomy with
  severity fixed by the code (a blocking condition cannot be filed as advisory),
  canonically ordered, deduplicated, and projected onto the canonical Phase 40B
  `SynthesisValidationResult`. Messages carry counts, closed-enum literals, and
  packet-local identifiers only — never a path, remote, credential, command
  output, or copied provider payload, even when the offending value is exactly
  what the guardrail rejected.

Fail-closed safety is preserved: unsafe repository identity recorded by the
assembler produces an explicit blocking diagnostic and prevents readiness, is
never normalized into a trusted identity, and never causes the safe evidence
alongside it to be reported as unsafe. Bounds and truncation claims are validated
without clipping or deleting records — an over-full packet is reported as
over-full rather than made to look valid.

**Nothing is generated.** Phase 40D adds no AI/LLM integration, prompt, synthesis
output, musings, loom output, recommendation, or drafted content — Hive|Mind
**still does not generate Grounded Synthesis output**. It also adds no endpoint,
frontend surface, TypeScript mirror, persistence, migration, dependency, or
repository, graph, source, or Active Memory mutation.

The Phase 40B and Phase 40C contracts were reused unchanged; **no contract
correction was required**. See the
[Phase 40D plan](planning/phase-40d-synthesis-evidence-provenance-validation-guardrails.md).

### Phase 40C — Grounding Context Assembly Service MVP

Phase 40C is a **backend service phase only**. It adds the first deterministic
service of the Grounded Synthesis Layer in
`apps/backend/app/services/grounding_context.py`: a read-only assembly of
evidence Hive|Mind already holds into valid Phase 40B `SynthesisContextPacket`
records. It answers one question — *given an eligible grounding request and
existing evidence, what bounded, traceable context packet should a future
synthesis process receive?* — and establishes the grounded **input boundary** for
the rest of the track. It is implemented and locally test-covered, pending
independent audit and the devdevbuilds human merge gate.

The MVP normalizes five existing evidence families that already carry the
Phase 37A/40B grounding vocabulary: Active Memory evidence records, Repository
Observer observations, repository drift findings, contradiction records, and
Active Memory records. Knowledge-graph nodes, source-registry entries, query
trails, Active Memory context packets, and the derived Dreaming/decay/provenance
views are **deliberately deferred** — they carry no evidence type, bounded
reference, scope, or confidence band, so normalizing them would mean inventing
grounding rather than assembling it.

The pipeline is collection → normalization → eligibility filtering →
deduplication → stable ranking → bounded selection → conflict/gap/coverage
construction → readiness evaluation. Deduplication keys on the provider's own
canonical identity (never object identity, `hash()`, or set iteration order);
ranking puts critical conflicts first and ends on a content-derived identifier;
every bound is at or below its Phase 40B ceiling, every truncation is represented
as a warning and a count, and raw candidate overflow fails closed rather than
dropping evidence before its criticality is known. Packet identifiers are derived
from the ordered packet content, so identical input always yields the same id and
material change always yields a different one.

**Nothing is generated.** Phase 40C adds no AI/LLM integration, prompt, synthesis
output, cross-record summary, recommendation, or drafted content; `context_summaries`
is always empty because a summary spanning several evidence records *is*
synthesis. It also adds no endpoint, frontend surface, TypeScript mirror,
persistence, migration, packet cache or history, dependency, or repository, graph,
source, Active Memory, or contradiction mutation. Raw provider payloads — bounded
excerpts, absolute repository roots, remote URLs, caller metadata bags — are never
copied into a packet; packet metadata carries only counts, closed-enum literals,
and fixed slugs.

The Phase 40B contracts were reused unchanged; **no contract correction was
required**. See the
[Phase 40C plan](planning/phase-40c-grounding-context-assembly-service-mvp.md).

### Phase 40B — Grounded Synthesis Contract Types + Schema Foundation

Phase 40B is a **backend contract and schema phase only**. It translates the
Phase 40A architecture into the versioned `grounded-synthesis.v1` contract family
in `apps/backend/app/models/grounded_synthesis.py`: the two synthesis modes
(`musings` and `loom` — capabilities *within* the Grounded Synthesis Layer, never
separate layers), the synthesis request, normalized grounding-evidence
references, bounded synthesis constraints, the synthesis context packet,
mandatory synthesis provenance, the proposed synthesis artifact, an explicit
validation result, and a bounded readiness vocabulary. It is implemented and
locally test-covered, pending Codex architecture/schema review, final independent
audit (Jules), and the devdevbuilds human merge gate. Phase 40C consumes these
contracts unchanged.

**No synthesis behavior exists.** Phase 40B adds no producer, grounding assembly,
evidence lookup, policy engine, API endpoint, frontend surface, persistence,
database schema or migration, repository write, graph mutation, Active Memory
insertion, dependency, or AI/LLM provider integration. Constructing a contract
performs no filesystem, Git, network, store, clock, or randomness access; every
identifier and timestamp is caller-supplied.

The boundary is structural, not conventional: the readiness vocabulary contains
no accepted/approved/canonical/committed/applied state, `human_review_required`
and `read_only` are pinned `True` and reject being disabled, provenance is a
required field on every artifact, a `proposed` artifact must cite evidence its
provenance records as used, an ungrounded packet cannot call itself `ready`, and
`extra="forbid"` on every model keeps provider configuration (model name,
temperature, token budget, prompt template, credentials) out of the contracts.
Future outputs are **proposals requiring human review**; devdevbuilds remains the
decision-maker and merge gate.

*Scope note:* Phase 40A proposed 40B as backend contracts *plus* a mirrored
frontend TypeScript parity test. The Phase 40B brief scopes this phase to the
backend only and prohibits frontend changes, so no frontend mirror or parity test
was added. The frontend mirror remains available to a later phase.

See the [Phase 40B plan](planning/phase-40b-grounded-synthesis-contract-types-schema-foundation.md)
and the [Grounded Synthesis + Memory Migration Track](#grounded-synthesis--memory-migration-track-planned) below.

### Phase 40A — Grounded Synthesis Foundation Planning + Project Cohesion (merged)

Phase 40A is a documentation, architecture, and project-cohesion phase. Its
historical planning label (and branch/commit name) is *Create Layer Foundation
Planning + Project Cohesion*; the architecture it establishes is now formally
named the **Grounded Synthesis Layer** (*Create Layer* is deprecated
terminology). It is merged on `main`. It defines the foundation for a
new **Grounded Synthesis Layer** — the planned capability that lets Hive|Mind's
grounded read-only intelligence *synthesize* development outputs (proposals,
drafts, plans, work packets, bounded artifacts, and low-authority Musings) while
staying evidence-grounded and never becoming an autonomous code generator or
silent repository mutator. It adds the
[Grounded Synthesis Layer architecture](create-layer-architecture.md), the
[Phase 40A plan](planning/phase-40a-create-layer-foundation-project-cohesion.md),
the [design-asset cohesion assessment](design-asset-cohesion-assessment.md), and
the Grounded Synthesis track below. It changes no runtime, contract, endpoint, UI,
dependency, or repository behavior; the Grounded Synthesis Layer is **planned, not
implemented**. See the [Grounded Synthesis + Memory Migration Track](#grounded-synthesis--memory-migration-track-planned)
below.

The prior repository-intelligence sequence (Phases 38A–39D) is complete and merged
on `main`; Phase 39D — Repository Observer End-to-End Workflow Hardening +
Failure-State QA is the most recent merged phase and is captured in the
Immediate Sequence table below and in the
[Repository Observer operator guide](operator-repository-observer.md).

### Phase 38B — PowerShell Governance Enforcement (merged)

Phase 38B is a
dependency-free [PowerShell governance preflight](../scripts/governance/README.md)
that deterministically validates canonical repository identity, Git branch and
baseline state, Phase 38A session enums, the Phase 36K lock, optional clean-tree
state, and JSON serializations of the existing composition-manifest schema.

The validator is diagnostic and read-only. It does not fetch or repair Git state,
install hooks, add CI, orchestrate agents, or make human-only composition and
merge decisions. Phase 38A remains the policy source. Active Memory remains the
authority for project data, memory, contradiction, and verification architecture;
Agent Lab governs repository contribution workflow. Neither replaces the other.

Phase 38C adds a documentation-only
[Agent Session Pack](agent-lab/agent-session-launch-guide.md) that lets a
fresh agent connect Phase 38A policy to the Phase 38B preflight from repository
documents alone: an ordered launch sequence, the session-to-parameter mapping,
the exact enum reference, the automated-versus-manual split, fail-closed
recovery, agent-unavailability handling, and copy-paste JSON session-header and
composition-manifest templates. It changes no executable governance behavior and
is pending independent Jules audit.

Phase 37P — Repository Drift API + Frontend Inspector Integration is complete
and merged at `0b901ef0a02857745afe9e5cf4cab0486ba7a6bb`. Its bounded,
read-only behavior remains unchanged.

The prior Phase 37G frontend inspector remains implemented as a frontend-only,
read-only inspector over the Phase 37F context-packet endpoint. Active-state
calculation, persistence, ingestion, evidence resolution, and AI/LLM
interpretation remain planned work unless a later phase explicitly implements
them.

## Immediate Sequence

| Phase | Status | Purpose |
| --- | --- | --- |
| Phase 37E — Pre-Action Context Packet MVP | Implemented | Generates a bounded, deterministic, read-only backend context packet from implemented Active Memory contracts, store records, and contradiction results. |
| Phase 37F — Read-Only Context Packet API Foundation | Implemented | `POST /api/active-memory/context-packet`: a thin, read-only, non-mutating endpoint over the existing `ContextPacket` model and Phase 37E builder; no new packet logic. |
| Phase 37G — Active Memory Frontend Inspector | Implemented | Read-only contextual frontend inspector over the stateless Phase 37F endpoint; records are explicitly supplied by the user and kept only in React state. |
| Phase 37H — Repository Observer Planning | Documentation complete | Documentation-only plan for a future read-only repository-observer evidence provider: responsibilities, identity model, snapshot contract, evidence hierarchy, integration boundary, security model, bounded behavior, MVP, and follow-on sequence. No runtime. |
| Phase 37I — Repository Observer Contract Types / Schema Alignment | Implemented | Backend-only `repo-observer.v1` Pydantic contract foundation for identity, scope, snapshots, working-tree state, file summaries, evidence, warnings, limitations, overflow, and completeness. No runtime. |
| Phase 37J — Deterministic Git Adapter Foundation | Implemented | Backend-only read-only Git command adapter and porcelain-v2 parser over the Phase 37I contracts. No snapshot service, API, watcher, persistence, ingestion, or mutation. |
| Phase 37K — Repository Observation Snapshot Service MVP | Implemented | Backend-only request-triggered snapshot service over the Phase 37J adapter and Phase 37I contracts. No watcher, persistence, ingestion, frontend, or mutation. |
| Phase 37L — Read-Only Repository Observation API Foundation | Implemented | `POST /api/repository-observer/snapshot`: thin read-only API over Phase 37K and the existing `RepositorySnapshot` contract. No persistence, ingestion, frontend, AI/LLM behavior, or mutation. |
| Phase 37M — Read-Only Repository Observer Frontend Inspector MVP | Implemented | Contextual graph-first dock panel over the Phase 37L endpoint. Renders the backend snapshot contract without watcher, persistence, ingestion, AI review, Git dashboard, or mutation. |
| Phase 37N — Repository Observer Frontend Integration QA + Hardening | Implemented | Verified and lightly hardened the Phase 37M frontend inspector against the Phase 37L endpoint contract. No backend, schema, dependency, persistence, ingestion, AI review, Git dashboard, or mutation changes. |
| Phase 37O — Deterministic Repository Drift Analysis MVP | Implemented | Backend-only `POST /api/repository-observer/drift` over current `HEAD`, with deterministic file-level drift classification, evidence, bounds, overflow, and safe errors. No persistence, frontend, ingestion, AI/LLM behavior, or mutation. |
| Phase 37P — Repository Drift API + Frontend Inspector Integration | Implemented / merged | Reuses Phase 37O through the existing drift API and adds an explicit, bounded, newest-request-only drift inspector to the Repository Observer panel. No persistence, watcher, monitoring, or mutation. |
| Phase 38A — Multi-Agent Contribution Contracts + Composition Governance | Implemented locally / pending independent audit | Documentation-only Agent Lab governance for contribution authority, isolation, evidence, composition, and human merge gates. |
| Phase 38B — PowerShell Governance Enforcement | Implemented locally / pending independent audit | Dependency-free local validation of repository identity, Git state, session declarations, and JSON composition manifests; no hook, CI, runtime service, or Git repair. |
| Phase 38C — Governance Adoption + Agent Session Pack Integration | Implemented locally / pending independent audit | Documentation-only Agent Session Pack — launch guide, unavailability/fallback guide, and JSON session-header and composition-manifest templates — connecting Phase 38A policy to the Phase 38B preflight. No executable governance behavior changes. |
| Phase 39A — Deterministic Repository Evidence Projection MVP | Implemented locally / pending completed hardening and final review | Backend-only, deterministic, request/input-driven, read-only projection of existing Repository Observer results into bounded, always-inactive candidate Active Memory records and evidence records with claim-dependent verification (limitations degrade verification where relevant), distinct observation and caller-supplied recording timestamps, snapshot/drift identity consistency, credential-safe remote handling, referentially sound evidence bounding (no dangling references), aggregate drift claims (baseline commit plus change-kind totals), and explicit warnings, skipped observations, and overflow. No endpoint, persistence, ingestion, Active Memory store insertion, watcher, active-state calculation, contradiction resolution, AI/LLM behavior, or repository mutation. |
| Phase 39B — Persistent Local Repository Workspace Configuration | Implemented locally / pending independent audit | Local-only, versioned `repository-workspaces.v1` workspace registry: a bounded contract, a deterministic configuration service (OS-appropriate path resolution with a `HIVEMIND_WORKSPACE_CONFIG_PATH` override, atomic corruption-resistant writes, credential-safe remotes, typed failure states, and read-only availability diagnostics that reuse the Phase 37J Git adapter), a narrow `resolve_active_repository_workspace` seam for a future Repository Observer phase, and a [PowerShell operator tool](../scripts/workspaces/README.md) over the authoritative Python CLI. No background observation, polling, watcher, automatic Repository Observer execution, Active Memory insertion, frontend, database, or repository mutation. |
| Phase 39C — One-Command Local Runtime Startup and Shutdown | Implemented locally / pending independent audit | Managed local [runtime launcher](../scripts/runtime/README.md) (`start`/`status`/`stop`/`restart`/`verify`) that resolves the repository through the Phase 39B workspace config, starts the backend (uvicorn, `8787`) and frontend (vite, `5173`) together, verifies real backend health and frontend reachability with bounded waits, rolls back a partial start, and stops only its managed processes (identity-gated by PID + process creation time + command-line signature). Bounded, secret-free runtime metadata (`hivemind-runtime.v1`) and logs live outside the repository. No service installer, scheduled task, container system, background daemon, dependency installation, backend/frontend feature change, or process termination by generic executable name. |
| Phase 39D — Repository Observer End-to-End Workflow Hardening + Failure-State QA | Implemented locally / pending independent audit | Reliability and failure-state hardening of the existing workspace → runtime → Repository Observer → evidence path. Adds a bounded client-side request timeout so a hung backend surfaces as a distinct, recoverable *timed out* transport state; extracts the deterministic operator-facing error classification into a testable module; adds an end-to-end regression suite exercising the real router → snapshot/drift service → Git adapter path over a real temporary repository (clean, dirty, detached `HEAD`, unborn, non-repository, credential-redacted remote, and repeated-request determinism); and documents the full operator workflow, failure-state taxonomy, and recovery in an [operator guide](operator-repository-observer.md). No new endpoint, feature expansion, persistence, watcher, dependency, Active Memory insertion, or repository mutation. |

Phase 38B remains locally implemented pending independent audit and hardening.
Phase 38C is documentation-only, implemented locally and pending independent
Jules audit; it adds no executable governance behavior. Phase 39A is
implemented locally and pending completed hardening and final review; it
produces candidates only — every projected candidate is `inactive`, projection
never activates records, Repository Observer evidence is never automatically
trusted, no dangling evidence references are permitted, and no record enters an
Active Memory store. The frontend-design track remains deferred. Each phase
remains independently scoped and reviewable.

Phase 39B is implemented locally and pending independent audit. It adds a
persistent, local-only repository workspace registry so an operator can register
a Git repository once and have Hive|Mind remember it between sessions. The
configuration is stored outside the repository (on Windows, under the user's
local application-data directory) and is never committed. Configuration is not
encrypted, workspaces are not synchronized across machines, no frontend workspace
editor exists, Repository Observer is not run automatically, Active Memory does
not ingest configured repositories, and repository contents and Git history are
never mutated. The `resolve_active_repository_workspace` seam is inert until a
future phase chooses to consume it. See the
[Phase 39B design note](phase-39b-persistent-local-repository-workspace-configuration.md).

Phase 39C is implemented locally and pending independent audit. Building directly
on the Phase 39B workspace resolution, it adds a single operator command that
starts the backend and frontend together, waits (bounded) for the backend
`/health` endpoint and the frontend to actually respond, and later stops only the
processes it started — each shutdown gated by a per-process identity check (PID,
process creation time, and command-line signature) so an unrelated or PID-reused
process is never terminated, and nothing is ever killed by generic executable
name. A partial start rolls back automatically. Runtime metadata and logs are
bounded, human-inspectable, secret-free, and stored outside the repository under
the user's local application-data directory. It is not a service installer,
scheduled task, container system, or background daemon; it never installs
dependencies and makes no backend or frontend feature change. See the
[managed local runtime guide](operator-runtime.md).

Phase 39D is implemented locally and pending independent audit. It hardens the
existing local Repository Observer workflow rather than expanding it: the observer
transport now fails a hung backend as a distinct, recoverable timeout instead of
pending indefinitely; the operator-facing error classification is extracted into
a self-tested module; a new end-to-end regression suite drives the real router,
snapshot and drift services, and Git adapter against a real temporary repository
to prove deterministic, credential-safe evidence across clean, dirty, detached
`HEAD`, unborn, and non-repository states; and the full operator workflow —
including the failure-state taxonomy and recovery actions — is documented. No new
endpoint, feature, dependency, persistence, watcher, Active Memory insertion, or
repository mutation is introduced. See the
[Repository Observer operator guide](operator-repository-observer.md).

Track 1 — Spatial Interaction remains paused at Phase 36K and is not the active
implementation track.

## Grounded Synthesis + Memory Migration Track (Planned)

The major direction remains the **Grounded Synthesis Layer** (historical planning
label: *Create Layer*, now deprecated): Hive|Mind evolving from a read-only
intelligence workspace into a *grounded synthesis workspace built on verified
read-only intelligence*. The Intelligence Layer stays authoritative for
observation, provenance, contradiction detection, repository evidence, and context
assembly; the Grounded Synthesis Layer consumes that grounded context and
synthesizes proposals, drafts, plans, or bounded change artifacts that are **not**
automatically accepted as truth and **not** automatically applied. *Musings* (low-
authority exploratory outputs) and *The Loom* (the internal capability that
assembles evidence, context, and intent into synthesis outputs) are planned
capabilities within the layer, not names for it. devdevbuilds remains the human
merge gate. Full design is in the
[Grounded Synthesis Layer architecture](create-layer-architecture.md).

**Memory migration now precedes Grounded Synthesis production.** Phase 40D.5
(above) records this pivot: before Hive|Mind builds a synthesis *producer*, it
adds a memory-migration track that brings a user's own history into Active Memory
as reviewable **candidates** through an explicit, provenance-preserving,
fail-closed boundary. Broadening the grounded evidence base safely is a
prerequisite to production, not a follow-on. The previously documented active
sequence (a provisional Phase 40E "Grounded Synthesis API and Read-Only
Workspace", Phase 40F "Review, Approval, Export, and Agent Handoff Workflow",
Phase 40G "End-to-End QA") is **superseded and renumbered** later in the sequence
(Phase 40I, 40J, 40K); that work is not cancelled.

Hive|Mind claims **no direct access to private ChatGPT system memory**. Migration
relies on **user-controlled exports or curated bundles** the user provides
explicitly. Parsed memory records are **candidates** — inactive, unverified,
provenance-linked proposals — until a human reviews and a later phase persists
them; imported material is never treated as verified truth.

The synthesis capability is **still planned, not implemented**. As of the merged
Phase 40D the track has backend contract types, one deterministic, read-only
grounding **assembly** service, and the deterministic **validation guardrails**
over its output: no grounded-synthesis producer, endpoint, UI, patch-application
engine, code-generation service, output persistence, or AI/LLM integration exists
yet. Assembling grounded input is not producing an output, and deciding that
grounding is trustworthy is not producing anything from it — Phase 40C packages
evidence and Phase 40D validates it, and both generate nothing. Memory migration,
ChatGPT export parsing, candidate projection, reviewed persistence, verified
import, the Grounded Synthesis producer, the read-only API and workspace, and the
review/export/handoff workflow are all **planned**.

| Phase | Status | Purpose |
| --- | --- | --- |
| Phase 40A — Grounded Synthesis Foundation Planning + Project Cohesion | Merged | Defines the Grounded Synthesis Layer architecture, product boundary, workflow, request/result lifecycle, evidence/provenance and authority restrictions, failure states, security posture, rejected alternatives, and this track. No runtime. |
| Phase 40B — Grounded Synthesis Contract Types + Schema Foundation | Merged | Introduces the `grounded-synthesis.v1` backend Pydantic contract family: schema version, synthesis modes, request, grounding evidence references, constraints, context packet, provenance, proposed artifact, validation result, and readiness vocabulary. Contracts only — no service, endpoint, persistence, frontend, or runtime behavior. The frontend TypeScript mirror and parity test proposed in 40A were out of scope for this phase and remain available to a later one. |
| Phase 40C — Grounding Context Assembly Service MVP | Merged | Backend-only, deterministic, read-only `GroundingContextAssemblyService` assembling five existing evidence families (Active Memory evidence records, Repository Observer observations, repository drift findings, contradiction records, Active Memory records) into valid Phase 40B `SynthesisContextPacket` records: explicit eligibility filtering, canonical-identity deduplication with documented winner precedence, a criticality-first stable ranking ending on a content-derived identifier, per-family and packet bounds with represented truncation and fail-closed raw-candidate overflow, surfaced-never-resolved conflicts, deterministic readiness, and bounded secret-free diagnostics. Contracts reused unchanged. No endpoint, persistence, cache, packet history, frontend, dependency, mutation, or AI/LLM/synthesis generation. |
| Phase 40D — Synthesis Evidence, Provenance, and Validation Guardrails | Merged | Backend-only, deterministic, read-only `SynthesisContextPacketValidator` over assembled Phase 40C packets: canonical evidence identity guardrails reusing the assembler's own identity rule, provenance integrity and resolution checking, fail-closed repository/source safety, packet consistency recomputed from actual contents (evidence and coverage totals, conflict totals, readiness reasons, canonical ordering, and re-derived content-addressed packet identity), bounds and truncation validation that never clips, blocking and non-blocking diagnostics with severity fixed by the code, and an explicit synthesis-readiness determination projected onto the canonical Phase 40B `SynthesisValidationResult`. Phase 40B and 40C contracts reused unchanged. No endpoint, persistence, frontend, dependency, mutation, or AI/LLM/synthesis generation — Hive\|Mind still does not generate Grounded Synthesis output. Deterministic policy over a *producer*, confidence/freshness indicators, and prohibited-assumption enforcement remain future work, because no producer exists yet. |
| Phase 40D.5 — Roadmap Reconciliation + Memory Migration Pivot | Documentation-only, implemented locally / pending independent audit | Documentation-only dependency gate. Records the decision to sequence memory migration ahead of Grounded Synthesis production and reconciles this roadmap, the README status, and the architecture note to the authoritative Phase 40D.5–40K sequence. No runtime, contract, schema, API, dependency, asset, or test change. See the [decision record](planning/phase-40d-5-roadmap-reconciliation-memory-migration-pivot.md). |
| Phase 40E — Memory Migration Contract + Intake Safety Foundation | Planned | Versioned memory-migration intake contract family and a deterministic, read-only intake-safety assessment over **declared** metadata only (fail-closed path and entry-type handling, explicit bounds, declared-vs-verified digest handling, provenance-preserving descriptors). No export parsing, byte access, persistence, endpoint, or frontend. |
| Phase 40F — Export Parser + Candidate Projection | Planned | Parses a user-controlled export or curated bundle only after Phase 40E judges the intake safe, and projects its contents into inactive, unverified, provenance-linked **candidate** memory records. No persistence and no verified import. |
| Phase 40G — Reviewed Persistence + Verified Import | Planned | First phase that may persist migrated candidates, and only for candidates a human has reviewed. Verified import is human-gated; imported material is never treated as verified truth automatically. |
| Phase 40H — Grounded Synthesis Producer MVP | Planned | The first deterministic synthesis *producer* over grounded, validated context (now including reviewed migrated evidence). Outputs are proposals requiring human review; nothing is auto-applied. |
| Phase 40I — Grounded Synthesis API + Read-Only Workspace | Planned | Thin read-only API and contextual read-only frontend workspace for inspecting synthesis results. No apply/commit/merge/push controls. (Supersedes the provisional Phase 40E numbering.) |
| Phase 40J — Review, Approval, Export, and Agent Handoff Workflow | Planned | Human review/approval, export, and handoff to an external agent or implementation workflow aligned with Agent Lab contribution contracts. Repository effects remain external and human-gated. (Supersedes the provisional Phase 40F numbering.) |
| Phase 40K — End-to-End QA, Operator Documentation, and Release Readiness | Planned | End-to-end QA over the deterministic synthesis and migration paths, operator documentation, and release readiness. (Supersedes the provisional Phase 40G numbering.) |

Phase names past 40A may be refined by later phases with justification. Every
Grounded Synthesis phase preserves the mandatory principles: evidence before
synthesis, proposal before mutation, human-reviewed execution, deterministic
boundaries, explicit confidence and limitations, no silent authority escalation,
reusable typed contracts, and auditability. Phase 36K remains paused and untouched
throughout this track.

## Completed Capability Groups

### Core Platform and Storage

- Phase 1 established the app foundation, local project boundaries, and initial
  backend/frontend separation.
- The backend grew a local JSON-backed `HiveStore`, source registry records,
  API contracts, and deterministic read paths.
- The frontend evolved from dashboard panels into a graph-primary workspace while
  keeping graph exploration read-only.
- Validation practices settled around backend `pytest`, frontend TypeScript/Vite
  checks, and narrow evidence documents for UI/runtime claims.

### Obsidian Import

- The Obsidian track implemented explicit one-shot import from developer-owned
  notes, source registration, normalized nodes/edges, and provenance-aware
  source metadata.
- Import remains explicit and local. There is no live vault watcher and no
  write-back into Obsidian.

### Knowledge Graph and Intelligence

- The Knowledge Graph is implemented as the primary inspection surface over
  normalized records.
- Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails are
  implemented as deterministic, backend-derived, read-only Intelligence Report
  sections.
- Remaining intelligence work includes richer source coverage, query-history
  persistence, selected-node provenance extensions, and per-section error states.
  These remain read-only and do not imply AI/LLM reasoning.

### Security and Release Readiness

- Security planning and regression passes documented local-only threat modeling,
  backend validation/error safety, selected edge-case hardening, and demo-release
  readiness.
- The current posture is demo/developer-tool readiness, not production security.
  Authentication, authorization, rate limiting, audit logging, cloud deployment
  hardening, and multi-user controls remain out of scope.

### Frontend and Spatial Hive Evolution

- The UI moved from dashboard-with-panels toward a graph-first shell with
  overlays, command surfaces, and a persistent graph viewport.
- Spatial Hive work added 2.5D depth, deterministic living-hive motion,
  focus-state behavior, transient interaction state, pointer orbit, momentum,
  and elastic node manipulation.
- MediaPipe hand-tracking foundations exist, including full-hand landmark
  feature extraction and a motion sandbox. Live gesture feel/tuning and evidence
  remain paused under Phase 36K.

### Active Memory and Verification

- **Phase 37A — Active Agent Memory + Verification Layer Planning:** complete
  documentation-only architecture for evidence-backed project memory, separate
  verification/lifecycle axes, contradiction handling, active-state calculation,
  and pre-action context packets.
- **Phase 37B — Active Memory Contract Types / Schema Alignment:** implemented
  backend Pydantic models and mirrored frontend TypeScript types for
  `active-memory.v1`, including memory records, evidence records, verification
  state, lifecycle state, contradiction records, active-state results, and context
  packet shapes.
- **Phase 37C — Deterministic Active Memory Store MVP:** implemented a
  backend-only in-memory store over `MemoryRecord` with duplicate-id rejection,
  explicit not-found behavior, deterministic listing/filtering, lifecycle
  transitions, defensive copies, and a versioned serialize/restore boundary.
- **Phase 37D — Deterministic Active Memory Contradiction Detection MVP:**
  implemented, validated, and merged. It adds a backend-only, read-only detector
  over the 37C store that derives contract-valid contradiction records from
  stored fields. Supported classes are `pending_vs_merged`,
  `clean_vs_dirty_working_tree`, `duplicate_phase_status`, and
  `current_vs_superseded_decision`. Results use stable content-derived ids,
  conservative trim/casefold normalization, `active`-only lifecycle eligibility,
  preserved evidence, and stable ordering. The detector mutates nothing and never
  auto-resolves a contradiction.
- **Phase 37E — Deterministic Pre-Action Context Packet MVP:** implemented. It
  adds a backend-only, read-only packet builder over the 37C store and 37D
  detector. The builder uses caller-supplied timestamps, exact project and
  optional exact scope filtering, active-record kind partitioning, unresolved
  contradiction inclusion, lifecycle warnings for non-active records, verification
  counts, rigid prohibited-assumption templates, and empty top-level evidence
  references until a real evidence resolver exists. It adds no frontend
  surface, persistence, action authorization, automatic contradiction
  resolution, or dependency.
- **Phase 37F — Read-Only Context Packet API Foundation:** implemented. It adds
  `POST /api/active-memory/context-packet`, a thin transport boundary over the
  Phase 37E builder: a validated request (`project_id`, caller-supplied
  `generated_at`, optional exact `scope`, and the record set) is converted into
  an ephemeral request-scoped store, the existing builder runs unchanged, and
  the existing `ContextPacket` contract is returned. The endpoint is
  operationally read-only — no persistence, store mutation, filesystem write,
  clock read, or AI/LLM behavior — and all packet rules and collection limits
  stay in the service layer.
- **Phase 37G — Active Memory Frontend Inspector:** implemented. It adds a
  frontend-only read-only inspector panel to the existing contextual dock. The
  panel provides editable request fields for `project_id`, caller-supplied
  `generated_at`, optional exact scope, and a JSON array of `MemoryRecord`
  objects, then renders the backend `ContextPacket` as structured sections:
  packet identity, repository baseline, verification summary, active record
  collections, unresolved contradictions, warnings, prohibited assumptions, and
  evidence references. It adds no backend changes, no package changes, no
  storage, no browser persistence, no ingestion, no repository observer, no
  evidence resolver, no AI interpretation, no action authorization, and no
  mutation controls.
- **Phase 37H — Repository Observer Planning:** complete documentation-only plan
  for a future read-only Repository Observer evidence provider. It defines the
  observer's responsibilities and non-responsibilities, a deterministic
  repository identity model, an immutable bounded observation snapshot contract,
  a repo-scoped evidence hierarchy (local Git history alone does not prove remote
  pull-request state), the Active Memory integration boundary (the observer emits
  evidence and candidate records; separate services own normalization, dedup,
  contradiction detection, context-packet selection, persistence, and policy),
  deterministic contradiction opportunities, a defensive security/trust model,
  bounded-behavior and overflow rules, a narrow MVP, deferred scope, a hermetic
  test strategy, and a conservative follow-on sequence (37I–37P). No observer,
  Git adapter, subprocess execution, endpoint, schema, dependency, or runtime
  behavior was implemented.
- **Phase 37I — Repository Observer Contract Types / Schema Alignment:**
  implemented backend-only `repo-observer.v1` Pydantic contract types and focused
  tests for the planned Repository Observer. The contracts cover repository
  identity/status, conservative observer scope, working-tree state, changed-file
  summaries, rename/copy path relationships, bounded repository evidence,
  evidence authority, warnings, limitations, overflow/truncation metadata, and
  snapshot completeness. They add validation for negative limits/counts, unsafe
  repository-relative paths, malformed rename/copy records, unbounded excerpts,
  impossible overflow metadata, and contradictory complete/truncated snapshots.
  No observer runtime, Git execution, filesystem scanning, endpoint, persistence,
  ingestion, frontend, dependency, graph, Obsidian, or Phase 36K work was added.
- **Phase 37J — Deterministic Git Adapter Foundation:** implemented a
  backend-only read-only Git adapter over the Phase 37I contracts. Command
  execution is allowlisted and shell-free with explicit `cwd`, bounded timeout,
  bounded stdout/stderr, bounded excerpts, and typed bounded errors. Parsing uses
  NUL-delimited porcelain-v2 status evidence rather than human-readable status
  output, covering branch headers, detached HEAD, unborn branches, ordinary
  tracked changes, untracked paths, unmerged records, renames, and copies.
  Conversion preserves repository-relative paths, deterministic path ordering,
  direct-Git evidence authority, metadata-only limitations, warning records, file
  observation overflow, and honest snapshot completeness. No watcher, API,
  persistence, ingestion, filesystem crawler, GitHub integration, dependency,
  frontend, repository mutation, graph, Obsidian, or Phase 36K work was added.
- **Phase 37K — Repository Observation Snapshot Service MVP:** implemented a
  backend-only request-triggered service over the Phase 37J adapter. It owns
  snapshot orchestration, preserves caller-supplied timestamps, maps conservative
  `ObserverScope` limits into adapter limits, rejects deferred scope features,
  keeps adapter parsing/conversion as the single snapshot-conversion path, and
  returns the existing `RepositorySnapshot` contract. No API route, watcher,
  polling loop, persistence, filesystem crawler, Active Memory ingestion, GitHub
  integration, dependency, frontend surface, repository mutation, graph,
  Obsidian, or Phase 36K work was added.
- **Phase 37L — Read-Only Repository Observation API Foundation:** implemented
  `POST /api/repository-observer/snapshot`, a backend-only read-only endpoint
  over the Phase 37K snapshot service. The request supports an explicit local
  repository root, caller-supplied timestamp, bounded file/snapshot limits, and
  optional existing `ObserverScope`; the response is the existing
  `RepositorySnapshot` contract. Expected failures map to client-safe status
  codes without leaking tracebacks, credentials, raw subprocess commands,
  environment details, or sensitive filesystem internals. No persistence,
  ingestion, watcher, frontend, graph, Obsidian, MediaPipe, AI/LLM, repository
  mutation, or Phase 36K work was added.
- **Phase 37M — Read-Only Repository Observer Frontend Inspector MVP:**
  implemented a frontend-only read-only inspector in the existing contextual
  graph dock. It adds TypeScript mirror contracts, a narrow API client method
  for `POST /api/repository-observer/snapshot`, a bounded request form, readable
  idle/loading/success/error states, and structured rendering for repository
  identity, branch/HEAD, working-tree state, changed files, rename/copy
  relationships, evidence authority, warnings, limitations,
  overflow/truncation, omitted paths, deterministic ordering, and completeness.
  It keeps request state in React only and adds no backend behavior, watcher,
  polling, browser persistence, Active Memory ingestion, AI/LLM behavior, Git
  dashboard, repository mutation, or Phase 36K work.
- **Phase 37N — Repository Observer Frontend Integration QA + Hardening:**
  verified the Phase 37M inspector against the Phase 37L request/response
  contract and made a narrow frontend-only resilience pass. The inspector now
  ignores stale async responses from older submissions, displays server failures
  without echoing backend internals, shows the exact `/api` endpoint, wraps long
  endpoint/path/status tokens more reliably, and extends request-builder
  self-tests for timestamp preservation and blank timestamp rejection. It adds no
  backend changes, schema changes, dependency changes, persistence, ingestion,
  watcher, polling loop, AI review, Git dashboard, repository mutation, or Phase
  36K work.
- **Phase 37O — Deterministic Repository Drift Analysis MVP:** implemented a
  backend-only read-only drift-analysis service and
  `POST /api/repository-observer/drift` endpoint over the existing
  Repository Observer contracts and Git adapter. The MVP supports current
  `HEAD` as the local baseline, resolves the baseline commit from direct Git
  status evidence when available, classifies bounded file-level drift as
  `added`, `modified`, `deleted`, `renamed`, `copied`, `untracked`,
  `type_changed`, `conflicted`, or `unknown`, preserves staged/unstaged and
  untracked flags, reports old/current paths only for authoritative Git
  rename/copy records, and returns evidence, warnings, limitations, overflow,
  and completeness without reading file contents. It adds no frontend,
  persistence, Active Memory ingestion, contradiction integration, GitHub API
  behavior, dependency, AI/LLM interpretation, repository mutation, or Phase 36K
  work.

`frontend_only_vs_backend_modification` is a contract class but is not
implemented in Phase 37D because it needs a deterministic path/scope target model
that does not yet exist.

## Paused Track

### Phase 36K — Full-Hand Gesture Live Camera QA + Control Tuning

Phase 36K is paused and untouched. It is not canceled, completed, resumed, or
superseded by the Active Memory track.

The paused work is live-camera QA and conservative control tuning for the
full-hand gesture foundation. Existing synthetic and non-camera validation does
not prove live hand-motion feel. No new webcam evidence is claimed here.

## Deferred / Future Work

| Area | Future direction | Boundary |
| --- | --- | --- |
| Active Memory persistence | Choose a durable medium after contracts, store semantics, contradiction detection, and context packet generation are stable. | Current store is in-memory with serialize/restore only. |
| Active-state calculation | Derive safe active baselines while preserving unresolved contradictions and missing evidence. | No "newest wins"; unresolved state must stay visible. |
| Context packet UI | Keep the Phase 37G inspector read-only while future phases decide durable memory and observer boundaries. | The inspector exists and remains stateless over user-supplied records. |
| Repository observer | Planned in Phase 37H as a read-only evidence provider; Phase 37I implements backend contract/schema types, Phase 37J implements the deterministic read-only Git adapter foundation, Phase 37K implements the backend-only snapshot service MVP, Phase 37L exposes a thin read-only snapshot API, Phase 37M adds a contextual frontend inspector, Phase 37N hardens that inspector's endpoint integration, and Phase 37O adds backend-only drift analysis from current `HEAD`. Keep evidence scoped and human-reviewable. | No watcher, polling loop, persistence, ingestion, filesystem scanner, frontend drift UI, AI review, Git dashboard, or automatic repository mutation exists. |
| AI/LLM integration | Consider only after deterministic trust boundaries and inspection surfaces are stable. | No AI truth arbitration, autonomous resolution, or autonomous action. |
| Intelligence report expansion | Source coverage, query persistence, and richer provenance/error states. | Read-only derivation over real store data. |
| Spatial interaction | Resume Phase 36K when the project chooses to return to live gesture tuning. | No gesture completion claim without live evidence. |
| Production hardening | Auth, authorization, rate limits, deployment controls, secret handling, and audit logging. | Current app is a local developer tool, not a production service. |

## Current Limitations

- Hive|Mind is local and single-user.
- There is no authentication, authorization, multi-user mode, cloud sync, or
  production deployment hardening.
- Obsidian import is explicit and one-shot; there is no live watcher or
  write-back.
- The Knowledge Graph and Intelligence Report are read-only; suggestions are
  advisory only.
- Query-history persistence does not exist, so query-history-dependent
  intelligence categories remain blocked.
- Active Memory currently has contracts, a deterministic in-memory backend store,
  deterministic read-only contradiction detection, backend context packet
  generation, and a read-only, stateless context-packet endpoint that derives
  packets from request-supplied records, plus a read-only frontend inspector for
  explicitly supplied records, backend-only Repository Observer contract types,
  a deterministic read-only Git adapter foundation, a backend-only
  repository observation snapshot service with a thin read-only API and
  contextual frontend inspector, a frontend integration QA/hardening pass over
  that inspector, and backend-only deterministic repository drift analysis from
  current `HEAD`. It does not yet have committed persistence,
  write endpoints, ingestion, active-state
  calculation, evidence resolution, AI
  interpretation, action authorization, autonomous mutation, or automatic
  resolution.
- Gesture tracking remains experimental; Phase 36K live camera tuning is paused.

## Reference Documents

- [README](../README.md)
- [Grounded Synthesis Layer Architecture (Planned)](create-layer-architecture.md)
- [Phase 40A Grounded Synthesis Foundation Planning + Project Cohesion](planning/phase-40a-create-layer-foundation-project-cohesion.md)
- [Phase 40B Grounded Synthesis Contract Types + Schema Foundation](planning/phase-40b-grounded-synthesis-contract-types-schema-foundation.md)
- [Phase 40C Grounding Context Assembly Service MVP](planning/phase-40c-grounding-context-assembly-service-mvp.md)
- [Phase 40D Synthesis Evidence, Provenance, and Validation Guardrails](planning/phase-40d-synthesis-evidence-provenance-validation-guardrails.md)
- [Phase 40D.5 Roadmap Reconciliation + Memory Migration Pivot](planning/phase-40d-5-roadmap-reconciliation-memory-migration-pivot.md)
- [Design-Asset Cohesion Assessment](design-asset-cohesion-assessment.md)
- [Active Agent Memory + Verification Layer reference](active-agent-memory-verification-layer.md)
- [Phase 37A Active Agent Memory + Verification Layer Planning](planning/phase-37a-active-agent-memory-verification-layer-planning.md)
- [Phase 37H Repository Observer Planning](planning/phase-37h-repository-observer-planning.md)
- [Phase 39B Persistent Local Repository Workspace Configuration](phase-39b-persistent-local-repository-workspace-configuration.md)
- [Repository Workspace Operator Tool](../scripts/workspaces/README.md)
- [Managed Local Runtime Guide](operator-runtime.md)
- [Managed Local Runtime Tool](../scripts/runtime/README.md)
- [Repository Observer Operator Workflow](operator-repository-observer.md)
- [Intelligence Surface Plan](intelligence-surface-plan.md)
- [Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md)
- [Demo Guide](demo-guide.md)
- [Final Demo Script](demo/final-demo-script.md)
- [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md)
- [Latest Spatial Hive evidence](demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)
