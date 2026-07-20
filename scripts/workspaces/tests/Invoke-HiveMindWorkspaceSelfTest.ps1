Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Phase 39B - self-test for the repository workspace operator tooling. Every case
# is fully isolated by pointing -ConfigPath at a throwaway temp file, so the test
# never reads or writes the operator's real configuration under LOCALAPPDATA.

$workspacesRoot = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $workspacesRoot 'HiveMindWorkspaces.psm1') -Force

$results = [System.Collections.Generic.List[object]]::new()
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hive-mind-workspace-tests-" + [guid]::NewGuid().ToString('N'))
$PythonExecutable = if ($env:HIVEMIND_SELFTEST_PYTHON) { $env:HIVEMIND_SELFTEST_PYTHON } else { 'python' }

function New-ConfigPath { param([string]$Name) Join-Path $tempRoot ($Name + '.json') }
function New-RepoRoot {
    param([string]$Name)
    $path = Join-Path $tempRoot $Name
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    $path
}
function Invoke-Workspace {
    param([hashtable]$Arguments)
    Invoke-HiveMindWorkspace @Arguments -PythonExecutable $PythonExecutable
}
function Get-Json { param($Result) ($Result.Output | Where-Object { $_ }) -join "`n" | ConvertFrom-Json }
function Add-Test {
    param([string]$Name, [scriptblock]$Body)
    try { & $Body; $results.Add([pscustomobject]@{ Name = $Name; Status = 'PASS'; Detail = $null }) }
    catch { $results.Add([pscustomobject]@{ Name = $Name; Status = 'FAIL'; Detail = ($_.Exception.Message + "`n" + $_.ScriptStackTrace) }) }
}
function Assert-True { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

    Add-Test '1 init succeeds with exit 0' {
        $cfg = New-ConfigPath 'init'
        $r = Invoke-Workspace @{ Command = 'init'; ConfigPath = $cfg; Json = $true }
        Assert-True ($r.ExitCode -eq 0) "init exit code was $($r.ExitCode)"
        $json = Get-Json $r
        Assert-True ($json.status -eq 'ok') 'init did not report ok'
        Assert-True (Test-Path -LiteralPath $cfg) 'init did not create the config file'
    }

    Add-Test '2 add then list shows the workspace' {
        $cfg = New-ConfigPath 'addlist'
        Invoke-Workspace @{ Command = 'init'; ConfigPath = $cfg } | Out-Null
        $repo = New-RepoRoot 'addlist-repo'
        $add = Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'alpha'; Name = 'Alpha'; RepositoryRoot = $repo; Activate = $true; Json = $true }
        Assert-True ($add.ExitCode -eq 0) "add exit code was $($add.ExitCode)"
        $list = Invoke-Workspace @{ Command = 'list'; ConfigPath = $cfg; Json = $true }
        $json = Get-Json $list
        Assert-True ($json.active_workspace_id -eq 'alpha') 'active workspace not recorded'
        Assert-True (@($json.workspaces).Count -eq 1) 'workspace count not 1'
    }

    Add-Test '3 show returns the registered workspace' {
        $cfg = New-ConfigPath 'show'
        $repo = New-RepoRoot 'show-repo'
        Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'beta'; Name = 'Beta'; RepositoryRoot = $repo } | Out-Null
        $r = Invoke-Workspace @{ Command = 'show'; ConfigPath = $cfg; Id = 'beta'; Json = $true }
        Assert-True ($r.ExitCode -eq 0) "show exit code was $($r.ExitCode)"
        $json = Get-Json $r
        Assert-True ($json.workspace.workspace_id -eq 'beta') 'show returned wrong workspace'
    }

    Add-Test '4 set-active selects the active workspace' {
        $cfg = New-ConfigPath 'active'
        $repo = New-RepoRoot 'active-repo'
        Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'gamma'; Name = 'Gamma'; RepositoryRoot = $repo } | Out-Null
        $r = Invoke-Workspace @{ Command = 'set-active'; ConfigPath = $cfg; Id = 'gamma' }
        Assert-True ($r.ExitCode -eq 0) "set-active exit code was $($r.ExitCode)"
        $validate = Invoke-Workspace @{ Command = 'validate'; ConfigPath = $cfg; Json = $true }
        $json = Get-Json $validate
        Assert-True ($json.active_workspace_id -eq 'gamma') 'active workspace not selected'
    }

    Add-Test '5 validate succeeds on a valid configuration' {
        $cfg = New-ConfigPath 'validate'
        $repo = New-RepoRoot 'validate-repo'
        Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'delta'; Name = 'Delta'; RepositoryRoot = $repo; Activate = $true } | Out-Null
        $r = Invoke-Workspace @{ Command = 'validate'; ConfigPath = $cfg; Json = $true }
        Assert-True ($r.ExitCode -eq 0) "validate exit code was $($r.ExitCode)"
        $json = Get-Json $r
        Assert-True ($json.status -eq 'ok') 'validate did not report ok'
    }

    Add-Test '6 duplicate add fails with exit 2' {
        $cfg = New-ConfigPath 'dup'
        $repo = New-RepoRoot 'dup-repo'
        Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'epsilon'; Name = 'E'; RepositoryRoot = $repo } | Out-Null
        $r = Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'epsilon'; Name = 'E2'; RepositoryRoot = (New-RepoRoot 'dup-repo-2'); Json = $true }
        Assert-True ($r.ExitCode -eq 2) "duplicate add exit code was $($r.ExitCode)"
        $json = Get-Json $r
        Assert-True ($json.error -eq 'DuplicateWorkspaceError') 'duplicate error not reported'
    }

    Add-Test '7 malformed configuration fails validate with exit 2' {
        $cfg = New-ConfigPath 'malformed'
        Set-Content -LiteralPath $cfg -Value '{ this is not valid json' -NoNewline
        $r = Invoke-Workspace @{ Command = 'validate'; ConfigPath = $cfg; Json = $true }
        Assert-True ($r.ExitCode -eq 2) "malformed validate exit code was $($r.ExitCode)"
    }

    Add-Test '8 JSON output parses for path' {
        $cfg = New-ConfigPath 'jsonpath'
        $r = Invoke-Workspace @{ Command = 'path'; ConfigPath = $cfg; Json = $true }
        $json = Get-Json $r
        Assert-True ($json.status -eq 'ok') 'path JSON did not parse to ok'
        Assert-True ($json.exists -eq $false) 'path reported an unexpected existing file'
    }

    Add-Test '9 credential-bearing remote is rejected with exit 2' {
        $cfg = New-ConfigPath 'creds'
        $repo = New-RepoRoot 'creds-repo'
        $r = Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'zeta'; Name = 'Z'; RepositoryRoot = $repo; ExpectedRemote = 'https://user:token@github.com/x/y.git'; Json = $true }
        Assert-True ($r.ExitCode -eq 2) "credential remote exit code was $($r.ExitCode)"
        $json = Get-Json $r
        Assert-True ($json.error -eq 'CredentialBearingRemoteError') 'credential rejection not reported'
    }

    Add-Test '10 remove active workspace clears the active selection' {
        $cfg = New-ConfigPath 'remove'
        $repo = New-RepoRoot 'remove-repo'
        Invoke-Workspace @{ Command = 'add'; ConfigPath = $cfg; Id = 'eta'; Name = 'Eta'; RepositoryRoot = $repo; Activate = $true } | Out-Null
        $r = Invoke-Workspace @{ Command = 'remove'; ConfigPath = $cfg; Id = 'eta' }
        Assert-True ($r.ExitCode -eq 0) "remove exit code was $($r.ExitCode)"
        $list = Invoke-Workspace @{ Command = 'list'; ConfigPath = $cfg; Json = $true }
        $json = Get-Json $list
        Assert-True ($null -eq $json.active_workspace_id) 'active workspace not cleared after removal'
    }
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
}

$passed = @($results | Where-Object Status -eq 'PASS').Count
$failed = @($results | Where-Object Status -eq 'FAIL').Count
$results | Format-Table -AutoSize
"Self-test total: $($results.Count) | Passed: $passed | Failed: $failed"
if ($failed -gt 0) { $results | Where-Object Status -eq 'FAIL' | ForEach-Object { "FAILDETAIL $($_.Name): $($_.Detail)" } }
if ($failed -gt 0) { exit 1 }
exit 0
