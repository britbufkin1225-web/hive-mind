# Template — Validation Report

> Standard format every agent uses to report results at the end of a run. Mirror these fields
> so reports can later be parsed into session records.

```
# Validation Report — <phase title> — <agent>

## Identity
branch: <branch>
latest_commit: <hash>
agent: <agent>
role: <role>

## What changed
files_touched:
  - <path>
summary: <one paragraph of what was done>

## Validation
commands_run:
  - <command> -> <pass | fail | partial>
validation_result: pass | fail | partial
evidence: <screenshots / command output / links>

## Scope check
stayed_in_allowed_files: yes | no
forbidden_scope_touched: none | <what and why>

## Outcome
self_assessment: <honest note on quality and any risks>
recommendation: <ready for review | needs retry | blocked>
handoff: <reviewer agent / human gate>

## Notes
<lessons, bugs, follow-ups>
```

## Rule

Report honestly. If validation failed or was skipped, say so plainly with the output. Do not
claim a pass without evidence.
