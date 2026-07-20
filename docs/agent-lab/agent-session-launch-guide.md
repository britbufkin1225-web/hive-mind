# Agent Session Launch Guide

This guide connects Phase 38A governance policy to Phase 38B executable preflight
validation. It is written for a fresh agent that has **no access to prior ChatGPT
conversation history**. Everything required to start a governed contribution is
here or in the linked canonical documents.

Working from this guide alone, an agent should be able to identify the canonical
repository, read its locked assignment, choose valid enum values, build a session
header and composition manifest, run the Phase 38B preflight, interpret the exit
codes, separate automated checks from manual obligations, stop safely when
preflight blocks, and complete a controlled handoff to the human merge gate.

This is documentation only. It changes no executable governance behavior. The
authoritative behavior lives in
[`scripts/governance/`](../../scripts/governance/README.md); Phase 38A remains the
policy source, and [`devdevbuilds`](agent-contribution-contract.md) remains the
sole merge gate.

## Canonical identity

| Field | Value |
| --- | --- |
| Canonical repository | `britbufkin1225-web/hive-mind` |
| Canonical remote | `https://github.com/britbufkin1225-web/hive-mind.git` |
| Canonical local path | `C:\Users\britb\Documents\hive-mind` |
| Repository folder name | exactly `hive-mind` (never inside OneDrive) |
| Merge gate | `devdevbuilds` |

Canonical repository identity is **derived**, not passed as a single parameter:
the preflight proves it by checking the repository path, the folder name, the
OneDrive exclusion, the Git top-level, and the `origin` remote together.

## 1. Launch sequence

Follow these steps in order. Do not skip a gate because a later step looks
routine.

1. **Receive the locked assignment.** Read the session header your operator
   supplied. It names the phase, branch, baseline, agent identity, role,
   capability, composition mode, write authority, permitted/forbidden paths, and
   stop conditions. Treat it as the narrowing contract for this one session.
2. **Verify the canonical path and remote.** Confirm the working directory is
   exactly `C:\Users\britb\Documents\hive-mind`, the folder is named `hive-mind`,
   the path contains no `OneDrive` segment, and `origin` is the canonical remote.
3. **Confirm `main` alignment and a clean start.** Confirm the current branch,
   that local `main` equals `origin/main`, and that the working tree is clean
   before you create a branch or edit anything.
4. **Fetch only when explicitly authorized.** The preflight never fetches. Run
   `git fetch` only when your assignment authorizes it, and re-verify afterward.
5. **Record the full baseline SHA.** Capture the complete 40-character
   `origin/main` commit id as the locked baseline for the session.
6. **Create or verify the expected branch.** Create the locked feature branch
   from verified `main` (or confirm you are already on it). A contribution branch
   is never `main`. Confirm `git merge-base HEAD origin/main` equals the locked
   baseline and that the branch is `0` behind.
7. **Prepare the session header.** Fill in
   [`templates/agent-session-header.template.json`](templates/agent-session-header.template.json)
   with canonical enum values only.
8. **Prepare the composition manifest.** Fill in
   [`templates/agent-composition.template.json`](templates/agent-composition.template.json).
   Keep empty lists as explicit `[]` evidence; never convert an unknown fact into
   a favorable Boolean.
9. **Run the Phase 38B preflight.** See [section 4](#4-run-the-preflight).
10. **Interpret PASS, WARNING, and BLOCKED.** See
    [section 5](#5-interpret-the-result).
11. **Perform only authorized work.** Edit only permitted paths; leave forbidden
    paths untouched.
12. **Validate changed paths.** Parse any JSON you added, resolve internal links,
    and run `git diff --check origin/main...HEAD`.
13. **Commit only when allowed.** Create the number of commits your assignment
    authorizes and nothing more. Do not amend, rebase, squash, or reset.
14. **Hand off for independent review.** An implementer's self-review is not an
    independent audit. Recommend the independent auditor explicitly.
15. **Push and open a PR only when explicitly authorized.** These transitions are
    authorized by `devdevbuilds`, never assumed from provider tooling.
16. **Preserve the `devdevbuilds` merge gate.** No agent merges.
17. **Normalize `main` only after a confirmed merge.** Fast-forward local `main`
    to `origin/main`; delete no branches unless separately authorized.
18. **Confirm final status with evidence.** Confirm W100, working-tree-clean
    (WTC), and merged status from direct Git and PR evidence, not from summaries.

## 2. Parameter mapping

The session header and manifest are human-facing. The Phase 38B preflight
(`Invoke-HiveMindGovernancePreflight.ps1`) consumes discrete parameters. Map them
as follows:

| Session concept | Phase 38B parameter |
| --- | --- |
| canonical local path | `-RepositoryPath` |
| canonical remote | `-ExpectedRemote` |
| expected branch | `-ExpectedBranch` |
| baseline commit | `-ExpectedBaseline` |
| phase identifier | `-CurrentPhase` |
| agent identity | `-AgentName` |
| assigned role | `-AgentRole` |
| capability level | `-CapabilityLevel` |
| composition mode | `-CompositionMode` |
| write authority | `-WriteAuthority` |
| Phase 36K status | `-Phase36KStatus` |
| composition manifest | `-ManifestPath` |
| require clean state | `-RequireCleanWorkingTree` |
| canonical path override value | `-CanonicalRepositoryPath` |
| fixture-only canonical bypass | `-DisableCanonicalPathEnforcement` |
| machine-readable output | `-Json` |

Canonical **repository identity** has no single standalone parameter. It is
derived from `-RepositoryPath` plus the `origin` remote compared against
`-ExpectedRemote`, together with the folder-name and OneDrive checks.
`-CanonicalRepositoryPath` defaults to the canonical path and is visible and
overrideable; `-DisableCanonicalPathEnforcement` exists only for disposable
self-test fixtures, never for a normal Hive|Mind session.

## 3. Enum quick reference

Use only these values, exactly as written, from
[`HiveMindGovernance.psm1`](../../scripts/governance/HiveMindGovernance.psm1). Do
not document or use aliases.

**Roles (`assigned_role` / `-AgentRole`)**

- `primary-implementer`
- `independent-auditor-hardener`
- `specialist-contributor`
- `read-only-scout`
- `integration-composer`
- `human-project-owner`

**Capability levels (`capability_level` / `-CapabilityLevel`)**

- `L0`
- `L1`
- `L2`
- `L3`
- `L4`

**Composition modes (`composition_mode` / `-CompositionMode`)**

- `sequential-isolated`
- `sequential-audit`
- `parallel-read-only`
- `parallel-isolated`
- `integration-composition`
- `adversarial-verification`

**Write authorities (`write_authority` / `-WriteAuthority`)**

- `none`
- `documentation-only`
- `tests-only`
- `bounded-path-write`
- `full-locked-phase-scope`

The pinned contract identifiers used by the composition manifest are
`manifest_version: agent-composition.v1` and
`contract_version: agent-contribution.v1`. A manifest that uses any other value
for these fields is blocked as a competing schema.

## 4. Run the preflight

Human-readable form:

```powershell
$baseline = git rev-parse origin/main

& .\scripts\governance\Invoke-HiveMindGovernancePreflight.ps1 `
  -RepositoryPath 'C:\Users\britb\Documents\hive-mind' `
  -ExpectedRemote 'https://github.com/britbufkin1225-web/hive-mind.git' `
  -ExpectedBranch 'phase-38c-governance-adoption-agent-session-pack' `
  -ExpectedBaseline $baseline `
  -CurrentPhase 'Phase 38C — Governance Adoption + Agent Session Pack Integration' `
  -AgentName 'claude' `
  -AgentRole 'primary-implementer' `
  -CapabilityLevel 'L3' `
  -CompositionMode 'sequential-isolated' `
  -WriteAuthority 'documentation-only' `
  -Phase36KStatus 'paused-and-untouched'
```

Add `-ManifestPath .\path\to\manifest.json` to also validate a completed JSON
serialization of the composition manifest. The manifest must live inside the
repository. Add `-RequireCleanWorkingTree` to turn a dirty tree from a warning
into a blocking failure (appropriate at session start, not mid-implementation).

Machine-readable form — one pure JSON value on stdout:

```powershell
$result = & .\scripts\governance\Invoke-HiveMindGovernancePreflight.ps1 <arguments> -Json
$result | ConvertFrom-Json | Out-Null
```

**Exit codes**

| Exit code | Meaning |
| --- | --- |
| `0` | Required checks passed (warnings may still be present). |
| `2` | One or more governance checks blocked. |
| `3` | Invalid invocation or malformed input. |

## 5. Interpret the result

- **PASS** (`[PASS]`, exit `0`): the declared state matches evidence for that
  check. Proceed with authorized work.
- **WARNING** (`[WARNING]`): a non-blocking condition. The three expected
  warnings for a governed session are: zero commits ahead before implementation
  starts, a dirty working tree when a clean tree was not required, and
  caller-managed fetch freshness (the validator never fetches). Read each warning
  — do not ignore it — but it does not stop the session.
- **BLOCKED** (`[BLOCKED]`, exit `2`): a governance check failed. Stop and follow
  the fail-closed recovery guidance in [section 8](#8-fail-closed-recovery). Do
  not attempt automatic repairs.
- **Invocation error** (exit `3`): the inputs or manifest location were invalid.
  Correct the invocation and rerun.

## 6. Automated checks versus manual obligations

The preflight is deterministic but narrow. It validates declared state; it does
not make human judgments.

**Phase 38B automated checks include:**

- repository path resolves and exists;
- OneDrive paths are rejected;
- folder is named exactly `hive-mind`;
- path matches the canonical path (unless explicitly disabled for fixtures);
- repository is a Git working tree and its top-level equals the supplied path;
- `origin` remote matches the expected remote;
- HEAD is attached (not detached);
- current branch equals the expected branch, which is never `main`;
- baseline is a valid 40-character commit id that exists;
- baseline is an ancestor of HEAD and the merge-base equals the baseline;
- branch is not behind the baseline (divergence check);
- working tree is clean when a clean tree is required;
- session enum values (role, capability, composition, write authority) are
  canonical;
- Phase 36K status is `paused-and-untouched`;
- optional manifest structure, pinned versions, required fields, and the fields
  that must match the session values;
- structured/JSON output and deterministic exit codes.

The baseline and merge-base checks prove the **expected baseline is an ancestor**
and that the **merge-base equals it**. They do **not** prove there are no
intermediate commits between the baseline and HEAD.

**Phase 38A manual obligations that the preflight cannot decide:**

- verify that work stayed inside allowed paths;
- verify that forbidden paths remain untouched;
- inspect semantic correctness of the change;
- inspect security consequences;
- confirm that tests are appropriate;
- distinguish an independent audit from a self-review;
- validate the handoff evidence;
- inspect push and PR authorization;
- confirm human merge authorization;
- verify the final W100 / WTC / merged evidence.

## 7. Push, PR, and merge policy

Every session must state, explicitly, whether commits, push, PR creation, and
merge are allowed, and who authorizes each transition. The default posture is
fail-closed: an agent does only what its locked assignment grants.

- Commits: allowed only up to the count the assignment grants.
- Push: authorized by `devdevbuilds`.
- PR creation: authorized by `devdevbuilds`.
- Merge: performed or authorized only by `devdevbuilds`, who also verifies final
  repository state.

Provider tooling that auto-creates a branch or PR is **not** authorization. See
[Agent Unavailability and Fallback](agent-unavailability-and-fallback.md) for the
required response to provider-created branches and empty PRs, and for handling
temporarily unavailable agents without inventing invalid enum values.

## 8. Fail-closed recovery

When a check blocks, stop. Report. Do not self-repair.

| Block | Required response |
| --- | --- |
| Wrong repository | Stop and open the canonical repository. |
| OneDrive path | Stop; do not move the active worktree automatically. |
| Wrong remote | Stop and report to `devdevbuilds`. |
| Detached HEAD | Stop and obtain explicit branch instructions. |
| Wrong branch | Stop and follow the locked session branch instruction. |
| Dirty tree | Stop and inventory all changes; do not stash, clean, or reset. |
| Missing baseline | Perform only an explicitly authorized fetch, then reverify. |
| Divergence | Stop; do not automatically rebase or merge. |
| Malformed manifest | Correct the JSON and rerun preflight. |
| Enum mismatch | Use the exact canonical enum from the locked assignment. |
| Conflicting ownership | Stop and escalate to `devdevbuilds`. |
| Unknown provider branch | Stop and verify why the branch exists. |

Never recommend or perform an automatic stash, clean, reset, rebase, force-push,
remote mutation, branch recreation, or a hidden repair flag.

## 9. Session examples

Each example states role, capability, composition mode, write authority, and the
commit/push/PR/merge posture. For the currently active pool and the full
reasoning about unavailable agents, see
[Agent Unavailability and Fallback](agent-unavailability-and-fallback.md).

### Claude Code (primary implementer)

- `assigned_role: primary-implementer`, `capability_level: L3`,
  `composition_mode: sequential-isolated`.
- Write authority is phase-specific. **For Phase 38C, Claude uses
  `write_authority: documentation-only`.**
- May create the expected branch, edit permitted documentation paths, and create
  one local implementation commit.
- May **not** push, open a PR, merge, amend, rebase, squash, reset, delete
  branches, or modify `main`.

### Jules (specialist contributor / independent reviewer)

- `assigned_role: specialist-contributor`, `capability_level: L1`,
  `composition_mode: parallel-read-only`, `write_authority: none`.
- Read-only: no intended repository writes, commits, push, PR, or merge.

### Antigravity (read-only scout)

- `assigned_role: read-only-scout`, `capability_level: L0`,
  `composition_mode: parallel-read-only`, `write_authority: none`.
- Read-only reconnaissance: no writes, commits, push, PR, or merge.

### ChatGPT (integration composer)

- `assigned_role: integration-composer`, `capability_level: L3`,
  `composition_mode: integration-composition`, `write_authority: none`.
- Composes prompts, manifests, handoffs, and integration guidance. ChatGPT does
  **not** execute commands on the user's local Windows machine; an authorized
  local actor runs the PowerShell commands.
- No local repository write or execution authority.

### devdevbuilds (human project owner / merge gate)

- `assigned_role: human-project-owner`, `capability_level: L4`,
  `composition_mode: adversarial-verification`,
  `write_authority: full-locked-phase-scope`.
- Authority is constrained by the locked phase: `full-locked-phase-scope` is not
  unlimited authority outside the phase. Repository protections and evidence
  requirements still apply.
- Sole merge gate: authorizes push and PR, performs or authorizes merge, and
  verifies final repository state.

## 10. Reference documents

- [Agent Lab README](README.md) — routing and boundaries.
- [Agent Contribution Contract](agent-contribution-contract.md) — governing rules.
- [Role and Capability Matrix](agent-role-capability-matrix.md) — eligibility.
- [Session Header Lockup](agent-session-header-lockup.md) — the YAML lockup form.
- [Preflight Checklist](agent-preflight-checklist.md) — execution gates.
- [Composition Manifest](agent-composition-manifest.md) — evidence and handoff.
- [Agent Unavailability and Fallback](agent-unavailability-and-fallback.md) —
  temporary exclusions and provider-PR handling.
- [PowerShell Governance README](../../scripts/governance/README.md) — the
  executable preflight.
