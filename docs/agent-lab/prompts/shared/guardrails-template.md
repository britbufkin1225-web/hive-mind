# Template — Standard Guardrail Block

> Paste this block into every agent brief. It encodes the branch governance from the source
> registry playbook and [`registry/workflow-rules.yml`](../../registry/workflow-rules.yml).

```
Guardrails:

Before editing, report:
  - current branch
  - latest commit
  - git status
  - whether required previous phase work exists
  - files you expect to touch

Do not work directly on main.
Do not add dependencies unless explicitly approved.
Do not change backend unless this phase allows it.
Do not broaden the UI redesign beyond the active task.
Do not edit files outside the allowed list.
If assumptions are wrong, stop and report rather than improvising.

You propose; the human decides merge / reject / retry / escalate.
Produce a session note for this run.
```
