# Agent Lab — Agent Ops Documentation Layer

> **Status:** Documentation and source-data first. App implementation later.
> **Scope:** Governed AI-assisted development workflow for Hive|Mind.

## What this folder is

`docs/agent-lab/` tracks how AI agents are used on Hive|Mind as **first-class project
knowledge**. It records:

- AI agent use and the roles each agent plays.
- Project source data and official source links for each agent.
- Reusable prompt packs for builders, reviewers, and shared workflows.
- Workflow governance and branch rules.
- Evaluation results and the human decisions that gate every merge.

This is not "we used AI tools." This is a **governed AI-assisted development workflow** with
auditable sessions, branch governance, and human decision gates.

## Why it exists

- **Prevent agent drift.** Every agent run has a defined scope, allowed files, and forbidden
  scope.
- **Prevent branch collisions.** One implementation agent per branch; nobody touches `main`.
- **Prevent undocumented AI-assisted changes.** Every run gets a session note with branch,
  task, files changed, validation result, review result, and human decision.
- **Build source data for the product.** These records are shaped so a future Agent Ops panel
  inside the app can ingest them directly.

## What lives here

```
docs/agent-lab/
├─ README.md                       ← you are here
├─ agent-model-source-registry.md  ← canonical registry + playbook (source of truth)
├─ agent-model-source-registry.docx← canonical original
├─ agent-ops-roadmap.md            ← phased roadmap (A–G)
├─ agent-user-workflows.md         ← human + agent workflow patterns
├─ future-implementation-plan.md   ← how this becomes app functionality
├─ context-pack-strategy.md        ← future context-pack generator design
├─ decision-log-strategy.md        ← how human decisions are captured
├─ prompt-pack-strategy.md         ← prompt pack categories and rules
├─ registry/                       ← machine-readable registry (YAML)
├─ prompts/                        ← reusable prompt packs (Claude / Codex / shared)
├─ sources/                        ← official source links
├─ templates/                      ← session + rubric templates
└─ sessions/                       ← one note per agent run
```

## Positioning

Documentation and source data come first. The
[`agent-ops-roadmap.md`](agent-ops-roadmap.md) lays out the path from documentation foundation
to a read-only Agent Registry API and, eventually, an Agent Lab frontend panel. **Do not
implement the future app phases yet** — they are documented so future phases can build them
cleanly against stable source shapes.

## Current coordination model

- **devdevbuilds** is the creator, main developer, and merge gate.
- **ChatGPT** is project manager/coordinator/scope guard.
- **Claude Code** owns UI Dynamics and frontend visual QA on scoped branches.
- **Codex** owns repo organization, documentation cohesion, API/app consistency,
  branch hygiene, and demo documentation.
- Other agents experiment only on isolated branches with explicit scope.

Agent Lab is documentation/source data for this coordination model. It is not an
implemented app feature yet.

## Start here

- New to the registry? Read [`agent-model-source-registry.md`](agent-model-source-registry.md).
- Want the roadmap? Read [`agent-ops-roadmap.md`](agent-ops-roadmap.md).
- Running an agent today? Copy the session template from
  [`templates/agent-session-entry-template.md`](templates/agent-session-entry-template.md) and
  follow the workflows in [`agent-user-workflows.md`](agent-user-workflows.md).

## One-line operating rule

> **devdevbuilds owns the merge gate. ChatGPT guards scope. Claude Code handles
> UI Dynamics. Codex keeps repo/docs/API/demo cohesion. Nobody touches main
> directly.**
