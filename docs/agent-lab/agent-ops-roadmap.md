# Agent Ops Roadmap

> **Guardrail:** This roadmap documents future phases. Do **not** implement Phases D–G now.
> Documentation and source data come first; app implementation comes later.

This roadmap takes Agent Lab from a documentation foundation to a fully governed Agent Ops
layer inside Hive|Mind. Each phase is additive and should leave the previous phase intact.

## Phase A — Documentation Foundation ✅

Establish the canonical source registry and templates.

- Commit the source registry docs and templates.
- Preserve the canonical [`agent-model-source-registry.docx`](agent-model-source-registry.docx)
  and [`agent-model-source-registry.md`](agent-model-source-registry.md).
- Provide session-entry and review-rubric templates under [`templates/`](templates/).

## Phase B — Prompt Packs + Machine-Readable Registry

Make the registry reusable and machine-readable.

- Add reusable prompts for Claude, Codex, and shared workflows under [`prompts/`](prompts/).
- Add YAML registry files for agents, roles, workflow rules, sources, and evaluation under
  [`registry/`](registry/).
- Keep prompts scoped, reusable, and branch-safe.

## Phase C — Session Ledger Discipline

Make every agent run auditable.

- Every agent run gets a session note in [`sessions/`](sessions/).
- Record branch, task, files changed, validation result, review result, and human decision.
- Sessions follow the [session template](templates/agent-session-entry-template.md) so they can
  later be parsed into structured records.

## Phase D — Context Pack Generator

Automate agent briefings.

- A future script generates copy-paste-ready agent briefings from project status, current
  phase, guardrails, and source registry.
- See [`context-pack-strategy.md`](context-pack-strategy.md) for the design and skeleton.

## Phase E — Read-Only Agent Registry API

Expose the registry to the app, read-only.

- Backend exposes read-only agent registry, session, and source data.
- No mutation at first — read-only until the source shapes are stable.
- See [`future-implementation-plan.md`](future-implementation-plan.md) for suggested endpoints.

## Phase F — Agent Lab Frontend Panel

Surface the registry in the product.

- UI displays agents, roles, sessions, scores, source links, decisions, and branch outcomes.
- Agent cards, session ledger, prompt library browser, and decision log.

## Phase G — Agent Performance Intelligence

Turn the ledger into insight.

- Track which agents are best for UI, backend, QA, docs, branch review, source research, and
  patching.
- Surface trends across sessions, validation results, and human decisions.

## Sequencing rule

Ship A → B → C as documentation and data. Only start D once session discipline (C) produces
enough real records to test against. Only start E once the source shapes from D are stable.
Frontend (F) and intelligence (G) build on a stable read-only API.
