# Agent Preflight and Postflight Checklist

Preflight occurs before writes. Read-only Git inspection is required even for a
read-only agent. Unexpected state means `STOP AND REPORT`; never automatically
clean, delete, stash, reset, rebase, overwrite, or repair.

## Common preflight

Every role verifies: repository-root and remote identity; fetch/prune; current
branch; baseline and input commit existence; merge-base and ahead/behind state;
tracked status and all untracked files; target branches and worktrees; overlapping
path ownership; paused-track locks; forbidden files; and the prohibition on
destructive Git. Existing command warnings are recorded separately from changes.
Ignored generated files are not tracked modifications, but relevant impact is
reported. Unexplained untracked files are never silently ignored.

Suggested evidence commands:

```powershell
git rev-parse --show-toplevel
git remote get-url origin
git fetch --prune origin
git branch --show-current
git cat-file -e <baseline>^{commit}
git cat-file -e <input>^{commit}
git merge-base HEAD origin/main
git rev-list --left-right --count origin/main...HEAD
git status --porcelain --untracked-files=all
git worktree list
git branch --all
```

## Role checklists

### Read-only scout

- Confirm `write_authority: none` and do not create or switch branches.
- Record facts, warnings, gaps, and evidence limitations without completion claims.
- Do not change documentation merely to record the review.

### Primary implementer

- Confirm exact branch, clean baseline, owned paths, deliverables, and non-goals.
- Confirm no active session owns the branch/worktree and no owned paths overlap.
- Create the branch only after all preflight gates pass.
- Before commit, inspect additions, deletions, and both sides of every rename.

### Independent auditor and hardener

- Start from the declared output commit in a separate audit session.
- Verify implementation evidence independently; do not repeat its claims as facts.
- Keep fixes in a separate hardening commit and preserve the implementation commit.
- If no defect exists, report that no hardening commit is required.

### Specialist contributor

- Confirm the narrow deliverable and bounded paths fit the assigned capability.
- Stop when work requires adjacent ownership or broader architectural authority.
- Report dependencies for the integration composer rather than composing them.

### Integration composer

- Require explicit human delegation, dependency order, integration order, and
  accepted manifests for every input commit.
- Preserve earlier commits and reject silent cherry-picks or history rewriting.
- Run independent validation after composition; do not claim human merge authority.

## Postflight verification

- Reverify root, remote, branch, merge-base, ahead/behind, and commit provenance.
- Inspect `git diff --name-status`, `--numstat`, and `--stat` from the baseline.
- Validate every added/deleted path and both paths of every rename against owned,
  read-only, forbidden, and paused-track rules.
- Run required validation and report exact commands with `PASS`, `FAIL`,
  `NOT RUN`, `BLOCKED`, or `NOT APPLICABLE`.
- Confirm no destructive operation, amendment, or history rewrite occurred.
- Report final staged, unstaged, untracked, and ignored-file-relevant state.
- Populate the composition manifest; never infer independent audit from self-test.

Phase 38B should enforce exact identities, normalized typed paths, commit ids,
branch/worktree ownership, diff scope, rename dual-validation, outcome vocabulary,
and manifest completeness in PowerShell. It must use deterministic matching, not
semantic/fuzzy matching, and must stop rather than repair.
