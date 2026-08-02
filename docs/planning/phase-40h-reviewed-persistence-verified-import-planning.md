# Phase 40H — Reviewed Persistence + Verified Import (Planning)

**Status:** Planning-only. No runtime implementation exists. This document defines
the foundation; nothing here is built. It is **proposed and pending a further
independent audit** (another Codex re-audit); implementation stays locked until this
planning branch passes that audit and is merged.
**Track:** Grounded Synthesis + Memory Migration (Phase 40D.5–40L sequence).
**Baseline:** `origin/main` at merge commit
`d1b2c3eea662ccb8876de9761650e31c0e44f4b9`.
**Branch:** `phase-40h-reviewed-persistence-verified-import-planning`.
**Depends on (merged / locally implemented, unchanged):**
[Phase 40E](phase-40e-memory-migration-contract-intake-safety-foundation.md) (intake,
merged), [Phase 40F](phase-40f-export-parser-candidate-projection.md) (parser +
projector), [Phase 40G](phase-40g-migration-candidate-assessment-dry-run.md)
(candidate-set dry-run assessment), and the existing Phase 37B/37C **Active Memory
contract + store** ([`app/models/active_memory.py`](../../apps/backend/app/models/active_memory.py),
[`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py)),
which Phase 40H integrates with and does **not** redefine.

Phase 40H is the first phase in the memory-migration track permitted to **create an
Active Memory record from a migration candidate** — and only for a candidate a human
has explicitly reviewed and approved, and only **through the existing Active Memory
ownership boundary**. Everything before it is read-only: Phase 40E judges
declarations, Phase 40F reads bytes and projects inactive candidates, Phase 40G
assesses the candidate set. None of them writes anything durable. Phase 40H adds the
durable, human-gated bridge from an assessed candidate to an Active Memory record,
and it does so without ever inferring approval from parsing success, assessment
cleanliness, or an approval boolean standing alone.

This is a **planning document**. It defines the ownership model, the durable
migration-workflow record types, the review-provenance requirements, the persistence
lifecycle, the verified-import contract, the authorized Active-Memory-insertion seam,
the mandatory durable **Active Memory snapshot store**, the shared persisted
**commit generation** that binds the two durable artifacts, the single **import
coordinator** and its one concrete exclusive lock-file protocol, the ordered
intent/effect/receipt protocol, the **post-insert rollback and quarantine** rules,
the idempotency/replay contract with a monotonic attempt sequence, the
**candidate-to-`MemoryRecord` provenance mapping**, the **canonical identity
derivation** for every derived id, uncertain-commit recovery, the typed diagnostics,
the test matrix, the integration map, the API decision, and the deferred work. It
implements none of them.

---

## 0. The one thing this phase exists to prevent

> An approval boolean by itself is not valid provenance.

A field reading `approved = true` records that *someone set a flag*. It does not
record **who** decided, **when**, **against which exact candidate bytes**, against
**which assessment**, on **what evidence**, or **why**. Phase 40H treats a bare
approval flag as meaningless. Mutation authority flows only from a complete,
immutable **review-decision record** bound to a specific candidate digest and a
specific assessment identity/version, re-validated at import time. If any part of
that binding is missing, stale, or contradictory, import **fails closed** and
Active Memory is not touched.

Three things are kept structurally distinct and are never conflated:

1. **Verified candidate bytes** — the bytes are the bytes the user declared
   (Phase 40F already proves this via recomputed digest; Phase 40H re-proves it at
   import time). This says nothing about whether the content is true.
2. **Reviewed claims and assessment** — a human looked at the assessed candidate
   set and its dry-run report and recorded an explicit, attributable decision.
   This is a statement about a *decision*, not about truth.
3. **Verified import into Active Memory** — a candidate a human approved was
   durably imported into the existing Active Memory store exactly once, under a
   deterministic receipt that links the candidate, its digest, its assessment, the
   review decision, the import attempt, the shared commit generation, and the exact
   resulting `MemoryRecord.record_id`.

"Verified import" proves the pipeline was honored end-to-end and byte-consistent.
It does **not** prove the imported statement is factually true — the resulting
Active Memory record is imported evidence, never adjudicated truth (see §E.1).

---

## A. State-ownership contract

Phase 40H spans **two durable stores plus one authoritative in-memory store**, with
distinct owners, and the plan is explicit about which owns what. Conflating them is
the specific failure this section exists to prevent.

### A.1 The Active Memory store remains authoritative for Active Memory records

The existing Phase 37C store — the `MemoryStore` protocol and its
`InMemoryActiveMemoryStore` implementation in
[`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py)
— **remains the sole authority for `MemoryRecord` state.** Phase 40H does **not**
introduce a competing Active Memory store, and it does **not** copy, wrap, shadow, or
re-home authoritative `MemoryRecord` data inside the migration ledger. The Active
Memory store keeps its own identity rule (caller-supplied `record_id`), its own
immutability guarantee, its own lifecycle transition table, and its own
serialize/restore boundary. Phase 40H reads and writes Active Memory **only** through
that store's existing public seam (§F.2). The **durable Active Memory snapshot**
(§A.4) is the authoritative durable representation of that store's records; the
migration ledger never holds record content.

### A.2 The import coordinator is an orchestration boundary

A single new backend service, the **Reviewed Migration Import Service** (working
name `MemoryMigrationImportService`), is the **one import coordinator**. It is
**not** an Active Memory store. It is an **orchestration boundary** that owns the
exclusive writer lock (§I.4) and coordinates three stores — the durable migration
ledger, the durable Active Memory snapshot, and the authoritative in-memory Active
Memory store — to perform one reviewed import:

- it records review decisions, import attempts, and receipts in the durable
  migration ledger (§A.3);
- it constructs the authorized `MemoryRecord` and inserts it into the **existing
  Active Memory store** through that store's own boundary (§F.2), then persists the
  durable Active Memory snapshot (§A.4);
- it answers idempotent replay lookups and drives uncertain-commit recovery (§I.7).

It owns the *workflow and the orchestration*, never the Active Memory records
themselves. No router, parser, projector, assessor, or frontend may write
migration-import workflow state; they call this coordinator or they read nothing.

### A.3 MigrationImportStore owns durable migration-workflow records only

Durable migration-workflow state lives behind a **persistence adapter** (working
name `MigrationImportStore`) that is the only component performing filesystem I/O for
the *ledger*. **It owns exactly four kinds of durable record and nothing else:**

1. **review decisions** (who approved/rejected/deferred which exact reviewed input);
2. **import attempts** (each retry a distinct attempt, §G);
3. **import receipts** (the deterministic link set, referencing — never copying —
   the resulting `MemoryRecord.record_id`);
4. **idempotency and recovery metadata** (the stable idempotency key → outcome map,
   the persisted ledger revision, the shared `commit_generation`, and per-attempt
   intent/commit markers used by recovery, §I).

It stores **references** to Active Memory records (a `record_id` plus the version
semantics described in §B), never a duplicate of the record's content. The
coordinator depends on the adapter's typed interface, never on `open`, `json`, or
`os.replace` directly. This mirrors the Phase 40F parser/projector split (all I/O
behind one seam) and the Phase 37 store/service split.

**The established local persistence architecture is reused, not replaced.** The
authoritative pattern is the Phase 39B
[`RepositoryWorkspaceConfigService`](../../apps/backend/app/services/repository_workspace_config.py):

- a **versioned JSON contract** (`schema_version`, `extra="forbid"` models);
- an **OS-appropriate path outside the repository** (Windows `%LOCALAPPDATA%`,
  otherwise XDG), with a `HIVEMIND_MIGRATION_IMPORT_PATH` environment override of
  highest precedence, resolved without side effects (Phase 39B's
  `resolve_workspace_config_path`);
- **atomic, corruption-resistant writes** (temp sibling + `fsync` + `os.replace`),
  so a failed write never destroys the prior valid file;
- **bounded loads** with typed failure states for not-found, malformed,
  unsupported-version, too-large, and inaccessible;
- **fail-closed reads** — a malformed or unreadable ledger raises a typed error and
  never silently discards or overwrites.

Phase 40H's ledger is an **append-oriented import ledger** rather than a mutable
registry (see §D.6), so the store adds two capabilities the Phase 39B config service
does not need, both additive reuses of the established pattern rather than a new
persistence technology: a **persisted monotonic ledger revision with compare-and-swap**
(§I.5) and the shared **commit generation** (§I.3). Atomic file replacement alone is
explicitly **insufficient** for this feature's concurrency and cross-store
guarantees (§I.4–§I.6) and is not relied on as if it were.

> **No speculative PostgreSQL rewrite.** A relational database is explicitly *not*
> proposed. Hive|Mind is local-first and single-user (roadmap "Current
> Limitations"); the Active Memory store itself is still
> in-memory-with-serialize/restore. Introducing a server database here would be a
> large, unaudited dependency far beyond the smallest reviewed-import foundation. The
> local versioned-JSON ledger plus the versioned-JSON Active Memory snapshot are
> sufficient for a single operator's own migration history; if future evidence ever
> shows them insufficient, that is a separate, justified decision — not part of this
> phase.

### A.4 ActiveMemorySnapshotStore owns the durable Active Memory snapshot (mandatory)

The Active Memory store is in-memory; its durability is caller-owned via
`serialize()`/`restore()` (Phase 37C), and **no durable snapshot owner exists
today**. Phase 40H makes a concrete **`ActiveMemorySnapshotStore`** a **mandatory**
component of this phase — not a conditional "if none exists" fallback. It is the
authoritative durable representation of `MemoryRecord` state and the second durable
artifact the commit generation binds (§I.3).

- **Proposed module:** `apps/backend/app/services/active_memory_snapshot_store.py`
  (§L).
- **Responsibility:** durable **serialization, loading, validation, and atomic
  replacement** of the authoritative Active Memory snapshot. It wraps the existing
  `InMemoryActiveMemoryStore.serialize()` / `restore()` boundary; it does **not**
  rewrite the store and does **not** re-home records into the ledger.
- **Interface (typed, minimal):**
  - `load() -> LoadedActiveMemorySnapshot` — returns the restored
    `InMemoryActiveMemoryStore` plus the snapshot's recorded `commit_generation`, or
    a typed failure;
  - `persist(store, commit_generation) -> None` — serialize the store, stamp the
    snapshot document with `commit_generation`, write atomically (temp sibling +
    `fsync` + `os.replace`);
  - `exists() -> bool`, `path() -> Path` (side-effect-free resolution).
- **Snapshot document:** the existing 37C snapshot payload
  (`contract_version = "active-memory.v1"`, `records: [...]`) wrapped with an outer
  envelope adding `schema_version = "active-memory-snapshot.v1"` and the shared
  `commit_generation`. Record content is exactly the store's own `serialize()`
  output — never reshaped, never augmented per-record by the ledger.
- **Configuration path:** OS-appropriate path outside the repository (Windows
  `%LOCALAPPDATA%`, otherwise XDG), resolved side-effect-free by the shared resolver,
  with a `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` **environment override of highest
  precedence** (parallel to `HIVEMIND_MIGRATION_IMPORT_PATH`).
- **Startup behavior:** at startup, **under the coordinator lock** (§I.4), the
  coordinator loads *both* the ledger and the snapshot and validates the shared
  generation (§I.3). A cold start with neither artifact present initializes both at
  `commit_generation = 0`.
- **Integrity checks:** structural validation and full contract re-validation of
  every record via the store's existing `restore()` (all-or-nothing); the outer
  envelope's `schema_version` and `commit_generation` must be present and typed; the
  snapshot's recorded generation must equal the ledger's (§I.3).
- **Typed failures:** `snapshot_missing`, `corrupt_active_memory_snapshot`,
  `generation_mismatch`, `persistence_failure`, `partial_write_detected` (§J).

Ownership boundary restated: **the Active Memory snapshot remains authoritative for
`MemoryRecord` data; the migration ledger remains authoritative for review decisions,
attempts, intents, receipts, idempotency, and recovery metadata.** Neither duplicates
the other.

### A.5 Router thinness and non-mutating layers

- **Routers stay thin.** Phase 40H proposes **no** router by default (see §M). If a
  future, separately-approved phase adds one, it does only transport: validate a
  request contract, call the coordinator, map typed results to safe responses. It
  holds no persistence, digest, or lifecycle logic.
- **Only the import coordinator creates an Active Memory record from a migration
  candidate**, and it does so exclusively through the Active Memory store's own
  insertion seam (§F.2). That is the single migration→Active-Memory mutation
  boundary (§F).
- **Parsing (40F), projection (40F), assessment (40G), dry-run, and inspection stay
  non-mutating.** They are pure/read-only today and Phase 40H changes none of them.
  Phase 40H depends on their outputs and never edits their modules.

---

## B. Durable record types and relationships

All migration-workflow records are versioned (`memory-migration-import.v1`),
`extra="forbid"`, and use the repository's canonical-JSON + SHA-256 identity
convention (§H). Identifiers are pure functions of typed content; nothing reads a
clock, randomness, or process state to form an identity. Caller-supplied timestamps
follow the Phase 37E/40F convention (the service records time it is given; it does
not read the wall clock to fabricate provenance).

**Ownership note (critical):** the first three rows describe *references into stores
Phase 40H does not own* (Phase 40F candidate, Phase 40G report, Phase 37C Active
Memory store). The migration ledger stores only their **identities**, never copies.
The **resulting Active Memory record is owned entirely by the Active Memory store**
(durably, by the §A.4 snapshot); the ledger holds only its `record_id` and
version-linkage metadata.

| Record | Identity | Key fields | Mutability / ownership |
| --- | --- | --- | --- |
| **Migration candidate reference** | `candidate_id` (Phase 40F, reused unchanged) | `candidate_id`, `content_digest`, `provenance` (bundle/artifact fingerprints, observed digest), assessed-set membership | Immutable; a *reference*, not a copy of candidate bytes; owned by Phase 40F output |
| **Candidate byte digest** | value of `content_digest` | the Phase 40F SHA-256 over candidate content; the observed artifact digest from `MigrationCandidateProvenance` | Immutable reference value |
| **Assessment reference** | `report_id` (Phase 40G) + `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION` | `report_id`, ruleset version, `review_readiness` verdict | Immutable; owned by Phase 40G output |
| **Review decision** | `review_decision_id` = canonical id over its own fields (§H) | reviewer id, decision timestamp, status, reason, notes, candidate id + digest, assessment id + version, evidence references, optional `supersedes_decision_id` | Immutable once recorded (append-only; a superseding decision is a new record, §C/§D.6/§D.7); **owned by the migration ledger** |
| **Review evidence reference** | reference tuple `(kind, ref_id)` | typed pointer to the assessment report, the dry-run finding(s), and/or the candidate provenance the reviewer relied on | Immutable; owned by the migration ledger |
| **Import attempt** | `import_attempt_id` = canonical id over `(idempotency_key, attempt_sequence)` (§H) | `idempotency_key`, `attempt_sequence` (deterministic monotonic int, retries only, §G.2), referenced `review_decision_id`, candidate id + digest, assessment id + version, `intent_state` (`intended`/`committed`/`failed`/`uncertain`), planned `target_record_id`, `commit_generation` observed at intent, attempt timestamp | Append-only; each retry is a **distinct** attempt id (§G); owned by the migration ledger |
| **Verified import receipt** | `receipt_id` = canonical id over the linked identities + `commit_generation` (§H) | see §B.3 (full receipt contract) | Immutable; created only at verified commit; **owned by the migration ledger** |
| **Resulting Active Memory record** | `record_id` (caller-supplied to the Active Memory store; here the canonical id over projected content + content-identity provenance, §H) | the `MemoryRecord` itself — lifecycle/verification standing, claim, provenance, supersession refs | **Owned exclusively by the Active Memory store** (durable in the §A.4 snapshot). The ledger stores only its `record_id`; it is never copied, wrapped, or shadowed in the ledger (§A.1) |
| **Ledger revision** | monotonic integer `ledger_revision` | the persisted CAS token guarding every *ledger* write (§I.5) | Monotone, advanced only under the exclusive writer lock |
| **Commit generation** | monotonic integer `commit_generation` | the shared cross-store epoch recorded in **both** the ledger and the Active Memory snapshot (§I.3) | Monotone, advanced exactly once per verified import, only under the exclusive writer lock |

### B.1 Ownership and cardinality

- One **candidate** may be referenced by many **review decisions** over time (a
  deferred decision later superseded by an approval), but at most **one
  non-superseded approved decision** is valid for a given `(candidate_id,
  content_digest, assessment_id, assessment_version)` tuple at any time (§D.6, §D.7).
- One valid **approved review decision** authorizes at most **one verified import**
  for its exact reviewed input (its idempotency key, §G.1), producing exactly **one
  receipt** and referencing exactly **one resulting `record_id`**.
- One **import attempt** references exactly one **review decision** and yields zero
  or one **receipt** (zero on failure, one on verified commit). Multiple attempts may
  share one idempotency key (retries), but each has a distinct `import_attempt_id`.
- One **receipt** references exactly one resulting `record_id`. That `record_id` must
  resolve to an existing record in the **Active Memory snapshot**. A receipt whose
  `record_id` does not resolve is a detected corruption (`missing_linked_memory_record`,
  §J), never a valid state. This cross-store linkage is the invariant §I protects.
- **Distinct decisions over identical content+assessment:** because `record_id`
  derives over content-identity provenance only (§H.3), two *different* approved
  decisions over the *same* `content_digest` + assessment yield the *same*
  `record_id`. The first import creates the record; the second reviewed input has its
  own idempotency key and its own receipt but **references the already-existing
  `record_id`** — one record, two audited approval receipts, never a duplicate
  record (§F.3, §G.3).

### B.2 Uniqueness, foreign keys, timestamps, version semantics

- **Uniqueness constraints (enforced by the ledger, adapter-level):**
  `review_decision_id`, `import_attempt_id`, and `receipt_id` are each unique. The
  **idempotency key** (§G) maps to at most **one** committed receipt — a duplicate
  valid request resolves to the existing receipt, never a new record.
- **Foreign-key equivalents:** every import attempt names an existing
  `review_decision_id`; every receipt names an existing `import_attempt_id`,
  `review_decision_id`, and a `record_id` that exists in the Active Memory snapshot;
  every review decision names an existing `candidate_id` + `content_digest` and
  `report_id` + version, and (when renewing review) an existing
  `supersedes_decision_id`. A dangling *intra-ledger* reference fails closed as
  `missing_linked_attempt` / `incomplete_review_provenance`; a dangling *cross-store*
  reference (receipt → absent `record_id`) fails closed as
  `missing_linked_memory_record` (§J).
- **Timestamps:** `decision_timestamp`, `attempt_timestamp`, and
  `verification_timestamp` are caller-supplied and immutable once recorded. There is
  no server-clock read; determinism and auditability come from the caller stating
  time, exactly as Phase 37E/40F do. Temporal fields are **excluded** from every
  derived identity (§H).
- **Version semantics (reuse, not reinvention):** Active Memory records have no
  numeric version field. The Active Memory store's existing model *is* the version
  semantics — a stable `record_id` is one immutable version, and a *changed* import
  (new digest or new assessment) produces a **new** `record_id` that **supersedes**
  the prior one via the store's existing `supersession_refs`, never an in-place edit
  (§D.7, §F.2). The receipt records `record_id` and, when the import supersedes a
  prior import of the same logical candidate line, the prior `record_id` in
  `record_supersedes`. Phase 40H introduces **no** competing version scheme for
  Active Memory.
- **Immutable vs mutable:** every ledger record above is immutable once written. The
  *ledger* grows by appending new records and advancing `ledger_revision`; a lifecycle
  "transition" is a new controlled record referencing the prior one (§D.6), never an
  in-place edit. The only field that could be described as "changing" is a decision's
  or attempt's *effective* status, and that is expressed by a newer superseding
  record or an appended attempt state, not by mutation.

### B.3 The verified-import receipt contract

The receipt is created **only** at verified commit and carries exactly these fields:

| Field | Purpose |
| --- | --- |
| `receipt_id` | Deterministic identity over the linked identities + `commit_generation` (§H.4). **Excludes** all timestamps. |
| `candidate_id` | The exact Phase 40F candidate imported. |
| `content_digest` | The exact candidate byte digest imported. |
| `assessment_report_id` | The exact Phase 40G report reviewed. |
| `assessment_version` | The Phase 40G ruleset contract/version reviewed. |
| `review_decision_id` | The approving decision. |
| `idempotency_key` | The stable reviewed-input key (§G.1). |
| `import_attempt_id` | The committing attempt. |
| `record_id` | The authoritative resulting `MemoryRecord.record_id`. |
| `record_supersedes` | 0..1 prior `record_id` this import supersedes (same logical candidate line). |
| `supersession_refs` | The applicable forward supersession references written on the new record (mirror of what §F.2 authored), for audit. |
| `commit_generation` | The shared generation this receipt (and its snapshot) represent (§I.3). |
| `verification_status` | Closed enum: `verified` (the only status a committed receipt carries). Uncertain/failed outcomes never produce a receipt. |
| `attempt_timestamp` | Caller-supplied time the attempt was made (temporal audit; **not** in `receipt_id`). |
| `verification_timestamp` | Caller-supplied time linkage was verified (temporal audit; **not** in `receipt_id`). |
| `receipt_version` | The `memory-migration-import.v1` contract tag. |
| `receipt_digest` | Canonical SHA-256 over the receipt's identity fields (§H.4), enabling `receipt_integrity_failure` detection at load. |

**Deterministic identity is separated from temporal audit fields:** `receipt_id` and
`receipt_digest` are computed over identity fields only, so a duplicate replay
recomputes and returns the **exact stored receipt unchanged** (§G.3), while
`attempt_timestamp` / `verification_timestamp` record *when* without perturbing
identity.

---

## C. Review-decision provenance

A review decision is the load-bearing artifact of this phase. It is a strict,
dedicated contract (it does **not** reuse `MemoryRecord`, mirroring Phase 40E's
refusal to reuse permissive Active Memory records). Every field below is
**required** unless marked optional; a decision missing any required field fails
contract validation and cannot be constructed, so it can never reach the import
path.

| Field | Required | Purpose |
| --- | --- | --- |
| `reviewer_id` | yes | Stable actor identifier (operator id / stable slug). Not a boolean; an anonymous or empty reviewer fails validation. |
| `decision_timestamp` | yes | Caller-supplied instant the decision was made. Excluded from `review_decision_id` (§H). |
| `status` | yes | Closed enum: `approved` / `rejected` / `deferred`. No other value is representable. |
| `reason` | yes | Non-empty, bounded free text stating *why*. An approval with no reason fails validation. |
| `notes` | optional | Additional bounded context. |
| `candidate_id` | yes | The exact Phase 40F candidate the decision is about. |
| `content_digest` | yes | The exact candidate byte digest the decision was made against (binds the decision to specific bytes). |
| `assessment_report_id` | yes | The exact Phase 40G report id reviewed. |
| `assessment_version` | yes | The Phase 40G ruleset version reviewed. |
| `evidence_references` | yes, ≥1 | Typed references to the assessment report, dry-run findings, and/or candidate provenance the reviewer relied on. |
| `supersedes_decision_id` | optional | The prior decision this one directly supersedes for the same logical candidate line, when the reviewer is explicitly renewing review (§D.7). When present it MUST reference an existing decision for the same `candidate_id` line. |

> A plain `approved = true` field **never independently authorizes mutation.** The
> `status` enum only *names* the decision; authority to import requires the whole
> record — reviewer, timestamp, reason, the exact candidate digest, the exact
> assessment identity/version, and evidence — and that whole record must still be
> valid, unchanged, and non-contradictory at import time (§E). The import path
> re-derives `review_decision_id` from its fields and rejects a record whose stored
> id disagrees, so a forged or edited decision cannot be presented.

Contradictory evidence (e.g., an `approved` decision whose referenced assessment
verdict is `blocked`, or whose evidence points at a different candidate) is a
fail-closed condition (`contradictory_evidence`, §J), not a soft warning.

**Review-decision supersession is a decision-lineage concern, not an
import-attempt-ordering concern.** A renewed decision references the decision it
supersedes directly through `supersedes_decision_id` (§D.7); `attempt_sequence`
(§G.2) plays **no** part in review-decision ordering.

---

## D. Persistence lifecycle

### D.1 Ledger workflow states

These are **migration-ledger workflow states**, tracked in the ledger. They are
distinct from the Active Memory record's own `lifecycle_state` (which, for every
imported record, is `INACTIVE` — §F.1).

```
candidate_received  →  assessment_completed  →  awaiting_review
                                                     |
                        ┌────────────────────────────┼────────────────────────────┐
                        v                            v                            v
                    approved                     rejected                     deferred
                        |                       (terminal*)                  (non-terminal)
                        v
                import_intended
                   |         |
                   v         v
             import_verified   import_failed
              (terminal)       (non-terminal; safe retry)
                   |
                   v
             uncertain_commit  → (recovery, §I.7) →  import_verified | import_failed
```

### D.2 State meanings

- **candidate_received** — a Phase 40F candidate exists and is referenced.
- **assessment_completed** — a Phase 40G report exists over the candidate's set.
- **awaiting_review** — no valid non-superseded decision yet exists for the exact
  `(candidate_id, digest, assessment_id, version)` tuple.
- **approved / rejected / deferred** — a review decision of that status is the
  current effective (non-superseded) decision for the tuple.
- **import_intended** — a distinct import attempt has durably recorded its *intent*
  (planned `target_record_id`, observed `commit_generation`) but the receipt is not
  yet committed. This is the window that makes uncertain commits detectable (§I).
- **import_verified** — a receipt exists, the snapshot and ledger `commit_generation`
  agree, and the `record_id` resolves in the Active Memory snapshot (the only
  success terminal).
- **import_failed** — an attempt did not commit; no receipt exists and the planned
  record is confirmed absent from the Active Memory snapshot (safe to retry).
- **uncertain_commit** — an intent exists, no receipt exists, and whether the Active
  Memory record durably persisted cannot yet be determined. Not a success and not a
  safe retry until recovery resolves it (§I.7).

### D.3 Terminal vs non-terminal

- **Terminal:** `import_verified` (success), `rejected` (\*terminal for that exact
  reviewed input; a *different* input — new digest or new assessment — is a fresh
  `awaiting_review`, not a re-opening of the rejected one).
- **Non-terminal:** `awaiting_review`, `deferred`, `import_intended`,
  `import_failed`, `uncertain_commit` (resolved only by recovery).

### D.4 Prohibited transitions

- `awaiting_review`/`deferred`/`rejected` → `import_intended` **without** a valid,
  non-superseded `approved` decision. Forbidden.
- A **superseded** approval authorizing import. Forbidden — a decision with a later
  superseding decision authorizes nothing (§D.7).
- `import_failed`/`uncertain_commit` → `import_verified` **without** a fresh, fully
  re-validated attempt or a successful recovery finalize (§I.7). A failed or
  uncertain attempt never "upgrades" to verified by assertion.
- Any state → `import_verified` **without** the receipt's `record_id` resolving in
  the Active Memory snapshot **and** the snapshot/ledger `commit_generation` agreeing
  (§I). Forbidden by construction.
- Editing a recorded decision's `status`, `reason`, `reviewer_id`, `digest`, or
  assessment binding in place. Forbidden — records are immutable (§B, §D.6).
- `approved` for tuple *X* authorizing import of tuple *Y* (different candidate,
  digest, assessment, or version). Forbidden — the import path binds to the exact
  tuple.
- Mutating the Active Memory record in place to "re-import." Forbidden — a changed
  import is a new `record_id` superseding the old via `supersession_refs` (§D.7,
  §F.2), honoring the Active Memory store's immutability.
- **Transitioning an imported `INACTIVE` Active Memory record directly to
  `SUPERSEDED`.** Forbidden and structurally impossible: the Phase 37C
  `LIFECYCLE_TRANSITIONS` table has **no `INACTIVE → SUPERSEDED` edge**
  (`INACTIVE` may move only to `ACTIVE` or `ARCHIVED`). Phase 40H therefore **never
  calls `transition_lifecycle` in the import path**; supersession of an imported
  record is expressed **only** through the *newer* record's `supersession_refs`
  (§D.7, §F.2), leaving the prior record `INACTIVE` and its "superseded" standing a
  *derived* relationship.

### D.5 Retry and stale-record rules

- **Retry:** after `import_failed`, a retry re-runs the full verified-import
  precondition set (§E) from scratch under a **new** `import_attempt_id` (§G). There
  is no shortcut path.
- **Stale record:** an `approved` decision whose candidate digest or assessment no
  longer matches the present candidate/assessment is **stale**; it is not deleted
  (history is preserved) but it fails the import preconditions and is reported
  (`stale_approval`, §J).

### D.6 Append-only vs updated

State transitions are **append-only through controlled records.** The ledger never
edits an existing record's field. A superseding decision is a *new* decision record
that references the one it supersedes (`supersedes_decision_id`); effective status is
computed as the newest non-superseded decision for a tuple, exactly as Phase 40D/40G
compute readiness rather than reading it off a record. Import attempts likewise
append status/intent records. This makes the whole history auditable and makes "who
changed what, when" answerable from the ledger alone.

### D.7 Supersession, renewed review, tie and cycle rules (deterministic)

Two supersession relationships are kept **separate**: **review-decision
supersession** (a lineage over decisions) and **Active Memory record supersession**
(a lineage over imported records). Neither uses `attempt_sequence` for ordering.

**Review-decision supersession (decision lineage):**

- **Renewed review required when** the candidate digest changes (re-parsed bytes) or
  the assessment identity/version changes (re-assessed set, or ruleset version bump).
  The prior approval no longer matches the exact reviewed input and authorizes
  nothing; a new `awaiting_review` applies until a new decision is recorded.
- A renewed decision **directly references** the decision it supersedes via
  `supersedes_decision_id`. Validation requires that the predecessor exists, belongs
  to the same `candidate_id` line, and that the renewal's own candidate identity,
  digest, and assessment identity/version are internally consistent with the review
  lineage it claims.
- The **effective head** of a decision line is the unique newest non-superseded
  decision. The graph is walked before any insert. It fails closed on:
  a missing predecessor (`incomplete_review_provenance`), a cycle
  (`supersession_cycle`), or **two or more unsuperseded heads** for one line
  (`supersession_tie`). The `review_decision_id` (a content-derived canonical id,
  §H.1) is used **only** as a deterministic validation/tiebreak mechanism where two
  candidate orderings are otherwise semantically equal — never to *pick a winner*
  among genuinely ambiguous heads (that is a tie and fails closed).
- **A superseded approval cannot authorize import** (§D.4).

**Active Memory record supersession (record lineage):**

- **Changed-byte identity:** different bytes ⇒ different `content_digest` ⇒ a
  distinct reviewed input ⇒ a **new** resulting `record_id`. Same bytes + same
  assessment ⇒ same `record_id` (§H.3) ⇒ idempotent (§G), never a second record.
- **Changed-assessment behavior:** a changed `report_id`/version invalidates the
  prior approval (renewed review) and, on re-approval, yields a **new** `record_id`
  that supersedes the prior import of the same logical candidate line. The new
  record's `supersession_refs` carry a single `SUPERSEDES` link to the prior
  `record_id`; the prior record is **not** transitioned (§D.4) — its superseded
  standing is the derived inverse the Phase 37C model already defines
  (`SUPERSEDED_BY` is never stored, only derived).
- **Deterministic supersession ordering (records):** when a new import supersedes a
  prior one, ordering is a **total order** over `(decision_timestamp, record_id)` —
  caller-supplied decision time first, and the content-derived `record_id` as the
  final, always-decisive tiebreak. No clock is read; ordering is fully determined by
  recorded fields. `attempt_sequence` is **not** part of record ordering.
- **Tie rejection:** a state that would leave **two** active (non-superseded) heads
  for one logical candidate line — two distinct records with identical ordering keys
  through `record_id` — is rejected fail-closed as `supersession_tie` (§J) rather
  than silently picking one head.
- **Cycle rejection:** a proposed supersession whose `record_supersedes` links would
  close a cycle in the record supersession graph (A supersedes B … supersedes A) is
  rejected fail-closed as `supersession_cycle` (§J). The graph is walked before any
  insert; a cycle is never persisted. (The Phase 37C single-stored-direction
  `SUPERSEDES` design keeps chains acyclic by construction; Phase 40H validates it
  explicitly before authoring the link.)

---

## E. Verified-import contract (the ordered protocol)

The reviewed-import operation (`import_reviewed_candidate`) is the only path that
creates an Active Memory record from a candidate. The complete ordered protocol,
**entirely under the coordinator's exclusive writer lock (§I.4)**, is:

1. **Acquire the coordinator lock** (§I.4), with bounded timeout/poll/attempts; on
   failure return `lock_unavailable` (retryable) or `stale_lock_ambiguous` (fail
   closed) as appropriate.
2. **Load and validate both durable stores** — the migration ledger and the Active
   Memory snapshot (§A.3, §A.4) — running the load-time integrity **detection** scan
   (§I.8). A cold start with neither present initializes both at generation 0.
3. **Validate the shared commit generation** — the ledger's and the snapshot's
   recorded `commit_generation` must agree; mismatch → `generation_mismatch`, fail
   closed (§I.3).
4. **Reload / revalidate the candidate.** Re-obtain the Phase 40F candidate (and,
   where the request carries the artifact reference, re-establish its provenance)
   rather than trusting a caller-passed blob.
5. **Recompute and compare the byte digest.** Recompute the candidate
   `content_digest` (Phase 40F SHA-256 convention) and compare it to the digest the
   review decision was made against. Mismatch → `changed_digest`.
6. **Confirm the reviewed candidate has not changed.** `candidate_id` and its
   provenance fingerprints must match the reviewed decision exactly (`stale_candidate`
   on mismatch).
7. **Confirm the reviewed assessment identity/version has not changed.** The Phase
   40G `report_id` and ruleset version must match the reviewed decision exactly
   (`changed_assessment` on mismatch).
8. **Confirm required review provenance exists** and is complete: reviewer id,
   timestamp, reason, candidate id + digest, assessment id + version, ≥1 evidence
   reference (`missing_review` / `incomplete_review_provenance`).
9. **Confirm the decision is `approved` and is the current non-superseded head** for
   the tuple (`rejected_candidate` / `deferred_candidate` / `stale_approval`); reject
   a superseded approval (§D.7).
10. **Cross-check evidence for contradictions** (approval over a `blocked`
    assessment, evidence pointing at a different candidate, etc.) →
    `contradictory_evidence`.
11. **Validate supersession** (§D.7): reject `supersession_tie` / `supersession_cycle`
    / missing predecessor before any write.
12. **Resolve idempotency.** Compute the stable idempotency key (§G.1, §H.1). If a
    committed receipt already exists for it, **return that exact stored receipt and
    its `record_id`** — no new record (`duplicate_replay`). If a *materially
    different* attempt collides on a related but non-identical input, fail closed
    (`conflicting_replay`).
13. **Fail closed** for any missing, stale, contradictory, or mismatched evidence.
    The default is refusal; only a fully consistent set proceeds.
14. **Allocate the next attempt sequence under the lock** as `(count of prior
    attempts for this idempotency key) + 1` (§G.2), and **persist a durable intent** —
    append a new `import_attempt` in `intent_state = intended` carrying the planned
    `target_record_id` and the currently-loaded `commit_generation`, committed via
    the ledger CAS write (§I.5). This is the point after which an interruption is
    *recoverable* rather than ambiguous.
15. **Construct the deterministic `MemoryRecord`** under the Active Memory contract
    (INACTIVE, UNVERIFIED, §F.1) with `record_id` derived per §H.3 and provenance
    mapped per §F.3.
16. **Insert it into the authoritative in-memory Active Memory store** through the
    store's own seam only (§F.2). A `DuplicateRecordError` whose existing record has
    **matching** content-identity is the already-inserted case (§F.3); a mismatch is
    `record_identity_collision` (fail closed).
17. **Persist the new Active Memory snapshot with the next commit generation**
    (`commit_generation + 1`) via `ActiveMemorySnapshotStore.persist` (§A.4), atomic
    temp-swap. On any snapshot failure, apply the **post-insert failure rule**
    (§I.6).
18. **Persist the receipt and completed attempt in the ledger with the same commit
    generation** — write the deterministic receipt (§B.3) linking candidate, digest,
    assessment, review decision, attempt, `commit_generation`, and the exact
    `record_id` (and `record_supersedes` when applicable), advance the attempt to
    `committed`, and advance the ledger `commit_generation` to match the snapshot, via
    the ledger CAS write (§I.5). **This ledger commit is the reporting commit point.**
19. **Reload and verify exact linkage before reporting success** — re-read both
    durable stores under the still-held lock and confirm: the receipt exists, its
    `record_id` resolves in the reloaded snapshot, the two `commit_generation` values
    agree, and the record's content-identity matches (§I.7 finalize check). Only then
    report `import_verified`.
20. **Release the lock** in a `finally` (success, handled failure, and exception
    paths all release — §I.4).

> The ledger receipt is the **reporting** commit point, but reported success
> **additionally requires** matching durable snapshot `commit_generation` and exact
> record linkage (steps 17–19). A receipt is *verified* only when its linked snapshot
> generation and ledger generation agree (§I.3).

### E.1 What "verified import" proves — and does not

**Proves:** the exact candidate bytes that were reviewed (digest-identical) were
imported; the exact assessment the reviewer saw still applies; a complete,
attributable, non-contradictory, non-superseded approval authorized it; and the
resulting Active Memory record (owned by the Active Memory store, durable in the
snapshot at an agreed `commit_generation`) is deterministically linked to all of that
by an immutable receipt referencing its exact `record_id`. Re-running the same
reviewed input yields the same receipt and the same `record_id`, and no second record.

**Does not prove:** that the imported statement is factually **true**. Byte integrity
and review provenance are not truth adjudication. Accordingly the resulting record is
imported evidence with a conservative standing (§F.1): it is not `human_confirmed`
truth merely because a human approved *importing it*, and it is never auto-activated
into the trusted baseline by this phase. No LLM or automated process decides truth
anywhere in the path.

---

## F. Mutation authority and provenance mapping

**One explicit mutation boundary:**

> Only the reviewed-import path (the import coordinator's `import_reviewed_candidate`)
> creates an Active Memory record from a migration candidate, and it does so
> **exclusively through the Active Memory store's own insertion seam (§F.2)** — never
> by owning, copying, or bypassing that store.

- Parsing, projection, validation, assessment, dry-run, inspection, and
  review-record creation **must not** mutate Active Memory. Recording a review
  decision writes a *decision* to the migration ledger; it does not touch Active
  Memory.
- **No automatic candidate approval.** Approval is a human act recorded as a review
  decision; nothing derives approval.
- **No semantic promotion inferred from parsing success.** A candidate that parsed
  cleanly, hashed cleanly, and assessed `ready_for_review` is still just a candidate
  until a human decision plus a verified import exist.
- **No LLM or automated truth adjudication** anywhere in the path.

### F.1 Standing of the resulting Active Memory record

The imported record is created **inactive** (`LifecycleState.INACTIVE`) and
**unverified** (`VerificationState.UNVERIFIED`) — it is imported history a human
chose to bring in, not an adjudicated active fact. Both values are already
first-class members of the existing Active Memory enums, so no enum or contract
change is required. Promotion to `active` / `human_confirmed` (active-state
calculation, contradiction handling) and any lifecycle retirement remain deferred
Active Memory work already named in the roadmap and are **not** part of Phase 40H.
This preserves the Phase 40E/40F invariant that imported material is never verified
truth automatically, while still letting a human durably persist a reviewed candidate.

### F.2 The authorized Active-Memory-insertion seam

Phase 40H inserts through the **existing** Active Memory store boundary, not a new
one:

- **Seam:** `MemoryStore.insert(record: MemoryRecord) -> MemoryRecord` in
  [`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py).
  The coordinator constructs a `MemoryRecord` with a deterministic caller-supplied
  `record_id` (§H.3) and inserts it.
- **Duplicate semantics are reused, not reinvented.** The store already raises
  `DuplicateRecordError` on a colliding `record_id`. Because Phase 40H's `record_id`
  is a pure function of the reviewed content-identity, a duplicate insert means *this
  exact content already exists*. The coordinator compares the existing record's
  content-identity to the one it would have written: on an exact match it treats this
  as the already-inserted case and reconciles against the ledger intent (§I.7); on a
  mismatch it fails closed as `record_identity_collision` (§J).
- **Supersession is authored on the new record only — `transition_lifecycle` is NOT
  called.** A changed re-import writes a *new* record whose `supersession_refs` carry
  a single `SUPERSEDES` link to the prior `record_id`, exactly as the Active Memory
  store already models supersession (forward-direction only; the inverse is derived).
  The prior imported record stays `INACTIVE`; Phase 40H **does not** invoke
  `transition_lifecycle` in the verified-import transaction, because the only
  transition it would want (`INACTIVE → SUPERSEDED`) is **not permitted by the Phase
  37C lifecycle table** and the ruling forbids changing that table here. The store's
  `transition_lifecycle` remains available for other, independently-valid transitions
  outside this phase; Phase 40H's import path simply never uses it.
- **Durability handshake.** Because the Active Memory store is in-memory with
  caller-owned serialize/restore, the *effect* of the insert is made durable by the
  mandatory `ActiveMemorySnapshotStore` (§A.4) **before** the ledger receipt is
  committed (§E steps 17–18). Phase 40H does **not** re-home Active Memory records
  into the ledger to fake durability.

### F.3 Candidate-to-`MemoryRecord` provenance mapping

Phase 40H maps a reviewed candidate onto the **existing** `MemoryRecord` fields.
Provenance is **not** left as unspecified free-form metadata: Phase 40H defines a
typed `MigrationProvenance` sub-model (in the new `memory_migration_import.py` models
module, §L) whose canonical dump populates `MemoryRecord.metadata["migration_provenance"]`.
The `metadata: dict[str, Any]` field is the Phase 37B contract's **documented
forward-compatible extension point**; specifying its exact shape in Phase 40H's own
module means **no change to the frozen Phase 37B `active_memory.py` contract is
required or proposed.**

| Migration value | Carried by (existing `MemoryRecord` surface) | Tier |
| --- | --- | --- |
| **Candidate identity** (`candidate_id`) | `metadata.migration_provenance.candidate_id`; also `source.source_id` (stable candidate-derived slug); also an input to `record_id` (§H.3) | content-identity |
| **Candidate digest** (`content_digest`) | `metadata.migration_provenance.content_digest`; input to `record_id` | content-identity |
| **Assessment identity + version** (`assessment_report_id`, `assessment_version`) | `metadata.migration_provenance.assessment_report_id` / `.assessment_version`; inputs to `record_id` | content-identity |
| **Review-decision identity** (`review_decision_id`) | `metadata.migration_provenance.review_decision_id` | review/attempt audit |
| **Stable idempotency key** | `metadata.migration_provenance.idempotency_key` | review/attempt audit |
| **Evidence references** | `metadata.migration_provenance.evidence_references` (typed, mirrors the decision's `evidence_references`) | review/attempt audit |
| **Import-attempt identity** (`import_attempt_id`) | `metadata.migration_provenance.import_attempt_id` | review/attempt audit |
| **Deterministic source/provenance** | `source` = `MemorySource(source_type=IMPORTED_DOCUMENT, source_id=<candidate slug>, display_label?, session_id?)` — `IMPORTED_DOCUMENT` already exists in `MemorySourceType`; plus the whole `metadata.migration_provenance` block | content-identity (source) + audit |
| **Supersession of a prior import** | `supersession_refs = [SupersessionReference(kind=SUPERSEDES, target_record_id=<prior>, created_at=<decision_timestamp>)]` | derived record lineage |
| **Record kind / claim / project / scope** | `kind` (from the Phase 40F projected candidate kind), `claim` (projected subject/predicate/value), `project_id`, optional `scope` | content |
| **Standing** | `lifecycle_state = INACTIVE`, `verification_state = UNVERIFIED` (§F.1) | fixed |

**Two provenance tiers, and why they matter for identity:**

- **Content-identity provenance** — `candidate_id`, `content_digest`,
  `assessment_report_id`, `assessment_version` — is part of `record_id` derivation
  (§H.3) **and** part of the *canonical record equality* check that gates a duplicate
  insert.
- **Review/attempt audit provenance** — `review_decision_id`, `idempotency_key`,
  `import_attempt_id`, `evidence_references` — is stored for audit but is **not** part
  of `record_id` and **not** part of the canonical-equality gate. Records are
  immutable; on an already-inserted match the existing record's audit provenance is
  never overwritten.

**Consequence (duplicate-`record_id` validity, per the ruling):** a duplicate
deterministic `record_id` is valid **only when complete canonical record content and
content-identity provenance match exactly**; then the second reviewed input reuses the
existing record and records its own receipt (§B.1, §G.3). If a matching `record_id`
carries **non-identical** content-identity (tampering, or an astronomically unlikely
hash collision), it is a typed `record_identity_collision` and fails closed. A
reviewed-input-level conflict (same digest under a different assessment/decision that
collides with a materially different existing attempt) is the distinct
`conflicting_replay` failure (§G.3).

> **Minimal-model-change note.** The existing `metadata` extension point safely
> carries all migration provenance as a typed, namespaced block, so **no Phase 37B
> model change is required.** If a future independent audit instead requires these
> values promoted to first-class typed fields on `MemoryRecord`, that is a **named,
> separate Phase 37B contract change** — explicitly out of scope here and listed as
> deferred (§N), not silently performed by Phase 40H.

---

## G. Idempotency and replay

### G.1 Stable idempotency key inputs

The stable idempotency key is the canonical id (§H.1) over exactly: `candidate_id`,
`content_digest`, `assessment_report_id`, `assessment_version`, and
`review_decision_id`. These five identify "this exact reviewed input." Nothing
time-based, random, or request-envelope-based enters the key. **The key is stable
across retries** — every retry of the same reviewed input computes the same key.

### G.2 Distinct attempt ids via a deterministic monotonic sequence (retries only)

While the idempotency key is stable, **every attempt gets a distinct
`import_attempt_id`** (§H.2), keyed off `attempt_sequence`. `attempt_sequence` is
**scoped only to retries under one stable reviewed-input idempotency key** — it is
**not** a review-decision ordering key (§C, §D.7). It is a deterministic monotonic
integer assigned **under the exclusive writer lock** as `(count of prior attempts
recorded in the ledger for this idempotency key) + 1`. The first attempt is `1`, its
retry is `2`, and so on. It is **persisted, append-only, unique, and contiguous per
idempotency key**, and it is **validated during load** (a gap or duplicate in the
per-key sequence is `corrupt_ledger`, §J). Consequences:

- attempt ids never collide, so a retry is a first-class, separately-auditable ledger
  record rather than an overwrite of the prior attempt;
- the sequence is reconstructible purely from durable ledger state (no counter held
  only in memory), so recovery (§I.7) can compute the next sequence deterministically;
- the *receipt* is keyed by the stable idempotency key (at most one committed), so
  many distinct attempts still yield at most one Active Memory record.

### G.3 Behavior

- **Duplicate valid request** (same key, prior committed receipt): return the **exact
  existing receipt unchanged** and its existing `record_id`. No new attempt commits a
  second record. Idempotent replay is a lookup, not a re-import (`duplicate_replay`).
- **Deterministic receipt lookup:** the committed receipt is addressable by the
  idempotency key, so a replay is answered from the ledger deterministically.
- **Successful replay:** returns the same `receipt_id` and same `record_id` as the
  original — byte-identical result.
- **Retry after failure:** if no committed receipt exists for the key, a retry
  acquires a **new** `import_attempt_id` (§G.2), re-runs §E fully, and may create the
  (first and only) receipt.
- **Distinct decisions over identical content+assessment:** a *different* approved
  decision over the *same* `content_digest` + assessment has a *different* idempotency
  key (it includes `review_decision_id`) but derives the *same* `record_id` (§H.3).
  Its import reuses the already-existing record (§F.2 already-inserted case) and writes
  its own receipt referencing that `record_id` — one record, a second audited receipt.
- **Concurrency:** two concurrent requests for the same key cannot both create a
  record. The exclusive writer lock (§I.4) serializes them and the persisted-revision
  CAS (§I.5) rejects a stale writer (`revision_conflict`); one wins and the other
  resolves to the winner's receipt (`duplicate_replay`). No lost update, no double
  record.
- **Conflicting replay detection:** the *same* candidate digest presented under a
  *different* assessment or a *different* review decision is a distinct reviewed input
  requiring its own approval; if it collides with an existing but **materially
  different** attempt it is reported (`conflicting_replay`), never silently merged.

> Approved candidates import **exactly once** for the same reviewed input; duplicate
> valid requests return the same deterministic result rather than creating another
> Active Memory record.

---

## H. Canonical identity derivation

Every derived identity is a pure function of typed content. The derivation is the
repository's canonical-JSON + SHA-256 convention (reused from Phase 40E/40F/40G — no
new scheme), pinned here so field boundaries are unambiguous.

**Common encoding rules (all four identities):**

- **canonical JSON encoded as UTF-8**, with **sorted object keys**;
- an explicit **`schema` field** = `"memory-migration-import.v1"`;
- an explicit **`domain` tag** naming the identity type (below), so two identities can
  never collide across types even with identical member values (domain separation);
- **typed values** (strings/ints/enums as themselves; no lossy stringification of
  structured values);
- **arrays preserve their defined ordering** (evidence references keep authored order);
- **no timestamps** in the stable reviewed-input key, and no timestamps in any
  identity used for equality (temporal fields are audit-only, §B.2);
- **SHA-256 over the canonical encoded bytes**, hex-encoded, as the identity value.

### H.1 Reviewed-input idempotency key

- **domain:** `migration-import/reviewed-input`
- **exact members:** `candidate_id`, `content_digest`, `assessment_report_id`,
  `assessment_version`, `review_decision_id`.
- No timestamps, no attempt data, no request envelope. This is "the exact reviewed
  input." `review_decision_id` is itself the canonical id over the decision's fields
  (a decision-domain id), so a renewed decision (new `review_decision_id`) forms a
  **distinct** reviewed input even over identical bytes/assessment — that is a new
  approval to be audited, and it is *not* a conflicting replay unless it collides with
  a materially different existing attempt (§G.3).

### H.2 `import_attempt_id`

- **domain:** `migration-import/attempt`
- **exact members:** `idempotency_key`, `attempt_sequence`.
- `attempt_sequence` obeys the persistence/uniqueness/contiguity rules of §G.2.

### H.3 Deterministic `MemoryRecord.record_id`

- **domain:** `migration-import/record`
- **exact members:** the **projected canonical claim content** (`kind`, `claim`
  subject/predicate/value/value_kind, `project_id`, optional `scope`) **plus the
  content-identity provenance** (`candidate_id`, `content_digest`,
  `assessment_report_id`, `assessment_version`).
- **Deliberately excluded:** `review_decision_id`, `idempotency_key`,
  `import_attempt_id`, all timestamps. This is why two distinct approved decisions over
  identical content+assessment produce the **same** `record_id` (§B.1, §G.3), and why a
  changed digest or changed assessment produces a **new** `record_id` that supersedes
  the prior one (§D.7).
- **Canonical record equality** (the duplicate-insert gate, §F.3) compares exactly this
  content-identity member set; a matching `record_id` with a differing member set is
  `record_identity_collision`.

### H.4 `receipt_id`

- **domain:** `migration-import/receipt`
- **exact members:** `idempotency_key`, `import_attempt_id`, `record_id`,
  `record_supersedes` (or an explicit null token), and `commit_generation`.
- **Deliberately excluded:** `attempt_timestamp`, `verification_timestamp`, and every
  other temporal/audit field — so `receipt_id` (and `receipt_digest`, computed the same
  way) is a stable function of the linkage and a duplicate replay returns the exact
  stored receipt unchanged (§B.3, §G.3).

**Distinct-reviewed-input vs conflicting-replay (clarified):** different assessments
or different review decisions over the same bytes form **distinct reviewed inputs**
(distinct idempotency keys, §H.1) that each require their own approval; they are
handled idempotently and, where they share a `record_id`, reuse the existing record
(§G.3). They become a typed **`conflicting_replay`** only when a request collides on a
related key with an existing but **materially different** attempt (e.g., an attempt
already recorded for that key referencing a different content-identity), never a
silent merge.

---

## I. Atomicity, concurrency, coordination, and recovery

This section is written to the hard constraint: **there is no single atomic commit
spanning the durable JSON ledger and the durable Active Memory snapshot.** The plan
does not pretend otherwise. Instead it defines a *recoverable two-artifact protocol*
whose durable reporting commit point is the ledger receipt, bound to the snapshot by a
shared **commit generation**, guarded by **one coordinator lock** and **per-file CAS**,
with an explicit recovery routine and an explicit quarantine.

### I.1 Why cross-store atomicity is not claimed

The migration ledger and the Active Memory snapshot are **two independent durable
files** with **two independent `os.replace` operations**. Two independent durability
domains cannot be committed by one filesystem operation. Any claim of a single atomic
swap covering "attempt + memory record + receipt" would be false. Phase 40H therefore
uses **ordering + a durable intent + a shared generation + recovery**, not fictional
atomicity.

### I.2 Transaction boundary and commit point

The import of one candidate is a *logical* transaction across the two durable
artifacts, ordered so the durable ledger is the authoritative record of the outcome
(the full ordered protocol is §E). In brief:

1. durably record the **intent** (`import_attempt`, `intent_state = intended`, planned
   `target_record_id`, observed `commit_generation`) via the ledger CAS write (§I.5);
2. insert the record into the Active Memory store (§F.2) and **durably persist the
   Active Memory snapshot at `commit_generation + 1`** (§A.4);
3. durably record the **receipt** and advance the ledger's `commit_generation` to the
   same `+1`, advancing the attempt to `committed`, via the ledger CAS write.

**The reporting commit point is step 3 — the durable receipt.** A receipt is written
**after** the snapshot durably reflects the record at the new generation, so *a
committed receipt whose generation matches the snapshot implies a durable record*. The
converse gap (a durable snapshot at `+1` with no receipt) is exactly the recoverable
window §I.7 resolves.

### I.3 Shared persisted commit generation

A persisted monotonic integer **`commit_generation`** is recorded in **both** durable
artifacts — the ledger document and the Active Memory snapshot envelope (§A.4).

- **Initialization:** a cold start with **neither** artifact present initializes both
  at `commit_generation = 0` under the coordinator lock. A start with exactly **one**
  present is a torn/absent state → fail closed (`snapshot_missing` or `corrupt_ledger`
  as applicable).
- **Validation:** at startup and at the top of every import (§E steps 2–3), **under
  the coordinator lock**, both artifacts are loaded and their recorded generations
  compared; they **must be equal**. Inequality → `generation_mismatch`, fail closed.
- **Increment:** each successful verified import advances the generation by **exactly
  1** — the snapshot is written at `N+1` (step 2) and the ledger receipt/generation is
  written at `N+1` (step 3).
- **Receipt verification rule:** a receipt is **verified only when its linked snapshot
  generation and the ledger generation agree.** A receipt at generation `N+1` over a
  snapshot still at `N` (torn write between steps 2 and 3) is not a verified success —
  it is the recoverable window (§I.7).
- **No false atomicity:** generation equality is a **cross-check that detects a torn
  cross-file write**, not a claim that both files were written atomically. It is what
  makes the two-file protocol *recoverable*, not *atomic*.

`commit_generation` (the shared cross-store epoch) is distinct from `ledger_revision`
(the ledger file's internal lost-update CAS token, §I.5): a single import advances the
ledger `ledger_revision` on each of its ledger writes, and advances the shared
`commit_generation` exactly once.

### I.4 The coordinator and its one concrete lock protocol

**One import coordinator (§A.2) owns a single exclusive writer lock** covering the
whole transaction and recovery: ledger reload, snapshot reload, generation validation,
intent persistence, in-memory insertion, snapshot persistence, receipt persistence,
and the reload-and-verify step. Readers (idempotent replay lookup, inspection) do not
take the writer lock and never mutate.

**One concrete, Windows-compatible, dependency-free protocol is selected — not a menu
of alternatives.** The lock is an **atomic exclusive lock-file creation** using the
Python standard library's `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. This
single primitive is atomic-create-or-fail on both Windows and POSIX and needs no third
-party dependency.

> **Not** used, and **not** presented as interchangeable alternatives: `msvcrt.locking`
> (Windows-only byte-range locking) and `fcntl.flock` (POSIX-only advisory locking) are
> explicitly **rejected** for this feature because they are platform-specific and would
> force a divergent two-path implementation. `O_EXCL` create is the one portable
> mechanism chosen; the others are named here only to record that they were considered
> and declined.

- **Owner metadata** (written as the exclusive-create payload, atomically, since the
  file did not previously exist): `owner_pid`, `created_at` (lock creation time, for the
  stale threshold), `host`/`boot_id` where determinable, and **`operation_identity` =
  the stable reviewed-input idempotency key** (§G.1). The idempotency key is known
  *before* an attempt is allocated, so it is a valid operation identity at acquisition.
- **The lock never contains `import_attempt_id` before the attempt exists.** The
  attempt id is allocated *after* the lock is held and the intent is about to be written
  (§E step 14). If desired for observability, the lock payload MAY be **updated
  in-place after attempt allocation** to add `import_attempt_id`, but the lock's
  validity and release never depend on that field — only `owner_pid` +
  `operation_identity` determine ownership.
- **Bounded acquisition:** a configurable **acquisition timeout**, **polling interval**,
  and **maximum attempts**, all env-overridable. On exhaustion the caller receives
  `lock_unavailable` (fail closed, retryable) — the coordinator does not proceed
  concurrently.
- **Stale-lock recovery is conservative and fails closed on ambiguity.** A lock is
  reclaimed **only when both**: (a) the recorded `owner_pid` is **positively validated
  to no longer exist** (POSIX: `os.kill(pid, 0)` semantics; Windows: a stdlib
  `ctypes` `OpenProcess` existence probe — still dependency-free), and the probe is
  **conclusive**; **and** (b) the lock's age exceeds the configured **stale threshold**.
  If process existence **cannot be conclusively determined**, or `host`/`boot_id`
  indicate a different machine/boot than the current one, ownership is **ambiguous** →
  `stale_lock_ambiguous`, fail closed (no reclaim). A conclusively-dead owner past the
  threshold allows a single atomic reclaim (remove-then-`O_EXCL`-create) under audit.
- **Release** removes the lock file **only if the current process still owns it**
  (`owner_pid` + `operation_identity` match), in a `finally`, covering all three paths:
  **success**, **handled failure** (any typed fail-closed result), and **exception**.
  A release that finds a foreign owner does not delete it and logs a safe diagnostic.

### I.5 Persisted revision + compare-and-swap (per-file, ledger)

Every **ledger** write is additionally guarded by a persisted monotonic
`ledger_revision`:

- a writer reads the current revision `R` (from disk, under the lock);
- it stages the next document with `R+1`;
- immediately before `os.replace`, it re-reads the on-disk revision and proceeds only
  if it is still `R`; otherwise it aborts with `revision_conflict` (§J).

Atomic replacement alone is **insufficient** because two writers could each read `R`,
each stage `R+1`, and the later replace would clobber the earlier without either
noticing. CAS on the persisted revision detects that lost-update race and refuses it.
The exclusive writer lock (§I.4) is the *primary* mutual exclusion; CAS is
defense-in-depth. **Atomic file replacement alone is explicitly not treated as
sufficient** for either the concurrency guarantee (CAS) or the cross-store guarantee
(shared generation, §I.3).

### I.6 Post-insert failure and quarantine

If the in-memory insertion (§E step 16) succeeds but **Active Memory snapshot
persistence (step 17) fails**, the coordinator MUST:

1. **not retain the uncommitted live mutation** — the in-memory store now holds a
   record that never became durable;
2. **reload the last validated durable snapshot into a fresh authoritative in-memory
   store** (via `ActiveMemorySnapshotStore.load`), discarding the live mutation;
3. **preserve the durable intent** already written at step 14 and **mark the attempt
   `failed` or `uncertain`** as appropriate (below);
4. **never create a verified receipt**;
5. if the **safe reload itself fails**, **quarantine/disable reviewed imports**
   (`import_service_quarantined`, §J) until startup recovery succeeds — the coordinator
   refuses further imports rather than operating on unknown in-memory state;
6. **return a typed fail-closed result.**

Equivalent behavior for the specific failure modes:

| Failure | What is (un)certain | Action | Attempt state |
| --- | --- | --- | --- |
| **Snapshot temp-write failure** (before `os.replace`) | Destination untouched; no `+1` snapshot exists | Discard live mutation, reload last validated snapshot; safe to retry | `failed` |
| **Snapshot replacement failure** (`os.replace` raised) | Destination may or may not have been swapped | Discard live mutation, reload; if a valid `+1` snapshot with the planned record is present but no receipt → hand to recovery; else → failed | `uncertain` if a `+1` snapshot may exist, else `failed` |
| **Snapshot reload failure** (cannot restore last-validated durable state) | Authoritative in-memory state is unknown | **Quarantine** reviewed imports until startup recovery; do not operate on unknown state | `uncertain`; `import_service_quarantined` |
| **Ledger receipt-persistence failure** (after snapshot success at `+1`) | Durable record exists at `+1`; no receipt; ledger generation still `N` | Leave the intent; on recovery, the `+1` snapshot + matching intent **prove the effect** → finalize by writing the receipt and advancing ledger generation (idempotent completion) | `uncertain` → recovery `committed` |

In every case: **never a verified receipt without a durable snapshot record at the
agreed generation**, and **never a retained live mutation that never became durable.**

### I.7 Uncertain-commit recovery (explicit routine)

Recovery is an **explicit operation**, not a load-time side effect. When an intent
exists without a matching committed receipt (`uncertain_commit`), recovery:

1. **reacquires the coordinator lock** (§I.4);
2. **reloads both durable stores** — the ledger and the Active Memory snapshot;
3. **validates the shared generation and integrity** (§I.3, §I.8);
4. **finds the durable intent** by its **stable idempotency identity** (§G.1);
5. **locates the deterministic `MemoryRecord` by `record_id`** in the reloaded snapshot;
6. **validates complete canonical record equality and migration provenance — not
   `record_id` alone**: the located record's content-identity member set (§H.3) and its
   `metadata.migration_provenance` content-identity tier (§F.3) must match what the
   intent describes;
7. **locates and validates any stored attempt and receipt** for the key;
8. **finalizes a recoverable missing receipt only when the durable intent and the exact
   snapshot record prove the effect** — i.e. the `+1` snapshot contains the exact
   content-identical record the intent planned: recovery writes the receipt at the
   snapshot's generation, advances the ledger generation to match, advances the attempt
   to `committed` (idempotent completion), and returns success;
9. **otherwise fails closed or restores the last mutually valid generation** according
   to the documented **bounded policy**: if the planned record is **absent** from the
   snapshot and no receipt exists → mark the attempt `failed` (safe retry under a new
   attempt id); if durable state is **unreadable or internally inconsistent** (snapshot
   unavailable, generation unreadable, revision unreadable) → return a typed fail-closed
   `uncertain_commit_result` and, where a *last mutually valid generation* (a prior
   `(ledger, snapshot)` pair whose generations agreed) is recoverable, restore to it
   rather than to an ambiguous half-state;
10. **never guesses success.** A committed receipt is only ever produced when the
    durable record provably exists at the agreed generation.

### I.8 Partial-write **detection** (separate from recovery)

Detection is strictly separated from the recovery *action*:

- a crash mid-write leaves only an orphan temp sibling (never the destination); load
  ignores temp siblings and loads the last good file;
- **load-time integrity scan (detection only):** every receipt must reference an
  existing `import_attempt`, a `record_id`, and a `commit_generation`; `ledger_revision`
  and the per-key `attempt_sequence` must be self-consistent and contiguous; the
  snapshot must validate structurally and per-record; the two artifacts' generations
  must agree; and each receipt's recomputed `receipt_digest` must match its stored one.
  Violations are *reported*, never auto-fixed, as `partial_write_detected`,
  `corrupt_ledger`, `corrupt_active_memory_snapshot`, `snapshot_missing`,
  `generation_mismatch`, `missing_linked_attempt`, `missing_linked_memory_record`, or
  `receipt_integrity_failure` (§J). The load **fails closed** on any violation.
- detection **does not** claim recovery. Turning a detected anomaly into a resolved
  state is only ever done by the explicit §I.7 routine under the writer lock. A load
  that detects a problem reports it and refuses; it does not silently repair.

> A committed, verified receipt must never exist unless its exact resulting Active
> Memory record exists and resolves in the snapshot **at the agreed commit
> generation**. This is the core invariant, enforced at commit (ordering + durable
> snapshot before receipt + shared generation, §I.2/§I.3) and re-checked at load
> (detection scan, §I.8), with ambiguity resolved only by explicit recovery (§I.7).

---

## J. Diagnostics and information safety

Typed, closed-vocabulary diagnostic codes (severity fixed per code, following the
Phase 40E/40F/40G pattern where a caller cannot downgrade a finding). Names are
normalized to the canonical taxonomy below.

| Code | Trigger | Disposition |
| --- | --- | --- |
| `stale_candidate` | Candidate id/provenance no longer matches the reviewed decision | fail closed |
| `changed_digest` | Recomputed candidate digest ≠ reviewed digest | fail closed |
| `changed_assessment` | Assessment id/version ≠ reviewed assessment | fail closed |
| `missing_review` | No review decision for the tuple | fail closed |
| `incomplete_review_provenance` | Decision missing required reviewer/timestamp/reason/evidence, or a dangling intra-ledger reference (incl. a missing `supersedes_decision_id` predecessor) | fail closed |
| `rejected_candidate` | Effective decision is `rejected` | fail closed (no mutation) |
| `deferred_candidate` | Effective decision is `deferred` | fail closed (no mutation) |
| `stale_approval` | Approved decision whose candidate digest or assessment no longer matches the present input, or which has been superseded | fail closed (no mutation) |
| `contradictory_evidence` | Approval contradicts assessment verdict or points at a different candidate | fail closed |
| `supersession_tie` | Two distinct records/decisions would become active heads of one logical line with identical ordering keys | fail closed |
| `supersession_cycle` | Proposed supersession links would close a cycle in the supersession graph | fail closed |
| `duplicate_replay` | Same idempotency key as an existing committed receipt | return the **exact stored receipt** (idempotent) |
| `conflicting_replay` | Same digest under a different assessment/decision colliding with a materially different existing attempt | fail closed (distinct input) |
| `record_identity_collision` | A matching `record_id` whose complete canonical record content / content-identity provenance does **not** match | fail closed |
| `lock_unavailable` | The exclusive writer lock is held by another live owner within the bounded acquisition budget | fail closed (retryable) |
| `stale_lock_ambiguous` | A lock whose owner liveness cannot be conclusively determined, or from a different host/boot | fail closed (no reclaim) |
| `revision_conflict` | The persisted `ledger_revision` changed under a writer (CAS failure) | fail closed (retryable) |
| `generation_mismatch` | Ledger and Active Memory snapshot `commit_generation` disagree | fail closed |
| `snapshot_missing` | Expected Active Memory snapshot absent when its counterpart ledger state exists | fail closed |
| `corrupt_active_memory_snapshot` | Snapshot structurally invalid or fails per-record contract validation | fail closed |
| `corrupt_ledger` | Ledger structurally invalid / internally inconsistent (incl. non-contiguous `attempt_sequence`) | fail closed |
| `persistence_failure` | Ledger or snapshot load/save failed (bounded, typed) | fail closed |
| `partial_write_detected` | Load-time scan found an incomplete/interrupted write (detection only) | fail closed; hand to explicit recovery |
| `missing_linked_attempt` | A receipt references an `import_attempt_id` that does not exist | fail closed |
| `missing_linked_memory_record` | A receipt's `record_id` does not resolve in the Active Memory snapshot | fail closed |
| `receipt_integrity_failure` | A receipt's recomputed `receipt_digest`/`receipt_id` disagrees with its stored value | fail closed |
| `uncertain_commit_result` | Intent exists without a matching committed receipt and durable state cannot determine the outcome | fail closed; resolved only by §I.7 recovery, never reported as success |
| `import_service_quarantined` | Safe reload of durable state failed; reviewed imports are disabled until startup recovery succeeds | fail closed (service disabled) |

**Information safety (reused Phase 40E/40F/40G rule):** diagnostics carry closed-enum
literals, counts, and record-local identifiers/digests (non-reversible hashes) only.
They **never** leak filesystem paths (ledger, snapshot, or lock-file locations),
database internals (there is no DB), credentials, raw exception strings/tracebacks,
candidate body text, exported conversation content, PIDs beyond a bounded owner marker,
or declared paths. Digests are hashes, not content. A path that appears in a raw
`OSError` is mapped to a typed `persistence_failure` with no path echoed.

---

## K. Test matrix

Layers: **C** = contract/model tests, **S** = service/coordinator tests (over a temp
ledger + temp snapshot + injected in-memory Active Memory store), **A** =
adapter/persistence tests (ledger, snapshot, lock), **I** = cross-store integration
tests (coordinator + real `InMemoryActiveMemoryStore` + real snapshot store + real lock),
**R** = regression over existing Phase 40E–40G and Phase 37B/37C suites. All are backend
`pytest`. No network, no real Active Memory activation, hermetic temp-dir artifacts
(Phase 39B convention: `HIVEMIND_MIGRATION_IMPORT_PATH` /
`HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` overrides / injected paths so no developer
profile is touched).

| # | Case | Layer | Expected result |
| --- | --- | --- | --- |
| 1 | Approved candidate imports exactly once | S/I | one receipt, one `record_id` resolvable in the snapshot, idempotent on replay |
| 2 | Rejected candidate never mutates memory | S | `rejected_candidate`, zero records inserted |
| 3 | Deferred candidate never mutates memory | S | `deferred_candidate`, zero records inserted |
| 4 | Changed candidate bytes invalidate approval | S | `changed_digest`, fail closed, no insert |
| 5 | Changed assessment invalidates approval / requires renewed review | S | `changed_assessment`, fail closed |
| 6 | Duplicate request returns the **exact stored receipt** | S/I | same `receipt_id` + `record_id`, byte-identical receipt, no second record |
| 7 | Concurrent duplicate requests cannot create duplicate records | A/I | exclusive lock + CAS: exactly one record; loser → winner's receipt |
| 8 | Stale writer loses CAS | A | `revision_conflict`; stale write refused; last good ledger intact |
| 9 | Exclusive writer lock enforced; bounded timeout | A | second writer gets `lock_unavailable` within the acquisition budget; never concurrent mutation |
| 10 | Stale lock: conclusively-dead owner past threshold reclaimed; ambiguous owner refused | A | dead+stale → single reclaim; inconclusive/other-host → `stale_lock_ambiguous`, no reclaim |
| 11 | Distinct `import_attempt_id` per retry; stable idempotency key; attempt-sequence integrity | S/C | `attempt_sequence` 1,2,3… contiguous per key; gap/dup → `corrupt_ledger`; one stable key; one committed receipt |
| 12 | Canonical identity serialization + domain separation | C | idempotency/attempt/record/receipt ids stable, sorted-key UTF-8 canonical JSON, domain-tagged; cross-domain collisions impossible; no timestamps in identity |
| 13 | Provenance mapping populates the typed `migration_provenance` block | C/S | candidate/digest/assessment/decision/idempotency/attempt/evidence carried; `source_type = IMPORTED_DOCUMENT`; no Phase 37B model change |
| 14 | Duplicate `record_id` with identical content-identity reuses the record | S/I | already-inserted case: one record, second receipt referencing it |
| 15 | Non-identical content under the same `record_id` | S/I | `record_identity_collision`, fail closed |
| 16 | Receipt contract fields present; identity separated from temporal audit | C | all §B.3 fields; `receipt_id` stable across differing timestamps; `receipt_digest` verifies |
| 17 | Receipt references the exact resulting `record_id` | C/S | link resolves in the snapshot; forged/dangling link rejected |
| 18 | Receipt with missing linked attempt detected | A | `missing_linked_attempt`, fail closed |
| 19 | Receipt with missing linked memory record detected | A/I | `missing_linked_memory_record`, fail closed |
| 20 | Receipt integrity failure detected | A | `receipt_integrity_failure`, fail closed |
| 21 | Corrupt / internally inconsistent ledger detected | A | `corrupt_ledger`, fail closed, no silent repair |
| 22 | Partial write detected (not "recovered") at load | A | `partial_write_detected`; temp sibling ignored; last good file loads; no success claimed |
| 23 | Snapshot path + environment override honored | A | `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` wins; side-effect-free resolution |
| 24 | Initial startup load (cold start) | I | neither artifact present → both initialized at generation 0 under the lock |
| 25 | Missing or corrupt snapshot | A/I | `snapshot_missing` / `corrupt_active_memory_snapshot`, fail closed |
| 26 | Shared-generation mismatch | A/I | ledger and snapshot generations disagree → `generation_mismatch`, fail closed |
| 27 | Failure after in-memory insertion but before snapshot durability | I | no verified receipt; live mutation discarded; reload of last validated snapshot; attempt `failed` |
| 28 | Rollback/reload of live in-memory state | I | post-insert failure reloads durable snapshot into a fresh store; no retained uncommitted record |
| 29 | Quarantine when reload fails | I | `import_service_quarantined`; reviewed imports disabled until startup recovery |
| 30 | Interrupted snapshot temp write | A/I | destination untouched; discard live mutation; safe retry |
| 31 | Interrupted snapshot replacement | A/I | uncertain if `+1` may exist → recovery; else failed; never false success |
| 32 | Receipt persistence failure after snapshot success | I | `+1` snapshot + intent prove effect → recovery finalizes receipt (idempotent) |
| 33 | Uncertain commit — record present, no receipt → recovery finalizes | I | §I.7 writes receipt at snapshot generation, returns stored success, idempotent |
| 34 | Uncertain commit — record absent, no receipt → recovery fails safe | I | attempt marked `failed`, safe retry; no false success |
| 35 | Uncertain commit — durable state unreadable → typed fail-closed | I/A | `uncertain_commit_result`; restore last mutually valid generation per bounded policy; never reported as success |
| 36 | Uncertain recovery validates exact record equality, not `record_id` alone | I | recovery rejects a `record_id` match whose content-identity/provenance differs |
| 37 | No cross-store atomicity is claimed/relied on | I | interrupting between snapshot and receipt is recoverable via shared generation, not silently committed |
| 38 | Prohibited `INACTIVE → SUPERSEDED` behavior is never invoked | S/I | import path never calls `transition_lifecycle`; supersession expressed via `supersession_refs` only |
| 39 | `supersession_refs` behavior against the actual store | I | new record's `SUPERSEDES` link authored on the newer record; prior record stays `INACTIVE`; `SUPERSEDED_BY` derived, never stored |
| 40 | Deterministic record supersession ordering | S/C | total order over (decision_timestamp, record_id); `attempt_sequence` not used |
| 41 | Record supersession tie rejected | S | `supersession_tie`, fail closed |
| 42 | Record supersession cycle rejected | S | `supersession_cycle`, fail closed, nothing persisted |
| 43 | Independent review-decision supersession via `supersedes_decision_id` | S/C | decision lineage ordered by explicit predecessor link; `attempt_sequence` not used |
| 44 | Review lineage: multiple heads, ties, missing predecessors, cycles | S | `supersession_tie` / `incomplete_review_provenance` / `supersession_cycle`, fail closed |
| 45 | Superseded approval cannot authorize import | S | `stale_approval`, no insert |
| 46 | Missing reviewer fails validation | C | decision cannot be constructed |
| 47 | Missing reason fails validation | C | decision cannot be constructed |
| 48 | Missing evidence fails validation | C | decision cannot be constructed (≥1 required) |
| 49 | Missing timestamp fails validation | C | decision cannot be constructed |
| 50 | Contradictory review evidence fails closed | S | `contradictory_evidence`, no insert |
| 51 | Conflicting replay (same digest, different assessment/decision, materially different attempt) | S | `conflicting_replay`, fail closed |
| 52 | Approval boolean alone does not authorize | S | a decision reduced to `status` only fails validation/preconditions |
| 53 | Imported record standing is INACTIVE + UNVERIFIED | I | inserted record carries the conservative standing; never auto-active |
| 54 | Diagnostics leak no path/secret/raw content | S | planted sensitive values never appear in any diagnostic |
| 55 | Full cross-store startup and recovery integration | I | startup loads+validates both stores under the lock; recovery resolves the uncertain window end-to-end |
| 56 | Existing Active Memory store contracts remain regression-clean | R | Phase 37B/37C suites unchanged and passing; `MemoryStore` seam unmodified in behavior |
| 57 | Existing Phase 40E–40G contracts remain regression-clean | R | 40E/40F/40G suites unchanged and passing |
| 58 | Full backend suite passes during implementation | R | green (baseline count + new Phase 40H tests) |

The full backend suite MUST pass during the implementation phase; these cases are
authored then, not now.

---

## L. Implementation map (mandatory, smallest credible; not implemented in this phase)

Tightly bounded and independently auditable. This is a **three-store** integration
(ledger + Active Memory snapshot + in-memory Active Memory store), so the map names the
**existing modules Phase 40H must exercise or integrate with**, not only net-new files.
The map is **mandatory** — the `ActiveMemorySnapshotStore` and the lock protocol are
committed components, not conditional fallbacks. Nothing below is written during
planning.

| File | New/Mod | Responsibility | Preserves / integrates |
| --- | --- | --- | --- |
| `apps/backend/app/models/memory_migration_import.py` | New | `memory-migration-import.v1` **workflow** contracts only: review decision (with `supersedes_decision_id`), evidence reference, import attempt (`attempt_sequence`, `intent_state`, observed `commit_generation`), receipt (§B.3, incl. `commit_generation`, `verification_status`, temporal audit fields, `receipt_digest`), `MigrationProvenance` sub-model (§F.3), `commit_generation`/`ledger_revision` types, canonical identity helpers + domain tags (§H), closed diagnostic taxonomy (§J), ledger + snapshot-envelope documents. `extra="forbid"`, pinned versions. **Does not redefine `MemoryRecord`.** | Phase 40E/40F/40G contracts; **references** (not copies of) `MemoryRecord.record_id` |
| `apps/backend/app/services/memory_migration_import_store.py` | New | Durable **ledger** adapter: versioned-JSON ledger, OS-path resolution + `HIVEMIND_MIGRATION_IMPORT_PATH` override, bounded load with typed failures, atomic append-with-CAS write (§I.5), `commit_generation` on the ledger doc (§I.3), load-time integrity **detection** scan (§I.8). | Phase 39B `RepositoryWorkspaceConfigService` persistence pattern (path resolution, atomic temp-swap, typed errors) |
| `apps/backend/app/services/active_memory_snapshot_store.py` | New (**mandatory**) | Durable **Active Memory snapshot** owner (§A.4): serialize/load/validate/atomic-replace over the existing `InMemoryActiveMemoryStore.serialize()`/`restore()`; `active-memory-snapshot.v1` envelope carrying `commit_generation`; path resolution + `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` override; startup load; typed failures (`snapshot_missing`, `corrupt_active_memory_snapshot`, `generation_mismatch`, `persistence_failure`, `partial_write_detected`). **Wraps, never rewrites, the store; never re-homes records into the ledger.** | Phase 37C serialize/restore boundary; Phase 39B atomic-write pattern |
| `apps/backend/app/services/migration_import_lock.py` | New | The **single** exclusive lock-file protocol (§I.4): `os.O_CREAT | os.O_EXCL | os.O_WRONLY` atomic create, owner metadata (`owner_pid`, `created_at`, `operation_identity` = idempotency key, host/boot), bounded acquire (timeout/poll/max-attempts), conservative stale detection with positive PID-absence validation (stdlib only), ownership-checked release in success/failure/exception. | Standard library only; no new dependency |
| `apps/backend/app/services/memory_migration_import.py` | New | The **import coordinator** (§A.2): owns the lock lifecycle; the ordered protocol (§E) — record review decision, allocate attempt sequence, persist intent, insert via the Active Memory seam (§F.2), persist snapshot at `+1` (§A.4), commit receipt at matching generation, reload-and-verify linkage; idempotent replay lookup (§G); **post-insert failure + quarantine** (§I.6); **uncertain-commit recovery** (§I.7); startup load+validate of both stores under the lock (§I.3). | The §C–§J rules; **depends on** the existing `MemoryStore` protocol; Phase 40F candidate + Phase 40G report contracts reused unchanged |
| `apps/backend/app/services/migration_import_paths.py` *(or fold into the store modules)* | New (thin) | Side-effect-free **configuration/path resolution** shared by the ledger and snapshot stores (OS-appropriate base + env overrides), reusing the Phase 39B resolver shape. | Phase 39B `resolve_workspace_config_path` pattern |
| `apps/backend/app/store/active_memory_store.py` | **Existing — integration touchpoint** | The **authoritative Active Memory store**. Phase 40H uses its existing `insert`, `DuplicateRecordError`, and `serialize`/`restore` seam **unchanged**, and **does not call `transition_lifecycle` in the import path** (§F.2). No change to this file. | Phase 37B/37C behavior; `MemoryRecord` identity/immutability/lifecycle table unchanged |
| `apps/backend/app/models/active_memory.py` | **Existing — read-only dependency** | Source of `MemoryRecord`, `LifecycleState.INACTIVE`, `VerificationState.UNVERIFIED`, `MemorySourceType.IMPORTED_DOCUMENT`, `SupersessionReference`/`SupersessionKind.SUPERSEDES`, and `metadata`. Phase 40H **reuses** these; **no enum, field, or contract change is required or proposed** (§F.3). | Phase 37B contract, unchanged |
| `apps/backend/app/services/__init__.py` / `app/models/__init__.py` | **Existing — possible touch** | **Any required package exports** for the new modules, if and only if the package uses explicit `__init__` re-exports; additive only. | Existing export convention |
| `apps/backend/tests/test_memory_migration_import_contracts.py` | New | Contract tests: §K rows 11–13, 16, 40, 43, 46–49, 52; identity derivation + domain separation; immutability. | — |
| `apps/backend/tests/test_memory_migration_import_store.py` | New | Ledger adapter tests: §K rows 8, 11, 18, 21, 22; CAS, atomicity, integrity **detection**, typed failures. | — |
| `apps/backend/tests/test_active_memory_snapshot_store.py` | New | Snapshot store tests: §K rows 22–26, 30, 31; path/env override, startup load, missing/corrupt snapshot, generation stamping, interrupted writes. | Exercises, does not modify, the Active Memory store |
| `apps/backend/tests/test_migration_import_lock.py` | New | Locking tests: §K rows 9, 10; O_EXCL exclusivity, bounded timeout, stale/ambiguous ownership, release paths. | Standard library only |
| `apps/backend/tests/test_memory_migration_import_service.py` | New | Coordinator tests: §K rows 1–6, 14, 15, 17, 40–45, 50–52, 54 over temp ledger + temp snapshot + injected store. | — |
| `apps/backend/tests/test_memory_migration_import_integration.py` | New | Cross-store integration/recovery: §K rows 1, 6, 7, 19, 24, 27–39, 53, 55 over the coordinator + real `InMemoryActiveMemoryStore` + real snapshot store + real lock. | Exercises, does not modify, the Active Memory store |
| `docs/planning/phase-40h-reviewed-persistence-verified-import-planning.md` | Mod (this doc) | The plan. | — |

Regression (§K 56–58) runs the existing Phase 37B/37C and 40E/40F/40G suites and the
full backend suite; **no existing test file is edited**, and the Active Memory store's
behavior is asserted unchanged. Net-new surface is **five source modules** (models,
ledger store, snapshot store, lock, coordinator; plus an optional thin path helper) and
**five test files**, with two existing Active Memory modules as named integration
touchpoints — the smallest credible integration for a human-gated, crash-recoverable,
two-artifact reviewed import, and small enough for one independent audit.

---

## M. API boundary

**Decision: no new public API in Phase 40H.** Default upheld.

Reviewed import is a durable, security-sensitive local operation; the smallest
foundation is a coordinator + two persistence adapters + a lock helper integrating the
existing Active Memory store, exercised by tests, matching how Phase 37C (store) and
Phase 39B (config service) landed before any endpoint. An HTTP surface would add
request-validation, auth-posture, and error-mapping concerns that are out of scope for
establishing the mutation boundary and are unnecessary to prove the contract.

If a later phase believes an endpoint is necessary (e.g., a review/approval workflow
UI), it must: (1) justify it separately, (2) define a narrow thin-router boundary that
only validates a request contract and maps typed results to safe responses (no
persistence/digest/lifecycle logic in the router), and (3) be marked as **requiring
explicit approval before implementation**. No endpoint is created in this planning
phase, and none is created by the proposed Phase 40H implementation above.

---

## N. Deferred work (explicitly out of scope)

Explicitly deferred and **not** part of Phase 40H:

- Frontend work of any kind (no review/approval/import UI).
- Grounded Synthesis Producer implementation (Phase 40I).
- Automatic approval or any derived/inferred approval.
- LLM or semantic truth adjudication.
- Active-state calculation / promotion of imported records to `active` /
  `human_confirmed`, and any **lifecycle retirement** of imported records (remains
  deferred Active Memory work).
- Any change to the Active Memory record contract, enums, identity rule, or **lifecycle
  transition table** (Phase 40H reuses them unchanged; it never adds an
  `INACTIVE → SUPERSEDED` edge and never calls `transition_lifecycle` in the import
  path).
- Promotion of migration provenance from the typed `metadata.migration_provenance`
  block to first-class typed `MemoryRecord` fields (a named, separate Phase 37B contract
  change if a future audit requires it, §F.3).
- Knowledge Graph mutation.
- Source Registry mutation.
- Obsidian mutation / write-back.
- Repository Observer mutation.
- Broad persistence replacement or migrating the existing Active Memory store to a new
  durable medium (beyond the thin, explicitly-scoped `ActiveMemorySnapshotStore` of
  §A.4, which wraps the existing serialize/restore boundary).
- **PostgreSQL / any server database migration.**
- Phase 36K (paused and untouched).
- Operational deployment, service install, scheduled tasks, background daemons.
- Screenshots and demo evidence.
- A public API / endpoint (see §M).
- Anything beyond the smallest reviewed-import foundation.

---

## Acceptance-criteria coverage

| Criterion | Section |
| --- | --- |
| Active Memory store remains authoritative | A.1 |
| Import coordinator is an orchestration boundary, not a competing store | A.2 |
| MigrationImportStore owns workflow records only | A.3 |
| Mandatory durable `ActiveMemorySnapshotStore` (module, interface, config, startup, integrity, failures) | A.4 |
| Authorized Active-Memory-insertion seam; `transition_lifecycle` not called | F.2 |
| No duplication/wrapping of authoritative records | A.1, A.4, B, F.2 |
| Imported records INACTIVE; no `INACTIVE → SUPERSEDED`; supersession via `supersession_refs` | D.4, D.7, F.1, F.2 |
| Candidate-to-`MemoryRecord` provenance mapping (named fields, no unspecified metadata) | F.3 |
| Receipt references exact `record_id` + full receipt contract | B.3, E, I.2 |
| Shared persisted `commit_generation` (init/validate/increment/mismatch; verified only on agreement) | I.3 |
| No false cross-store atomicity; recoverable protocol | I.1–I.3 |
| One coordinator; one concrete Windows-compatible dependency-free lock protocol; stale/ambiguous rules; release paths | I.4 |
| Concurrency: exclusive writer + persisted-revision/CAS | I.4, I.5 |
| Ordered intent/effect/receipt protocol incl. reload-and-verify | E, I.2 |
| Post-insert failure rollback + quarantine (all failure modes) | I.6 |
| Uncertain-commit recovery with exact record equality, not `record_id` alone | I.7 |
| Canonical identity derivation for all four ids (domains, membership, no timestamps) | H |
| Stable idempotency key + distinct monotonic attempt ids (retries only) | G.1, G.2, H.1, H.2 |
| Review-decision supersession independent of attempt ordering | C, D.7, G.2 |
| Supersession ordering / tie / cycle / missing predecessor / changed-byte / changed-assessment | D.7 |
| Normalized diagnostic taxonomy incl. all required codes | J |
| Partial-write detection separated from recovery | I.7, I.8 |
| Expanded test matrix | K |
| Mandatory, bounded, auditable implementation map incl. existing modules + tests | L |
| Fail-closed behavior | E, I, J |
| Explicit deferred work | N |
| Explicit API boundary | M |

Phase 36K remains **paused and untouched** by this plan. This document persists
nothing, imports nothing, and implements no runtime; it defines the Phase 40H
foundation only, and that foundation is **proposed and pending a further independent
audit** before any implementation is unlocked.
