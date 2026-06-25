# Prompt — Claude QA / Demo Polish Pass

> **Role:** `ui-builder` (QA scope) · **Agent:** Claude Code · **Reviewer:** Codex → human gate
> For small, scoped QA and demo polish only. Not for new features.

Use Claude Code for **small QA and demo polish**: verify UI behavior and fix only scoped
frontend issues. Report validation honestly.

## Brief

```
You are doing a scoped QA / demo polish pass for Hive|Mind, Phase <phase title>.

Branch: <scoped branch, never main>
Active task: Fix the listed QA issues only.

QA issues to fix:
  - <issue 1>
  - <issue 2>

Allowed files:
  - <path or glob>

Forbidden scope:
  - No new features.
  - No redesign.
  - No backend or dependency changes.
  - No direct main edits.

Before editing, report branch, latest commit, git status, and files you expect to touch.

For each issue:
  - Reproduce / verify the current behavior.
  - Make the minimal fix.
  - Confirm the fix.

Validate:
  - <frontend build command>

Report which issues were fixed, which were not, and why. Capture before/after screenshots
where the change is visual. Hand off to Codex; the human decides on merge.
```

## Notes

- "Polish" means small and targeted. If an issue needs a larger change, report it and stop —
  do not expand the pass into a redesign.
