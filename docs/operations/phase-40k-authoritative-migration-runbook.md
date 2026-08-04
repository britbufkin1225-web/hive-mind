# Phase 40K — Authoritative Migration Runbook + Execution Readiness

**Runbook version:** `phase-40k-runbook.v1`

**Repository baseline:** `c6e016986d43236a8bf747604986a9ea4e19490d`

**Status:** repository procedure implemented; **operational readiness blocked**
**Companion artifacts:** [operator checklist](phase-40k-operator-checklist.md) and
[fail-closed readiness template](phase-40k-readiness.template.json)

## 1. Authority, purpose, and boundary

This is the canonical human-operated procedure for preparing a separately authorized
future migration of a reviewed dataset into authoritative Active Memory. Phase 40F
verifies and parses declared bytes and projects inactive candidates; 40G assesses the
complete candidate set without mutation; 40H specifies the review/import contract;
40I implements the human-gated ledger, snapshot, authorization, receipt, recovery, and
publish-last coordinator; 40J rehearses those seams only with synthetic disposable
data. Phase 40K turns that implementation truth into operating controls. It does not
run a production migration.

Repository readiness means the procedure and fail-closed template are reviewable.
Operational readiness means every real-world field in an instantiated template has
been independently verified immediately before execution. This repository supplies
no production migration CLI and no genuinely read-only production preflight entry
point. Consequently the checked-in template is `blocked`, and Phase 40L may not start
until an approved execution interface and the missing operational facts exist.

Roles are separate even when one person holds more than one role:

| Role | Authority and responsibility |
| --- | --- |
| Operator | Collects evidence, runs only independently confirmed commands, observes, and stops on ambiguity. Does not self-authorize. |
| Reviewer | Confirms dataset identity, assessment, exclusions, expected mutations, evidence, and command independently. |
| Authorization issuer | Issues exact immutable project/scope/specification-bound runtime authorization through the supported contract. Does not infer approval from repository state. |
| Recovery decision-maker | Classifies outcomes from durable facts and authorizes retry, recovery, or restoration. |
| devdevbuilds | Human decision-maker, merge gate, and final go/no-go authority. Repository approval is not dataset authorization; PR merge is not runtime authorization. |

Preparation ends after a complete readiness packet receives a human no-go/go decision.
Execution begins only in separately authorized **Phase 40L — Authorized Production
Migration Execution + Acceptance Evidence**. Missing, ambiguous, expired, revoked, or
mismatched authorization fails closed. Human decisions include source selection,
candidate meaning, approval/exclusion, authorization issuance, go/no-go, recovery,
restoration, and acceptance. Runtime validation supports those decisions; it does not
replace them.

## 2. Implementation truth and supported guarantees

- Only `memory_migration_parser.py` reads Phase 40F artifact bytes, after the Phase
  40E assessment permits the exact bundle fingerprint; it recomputes size/digest.
- Projection and 40G assessment are deterministic. Candidates remain inactive,
  unverified, human-review-required, and non-persistable until reviewed import.
- `ReviewedImportSpecification` supplies kind, structured claim, observed time, and
  project; none is guessed from a candidate. The review decision and specification
  bind exact candidate/report identities and content digests.
- `ProjectScopeAuthorizationValidator` uses an injected trusted UTC clock, exact
  project equality, exact scope membership, immutable issuance lineage, integrity,
  expiry, and the durable revocation registry. Missing authorization returns
  `missing_authorization` before storage or publication.
- The workflow ledger and Active Memory snapshot are separately integrity-sealed and
  share a commit generation. The coordinator takes the exclusive lock, persists
  intent, builds a private candidate store, persists and verifies the next snapshot,
  commits and verifies the receipt, then publishes the live holder last.
- A receipt identifies the exact attempt and record; its integrity digest covers its
  full persisted content. Exact replay returns the stored receipt unchanged.
- N/N+1 recovery is a narrow durable-state exception: after both envelopes pass
  integrity checks, ledger generation N with intent and snapshot generation N+1 can
  be finalized from disk. Other ambiguous or corrupt states quarantine and require a
  human recovery decision. This is not filesystem-level atomicity or magical undo.
- Phase 40J proves these behaviors only over deterministic synthetic disposable data.
  It does not prove production paths, capacity, credentials, multi-host exclusion,
  backup readability, or real dataset identity.

There is no supported production command to list here. Directly importing backend
classes from an ad-hoc shell is **prohibited**. The execution command must be introduced
or approved separately, reviewed against these contracts, recorded byte-for-byte in
the operational packet, and independently confirmed before Phase 40L.

## 3. Dataset identity manifest

Instantiate the JSON template outside Git and keep secrets/private paths out of it.
All applicable fields below are mandatory; a filename is never identity.

| Required identity | Verification rule |
| --- | --- |
| Non-secret canonical locator and format | Reviewer resolves it to exactly one source object/set; format is one supported by Phase 40F. |
| Byte size and file/object count | Recomputed read-only at final preflight; no silent omissions. |
| Digest and algorithm | SHA-256 or SHA-512 (the implemented accepted algorithms; MD5/SHA-1 are rejected as weak) recomputed over the approved artifact bytes under the algorithm the export declared; for a set, use the implementation-approved bundle identity, not concatenation invented by an operator. |
| Capture time and source version | Trusted UTC timestamp plus export id/revision/version supplied by the source where applicable. |
| Implementation identity | Exact repository commit and identities/versions of intake, parser, projector, assessor, reviewed-import contracts, and runbook. |
| Project and scope | Exact project id and authorized scope member; no hierarchy or repository-location inference. |
| Expected results | Total projected candidates and explicit approved/imported, rejected, skipped, excluded, and unresolved counts. |
| Custody | Origin, transfers, access restrictions, and operator/reviewer acknowledgements without private content. |

For a single locally available artifact, an operator may capture safe metadata
read-only in an approved environment:

```powershell
Get-Item -LiteralPath '<approved-source-path>' | Select-Object Length, LastWriteTimeUtc
Get-FileHash -Algorithm SHA256 -LiteralPath '<approved-source-path>'
```

These commands do not establish bundle semantics, custody, approval, or truth. Do not
run them against a path that has not been explicitly placed in scope. The real dataset
was unavailable in Phase 40K, so no real identity was captured.

## 4. Backup readiness

Back up both authoritative artifacts immediately before execution: the exact active
memory snapshot and exact migration workflow ledger resolved by the approved runtime
configuration. Also retain their revisions/generations and non-secret configuration
identity. Never copy authorization secrets into the evidence packet.

1. Stop or exclude every authoritative writer using the deployment's approved
   service-control procedure. The implementation lock is single-process/file based;
   it is not evidence that every host is stopped.
2. Resolve the ledger and snapshot paths through the approved runtime configuration.
   Record only safe locator aliases in shared evidence.
3. Create a new, access-controlled, non-source, non-runtime backup directory named
   `hivemind-memory-backup_<UTC-basic>_gen-<N>_<short-digest>`. Refuse an existing name.
4. Copy both files without overwriting. Preserve the originals. The exact copy command
   is deployment-specific and remains blocked until paths, writer-stop procedure, and
   backup medium are approved; do not improvise it from this document.
5. Hash originals and copies with SHA-256 and require pairwise equality. Parse copies
   using the same store loaders in an isolated, read-only restoration environment;
   validate both envelope integrity digests and equal commit generation.
6. Record source/destination revisions, generation, sizes, hashes, backup medium,
   access owner, creation time from a trusted clock, operator/reviewer, and retention.
7. Prove readability by completing the isolated restoration rehearsal in §5. A hash
   alone proves byte equality, not restorability.

Backup readiness passes only when no writer is active, originals are intact, a new
non-overwriting copy exists on an approved separate medium, hashes match, both copies
load and validate together, an isolated restoration reaches the exact expected state,
retention/access rules are recorded, and two-person review is acknowledged. Retain at
least through migration acceptance plus the organization-approved rollback window;
the human owner sets the actual duration.

## 5. Restoration, rollback, replay, and uncertain outcomes

These operations are distinct:

- **Abort before write:** stop; preserve preflight evidence. No rollback or receipt.
- **Confirmed no-write failure:** prove ledger, snapshot, live generation, and attempt
  set are unchanged. A retry needs a fresh preflight and authorization revalidation.
- **Confirmed partial failure:** quarantine. Do not delete ledger intents, attempts,
  receipts, snapshots, or logs. Recovery decision-maker uses the matrix below.
- **Uncertain commit:** acquire the approved exclusive boundary and invoke only the
  implemented recovery route. Validate both envelopes before generation comparison.
  N/N+1 may finalize the original intent/receipt and publish the verified snapshot;
  never manufacture a receipt or restore historical live state.
- **Exact replay:** only an identical idempotency binding may return the immutable
  stored receipt. Changed dataset/specification/authorization is not replay.
- **Backup restoration:** last-resort state replacement requiring explicit human
  authority and proof the target backup is not older than newer accepted state.
- **Integrity/authorization failure:** preserve evidence and quarantine/stop. Never
  edit sealed JSON, resurrect revocation, extend expiry, or retry until it passes.

An isolated restoration rehearsal must copy the backup into a disposable root that
cannot collide with configured authoritative paths, load and integrity-check ledger
and snapshot, require matching generation (or classify the implemented N/N+1 case),
restore a private Active Memory store, reconcile exact record/count identities, and
destroy only the disposable copies after evidence is retained. It must never publish
the authoritative holder. Production restoration requires writers stopped, a fresh
backup of the observed failed state, explicit target generation, proof no newer valid
accepted state would be lost, atomic approved replacement procedures, reload and
integrity verification, exact record reconciliation, service restart, and human
acceptance. Preserve the failed-state backup and the complete workflow history.

## 6. Authorization ceremony

1. Identify the exact source dataset and fingerprint.
2. Identify destination aliases, ledger/snapshot generation, and current revision.
3. Review the complete assessment and Phase 40J evidence.
4. Confirm backup and isolated restoration readiness.
5. Review exclusions, counts, exact records, and expected mutations.
6. Create or obtain exact scoped authorization through the approved runtime boundary.
7. Recompute and verify authorization identity/integrity and issuance lineage.
8. Verify the trusted server-side UTC clock is available, timezone-aware, and sane.
9. Evaluate expiry at execution time.
10. Query the integrity-valid durable ledger for revocation.
11. Verify exact project equality and exact authorized-scope membership.
12. Verify intended operator/execution context where the contract supports it; where
    it does not, record the governance check and do not claim runtime enforcement.
13. Operator and independent reviewer compare the exact execution command.
14. devdevbuilds records final human go/no-go approval in the private evidence packet.
15. Only a separately authorized Phase 40L begins execution.

The two-person checkpoint is governance, not a claimed runtime feature. Authorization
for one project, scope, dataset binding, reviewed specification, issuance, or revision
authorizes no other. Stale authorization cannot be reused; durable revocation cannot
be resurrected; repository approval and PR merge confer no runtime authority.

## 7. Dry preflight (read-only)

Complete every checklist field and set the instantiated manifest fields to `verified`.
Repository checks are supported:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check
```

The following operational checks currently have **no supported all-read-only command**:
production parser/projection/assessment over the real source, destination/load and
revision inspection, authorization validation without attempt allocation, expected
receipt derivation, capacity evaluation, and global writer exclusion. Phase 40J may be
rerun only against its deterministic disposable fixture; it is not a production
preflight. Until an approved read-only orchestration surface covers these checks, the
go/no-go result is `blocked`.

The future dry preflight must verify repository/build identity; dataset fingerprint;
parse/projection/assessment identities and counts; destination accessibility and exact
generation; backup integrity/readability; authorization presence, integrity, expiry,
revocation, project, and scope through the trusted clock/ledger; expected write set and
receipt identity; capacity; evidence destination writability without exposing secrets;
writer exclusion; recovery materials; and operator/reviewer acknowledgements. It must
not publish a holder, create/consume an attempt or receipt, mutate ledger/snapshot/source,
or change/revoke authorization.

## 8. Stop conditions

For every row: immediate default is stop and preserve evidence. Never bypass, repair
sealed state, renew authority, or retry repeatedly.

| Stop signal | Immediate action | Prohibited action | Preserve | Escalation |
| --- | --- | --- | --- | --- |
| Dataset locator/digest/size/count differs | Isolate source; recompute once read-only | Parse/import changed bytes | Both fingerprints and custody log | Reviewer re-identifies dataset; new review/authorization |
| Destination revision/generation changed or concurrent writer detected | Release/avoid lock; snapshot observations | Continue on stale expectations | Before/observed revisions, writer evidence | Recovery decision-maker classifies; repeat backup/preflight |
| Backup absent, unreadable, hash-invalid, overwriting, or rehearsal incomplete | No-go | Use only copy or claim hash means restorable | Backup metadata, errors, hashes | Backup owner remediates and reviewer repeats rehearsal |
| Authorization missing, integrity-invalid, expired, revoked, lineage-incomplete, wrong project/scope | No-go; preserve safe identifiers | Forge, renew, un-revoke, substitute, or bypass | Safe id/digest, clock result, diagnostic, ledger revision | Issuer performs a separate authorized ceremony |
| Trusted clock unavailable/naive/implausible | No-go | Use caller time or change timestamps | Clock source/error | Platform owner restores trusted clock; revalidate |
| Parse/projection/assessment or expected counts/change set differs | Stop before import | Drop unexpected records or adjust expectations during run | Diagnostics, identities, counts (no private content in Git) | Reviewer repeats assessment and approval |
| Implementation commit/command differs | No-go | Execute unreviewed code/command | Commit and command digest | Independent code/command review |
| Capacity insufficient | No-go | Delete evidence/backups or proceed partially | Capacity measurement | Platform owner provisions approved capacity |
| Ledger/snapshot/receipt integrity or receipt identity conflicts | Quarantine | Edit JSON, fabricate receipt, blind retry | Exact artifacts under private custody, hashes, diagnostics | Recovery decision-maker invokes supported recovery |
| Outcome uncertain, partial result, unexplained warning, or operator cannot explain state | Stop interaction; preserve process output and state | Retry until success or restore blindly | Logs, timestamps, attempts, generations, lock metadata | Human recovery classification using §10 |
| Evidence destination unsafe/unwritable | No-go or stop before further mutation | Redirect secrets to Git/public logs | Safe error and intended alias | Evidence custodian supplies approved destination |

## 9. Evidence packets and handling

| Packet | Minimum contents |
| --- | --- |
| Preflight | Repository/build identity, dataset fingerprint, destination revision/generation, counts, capacity, writer exclusion, checks/results, stop evaluation, trusted time, acknowledgements. |
| Authorization | Safe authorization id/digest, issuance lineage, project/scope result, expiry/revocation result, trusted time, issuer and independent confirmation. Never bearer/raw authority. |
| Backup | Backup alias/id, original/copy digests and sizes, generation, medium, readability/restoration result, retention/access owners. |
| Execution | Exact command/digest, operator, start/end trusted times, expected write set, captured output alias, observed transitions, stop decisions. |
| Receipt | Attempt and receipt ids, integrity result, record id, ledger revision/generation, replay result. Runtime artifact remains in its owned store. |
| Post-run | Before/after revisions, candidate/imported/skipped/rejected counts, exact projection reconciliation, holder publication check, source unchanged, focused/regression results, acceptance. |
| Recovery | Classification, all observed artifacts/hashes, decision authority, recovery command/result, retained failed-state backup, post-recovery integrity and disposition. |

Commit only this generic procedure and template. Store instantiated manifests, private
locators, raw logs, screenshots, full hashes when sensitive, source content, runtime
artifacts, attempts/receipts, raw authorization, and bearer tokens in the approved
access-controlled operational evidence location—not Git. Use aliases in shareable
packets. Generated ledgers/snapshots/receipts remain owned runtime artifacts.

## 10. Recovery decision matrix

| Case | Authoritative facts | Retry | Rollback / restore | New authorization | Evidence and human decision |
| --- | --- | --- | --- | --- | --- |
| Pre-write/operator abort | No intent/attempt/effect; generations unchanged | After fresh preflight | Neither | Revalidate; new if expired/context changed | Preflight/output; operator + devdevbuilds no-go/go |
| Confirmed no-write failure | Integrity-valid ledger/snapshot/live all unchanged | Yes, after cause fixed | Neither | Revalidate at retry | Diagnostics and unchanged-state proof; recovery decision-maker |
| Confirmed partial failure | Intent/effect/generations and private/live state | Only through supported recovery | No blind rollback; restore only by explicit decision | Usually no for recovery of same intent; new for a new attempt/context | Preserve all stores/logs; recovery decision-maker |
| N/N+1 uncertain commit | Valid ledger N + matching intent, valid snapshot N+1 exact record | Recovery finalization, not a new import | No ordinary rollback/restore | Original exact authorization must still validate as implementation requires | Both envelopes and intent; recovery decision-maker |
| Success, response lost | Valid matching receipt/attempt/snapshot/live state | Exact replay only | No | No for exact replay | Stored receipt and reconciliation; reviewer accepts |
| Exact replay after success | Stable idempotency binding and immutable receipt | Replay permitted | No | No changed context allowed | Original/replayed receipt equality; operator/reviewer |
| Receipt mismatch | Receipt id/integrity/linkage conflict | No | No until classified; restoration exceptional | Not a cure | Quarantine artifacts; recovery decision-maker |
| Ledger-integrity failure | Raw sealed ledger and last known-good backup | No | Only approved restore after newer-state proof | Not a cure | Private copy/hash/diagnostic; recovery decision-maker |
| Authorization failure | Validator diagnostic, trusted time, revocation registry | No | No | Issuer may conduct a new separate ceremony; never mutate old authority | Safe auth evidence; issuer + devdevbuilds |
| Destination revision conflict | Expected/actual revisions and writer evidence | No immediate retry | No | New authorization if binding/revision changes | Both revisions; reviewer re-baselines |
| Backup restoration | Failed-state backup, target backup validity/generation, proof no newer accepted state lost | Not an import retry | Restore only with explicit authority | New authorization required for later new execution | All backups/hashes/restoration checks; recovery decision-maker + devdevbuilds |

## 11. Post-run acceptance gates

Phase 40L can declare success only when exact authoritative records equal the reviewed
projection/specifications; all expected counts reconcile; destination generation
advances exactly; the validated private store is the holder's published store; ledger
and snapshot integrity agree; receipt matches the actual attempt and record; exact
replay returns the same receipt; rejected/excluded material remains absent; source bytes
remain unchanged; no unexpected records exist; backup remains readable; focused and
full regression validation pass; every evidence packet is complete; and devdevbuilds
records human acceptance. Exit code zero is one datum, never sufficient acceptance.

## 12. Decision rationale and open blockers

| Decision | Why / risk controlled | Governance and remaining human choice |
| --- | --- | --- |
| One canonical runbook plus checklist/template | Prevents divergent procedures while keeping operator flow concise and facts machine-readable. | Agents propose structure; devdevbuilds reviews and merges/authorizes. |
| Fail-closed template checked in as `blocked` | Prevents placeholder facts from becoming apparent readiness and protects provenance/knowledge consistency. | Humans supply and independently verify real identity, backup, authorization, and evidence destinations. |
| No readiness validator/runtime code | Existing code has no read-only production orchestration seam; a partial validator could imply safety while creating API/contract scope. | A later approved phase chooses and reviews the execution/preflight interface. |
| No copy command with guessed paths | Prevents copying the wrong authoritative files, racing writers, or exposing private paths. | Deployment owner approves stop/copy/retention procedures. |
| Preserve ledger/attempt/receipt history through recovery | Maintains provenance and makes uncertainty diagnosable instead of hiding it. | Recovery decision-maker selects supported recovery/restoration. |
| Two-person checkpoint stated as governance | Improves coordination and catches command/identity drift without falsely claiming runtime enforcement. | devdevbuilds determines personnel and final go/no-go. |

This work supports a real developer tool: faster, consistent organization of reviewed
knowledge with provenance and unified coordination. Convenience never outranks exact
identity, human authority, or recoverability.

Remaining operational blockers are: real dataset identity and custody; approved
candidate decisions/counts; destination paths/revision/capacity; writer-stop proof;
non-overwriting backup medium/retention and completed isolated restoration rehearsal;
exact authorization and trusted-clock/revocation results; private evidence destination;
and a reviewed production execution plus genuinely read-only preflight interface.
