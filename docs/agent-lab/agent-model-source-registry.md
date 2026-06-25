# HIVE|MIND — Agent Model Source Registry & Implementation Playbook

> **Status:** Project source of truth for how agents are used on Hive|Mind.
> **Version:** 0.1 · **Prepared:** 2026-06-25
> **Canonical original:** [`agent-model-source-registry.docx`](agent-model-source-registry.docx)
>
> This is a **reusable source registry and implementation guide** for projects that use AI
> coding, planning, review, and documentation agents. Written for Hive|Mind first, but the
> templates are project-agnostic. **We will steer the product to match this over time —
> treat it as a forward-looking spec, not just process docs.**

## 1. Project angle

Hive|Mind is a full-stack knowledge graph dashboard and local intelligence layer. It connects
Obsidian vaults and future local/external data sources into a normalized backend model,
searchable API, source registry, command console, and read-only graph frontend.

The product direction is a **dark intelligence workbench**: command-console UX, source
provenance, graph intelligence overlays, and keyboard-first power-user controls. The goal is a
serious hacker-tool / analyst-console experience, not fake terminal cosplay.

## 2. Why this source registry exists

- Keep agent usage auditable across projects.
- Track which agent made which implementation decision.
- Capture prompt, branch, commit, PR, validation result, and risk notes.
- Compare agents on frontend design, backend correctness, review quality, and branch hygiene.
- Create structured project source data that can later feed Hive|Mind itself.

## 3. Recommended agent stack

| Agent | Preferred role | Best Hive|Mind use | Caution |
|---|---|---|---|
| **Claude Code** | Primary UI builder | Frontend polish, component/CSS work, screenshot-driven fixes, controlled implementation branches | High visual judgment; can over-edit if scope is loose. |
| **Codex** | Reviewer / finalizer | Branch verification, test gates, PR review, merge safety, guardrail enforcement | Best as engineering governor, not the only UI craft pass. |
| **GitHub Copilot Student/Free** | Daily IDE assistant | Inline suggestions, PR help, quick explanations, second-opinion edits | Strong student/free value; verify current entitlement. |
| **Cline / Roo Code** | Alternate UI agent | Local VS Code agent experiments, Plan/Act workflows, component updates | Useful as Claude comparison; keep on separate branches. |
| **Aider** | Terminal / Git patch agent | Small commits, docs fixes, tests, targeted refactors | Good Git discipline; less visual-design oriented. |
| **Qodo / Copilot Review** | Review agent | PR review, test gaps, consistency checks | Good external critic; do not let review-only tools drive product scope. |

## 4. Candidate agent source registry

> Treat free/trial/free-tier notes as **source leads, not permanent pricing facts**. Re-check
> official pages before committing to a long workflow.

| Tool | Category | Best use | Testing note |
|---|---|---|---|
| GitHub Copilot Student/Free | IDE assistant / code review | Student/free access path; daily coding assistant | Activate if student eligibility is available; useful across all projects. |
| Cline | Agentic local coding | Frontend/UI implementation comparison | Open-source tool; model/API cost depends on provider. |
| Roo Code | Agentic local coding | Mode-based planning, debugging, implementation | Good alternate to Claude Code; keep task scope tight. |
| Aider | Terminal pair programmer | Git-native patches and small commits | Excellent for branch-based agent lab experiments. |
| Continue | Open-source coding agent | Local/BYOK experimentation | Current ecosystem status should be verified before deep setup. |
| Kilo Code | IDE/CLI/cloud coding agent | Architect/planning mode and model comparison | Test on noncritical branches first. |
| OpenHands | Cloud/sandbox agent platform | Bigger autonomous agent experiments | Heavier setup; more research-platform than quick UI pass. |
| Jules | Async cloud coding agent | Background GitHub issue/PR experiments | Use later; not during delicate branch recovery. |
| Qodo | PR review / governance | Automated PR review and quality checks | Reviewer layer, not main UI builder. |
| Amazon Q Developer | Secondary assistant | Free-tier review/coding experiments | Useful but not primary for Hive|Mind UI craft. |
| Replit Agent | Prototype sandbox | Throwaway prototypes and UI idea tests | Keep outside source-of-truth repo; credits/usage require attention. |

## 5. Source registry fields

| Field | Meaning |
|---|---|
| `source_id` | Stable unique ID, e.g., `agent_claude_code_phase_9c`. |
| `project` | Project name: Hive|Mind, GhostBrain Infinity, ZeroSOC, etc. |
| `source_type` | `agent_session`, `official_doc`, `implementation_branch`, `PR_review`, `screenshot`, `run_log`, `prompt`. |
| `agent_name` | Claude Code, Codex, Cline, Aider, Copilot, etc. |
| `model_or_provider` | Claude, OpenAI, GitHub, local model, BYOK provider, unknown. |
| `task_phase` | Example: Phase 9C — Knowledge Graph Visualization QA + Demo Polish. |
| `branch` | Working branch used by the agent. |
| `commit_or_pr` | Commit hash, PR number, or link if available. |
| `prompt_summary` | One-paragraph description of the instruction given. |
| `files_touched` | List of modified files. |
| `commands_run` | Build/test/validation commands executed. |
| `validation_result` | Pass/fail/partial, plus short details. |
| `risk_level` | Low, medium, high. |
| `guardrails_checked` | No backend changes, no deps, no graph mutation, etc. |
| `human_decision` | Accepted, rejected, merged, needs review, archived. |
| `notes` | Lessons, bugs, agent behavior, and follow-up ideas. |

## 6. Agent lab workflow

1. Create a dedicated branch for each agent experiment.
2. Start with a short briefing: goal, allowed files, guardrails, validation commands, report format.
3. Require the agent to report branch, latest commit, git status, and assumptions before editing.
4. Run the smallest possible implementation task.
5. Run build/tests and collect command output.
6. Capture screenshots or rendered evidence for UI work.
7. Record an agent registry entry before merge or archive.
8. Use Codex or another reviewer agent for final verification when available.

## 7. Branch governance rules

- No agent works directly on `main`.
- No two agents edit the same branch at the same time.
- Every agent task must define allowed files and forbidden scope.
- Every UI branch must pass frontend build before merge consideration.
- Every backend/shared branch must pass backend tests before merge consideration.
- Merge only after human review or an explicit finalizer-agent review.
- If branch assumptions are wrong, stop and report rather than improvising.

## 8. Implementation-source template

See [`templates/agent-session-entry-template.md`](templates/agent-session-entry-template.md).

## 9. Agent evaluation rubric

See [`templates/agent-review-rubric.md`](templates/agent-review-rubric.md).

## 10. Hive|Mind future-agent angle

Later, Hive|Mind can ingest its own agent records as source data. The product can show which
agent produced which code, what evidence supported the merge, what failed validation, and what
source documents shaped the implementation.

- Agent sessions become traceable source objects.
- PR reviews become provenance events.
- Build/test results become validation evidence.
- Screenshots become UI-state evidence.
- Prompts become planning artifacts.
- Human decisions become confirmation events.

## 11. Recommended project folder structure

```
docs/
  agent-lab/
    agent-model-source-registry.docx
    agent-model-source-registry.md
    sessions/
      2026-06-25-claude-code-phase-9c.md
      2026-06-25-codex-review-phase-9c.md
      2026-06-25-cline-console-ux-test.md
    sources/
      official-agent-source-links.md
    templates/
      agent-session-entry-template.md
      agent-review-rubric.md
```

## 12. Guardrail language for future prompts

```
Before editing, report:
- current branch
- latest commit
- git status
- whether required previous phase work exists
- files you expect to touch

Do not work directly on main.
Do not add dependencies unless explicitly approved.
Do not change backend unless the phase allows it.
Do not broaden the UI redesign.
If assumptions are wrong, stop and report.
```

## 13. Reference source links

See [`sources/official-agent-source-links.md`](sources/official-agent-source-links.md).

## 14. One-line operating rule

> **Claude builds the UI. Codex audits the UI. Other agents experiment on isolated branches.
> Nobody touches main directly.**
