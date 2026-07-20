Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Phase 39B - operator-facing PowerShell surface for the persistent repository
# workspace registry. This module is intentionally thin: it locates and invokes
# the authoritative Python CLI
# (apps/backend/app/console/repository_workspace_cli.py) rather than
# re-implementing any validation, path-resolution, or persistence rules. The
# Python service remains the single source of truth; this module only marshals
# arguments and forwards the CLI's exit code.

function Get-HiveMindWorkspaceCliPath {
    param([string]$RepositoryRoot)
    if (-not $RepositoryRoot) {
        # This module lives at scripts/workspaces; the repository root is two
        # directory levels up.
        $RepositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    }
    Join-Path $RepositoryRoot 'apps/backend/app/console/repository_workspace_cli.py'
}

function Invoke-HiveMindWorkspace {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('path','init','list','show','add','set-active','remove','validate')]
        [string]$Command,
        [string]$Id,
        [string]$Name,
        [string]$RepositoryRoot,
        [string]$ExpectedRemote,
        [switch]$Activate,
        [switch]$Disabled,
        [switch]$Overwrite,
        [string]$ConfigPath,
        [string]$PythonExecutable = 'python',
        [string]$CliPath,
        [switch]$Json
    )

    if (-not $CliPath) { $CliPath = Get-HiveMindWorkspaceCliPath }
    if (-not (Test-Path -LiteralPath $CliPath)) {
        throw "Repository workspace CLI not found at $CliPath"
    }

    $arguments = [System.Collections.Generic.List[string]]::new()
    if ($Json) { $arguments.Add('--json') }
    if ($ConfigPath) { $arguments.Add('--config-path'); $arguments.Add($ConfigPath) }
    $arguments.Add($Command)

    switch ($Command) {
        'init' { if ($Overwrite) { $arguments.Add('--overwrite') } }
        'show' { $arguments.Add('--id'); $arguments.Add($Id) }
        'set-active' { $arguments.Add('--id'); $arguments.Add($Id) }
        'remove' { $arguments.Add('--id'); $arguments.Add($Id) }
        'add' {
            $arguments.AddRange([string[]]@(
                '--id', $Id, '--name', $Name, '--repository-root', $RepositoryRoot
            ))
            if ($ExpectedRemote) { $arguments.Add('--expected-remote'); $arguments.Add($ExpectedRemote) }
            if ($Disabled) { $arguments.Add('--disabled') }
            if ($Activate) { $arguments.Add('--activate') }
        }
    }

    $output = & $PythonExecutable $CliPath @arguments
    $exitCode = $LASTEXITCODE
    [pscustomobject]@{
        ExitCode = $exitCode
        Output   = @($output | ForEach-Object { "$_" })
        Command  = $Command
    }
}

Export-ModuleMember -Function Invoke-HiveMindWorkspace,Get-HiveMindWorkspaceCliPath
