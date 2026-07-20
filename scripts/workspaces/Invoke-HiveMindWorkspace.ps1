[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
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

# Phase 39B - operator entry point. Forwards to the authoritative Python CLI and
# preserves its exit code (0 success, 2 operation/configuration error, 3
# usage/invalid invocation) so scripts and humans get consistent signals.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'HiveMindWorkspaces.psm1') -Force

try {
    $result = Invoke-HiveMindWorkspace @PSBoundParameters
    foreach ($line in $result.Output) { $line }
    exit $result.ExitCode
} catch {
    if ($Json) {
        [pscustomobject]@{ command = $Command; status = 'error'; error = 'InvocationError'; message = $_.Exception.Message } | ConvertTo-Json -Compress
    } else {
        "[error] $Command (invocation): $($_.Exception.Message)"
    }
    exit 3
}
