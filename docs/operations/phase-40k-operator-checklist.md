# Phase 40K Operator Checklist

Use with the [canonical runbook](phase-40k-authoritative-migration-runbook.md) and a
private instance of the [readiness template](phase-40k-readiness.template.json).
Every box requires recorded evidence; unchecked, ambiguous, or placeholder means no-go.

## T-minus preparation

- [ ] Exact repository/build commit equals the independently approved commit.
- [ ] Source locator resolves to exactly one approved dataset without exposing it in Git.
- [ ] Format, byte size, object count, SHA-256, trusted capture time, and source version are recomputed and match review.
- [ ] Parser/projector/assessor/contract versions and complete candidate report identity are recorded.
- [ ] Project, scope, expected candidate/import/reject/skip/exclusion counts reconcile.
- [ ] Destination ledger/snapshot aliases, revision, generation, access, and capacity are verified read-only.
- [ ] All writers are stopped/excluded by an approved deployment procedure.
- [ ] New non-overwriting backup contains ledger and snapshot; original/copy hashes match.
- [ ] Backup copies load together, pass integrity/generation checks, and complete isolated non-publishing restoration rehearsal.
- [ ] Private evidence destination is access-controlled, writable, and has sufficient capacity.

## Final authorization

- [ ] Issuer reviewed exact dataset, destination revision, specification, scope, counts, backup, and rehearsal evidence.
- [ ] Authorization id/integrity and issuance lineage validate without exposing raw authority.
- [ ] Trusted server UTC clock is available, timezone-aware, and plausible.
- [ ] Authorization is unexpired at go time and absent from the integrity-valid revocation registry.
- [ ] Exact project equality and authorized-scope membership pass.
- [ ] Operator/context governance check is recorded; runtime enforcement is claimed only where implemented.
- [ ] Operator and independent reviewer compare the exact execution command byte-for-byte.
- [ ] devdevbuilds records final private go/no-go decision; PR/merge status is not used as authority.

## Dry preflight

- [ ] Repository is clean and implementation identity remains approved.
- [ ] Dataset fingerprint is unchanged from authorization review.
- [ ] Read-only parse/projection/assessment succeeds with identical identities/counts.
- [ ] Destination revision/generation and expected write set remain unchanged.
- [ ] Backup remains present, readable, integrity-valid, and restorable.
- [ ] Authorization integrity, expiry, revocation, project, and scope are revalidated.
- [ ] Expected receipt identity and count reconciliation are recorded.
- [ ] Writer exclusion, capacity, logging/evidence destination, and recovery materials pass.
- [ ] No preflight step created an attempt/receipt, changed ledger/snapshot/source/authorization, or published a holder.
- [ ] Supported read-only orchestration exists; otherwise status remains `blocked`.

## Go/no-go

- [ ] Every readiness-template state required for execution is `verified`; no `not_supplied`, `unverified`, or `blocked` remains.
- [ ] Every runbook stop condition was evaluated and none is active.
- [ ] Operator can explain current dataset, destination, authorization, backup, command, expected writes, and recovery route.
- [ ] Independent reviewer and devdevbuilds record go; otherwise stop and preserve evidence.

## Execution observation (Phase 40L only)

- [ ] Separately authorized Phase 40L is active; exact approved command is used once.
- [ ] Trusted start/end times, output alias, lock state, attempts, generations, and warnings are observed.
- [ ] Any ambiguity, partial result, changed identity/revision/count, or evidence failure triggers immediate stop—no blind retry.
- [ ] No operator edits sealed state, fabricates a receipt, bypasses authorization, or deletes artifacts.

## Post-run validation

- [ ] Authoritative records exactly match reviewed specifications and counts reconcile.
- [ ] Destination generation advances exactly and the correct validated holder is published.
- [ ] Ledger/snapshot/receipt integrity and attempt/record linkage pass.
- [ ] Exact replay returns the identical stored receipt without another effect.
- [ ] Rejected/excluded records remain absent; no unexpected record exists; source digest is unchanged.
- [ ] Backup remains readable; focused migration and full backend regression suites pass.
- [ ] Complete evidence packet and human acceptance are recorded.

## Recovery path

- [ ] Outcome is classified from durable facts as pre-write, no-write, partial, N/N+1, success/lost-response, or corrupt/conflicting.
- [ ] Ledger, snapshot, attempts, receipts, logs, locks, and failed-state backup are preserved.
- [ ] Only implemented exact replay or recovery is used; N/N+1 integrity checks occur before generation reasoning.
- [ ] Restoration, if selected, has explicit authority and proof it cannot replace newer accepted state.
- [ ] Post-recovery integrity, records, generation, holder, and disposition are independently verified.

## Acceptance and closure

- [ ] Preflight, authorization, backup, execution, receipt, post-run, and recovery packets are complete as applicable.
- [ ] Sensitive evidence remains outside Git under approved access and retention controls.
- [ ] Final disposition is `accepted`, `recovered`, or `blocked` and is signed by operator, reviewer, and devdevbuilds as applicable.
- [ ] Follow-up work and remaining retention/monitoring obligations are assigned.
