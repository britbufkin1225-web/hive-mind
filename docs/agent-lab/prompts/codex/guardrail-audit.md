# Prompt — Codex Guardrail Audit

> **Role:** `pr-auditor` · **Agent:** Codex · **Decision:** human gate
> Audit for scope creep, dependency drift, boundary violations, and missing tests.

Use Codex to **audit** a change against the guardrails. This is findings-only — report
violations; do not fix them.

## Brief

```
You are auditing a change for guardrail compliance on Hive|Mind, Phase <phase title>.

Branch / PR: <branch or PR>
Allowed scope: <path or glob>
Guardrails: <branch rules, dependency limits, backend/frontend boundary, test requirements>

Audit the diff and report findings in these categories:
  - Scope creep: changes outside the allowed files or stated task.
  - Dependency drift: new or changed dependencies / package files.
  - Boundary violations: frontend touching backend or vice versa beyond the phase scope.
  - Missing tests: changed behavior without corresponding validation.
  - Branch hygiene: any sign of direct main edits or branch collisions.

For each finding: file, line/area, what rule it violates, and severity (low/med/high).
If a category is clean, say so explicitly.

Report findings only. Do not implement fixes. The human decides on remediation.
```
