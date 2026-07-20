# Phase 39B — Persistent Local Repository Workspace Configuration

## Purpose

Hive|Mind's Repository Observer (Phases 37I–37P) is request-driven: every
snapshot or drift analysis requires the operator to supply a repository root.
Phase 39B adds a durable, **local-only** workspace registry so an operator can
register a repository once and have Hive|Mind remember it between application
sessions. This phase establishes configuration and operator tooling only. It
adds no background observation, no automatic repository mutation, and no frontend
configuration interface.

The intended daily workflow:

1. An operator registers a local Git repository once.
2. Hive|Mind stores a bounded workspace definition locally.
3. The operator lists configured workspaces.
4. One workspace is selected as active.
5. A future Repository Observer phase resolves the active repository without
   re-entering its path.
6. Invalid or unavailable repositories produce explicit diagnostic states rather
   than destructive automatic repair.

## What this phase does not do

- It does **not** watch repositories or poll them in the background.
- It does **not** run Repository Observer snapshots or drift analysis
  automatically.
- It does **not** insert anything into Active Memory.
- It does **not** synchronize workspaces across machines.
- It does **not** add a frontend workspace editor.
- It does **not** encrypt the configuration.
- It does **not** mutate repository contents or Git history.
- It does **not** resume Phase 36K.

## Configuration contract (`repository-workspaces.v1`)

The persisted document is a small JSON object with an explicit
`schema_version`. A loader rejects any other version rather than guessing.

```jsonc
{
  "schema_version": "repository-workspaces.v1",
  "active_workspace_id": "hive-mind",
  "workspaces": [
    {
      "workspace_id": "hive-mind",
      "display_name": "Hive|Mind",
      "repository_root": "C:\\Users\\britb\\Documents\\hive-mind",
      "expected_remote": "https://github.com/britbufkin1225-web/hive-mind.git",
      "enabled": true
    }
  ]
}
```

Each workspace record holds only the minimum needed for deterministic local
operation: a stable identifier, a human-readable name, an absolute repository
root, an optional expected canonical remote, and an enabled flag. The document
records at most one operator-selected active workspace. There are **no
timestamps** — they add nondeterminism without value here.

Bounds (rejected, never silently truncated): workspace id ≤ 128 chars, display
name ≤ 256, repository root ≤ 4096, expected remote ≤ 2048, ≤ 256 workspace
records, and a ≤ 256 KiB configuration file.

## Configuration location

Resolution order (see `resolve_workspace_config_path`):

1. The `HIVEMIND_WORKSPACE_CONFIG_PATH` environment override.
2. The OS-appropriate user configuration directory. On **Windows** this is
   `%LOCALAPPDATA%\HiveMind\repository-workspaces.json` — outside the repository
   and outside OneDrive. Elsewhere it follows the XDG convention
   (`$XDG_CONFIG_HOME/hive-mind/repository-workspaces.json`).
3. A safe user-home fallback when neither is available.

Path resolution never creates or writes anything; directories are created only
when an explicit save or `init` requires them. The configuration is **local and
must not be committed** (the default location already lives outside the
repository).

## Atomic, corruption-resistant persistence

Writes serialize the complete validated document, write it to a temporary
sibling file, `flush`/`fsync`, and then `os.replace` it into place atomically.
A failed write leaves the previous valid file intact, and a malformed or
oversized existing file is never overwritten unless the operator explicitly
requests initialization or replacement. Serialized output is deterministic
(workspaces ordered by id).

## Identity and remote safety

Duplicate detection uses a canonical comparison key that folds Windows
drive-letter casing, separator direction, duplicate and trailing separators, and
Unicode form (NFC), while the operator-readable path is preserved for display.
Expected remotes normalize ordinary HTTPS and SSH forms to a common key for
mismatch detection; credential-bearing remotes (`user:secret@…`, lone tokens)
are rejected before persistence so secrets are never stored. Configuration
validation performs no network access.

## Failure and diagnostic states

Structural problems raise typed exceptions: absent, malformed, unsupported
version, inaccessible, too large, duplicate id, duplicate root, missing active
workspace, credential-bearing remote, and atomic-save failure. Repository
availability is reported as non-destructive diagnostics: no active workspace,
active workspace disabled, repository root absent/inaccessible, path is not a Git
repository, expected remote absent/mismatched, and Git unavailable. Unavailable
repositories are retained with a diagnostic — never automatically rewritten or
deleted. Availability probing reuses the deterministic read-only Phase 37J Git
adapter (`git rev-parse` / `git remote -v`) through a narrow boundary.

## Operator tooling (PowerShell)

`scripts/workspaces/Invoke-HiveMindWorkspace.ps1` wraps the authoritative Python
CLI (`apps/backend/app/console/repository_workspace_cli.py`) so the two front
ends never diverge. Commands: `path`, `init`, `list`, `show`, `add`,
`set-active`, `remove`, `validate`. Every command supports `-Json`. Exit codes:
`0` success, `2` operation/configuration error, `3` usage/invalid invocation
(including an invalid environment override). No administrator privileges are
required. See [the operator README](../scripts/workspaces/README.md).

## Repository Observer integration boundary

`resolve_active_repository_workspace(...)` is the narrow seam a future phase will
call to obtain the active repository root without re-entering it. It performs a
bounded, read-only resolution only. It does **not** run observation snapshots,
add an observer endpoint, change existing Repository Observer request contracts,
start polling, watch files, or launch subprocess observation merely because
configuration was loaded. The existing explicit request behavior is unchanged,
and the seam is inert until a later phase chooses to consume it.
