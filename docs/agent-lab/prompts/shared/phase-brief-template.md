# Template — Phase Brief

> General phase prompt skeleton. Compose with the
> [guardrails block](guardrails-template.md) and a role-specific prompt, and require the
> [validation report format](validation-report-template.md).

```
# Phase Brief — Hive|Mind — <phase title>

## Goal
<one-paragraph description of what this phase delivers and why>

## Agent + role
agent: <Claude Code | Codex | Cline | Roo Code | Aider | other>
role: <ui-builder | backend-builder | reviewer-finalizer | planning-agent |
       docs-agent | experiment-agent | source-research-agent | patch-agent>

## Branch
branch: <scoped branch, never main>

## Scope
active_task: <one scoped task>
allowed_files:
  - <path or glob>
forbidden_scope:
  - <e.g. no backend, no deps, no redesign, no main edits>

## Pre-flight (report before editing)
- current branch
- latest commit
- git status
- whether required previous phase work exists
- files you expect to touch
- if assumptions are wrong, stop and report

## Validation
validation_commands:
  - <command>
known_risks:
  - <risk>

## Reporting
- Use the validation report format.
- Capture evidence (screenshots / command output) as applicable.

## Handoff
- reviewer: <reviewer agent or none>
- decision: human gate (merge / reject / retry / escalate)
```
