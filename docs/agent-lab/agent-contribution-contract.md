# Agent Contribution Contract

Contract version: `agent-contribution.v1`

## Purpose and applicability

This contract applies to every agent contribution to Hive|Mind. It makes scope,
authority, provenance, validation, and composition explicit. It exists to
prevent repository mistakes, overlapping writes, unverifiable claims, and
provider-name-based authority. A later Phase 38B may automate deterministic
checks; this document remains the policy source.

## Authority and evidence

Authority descends in this order: human project owner; canonical repository
policy; locked session header; assigned role and capability; verified repository
state; agent recommendations. When two canonical policies conflict, stop for a
human resolution. This ordering prevents a prompt, memory, or agent assertion
from silently overriding project control.

Repository evidence outranks chat memory. An agent must verify root, remote,
baseline, branch, worktrees, status, and relevant documents before writing. This
prevents work in the wrong checkout or from stale assumptions.

Provider identity grants no permission. Active authority is the intersection of
the session's assigned role, capability level, write authority, paths, objective,
and locks. This prevents reputation from becoming an implicit access control.

## Roles, capabilities, and write authority

Roles are `primary-implementer`, `independent-auditor-hardener`,
`specialist-contributor`, `read-only-scout`, `integration-composer`, and
`human-project-owner`. Capability levels are L0 through L4 and are defined in
the [matrix](agent-role-capability-matrix.md). Roles say what work is assigned;
levels say what risk has been demonstrated. Keeping them separate prevents
historical role labels from becoming permanent authority.

Write authority is exactly one of `none`, `documentation-only`, `tests-only`,
`bounded-path-write`, or `full-locked-phase-scope`. An enumerated value prevents
an ambiguous Boolean from hiding the kind of permitted change.

## Scope and path ownership

Every writable session declares owned, read-only, and forbidden paths. Forbidden
paths override owned paths; read-only paths cannot be changed. Additions and
deletions must be owned. A rename is both removal of the old path and addition
of the new path, so both paths must be owned. This prevents scope expansion by
file operation semantics.

Path entries use repository-relative paths, forward slashes, no absolute path,
and no `..` traversal. Windows comparison is case-insensitive while reports
preserve canonical spelling. Each entry explicitly declares one match type:

```yaml
- type: exact
  value: README.md
- type: prefix
  value: docs/agent-lab/
- type: glob
  value: docs/**/*.md
```

Exact, prefix, and glob meanings must never be inferred or fuzzily matched. This
gives Phase 38B deterministic enforcement and prevents accidental broad grants.

## Concurrency and branch ownership

Default: one write-capable agent owns one branch and one worktree. Two agents
must not write in the same worktree or branch, share uncommitted state, or make
competing roadmap completion claims. This prevents collisions and ambiguous
provenance.

Parallel writes require separate branches and worktrees, non-overlapping owned
paths, locked baselines, declared dependency and integration order, an assigned
integration composer, and independent post-composition validation. Parallel
read-only review is permitted when no session claims write authority.

The session header names branch ownership. An already-owned branch or worktree
causes `STOP AND REPORT`; agents do not take it over or repair it.

## Composition and commit preservation

Composition follows declared dependency order, then declared integration order.
Earlier contributions remain distinct commits. Silent cherry-picking, amendment,
rebasing shared commits, squashing existing contributions, and “newest commit
wins” conflict handling are prohibited. These rules preserve authorship,
reviewability, and contradiction evidence.

Implementation and audit/hardening are separate contributions and commits.
Hardening needs a separate commit only when verified defects are corrected. An
integration composer may act only under explicit session delegation; final merge
authorization remains human-only.

## Validation and evidence

Allowed validation outcomes are `PASS`, `FAIL`, `NOT RUN`, `BLOCKED`, and
`NOT APPLICABLE`. Exact commands and results are mandatory. Output hashes and
persistent logs are optional unless a later high-risk session requires them.
`NOT RUN` must never become `PASS`.

Evidence categories are distinct:

- Git-state evidence: root, remote, commits, branches, worktrees, and status.
- Diff-scope evidence: names, statuses, renames, deletions, and statistics.
- Unit-test evidence and full-suite evidence.
- Build and type-check evidence.
- API runtime evidence and browser interaction evidence.
- Responsive-layout evidence.
- Hardware evidence and camera evidence.
- Screenshot evidence and human visual approval.

A build is not runtime validation; an API smoke test is not browser validation;
static CSS inspection is not responsive browser validation; a camera-free test
is not live camera evidence; and a screenshot is not interaction proof. An
implementation agent's report is not independent audit. These distinctions
prevent false validation claims.

## Documentation and completion authority

Canonical repository documentation outranks agent memory, but documentation must
itself cite verified state and must not claim work beyond available evidence.
Agent Lab governs contribution workflow; [Active Memory](../active-agent-memory-verification-layer.md)
governs project data, memory, contradictions, and verification architecture.

Completion terms:

- **Planned:** documented scope; no active implementation branch.
- **Active:** locked session and work started on its required branch.
- **Implemented locally:** primary contribution committed locally and tree clean;
  audit and integration remain pending.
- **Audited:** separate agent or human completed required independent review.
- **Hardened:** verified audit defects corrected in a separate commit; not required
  when no defects are found.
- **Pushed:** contribution branch exists on expected remote.
- **PR opened:** pull request exists against intended base.
- **Merge-ready:** implementation, audit, validation, and docs are satisfied;
  human merge authorization remains pending.
- **Merged:** approved contribution integrated into `main`.
- **W100:** complete locked phase workflow finished and validated.
- **WTC (Working Tree Clean):** no staged, unstaged, or unexplained untracked
  files, and local `main` aligned with `origin/main`.
- **Blocked:** required condition prevents safe continuation.
- **Paused:** intentionally suspended and human authorization is required to resume.
- **Superseded:** a newer approved plan or implementation replaces earlier work.

Only the human project owner may authorize final merge, contract exemptions,
capability promotion/demotion, destructive Git, paused-track resumption, scope
expansion, new phases, final W100, final WTC, or resolution of conflicting
canonical policy. This prevents premature phase closure.

## Stop and escalation conditions

Use these exact deterministic conditions:

```text
STOP: Repository root does not match the locked session header.
STOP: Git remote does not match the locked repository.
STOP: The expected baseline commit cannot be verified.
STOP: The required merge-base does not match.
STOP: The working tree contains unexplained changes.
STOP: The target branch contains unexplained commits.
STOP: The branch or worktree is already owned by another active session.
STOP: A changed path falls outside owned paths.
STOP: A forbidden or read-only path would be modified.
STOP: An earlier agent commit would need to be amended or rewritten.
STOP: A destructive Git operation would be required.
STOP: A paused-track file would be modified.
STOP: Required validation cannot be honestly performed.
STOP: Two canonical instructions conflict and no human resolution exists.
```

On a stop, preserve state and report evidence. Never automatically clean, stash,
reset, rebase, overwrite, delete, or repair. This avoids turning an anomaly into
data loss.

## Current Hive|Mind standing locks

Hive|Mind remains standalone under parent label devdevbuilds. Backend and
frontend work remain separated unless integration is explicit. Phase 36K is
paused. Phase 38A is documentation-only; Phase 38B enforcement is planned, not
active. Human-controlled composition and merge remain mandatory.

These decisions treat Hive|Mind as a real coordination, knowledge-consistency,
provenance, and workflow-acceleration system. Phase 38B may automate path,
header, Git-state, and manifest checks without weakening these controls.
