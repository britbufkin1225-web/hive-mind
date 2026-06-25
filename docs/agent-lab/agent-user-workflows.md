# Agent + User Workflows

How human and agent work should operate on Hive|Mind. These workflows are practical patterns,
not theory. Every one of them ends at a human decision gate.

The governing rules are defined in [`registry/workflow-rules.yml`](registry/workflow-rules.yml).
Agent roles are defined in [`registry/agent-roles.yml`](registry/agent-roles.yml).

## Workflow 1 — UI Builder + Reviewer

1. Claude Code builds UI on a scoped branch with defined allowed files and forbidden scope.
2. Codex reviews and validates the branch before merge — build state, changed files, tests,
   guardrails.
3. The human approves the final merge decision.

**Roles:** `ui-builder` (Claude Code) → `reviewer-finalizer` (Codex) → human gate.

## Workflow 2 — Planning Agent + Implementation Agent

1. A planning agent creates scope, risks, and allowed files. No code changes.
2. An implementation agent performs a limited, scoped code change on its own branch.
3. A reviewer agent checks for drift against the plan.

**Roles:** `planning-agent` → `ui-builder` / `backend-builder` → `reviewer-finalizer` → human
gate.

## Workflow 3 — Experiment Agent

1. Cline, Roo Code, Aider, or OpenHands tests ideas on an **isolated** branch.
2. Experiments cannot touch `main`.
3. Useful output becomes **source data** (a session note, a prompt, a finding), not
   automatically product code. Promoting an experiment to product follows Workflow 1 or 2.

**Roles:** `experiment-agent` → human gate (promote or archive).

## Workflow 4 — Source Research Agent

1. An agent collects official docs and links into [`registry/source-links.yml`](registry/source-links.yml)
   and [`sources/official-agent-source-links.md`](sources/official-agent-source-links.md).
2. The human verifies important links before promotion.
3. The source registry stores verification status (`pending` → `verified`). Unverified URLs
   stay `verify-required`; **never invent URLs**.

**Roles:** `source-research-agent` → human verification gate.

## Workflow 5 — Agent Session Logging

1. Every agent run creates a session note in [`sessions/`](sessions/) using the
   [session template](templates/agent-session-entry-template.md).
2. The note records task, branch, files, tests, score, decision, and lessons.
3. No session note → the run is not considered complete or mergeable.

**Roles:** every role. Logging is mandatory, not optional.

## Workflow 6 — Human Decision Gate

1. Agents **propose**. They never merge themselves.
2. The human decides: merge, reject, retry, or escalate.
3. The decision becomes tracked project knowledge in the decision log
   (see [`decision-log-strategy.md`](decision-log-strategy.md)).

**Roles:** human is the only actor at this gate.

## Operating tone

Professional, clear, and practical. Agents do scoped work and report honestly. Humans decide.
The record is the product.
