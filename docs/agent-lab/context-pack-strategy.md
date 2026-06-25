# Context Pack Strategy

A **context pack** is a copy-paste-ready briefing handed to an agent (Claude, Codex, Cline,
Roo Code, Aider, OpenHands, or another) at the start of a run. It gives the agent exactly the
scope, guardrails, and validation it needs — and nothing more.

This document defines the future context-pack generator (Agent Ops Roadmap
[Phase D](agent-ops-roadmap.md)). The generator is **not implemented in this phase**; the
shape and skeleton below are the spec.

## What a context pack includes

- **project name** — e.g. Hive|Mind.
- **current phase** — e.g. Phase 9C — Knowledge Graph Visualization QA + Demo Polish.
- **current branch** — the scoped working branch (never `main`).
- **completed phases** — what already shipped, so the agent does not redo it.
- **active task** — the one scoped task for this run.
- **allowed files** — explicit list or globs the agent may edit.
- **forbidden scope** — what must not change (backend, deps, redesign, etc.).
- **validation commands** — exact build/test commands to run and report.
- **known risks** — traps, brittle areas, prior failures.
- **required report format** — how the agent must report results
  (see [`prompts/shared/validation-report-template.md`](prompts/shared/validation-report-template.md)).
- **agent role** — which role from [`registry/agent-roles.yml`](registry/agent-roles.yml).
- **handoff instructions** — what happens next (reviewer, human gate, archive).

## Future output

A single copy-paste block the human pastes into the agent's first message. The generator
assembles it from:

- Live project status (branch, last commit, git status).
- The current phase definition.
- The standard guardrail block
  ([`prompts/shared/guardrails-template.md`](prompts/shared/guardrails-template.md)).
- The relevant role from the registry.
- Source registry context where source research is involved.

## Context pack skeleton

```
# Context Pack — <project> — <phase>

## Identity
project: Hive|Mind
phase: <phase title>
branch: <scoped branch, never main>
agent_role: ui-builder | backend-builder | reviewer-finalizer | planning-agent |
            docs-agent | experiment-agent | source-research-agent | patch-agent

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

## Pre-flight (agent must report before editing)
- current branch
- latest commit
- git status
- whether required previous phase work exists
- files you expect to touch
- if assumptions are wrong, stop and report
```

## Rules

- A context pack is **scoped and branch-safe**. It always names a non-`main` branch.
- It always includes the pre-flight report requirement.
- It always names a validation command and a report format.
- It always names a handoff (who reviews, who decides).
