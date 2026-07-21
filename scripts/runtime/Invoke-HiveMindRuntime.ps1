[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('start', 'status', 'stop', 'restart', 'verify')]
    [string]$Command,
    # Optional explicit workspace configuration path, forwarded to the Phase 39B
    # resolver (primarily for tests / CI isolation). Omit to use the operator's
    # persistent configuration.
    [string]$WorkspaceConfigPath,
    [switch]$Json
)

# Phase 39C - operator entry point for the managed Hive|Mind local runtime.
#
# This script is intentionally thin: all logic lives in HiveMindRuntime.psm1 so
# it can be exercised deterministically by the self-test suite. Exit codes mirror
# the Phase 39B tooling (0 success, 2 runtime/operation failure, 3 usage/invalid
# invocation) so scripts and humans get one consistent signal.
#
#   .\scripts\runtime\Invoke-HiveMindRuntime.ps1 start
#   .\scripts\runtime\Invoke-HiveMindRuntime.ps1 status
#   .\scripts\runtime\Invoke-HiveMindRuntime.ps1 stop
#   .\scripts\runtime\Invoke-HiveMindRuntime.ps1 restart
#   .\scripts\runtime\Invoke-HiveMindRuntime.ps1 verify

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'HiveMindRuntime.psm1') -Force

try {
    $params = @{ Command = $Command }
    if ($WorkspaceConfigPath) { $params['WorkspaceConfigPath'] = $WorkspaceConfigPath }
    $result = Invoke-HiveMindRuntime @params

    if ($Json) {
        $result.Payload | ConvertTo-Json -Depth 8
    } else {
        foreach ($line in $result.Lines) { $line }
    }
    exit $result.ExitCode
} catch {
    if ($Json) {
        [pscustomobject]@{ command = $Command; status = 'error'; error = 'InvocationError'; message = $_.Exception.Message } | ConvertTo-Json -Compress
    } else {
        "[error] $Command (invocation): $($_.Exception.Message)"
    }
    exit 3
}
