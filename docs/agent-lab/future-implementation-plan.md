# Future Implementation Plan

> **Guardrail:** This is a forward-looking plan. No app code is implemented in this phase.
> Read-only first. No database mutation until the source shapes are stable.

How the Agent Lab documentation layer eventually becomes app functionality inside Hive|Mind.
This plan corresponds to Phases E–G of the [Agent Ops Roadmap](agent-ops-roadmap.md).

## Future app features

- **Agent Registry API** — serve the agent catalog from
  [`registry/agents.yml`](registry/agents.yml).
- **Agent Sessions API** — serve session records from [`sessions/`](sessions/).
- **Source Links API** — serve verified source links from
  [`registry/source-links.yml`](registry/source-links.yml).
- **Evaluation Scores API** — serve rubric scores from
  [`registry/evaluation-rubric.yml`](registry/evaluation-rubric.yml).
- **Agent Lab frontend panel** — the in-app surface for everything below.
- **Agent cards** — per-agent summary: roles, best-for, risks, branch permissions.
- **Session ledger** — chronological list of agent runs with validation and decisions.
- **Prompt library browser** — browse and copy the [`prompts/`](prompts/) packs.
- **Decision log** — human decisions as tracked knowledge
  (see [`decision-log-strategy.md`](decision-log-strategy.md)).
- **Context pack generator** — build agent briefings on demand
  (see [`context-pack-strategy.md`](context-pack-strategy.md)).
- **Agent performance dashboard** — which agents are best for which work.
- **Branch safety checklist** — surfaces the [workflow rules](registry/workflow-rules.yml).
- **Guardrail compliance report** — flags sessions that broke scope or skipped validation.

## Suggested future endpoints

> Read-only at first. Each maps to a documented source file, not a live mutation surface.

| Endpoint | Returns | Backed by |
|---|---|---|
| `GET /api/agents` | Agent catalog | [`registry/agents.yml`](registry/agents.yml) |
| `GET /api/agents/{agent_id}` | Single agent | [`registry/agents.yml`](registry/agents.yml) |
| `GET /api/agent-sessions` | Session ledger | [`sessions/`](sessions/) |
| `GET /api/agent-sessions/{session_id}` | Single session | [`sessions/`](sessions/) |
| `GET /api/agent-sources` | Source links | [`registry/source-links.yml`](registry/source-links.yml) |
| `GET /api/agent-workflow-rules` | Workflow rules | [`registry/workflow-rules.yml`](registry/workflow-rules.yml) |
| `GET /api/agent-evaluation-rubric` | Scoring rubric | [`registry/evaluation-rubric.yml`](registry/evaluation-rubric.yml) |

## Implementation rule

**Read-only first. No database mutation until the source shapes are stable.**

1. Stabilize the YAML shapes in [`registry/`](registry/) and the session template.
2. Serve them read-only (Phase E).
3. Build the frontend panel against the read-only API (Phase F).
4. Only then consider write paths (creating sessions, recording decisions in-app) — and only
   after the shapes have proven stable across many real sessions.

## Data shape stability

The API contracts above should mirror the documented fields exactly:

- Agent fields: see [`registry/agents.yml`](registry/agents.yml).
- Session fields: see [`templates/agent-session-entry-template.md`](templates/agent-session-entry-template.md).
- Source fields: see [`registry/source-links.yml`](registry/source-links.yml).
- Rubric categories: see [`registry/evaluation-rubric.yml`](registry/evaluation-rubric.yml).

Changing a documented field is a breaking change. Treat the docs as the schema until a formal
schema replaces them.
