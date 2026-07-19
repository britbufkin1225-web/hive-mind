# Hive|Mind Agent Lab

Agent Lab is the repository governance layer for predictable, composable,
auditable, and safe contributions by Codex, Claude, Jules, Antigravity, and
future agents. It governs contribution workflow; it does not grant runtime
authority to Hive|Mind or replace the product's Active Memory architecture.

## Canonical reading order

1. This `README.md` for boundaries and document routing.
2. [Contribution contract](agent-contribution-contract.md) for governing rules.
3. [Role and capability matrix](agent-role-capability-matrix.md) for eligibility.
4. [Session header lockup](agent-session-header-lockup.md) for active authority.
5. [Preflight checklist](agent-preflight-checklist.md) for repository checks.
6. [Composition manifest](agent-composition-manifest.md) for evidence and handoff.

The contribution contract governs stable policy. A locked session header narrows
that policy for one contribution and cannot silently expand it. The checklist
governs execution gates, and the manifest records what actually happened.

## Existing Agent Lab knowledge and source data

The governance documents above complement — and do not delete — the Agent Lab
knowledge and source data that predate Phase 38A. Where any earlier document
describes contribution roles, authority, or workflow, the governance documents
above are authoritative; the earlier material remains as background, source data,
and reusable assets:

- [Agent model and source registry](agent-model-source-registry.md) — canonical
  agent registry and playbook, with machine-readable data under
  [`registry/`](registry/) and official links in
  [`sources/`](sources/official-agent-source-links.md).
- [Agent Ops roadmap](agent-ops-roadmap.md) and
  [future implementation plan](future-implementation-plan.md) — the documented
  path toward later Agent Ops app functionality.
- [Agent user workflows](agent-user-workflows.md),
  [prompt-pack strategy](prompt-pack-strategy.md),
  [context-pack strategy](context-pack-strategy.md), and
  [decision-log strategy](decision-log-strategy.md) — human/agent workflow
  patterns and strategy notes, with reusable prompt packs under
  [`prompts/`](prompts/).
- [Session entry template](templates/agent-session-entry-template.md) and
  [review rubric](templates/agent-review-rubric.md) — per-run session notes
  (stored under [`sessions/`](sessions/)) and the evaluation rubric.

These records remain documentation and source data only; they grant no runtime
authority and do not override the governance documents above.

## Shared-state boundary

Agents do not automatically share ChatGPT conversation context, project memory,
another agent's session state, another agent's working directory, or another
agent's completion claims. Repository documents and direct repository evidence
are the shared source. Chat messages and agent summaries are inputs to verify,
not canonical state.

## Phase boundary

Phase 38A adds documentation contracts only. It adds no scripts, hooks, CI,
runtime enforcement, dependencies, application code, repository mutation
features, or agent services. Phase 38B may implement deterministic PowerShell
validation of these contracts after independent audit and human authorization.

Active Memory continues to govern project data, memory, contradiction, and
verification architecture. Agent Lab complements it by governing how humans and
agents contribute to the repository.

Every merge remains human-gated. Agents may prepare commits, evidence, audits,
hardening, pull requests, and merge-readiness recommendations; the human project
owner retains final merge and phase-completion authority.
