[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepositoryPath,
    [Parameter(Mandatory)][string]$ExpectedRemote,
    [Parameter(Mandatory)][string]$ExpectedBranch,
    [Parameter(Mandatory)][string]$ExpectedBaseline,
    [Parameter(Mandatory)][string]$CurrentPhase,
    [Parameter(Mandatory)][string]$AgentName,
    [Parameter(Mandatory)][string]$AgentRole,
    [Parameter(Mandatory)][string]$CapabilityLevel,
    [Parameter(Mandatory)][string]$CompositionMode,
    [Parameter(Mandatory)][string]$WriteAuthority,
    [string]$Phase36KStatus='paused-and-untouched',
    [string]$ManifestPath,
    [switch]$RequireCleanWorkingTree,
    [string]$CanonicalRepositoryPath='C:\Users\britb\Documents\hive-mind',
    [switch]$DisableCanonicalPathEnforcement,
    [switch]$Json
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'HiveMindGovernance.psm1') -Force
try {
    $arguments=@{}; foreach($key in $PSBoundParameters.Keys){ if($key -ne 'Json'){$arguments[$key]=$PSBoundParameters[$key]} }
    $result=Invoke-HiveMindGovernancePreflight @arguments
    if($Json){ $result | ConvertTo-Json -Depth 10 -Compress }
    else {
        foreach($check in $result.Checks){ '[{0}] {1} ({2}): {3}' -f $check.Status,$check.CheckIdentifier,$check.Category,$check.Message }
        "Overall: $($result.OverallResult) | Blocking: $($result.BlockingFailureCount) | Warnings: $($result.WarningCount)"
    }
    if($result.InvocationError){exit 3}; if($result.BlockingFailureCount -gt 0){exit 2}; exit 0
} catch {
    if($Json){ [pscustomobject]@{OverallResult='BLOCKED';BlockingFailureCount=1;WarningCount=0;InvocationError=$true;Error=$_.Exception.Message} | ConvertTo-Json -Compress }
    else { "[BLOCKED] invocation.error (Invocation): $($_.Exception.Message)" }
    exit 3
}
