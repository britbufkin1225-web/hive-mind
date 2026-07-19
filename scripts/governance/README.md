# Hive|Mind PowerShell Governance

Phase 38B translates the Phase 38A contribution contract into a deterministic,
local, read-only preflight. It diagnoses repository, Git, session, and optional
composition-manifest state; it never fetches, switches, cleans, stashes, resets,
merges, rebases, pulls, pushes, amends, or changes Git configuration.

## Run the preflight

```powershell
$baseline = git rev-parse origin/main

& .\scripts\governance\Invoke-HiveMindGovernancePreflight.ps1 `
  -RepositoryPath 'C:\Users\britb\Documents\hive-mind' `
  -ExpectedRemote 'https://github.com/britbufkin1225-web/hive-mind.git' `
  -ExpectedBranch 'phase-38b-powershell-governance-enforcement' `
  -ExpectedBaseline $baseline `
  -CurrentPhase 'Phase 38B — PowerShell Governance Enforcement' `
  -AgentName 'codex' `
  -AgentRole 'primary-implementer' `
  -CapabilityLevel 'L3' `
  -CompositionMode 'sequential-isolated' `
  -WriteAuthority 'bounded-path-write' `
  -Phase36KStatus 'paused-and-untouched' `
  -RequireCleanWorkingTree
```

The required inputs are repository path, expected remote, branch, full baseline
commit, current phase, agent name, assigned role, capability, composition mode,
and write-authority enum. `Phase36KStatus` defaults to the locked value. Canonical
path enforcement is enabled by default; `CanonicalRepositoryPath` is visible and
overrideable. `DisableCanonicalPathEnforcement` exists for disposable self-test
fixtures, not normal Hive|Mind sessions.

Add `-ManifestPath .\path\manifest.json` to validate a JSON serialization of the
existing `agent-composition.v1` structure. JSON is the dependency-free executable
serialization supported in Phase 38B; the field names and nesting remain those
defined by the Phase 38A composition manifest. Commands or paths in a manifest
are never executed. The manifest must be inside the repository.

Human output emits `[PASS]`, `[WARNING]`, and `[BLOCKED]` lines. Add `-Json` for
one pure JSON value on stdout:

```powershell
$result = & .\scripts\governance\Invoke-HiveMindGovernancePreflight.ps1 <arguments> -Json
$result | ConvertFrom-Json | Out-Null
```

Exit codes are deterministic: `0` means required checks passed, `2` means one or
more governance checks blocked, and `3` means invalid invocation or malformed
input. Wrong identity, remote, branch, baseline, ancestry, manifest, enum, Phase
36K lock, or a required clean-tree violation blocks. Zero commits ahead and
caller-managed fetch freshness are warnings.

## Self-test

```powershell
& .\scripts\governance\tests\Invoke-HiveMindGovernanceSelfTest.ps1
```

The dependency-free suite creates fixture-local Git repositories under the
system temporary directory, configures identity only in each fixture, and
removes fixtures in `finally`. It does not mutate Hive|Mind history.

## Limitations and deferred work

This layer validates declared state; it does not prove branch ownership across
independent live sessions, enforce changed-path ownership after edits, install
hooks, run in hosted CI, support YAML parsing, orchestrate agents, or authorize
human-only composition and merge decisions. Those concerns remain manual or
deferred. Windows PowerShell and PowerShell 7 workflows are the supported target.
