# Active Agent Memory + Verification Layer — Reusable Reference

**Status:** Architecture reference with partial implementation through Phase 37E.
Phase 37B implements the `active-memory.v1` backend/frontend contracts, Phase 37C
implements a deterministic backend-only in-memory store, and Phase 37D implements
a deterministic backend-only read-only contradiction-detection MVP. Phase 37E
implements backend-only deterministic context packet generation. No endpoint,
committed persistence medium, ingestion workflow, active-state calculation,
inspector, repository observer, evidence-resolution store, AI/LLM interpretation,
or autonomous mutation/action execution has been built.
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
→ `37F` Read-Only Context Packet API Foundation (next planned) → `37G` Active
Memory Frontend Inspector → `37H` Repository observer planning. This is a **Track 2 —
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
