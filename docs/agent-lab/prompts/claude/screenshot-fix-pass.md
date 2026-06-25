# Prompt — Claude Screenshot Fix Pass

> **Role:** `ui-builder` (screenshot-driven) · **Agent:** Claude Code · **Reviewer:** Codex → human gate
> Use screenshots as evidence. Make minimal, targeted UI fixes. Preserve scope.

Use Claude Code for **screenshot-driven UI fixes**. The screenshot is the evidence of what is
wrong; the fix should be the smallest change that resolves what the screenshot shows.

## Brief

```
You are fixing UI issues shown in screenshots for Hive|Mind, Phase <phase title>.

Branch: <scoped branch, never main>
Screenshots / evidence: <attach or describe each screenshot and the visible problem>

Allowed files:
  - <path or glob>

Forbidden scope:
  - Fix only what the screenshots show.
  - No new features, no redesign.
  - No backend or dependency changes.
  - No direct main edits.

Before editing, report branch, latest commit, git status, and files you expect to touch.

For each screenshot:
  - Identify the exact element and the visible defect.
  - Make the minimal targeted fix.
  - Re-render and confirm with a new screenshot.

Validate:
  - <frontend build command>

Report each fix with before/after screenshots as UI-state evidence. Hand off to Codex; the
human decides on merge.
```

## Notes

- Anchor every change to a specific screenshot. If you cannot tie a change to the evidence, do
  not make it.
- Preserve the existing dark-workbench visual language.
