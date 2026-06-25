# Prompt Pack Strategy

Prompt packs are reusable, scoped, branch-safe prompts for agent runs. They live under
[`prompts/`](prompts/) and are organized by agent and by shared workflow.

The goal: stop rewriting briefings from scratch. A prompt pack encodes the role, the
guardrails, and the report format once, so every run starts from a known-good base.

## Prompt pack categories

| Category | Where | Purpose |
|---|---|---|
| Claude UI builder prompts | [`prompts/claude/ui-builder-brief.md`](prompts/claude/ui-builder-brief.md) | Primary UI build briefs. |
| Claude QA polish prompts | [`prompts/claude/qa-polish-pass.md`](prompts/claude/qa-polish-pass.md) | Small scoped QA/demo polish. |
| Claude screenshot review prompts | [`prompts/claude/screenshot-fix-pass.md`](prompts/claude/screenshot-fix-pass.md) | Screenshot-evidence UI fixes. |
| Codex review / finalizer prompts | [`prompts/codex/`](prompts/codex/) | Branch review, merge readiness, guardrail audit. |
| Shared guardrail prompts | [`prompts/shared/guardrails-template.md`](prompts/shared/guardrails-template.md) | Standard guardrail block. |
| Context pack prompts | [`prompts/shared/context-pack-template.md`](prompts/shared/context-pack-template.md) | Copy-paste agent briefing. |
| Validation report prompts | [`prompts/shared/validation-report-template.md`](prompts/shared/validation-report-template.md) | Standard validation report. |
| Phase brief prompts | [`prompts/shared/phase-brief-template.md`](prompts/shared/phase-brief-template.md) | General phase prompt skeleton. |
| Source research prompts | (future) | Collect + verify official source links. |

## Rules

- **Reusable.** A prompt pack works across phases; fill in the blanks per run.
- **Scoped.** Every prompt names allowed files and forbidden scope.
- **Branch-safe.** Every prompt names a non-`main` branch and the pre-flight report
  requirement.
- **Honest reporting.** Every prompt requires the agent to run validation and report results in
  the standard format.

## How packs compose

A typical run assembles:

1. A **phase brief** ([`phase-brief-template.md`](prompts/shared/phase-brief-template.md)) — the
   what and why.
2. The **guardrail block** ([`guardrails-template.md`](prompts/shared/guardrails-template.md)) —
   the boundaries.
3. A **role-specific prompt** (e.g. [`ui-builder-brief.md`](prompts/claude/ui-builder-brief.md)).
4. The **validation report format**
   ([`validation-report-template.md`](prompts/shared/validation-report-template.md)) — the
   required output.

The future context-pack generator (see [`context-pack-strategy.md`](context-pack-strategy.md))
assembles these automatically.
