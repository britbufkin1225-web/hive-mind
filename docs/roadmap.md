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
- Active Memory foundation through Phase 37D: contract types, deterministic
  backend-only in-memory store, and deterministic backend-only read-only
  contradiction detection.

The product remains local, single-user, and review-oriented. It does not run
autonomous agents, mutate repositories, persist Active Memory beyond the current
serialize/restore boundary, or generate pre-action context packets yet.

## Active Phase

### Phase 37E — Pre-Action Context Packet MVP

Phase 37E is the next active implementation phase on Track 2 — Agent
Intelligence Infrastructure.

The goal is to assemble relevant, evidence-backed Active Memory into a bounded,
deterministic, read-only context packet before an action or decision. The packet
should make current facts, decisions, constraints, capabilities, unresolved
contradictions, warnings, evidence references, and prohibited assumptions visible
without mutating memory records or resolving uncertainty automatically.

Phase 37E has not been implemented. Context packet contract shapes exist from
Phase 37B, but packet generation logic, active-state calculation, endpoints,
frontend inspection surfaces, repository observers, and AI/LLM interpretation
remain planned work unless a later phase explicitly implements them.

## Immediate Sequence

| Phase | Status | Purpose |
| --- | --- | --- |
| Phase 37E — Pre-Action Context Packet MVP | Next active | Generate a bounded, deterministic, read-only packet from implemented Active Memory contracts, store records, and contradiction results. |
| Phase 37F — Active-memory frontend inspector | Planned | Expose Active Memory state for human inspection without claiming autonomous action or hidden mutation. |
| Phase 37G — Agent session ingestion planning | Planned | Plan governed ingestion from session artifacts into evidence-backed records. |
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
| Context packet endpoint/UI | Add reviewed runtime surfaces after Phase 37E generation logic is implemented. | No endpoint or frontend inspector exists yet. |
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
  and deterministic read-only contradiction detection. It does not yet have
  committed persistence, endpoint exposure, ingestion, active-state calculation,
  context packet generation, frontend inspection, repository observation, or
  automatic resolution.
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
