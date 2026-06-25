# Decision Log Strategy

Agents propose. Humans decide. This document defines how those human decisions are captured as
tracked project knowledge — the final gate in [Workflow 6](agent-user-workflows.md).

Every agent run ends at a decision. Recording it makes the workflow auditable and feeds the
future decision log surface (Future Implementation Plan
[decision log](future-implementation-plan.md)).

## Decision types

| Decision | Meaning |
|---|---|
| `approve` | Work is accepted as-is. |
| `reject` | Work is not accepted; not merged. |
| `retry` | Send back to the same agent with adjusted scope. |
| `split phase` | Break the task into smaller scoped phases. |
| `merge` | Merge the branch into the target. |
| `postpone` | Defer the decision to a later phase. |
| `escalate to reviewer` | Hand to a reviewer/finalizer agent before deciding. |
| `switch agent` | Re-run the task with a different agent. |
| `revert` | Undo a previously merged change. |
| `mark W100` | Mark as a clean win / fully validated outcome. |
| `mark T404/W404` | Mark as a known failure / missing-result outcome. |

> `W100` and `T404/W404` are project status codes. `W100` = validated win.
> `T404`/`W404` = task/work not found or not delivered. Keep their use consistent across
> sessions so the codes stay queryable.

## Example decision record

```yaml
decision_id: dec_2026-06-25_phase9c_merge
date: 2026-06-25
phase: Phase 9C — Knowledge Graph Visualization QA + Demo Polish
branch: phase-9c-graph-viz-qa-polish
agent: Claude Code
decision: merge
reason: Scoped UI polish validated; reviewer confirmed no scope creep.
evidence: frontend build pass; screenshots attached; Codex review note.
validation: pass
outcome: merged to main via PR #24
follow_up: none
```

## Fields

| Field | Meaning |
|---|---|
| `decision_id` | Stable unique ID, e.g. `dec_<date>_<phase>_<action>`. |
| `date` | Decision date (absolute). |
| `phase` | Phase title the decision applies to. |
| `branch` | Branch the decision acts on. |
| `agent` | Agent whose work is being decided on. |
| `decision` | One of the decision types above. |
| `reason` | Short justification. |
| `evidence` | What supported the decision (builds, tests, screenshots, reviews). |
| `validation` | `pass` / `fail` / `partial`. |
| `outcome` | What actually happened (merged, reverted, archived, etc.). |
| `follow_up` | Any required follow-up, or `none`. |

## Rules

- Every merge, reject, or revert has a decision record.
- A decision record references the session note(s) it acts on.
- Decisions are not edited after the fact; corrections get a new record that references the
  prior one.
