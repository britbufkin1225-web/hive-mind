# Phase 40J — Migration Rehearsal + End-to-End Validation

## Verdict boundary

Phase 40J rehearsed the reviewed migration workflow only against a deterministic,
synthetic, disposable dataset. The authoritative dataset was not accessed or
mutated. Passing this phase makes an authoritative migration eligible for a
separate, explicit, human-authorized phase; it does not mean that migration ran.

## Repository baseline

- Repository: `britbufkin1225-web/hive-mind`
- Locked `origin/main` and starting HEAD: `5984108c5aa9309f9b9071817204ca0a7d5036ad`
- Merge base: `5984108c5aa9309f9b9071817204ca0a7d5036ad`
- Phase 40I lineage: merge commit `5984108`
- Working tree before Phase 40J: clean; zero behind and zero ahead

## Disposable construction and isolation

`test_memory_migration_rehearsal.py` deterministically builds a three-message
synthetic ChatGPT-shaped JSON export containing accepted, rejected, and unreviewed
representative content. The bytes, declared SHA-256 digest, intake bundle,
projection, assessment, human decisions, reviewed specification, authorization,
clock, and destination paths are repository-owned definitions. No private export,
credential, secret, private ChatGPT system memory, or runtime-generated dataset is
committed.

`MigrationRehearsalPaths.isolated()` requires an explicit test-owned root and
constructs exact ledger, snapshot, and lock paths without a production fallback.
It compares those paths and their root with all normal authoritative path
resolutions and fails closed on collision, including environment-variable
overrides. `reset()` can unlink only those three exact children and removes the
root only when empty. The authoritative dataset access count was **zero**.

## Scenario evidence

| Scenario | Expected and observed outcome | Automated evidence |
| --- | --- | --- |
| Parse and projection | One declared synthetic artifact read; three deterministic candidates projected | `test_disposable_complete_workflow_and_clean_deterministic_rerun` |
| Candidate assessment and review | Complete set assessed; one explicitly approved, one rejected, one deliberately unreviewed | same |
| Reviewed specification and authorization | Exact candidate/report/decision/project bindings accepted | same |
| Successful import and durable ordering | One record, intent, receipt, ledger generation, snapshot generation, and live generation at 1; snapshot visible only after verification | same plus existing Phase 40I ordering tests |
| Receipt verification | Receipt identity/integrity recomputed successfully; record linked in snapshot | same |
| Exact replay | Stored receipt returned unchanged; one attempt, receipt, record, and generation remain | same |
| Rejection/incomplete review | Rejected candidate fails closed; unreviewed candidate is never submitted or imported; payload text is absent from durable snapshot | same |
| Authorization failures | Missing authorization, trusted-clock expiry, wrong project, changed specification binding, durable revocation, and reuse for another candidate fail closed with no receipt/live record | `test_missing_authorization_fails_with_stable_diagnostic_and_no_side_effects`; `test_authorization_boundaries_fail_without_side_effects`; `test_revocation_and_authorization_reuse_fail_closed`; existing Phase 40I contract/service tests cover wrong-scope and altered immutable authorization construction |
| Integrity failures | Candidate/assessment/specification/authorization/revocation/attempt/receipt/ledger/snapshot integrity coverage is split between the focused rehearsal and existing Phase 40I tamper matrix; prior live generation is preserved | `test_tampered_ledger_snapshot_and_stale_revision_are_detected` plus Phase 40I import contract/store/service tests |
| CAS and stale revision | Stale expected ledger revision returns `revision_conflict`; no live overwrite | `test_tampered_ledger_snapshot_and_stale_revision_are_detected` plus Phase 40I concurrency tests |
| Crash before durable intent/effect/publication | Existing Phase 40I injected persistence/publication failures return no false success and preserve live state | Phase 40I import service/store tests |
| N/N+1 uncertain commit | Injected crash leaves ledger N=0 with durable intent and snapshot N+1=1; a fresh service derives recovery from disk, returns original deterministic receipt, and publishes generation 1 | `test_n_n1_uncertain_commit_recovery_uses_durable_state` |
| Clean rerun | Purpose-built reset removes only disposable artifacts; second full run produces identical receipt id, integrity digest, and record id | `test_disposable_complete_workflow_and_clean_deterministic_rerun` |
| Authoritative path override | Rehearsal root matching environment-overridden authoritative paths is rejected before directory creation | `test_rehearsal_path_guard_rejects_environment_override` |

## Validation results

- Focused Phase 40J rehearsal: **9 passed**.
- Phase 40I plus broader migration suite: **366 passed**.
- Complete backend suite: **1,280 passed**, with one upstream Starlette/httpx
  deprecation warning.
- Frontend validation: not required; no shared contract or frontend-visible file
  changed.
- Phase 40I defect found and corrected: a missing runtime authorization value was
  converted to generic `persistence_failure` before the authorization validator.
  The narrow guard now returns stable `missing_authorization` before any storage,
  lock, ledger, snapshot, receipt, or live-store side effect.

## Limitations and eligibility

The rehearsal uses the existing single-process lock, filesystem stores, and
deterministic injected failure seams. It does not claim operating-system crash
simulation, multi-host coordination, or an authoritative-data migration. The
authoritative migration is **eligible for a separately authorized next phase**,
subject to independent audit of this local commit. Phase 36K remains paused and
untouched.
