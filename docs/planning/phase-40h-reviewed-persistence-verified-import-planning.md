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
(candidate-set dry-run assessment).

Phase 40H is the first phase in the memory-migration track permitted to **create
Active Memory from a migration candidate** — and only for a candidate a human has
explicitly reviewed and approved. Everything before it is read-only: Phase 40E
judges declarations, Phase 40F reads bytes and projects inactive candidates, Phase
40G assesses the candidate set. None of them writes anything durable. Phase 40H
adds the durable, human-gated bridge from an assessed candidate to a verified
Active Memory version, and it does so without ever inferring approval from parsing
success, assessment cleanliness, or an approval boolean standing alone.

This is a **planning document**. It defines the state owner, the durable record
types, the review-provenance requirements, the persistence lifecycle, the
verified-import contract, the exclusive mutation boundary, idempotency/replay,
atomicity/recovery, the typed diagnostics, the test matrix, the proposed
implementation file map, the API decision, and the deferred work. It implements
none of them.

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
   durably written into Active Memory exactly once, under a deterministic receipt
   that links the candidate, its digest, its assessment, the review decision, the
   import attempt, and the resulting memory version.

"Verified import" proves the pipeline was honored end-to-end and byte-consistent.
It does **not** prove the imported statement is factually true — the resulting
Active Memory version is imported evidence, never adjudicated truth (see §5.4).

---

## A. State-ownership contract

### A.1 Authoritative state owner

A single new backend service, the **Reviewed Migration Import Service** (working
name `MemoryMigrationImportService`), is the sole authority for durable
migration-import state. It owns: recording review decisions, recording import
attempts, performing verified import, creating the resulting Active Memory version,
writing the receipt, and answering idempotent replay lookups. No router, no parser,
no projector, no assessor, and no frontend may write migration-import state; they
call this service or they read nothing.

### A.2 Persistence adapter boundary

Durable state lives behind a **persistence adapter** (working name
`MigrationImportStore`) that is the only component performing filesystem I/O for
this feature. The service depends on the adapter's typed interface, never on
`open`, `json`, or `os.replace` directly. This mirrors the Phase 40F
parser/projector split (all I/O behind one seam) and the Phase 37 store/service
split.

**The established local persistence architecture is reused, not replaced.** The
authoritative pattern is the Phase 39B
[`RepositoryWorkspaceConfigService`](../../apps/backend/app/services/repository_workspace_config.py):

- a **versioned JSON contract** (`schema_version`, `extra="forbid"` models);
- an **OS-appropriate path outside the repository** (Windows `%LOCALAPPDATA%`,
  otherwise XDG), with a `HIVEMIND_*_PATH` environment override of highest
  precedence, resolved without side effects (Phase 39B's
  `resolve_workspace_config_path`);
- **atomic, corruption-resistant writes** (temp sibling + `fsync` + `os.replace`),
  so a failed write never destroys the prior valid file;
- **bounded loads** with typed failure states for not-found, malformed,
  unsupported-version, too-large, and inaccessible;
- **fail-closed reads** — a malformed or unreadable store raises a typed error and
  never silently discards or overwrites.

Phase 40H's durable state is an **append-oriented import ledger** rather than a
mutable registry (see §D.6), so the store adds one capability the Phase 39B config
service does not need: **append-with-conflict-detection** under the same atomic
temp-swap discipline. That is an additive reuse of the established pattern, not a
new persistence technology.

> **No speculative PostgreSQL rewrite.** A relational database is explicitly *not*
> proposed. Hive|Mind is local-first and single-user (roadmap "Current
> Limitations"); Active Memory itself is still in-memory-with-serialize/restore.
> Introducing a server database here would be a large, unaudited dependency far
> beyond the smallest reviewed-import foundation. The local versioned-JSON ledger
> is sufficient for a single operator's own migration history; if future evidence
> ever shows it insufficient, that is a separate, justified decision — not part of
> this phase.

### A.3 Router thinness and non-mutating layers

- **Routers stay thin.** Phase 40H proposes **no** router by default (see §L). If a
  future, separately-approved phase adds one, it does only transport: validate a
  request contract, call the service, map typed results to safe responses. It holds
  no persistence, digest, or lifecycle logic.
- **Only the Reviewed Migration Import Service may create Active Memory versions**
  from a migration candidate. That is the single mutation boundary (§F).
- **Parsing (40F), projection (40F), assessment (40G), dry-run, and inspection stay
  non-mutating.** They are pure/read-only today and Phase 40H changes none of them.
  Phase 40H depends on their outputs and never edits their modules.

---

## B. Durable record types and relationships

All records are versioned (`memory-migration-import.v1`), `extra="forbid"`, and use
the repository's canonical-JSON + SHA-256 identity convention (`derive_migration_id`,
reused from Phase 40E/40F/40G — no new identity scheme). Identifiers are pure
functions of typed content; nothing reads a clock, randomness, or process state to
form an identity. Caller-supplied timestamps follow the Phase 37E/40F convention
(the service records time it is given; it does not read the wall clock to fabricate
provenance).

| Record | Identity | Key fields | Mutability |
| --- | --- | --- | --- |
| **Migration candidate reference** | `candidate_id` (Phase 40F, reused unchanged) | `candidate_id`, `content_digest`, `provenance` (bundle/artifact fingerprints, observed digest), assessed-set membership | Immutable; a *reference*, not a copy of candidate bytes |
| **Candidate byte digest** | value of `content_digest` | the Phase 40F SHA-256 over candidate content; the observed artifact digest from `MigrationCandidateProvenance` | Immutable |
| **Assessment reference** | `report_id` (Phase 40G, reused unchanged) + `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION` | `report_id`, ruleset version, `review_readiness` verdict | Immutable |
| **Review decision** | `derive_migration_id` over its own canonical fields (`review_decision_id`) | reviewer id, decision timestamp, status, reason, notes, candidate id + digest, assessment id + version, evidence references | Immutable once recorded (append-only; a superseding decision is a new record, §C/§D.6) |
| **Review evidence reference** | reference tuple `(kind, ref_id)` | typed pointer to the assessment report, the dry-run finding(s), and/or the candidate provenance the reviewer relied on | Immutable |
| **Import attempt** | `derive_migration_id` over idempotency-key inputs (`import_attempt_id`) | idempotency key, referenced review_decision_id, candidate id + digest, assessment id + version, attempt status, attempt timestamp | Append-only; status advances through controlled records, never edited in place |
| **Verified import receipt** | `derive_migration_id` over the linked identities (`receipt_id`) | candidate id, candidate digest, assessment id + version, review_decision_id, import_attempt_id, resulting `memory_version_id` | Immutable; created only at successful commit |
| **Resulting Active Memory version** | `memory_version_id` = `derive_migration_id` over the projected record content + provenance | the `MemoryRecord`-shaped imported record, its lifecycle/verification standing, back-links to receipt + candidate | Immutable version; a re-import is a new version, never an edit |

### B.1 Ownership and cardinality

- One **candidate** may be referenced by many **review decisions** over time (a
  deferred decision later superseded by an approval), but at most **one
  non-superseded approved decision** is valid for a given `(candidate_id,
  content_digest, assessment_id, assessment_version)` tuple at any time (§D.6, §G).
- One valid **approved review decision** authorizes at most **one successful import
  attempt** for its exact reviewed input, producing exactly **one receipt** and
  exactly **one resulting memory version** (§G idempotency).
- One **import attempt** references exactly one **review decision** and yields zero
  or one **receipt** (zero on failure, one on verified commit).
- One **receipt** references exactly one resulting **memory version**, and that
  memory version back-links to exactly one receipt. This 1:1 linkage is the
  invariant §H protects: a receipt without its exact memory version, or a memory
  version without its receipt, is a corruption to be detected, never a valid state.

### B.2 Uniqueness, foreign keys, timestamps

- **Uniqueness constraints (enforced by the ledger, adapter-level):**
  `review_decision_id`, `import_attempt_id`, `receipt_id`, and `memory_version_id`
  are each unique. The **idempotency key** (§G) is unique across successful import
  attempts — a duplicate maps to the existing receipt, never a new version.
- **Foreign-key equivalents:** every import attempt names an existing
  `review_decision_id`; every receipt names an existing `import_attempt_id`,
  `review_decision_id`, and `memory_version_id`; every review decision names an
  existing `candidate_id` + `content_digest` and `report_id` + version. A dangling
  reference fails closed at validation and is reported (`incomplete_provenance` /
  `receipt_verification_failed`, §I).
- **Timestamps:** `decision_timestamp` and `attempt_timestamp` are caller-supplied
  and immutable once recorded. There is no server-clock read; determinism and
  auditability come from the caller stating time, exactly as Phase 37E/40F do.
- **Immutable vs mutable:** every record above is immutable once written. The
  *ledger* grows by appending new records; a lifecycle "transition" is a new
  controlled record referencing the prior one (§D.6), never an in-place edit of an
  existing field. The only field that could be described as "changing" is a
  decision's or attempt's *effective* status, and that is expressed by a newer
  superseding record, not by mutation.

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
                import_attempted
                   |         |
                   v         v
             import_verified   import_failed
              (terminal)       (non-terminal; safe retry)
```

### D.2 State meanings

- **candidate_received** — a Phase 40F candidate exists and is referenced.
- **assessment_completed** — a Phase 40G report exists over the candidate's set.
- **awaiting_review** — no valid non-superseded decision yet exists for the exact
  `(candidate_id, digest, assessment_id, version)` tuple.
- **approved / rejected / deferred** — a review decision of that status is the
  current effective decision for the tuple.
- **import_attempted** — an approved decision has an import attempt in progress or
  recorded.
- **import_verified** — a receipt and its exact resulting memory version exist and
  are linked (the only success terminal).
- **import_failed** — an attempt did not commit; no receipt and no memory version
  were created (safe to retry).

### D.3 Terminal vs non-terminal

- **Terminal:** `import_verified` (success), `rejected` (\*terminal for that exact
  reviewed input; a *different* input — new digest or new assessment — is a fresh
  `awaiting_review`, not a re-opening of the rejected one).
- **Non-terminal:** `awaiting_review`, `deferred`, `import_attempted`,
  `import_failed`.

### D.4 Prohibited transitions

- `awaiting_review`/`deferred`/`rejected` → `import_attempted` **without** a valid
  `approved` decision. Forbidden.
- `import_failed` → `import_verified` **without** a fresh, fully re-validated import
  attempt. A failed attempt never "upgrades" to verified.
- Any state → `import_verified` **without** the exact resulting memory version
  existing and linked (§H). Forbidden by construction.
- Editing a recorded decision's `status`, `reason`, `reviewer_id`, `digest`, or
  assessment binding in place. Forbidden — records are immutable (§B, §D.6).
- `approved` for tuple *X* authorizing import of tuple *Y* (different candidate,
  digest, assessment, or version). Forbidden — the import path binds to the exact
  tuple.

### D.5 Renewed-review, retry, stale-record rules

- **Renewed review required when:** the candidate digest changes (re-parsed
  bytes), or the assessment identity/version changes (re-assessed set, or ruleset
  version bump). The prior approval no longer matches the exact reviewed input and
  authorizes nothing; a new `awaiting_review` state applies until a new decision is
  recorded (§E preconditions enforce this at import time — a mismatched approval is
  rejected as `stale_candidate` / `changed_assessment`).
- **Retry:** after `import_failed`, a retry re-runs the full verified-import
  precondition set (§E) from scratch. There is no shortcut path.
- **Stale record:** an `approved` decision whose candidate digest or assessment no
  longer matches the present candidate/assessment is **stale**; it is not deleted
  (history is preserved) but it fails the import preconditions and is reported
  (`stale_approval`, §I).

### D.6 Append-only vs updated

State transitions are **append-only through controlled records.** The ledger never
edits an existing record's field. A superseding decision is a *new* decision record
that references the one it supersedes; effective status is computed as the newest
non-superseded decision for a tuple, exactly as Phase 40D/40G compute readiness
rather than reading it off a record. Import attempts likewise append status records.
This makes the whole history auditable and makes "who changed what, when" answerable
from the ledger alone.

---

## E. Verified-import contract

The reviewed-import operation (`import_reviewed_candidate`) is the only path that
creates Active Memory from a candidate. Before creating anything, it MUST, in order:

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
8. **Fail closed** for any missing, stale, contradictory, or mismatched evidence.
   The default is refusal; only a fully consistent set proceeds.
9. **Create or update Active Memory only through this service.** The imported record
   is constructed under the Active Memory contract and written via the authorized
   path. No other layer performs the write.
10. **Produce a deterministic receipt** linking candidate, candidate digest,
    assessment, review decision, import attempt, and the resulting memory version.

### E.1 What "verified import" proves — and does not

**Proves:** the exact candidate bytes that were reviewed (digest-identical) were
imported; the exact assessment the reviewer saw still applies; a complete,
attributable, non-contradictory approval authorized it; and the resulting Active
Memory version is deterministically linked to all of that by an immutable receipt.
Re-running the same reviewed input yields the same receipt and no second version.

**Does not prove:** that the imported statement is factually **true**. Byte
integrity and review provenance are not truth adjudication. Accordingly the
resulting Active Memory version is imported evidence with a conservative standing
(§F.1): it is not `human_confirmed` truth merely because a human approved *importing
it*, and it is never auto-activated into the trusted baseline by this phase. No LLM
or automated process decides truth anywhere in the path.

---

## F. Mutation authority

**One explicit mutation boundary:**

> Only the reviewed-import path (the Reviewed Migration Import Service's
> `import_reviewed_candidate`) may create or update Active Memory from a migration
> candidate.

- Parsing, projection, validation, assessment, dry-run, inspection, and
  review-record creation **must not** mutate Active Memory. Recording a review
  decision writes a *decision* to the migration-import ledger; it does not touch
  Active Memory.
- **No automatic candidate approval.** Approval is a human act recorded as a review
  decision; nothing derives approval.
- **No semantic promotion inferred from parsing success.** A candidate that parsed
  cleanly, hashed cleanly, and assessed `ready_for_review` is still just a
  candidate until a human decision plus a verified import exist.
- **No LLM or automated truth adjudication** anywhere in the path.

### F.1 Standing of the resulting Active Memory version

The imported record is created **inactive** and **unverified** — it is imported
history a human chose to bring in, not an adjudicated active fact. It carries
provenance back to the candidate, the receipt, and the review decision. Promotion
to `active` / `human_confirmed` (active-state calculation, contradiction handling)
remains the deferred Active Memory work already named in the roadmap and is **not**
part of Phase 40H. This preserves the Phase 40E/40F invariant that imported material
is never verified truth automatically, while still letting a human durably persist a
reviewed candidate.

---

## G. Idempotency and replay

### G.1 Idempotency key inputs

The stable idempotency key is `derive_migration_id` over exactly:
`candidate_id`, `content_digest`, `assessment_report_id`, `assessment_version`, and
`review_decision_id`. These five identify "this exact reviewed input." Nothing
time-based, random, or request-envelope-based enters the key.

### G.2 Behavior

- **Duplicate valid request** (same key, prior success): return the **existing
  receipt** and its existing memory version. No new attempt record's success, no
  second memory version. Idempotent replay is a lookup, not a re-import.
- **Deterministic receipt lookup:** the receipt is addressable by the idempotency
  key, so a replay is answered from the ledger deterministically.
- **Successful replay:** returns the same `receipt_id` and same `memory_version_id`
  as the original — byte-identical result.
- **Retry after failure:** if no successful receipt exists for the key, a retry
  re-runs §E fully and may create the (first and only) receipt.
- **Concurrency:** two concurrent requests for the same key must not both create a
  memory version. The adapter's append-with-conflict-detection (unique idempotency
  key over successful attempts, atomic swap) makes one win and the other resolve to
  the winner's receipt (`duplicate_replay`). No lost update, no double version.
- **Conflicting replay detection:** the *same* candidate digest presented under a
  *different* assessment or a *different* review decision is **not** the same key —
  it is a distinct reviewed input requiring its own approval, and if it collides
  with an existing but materially different attempt it is reported
  (`conflicting_replay`), never silently merged.

> Approved candidates import **exactly once** for the same reviewed input; duplicate
> valid requests return the same deterministic result rather than creating another
> memory version.

---

## H. Atomicity and recovery

### H.1 Transaction boundary and commit point

The import of one candidate is a single logical transaction over the local ledger:
record the import attempt → create the resulting memory version → create the receipt
linking them. The **commit point** is the atomic ledger swap (temp sibling + `fsync`
+ `os.replace`, the Phase 39B discipline) that makes the receipt durable. Before the
swap, nothing is durable; after it, everything is.

### H.2 Ordering to make a false-positive impossible

The resulting memory version is written into the ledger's staged content **before**
the receipt that references it, and the whole staged document (attempt + memory
version + receipt, mutually linked) is swapped in one atomic replace. There is no
window in which a durable receipt exists without its durable memory version.

### H.3 Rollback / compensating behavior

Because durability is a single atomic swap of a fully-formed document, a failure
before the swap leaves the prior ledger untouched (no partial write survives — the
temp file is discarded, exactly as Phase 39B's `_atomic_write` unlinks on failure).
There is nothing to compensate: either the complete linked set committed, or none of
it did.

### H.4 Partial-write and crash recovery

- A crash mid-write leaves only an orphan temp file (never the destination); startup
  / next-load ignores temp siblings and loads the last good ledger.
- On load, the service runs a **receipt-integrity check**: every receipt must
  reference an existing memory version and an existing import attempt, and every
  memory version claiming a receipt must be referenced by exactly that receipt. A
  violation is surfaced as `partial_write_recovery` / `receipt_verification_failed`
  (§I) and the affected import is treated as **not verified** (fail closed) — never
  reported as a success.
- **Safe retry:** a candidate whose prior attempt failed or was not durably
  committed is retryable via the full §E path; the idempotency key guarantees the
  retry cannot double-create.

> A verified receipt must never exist unless the exact resulting memory version
> exists and is linked successfully. This is an invariant, enforced at commit
> (ordering + atomic swap) and re-checked at load (receipt-integrity scan).

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
| `incomplete_provenance` | Decision missing required reviewer/timestamp/reason/evidence, or a dangling reference | fail closed |
| `rejected_candidate` | Effective decision is `rejected` | fail closed (no mutation) |
| `deferred_candidate` | Effective decision is `deferred` | fail closed (no mutation) |
| `contradictory_evidence` | Approval contradicts assessment verdict or points at a different candidate | fail closed |
| `duplicate_replay` | Same idempotency key as an existing success | return existing receipt (idempotent) |
| `conflicting_replay` | Same digest under a different assessment/decision than an existing attempt | fail closed (distinct input) |
| `persistence_failure` | Ledger load/save failed (bounded, typed) | fail closed |
| `partial_write_recovery` | Load-time integrity scan found an incomplete write | fail closed; treat import as not verified |
| `receipt_verification_failed` | A receipt does not link to its exact memory version | fail closed |

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
injected adapter), **A** = adapter/persistence tests, **R** = regression over
existing Phase 40E–40G suites. All are backend `pytest`. No network, no real Active
Memory activation, hermetic temp-dir ledger (Phase 39B test convention:
`HIVEMIND_*_PATH` override / injected path so no developer profile is touched).

| # | Case | Layer | Expected result |
| --- | --- | --- | --- |
| 1 | Approved candidate imports exactly once | S | one receipt, one memory version, idempotent on replay |
| 2 | Rejected candidate never mutates memory | S | `rejected_candidate`, zero memory versions written |
| 3 | Deferred candidate never mutates memory | S | `deferred_candidate`, zero memory versions |
| 4 | Changed candidate bytes invalidate approval | S | `changed_digest`, fail closed, no mutation |
| 5 | Changed assessment invalidates approval / requires renewed review | S | `changed_assessment`, fail closed |
| 6 | Duplicate request returns the same deterministic result | S | same `receipt_id` + `memory_version_id`, no second version |
| 7 | Concurrent duplicate requests cannot create duplicate versions | S/A | exactly one version; loser resolves to winner's receipt |
| 8 | Failed write cannot leave a falsely verified record | A | no receipt without its exact memory version |
| 9 | Partial write detected and recoverable | A | `partial_write_recovery`; load ignores temp sibling; last good ledger loads |
| 10 | Receipt references the exact resulting memory version | C/S | 1:1 link verified; forged link rejected |
| 11 | Missing reviewer fails validation | C | decision cannot be constructed |
| 12 | Missing reason fails validation | C | decision cannot be constructed |
| 13 | Missing evidence fails validation | C | decision cannot be constructed (≥1 required) |
| 14 | Missing timestamp fails validation | C | decision cannot be constructed |
| 15 | Contradictory review evidence fails closed | S | `contradictory_evidence`, no mutation |
| 16 | Stale approval fails closed | S | `stale_approval`/`stale_candidate`, no mutation |
| 17 | Existing Phase 40E–40G contracts remain regression-clean | R | 40E/40F/40G suites unchanged and passing |
| 18 | Full backend suite passes during implementation | R | green (baseline count + new Phase 40H tests) |
| 19 | Diagnostics leak no path/secret/raw content | S | planted sensitive values never appear in any diagnostic |
| 20 | Approval boolean alone does not authorize | S | a decision reduced to `status` only fails validation/preconditions |

The full backend suite MUST pass during the implementation phase; these cases are
authored then, not now.

---

## K. Proposed implementation file map (not implemented in this phase)

Tightly bounded, independently auditable. New unless noted; nothing below is written
during planning.

| File | New/Mod | Responsibility | Preserves |
| --- | --- | --- | --- |
| `apps/backend/app/models/memory_migration_import.py` | New | `memory-migration-import.v1` contracts: review decision, evidence reference, import attempt, receipt, resulting-memory-version wrapper, closed diagnostic taxonomy, ledger document. `extra="forbid"`, pinned versions, `derive_migration_id` identities. | Phase 40E/40F/40G contracts + `CANDIDATE_MEMORY_POLICY`; Active Memory `MemoryRecord`/`LifecycleState`/`VerificationState` semantics |
| `apps/backend/app/services/memory_migration_import_store.py` | New | Persistence adapter: versioned-JSON ledger, OS-path resolution + `HIVEMIND_MIGRATION_IMPORT_PATH` override, bounded load with typed failures, atomic append-with-conflict-detection write, load-time receipt-integrity scan. | Phase 39B `RepositoryWorkspaceConfigService` persistence pattern (path resolution, atomic temp-swap, typed errors) |
| `apps/backend/app/services/memory_migration_import.py` | New | Reviewed Migration Import Service: record review decision, record import attempt, `import_reviewed_candidate` (the §E preconditions, exclusive Active Memory creation, receipt production), idempotent replay lookup. | The §E/§F/§G/§H rules; Phase 40F candidate + Phase 40G report contracts, reused unchanged |
| `apps/backend/tests/test_memory_migration_import_contracts.py` | New | Contract tests: §J rows 10–14, 20; identity derivation; immutability. | — |
| `apps/backend/tests/test_memory_migration_import_service.py` | New | Service tests: §J rows 1–7, 15–16, 19–20 over a temp ledger. | — |
| `apps/backend/tests/test_memory_migration_import_store.py` | New | Adapter tests: §J rows 7–9; atomicity, partial-write recovery, integrity scan, typed failures. | — |
| `docs/planning/phase-40h-reviewed-persistence-verified-import-planning.md` | New (this doc) | The plan. | — |

Regression (§J 17–18) runs the existing 40E/40F/40G suites and the full backend
suite; no existing test file is edited. Total net-new surface is three source files
plus three test files — small enough for one independent audit.

---

## L. API boundary

**Decision: no new public API in Phase 40H.** Default upheld.

Reviewed import is a durable, security-sensitive local operation; the smallest
foundation is a backend service + persistence adapter exercised by tests, matching
how Phase 37C (store) and Phase 39B (config service) landed before any endpoint. An
HTTP surface would add request-validation, auth-posture, and error-mapping concerns
that are out of scope for establishing the mutation boundary and are unnecessary to
prove the contract.

If a later phase believes an endpoint is necessary (e.g., a review/approval
workflow UI), it must: (1) justify it separately, (2) define a narrow thin-router
boundary that only validates a request contract and maps typed results to safe
responses (no persistence/digest/lifecycle logic in the router), and (3) be marked
as **requiring explicit approval before implementation**. No endpoint is created in
this planning phase, and none is created by the proposed Phase 40H implementation
above.

---

## M. Deferred work (explicitly out of scope)

Explicitly deferred and **not** part of Phase 40H:

- Frontend work of any kind (no review/approval/import UI).
- Grounded Synthesis Producer implementation (Phase 40I).
- Automatic approval or any derived/inferred approval.
- LLM or semantic truth adjudication.
- Active-state calculation / promotion of imported records to `active` /
  `human_confirmed` (remains deferred Active Memory work).
- Knowledge Graph mutation.
- Source Registry mutation.
- Obsidian mutation / write-back.
- Repository Observer mutation.
- Broad persistence replacement or migrating existing Active Memory to a durable
  medium.
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
| Authoritative state owner | A.1 |
| Persistence adapter boundary | A.2 |
| Durable record types and relationships | B |
| Review provenance requirements | C |
| Allowed and prohibited transitions | D |
| Idempotency and replay rules | G |
| Atomicity and recovery behavior | H |
| Verified-import preconditions | E |
| Deterministic import receipt | B, E, H |
| Exclusive mutation authority | F |
| Fail-closed behavior | E, I |
| Typed diagnostic categories | I |
| Test matrix | J |
| Implementation file map | K |
| Explicit deferred work | M |
| Explicit API boundary | L |
| Independently auditable implementation scope | K |

Phase 36K remains **paused and untouched** by this plan. This document persists
nothing, imports nothing, and implements no runtime; it defines the Phase 40H
foundation only.
