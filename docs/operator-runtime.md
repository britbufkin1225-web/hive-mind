# Managed Local Runtime (Phase 39C)

Hive|Mind ships a single operator command that starts the backend and frontend
together, verifies that both actually became reachable, and later stops **only**
the processes it started. It is a thin, transparent process manager over the
repository's existing dev commands — not a service installer, container system,
or background daemon.

The launcher resolves *which* repository to run from the persistent
[repository workspace configuration](../scripts/workspaces/README.md) introduced
in Phase 39B, so you never re-enter a path.

## Prerequisites

- **Python 3.11+** with the backend dependencies installed
  (`python -m pip install -r apps/backend/requirements-dev.txt`).
- **Node.js 20+** with frontend dependencies installed (`npm install` at the
  repository root — this hoists `vite` into the root `node_modules`).
- **A configured, active workspace.** Register the Hive|Mind repository once:

  ```powershell
  python .\apps\backend\app\console\repository_workspace_cli.py add `
      --id hive-mind --name "Hive|Mind" `
      --repository-root "C:\Users\<you>\Documents\hive-mind" `
      --expected-remote "https://github.com/britbufkin1225-web/hive-mind.git" `
      --activate
  ```

  The workspace registry is stored under your local application-data directory
  (never inside the repository), so no machine-specific path is committed.

The launcher never installs dependencies. If Python, Node, or `vite` is missing,
it reports the gap and stops — run the install command yourself.

## Commands

```powershell
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 start     # start backend + frontend, wait for readiness
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 status    # report managed runtime health (read-only)
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 stop      # stop only the managed processes
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 restart   # managed stop, then managed start
.\scripts\runtime\Invoke-HiveMindRuntime.ps1 verify    # check config, files, toolchain, ports (read-only)
```

Add `-Json` to any command for machine-readable output. Exit codes: `0` success,
`2` runtime/operation failure, `3` invalid invocation.

### `start`

Resolves the active workspace, validates that it is the Hive|Mind repository and
that the backend/frontend project files exist, checks that both ports are free,
then launches:

- **backend** — `python -m uvicorn app.main:app --app-dir apps/backend --host 127.0.0.1 --port 8787`
- **frontend** — the installed Vite dev server on `--host 127.0.0.1 --port 5173`

It records bounded runtime metadata, then waits (bounded) for the backend
`/health` endpoint to return a valid Hive|Mind health response and for the
frontend to answer over HTTP. It prints a final `PASS`/`FAIL` with the URLs. If
one service comes up but the other never becomes ready, `start` automatically
rolls back the service it launched and leaves no managed processes behind.

> The backend is launched **without** `--reload`. Reload spawns a supervisor plus
> a worker child; a single process gives the manager one unambiguous owner to
> track and stop. Both ports match the repository's `npm run dev:*` defaults; the
> host is bound to loopback (`127.0.0.1`) so the services are local-only and do
> not trigger a firewall prompt.

### `status`

Read-only. Reports the configured workspace, whether runtime metadata exists,
each managed process's liveness (validated by identity, not just PID), backend
health, frontend reachability, the PIDs, the service URLs, and an overall state:

| Overall | Meaning |
| --- | --- |
| `stopped` | No managed runtime (no metadata, or no active workspace). |
| `starting` | Both processes are up but readiness has not yet been confirmed. |
| `healthy` | Both processes alive; backend healthy and frontend reachable. |
| `degraded` | Both processes alive but health/reachability is failing. |
| `partial` | Exactly one managed process is alive. |
| `stale` | Metadata exists but no recorded process is still ours (e.g., after a reboot), or metadata is malformed. |

### `stop`

Reads only the managed runtime metadata. For each recorded process it re-checks
identity (name, process creation time, and command-line signature) before doing
anything — a reused PID or unrelated process is skipped, never terminated. It
stops the managed frontend and backend (and any child processes they spawned),
waits a bounded time for exit, escalates once if needed, and clears the metadata.
It **never** terminates processes by generic name (no "kill all python/node").

### `restart` / `verify`

`restart` composes the ordinary managed `stop` then `start`. `verify` performs a
read-only preflight (workspace, repository layout, Python/Node/vite availability,
and port ownership) without starting anything.

## Default URLs

- Frontend: <http://127.0.0.1:5173>
- Backend: <http://127.0.0.1:8787>
- Backend health: <http://127.0.0.1:8787/health>

## Runtime metadata and logs

Runtime state lives **outside** the repository, under your local application-data
directory, keyed by workspace id:

```text
%LOCALAPPDATA%\HiveMind\runtime\<workspace-id>\runtime.json
%LOCALAPPDATA%\HiveMind\runtime\<workspace-id>\logs\backend.out.log
%LOCALAPPDATA%\HiveMind\runtime\<workspace-id>\logs\backend.err.log
%LOCALAPPDATA%\HiveMind\runtime\<workspace-id>\logs\frontend.out.log
%LOCALAPPDATA%\HiveMind\runtime\<workspace-id>\logs\frontend.err.log
```

The metadata is a small, human-inspectable JSON document (schema
`hivemind-runtime.v1`) written atomically. It records the workspace id,
repository path, start time, both PIDs and their identity fingerprints, the
service URLs, the launcher PID, and the runtime state. It contains **no**
credentials, tokens, environment secrets, or source content. Logs are rewritten
fresh on each `start`, so they stay bounded by the runtime lifecycle. Set
`HIVEMIND_RUNTIME_HOME` to relocate this tree (used by the self-tests).

## Troubleshooting

**"port … is already in use by pid N (name)"** — another process holds `8787`
or `5173`. If it is a stray previous run, `stop` (or `restart`) clears the
managed one; otherwise stop the conflicting process or free the port. `start`
detects this *before* launching anything, so it never leaves a half-started
runtime.

**"backend did not become healthy" / "frontend did not become reachable"** — the
process started but never answered in time. Check the referenced log file. The
runtime is rolled back automatically, so a plain `start` retry is safe.

**Stale state after a reboot or crash** — `status` reports `stale` when the
recorded PIDs are no longer ours. A subsequent `start` clears the stale metadata
automatically before launching; `stop` on stale/absent metadata is a safe no-op.

**Malformed metadata** — `stop` removes an unreadable metadata file without
terminating anything (it cannot trust the PIDs), returning a deterministic clean
state.

## Guarantees

- Only processes this workflow started are ever stopped; identity is verified by
  PID **plus** process creation time **plus** command-line signature.
- No machine-specific path or secret is written into the repository — workspace
  configuration and runtime state both live under your local app-data directory.
- Every wait is bounded and deterministic; a failed launch never hangs.
