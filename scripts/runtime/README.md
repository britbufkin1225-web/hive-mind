# Managed Local Runtime Tool (Phase 39C)

A transparent PowerShell tool that starts the Hive|Mind **backend and frontend**
with one command, verifies both became reachable, and later stops **only** the
processes it started. It resolves which repository to run from the Phase 39B
[repository workspace configuration](../workspaces/README.md) and never
re-implements that resolution.

Full operator guide (prerequisites, troubleshooting, metadata/log locations,
guarantees): [`docs/operator-runtime.md`](../../docs/operator-runtime.md).

## Requirements

- PowerShell (Windows PowerShell 5.1 or PowerShell 7+).
- Python 3.11+ and Node.js 20+ on `PATH`, with backend and frontend dependencies
  already installed. The tool never installs anything.
- A configured, active Hive|Mind workspace (see the operator guide).

## Commands

Run from the repository root:

```powershell
./scripts/runtime/Invoke-HiveMindRuntime.ps1 start     # start backend + frontend and wait for readiness
./scripts/runtime/Invoke-HiveMindRuntime.ps1 status    # read-only managed runtime report
./scripts/runtime/Invoke-HiveMindRuntime.ps1 stop      # stop only the managed processes
./scripts/runtime/Invoke-HiveMindRuntime.ps1 restart   # managed stop, then managed start
./scripts/runtime/Invoke-HiveMindRuntime.ps1 verify    # read-only preflight (config, files, toolchain, ports)
```

Add `-Json` for machine-readable output. Use `-WorkspaceConfigPath` to point at
an explicit workspace configuration file (primarily for tests/CI).

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (including safe no-ops: already-running, already-stopped) |
| `2` | Runtime/operation failure (preflight failed, port conflict, service never became ready, stop incomplete) |
| `3` | Usage / invalid invocation |

## Design boundaries

- **Reuses Phase 39B.** The active repository is resolved only through the
  authoritative workspace CLI; the launcher never parses workspace config itself.
- **Owns exactly two processes.** Only the backend (uvicorn) and frontend (vite)
  it starts are managed; shutdown is gated by a per-process identity check
  (PID + creation time + command-line signature) so an unrelated or PID-reused
  process is never terminated. Nothing is ever killed by generic executable name.
- **Local-only, secret-free state.** Runtime metadata (schema
  `hivemind-runtime.v1`) and logs live under `%LOCALAPPDATA%\HiveMind\runtime\`,
  outside the repository, and contain no credentials or source content. Relocate
  with `HIVEMIND_RUNTIME_HOME`.
- **Bounded everything.** Readiness and shutdown waits are bounded and
  deterministic; a partial start rolls back automatically.

## Self-test

```powershell
pwsh -NoProfile -File ./scripts/runtime/tests/Invoke-HiveMindRuntimeSelfTest.ps1
```

The self-test replaces process, HTTP, port, clock, and workspace operations with
in-memory fakes and writes metadata under a throwaway directory, so it exercises
the full start/status/stop/restart/verify control flow without launching a real
process, opening a real socket, or touching the operator's configuration.
