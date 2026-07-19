# Agent Role and Capability Matrix

Roles describe the current assignment; capability describes demonstrated risk
eligibility. Neither provider identity nor a previous role grants active authority.
The locked session header always determines the active, narrower permission set.

## Roles

| Role | Responsibility | Default boundary |
| --- | --- | --- |
| Primary implementer | Produce the locked phase contribution. | One owned branch/worktree and explicit paths. |
| Independent auditor and hardener | Verify another contribution and fix verified defects. | Separate session and hardening commit. |
| Specialist contributor | Deliver a narrow specialist scope. | No integration or phase-completion authority. |
| Read-only scout | Inspect and report evidence. | No repository writes. |
| Integration composer | Compose declared inputs in order. | Explicit per-session delegation required. |
| Human project owner | Set scope and resolve final authority decisions. | Final project authority. |

## Capability levels

| Level | Meaning | Permitted posture |
| --- | --- | --- |
| L0 | Read-only orientation | Inspect and report; no repository writes. |
| L1 | Bounded specialist | Narrow work only when explicitly authorized. |
| L2 | Bounded contributor | Isolated low-to-moderate risk implementation. |
| L3 | Full locked-phase contributor | Implement or independently audit a bounded phase within explicit guardrails. |
| L4 | Integration and project authority | Initially reserved for the human owner; agent composition requires explicit delegation. |

## Conservative starting defaults

```yaml
codex:
  default_level: L3
  observed_roles: [primary-implementer]
claude:
  default_level: L3
  observed_roles: [independent-auditor-hardener]
jules:
  default_level: L1
  observed_roles: [specialist-contributor, read-only-scout]
antigravity:
  default_level: L0
  optional_bounded_level: L1
  observed_roles: [read-only-scout]
future_untested_agents:
  default_level: L0
human_project_owner:
  level: L4
```

These defaults are conservative observations, not a permanent provider
hierarchy. A level does not bind an agent to one role. Promotion or demotion
requires human approval and evidence of repository behavior, not provider
reputation. The separation prevents over-trusting a new context or under-scoping
a demonstrated specialist; Phase 38B may validate level/role combinations but
must not promote agents automatically.
