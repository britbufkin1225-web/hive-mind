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
7. [Session launch guide](agent-session-launch-guide.md) for the end-to-end
   sequence that connects this policy to the Phase 38B executable preflight.

The contribution contract governs stable policy. A locked session header narrows
that policy for one contribution and cannot silently expand it. The checklist
governs execution gates, and the manifest records what actually happened.

## Agent Session Pack

The Agent Session Pack lets a fresh agent — one with no prior ChatGPT
conversation history — start a governed contribution from repository documents
alone:

- [Session launch guide](agent-session-launch-guide.md) — the ordered launch
  sequence, the session-concept-to-Phase-38B parameter mapping, the exact enum
  quick reference, exit-code interpretation, the automated-versus-manual split,
  fail-closed recovery, and per-agent session examples.
- [Agent unavailability and fallback](agent-unavailability-and-fallback.md) —
  how to represent a temporarily excluded agent without inventing invalid enum
  values, the current fallback distribution, and provider-created empty-PR
  handling.
- Copy-paste JSON templates under [`templates/`](templates/):
  [`agent-session-header.template.json`](templates/agent-session-header.template.json)
  (session metadata) and
  [`agent-composition.template.json`](templates/agent-composition.template.json)
  (a JSON serialization of the `agent-composition.v1` manifest that validates
  through the Phase 38B `-ManifestPath` workflow).

The session pack is documentation only. It routes to the existing Phase 38A
policy and the Phase 38B validator; it adds no executable governance behavior.

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

Phase 38A adds the policy contracts and remains the source of truth. Phase 38B
adds [dependency-free local PowerShell validation](../../scripts/governance/README.md)
of repository identity, Git state, explicit session declarations, and JSON
serializations of the existing composition manifest. It adds no hooks, CI,
dependencies, application code, repository mutation features, or agent services.

Active Memory continues to govern project data, memory, contradiction, and
verification architecture. Agent Lab complements it by governing how humans and
agents contribute to the repository.

Every merge remains human-gated. Agents may prepare commits, evidence, audits,
hardening, pull requests, and merge-readiness recommendations; the human project
owner retains final merge and phase-completion authority.
