# Template — Context Pack (Agent Briefing)

> Copy-paste-ready briefing handed to an agent at the start of a run. This is the manual
> version of the future generator described in
> [`context-pack-strategy.md`](../../context-pack-strategy.md). Works for Claude, Codex, Cline,
> Roo Code, Aider, OpenHands, or another agent.

```
# Context Pack — Hive|Mind — <phase title>

## Identity
project: Hive|Mind
phase: <phase title>
branch: <scoped branch, never main>
agent_role: <ui-builder | backend-builder | reviewer-finalizer | planning-agent |
             docs-agent | experiment-agent | source-research-agent | patch-agent>

## State
completed_phases:
  - <phase>
active_task: <one scoped task>

## Scope
allowed_files:
  - <path or glob>
forbidden_scope:
  - no direct main edits
  - no new dependencies
  - no backend changes unless this phase allows it
  - no UI redesign beyond the active task

## Validation
validation_commands:
  - <command>
known_risks:
  - <risk>

## Reporting
required_report_format: validation-report-template.md
handoff: <reviewer agent / human gate / archive>

## Pre-flight (report before editing)
- current branch
- latest commit
- git status
- whether required previous phase work exists
- files you expect to touch
- if assumptions are wrong, stop and report
```

## Rule

A context pack is scoped and branch-safe. It always names a non-`main` branch, a validation
command, a report format, and a handoff.
