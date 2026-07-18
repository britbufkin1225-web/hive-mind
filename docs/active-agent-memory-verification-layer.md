# Active Agent Memory + Verification Layer — Reusable Reference

**Status:** Architecture reference with partial implementation through Phase 37M.
Phase 37B implements the `active-memory.v1` backend/frontend contracts, Phase 37C
implements a deterministic backend-only in-memory store, and Phase 37D implements
a deterministic backend-only read-only contradiction-detection MVP. Phase 37E
implements backend-only deterministic context packet generation, and Phase 37F
exposes it through one read-only, stateless endpoint
(`POST /api/active-memory/context-packet`). Phase 37G adds a frontend-only,
read-only inspector over that endpoint for records explicitly supplied by the
user. Phase 37H is **documentation-only**: it plans a future read-only
Repository Observer evidence provider (see §17) but implements no observer,
adapter, subprocess execution, or Git invocation. Phase 37I adds the
`repo-observer.v1` backend contract/schema foundation for that planned observer
(see §18). Phase 37J adds a backend-only deterministic, read-only Git adapter
foundation over those contracts (see §19). Phase 37K adds a backend-only
request-triggered repository observation snapshot service MVP over that adapter
(see §20). Phase 37L exposes that service through a thin read-only HTTP API
(see §21). Phase 37M adds a frontend-only read-only contextual inspector over
that endpoint (see §22), but still implements no watcher, polling loop,
persistence, ingestion, evidence resolver, AI/LLM interpretation, Git dashboard,
or autonomous mutation/action execution.
**Purpose:** a durable, contract-facing distillation of the vocabulary, record
types, state axes, evidence hierarchy, and contradiction classes for the Active
Agent Memory + Verification Layer, so later phases can cite a stable reference
without re-deriving concepts. The full rationale, problem framing, trust model,
lifecycle rules, security analysis, and phase sequence live in the
[Phase 37A planning doc](planning/phase-37a-active-agent-memory-verification-layer-planning.md).

> This layer remembers *what is currently true, why we believe it, and when to
> stop believing it* — as evidence-backed, supersedable records, computed into a
> read-only pre-action baseline, with humans keeping authority over decisions and
> mutation. It is **not** chat history, notes, logs, or semantic search.

---

## 1. Two state axes (keep separate)

- **Verification state** — *how strongly a claim is believed given evidence*:
  `unverified` · `partially_verified` · `verified` · `human_confirmed` ·
  `contradicted` · `superseded` · `retracted` · `stale` · `unresolvable`.
- **Lifecycle state** — *where the record sits in its life*: created → validated →
  (evidence attached) → verified → active / inactive (superseded · retracted ·
  stale · contradicted-out) → archived.

Records are **immutable**; change is expressed by **appending** new records and
new state/verification events, plus **supersession/retraction links**. History is
preserved, never overwritten.

## 2. Core distinctions

| Distinction | Short rule |
|---|---|
| Fact vs decision | Fact = verifiable "is" (repo evidence rules). Decision = chosen "ought" (human authority rules). |
| Claim vs verified fact | Storing a claim ≠ endorsing it; verified = evidence checked and sufficient. |
| Superseded vs contradicted | Superseded = orderly replacement (winner known). Contradicted = incompatible, unresolved (needs attention). |
| Stale vs false | Stale = was true, evidence aged out. False = asserted untrue (retract/contradict). |
| Confidence vs verification | Confidence = strength of support. Verification = standing/state. Separate axes. |
| Repo evidence vs human intent | Repo evidence decides facts; human intent decides decisions. Neither resolves the other's category. |
| Active vs original state | Original standing = immutable history. Active = computed, current, changeable. |

## 3. Record types (conceptual)

`ProjectFact` · `ProjectDecision` · `ProjectConstraint` · `PhaseStatusRecord` ·
`RepositoryStateRecord` · `CapabilityRecord` · `EvidenceRecord` ·
`ContradictionRecord` · `VerificationRecord` · `ContextPacket` (derived view).

Common spine: stable **identity** (subject + predicate + scope), a **claim**,
**evidence references**, **verification state** + **lifecycle state** (separate),
**source authority + observer**, **timestamps** (observed-at / recorded-at /
evidence-as-of), optional **supersession/retraction links**, append-only state
history. Perishability is carried by type: decisions/constraints are durable
(retired only by humans); repository-state and many facts are perishable (expire
by freshness). Full per-type fields in the planning doc §4.

## 4. Trust model (domain-aware)

Authority depends on **claim category**, not a global ranking:

- **Repository-state claims** → machine/VCS/CI evidence outranks unsupported prose.
- **Product-intent claims** → explicit human decisions are authoritative; committed
  docs are durable *supporting* evidence, not the authority.
- **Implementation-behavior claims** → code + tests + runtime + committed docs
  weighed together, **scoped** to what each demonstrates.

Trust is a policy over *absent/partial* evidence. Where in-scope evidence exists,
evidence governs. Deterministic and inspectable for the MVP — never LLM judgment.

## 5. Evidence hierarchy (claim-relative, strongest first)

1. Human confirmation (for intent) · 2. Repository command output / VCS queries ·
3. Test / CI output · 4. Runtime API responses · 5. Source-code references ·
6. Source-controlled docs · 7. Structured CLI / agent reports (only as strong as
the evidence they carry) · 8. Screenshots · 9. Video · 10. Conversational
summaries · 11. Inferred/reconstructed context.

**Scope discipline:** a screenshot proves visible UI state, not merge status; a
clean `git status` proves tree state at a moment, not runtime behavior; a commit
hash proves a commit exists, not that it is on `main`; a passing test proves the
tested cases, not "feel." Evidence carries: strength, scope, freshness, source,
timestamp, references, invalidation, aggregation.

## 6. Contradiction classes

**Implemented in Phase 37D:** duplicate phase status · pending vs merged ·
current vs superseded decision · clean vs dirty working-tree reports.

**Contracted but deferred:** frontend-only vs backend modifications. This needs a
deterministic path/scope target model before it can be implemented without
speculative inference.

**Later (named, not MVP):** test-passed vs failing CI · capability vs missing code
· dependency-unchanged vs lockfile change · no-persistence vs migration ·
read-only vs mutation · endpoint-unchanged vs contract change · security vs unsafe
impl · evidence-scope mismatch · temporal conflict · identity collision ·
incompatible human decisions.

**Not a contradiction:** orderly temporal replacement · missing evidence (→
unverified) · scope mismatch · ambiguity (→ unresolved) · duplicates (→ dedup) ·
mere staleness · policy violation (→ validation/security). MVP rules are
conservative: prefer "unresolved / needs attention" over a false positive.

## 7. Active-state calculation

Deterministic and pure (same records in → same active set out). Per subject/scope
slot: match identity/scope → exclude superseded/retracted → require
`verified`/`human_confirmed`/scoped `partially_verified` → exclude
stale/contradicted/unresolvable → if unresolved contradiction, return "unresolved"
(do **not** pick a winner) → only then prefer most-recent among still-eligible.
**Never "newest wins."** When nothing is safely active, return an explicit
"no active record / unresolved" and expose the uncertainty.

## 8. Pre-action context packet

A **read-only**, bounded, deterministic bundle read *before* acting: project
identity · repository baseline (freshest, timestamped) · active roadmap position /
phase · verified completed phases · active decisions · active constraints · known
capabilities (and explicit gaps) · unresolved contradictions · stale/superseded
warnings · evidence references · verification summary · prohibited assumptions ·
generation timestamp. Only active records enter the baseline; contradictions and
uncertainty get their own sections; generating a packet never mutates anything.
An agent should honor constraints and **stop and ask a human** on unresolved
contradictions or missing baseline — never paper over uncertainty.

## 9. Boundaries

**Owns:** memory records, evidence references, verification/lifecycle state,
supersession/retraction links, contradiction-detection results, active-state
calculation, read-only context-packet generation.

**Must not become:** a graph database · a replacement for source documents · a
hidden chat-history store · an autonomous project manager · an unrestricted agent
scratchpad · a mutation engine · a vector-search dump · a repository watcher · an
"AI truth oracle." Must not mutate the Knowledge Graph. Human governance for
consequential state; **no command execution from records**; **no auto-trust of
prose**; reject/redact secrets; **no autonomous repository mutation**.

## 10. Phase sequence

`37A` Planning → `37B` Contract types / schema alignment (implemented) → `37C`
Deterministic memory store MVP (implemented) → `37D` Contradiction detection MVP
(implemented, validated, merged) → `37E` Pre-action context packet (implemented)
→ `37F` Read-Only Context Packet API Foundation (implemented) → `37G` Active
Memory Frontend Inspector (implemented) → `37H` Repository Observer planning
(documentation only; see §17) → `37I` Repository Observer contract types
(implemented; see §18) → `37J` Deterministic Git Adapter Foundation
(implemented; see §19) → `37K` Repository Observation Snapshot Service MVP
(implemented; see §20) → `37L` Read-Only Repository Observation API Foundation
(implemented; see §21) → `37M` Read-Only Repository Observer Frontend Inspector
MVP (implemented; see §22). This is a **Track 2 —
Agent Intelligence Infrastructure** effort, parallel to and independent of
**Track 1 — Spatial Interaction** (whose active implementation phase, **36K**,
is **paused — not completed**).

---

## 11. Phase 37B — settled contract decisions

Phase 37B converts the Phase 37A concept into stable **wire contracts** — backend
Pydantic models in `apps/backend/app/models/active_memory.py` and mirrored
frontend TypeScript in `apps/frontend/src/types/api.ts`. **Contract only:** no
persistence, store, service, router, endpoint, ingestion, contradiction
detection, active-state calculation, context-packet generation, or AI/LLM logic
was added; nothing can store or verify memories after this phase. Enums are
`StrEnum` with `UPPER_SNAKE` members whose `snake_case` value is the wire
contract; the frontend unions mirror those literals exactly, checked by a
parity test (`test_active_memory_contracts.py`).

### 11.1 Final enum wire values

- **Record kind** (`MemoryRecordKind`): `project_fact` · `project_decision` ·
  `project_constraint` · `phase_status` · `repository_state` · `capability`.
- **Verification state** (`VerificationState`, belief axis): `unverified` ·
  `partially_verified` · `verified` · `human_confirmed` · `contradicted` ·
  `unresolvable`.
- **Lifecycle state** (`LifecycleState`, in-force axis): `active` · `inactive` ·
  `superseded` · `retracted` · `stale` · `archived`.
- **Confidence** (`ConfidenceBand`): `low` · `medium` · `high` (optional).
- **Claim value kind** (`ClaimValueKind`): `string` · `boolean` · `integer` ·
  `float` · `timestamp` · `identifier` · `enum`.
- **Scope type** (`MemoryScopeType`): `project` · `repository` · `branch` ·
  `phase` · `feature` · `component` · `session`.
- **Source type** (`MemorySourceType`): `human` · `claude_code` · `codex` ·
  `chatgpt` · `cli_report` · `repository_observer` · `ci_system` ·
  `imported_document` · `unknown`.
- **Evidence type** (`EvidenceType`): `human_confirmation` ·
  `repository_command_output` · `commit` · `branch` · `pull_request` ·
  `test_output` · `ci_output` · `runtime_api_response` · `source_code` ·
  `source_controlled_doc` · `structured_cli_report` · `structured_agent_report` ·
  `screenshot` · `video` · `conversational_summary` · `inferred_context`.
- **Evidence reference kind** (`EvidenceReferenceKind`): `commit_hash` ·
  `branch_name` · `pull_request_number` · `file_path` · `symbol_reference` ·
  `command_id` · `test_run_id` · `source_record_id` · `artifact_id` ·
  `external_source_id`.
- **Supersession kind** (`SupersessionKind`): `supersedes` · `superseded_by` ·
  `retracts` · `retracted_by` (only the first and third are *stored*; the `_by`
  values are derived inverses).
- **Contradiction class** (`ContradictionClass`, the five contracted classes;
  four are implemented by the Phase 37D MVP):
  `duplicate_phase_status` · `pending_vs_merged` ·
  `frontend_only_vs_backend_modification` · `current_vs_superseded_decision` ·
  `clean_vs_dirty_working_tree`.
- **Contradiction resolution state** (`ContradictionResolutionState`): `open` ·
  `resolved` · `archived`. **Severity** (`ContradictionSeverity`, optional):
  `info` · `warning` · `critical`.
- **Active-state result** (`ActiveStateResult`): `active` · `inactive` ·
  `unresolved` · `no_eligible_record`.

### 11.2 Record, claim, evidence, source, contradiction, packet shapes

- **Record identity** is explicit (`record_id` + claim `subject`/`predicate` +
  `project_id` + optional narrower `scope` + `source` + `created_at`) — never
  derived from display text. No dedup logic is implemented.
- **Claim** is a structured `subject` / `predicate` / bounded scalar `value`
  (tagged by `value_kind`) plus an optional human `summary` — not prose-only.
- **Evidence reference** is a bounded pointer: `reference_kind` + `value` +
  optional `detail` (e.g. a line range). No raw-command / arbitrary-path kind
  exists; a reference is never executable content or a secret payload.
- **Evidence record** carries `evidence_type`, the bounded `reference`, optional
  `scope`/`source`, `captured_at`, an optional `valid_until` freshness window, and
  a free-form `metadata` bag (where future strength/authority signals ride).
- **Source identity** (`MemorySource`) is `source_type` + `source_id` + optional
  `display_label` + optional `session_id`, and carries **no trust flag**.
- **Supersession/retraction** are forward-only stored links
  (`SupersessionReference`: `supersedes`/`retracts` → `target_record_id`); the
  `_by` inverses are derived, never authored.
- **Contradiction record** carries the class, ≥2 `involved_record_ids`, summary,
  detection source + time, a resolution state that is never auto-advanced, an
  optional resolution record/source, evidence refs, and optional severity.
- **Context packet** is a read-only, bounded, kind-partitioned baseline
  (`active_facts`/`active_decisions`/`active_constraints`/`known_capabilities`,
  `unresolved_contradictions`, `warnings`, `evidence_references`,
  `verification_summary`, `prohibited_assumptions`, a timestamped
  `repository_baseline`). Only active records enter the baseline; bulky/derivable
  data is carried by reference; every collection is length-bounded.
- **Contract version** is a fixed wire literal, `active-memory.v1`
  (`ACTIVE_MEMORY_CONTRACT_VERSION`), decoupled from the package version.

### 11.3 Why these choices (rationale over alternatives)

- **Separate verification and lifecycle axes** — Phase 37A §7 warned that one
  overloaded enum makes `superseded` (a lifecycle fact) and `contradicted` (a
  belief signal) ambiguous. 37B settles it by putting `superseded`/`retracted`/
  `stale` on the lifecycle axis only; the two axes share **no** wire values, so a
  consumer can never confuse "believe it?" with "is it in force?".
- **Structured claims, not prose** — a prose paragraph cannot be compared
  deterministically, which would make 37D contradiction rules and
  subject+predicate identity keying impossible. A bounded scalar triple is
  comparable and serializable and cannot grow into an unbounded recursive blob.
- **Closed enums for wire values** — 37C/37D branch on record kind, evidence
  type, and contradiction class; an open string would let a typo create an
  uncomputable category. Closed sets also let the frontend union + parity test
  guarantee exact cross-boundary agreement.
- **Source identity separated from trust** — a recognized `source_type` never
  implies the source is trusted (Phase 37A §5). Trust is a domain-aware policy
  over *evidence*, computed later; storing a `trusted` flag on identity would
  invite the exact "confident wrong report outranks hedged correct one" failure.
- **Confidence separated from verification** — a qualitative band (not a float)
  prevents false precision and the silent evidence-averaging Phase 37A §6.3
  forbids, and keeps "strength of support" distinct from "standing".
- **Explicit, bounded evidence references** — pointers (hash / PR number / path)
  rather than payloads keep evidence inspectable and defend the §13 boundary (no
  executable content, no secret-bearing blobs, DoS-resistant bounded sizes).
- **Forward-only supersession direction** — one stored direction keeps chains
  acyclic and the chain head deterministically computable; two independently
  written link sets could disagree. The inverses are reserved in the vocabulary
  so a read view can serialize them without storing them.
- **Bounded context-packet collections** — the packet is a baseline, not a data
  dump; inlining unlimited history would defeat "read this before acting" and
  reopen the §13 DoS surface. Active records inline (bounded, kind-partitioned);
  evidence and stale/superseded history are carried by reference/warning.
- **Common record model over a discriminated union** — every record kind shares
  the same identity/claim/evidence/state spine and differs only by `kind` and
  claim vocabulary, matching the Phase 37A §4 "common conceptual spine". A single
  `MemoryRecord` keyed by `kind` avoids six near-duplicate models and lets the
  active-state calculation treat records uniformly; the discriminated union is
  used where it *does* add safety (claim `value_kind`, supersession `kind`,
  contradiction `class`).
- **Timestamp semantics kept distinct** — record `created_at` vs. claimed
  `observed_at` vs. evidence `captured_at`/`valid_until` vs. verification
  `checked_at` vs. supersession `created_at` vs. contradiction `detected_at` vs.
  packet `generated_at` are separate fields; none is silently substituted for
  another (Phase 37A §13). Values are ISO-8601; UTC/timezone-aware is recommended
  and enforcement of aware-only is deferred to avoid diverging from the repo's
  existing naive-tolerant `datetime` convention (see §11.4).
- **Scope as a closed type + bounded id** lets active state be computed per scope
  (a decision active for one phase need not be active globally); no scope
  inheritance is implemented.
- **Contract version as a fixed literal** lets a client pin `active-memory.v1`
  independent of the package version; no migration system is built.

### 11.4 Open contract questions (not silently deferred into implementation)

- **Timezone-aware timestamps.** Phase 37A §13 asks for timezone-aware contracts;
  the repo's existing models use naive-tolerant `datetime`. 37B keeps the repo
  convention (ISO-8601, tz-aware recommended) and rejects malformed timestamps
  via Pydantic parsing, but does **not** enforce aware-only. If 37C wants strict
  UTC-aware timestamps, that is a deliberate, coordinated contract tightening
  across backend and frontend — not an implementation-time assumption.
- **Evidence strength / source authority typing.** These ride in `metadata` for
  now (additive, matching the repo's `metadata.evidence` pattern). Promoting them
  to typed fields is a 37C+ decision once the trust policy is designed.
- **Verification-event history.** 37B models the *latest* verification as optional
  `VerificationMetadata`; the full append-only `VerificationRecord` event trail
  (Phase 37A §4.9) is left to the 37C store, which owns immutability/append-only.

---

## 12. Phase 37C — deterministic Active Memory store MVP

Phase 37C builds the first runtime storage layer over the 37B contracts:
`apps/backend/app/store/active_memory_store.py` (implementation) and
`apps/backend/tests/test_active_memory_store.py` (tests). It is **backend-only,
local-first, deterministic, and read-safe**. It implements the storage domain and
lifecycle behavior *only* — **no** API endpoint, ingestion, active-state
calculation, context-packet generation, or AI/LLM logic, and **no new
dependency**. Contradiction detection was implemented later by Phase 37D as a
separate read-only service over the store.

### 12.1 What the store does

A small explicit abstraction — a `MemoryStore` `Protocol` plus an
`InMemoryActiveMemoryStore` implementation — supporting: insert a `MemoryRecord`;
retrieve by id (`get` raises `RecordNotFoundError`, `find` returns `None`); list
in deterministic order; filter by a small set of contract-backed fields; transition
lifecycle state through an explicit table; and serialize / restore through a
versioned snapshot boundary.

### 12.2 Persistence mechanism selected — and why

**In-memory store + a deterministic serialize/restore boundary; no database, no
file persistence.** Phase 37A/37B fix the record *contracts* but leave the 37C
persistence *medium* open. Per the phase brief, an undecided medium defaults to a
clean in-memory store plus a serialization boundary rather than committing
permanent infrastructure (SQLite, migrations, remote storage, file watchers)
prematurely. `serialize()` emits a JSON-compatible `{contract_version, records}`
document (records contract-dumped, in stable order); `restore()`/`from_json()`
rebuild all-or-nothing with full contract validation. Callers that later want
durability own reading/writing that snapshot — the store itself never touches the
filesystem.

### 12.3 Determinism rules

- **Ordering** is explicit and total: ascending `created_at`, then `record_id` as
  a stable tiebreak. Insertion order never affects output; equal-timestamp records
  never reorder between runs.
- **Identifiers** are **caller-supplied** (`MemoryRecord.record_id` is a required
  contract field); the store generates none — no random UUIDs in core logic.
- **Timestamps** are never generated or rewritten inside storage operations;
  `created_at` rides on the record.
- **Serialization** is byte-stable for unchanged state (`to_json` uses sorted
  keys); repeated reads never mutate stored records.
- Tests inject fixed clocks/ids via contract-valid fixtures.

### 12.4 Duplicate, not-found, and immutability behavior

- **Duplicate ids** are rejected deterministically on insert
  (`DuplicateRecordError`); snapshot restore rejects duplicate ids too.
- **Not-found** is explicit: `get`/`transition_lifecycle` raise
  `RecordNotFoundError`; `find` returns `None`.
- **Immutability / defensive copies** — the store deep-copies on insert, on every
  read, and on transition, so neither a caller's retained handle nor a returned
  copy can mutate stored state (Phase 37A §9 immutable-record intent).

### 12.5 Lifecycle transitions

An explicit `LIFECYCLE_TRANSITIONS` table (Phase 37A §7.2/§9), not scattered
conditionals: `active` → any leaving state (`inactive`/`superseded`/`retracted`/
`stale`/`archived`); `inactive` ⇄ `active` or → `archived`; `stale` →
`superseded`/`retracted`/`archived`; `superseded`/`retracted` → `archived` only
(terminal-ish — reversal is a *new* record, never in-place); `archived` terminal.
A transition to the current state is an idempotent no-op. Invalid transitions
raise `InvalidLifecycleTransitionError` and leave the stored record untouched. A
transition produces a **new record snapshot** (`model_copy`) that changes only
`lifecycle_state` and carries every claim, evidence, provenance, verification, and
supersession field forward unrewritten.

### 12.6 Known limitations / deferred to later phases

- **No append-only `VerificationRecord` event trail yet.** 37C stores the record's
  head `lifecycle_state`/`verification_state` (transitions replace the stored
  snapshot in-place under immutable-copy semantics); the full append-only event
  history (Phase 37A §4.9) is deferred with the contradiction/verification phases.
- **No active-state calculation or dedup** — 37C stores and transitions records
  but never picks a winner or keys by subject+predicate identity. Phase 37D adds
  a separate read-only contradiction detector; active-state selection remains
  planned for later phases.
- **Ordering assumes consistent timestamp awareness** across records (the repo's
  naive-tolerant `datetime` convention); mixing naive and tz-aware `created_at`
  values would break comparison, matching the 37B open question on strict
  UTC-aware timestamps.
- **No durability by default** — persistence is a serialize/restore boundary; no
  medium is committed.

## 13. Phase 37D — deterministic contradiction detection MVP

Phase 37D adds a **backend-only, read-only** contradiction-detection service
(`apps/backend/app/services/active_memory_contradiction.py`) over the 37C store.
It derives contract-valid `ContradictionRecord` results from stored record fields
and **never** mutates, deletes, supersedes, resolves, or auto-picks a winner; it
adds no API endpoint, frontend surface, persistence, ingestion, observer, or
AI/LLM behavior. Records are read through the public `MemoryStore` surface (or a
plain iterable); the store is untouched.

### 13.1 Supported classes and exact deterministic rules

Records are only ever compared when their **canonical assertion target** matches:
`project_id` + narrower `scope` (type + id) + normalized `subject` + normalized
`predicate`. Scope is part of identity and is **not** inherited, so a global claim
and a phase-scoped claim about the same subject are different targets.

- **`pending_vs_merged`** (mutually-exclusive state) — same target, same
  `ClaimValueKind`, one normalized value in `{merged}` and the other in
  `{pending, unmerged, not_merged}`. Severity `critical` (can invalidate a
  baseline).
- **`clean_vs_dirty_working_tree`** (mutually-exclusive state) — same target,
  same value kind, one value `clean` and the other `dirty`. Severity `info`.
- **`duplicate_phase_status`** (incompatible value assertion) — *both* records are
  `phase_status`, same target and value kind, normalized values differ, and the
  pair matched no more-specific vocabulary above. Severity `warning`.
- **`current_vs_superseded_decision`** (structural, not value-based) — an eligible
  `project_decision` `R` is still `active`, yet another eligible record `S`
  authors a `supersedes` link at `R`. Detected from `supersession_refs` +
  `lifecycle_state` only; no value inference. Severity `warning`.

The recognized value vocabularies are small, closed, and case/whitespace-folded —
**not** a natural-language ontology; there is no synonym expansion or fuzzy
matching. A differing-value pair that matches no vocabulary and is not
`phase_status` produces **nothing** (there is no general "values differ" class).

### 13.2 Deferred class

- **`frontend_only_vs_backend_modification`** is deferred. Establishing it would
  require mapping a decision/constraint's scope onto observed file-modification
  paths — a path/domain ontology — which is exactly the speculative semantic
  inference this phase forbids. It stays deferred until a contract provides a
  deterministic shared target for it. **`temporal conflict`** and **trust/evidence
  disagreement** are likewise not implemented: `MemoryRecord` carries no
  effective-time *validity window* (only point `observed_at`/`created_at`), and no
  contract `ContradictionClass` represents a trust-disagreement conflict.

### 13.3 Eligibility, normalization, stable id, evidence, ordering

- **Eligibility.** Only `lifecycle_state == active` records participate. Records
  that left the active baseline (`inactive`/`superseded`/`retracted`/`stale`/
  `archived`) are stored history and are excluded. `verification_state` does
  **not** affect eligibility — a contradiction is structural, independent of
  belief (an `unverified` active claim can still contradict another).
- **Normalization.** Conservative and deterministic: trim + Unicode casefold for
  subject, predicate, and value comparison. `"Merged"` == `"merged"` (no false
  conflict); `"Phase 37B"` groups with `"phase 37b"`; but `"complete"` ≠
  `"completed"` (no stemming). Comparison is like-with-like: a `ClaimValueKind`
  mismatch is missing basis, not a conflict.
- **Stable id.** `contradiction-<sha1(class | canonical-target | sorted-record-ids)>`
  (repo sha1-hexdigest convention). Depends only on content, never insertion
  order, RNG, wall-clock, or dict order; reversing the input or re-running over
  unchanged records reproduces the same id, and duplicate input records (same
  `record_id`) are de-duplicated so they can never double the output.
- **Caller owns the clock.** Like the 37C store, the detector never reads the wall
  clock; `detected_at` is caller-supplied so repeated detection is reproducible.
- **Evidence.** Each result carries both supporting record ids
  (`involved_record_ids`), the unioned+sorted supporting `evidence_ids`, and a
  `metadata` `reason_code` + `assertion_target` + the conflicting canonical values
  (or supersession record ids). No narrative is fabricated.
- **Ordering.** Stable: severity (most-severe first) → contradiction class →
  canonical target → stable id. Insertion order never changes it.

## 14. Phase 37E — deterministic pre-action context packet MVP

Phase 37E adds a backend-only, read-only packet builder at
`apps/backend/app/services/active_memory_context_packet.py`, with tests in
`apps/backend/tests/test_active_memory_context_packet.py`. The public entry point
is `build_context_packet(*, store, project_id, generated_at, detector=None,
scope=None) -> ContextPacket`. The caller supplies `generated_at`; the builder
does not call the wall clock and passes the same timestamp to contradiction
detection as `detected_at`.

### 14.1 Selection and packet assembly

- Records are read through the public `MemoryStore` interface and filtered by
  exact `project_id`; an optional `MemoryScope` applies exact scope type + id
  filtering without changing the store contract.
- All `active` lifecycle records remain eligible regardless of verification
  state. Active `project_fact`, `project_decision`, `project_constraint`, and
  `capability` records are partitioned into the existing packet collections.
  Other active record kinds are not forced into unrelated sections.
- `inactive`, `superseded`, `retracted`, and `stale` records become
  contract-valid `PacketWarning` entries. `archived` records do not enter the
  active baseline.
- The builder uses the Phase 37D detector, preserves detector ordering, includes
  only `open` contradictions, keeps contradictory records in their normal
  baseline sections, and never chooses a winning claim or resolves a
  contradiction.
- Verification state for the visible baseline is represented in
  `verification_summary`; it counts only records included in `active_facts`,
  `active_decisions`, `active_constraints`, and `known_capabilities`. Records
  used only to derive `repository_baseline`, `active_phase`, or `active_track`
  are represented by those scalar fields and do not increase the summary totals.
  Active visible records are not dropped merely because they are unverified,
  partially verified, contradicted, or unresolvable.

### 14.2 Structured metadata and MVP limits

- Repository baseline, active phase, and active track are populated only from
  explicit structured metadata on active records. Human-readable claim text is
  not parsed for branch names, clean-tree state, phase names, or track names.
  Unknown repository cleanliness remains `None`.
- There is no persistent evidence-resolution store in this MVP. Record
  `evidence_ids` and contradiction `evidence_ids` are preserved, but top-level
  `evidence_references` stays empty until a real deterministic resolver exists.
- Prohibited assumptions are deterministic rigid strings derived from active
  constraints, unverified/partially verified capabilities, and unresolved
  contradictions. Stored record content is treated only as data, never as
  instructions.
- Packet collections respect `MAX_MEMORY_COLLECTION_ITEMS`. Because the existing
  `PacketWarning` model is record-lifecycle-specific rather than packet-level,
  oversized derived collections fail closed with a service error instead of being
  silently truncated or represented by a misleading warning.
- The builder does not persist packets, cache packets, execute commands, read
  arbitrary paths, authorize actions, add an endpoint, add a frontend surface,
  mutate the store, or modify the contradiction detector.

## 15. Phase 37F — read-only context packet API foundation

Phase 37F adds the first Active Memory API boundary: a thin router at
`apps/backend/app/routers/active_memory.py` exposing
**`POST /api/active-memory/context-packet`**, with the request schema in
`apps/backend/app/models/active_memory_api.py` and endpoint tests in
`apps/backend/tests/test_active_memory_context_packet_api.py`.

- **Request** (`ContextPacketRequest`): `project_id`, required caller-supplied
  `generated_at` (the endpoint never reads the wall clock), optional exact
  `scope` (`MemoryScope`), and `records` (a list of contract `MemoryRecord`
  objects). `POST` is used only because the input is a structured document; the
  operation is read-only.
- **Response:** the existing Phase 37B `ContextPacket` contract, returned
  unchanged from the Phase 37E builder — identity, ordering, evidence and
  reason metadata, verification summary, warnings, contradictions, and
  prohibited assumptions are all owned by the service layer.
- **Ownership boundary:** the router only validates transport input, converts
  the supplied records into an ephemeral request-scoped in-memory store, calls
  `build_context_packet`, and returns the result. It sorts nothing, detects
  nothing, recalculates no limits, and holds no store state between requests.
- **Errors:** malformed bodies fail through the standard FastAPI/Pydantic 422
  path. Two contract-level service errors are translated to 422 with the
  service's bounded message: a duplicate `record_id` in the supplied records,
  and the Phase 37E fail-closed collection-overflow error. Unexpected failures
  fall through to the existing generic 500 handler; no traceback, path, or
  internal object is exposed.
- **Limitations:** the endpoint is stateless — it derives packets only from
  records supplied in the request (no server-side Active Memory store is wired
  yet), it enforces no request-level cap on the `records` list (the service's
  per-collection limits remain the single owner of bounds and fail closed), and
  mixing timezone-aware and naive `created_at` values within one request is
  rejected at the API validation boundary with HTTP 422 before store ordering.

## 16. Phase 37G — active memory frontend inspector

Phase 37G adds the first frontend surface for Active Memory: a read-only
inspector panel mounted in the existing graph-primary contextual dock. It uses
the Phase 37F endpoint and changes no backend service or endpoint behavior.

- **Request editor:** a human explicitly supplies `project_id`,
  caller-editable `generated_at`, optional exact scope (`scope_type` +
  `scope_id` together), and a JSON array of `MemoryRecord` objects. The default
  record payload is `[]`; no fake Active Memory records are preloaded.
- **Validation:** the frontend safely parses JSON, requires the top-level value
  to be an array, rejects malformed JSON, and rejects partial scope input before
  submitting. Backend/Pydantic validation remains authoritative for the record
  contract and HTTP 422 details.
- **Response inspector:** the returned `ContextPacket` is rendered as structured
  sections: packet identity, repository baseline, verification summary, active
  facts, active decisions, active constraints, known capabilities, unresolved
  contradictions, packet warnings, prohibited assumptions, and packet-level
  evidence references. Missing active track/phase and unknown repository
  cleanliness stay visibly unavailable rather than being fabricated.
- **Contradictions:** unresolved contradictions are highlighted, but the
  frontend never chooses a winning record, resolves a conflict, supersedes,
  retracts, verifies, edits, or deletes records.
- **Evidence limitation:** empty packet-level `evidence_references` are explained
  as the current MVP's missing connected evidence resolver, not a frontend
  failure.
- **State boundary:** entered request data lives only in React state. The panel
  adds no `localStorage`, `sessionStorage`, IndexedDB, cookies, files, backend
  persistence, ingestion, repository observer, AI interpretation, action
  authorization, autonomous mutation, or hidden Active Memory storage.

Phase 36K remains paused and untouched. Phase 37H remains repository-observer
planning unless a later roadmap update explicitly changes that.

## 17. Phase 37H — repository observer planning (documentation only)

Phase 37H is a **documentation-only** planning phase that specifies a *future*
**Repository Observer**: a read-only backend evidence provider that would inspect
a single local Git repository without mutating it and emit a bounded,
deterministically ordered, immutable observation snapshot plus derived evidence
and candidate records for this layer's separate ingestion, contradiction, and
context-packet services. **Nothing is implemented** — no observer, Git adapter,
subprocess execution, filesystem scan, watcher, endpoint, schema, dependency, or
runtime behavior. The long-form contract lives in the
[Phase 37H planning doc](planning/phase-37h-repository-observer-planning.md).

- **Evidence provider, not a developer.** The planned observer never edits,
  commits, amends, switches/creates/deletes branches, stashes, resets, cleans,
  pushes, pulls, merges, rebases, executes hooks or project code, changes Git
  config, or mutates memory. Mutation is fail-closed.
- **Direct observation, honestly scoped.** It may observe repository identity,
  branch/HEAD/upstream, ahead/behind, clean/dirty working tree, staged/unstaged/
  untracked paths, bounded recent commits, changed paths (with renames/deletes),
  diff *statistics*, remotes, tags, and merge/rebase/cherry-pick/bisect operation
  state. Each item is classified as a direct fact, derived fact, externally
  supplied claim, unverified assumption, or unsupported gap.
- **Evidence hierarchy (repo-scoped).** Direct Git output > direct filesystem
  metadata > parsed repository documents > validated test/build output (never run
  by the observer) > user statements > agent summaries > unsupported assumptions.
  **Local Git history alone does not prove remote pull-request state, CI results,
  or remote-branch deletion** — those require verified external GitHub/execution
  evidence and are otherwise reported as unverified.
- **Integration boundary.** The observer produces evidence and candidate records
  (`repository_state`, `project_fact`, `capability`, `EvidenceRecord`, and
  contradiction *signals*) and hands a snapshot to a separate ingestion decision.
  Record normalization, deduplication, contradiction detection (Phase 37D),
  context-packet selection (Phase 37E), persistence, policy, and presentation stay
  owned by the existing services. The observer never writes the store.
- **Security posture.** Repository content is untrusted input: argument-array
  process execution (never shell interpolation), no hook or script execution,
  strict repository-root confinement, no symlink escape, bounded output/history/
  file counts, per-command and whole-observation timeouts, structured parsing,
  secret redaction, terminal-escape neutralization, structured errors, and
  fail-closed mutation behavior.
- **Determinism and overflow.** Every collection is totally ordered with stable
  tiebreaks; the snapshot is byte-reproducible for identical state and caller
  inputs (the observation timestamp is caller-supplied, matching the store and
  detector convention); bounds truncate deterministically with explicit overflow
  metadata, never silent drops.
- **MVP vs. deferred.** The MVP is a backend-only, read-only, single-repository
  snapshot (identity, branch, HEAD, upstream, ahead/behind, clean/dirty, staged/
  unstaged/untracked, bounded commits, remotes, operation state, warnings) with
  focused hermetic tests. GitHub API integration, PR/issue ingestion, a watcher,
  background polling, mutation, diff-content ingestion, semantic indexing, AI/LLM
  summarization, frontend visualization, and persistence are deferred.
- **Follow-on sequence (planned, not authorized here).** 37I contract types → 37J
  Git adapter → 37K snapshot service MVP → 37L observation API → 37M read-only
  frontend inspector → later evidence ingestion, contradiction integration, and
  end-to-end QA. Phase 37J is now implemented as the adapter foundation, Phase
  37K is now implemented as the snapshot service MVP, Phase 37L is now
  implemented as the read-only observation API, and Phase 37M is now implemented
  as the read-only frontend inspector; ingestion and contradiction integration
  remain planned and unauthorized here.

Phase 36K remains paused and untouched.

## 18. Phase 37I — repository observer contract types / schema alignment

Phase 37I adds the backend-only `repo-observer.v1` contract foundation in
`apps/backend/app/models/repository_observer.py`, with focused model tests in
`apps/backend/tests/test_repository_observer_models.py`. These contracts define
read-only, bounded, JSON-safe shapes for repository identity, observer scope,
working-tree state, changed-file summaries, rename/copy relationships,
repository evidence, evidence authority, warnings, limitations, overflow and
truncation metadata, and snapshot completeness.

The contracts are a schema floor only. They do not resolve paths, inspect Git
metadata, walk the filesystem, scan file contents, derive snapshots, create
candidate memory records, ingest evidence, persist data, expose an API, or change
context-packet and contradiction behavior. Timestamps remain caller-supplied;
validators reject malformed contract data such as negative limits, unsafe
repository-relative paths, malformed rename/copy records, unbounded excerpts,
impossible overflow counts, and complete snapshots that claim truncation.

Security and bounded-observation rules from Phase 37H remain preserved: file
contents are absent by default, excerpts are optional and explicitly bounded,
absolute and parent-traversing repository-relative paths are rejected, warnings
and limitations are structured for future API exposure, and local secrets,
stack traces, arbitrary exception strings, environment variables, and unrestricted
absolute filesystem paths are not modeled as automatic payloads.

Phase 37J now owns read-only argument-array Git adapter behavior; Phase 37I did
not authorize or implement it.

## 19. Phase 37J — deterministic Git adapter foundation

Phase 37J adds a backend-only deterministic Git adapter foundation in
`apps/backend/app/services/repository_git_adapter.py`, with focused tests in
`apps/backend/tests/test_repository_git_adapter.py`. The adapter is read-only and
translates bounded Git CLI evidence into the existing Phase 37I
`repo-observer.v1` models; it does not create a competing contract.

### 19.1 Implemented command boundary

The application command set is intentionally small and internal:

- `git rev-parse --show-toplevel`
- `git status --porcelain=v2 -z --branch --untracked-files=all`
- `git remote -v`

Commands are executed with argument arrays and `shell=False`, an explicit
repository `cwd`, a 5 second per-command timeout, 262,144 stdout bytes, 8,192
stderr bytes, and bounded excerpts of 512 characters. Mutating Git subcommands
such as add, commit, checkout, switch, reset, clean, stash, fetch, pull, push,
update-index, config, merge, rebase, cherry-pick, restore, rm, and mv are
excluded from the application command set. Phase implementation still used Git
normally for branch and commit workflow outside the adapter.

### 19.2 Parsing and conversion

Porcelain-v2 status output was selected because it is stable, machine-readable,
and avoids human-readable `git status` parsing. The parser handles branch
headers, detached HEAD, unborn initial branches, missing upstream metadata,
ordinary tracked records, staged and unstaged changes, untracked paths, unmerged
records, renames, copies, paths containing spaces, and NUL-delimited records.
Malformed records, undecodable paths, unsafe absolute paths, drive paths, parent
traversal, and unexpected record types fail with typed bounded adapter errors
rather than raw tracebacks.

Conversion preserves repository-relative paths, rename/copy prior/current
relationships, direct-Git evidence authority, metadata-only limitations,
deterministic ordering by normalized path, working-tree clean/dirty counts,
detached/unborn branch behavior, warning records, overflow metadata, and honest
snapshot completeness. File observations default to 200 retained records; when
that limit is exceeded, the first records by deterministic path order are kept,
omitted paths are recorded, `FILE_COUNT` overflow is populated, and completeness
is `partial`.

### 19.3 Boundaries and limitations

Phase 37J does not add an API route, request model, database schema, persistence,
background task, polling loop, filesystem crawler, source-file reader, watcher,
Active Memory ingestion, contradiction integration, GitHub API integration,
frontend surface, new dependency, AI/LLM behavior, automatic remediation, or
repository mutation. Phase 36K remains paused and untouched.

## 20. Phase 37K — repository observation snapshot service MVP

Phase 37K adds a backend-only snapshot service in
`apps/backend/app/services/repository_observation_snapshot.py`, with focused
tests in `apps/backend/tests/test_repository_observation_snapshot.py`. The
service is the request-triggered observation boundary for the Repository
Observer MVP. It uses the Phase 37J adapter for allowlisted Git command
execution, porcelain-v2 parsing, remote parsing, and deterministic low-level
conversion helpers, then returns the existing Phase 37I `RepositorySnapshot`
contract.

The architecture overlap from Phase 37J is reconciled deliberately: adapter
parsing and `convert_git_evidence_to_snapshot(...)` remain the single low-level
conversion path, while the Phase 37K service owns orchestration. The adapter's
older `observe_repository(...)` entry point is retained only as a compatibility
wrapper that delegates to the service.

The service preserves caller-supplied `observed_at`, maps conservative
`ObserverScope` limits into adapter limits, rejects deferred scope features
(`included_paths`, `excluded_paths`, file contents, ignored-file observation, and
binary-file observation), verifies a supplied scope root against the resolved Git
root, and preserves the fail-closed root evidence behavior from Phase 37J.

Phase 37K does not add an API route, request model, database schema, persistence,
background task, polling loop, filesystem crawler, source-file reader, watcher,
Active Memory ingestion, contradiction integration, GitHub API integration,
frontend surface, new dependency, AI/LLM behavior, automatic remediation, or
repository mutation. Phase 36K remains paused and untouched.

## 21. Phase 37L — read-only repository observation API foundation

Phase 37L adds a backend-only read-only HTTP boundary in
`apps/backend/app/routers/repository_observer.py`, with request schema in
`apps/backend/app/models/repository_observer_api.py` and focused API tests in
`apps/backend/tests/test_repository_observer_api.py`.

The endpoint is **`POST /api/repository-observer/snapshot`**. `POST` is used
because the request is structured; the operation itself remains read-only. The
request requires a local absolute `repository_root` and caller-supplied
`observed_at`, supports bounded `max_file_count` and `max_snapshot_bytes`, and
may carry the existing Phase 37I `ObserverScope`. Empty roots, malformed paths,
relative paths, parent traversal, negative bounds, oversized bounds, unsupported
scope behavior, and unexpected request fields are rejected at the transport or
service boundary.

The response is the existing Phase 37I `RepositorySnapshot` contract, not a
flattened presentation model. Repository identity, identity status,
working-tree state, changed-file observations, rename/copy relationships,
repository evidence, evidence authority, warnings, limitations, overflow,
truncation, omitted paths, completeness, and `read_only` semantics remain intact.

The dependency flow is intentionally narrow:

```text
API router
  -> repository observation snapshot service
  -> deterministic Git adapter
  -> read-only Git subprocess calls
```

The router owns client-safe error mapping only. Repository-not-found and
non-directory paths return stable client errors; non-Git directories, access
denial, expected bounded adapter/service failures, unavailable Git capability,
and unexpected failures are reported without exposing tracebacks, credentials,
raw subprocess commands, environment values, or sensitive filesystem internals.

Phase 37L does not add repository mutation, arbitrary command execution, fetch,
pull, checkout, branch management, commits, persistence, historical snapshot
storage, diffing across time, watcher/polling behavior, Active Memory ingestion,
contradiction integration, frontend UI, graph changes, Obsidian changes,
MediaPipe work, AI/LLM behavior, or new package dependencies. Phase 36K remains
paused and untouched.

## 22. Phase 37M — read-only repository observer frontend inspector MVP

Phase 37M adds a frontend-only read-only inspector mounted in the existing
graph-primary contextual dock. It uses the Phase 37L endpoint,
**`POST /api/repository-observer/snapshot`**, and changes no backend service,
Git adapter, endpoint, or snapshot contract behavior.

- **API integration:** `apps/frontend/src/api/client.ts` adds a narrow
  `observeRepositorySnapshot` client method. `apps/frontend/src/types/api.ts`
  mirrors the existing `repo-observer.v1` backend snapshot and request wire
  shapes so the UI consumes the backend-owned contract instead of inventing a
  flattened presentation model.
- **Request controls:** the panel exposes only the contract-valid MVP fields:
  absolute repository root, caller-supplied observation timestamp, file limit,
  and snapshot byte limit. Numeric bounds match the Phase 37L request limits.
  Optional `ObserverScope` remains deferred because this MVP does not expose its
  path and content toggles.
- **Response inspector:** the returned `RepositorySnapshot` is rendered as
  structured sections for snapshot status, repository identity, branch/HEAD,
  working-tree state, changed files, rename/copy relationships, evidence and
  evidence authority, warnings, limitations, overflow/truncation, omitted paths,
  deterministic ordering, completeness, and `read_only`.
- **State and errors:** idle, loading, successful clean/dirty snapshots, empty
  file observations, partial/truncated snapshots, identity uncertainty, contract
  validation failures, invalid/not-found roots, backend unavailability, and
  unexpected server errors have readable states. Raw stack traces and unfiltered
  server bodies are not displayed.
- **Boundary:** request data lives only in React state. The inspector adds no
  `localStorage`, `sessionStorage`, IndexedDB, cookies, file persistence,
  watcher, polling loop, WebSocket, Server-Sent Event, Git mutation, Active
  Memory ingestion, contradiction integration, AI review, source registry
  mutation, graph mutation, or dashboard replacement.

The inspector is contextual because Repository Observer evidence is supporting
visibility for the graph-first workspace. It is intentionally not an IDE, file
explorer, source-control client, or repository repair surface.
