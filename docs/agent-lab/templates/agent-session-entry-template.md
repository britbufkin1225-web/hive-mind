# Agent Session Entry Template

Copy this block into `docs/agent-lab/sessions/<date>-<agent>-<phase>.md` for each agent run.

```yaml
source_id: agent_<tool>_<project>_<phase>_<date>
project: Hive|Mind
source_type: agent_session
agent_name: Claude Code | Codex | Cline | Roo Code | Aider | Copilot | Qodo | Other
model_or_provider: <provider/model if known>
task_phase: <phase title>
branch: <branch name>
commit_or_pr: <commit hash / PR number / none>
prompt_summary: <brief instruction summary>
files_touched:
  - <path>
commands_run:
  - <command>
validation_result: pass | fail | partial
risk_level: low | medium | high
guardrails_checked:
  - no direct main edits
  - no forbidden dependencies
  - no backend changes unless allowed
  - no dashboard redesign unless allowed
human_decision: accepted | rejected | merged | archived | needs-review
notes: <lessons, agent behavior, unresolved issues>
```
