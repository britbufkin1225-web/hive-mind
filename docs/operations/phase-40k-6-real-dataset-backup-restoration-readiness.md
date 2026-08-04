# Phase 40K.6 — Real Dataset Identity + Backup/Restoration Readiness Verification

**Planning version:** `phase-40k-6-readiness-verification.v1`

**Repository baseline:** `b46b9837735747692d50cee636fe61348109f6d8` (origin/main; Phase 40K.5
merged via PR #203)

**Status:** planning/verification-readiness only. **No production migration, no
production import, no writes to any authoritative dataset, no restoration execution,
and no backup mutation occur in this phase.**

**Companion artifacts:** the canonical
[authoritative migration runbook](phase-40k-authoritative-migration-runbook.md), the
[operator checklist](phase-40k-operator-checklist.md), the fail-closed
[readiness template](phase-40k-readiness.template.json), and the
[Phase 40K.5 readiness interface](phase-40k-5-migration-readiness-interface.md).

**Documentation verdict:** **`CONDITIONALLY READY`.** The repository proves the
manifest form, verification vocabulary, and read-only preflight/gate boundary needed
to *record and evaluate* dataset-identity and backup/restoration readiness. It cannot
prove the real dataset identity, backup existence, or restorability, all of which
remain operator/environment inputs. This document therefore defines the evidence,
procedures, and gates required and does **not** declare `READY FOR RESTORATION
REHEARSAL IMPLEMENTATION`.

---

## 0. Purpose, boundary, and what this phase is not

Phase 40K.5 supplied a genuinely read-only manifest preflight
(`app.services.migration_readiness_preflight.MigrationReadinessPreflight`) and a
fail-closed reviewed-execution gate
(`app.services.migration_execution_gate.ReviewedMigrationExecutionGate`) over the
`memory-migration-readiness.v1` contract
(`app.models.migration_readiness.MigrationReadinessManifest`). Those interfaces
evaluate a **declared** manifest; every real operational field in the checked-in
[template](phase-40k-readiness.template.json) is `not_supplied` / `unverified` /
`blocked`, so the template still evaluates to `blocked`.

Phase 40K.6 plans the *next* readiness step named by the 40K.5 interface (§7): how the
project will **safely identify the authoritative real dataset** and **verify its
backup and restoration chain** before an isolated restoration rehearsal — and, far
later, a production migration — could even be considered.

Passing Phase 40K.6 establishes **readiness evidence and procedure only**. It does
**not** authorize, begin, imply, or bring closer:

- production migration or any production write;
- any read of, or connection to, real production infrastructure;
- restoration against an authoritative target;
- the isolated restoration rehearsal itself (that is a separately authorized future
  execution — see §6);
- Phase 40L;
- deployment, provisioning, credential issuance, or infrastructure change.

Nothing in this document may be read as authorization for Phase 40L. Its strongest
permissible conclusion is `READY FOR RESTORATION REHEARSAL IMPLEMENTATION`, and this
phase's own inputs do not reach it (see §11).

### 0.1 Evidence-tier discipline used throughout

Every claim in this document is tagged as exactly one of:

- **[REPO-PROVEN]** — demonstrable from committed repository source at baseline
  `b46b983`. Cited by file/interface.
- **[OPERATOR-REQUIRED]** — a real-world fact only a human operator/reviewer can
  supply and independently confirm; it lives outside Git and is never fabricated
  here.
- **[ENVIRONMENT-DEPENDENT]** — a fact about deployment, storage, or infrastructure
  that cannot be confirmed from this repository at all.
- **[FUTURE-AUTHORIZED]** — work that requires a separate explicit authorization
  before it may be performed.

These tiers are load-bearing: they are the difference between "the repository can
represent this" and "this is true of the real world," which the migration track
(`migration_readiness.py` docstring) deliberately refuses to conflate.

---

## 1. Real Dataset Identity Record

### 1.1 What it is

A **Real Dataset Identity Record (RDIR)** is the operator-instantiated, out-of-Git
evidence set that pins the *one* authoritative dataset a future migration would read,
without exposing its contents. The repository already models the identity fields as
the `source_dataset` section of the `phase-40k-readiness.v1` manifest
([`MigrationReadinessManifest.source_dataset` → `SourceDatasetSection`],
`app/models/migration_readiness.py`) and evaluates their declared states through the
`DATASET_FINGERPRINT` / dataset checks in
`app/services/migration_readiness_preflight.py`. **[REPO-PROVEN]** The RDIR is the
operator instance of that section plus the custody context the manifest references but
does not store.

### 1.2 Required identity evidence

For each field: the manifest field it maps to (where one exists), the verification
rule, and its evidence tier. A **filename or path alone is never identity**
(runbook §3). **[REPO-PROVEN]** that these fields exist in-contract; **[OPERATOR-REQUIRED]**
that any real value is true.

| Identity claim | Manifest field (`source_dataset.*` unless noted) | Verification rule | Tier |
| --- | --- | --- | --- |
| Logical dataset name | `non_secret_locator` (safe alias) | Reviewer resolves the alias to exactly one dataset; the alias exposes no secret path. | OPERATOR-REQUIRED |
| Environment | (custody reference) | Named explicitly (e.g. production vs staging); ambiguity fails closed. | ENVIRONMENT-DEPENDENT |
| Owner / responsible operator | `operator_acknowledgement`, `reviewer_acknowledgement` | Two named humans acknowledge; no anonymous ownership. | OPERATOR-REQUIRED |
| Persistence technology & format | `format` | One format Phase 40F supports (`memory_migration_parser.py`); others are out of scope. | REPO-PROVEN (accepted set) / OPERATOR-REQUIRED (which) |
| Authoritative location (safe) | `non_secret_locator` | Non-secret canonical locator; no sensitive absolute production path in Git. | ENVIRONMENT-DEPENDENT |
| Workspace / project / scope | `destination.project_id`, `destination.scope` (destination side) | Exact project id and authorized scope member; no hierarchy or location inference (runbook §3). | OPERATOR-REQUIRED |
| Schema / contract version | `repository.execution_commit`, `pipeline.*_identity` | Exact commit and parser/projection/assessment/spec identities recorded. | REPO-PROVEN (identities exist) / OPERATOR-REQUIRED (which commit) |
| Dataset revision / generation | `source_revision_or_export_id` | Source-supplied export id/revision/version where applicable. | OPERATOR-REQUIRED |
| Creation / update metadata | `captured_at_trusted_utc` | Trusted UTC timestamp; a naive/absent clock fails closed (§2.4, `_trusted_time_check`). | OPERATOR-REQUIRED |
| Expected record / object counts | `object_count`, `byte_size`, `expected_counts.*` | Recomputed read-only where safely obtainable; no silent omission. | OPERATOR-REQUIRED |
| Integrity fingerprint / manifest strategy | `digest`, `digest_algorithm`, `reviewed_digest` | Canonical lowercase-hex SHA-256/512 over approved bytes; `reviewed_digest` mismatch is the conflicting-fingerprint stop. | REPO-PROVEN (rule) / OPERATOR-REQUIRED (value) |
| Access boundary | `custody_notes_reference` | Access restrictions recorded by reference, not inline. | OPERATOR-REQUIRED |
| Sensitivity classification | (custody reference) | Explicit classification label; drives handling. | OPERATOR-REQUIRED |
| Provenance for each claim | `custody_notes_reference` | Every identity claim cites where it came from. | OPERATOR-REQUIRED |
| Unresolved identity fields | manifest `not_supplied` sentinels | Enumerated explicitly; absence is honest, not skipped. | OPERATOR-REQUIRED |

### 1.3 Integrity-fingerprint rule (repository-anchored)

Dataset digests must be **canonical lowercase hexadecimal** of exactly the length the
declared `sha256`/`sha512` algorithm produces; MD5/SHA-1, aliases, case variants,
whitespace, and malformed digests are rejected fail-closed
(`ACCEPTED_DIGEST_ALGORITHMS`, `looks_like_secret` hex exemption in
`migration_readiness.py`; digest-canonicality checks in
`migration_readiness_preflight.py`). **[REPO-PROVEN]** For a multi-object set, use the
implementation-approved bundle identity, **not** operator-invented concatenation
(runbook §3). The `reviewed_digest` companion field lets the preflight represent the
runbook's "conflicting dataset fingerprints" stop condition when the fingerprint at
review differs from the fingerprint at preflight. **[REPO-PROVEN]**

### 1.4 What must never be committed

Real secrets, credentials, tokens, connection strings, private keys, sensitive
absolute production paths, raw records, or **fabricated redacted examples that could
be mistaken for verified facts.** Placeholders are permitted only when unmistakably
labeled as operator-supplied. The manifest enforces this defensively: `PLACEHOLDER_MARKERS`
and `SECRET_MARKERS` cause a supplied operational value to be **rejected**
(fail-closed), not normalized (`looks_like_placeholder`, `looks_like_secret` in
`migration_readiness.py`). **[REPO-PROVEN]**

---

## 2. Dataset Identity Verification Procedure

A deterministic, **read-only** procedure confirming the selected dataset is the
intended authoritative source. A matching path alone is **never** sufficient proof.

### 2.1 Evidence sources

1. The operator-supplied RDIR (§1).
2. Read-only recomputation of safe metadata in an approved environment. The runbook
   supplies the only sanctioned safe commands (runbook §3): **[REPO-PROVEN]**
   ```powershell
   Get-Item -LiteralPath '<approved-source-path>' | Select-Object Length, LastWriteTimeUtc
   Get-FileHash -Algorithm SHA256 -LiteralPath '<approved-source-path>'
   ```
   These establish byte size, last-write time, and a digest **only**; they do not
   establish bundle semantics, custody, approval, or truth, and must not be run
   against a path not explicitly in scope. **[OPERATOR-REQUIRED]** to select the path.
3. The source system's own export id / revision / version, where the source can
   supply it.
4. The pipeline identity the dataset will flow through
   (`pipeline.parser_identity` etc.) recorded at the exact `execution_commit`.

### 2.2 Comparison rules

- Recomputed `byte_size`, `object_count`, and `digest` must equal the RDIR values
  under the **same** declared algorithm.
- `digest` (preflight) vs `reviewed_digest` (review) must be equal; inequality is
  `conflicting` and a stop. **[REPO-PROVEN]** (the preflight raises the conflicting
  state for mismatched fingerprints).
- `non_secret_locator` must resolve to exactly one dataset object/set.
- The declared `format` must be one Phase 40F accepts.

### 2.3 Acceptable vs unacceptable mismatches

- **Acceptable:** only differences the source system provably attributes to a benign,
  documented cause (e.g. a new export id with an identical digest of identical bytes).
  Even here the reviewer records the reconciliation.
- **Unacceptable (fail closed):** any digest change, size change, object-count change,
  locator resolving to zero or multiple datasets, weak/aliased algorithm, or a
  fingerprint conflict between review and preflight.

### 2.4 Ambiguity, conflict, and fail-closed behavior

- **Ambiguity** (locator resolves to more than one candidate, or a field is
  `not_supplied` where identity requires it) → stop; do not guess. The manifest's
  honest-absence states (`not_supplied` / `unverified`) drive a **`blocked`** result,
  never a pass (`migration_readiness.py` docstring; `_state_check`). **[REPO-PROVEN]**
- **Conflict** (two values that must agree do not) → `conflicting` / **rejected**
  (`fail_closed`). Deceptive inputs (placeholder/fixture/secret-like, malformed
  timestamp, weak digest) are rejected, not blocked. **[REPO-PROVEN]**
- **Trusted time** is mandatory: a naive or absent clock fails closed
  (`_trusted_time_check`). **[REPO-PROVEN]**

### 2.5 Operator sign-off, retention, and re-verification triggers

- **Sign-off:** the `operator_acknowledgement` and `reviewer_acknowledgement` fields
  must both name a human; identity is a two-person confirmation, not a single actor's
  assertion (runbook §1 role separation). **[OPERATOR-REQUIRED]**
- **Evidence retention:** the RDIR, recomputation output, and reconciliation notes are
  retained in the access-controlled operational evidence location (runbook §9), never
  Git. Retain at least through any downstream acceptance plus the org-approved
  rollback window.
- **Re-verification triggers:** any change to source bytes, export id, `execution_commit`,
  pipeline identity, or elapsed time beyond the `--max-age-seconds` staleness bound
  (`migration_readiness_cli`) forces a fresh verification. **[REPO-PROVEN]** (staleness
  bound exists) / **[OPERATOR-REQUIRED]** (the actual events).

---

## 3. Production Persistence Interface Confirmation

Reconciles this plan with the **exact** boundary Phase 40K.5 established. No production
adapter is implemented and no production infrastructure is connected here.

### 3.1 What the repository proves — [REPO-PROVEN]

- The read-only preflight `MigrationReadinessPreflight.evaluate(manifest, now)` holds
  **no** store, holder, ledger, snapshot, lock, attempt, receipt, or
  authorization-registry reference and reads no filesystem/network resource; it is
  read-only *by construction* (40K.5 interface §1).
- The execution decision is a **separate** boundary:
  `ReviewedMigrationExecutionGate` defaults to refusal and clears only with an
  explicit `OperationalExecutionAuthorization`, an operational (non-fixture) marking,
  no placeholder/secret text, an explicit devdevbuilds go, the exact manifest
  identity, and a `pass` preflight (40K.5 interface §4).
- **No executor is wired** in 40K.5; even a cleared decision performs no work. In a
  separately authorized Phase 40L a cleared decision would dispatch to the existing
  Phase 40I coordinator `MemoryMigrationImportService.import_reviewed_candidate`
  through an injected executor (40K.5 interface §4).
- The two authoritative artifacts a migration touches are the **Active Memory
  snapshot** and the **migration workflow ledger**, separately integrity-sealed and
  sharing a commit generation (runbook §2; `active_memory_snapshot_store.py`,
  `memory_migration_import_store.py`, `migration_import_lock.py`,
  `migration_import_paths.py`).

### 3.2 What remains abstract / environment-dependent — [ENVIRONMENT-DEPENDENT]

- The real ledger and snapshot **paths** (resolved only through approved runtime
  configuration; only safe aliases are ever recorded — runbook §4).
- Destination identity, revision, generation, capacity, and multi-host writer
  exclusion (the single-process/file lock is **not** proof every host is stopped —
  runbook §4.1).
- Any real production adapter or read-only orchestration over live data
  (`preflight.production_read_only_orchestration_state` is `blocked` by default —
  `migration_readiness.py`).

### 3.3 Required adapter / operator inputs — [OPERATOR-REQUIRED] / [FUTURE-AUTHORIZED]

- Approved runtime configuration resolving ledger/snapshot locations.
- Approved service-control (writer-stop) procedure.
- An approved, complete, and auditable implementation plan and contract for wiring the
  existing execution gate to the Phase 40I coordinator and introducing the operational
  migration command (the standing blocker in runbook §12). The plan/contract must
  specify fail-closed behavior, exact authorization consumption, durable revocation
  handling, bounded audit evidence, validation, and rollback expectations.
- Implementing or validating that plan is **[FUTURE-AUTHORIZED]** Phase 40L work, out
  of scope here. Phase 40L may implement the wiring and command only after separate
  operator authorization; authorization to implement them is not authorization to
  execute a production migration.

### 3.4 Source/destination identity, compatibility, prohibited assumptions

- Source identity comes from the RDIR (§1); destination identity from
  `destination.non_secret_identity` / `project_id` / `scope` / `ledger_revision` /
  `commit_generation`.
- **Compatibility check:** the destination `commit_generation` and `ledger_revision`
  observed read-only must equal what authorization review recorded; `observed_ledger_revision`
  vs `ledger_revision` mismatch is a stop (`DestinationSection`; 40K.5 interface §1).
  **[REPO-PROVEN]**
- **Prohibited assumptions:** never infer project/scope from repository location; never
  treat repository approval or PR merge as runtime authority; never assume a path is
  correct because it "looks right." **[REPO-PROVEN]** (runbook §1, §6).

### 3.5 Fail-closed conditions

Any `not_supplied` / `unverified` operational field, any placeholder/secret-like
value, any digest or revision conflict, or an absent trusted clock yields `blocked`
or `fail_closed`. Do not implement a production adapter or connect to production
infrastructure in this phase.

---

## 4. Backup Inventory and Integrity Checklist

How backups are **inventoried and assessed without altering them.** No backup is
created, mutated, rotated, deleted, or restored in this phase. The `backup` manifest
section (`BackupSection`) and the `BACKUP_IDENTITY` / `BACKUP_VERIFICATION` /
`RESTORATION_READINESS` preflight checks
(`migration_readiness_preflight.py`) are the repository anchors. **[REPO-PROVEN]**

### 4.1 Per-backup inventory fields

| Attribute | Manifest anchor (`backup.*`) | Rule | Tier |
| --- | --- | --- | --- |
| Backup identifier | `non_secret_backup_id` | Safe non-secret id; naming per runbook §4 (`hivemind-memory-backup_<UTC-basic>_gen-<N>_<short-digest>`). | OPERATOR-REQUIRED |
| Source dataset identity | (links to §1 RDIR + `source_generation`) | The exact ledger + snapshot generation the backup covers. | OPERATOR-REQUIRED |
| Creation time (trusted) | `created_at_trusted_utc` | From a trusted clock, not local wall time. | OPERATOR-REQUIRED |
| Backup format | (custody reference) | Store loader-compatible; parseable by the same loaders. | OPERATOR-REQUIRED |
| Storage location (safe) | `retention_and_access_reference` | Alias only; access-controlled, non-source, non-runtime medium. | ENVIRONMENT-DEPENDENT |
| Encryption status | (custody reference) | Recorded; key availability tracked in §7 assumptions. | ENVIRONMENT-DEPENDENT |
| Retention state | `retention_and_access_reference` | Retention window recorded; owner sets duration. | OPERATOR-REQUIRED |
| Completeness evidence | `state`, `ledger_digest`, `snapshot_digest` | Both authoritative artifacts present; no partial capture. | OPERATOR-REQUIRED |
| Integrity evidence | `integrity_state` | SHA-256 pairwise equality of originals and copies (runbook §4). | OPERATOR-REQUIRED |
| Readability | `readability_state` | Copies load via the same store loaders in an isolated read-only environment. | OPERATOR-REQUIRED |
| Compatibility | `digest_algorithm`, generation | Loader/version compatible; equal commit generation across envelopes. | OPERATOR-REQUIRED |
| Dependency requirements | (custody reference) | Any tool/version needed to read the backup. | ENVIRONMENT-DEPENDENT |
| Chain relationships (incremental) | `source_generation` | For incrementals, the base and chain are identified and complete. | OPERATOR-REQUIRED |
| Freshness | `created_at_trusted_utc` vs RPO | Assessed against the §7 RPO window. | OPERATOR-REQUIRED |
| Recovery-point implications | (derived) | What data-loss window this backup implies if restored. | OPERATOR-REQUIRED |
| Custody / ownership | `retention_and_access_reference` | Named owner and access boundary. | OPERATOR-REQUIRED |
| Evidence gaps | manifest `not_supplied` / `unverified` | Explicitly enumerated; unknown stays unknown. | OPERATOR-REQUIRED |

### 4.2 The five states that are NOT synonyms

The runbook (§4, §5) and this plan treat these as strictly distinct; infrastructure
tooling routinely and wrongly collapses them into "we have a backup." **[REPO-PROVEN]**
that the manifest keeps `integrity_state`, `readability_state`, and
`isolated_restoration_rehearsal_state` as separate fields precisely to prevent this
collapse.

1. **A file exists** — a path is present. Proves nothing about contents.
2. **A backup is readable** — the copy loads via the store loaders. `readability_state`.
3. **A backup passes integrity validation** — envelope integrity digests verify and
   generations match. `integrity_state`.
4. **A backup is restoration-capable** — it *could* be restored into an isolated
   target (all §5 prerequisites met). Not yet demonstrated.
5. **A backup has been successfully restored in isolation** — the §6 rehearsal ran and
   reconciled. `isolated_restoration_rehearsal_state` = `verified`, achievable only by
   the **[FUTURE-AUTHORIZED]** rehearsal, never in this phase.

A `verified` `BACKUP_VERIFICATION` check requires **both** `integrity_state` **and**
`readability_state` = `verified`; `RESTORATION_READINESS` requires
`isolated_restoration_rehearsal_state` = `verified` separately
(`_backup_verification_check`, `RESTORATION_READINESS` state check). **[REPO-PROVEN]**

---

## 5. Restoration Readiness Verification Plan

Checks required **before** an isolated restoration rehearsal may be authorized. The
rehearsal itself is **not** executed here (§6, §0).

| # | Check | Rule | Tier |
| --- | --- | --- | --- |
| 1 | Backup selection | Choose the integrity-valid, readable backup whose `source_generation` is not older than any newer accepted state (runbook §5 backup-restoration rule). | OPERATOR-REQUIRED |
| 2 | Restoration tooling & version | Exact store loaders / tooling and versions the backup requires are identified and available. | ENVIRONMENT-DEPENDENT |
| 3 | Isolated target | A disposable root that **cannot** collide with configured authoritative paths (runbook §5). | ENVIRONMENT-DEPENDENT |
| 4 | Permissions & credentials | Least-privilege access to the backup and the disposable target only; via approved mechanisms, never inline secrets. | OPERATOR-REQUIRED |
| 5 | Capacity & resources | Disposable target has sufficient space/resources; failing this is a stop, not a reason to delete evidence. | ENVIRONMENT-DEPENDENT |
| 6 | Dependencies | All runtime dependencies to load ledger + snapshot present. | ENVIRONMENT-DEPENDENT |
| 7 | Expected restoration outputs | The exact records/counts/generation the restore should reproduce are declared in advance. | OPERATOR-REQUIRED |
| 8 | Post-restore identity comparison | Restored dataset identity is compared to the RDIR (§1) and to expected outputs. | OPERATOR-REQUIRED |
| 9 | Integrity & completeness | Both envelope integrity digests verify; generations match or the implemented N/N+1 case is classified (runbook §5). | REPO-PROVEN (rule) / OPERATOR-REQUIRED (result) |
| 10 | Functional / read-only validation | Read-only reconciliation of records/counts; **never** publish the authoritative holder. | REPO-PROVEN (must-not-publish) / OPERATOR-REQUIRED (result) |
| 11 | Cleanup | Only disposable copies are destroyed, and only after evidence is retained. | FUTURE-AUTHORIZED |
| 12 | Evidence capture | Deterministic evidence package (backup alias, tooling, config, digests, reconciliation). | OPERATOR-REQUIRED |
| 13 | Stop conditions | Any integrity failure, generation mismatch (outside N/N+1), or reconciliation gap stops the rehearsal. | REPO-PROVEN (matrix) |
| 14 | Failure classification | Classify per runbook §10 recovery matrix (pre-write, no-write, partial, N/N+1, corrupt/conflicting). | REPO-PROVEN (matrix) |
| 15 | Escalation path | Backup owner remediates; reviewer/recovery decision-maker repeats or reclassifies (runbook §8, §10). | OPERATOR-REQUIRED |

A hash match alone proves byte equality, **not** restorability (runbook §4.7); only
checks 8–10 in a real rehearsal establish restorability.

---

## 6. Isolated Restoration Rehearsal Contract — [FUTURE-AUTHORIZED]

Defines a future, **separately authorized** rehearsal. It is specified here; it is
**not** run in Phase 40K.6.

### 6.1 Isolation guarantees (authorization boundary)

The rehearsal **must**:

- use a **disposable, isolated destination** root that cannot collide with any
  configured authoritative ledger/snapshot path (runbook §5); **[REPO-PROVEN]** the
  requirement, **[ENVIRONMENT-DEPENDENT]** the root;
- be structurally incapable of overwriting or mutating the authoritative dataset (no
  authoritative path is writable in the rehearsal context);
- be unmistakable from production (distinct naming, distinct root, recorded disposable
  marker);
- prevent accidental network/service attachment where appropriate (no live holder
  publication; the rehearsal **never** publishes the authoritative holder — runbook §5);
- run under **least privilege** (read the backup, write only the disposable target).

### 6.2 Determinism and evidence

The rehearsal records: the exact backup input (`non_secret_backup_id`, digests,
`source_generation`); restoration tooling and configuration; restored identity vs RDIR;
envelope integrity and generation results; exact record/count reconciliation; and a
deterministic evidence package suitable for independent audit. It then applies the
cleanup/disposal rules (§5 #11) and requires explicit operator authorization before it
may execute.

### 6.3 Evidence needed to prove isolation

- The disposable root path (safe alias) and proof it is disjoint from every configured
  authoritative path.
- Confirmation no authoritative store loader was pointed at an authoritative path.
- Confirmation the authoritative holder was never published.
- The least-privilege grant used.

Until such a rehearsal is separately authorized and passes, every manifest
`backup.isolated_restoration_rehearsal_state` is `unverified` and `RESTORATION_READINESS`
is not `verified`. **[REPO-PROVEN]** default.

---

## 7. Recovery Assumptions and Operator Decisions

Explicit planning assumptions. **No approved RPO/RTO values exist in the repository**;
they are recorded here as **[OPERATOR-REQUIRED] decisions**, not invented numbers.

| Assumption | Status | Impact if unset | Tier |
| --- | --- | --- | --- |
| Recovery Point Objective (acceptable data-loss window) | **Required operator decision — no approved value** | Backup freshness (§4.1) cannot be judged; restoration selection (§5 #1) is unbounded. | OPERATOR-REQUIRED |
| Recovery Time Objective (restoration-time expectation) | **Required operator decision — no approved value** | Rehearsal/restore duration cannot be judged adequate. | OPERATOR-REQUIRED |
| Backup freshness bound | Required operator decision | Determines when a backup is too stale to trust. | OPERATOR-REQUIRED |
| Retention window | Required operator decision (runbook §4: "human owner sets the actual duration") | Determines how long backups + evidence are kept. | OPERATOR-REQUIRED |
| Backup redundancy | Required operator decision | Single-copy backups are a single point of failure. | ENVIRONMENT-DEPENDENT |
| Encryption / key availability | Required operator input | An encrypted backup with an unavailable key is not restoration-capable. | ENVIRONMENT-DEPENDENT |
| Restoration tooling availability | Required operator input | Missing loaders/versions block the rehearsal. | ENVIRONMENT-DEPENDENT |
| Operator availability | Required operator input | Two-person review + recovery decisions need named humans. | OPERATOR-REQUIRED |
| Acceptable degraded conditions | Required operator decision | Defines what partial state, if any, is tolerable. | OPERATOR-REQUIRED |

Do not proceed past `CONDITIONALLY READY` while RPO/RTO remain unset: without them,
"the backup is fresh enough" and "restoration is fast enough" are unjudgeable claims.

---

## 8. Production-Migration Prerequisite / Blocker Register

Structured register. "Blocks rehearsal" = blocks the §6 isolated restoration rehearsal;
"Blocks 40L" = blocks Phase 40L authorization. Unknown production information stays
explicitly unknown.

| ID | Description | Evidence required | Responsible role | Status | Severity | Blocks rehearsal | Blocks 40L | Resolution needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B-01 | Authoritative real dataset identity unestablished | Verified RDIR (§1) | Operator + Reviewer | Open | Critical | Yes | Yes | Instantiate + independently verify RDIR |
| B-02 | RPO/RTO not defined | Recorded operator decision (§7) | devdevbuilds / owner | Open | Critical | Yes | Yes | Approve RPO/RTO values |
| B-03 | Backup inventory absent/incomplete | Completed §4 inventory | Backup owner | Open | Critical | Yes | Yes | Inventory + integrity-assess backups |
| B-04 | Selected backup integrity/readability unverified | `integrity_state` + `readability_state` = verified | Backup owner + Reviewer | Open | Critical | Yes | Yes | Run §4 integrity + readability checks |
| B-05 | Isolated restoration rehearsal not executed | Passed §6 rehearsal evidence package | Operator + Recovery DM | Open | Critical | Is the rehearsal | Yes | Separately authorize + run §6 |
| B-06 | Restoration tooling/version availability unknown | §5 #2/#6 evidence | Platform owner | Open | High | Yes | Yes | Confirm loaders/versions |
| B-07 | Isolated disposable target unavailable | §5 #3/#5 evidence | Platform owner | Open | High | Yes | Yes | Provision disposable, disjoint target |
| B-08 | Production persistence paths resolve only via runtime config | Safe aliases (§3.2) | Deployment owner | Open | High | No | Yes | Approve runtime config + writer-stop procedure |
| B-09 | Multi-host writer exclusion unproven (lock is single-process) | Approved service-control proof | Deployment owner | Open | High | No | Yes | Approve + evidence writer stop |
| B-10 | Approved Phase 40L wiring/command implementation plan and contract absent | Approved, complete, auditable plan/contract covering gate-to-coordinator wiring, operational command, fail-closed behavior, authorization consumption, revocation handling, audit evidence, validation, and rollback (runbook §12) | devdevbuilds | Open | Critical | No | Yes | Approve the plan/contract before considering Phase 40L implementation authorization |
| B-11 | Runtime authorization/trusted-clock/revocation results absent | Live auth ceremony evidence (runbook §6) | Auth issuer | Open | Critical | No | Yes | Perform authorization ceremony at execution time |
| B-12 | Private evidence destination unconfirmed | Access-controlled writable location | Evidence custodian | Open | Medium | Partial | Yes | Approve evidence destination |
| B-13 | Encryption key availability unknown | Key-availability evidence (§7) | Platform owner | Open | Medium | Yes (if encrypted) | Yes | Confirm key custody |

All rows are **Open**. None is resolved by this document.

---

## 9. Phase 40L Go/No-Go Gate

Concrete, auditable criteria for **considering** Phase 40L authorization. **Phase 40K.6
never returns "authorized for Phase 40L."** Every criterion must independently hold;
each maps to evidence, not assertion.

| # | Criterion | Cleared when | Current |
| --- | --- | --- | --- |
| 1 | Authoritative dataset identity established | RDIR verified, two-person acknowledged (§1–2) | **Not met** (B-01) |
| 2 | Production persistence implementation contract approved | §3 inputs supplied; the complete, auditable wiring/command implementation plan and contract described by B-10 are approved | **Not met** (B-08, B-10) |
| 3 | Backup inventory complete for scope | §4 inventory complete | **Not met** (B-03) |
| 4 | Selected backup integrity verified | `integrity_state` + `readability_state` verified | **Not met** (B-04) |
| 5 | Restoration rehearsal separately executed and passed | §6 evidence package; `isolated_restoration_rehearsal_state` verified | **Not met** (B-05) |
| 6 | Source/destination compatibility established | §3.4 revision/generation match | **Not met** |
| 7 | Rollback path validated | §5/§6 restoration proven; runbook §5 restoration rule satisfied | **Not met** |
| 8 | Authorization inputs complete | Runbook §6 ceremony evidence | **Not met** (B-11) |
| 9 | Credentials/access via approved mechanisms | Least-privilege grants recorded | **Not met** |
| 10 | Unresolved critical blockers = 0 | §8 register has zero open Critical rows | **Not met** (multiple) |
| 11 | Operator approval recorded | devdevbuilds go in private packet | **Not met** |
| 12 | Migration window + abort conditions defined | Window + abort criteria recorded | **Not met** |

With criteria 1–12 unmet, **Phase 40L is not eligible for consideration.** This gate is
a checklist for a *future* human decision, not a decision this phase makes.

If every criterion is later met, the resulting decision may authorize **Phase 40L
implementation only**. After that separate operator authorization, Phase 40L may
implement and validate the cleared-gate-to-coordinator wiring and operational migration
command under the approved contract. Implementing, testing, or validating those
components grants no authority to execute against production.

Before any real migration command may run, the Phase 40L implementation and its tests
and validation must be complete, every critical blocker must remain resolved, and the
execution gate must make a fresh fail-closed decision against the exact current
manifest and operational authorization. Production execution still requires its own
explicit operator go; an implementation authorization or successful validation is
never an execution authorization.

---

## 10. Repository Evidence Traceability

Every interface claim above is anchored to committed source at baseline `b46b983`:

| Claim area | Repository anchor |
| --- | --- |
| Readiness manifest contract, field-state vocabulary, placeholder/secret rejection | `apps/backend/app/models/migration_readiness.py` (`MigrationReadinessManifest`, `FieldState`, `SourceDatasetSection`, `BackupSection`, `looks_like_placeholder`, `looks_like_secret`, `ACCEPTED_DIGEST_ALGORITHMS`) |
| Read-only preflight, backup/restoration check IDs, digest canonicality, trusted-time fail-close | `apps/backend/app/services/migration_readiness_preflight.py` (`BACKUP_IDENTITY`, `BACKUP_VERIFICATION`, `RESTORATION_READINESS`, `_backup_verification_check`, `_trusted_time_check`) |
| Read-only CLI, exit codes, staleness bound | `apps/backend/app/console/migration_readiness_cli.py` |
| Fail-closed execution gate | `apps/backend/app/services/migration_execution_gate.py` (`ReviewedMigrationExecutionGate`) |
| Phase 40I coordinator (executor target, not wired) | `apps/backend/app/services/memory_migration_import.py` (`MemoryMigrationImportService.import_reviewed_candidate`) |
| Two-store + snapshot model, lock, paths | `active_memory_snapshot_store.py`, `memory_migration_import_store.py`, `migration_import_lock.py`, `migration_import_paths.py` |
| Dataset identity, backup readiness, restoration/rollback, authorization ceremony, stop conditions, recovery matrix | `docs/operations/phase-40k-authoritative-migration-runbook.md` §3–§10 |
| Manifest interface, preflight/gate separation, blocked operational fields | `docs/operations/phase-40k-5-migration-readiness-interface.md` §1–§7 |
| Fail-closed manifest instance | `docs/operations/phase-40k-readiness.template.json` |
| Operator checklist | `docs/operations/phase-40k-operator-checklist.md` |

**Distinguished explicitly:** §0.1 tags every claim REPO-PROVEN / OPERATOR-REQUIRED /
ENVIRONMENT-DEPENDENT / FUTURE-AUTHORIZED. No production path, dataset identity,
fingerprint, owner, backup, RPO/RTO value, or restoration result is asserted as fact.

---

## 11. Backup / Restoration Readiness Conclusion and Non-Authorization

### 11.1 Conclusion — `CONDITIONALLY READY`

The repository proves the **form** of dataset-identity and backup/restoration
readiness — the manifest contract, the read-only preflight, the fail-closed gate, the
five-state backup distinction, and the isolation rules. It cannot and does not prove
any **real-world** dataset identity, backup existence, integrity, readability, or
restorability. Those are `not_supplied` / `unverified` operator and environment inputs
(§8 blockers B-01–B-13, all Open), and RPO/RTO (§7) are undefined. The planning inputs
are therefore **not** genuinely sufficient to declare `READY FOR RESTORATION REHEARSAL
IMPLEMENTATION`; the correct documentation verdict is **`CONDITIONALLY READY`**, and it
becomes `READY FOR RESTORATION REHEARSAL IMPLEMENTATION` only after B-01, B-02, B-03,
B-04, B-06, B-07 (and B-13 if encrypted) are closed with verified evidence.

### 11.2 Explicit non-authorization statement

**Phase 40K.6 authorizes nothing.** It performs no production migration, no production
import, no write to any authoritative dataset, no restoration, and no backup mutation.
It does not read or connect to production infrastructure. Passing Phase 40K.6 — or any
repository review or PR merge of it — confers **no** runtime authority and does **not**
authorize the isolated restoration rehearsal, Phase 40K.7, or **Phase 40L**. Phase 40L
remains **locked** and requires a separate, explicit devdevbuilds go decision made
only after every §9 criterion is independently satisfied. Repository approval is never
dataset authorization.
