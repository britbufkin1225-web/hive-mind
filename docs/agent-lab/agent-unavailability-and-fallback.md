# Agent Unavailability and Fallback

This document explains how to represent a temporarily unavailable agent, how to
reassign its responsibilities safely, and how to respond when provider tooling
creates a branch or pull request that no assignment authorized. It complements
the [Agent Session Launch Guide](agent-session-launch-guide.md) and is
documentation only — it changes no executable governance behavior.

## Principles

- An unavailable agent is **excluded from the active composition**. It is not
  present with a placeholder role.
- An unavailable agent does **not** receive placeholder or invalid enum values.
  Temporary unavailability is recorded only as availability/exclusion metadata,
  never by inventing a fake role, capability, composition mode, or write
  authority.
- Responsibilities may be reassigned **only to an authorized active agent** whose
  role and capability already cover the work.
- Independent review must remain independent. An implementer's self-review is
  never an independent audit, even when the usual auditor is unavailable.
- The human merge gate (`devdevbuilds`) is **never** replaced by an agent,
  regardless of who is unavailable.

## Representing a temporary exclusion

Record temporary unavailability as adoption/session metadata. It is **not**
currently enforced by Phase 38B executable logic — the preflight validates the
individual session values it is given; it does not read an availability roster or
suspend an agent at runtime.

```yaml
temporarily_excluded_agents:
  - agent: codex
    through: 2026-07-24
    reason: token allowance unavailable
```

The JSON equivalent lives in
[`templates/agent-session-header.template.json`](templates/agent-session-header.template.json)
under `temporarily_excluded_agents`. Do not represent the excluded agent as an
active record with invalid placeholder enum values; represent the state only
through this metadata.

## Codex exclusion (through 2026-07-24)

Codex is outside the active agent pool through **July 24, 2026**. During the
exclusion window, Codex must not be assigned implementation, audit, testing,
documentation, support, fallback, reconnaissance, review, PR work, or merge work.

Codex must not appear as an active actor using invalid placeholder enum values.
Represent it only with the `temporarily_excluded_agents` metadata above.

## Current active pool and fallback

The currently active composition is Claude Code, Jules, Antigravity, and ChatGPT,
with `devdevbuilds` as the merge gate. The current fallback distribution while
Codex is excluded is:

| Agent | Fallback responsibility |
| --- | --- |
| Claude Code | Primary implementation. |
| Jules | Independent documentation and contract review. |
| Antigravity | Read-only reconnaissance. |
| ChatGPT | Composition and handoff drafting (no local execution). |
| devdevbuilds | Merge gate. |
| Codex | Excluded through July 24, 2026 — receives no work. |

Reassignment never collapses independence: the implementer and the independent
reviewer remain different actors, and the merge gate remains the human owner.

## Provider-created branches and empty PRs

A provider platform may create a branch or a pull request automatically even when
the locked assignment grants no PR authority. Provider behavior is **not**
authorization, and an unauthorized or empty PR must never be merged.

When an unauthorized or empty provider PR appears:

1. **Verify** the PR contents and the changed-file count before doing anything
   else.
2. **Do not merge** an unauthorized or empty PR.
3. **Recover** any required report text carried in the PR (for example, review
   comments) so no intended evidence is lost.
4. **Close** the PR with an audit-trail comment explaining why.
5. **Delete the provider branch only under `devdevbuilds` authority.**
6. **Confirm** that no intended changes were lost.
7. **Record** the provider behavior separately from agent authorization, so the
   audit trail distinguishes "the platform did this" from "an agent was
   authorized to do this."

For example, PR #173 was auto-created by a provider for a read-only session that
held no PR authority; the correct handling is to preserve its review comments and
close it without merging. Treat that only as an illustration of provider
behavior — do not build a durable process that depends on a specific PR number.

## Deferred (Phase 38D candidates)

The following are recorded as candidates for separate planning and explicit human
approval. They are **not** implemented and **not** pre-decided as mandatory:

- executable availability-policy enforcement;
- runtime active/suspended-agent validation;
- provider-PR authorization detection;
- session-identifier uniqueness and workspace concurrency hashes;
- `input_commit` existence verification;
- JSON Schema publication and expanded composition schema;
- CI or Git-hook integration and fetch-freshness policy;
- optional wrapper tooling and post-edit path-ownership enforcement.

Until such a phase is planned and approved, unavailability and provider-PR
handling remain **manual obligations** governed by this document.

## Reference documents

- [Agent Session Launch Guide](agent-session-launch-guide.md)
- [Agent Lab README](README.md)
- [Agent Contribution Contract](agent-contribution-contract.md)
- [Role and Capability Matrix](agent-role-capability-matrix.md)
- [PowerShell Governance README](../../scripts/governance/README.md)
