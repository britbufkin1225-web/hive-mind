# Phase 40H — Reviewed Persistence + Verified Import (Planning)

**Status:** Planning-only. No runtime implementation exists. This document defines
the foundation; nothing here is built.
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
the two-store recoverable transaction protocol, the concurrency (exclusive-writer +
persisted-revision/CAS) protocol, idempotency/replay with a monotonic attempt
sequence, uncertain-commit recovery, the typed diagnostics, the test matrix, the
integration map, the API decision, and the deferred work. It implements none of them.

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
   review decision, the import attempt, and the exact resulting
   `MemoryRecord.record_id`.

"Verified import" proves the pipeline was honored end-to-end and byte-consistent.
It does **not** prove the imported statement is factually true — the resulting
Active Memory record is imported evidence, never adjudicated truth (see §E.1).

---

## A. State-ownership contract

Phase 40H spans **two distinct stores with two distinct owners**, and the plan is
explicit about which owns what. Conflating them is the specific failure this section
exists to prevent.

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
that store's existing public seam (§F.2).

### A.2 The Reviewed Migration Import Service is an orchestration boundary

A single new backend service, the **Reviewed Migration Import Service** (working
name `MemoryMigrationImportService`), is **not** an Active Memory store. It is an
**orchestration boundary** that coordinates two stores to perform one reviewed
import:

- it records review decisions, import attempts, and receipts in the durable
  migration ledger (§A.3);
- it constructs the authorized `MemoryRecord` and inserts it into the **existing
  Active Memory store** through that store's own boundary (§F.2);
- it answers idempotent replay lookups and drives uncertain-commit recovery (§H).

It owns the *workflow and the orchestration*, never the Active Memory records
themselves. No router, parser, projector, assessor, or frontend may write
migration-import workflow state; they call this service or they read nothing.

### A.3 MigrationImportStore owns durable migration-workflow records only

Durable migration-workflow state lives behind a **persistence adapter** (working
name `MigrationImportStore`) that is the only component performing filesystem I/O for
this feature. **It owns exactly four kinds of durable record and nothing else:**

1. **review decisions** (who approved/rejected/deferred which exact reviewed input);
2. **import attempts** (each retry a distinct attempt, §G);
3. **import receipts** (the deterministic link set, referencing — never copying —
   the resulting `MemoryRecord.record_id`);
4. **idempotency and recovery metadata** (the stable idempotency key → outcome map,
   the persisted ledger revision, and per-attempt intent/commit markers used by
   recovery, §H).

It stores **references** to Active Memory records (a `record_id` plus the version
semantics described in §B), never a duplicate of the record's content. The service
depends on the adapter's typed interface, never on `open`, `json`, or `os.replace`
directly. This mirrors the Phase 40F parser/projector split (all I/O behind one seam)
and the Phase 37 store/service split.

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

Phase 40H's durable state is an **append-oriented import ledger** rather than a
mutable registry (see §D.6), so the store adds two capabilities the Phase 39B config
service does not need, both additive reuses of the established pattern rather than a
new persistence technology: a **persisted monotonic ledger revision with
compare-and-swap** (§H.5) and an **exclusive writer lock** (§H.6). Atomic file
replacement alone is explicitly **insufficient** for this feature's concurrency
guarantee (§H.6) and is not relied on as if it were.

> **No speculative PostgreSQL rewrite.** A relational database is explicitly *not*
> proposed. Hive|Mind is local-first and single-user (roadmap "Current
> Limitations"); the Active Memory store itself is still
> in-memory-with-serialize/restore. Introducing a server database here would be a
> large, unaudited dependency far beyond the smallest reviewed-import foundation. The
> local versioned-JSON ledger is sufficient for a single operator's own migration
> history; if future evidence ever shows it insufficient, that is a separate,
> justified decision — not part of this phase.

### A.4 Router thinness and non-mutating layers

- **Routers stay thin.** Phase 40H proposes **no** router by default (see §L). If a
  future, separately-approved phase adds one, it does only transport: validate a
  request contract, call the service, map typed results to safe responses. It holds
  no persistence, digest, or lifecycle logic.
- **Only the Reviewed Migration Import Service creates an Active Memory record from a
  migration candidate**, and it does so exclusively through the Active Memory store's
  own insertion seam (§F.2). That is the single migration→Active-Memory mutation
  boundary (§F).
- **Parsing (40F), projection (40F), assessment (40G), dry-run, and inspection stay
  non-mutating.** They are pure/read-only today and Phase 40H changes none of them.
  Phase 40H depends on their outputs and never edits their modules.

---

## B. Durable record types and relationships

All migration-workflow records are versioned (`memory-migration-import.v1`),
`extra="forbid"`, and use the repository's canonical-JSON + SHA-256 identity
convention (`derive_migration_id`, reused from Phase 40E/40F/40G — no new identity
scheme). Identifiers are pure functions of typed content; nothing reads a clock,
randomness, or process state to form an identity. Caller-supplied timestamps follow
the Phase 37E/40F convention (the service records time it is given; it does not read
the wall clock to fabricate provenance).

**Ownership note (critical):** the first three rows describe *references into stores
Phase 40H does not own* (Phase 40F candidate, Phase 40G report, Phase 37C Active
Memory store). The migration ledger stores only their **identities**, never copies.
The **resulting Active Memory record is owned entirely by the Active Memory store**;
the ledger holds only its `record_id` and version-linkage metadata.

| Record | Identity | Key fields | Mutability / ownership |
| --- | --- | --- | --- |
| **Migration candidate reference** | `candidate_id` (Phase 40F, reused unchanged) | `candidate_id`, `content_digest`, `provenance` (bundle/artifact fingerprints, observed digest), assessed-set membership | Immutable; a *reference*, not a copy of candidate bytes; owned by Phase 40F output |
| **Candidate byte digest** | value of `content_digest` | the Phase 40F SHA-256 over candidate content; the observed artifact digest from `MigrationCandidateProvenance` | Immutable reference value |
| **Assessment reference** | `report_id` (Phase 40G) + `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION` | `report_id`, ruleset version, `review_readiness` verdict | Immutable; owned by Phase 40G output |
| **Review decision** | `derive_migration_id` over its own canonical fields (`review_decision_id`) | reviewer id, decision timestamp, status, reason, notes, candidate id + digest, assessment id + version, evidence references, optional `supersedes_decision_id` | Immutable once recorded (append-only; a superseding decision is a new record, §C/§D.6); **owned by the migration ledger** |
| **Review evidence reference** | reference tuple `(kind, ref_id)` | typed pointer to the assessment report, the dry-run finding(s), and/or the candidate provenance the reviewer relied on | Immutable; owned by the migration ledger |
| **Import attempt** | `derive_migration_id(idempotency_key, attempt_sequence)` (`import_attempt_id`) | `idempotency_key`, `attempt_sequence` (deterministic monotonic int), referenced `review_decision_id`, candidate id + digest, assessment id + version, `intent_state` (`intended`/`committed`/`failed`), planned `target_record_id`, attempt timestamp | Append-only; each retry is a **distinct** attempt id (§G); owned by the migration ledger |
| **Verified import receipt** | `derive_migration_id` over the linked identities (`receipt_id`) | `idempotency_key`, `candidate_id`, `content_digest`, assessment id + version, `review_decision_id`, `import_attempt_id`, the resulting `record_id`, `record_supersedes` (0..1 prior `record_id`) | Immutable; created only at verified commit; **owned by the migration ledger** |
| **Resulting Active Memory record** | `record_id` (caller-supplied to the Active Memory store; here `derive_migration_id` over projected content + provenance) | the `MemoryRecord` itself — lifecycle/verification standing, claim, provenance, supersession refs | **Owned exclusively by the Active Memory store.** The ledger stores only its `record_id`; it is never copied, wrapped, or shadowed in the ledger (§A.1) |
| **Ledger revision** | monotonic integer `ledger_revision` | the persisted CAS token guarding every write (§H.5) | Monotone, advanced only under the exclusive writer lock |

### B.1 Ownership and cardinality

- One **candidate** may be referenced by many **review decisions** over time (a
  deferred decision later superseded by an approval), but at most **one
  non-superseded approved decision** is valid for a given `(candidate_id,
  content_digest, assessment_id, assessment_version)` tuple at any time (§D.6, §D.7).
- One valid **approved review decision** authorizes at most **one verified import**
  for its exact reviewed input, producing exactly **one receipt** and referencing
  exactly **one resulting `record_id`** (§G idempotency).
- One **import attempt** references exactly one **review decision** and yields zero
  or one **receipt** (zero on failure, one on verified commit). Multiple attempts may
  share one idempotency key (retries), but each has a distinct `import_attempt_id`.
- One **receipt** references exactly one resulting `record_id`. That `record_id` must
  resolve to an existing record in the **Active Memory store**. A receipt whose
  `record_id` does not resolve is a detected corruption (`missing_linked_memory_record`,
  §I), never a valid state. This cross-store linkage is the invariant §H protects.

### B.2 Uniqueness, foreign keys, timestamps, version semantics

- **Uniqueness constraints (enforced by the ledger, adapter-level):**
  `review_decision_id`, `import_attempt_id`, and `receipt_id` are each unique. The
  **idempotency key** (§G) maps to at most **one** committed receipt — a duplicate
  valid request resolves to the existing receipt, never a new record.
- **Foreign-key equivalents:** every import attempt names an existing
  `review_decision_id`; every receipt names an existing `import_attempt_id`,
  `review_decision_id`, and a `record_id` that exists in the Active Memory store;
  every review decision names an existing `candidate_id` + `content_digest` and
  `report_id` + version. A dangling *intra-ledger* reference fails closed as
  `missing_linked_attempt` / `incomplete_provenance`; a dangling *cross-store*
  reference (receipt → absent `record_id`) fails closed as
  `missing_linked_memory_record` (§I).
- **Timestamps:** `decision_timestamp` and `attempt_timestamp` are caller-supplied
  and immutable once recorded. There is no server-clock read; determinism and
  auditability come from the caller stating time, exactly as Phase 37E/40F do.
- **Version semantics (reuse, not reinvention):** Active Memory records have no
  numeric version field. The Active Memory store's existing model *is* the version
  semantics — a stable `record_id` is one immutable version, and a *changed* import
  (new digest or new assessment) produces a **new** `record_id` that **supersedes**
  the prior one via the store's existing `supersession_refs`, never an in-place edit
  (§D.7). The receipt records `record_id` and, when the import supersedes a prior
  import of the same logical candidate, the prior `record_id` in `record_supersedes`.
  Phase 40H introduces **no** competing version scheme for Active Memory.
- **Immutable vs mutable:** every ledger record above is immutable once written. The
  *ledger* grows by appending new records and advancing `ledger_revision`; a lifecycle
  "transition" is a new controlled record referencing the prior one (§D.6), never an
  in-place edit. The only field that could be described as "changing" is a decision's
  or attempt's *effective* status, and that is expressed by a newer superseding
  record, not by mutation.

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
| `decision_timestamp` | yes | Caller-supplied instant the decision was made. |
| `status` | yes | Closed enum: `approved` / `rejected` / `deferred`. No other value is representable. |
| `reason` | yes | Non-empty, bounded free text stating *why*. An approval with no reason fails validation. |
| `notes` | optional | Additional bounded context. |
| `candidate_id` | yes | The exact Phase 40F candidate the decision is about. |
| `content_digest` | yes | The exact candidate byte digest the decision was made against (binds the decision to specific bytes). |
| `assessment_report_id` | yes | The exact Phase 40G report id reviewed. |
| `assessment_version` | yes | The Phase 40G ruleset version reviewed. |
| `evidence_references` | yes, ≥1 | Typed references to the assessment report, dry-run findings, and/or candidate provenance the reviewer relied on. |
| `supersedes_decision_id` | optional | The prior decision this one supersedes for the same logical candidate line, when the reviewer is explicitly renewing review (§D.7). |

> A plain `approved = true` field **never independently authorizes mutation.** The
> `status` enum only *names* the decision; authority to import requires the whole
> record — reviewer, timestamp, reason, the exact candidate digest, the exact
> assessment identity/version, and evidence — and that whole record must still be
> valid, unchanged, and non-contradictory at import time (§E). The import path
> re-derives the decision id from its fields and rejects a record whose stored id
> disagrees, so a forged or edited decision cannot be presented.

Contradictory evidence (e.g., an `approved` decision whose referenced assessment
verdict is `blocked`, or whose evidence points at a different candidate) is a
fail-closed condition (`contradictory_evidence`, §I), not a soft warning.

---

## D. Persistence lifecycle

### D.1 States

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
             uncertain_commit  → (recovery, §H.7) →  import_verified | import_failed
```

### D.2 State meanings

- **candidate_received** — a Phase 40F candidate exists and is referenced.
- **assessment_completed** — a Phase 40G report exists over the candidate's set.
- **awaiting_review** — no valid non-superseded decision yet exists for the exact
  `(candidate_id, digest, assessment_id, version)` tuple.
- **approved / rejected / deferred** — a review decision of that status is the
  current effective decision for the tuple.
- **import_intended** — a distinct import attempt has durably recorded its *intent*
  (planned `target_record_id`) but the receipt is not yet committed. This is the
  window that makes uncertain commits detectable (§H).
- **import_verified** — a receipt exists and its `record_id` resolves to an existing
  Active Memory record (the only success terminal).
- **import_failed** — an attempt did not commit; no receipt exists and the planned
  record is confirmed absent from the Active Memory store (safe to retry).
- **uncertain_commit** — an intent exists, no receipt exists, and whether the Active
  Memory record durably persisted cannot yet be determined. Not a success and not a
  safe retry until recovery resolves it (§H.7).

### D.3 Terminal vs non-terminal

- **Terminal:** `import_verified` (success), `rejected` (\*terminal for that exact
  reviewed input; a *different* input — new digest or new assessment — is a fresh
  `awaiting_review`, not a re-opening of the rejected one).
- **Non-terminal:** `awaiting_review`, `deferred`, `import_intended`,
  `import_failed`, `uncertain_commit` (resolved only by recovery).

### D.4 Prohibited transitions

- `awaiting_review`/`deferred`/`rejected` → `import_intended` **without** a valid
  `approved` decision. Forbidden.
- `import_failed`/`uncertain_commit` → `import_verified` **without** a fresh, fully
  re-validated attempt or a successful recovery finalize (§H.7). A failed or
  uncertain attempt never "upgrades" to verified by assertion.
- Any state → `import_verified` **without** the receipt's `record_id` resolving to an
  existing Active Memory record (§H). Forbidden by construction.
- Editing a recorded decision's `status`, `reason`, `reviewer_id`, `digest`, or
  assessment binding in place. Forbidden — records are immutable (§B, §D.6).
- `approved` for tuple *X* authorizing import of tuple *Y* (different candidate,
  digest, assessment, or version). Forbidden — the import path binds to the exact
  tuple.
- Mutating the Active Memory record in place to "re-import." Forbidden — a changed
  import is a new `record_id` superseding the old (§D.7), honoring the Active Memory
  store's immutability.

### D.5 Retry and stale-record rules

- **Retry:** after `import_failed`, a retry re-runs the full verified-import
  precondition set (§E) from scratch under a **new** `import_attempt_id` (§G). There
  is no shortcut path.
- **Stale record:** an `approved` decision whose candidate digest or assessment no
  longer matches the present candidate/assessment is **stale**; it is not deleted
  (history is preserved) but it fails the import preconditions and is reported
  (`stale_approval`, §I).

### D.6 Append-only vs updated

State transitions are **append-only through controlled records.** The ledger never
edits an existing record's field. A superseding decision is a *new* decision record
that references the one it supersedes; effective status is computed as the newest
non-superseded decision for a tuple, exactly as Phase 40D/40G compute readiness
rather than reading it off a record. Import attempts likewise append status/intent
records. This makes the whole history auditable and makes "who changed what, when"
answerable from the ledger alone.

### D.7 Supersession, renewed review, tie and cycle rules (deterministic)

- **Renewed review required when** the candidate digest changes (re-parsed bytes) or
  the assessment identity/version changes (re-assessed set, or ruleset version bump).
  The prior approval no longer matches the exact reviewed input and authorizes
  nothing; a new `awaiting_review` applies until a new decision is recorded. §E
  preconditions enforce this at import time — a mismatched approval is rejected as
  `stale_approval` / `changed_digest` / `changed_assessment`.
- **Changed-byte identity:** different bytes ⇒ different `content_digest` ⇒ a
  distinct reviewed input ⇒ a **new** resulting `record_id`. Same bytes ⇒ same digest
  ⇒ same reviewed input ⇒ idempotent (§G), never a second record.
- **Changed-assessment behavior:** a changed `report_id`/version invalidates the
  prior approval (renewed review) and, on re-approval, yields a new `record_id` that
  supersedes the prior import of the same logical candidate line.
- **Deterministic supersession ordering:** when a new import supersedes a prior one,
  the ordering of "which supersedes which" is a **total order** over
  `(decision_timestamp, attempt_sequence, record_id)` — caller-supplied time first,
  the monotonic attempt sequence next, and the content-derived `record_id` as the
  final, always-decisive tiebreak. No clock is read; ordering is fully determined by
  recorded fields.
- **Tie rejection:** a *tie* is two **distinct** records that would each become the
  active non-superseded head of the **same** logical candidate line with identical
  ordering keys through `attempt_sequence`. The `record_id` tiebreak resolves normal
  ordering, but a state that would leave **two** active heads for one line (ambiguous
  supersession) is rejected fail-closed as `supersession_tie` (§I) rather than
  silently picking one head.
- **Cycle rejection:** a proposed supersession whose `record_supersedes` /
  `supersedes_decision_id` links would close a cycle in the supersession graph (A
  supersedes B … supersedes A) is rejected fail-closed as `supersession_cycle` (§I).
  The graph is walked before any insert; a cycle is never persisted.

---

## E. Verified-import contract

The reviewed-import operation (`import_reviewed_candidate`) is the only path that
creates an Active Memory record from a candidate. Before creating anything, and
**under the exclusive writer lock (§H.6)**, it MUST, in order:

1. **Reload / revalidate the candidate.** Re-obtain the Phase 40F candidate (and,
   where the reviewed-import request carries the artifact reference, re-establish
   its provenance) rather than trusting a caller-passed blob.
2. **Recompute and compare the byte digest.** Recompute the candidate
   `content_digest` (Phase 40F SHA-256 convention) and compare it to the digest the
   review decision was made against. Mismatch → fail closed (`changed_digest`).
3. **Confirm the reviewed candidate has not changed.** The `candidate_id` and its
   provenance fingerprints must match the reviewed decision exactly
   (`stale_candidate` on mismatch).
4. **Confirm the reviewed assessment identity/version has not changed.** The Phase
   40G `report_id` and ruleset version must match the reviewed decision exactly
   (`changed_assessment` on mismatch).
5. **Confirm required review provenance exists** and is complete: reviewer id,
   timestamp, reason, candidate id + digest, assessment id + version, ≥1 evidence
   reference (`missing_review` / `incomplete_provenance`).
6. **Confirm the decision is `approved`** and is the current non-superseded decision
   for the tuple (`rejected_candidate` / `deferred_candidate` / `stale_approval`).
7. **Cross-check evidence for contradictions** (approval over a `blocked`
   assessment, evidence pointing at a different candidate, etc.) →
   `contradictory_evidence`.
8. **Resolve idempotency.** Compute the stable idempotency key (§G.1). If a committed
   receipt already exists for it, return that receipt and its `record_id` — no new
   record (`duplicate_replay`). If a *materially different* attempt collides on a
   related but non-identical input, fail closed (`conflicting_replay`).
9. **Validate supersession** (§D.7): reject `supersession_tie` / `supersession_cycle`
   before any write.
10. **Fail closed** for any missing, stale, contradictory, or mismatched evidence.
    The default is refusal; only a fully consistent set proceeds.
11. **Record the import intent durably.** Append a new `import_attempt` (distinct
    `import_attempt_id` via the monotonic `attempt_sequence`, §G) in `intent_state =
    intended` carrying the planned `target_record_id`, committed to the ledger via
    the CAS write (§H.5). This is the point after which an interruption is
    *recoverable* rather than ambiguous.
12. **Create the Active Memory record through the store's own seam only (§F.2)** and
    durably persist the Active Memory snapshot (§H.4). No other layer performs the
    write; the record is constructed under the Active Memory contract (INACTIVE,
    UNVERIFIED — §F.1).
13. **Produce a deterministic receipt** linking candidate, candidate digest,
    assessment, review decision, import attempt, and the exact resulting `record_id`
    (and `record_supersedes` when applicable), advance the attempt to `committed`,
    and commit it via the CAS write. **This ledger commit is the whole operation's
    commit point.**

### E.1 What "verified import" proves — and does not

**Proves:** the exact candidate bytes that were reviewed (digest-identical) were
imported; the exact assessment the reviewer saw still applies; a complete,
attributable, non-contradictory approval authorized it; and the resulting Active
Memory record (owned by the Active Memory store) is deterministically linked to all
of that by an immutable receipt referencing its exact `record_id`. Re-running the
same reviewed input yields the same receipt and the same `record_id`, and no second
record.

**Does not prove:** that the imported statement is factually **true**. Byte
integrity and review provenance are not truth adjudication. Accordingly the resulting
record is imported evidence with a conservative standing (§F.1): it is not
`human_confirmed` truth merely because a human approved *importing it*, and it is
never auto-activated into the trusted baseline by this phase. No LLM or automated
process decides truth anywhere in the path.

---

## F. Mutation authority

**One explicit mutation boundary:**

> Only the reviewed-import path (the Reviewed Migration Import Service's
> `import_reviewed_candidate`) creates an Active Memory record from a migration
> candidate, and it does so **exclusively through the Active Memory store's own
> insertion seam (§F.2)** — never by owning, copying, or bypassing that store.

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
chose to bring in, not an adjudicated active fact. It carries provenance back to the
candidate and (via the receipt) to the review decision. Both values are already
first-class members of the existing Active Memory enums, so no enum or contract
change is required. Promotion to `active` / `human_confirmed` (active-state
calculation, contradiction handling) remains the deferred Active Memory work already
named in the roadmap and is **not** part of Phase 40H. This preserves the Phase
40E/40F invariant that imported material is never verified truth automatically, while
still letting a human durably persist a reviewed candidate.

### F.2 The authorized Active-Memory-insertion seam

Phase 40H inserts through the **existing** Active Memory store boundary, not a new
one:

- **Seam:** `MemoryStore.insert(record: MemoryRecord) -> MemoryRecord` in
  [`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py).
  The service constructs a `MemoryRecord` with a deterministic caller-supplied
  `record_id = derive_migration_id(projected content + provenance)` and inserts it.
- **Duplicate semantics are reused, not reinvented.** The store already raises
  `DuplicateRecordError` on a colliding `record_id`. Because Phase 40H's `record_id`
  is a pure function of the reviewed content, a duplicate insert means *this exact
  record already exists* — the service treats it as the already-inserted case and
  reconciles against the ledger intent (§H.7) rather than creating anything new.
- **Supersession is reused, not reinvented.** A changed re-import writes a *new*
  record whose `supersession_refs` point at the prior `record_id`, exactly as the
  Active Memory store already models supersession; the prior record is transitioned
  via the store's existing `transition_lifecycle` table, never edited in place.
- **Durability handshake.** Because the Active Memory store is in-memory with
  caller-owned serialize/restore, the *effect* of the insert is made durable by
  serializing the store and writing that snapshot through the Active Memory snapshot
  persistence seam (§H.4) **before** the ledger receipt is committed. Phase 40H does
  **not** re-home Active Memory records into the ledger to fake durability.

---

## G. Idempotency and replay

### G.1 Stable idempotency key inputs

The stable idempotency key is `derive_migration_id` over exactly:
`candidate_id`, `content_digest`, `assessment_report_id`, `assessment_version`, and
`review_decision_id`. These five identify "this exact reviewed input." Nothing
time-based, random, or request-envelope-based enters the key. **The key is stable
across retries** — every retry of the same reviewed input computes the same key.

### G.2 Distinct attempt ids via a deterministic monotonic sequence

While the idempotency key is stable, **every attempt gets a distinct
`import_attempt_id`.** The id is `derive_migration_id(idempotency_key,
attempt_sequence)`, where `attempt_sequence` is a deterministic monotonic integer
assigned **under the exclusive writer lock** as `(count of prior attempts recorded in
the ledger for this idempotency key) + 1`. The first attempt is `1`, its retry is
`2`, and so on. Consequences:

- attempt ids never collide, so a retry is a first-class, separately-auditable ledger
  record rather than an overwrite of the prior attempt;
- the sequence is reconstructible purely from durable ledger state (no counter held
  only in memory), so recovery (§H.7) can compute the next sequence deterministically;
- the *receipt* is keyed by the stable idempotency key (at most one committed), so
  many distinct attempts still yield at most one Active Memory record.

### G.3 Behavior

- **Duplicate valid request** (same key, prior committed receipt): return the
  **existing receipt** and its existing `record_id`. No new attempt commits a second
  record. Idempotent replay is a lookup, not a re-import (`duplicate_replay`).
- **Deterministic receipt lookup:** the committed receipt is addressable by the
  idempotency key, so a replay is answered from the ledger deterministically.
- **Successful replay:** returns the same `receipt_id` and same `record_id` as the
  original — byte-identical result.
- **Retry after failure:** if no committed receipt exists for the key, a retry
  acquires a **new** `import_attempt_id` (§G.2), re-runs §E fully, and may create the
  (first and only) receipt.
- **Concurrency:** two concurrent requests for the same key cannot both create a
  record. The exclusive writer lock (§H.6) serializes them and the persisted-revision
  CAS (§H.5) rejects a stale writer (`revision_conflict`); one wins and the other
  resolves to the winner's receipt (`duplicate_replay`). No lost update, no double
  record.
- **Conflicting replay detection:** the *same* candidate digest presented under a
  *different* assessment or a *different* review decision is **not** the same key —
  it is a distinct reviewed input requiring its own approval, and if it collides with
  an existing but materially different attempt it is reported (`conflicting_replay`),
  never silently merged.

> Approved candidates import **exactly once** for the same reviewed input; duplicate
> valid requests return the same deterministic result rather than creating another
> Active Memory record.

---

## H. Atomicity, concurrency, and recovery

This section is written to the ruling's hard constraint: **there is no single atomic
commit spanning the durable JSON ledger and the in-memory-with-serialize Active
Memory store.** The plan does not pretend otherwise. Instead it defines a *recoverable
two-store transaction protocol* whose durable commit point is the ledger receipt, plus
a concrete concurrency mechanism and an explicit recovery routine.

### H.1 Why cross-store atomicity is not claimed

The migration ledger is a durable versioned-JSON file (§A.3). The Active Memory store
is **in-memory**, and its durability is caller-owned via `serialize()`/`restore()`
(Phase 37C); **no durable Active Memory snapshot owner exists today** (§H.4). Two
independent durability domains cannot be committed by one `os.replace`. Any claim of a
single atomic swap covering "attempt + memory record + receipt" would be false. Phase
40H therefore uses **ordering + a durable intent + recovery**, not fictional
atomicity.

### H.2 Transaction boundary and commit point

The import of one candidate is a *logical* transaction across two stores, ordered so
that the durable ledger is the authoritative record of the outcome:

1. durably record the **intent** (`import_attempt`, `intent_state = intended`, planned
   `target_record_id`) via the CAS write (§H.5);
2. insert the record into the Active Memory store (§F.2) and durably persist the
   Active Memory snapshot (§H.4);
3. durably record the **receipt** and advance the attempt to `committed` via the CAS
   write.

**The commit point of the whole operation is step 3 — the durable receipt.** A
receipt exists only after step 2's snapshot durably reflects the record, so *a
committed receipt implies a durable record*. The converse gap (a durable record with
no receipt) is exactly the recoverable window §H.7 resolves.

### H.3 Ordering to make a false success impossible

The receipt is written **after** the Active Memory snapshot is durable, never before.
There is therefore no window in which a durable, committed receipt exists without its
durable Active Memory record. The only interruption windows are *before* the receipt,
which resolve to "not verified" (fail closed) until recovery proves otherwise — never
to a false success.

### H.4 Active Memory snapshot persistence seam (explicit prerequisite)

Because durable import requires the inserted record to survive a crash, the *effect*
must be persisted, and the Active Memory store does not persist itself today. Phase
40H makes this an **explicit, named seam** rather than an assumed capability:

- the service serializes the Active Memory store (`serialize()`, already provided) and
  writes the snapshot through an **Active Memory snapshot persistence seam** using the
  same atomic temp-swap discipline (§A.3);
- if no durable Active Memory snapshot owner exists at implementation time, defining
  this durable-snapshot write is a **prerequisite integration point of Phase 40H**
  (listed in §K), not a silent assumption. It is a thin, additive durable-write seam
  over the existing `serialize()`/`restore()` boundary — **not** a rewrite of the
  Active Memory store and **not** a re-homing of records into the ledger.

This is the ruling's "explicitly revise the persistence boundary" applied: the plan
names the missing durable seam instead of hiding a cross-store atomicity claim.

### H.5 Persisted revision + compare-and-swap

Every ledger write is guarded by a persisted monotonic `ledger_revision`:

- a writer reads the current revision `R` (from disk, under the lock);
- it stages the next document with `R+1`;
- immediately before `os.replace`, it re-reads the on-disk revision and proceeds only
  if it is still `R`; otherwise it aborts with `revision_conflict` (§I).

Atomic replacement alone is **insufficient** because two writers could each read `R`,
each stage `R+1`, and the later replace would clobber the earlier without either
noticing. CAS on the persisted revision detects that lost-update race and refuses it.

### H.6 Exclusive writer + concrete mechanism

CAS is defense-in-depth; the **primary** mutual-exclusion is a concrete
**exclusive-writer lock**:

- a single-writer lock is acquired for the whole `import_reviewed_candidate`
  transaction and for recovery, via an OS exclusive-create lockfile (`O_EXCL` /
  `msvcrt.locking` on Windows, `fcntl.flock` on POSIX; a small cross-platform helper
  in the adapter), holding the current owner's `import_attempt_id`, released in a
  `finally`;
- a second writer fails fast with `writer_locked` (or, by policy, waits) rather than
  proceeding concurrently;
- readers (idempotent replay lookup, inspection) do not take the writer lock and never
  mutate.

Exclusive writer + persisted-revision CAS together give a concrete concurrency
guarantee; **atomic file replacement alone is explicitly not treated as sufficient.**

### H.7 Uncertain-commit recovery (explicit routine)

Recovery is an **explicit operation**, not a load-time side effect. When an intent
exists without a committed receipt (`uncertain_commit`), recovery:

1. **reacquires the exclusive writer lock** (§H.6);
2. **reloads durable state** — the ledger and the durable Active Memory snapshot;
3. **inspects the idempotency key and any receipt** for the intent's key;
4. **validates linkage**:
   - if a committed **receipt exists** and its `record_id` resolves in the Active
     Memory snapshot → return the **stored result** (idempotent success);
   - if **no receipt** but the planned `target_record_id` **is present** and its
     provenance links back to this intent → **finalize**: write the receipt, advance
     the attempt to `committed` (idempotent completion), return success;
   - if **no receipt** and the planned record **is absent** → the effect never became
     durable → mark the attempt `failed`; the input is safe to retry under a new
     attempt id;
   - if durable state cannot be read or is internally inconsistent (snapshot
     unavailable, revision unreadable) → return a typed fail-closed
     `uncertain_commit_result` (§I); **never guess a success.**

### H.8 Partial-write **detection** (separate from recovery)

Detection is strictly separated from the recovery *action*:

- a crash mid-ledger-write leaves only an orphan temp sibling (never the destination);
  load ignores temp siblings and loads the last good ledger;
- **load-time integrity scan (detection only):** every receipt must reference an
  existing `import_attempt` and a `record_id`, and `ledger_revision` must be
  self-consistent. Violations are *reported*, never auto-fixed, as
  `partial_write_detected`, `corrupt_ledger`, `missing_linked_attempt`, or
  `missing_linked_memory_record` (§I). The load **fails closed** on any violation.
- detection **does not** claim recovery. Turning a detected anomaly into a resolved
  state is only ever done by the explicit §H.7 routine under the writer lock. A load
  that detects a problem reports it and refuses; it does not silently repair.

> A committed receipt must never exist unless its exact resulting Active Memory record
> exists and resolves. This is an invariant, enforced at commit (ordering + durable
> snapshot before receipt, §H.2/§H.3) and re-checked at load (detection scan, §H.8),
> with ambiguity resolved only by explicit recovery (§H.7).

---

## I. Diagnostics and information safety

Typed, closed-vocabulary diagnostic codes (severity fixed per code, following the
Phase 40E/40F/40G pattern where a caller cannot downgrade a finding):

| Code | Meaning | Disposition |
| --- | --- | --- |
| `stale_candidate` | Candidate id/provenance no longer matches the reviewed decision | fail closed |
| `changed_digest` | Recomputed candidate digest ≠ reviewed digest | fail closed |
| `changed_assessment` | Assessment id/version ≠ reviewed assessment | fail closed |
| `missing_review` | No review decision for the tuple | fail closed |
| `incomplete_provenance` | Decision missing required reviewer/timestamp/reason/evidence, or a dangling intra-ledger reference | fail closed |
| `rejected_candidate` | Effective decision is `rejected` | fail closed (no mutation) |
| `deferred_candidate` | Effective decision is `deferred` | fail closed (no mutation) |
| `stale_approval` | Approved decision whose candidate digest or assessment no longer matches the present input | fail closed (no mutation) |
| `contradictory_evidence` | Approval contradicts assessment verdict or points at a different candidate | fail closed |
| `supersession_tie` | Two distinct records would become active heads of one logical line with identical ordering keys | fail closed |
| `supersession_cycle` | Proposed supersession links would close a cycle in the supersession graph | fail closed |
| `duplicate_replay` | Same idempotency key as an existing committed receipt | return existing receipt (idempotent) |
| `conflicting_replay` | Same digest under a different assessment/decision than an existing attempt | fail closed (distinct input) |
| `writer_locked` | The exclusive writer lock is held by another writer | fail closed (retryable) |
| `revision_conflict` | The persisted `ledger_revision` changed under a writer (CAS failure) | fail closed (retryable) |
| `persistence_failure` | Ledger load/save failed (bounded, typed) | fail closed |
| `partial_write_detected` | Load-time scan found an incomplete/interrupted write (detection only) | fail closed; hand to explicit recovery |
| `corrupt_ledger` | Load-time scan found structurally invalid or internally inconsistent ledger state | fail closed |
| `missing_linked_attempt` | A receipt references an `import_attempt_id` that does not exist | fail closed |
| `missing_linked_memory_record` | A receipt's `record_id` does not resolve in the Active Memory store | fail closed |
| `uncertain_commit_result` | Intent exists without a committed receipt and durable state cannot determine the outcome | fail closed; resolved only by §H.7 recovery, never reported as success |

**Information safety (reused Phase 40E/40F/40G rule):** diagnostics carry closed-enum
literals, counts, and record-local identifiers/digests (non-reversible hashes) only.
They **never** leak filesystem paths, the ledger's on-disk location, database
internals (there is no DB), credentials, raw exception strings/tracebacks, candidate
body text, exported conversation content, or declared paths. Digests are hashes, not
content. A path that appears in a raw `OSError` is mapped to a typed
`persistence_failure` with no path echoed.

---

## J. Test matrix

Layers: **C** = contract/model tests, **S** = service tests (over a temp ledger /
injected adapter + an injected in-memory Active Memory store), **A** =
adapter/persistence tests, **I** = cross-store integration tests (service + real
`InMemoryActiveMemoryStore` + durable snapshot seam), **R** = regression over existing
Phase 40E–40G and Phase 37B/37C suites. All are backend `pytest`. No network, no real
Active Memory activation, hermetic temp-dir ledger (Phase 39B test convention:
`HIVEMIND_MIGRATION_IMPORT_PATH` override / injected path so no developer profile is
touched).

| # | Case | Layer | Expected result |
| --- | --- | --- | --- |
| 1 | Approved candidate imports exactly once | S/I | one receipt, one `record_id` in the Active Memory store, idempotent on replay |
| 2 | Rejected candidate never mutates memory | S | `rejected_candidate`, zero records inserted |
| 3 | Deferred candidate never mutates memory | S | `deferred_candidate`, zero records inserted |
| 4 | Changed candidate bytes invalidate approval | S | `changed_digest`, fail closed, no insert |
| 5 | Changed assessment invalidates approval / requires renewed review | S | `changed_assessment`, fail closed |
| 6 | Duplicate request returns the same deterministic result | S/I | same `receipt_id` + `record_id`, no second record |
| 7 | Concurrent duplicate requests cannot create duplicate records | A/I | exclusive writer + CAS: exactly one record; loser → winner's receipt |
| 8 | Stale writer loses CAS | A | `revision_conflict`; stale write refused; last good ledger intact |
| 9 | Exclusive writer lock enforced | A | second writer gets `writer_locked` (or serializes); never concurrent mutation |
| 10 | Distinct `import_attempt_id` per retry, stable idempotency key | S/C | attempt_sequence 1,2,3…; one stable key; one committed receipt |
| 11 | Receipt references the exact resulting `record_id` | C/S | link resolves in the Active Memory store; forged/dangling link rejected |
| 12 | Receipt with missing linked attempt detected | A | `missing_linked_attempt`, fail closed |
| 13 | Receipt with missing linked memory record detected | A/I | `missing_linked_memory_record`, fail closed |
| 14 | Corrupt / internally inconsistent ledger detected | A | `corrupt_ledger`, fail closed, no silent repair |
| 15 | Partial write detected (not "recovered") at load | A | `partial_write_detected`; temp sibling ignored; last good ledger loads; no success claimed |
| 16 | Uncertain commit — record present, no receipt → recovery finalizes | I | §H.7 writes receipt, returns stored success, idempotent |
| 17 | Uncertain commit — record absent, no receipt → recovery fails safe | I | attempt marked `failed`, safe retry; no false success |
| 18 | Uncertain commit — durable state unreadable → typed fail-closed | I/A | `uncertain_commit_result`, never reported as success |
| 19 | No cross-store atomicity is claimed/relied on | I | interrupting between snapshot and receipt is recoverable, not silently committed |
| 20 | Deterministic supersession ordering | S/C | total order over (decision_timestamp, attempt_sequence, record_id) |
| 21 | Supersession tie rejected | S | `supersession_tie`, fail closed |
| 22 | Supersession cycle rejected | S | `supersession_cycle`, fail closed, nothing persisted |
| 23 | Missing reviewer fails validation | C | decision cannot be constructed |
| 24 | Missing reason fails validation | C | decision cannot be constructed |
| 25 | Missing evidence fails validation | C | decision cannot be constructed (≥1 required) |
| 26 | Missing timestamp fails validation | C | decision cannot be constructed |
| 27 | Contradictory review evidence fails closed | S | `contradictory_evidence`, no insert |
| 28 | Stale approval fails closed | S | `stale_approval`, no insert |
| 29 | Conflicting replay (same digest, different assessment/decision) | S | `conflicting_replay`, fail closed |
| 30 | Approval boolean alone does not authorize | S | a decision reduced to `status` only fails validation/preconditions |
| 31 | Imported record standing is INACTIVE + UNVERIFIED | I | inserted record carries the conservative standing; never auto-active |
| 32 | Diagnostics leak no path/secret/raw content | S | planted sensitive values never appear in any diagnostic |
| 33 | Existing Active Memory store contracts remain regression-clean | R | Phase 37B/37C suites unchanged and passing; `MemoryStore` seam unmodified in behavior |
| 34 | Existing Phase 40E–40G contracts remain regression-clean | R | 40E/40F/40G suites unchanged and passing |
| 35 | Full backend suite passes during implementation | R | green (baseline count + new Phase 40H tests) |

The full backend suite MUST pass during the implementation phase; these cases are
authored then, not now.

---

## K. Integration map (smallest credible; not implemented in this phase)

Tightly bounded and independently auditable. This is a two-store integration, so the
map names the **existing Active Memory modules and integration tests Phase 40H must
exercise or (minimally) touch**, not only net-new files. Nothing below is written
during planning.

| File | New/Mod | Responsibility | Preserves / integrates |
| --- | --- | --- | --- |
| `apps/backend/app/models/memory_migration_import.py` | New | `memory-migration-import.v1` **workflow** contracts only: review decision, evidence reference, import attempt (with `attempt_sequence`, `intent_state`), receipt (referencing `record_id`, never copying a record), idempotency + recovery metadata, `ledger_revision`, closed diagnostic taxonomy, ledger document. `extra="forbid"`, pinned versions, `derive_migration_id` identities. **Does not redefine `MemoryRecord`.** | Phase 40E/40F/40G contracts; references (not copies of) Active Memory `MemoryRecord.record_id` |
| `apps/backend/app/services/memory_migration_import_store.py` | New | Durable ledger adapter: versioned-JSON ledger, OS-path resolution + `HIVEMIND_MIGRATION_IMPORT_PATH` override, bounded load with typed failures, atomic append-with-CAS write (§H.5), exclusive writer lock (§H.6), load-time integrity **detection** scan (§H.8). | Phase 39B `RepositoryWorkspaceConfigService` persistence pattern (path resolution, atomic temp-swap, typed errors) |
| `apps/backend/app/services/memory_migration_import.py` | New | Orchestration service: record review decision, record import attempt (monotonic sequence), `import_reviewed_candidate` (§E preconditions, insert via the Active Memory seam §F.2, durable snapshot §H.4, receipt commit), idempotent replay lookup, uncertain-commit **recovery** (§H.7). | The §E/§F/§G/§H rules; **depends on** the existing `MemoryStore` protocol; Phase 40F candidate + Phase 40G report contracts reused unchanged |
| `apps/backend/app/store/active_memory_store.py` | **Existing — integration touchpoint** | The **authoritative Active Memory store**. Phase 40H uses its existing `insert`, `DuplicateRecordError`, `transition_lifecycle`, and `serialize`/`restore` seam **unchanged**. If, and only if, a durable Active Memory snapshot owner (§H.4) proves necessary and none exists, a **thin additive durable-snapshot write** is introduced as a separate, explicitly-approved seam over the existing `serialize()` — never a rewrite and never record re-homing. | Phase 37B/37C behavior; `MemoryRecord` identity/immutability/lifecycle |
| `apps/backend/app/models/active_memory.py` | **Existing — read-only dependency** | Source of `MemoryRecord`, `LifecycleState.INACTIVE`, `VerificationState.UNVERIFIED`, and `supersession_refs`. Phase 40H **reuses** these; no enum, field, or contract change is required or proposed. | Phase 37B contract, unchanged |
| `apps/backend/tests/test_memory_migration_import_contracts.py` | New | Contract tests: §J rows 10–11, 20, 23–26, 30; identity derivation; immutability. | — |
| `apps/backend/tests/test_memory_migration_import_service.py` | New | Service tests: §J rows 1–6, 10, 20–22, 27–30, 32 over a temp ledger + injected store. | — |
| `apps/backend/tests/test_memory_migration_import_store.py` | New | Adapter tests: §J rows 7–9, 12–15; CAS, exclusive writer, atomicity, integrity **detection**, typed failures. | — |
| `apps/backend/tests/test_memory_migration_import_integration.py` | New | Cross-store integration: §J rows 1, 6, 7, 13, 16–19, 31 over the service + real `InMemoryActiveMemoryStore` + durable snapshot seam. | Exercises, does not modify, the Active Memory store |
| `docs/planning/phase-40h-reviewed-persistence-verified-import-planning.md` | New (this doc) | The plan. | — |

Regression (§J 33–35) runs the existing Phase 37B/37C and 40E/40F/40G suites and the
full backend suite; **no existing test file is edited**, and the Active Memory store's
behavior is asserted unchanged. Net-new surface is three source files plus four test
files, with two existing Active Memory modules as named integration touchpoints — the
smallest credible integration for a two-store reviewed import, and small enough for
one independent audit.

---

## L. API boundary

**Decision: no new public API in Phase 40H.** Default upheld.

Reviewed import is a durable, security-sensitive local operation; the smallest
foundation is a backend service + persistence adapter integrating the existing Active
Memory store, exercised by tests, matching how Phase 37C (store) and Phase 39B (config
service) landed before any endpoint. An HTTP surface would add request-validation,
auth-posture, and error-mapping concerns that are out of scope for establishing the
mutation boundary and are unnecessary to prove the contract.

If a later phase believes an endpoint is necessary (e.g., a review/approval workflow
UI), it must: (1) justify it separately, (2) define a narrow thin-router boundary that
only validates a request contract and maps typed results to safe responses (no
persistence/digest/lifecycle logic in the router), and (3) be marked as **requiring
explicit approval before implementation**. No endpoint is created in this planning
phase, and none is created by the proposed Phase 40H implementation above.

---

## M. Deferred work (explicitly out of scope)

Explicitly deferred and **not** part of Phase 40H:

- Frontend work of any kind (no review/approval/import UI).
- Grounded Synthesis Producer implementation (Phase 40I).
- Automatic approval or any derived/inferred approval.
- LLM or semantic truth adjudication.
- Active-state calculation / promotion of imported records to `active` /
  `human_confirmed` (remains deferred Active Memory work).
- Any change to the Active Memory record contract, enums, identity rule, or lifecycle
  transition table (Phase 40H reuses them unchanged).
- Knowledge Graph mutation.
- Source Registry mutation.
- Obsidian mutation / write-back.
- Repository Observer mutation.
- Broad persistence replacement or migrating the existing Active Memory store to a new
  durable medium (beyond the thin, explicitly-scoped durable-snapshot seam of §H.4).
- **PostgreSQL / any server database migration.**
- Phase 36K (paused and untouched).
- Operational deployment, service install, scheduled tasks, background daemons.
- Screenshots and demo evidence.
- A public API / endpoint (see §L).
- Anything beyond the smallest reviewed-import foundation.

---

## Acceptance-criteria coverage

| Criterion | Section |
| --- | --- |
| Active Memory store remains authoritative | A.1 |
| Migration service is an orchestration boundary, not a competing store | A.2 |
| MigrationImportStore owns workflow records only | A.3 |
| Authorized Active-Memory-insertion seam | F.2 |
| No duplication/wrapping of authoritative records | A.1, B, F.2 |
| Receipt references exact `record_id` + existing version semantics | B, B.2, E, H.2 |
| No false cross-store atomicity; recoverable protocol | H.1–H.3 |
| Durable Active Memory snapshot seam (persistence-boundary revision) | H.4 |
| Concurrency: exclusive writer + persisted-revision/CAS | H.5, H.6 |
| Stable idempotency key + distinct monotonic attempt ids | G.1, G.2 |
| Uncertain-commit recovery routine | H.7 |
| Supersession ordering / tie / cycle / changed-byte / changed-assessment / renewed review | D.7 |
| Diagnostic taxonomy incl. the six required codes | I |
| Partial-write detection separated from recovery | H.7, H.8 |
| Expanded test matrix | J |
| Smallest credible integration map incl. existing modules + integration tests | K |
| Fail-closed behavior | E, H, I |
| Explicit deferred work | M |
| Explicit API boundary | L |
| Independently auditable implementation scope | K |

Phase 36K remains **paused and untouched** by this plan. This document persists
nothing, imports nothing, and implements no runtime; it defines the Phase 40H
foundation only.
