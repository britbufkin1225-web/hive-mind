# Phase 40K.5 — Production Migration Readiness Interface

**Interface version:** `migration-readiness-preflight.v1` / `migration-execution-gate.v1`

**Manifest contract:** `memory-migration-readiness.v1` (validates the checked-in
[`phase-40k-readiness.v1` template](phase-40k-readiness.template.json))

**Status:** repository tooling implemented; **operational readiness blocked**.

Phase 40K identified that the repository supplied *no genuinely read-only
production preflight entry point* and *no reviewed production execution entry
point* (see the [runbook](phase-40k-authoritative-migration-runbook.md) §7, §12).
Phase 40K.5 supplies both as a narrow, repository-only bridge. It accesses no real
dataset, creates no authorization, and executes no migration. Passing repository
validation does **not** authorize Phase 40L.

## 1. What the read-only preflight checks

`app.services.migration_readiness_preflight.MigrationReadinessPreflight.evaluate`
is a pure, deterministic function of `(manifest, injected trusted clock)`. It
holds **no** store, holder, ledger, snapshot, lock, attempt, receipt, or
authorization-registry reference and reads no filesystem/network resource, so it
is read-only by construction, not merely by description. It evaluates:

- repository/implementation identity (declared execution commit + state);
- dataset fingerprint presence, digest-algorithm strength (SHA-256/512 only), and
  a declared-vs-reviewed fingerprint **conflict** check;
- pipeline (parser/projection/assessment/specification) identity state;
- destination revision presence, verification, and an expected-vs-observed
  revision **mismatch** check; destination capacity; concurrent-writer exclusion;
- backup identity and integrity/readability verification; isolated
  restoration-rehearsal readiness;
- authorization presence, integrity/lineage, project and scope binding,
  **expiry** (evaluated against the trusted clock), and **revocation** state;
- trusted-time availability (a naive/absent clock fails closed);
- expected input/output counts and their arithmetic **consistency**;
- expected receipt identity / write-set state; evidence-destination and
  recovery-materials state;
- **stale** declared trusted-evidence timestamps;
- **placeholder/fixture** and **secret-like** values used in an operational field;
- explicit runbook **stop conditions**;
- the production read-only **orchestration** state (whether real-source/destination
  orchestration is wired — it is not, so this stays `blocked`).

Field-state vocabulary: `not_supplied`, `unverified`, `verified`, `blocked`,
`conflicting`. Absence (`not_supplied` / `unverified` / `blocked`) is an honest
not-ready signal and yields **`blocked`**. A deceptive or dangerous input — a
placeholder/fixture/secret-like value, a malformed timestamp, a weak digest
algorithm, or a manifest that violates the contract — is **rejected** and yields
**`fail_closed`**. Unknown states are never treated as safe.

JSON duplicate keys are rejected at the CLI boundary. Dataset and backup digests
must be canonical lowercase hexadecimal of the exact length required by the
declared `sha256` or `sha512` algorithm; aliases, case variants, whitespace, and
malformed digest values fail closed. Whitespace-only operational identifiers are
treated as placeholders and rejected.

## 2. How it is invoked

Read-only CLI (a thin front end; all logic lives in the service):

```bash
python -m app.console.migration_readiness_cli preflight --manifest <path-to-manifest.json> --json
```

Instantiate the manifest from the fail-closed
[`phase-40k-readiness.template.json`](phase-40k-readiness.template.json) **outside
Git**, keeping secrets and private paths out of it. Options: `--json` for the
machine-readable report; `--now <ISO-8601>` for a deterministic trusted evaluation
time (an explicit timezone offset is mandatory); `--max-age-seconds` for the
stale-evidence bound. Exit codes: `0` pass, `10`
blocked, `11` fail_closed, `2` manifest access/size error, `3` usage error.

## 3. Machine-readable output contract

`--json` emits a bounded, non-secret `PreflightReport`:

- `outcome`: `pass` | `blocked` | `fail_closed`;
- `manifest_identity`: deterministic content-derived id (`mm-readiness-…`);
- `tool_version`, `evaluated_at`;
- `checks[]`: `{check_id, state, blocked_reason?, detail}`;
- `blocked_reasons[]`: deduplicated typed reason codes;
- `active_stop_conditions[]`;
- `evidence`: manifest identity, schema/runbook/tool versions, repository
  baseline/execution commit, destination revision, **redacted-if-secret**
  authorization and backup identifiers, supplied expected counts, a per-section
  supplied/verified summary, and the active stop conditions.

The evidence never contains credentials, tokens, keys, raw records, unbounded
exception text, or unrestricted paths; secret-like identifiers are redacted to
`[redacted]` and independently rejected.

## 4. Separation between preflight and execution

The read-only preflight and the execution decision are **separate boundaries**:

- `MigrationReadinessPreflight` answers *"is this declared manifest well-formed and
  ready?"* and never authorizes anything.
- `app.services.migration_execution_gate.ReviewedMigrationExecutionGate` is the
  execution-facing decision boundary. It **defaults to refusal** and clears
  execution only when **all** of the following hold: an explicit
  `OperationalExecutionAuthorization` is supplied (never inferred from a passing
  preflight); it is not a fixture/demonstration and is marked operational; it
  carries no placeholder/secret text; it carries an explicit devdevbuilds go; it
  names the **exact** manifest identity; and the preflight outcome is `pass`.
  Any failure yields a typed refusal with no side effect.

The gate does not itself migrate. In a separately authorized Phase 40L, a cleared
decision is dispatched to the existing Phase 40I coordinator
(`MemoryMigrationImportService.import_reviewed_candidate`) through an injected
executor. **No executor is wired in Phase 40K.5**, so even a cleared decision
performs no work here. The gate never silently downgrades execution to a dry run.
If a separately wired executor raises, the gate returns a bounded
`execution_failed` decision marked as dispatched, with generic reconciliation
guidance and no raw exception text; it never reports the attempt as successful.

## 5. Operational values that remain blocked / `not_supplied`

Every real operational field stays `not_supplied` / `unverified` / `blocked`: real
dataset identity/fingerprint and custody; destination identity/revision/capacity;
writer-exclusion proof; backup identity/integrity/readability and isolated
restoration rehearsal; runtime authorization identity/integrity/expiry/revocation
and its trusted-clock results; expected counts and receipt identity; private
evidence destination; and the production read-only orchestration over real data.
The checked-in template therefore still evaluates to **`blocked`**. Test fixtures
that set states to `verified` describe the fixture only and are **never**
production verification.

## 6. Why passing repository validation does not authorize Phase 40L

A `pass` means a **declared** manifest is internally consistent and structurally
ready and that the repository tooling works. It does not read the real source or
destination, does not create or validate a live runtime authorization, and does
not perform the independent human verification the runbook requires. Repository
approval and PR merge confer no runtime authority; a passing preflight confers
none either. Execution additionally requires the exact operational authorization
above **and** a separate explicit devdevbuilds go.

## 7. Future sequence (not implemented here)

- **Phase 40K.6 — Real Dataset Identity + Backup/Restoration Readiness
  Verification.** Supplies and independently verifies the real dataset identity/
  fingerprint, backup, and isolated restoration readiness that 40K.5 leaves
  `not_supplied`.
- **Phase 40K.7 — Final Operational Go/No-Go Review.** The human readiness-packet
  review that precedes any execution.
- **Phase 40L — Authorized Production Migration Execution + Acceptance Evidence.**
  Wires the cleared execution gate to the Phase 40I coordinator under authority.

These are described for sequence only; none is implemented. **Phase 40L requires a
new, explicit devdevbuilds go**; nothing in Phase 40K.5 begins, implies, or
authorizes it.
