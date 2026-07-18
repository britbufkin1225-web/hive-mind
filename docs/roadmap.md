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
- Active Memory foundation through Phase 37F: contract types, deterministic
  backend-only in-memory store, deterministic backend-only read-only
  contradiction detection, backend-only deterministic context packet
  generation, a read-only context-packet API endpoint, and a read-only frontend
  inspector over user-supplied records.

The product remains local, single-user, and review-oriented. It does not run
autonomous agents, mutate repositories, persist Active Memory beyond the current
serialize/restore boundary, or authorize actions from packet data. The context
packet endpoint is read-only and stateless: it derives a packet from
request-supplied records and mutates nothing. The frontend inspector keeps
entered records only in React state and adds no persistence, ingestion,
repository observer, evidence resolver, AI interpretation, action authorization,
or mutation controls.

## Active Phase

### Phase 37G — Active Memory Frontend Inspector

Phase 37G is implemented on Track 2 — Agent Intelligence Infrastructure — as a
frontend-only, read-only inspector over the Phase 37F context-packet endpoint.
It lets a human enter an explicit `MemoryRecord` JSON array, submit it to the
stateless endpoint, and inspect the returned `ContextPacket` sections.
Active-state calculation, repository observers, persistence, ingestion,
evidence resolution, and AI/LLM interpretation remain planned work unless a
later phase explicitly implements them.

## Immediate Sequence

| Phase | Status | Purpose |
| --- | --- | --- |
| Phase 37E — Pre-Action Context Packet MVP | Implemented | Generates a bounded, deterministic, read-only backend context packet from implemented Active Memory contracts, store records, and contradiction results. |
| Phase 37F — Read-Only Context Packet API Foundation | Implemented | `POST /api/active-memory/context-packet`: a thin, read-only, non-mutating endpoint over the existing `ContextPacket` model and Phase 37E builder; no new packet logic. |
| Phase 37G — Active Memory Frontend Inspector | Implemented | Read-only contextual frontend inspector over the stateless Phase 37F endpoint; records are explicitly supplied by the user and kept only in React state. |
| Phase 37H — Repository observer planning | Planned | Plan repository-observer workflows and trust boundaries before any watcher/runtime automation exists. |

Track 1 — Spatial Interaction remains paused at Phase 36K and is not the active
implementation track.

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
| Repository observer | Plan before implementation; keep evidence scoped and human-reviewable. | No watcher or automatic repository mutation exists. |
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
  explicitly supplied records. It does not yet have committed persistence, write
  endpoints, ingestion, active-state calculation, repository observation,
  evidence resolution, AI interpretation, action authorization, autonomous
  mutation, or automatic resolution.
- Gesture tracking remains experimental; Phase 36K live camera tuning is paused.

## Reference Documents

- [README](../README.md)
- [Active Agent Memory + Verification Layer reference](active-agent-memory-verification-layer.md)
- [Phase 37A Active Agent Memory + Verification Layer Planning](planning/phase-37a-active-agent-memory-verification-layer-planning.md)
- [Intelligence Surface Plan](intelligence-surface-plan.md)
- [Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md)
- [Demo Guide](demo-guide.md)
- [Final Demo Script](demo/final-demo-script.md)
- [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md)
- [Latest Spatial Hive evidence](demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)
