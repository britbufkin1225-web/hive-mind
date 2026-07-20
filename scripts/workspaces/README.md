# Repository Workspace Operator Tool (Phase 39B)

A small, dependency-free PowerShell surface for managing the **local-only**
Hive|Mind repository workspace registry. It wraps the authoritative Python CLI
(`apps/backend/app/console/repository_workspace_cli.py`) so validation, path
resolution, atomic persistence, and diagnostics live in one place.

The configuration is **local and must not be committed**. By default it is stored
outside the repository — on Windows under
`%LOCALAPPDATA%\HiveMind\repository-workspaces.json`. Override the location with
the `HIVEMIND_WORKSPACE_CONFIG_PATH` environment variable or the `-ConfigPath`
parameter.

## Requirements

- PowerShell (Windows PowerShell 5.1 or PowerShell 7+).
- Python on `PATH` (or pass `-PythonExecutable`). No administrator privileges are
  required.

## Commands

Run from the repository root:

```powershell
# Show the resolved configuration path (and whether it exists yet)
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 path -Json

# Initialize an empty configuration (refuses to clobber unless -Overwrite)
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 init

# Register a repository and select it as active
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 add `
    -Id hive-mind -Name 'Hive|Mind' `
    -RepositoryRoot 'C:\Users\britb\Documents\hive-mind' `
    -ExpectedRemote 'https://github.com/britbufkin1225-web/hive-mind.git' `
    -Activate

# List, show, select, validate, remove
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 list
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 show -Id hive-mind
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 set-active -Id hive-mind
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 validate -Json
./scripts/workspaces/Invoke-HiveMindWorkspace.ps1 remove -Id hive-mind
```

Add `-Json` to any command for machine-readable output consistent with the
Phase 38B governance tooling.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Operation or configuration error (duplicate, not found, malformed/unsupported/oversized config, credential-bearing remote, save failure) |
| `3` | Usage / invalid invocation (including an invalid `HIVEMIND_WORKSPACE_CONFIG_PATH` override) |

## What `validate` reports

`validate` confirms the configuration document is structurally valid and reports
per-workspace **availability diagnostics** (repository absent, path is not a Git
repository, expected-remote mismatch, active workspace disabled, and so on). It
is read-only: it never rewrites or deletes an unavailable workspace and never
mutates the repository or its Git history. Repository probing reuses the
deterministic read-only Git adapter.

## Safety boundaries

- Local-only; no network access during configuration validation.
- Credentials/tokens embedded in a remote URL are rejected, never stored.
- The active-workspace resolver is inert: a future Repository Observer phase may
  consume it, but this tool never runs observation, polling, or ingestion.

## Self-test

```powershell
pwsh -NoProfile -File ./scripts/workspaces/tests/Invoke-HiveMindWorkspaceSelfTest.ps1
```

The self-test isolates every case with a throwaway `-ConfigPath`, so it never
touches the operator's real configuration.
