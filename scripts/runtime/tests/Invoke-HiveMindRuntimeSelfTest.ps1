Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Phase 39C - deterministic self-test for the managed local runtime engine.
#
# Every case is fully isolated: process creation, process inspection, HTTP
# probing, TCP port probing, the clock, and sleeping are all replaced with
# in-memory fakes, and runtime metadata is written under a throwaway temp
# directory (including one path that contains spaces). No real backend, frontend,
# socket, or operator configuration is ever touched, and no process is left
# running after the suite completes.

$runtimeRoot = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $runtimeRoot 'HiveMindRuntime.psm1') -Force

$results = [System.Collections.Generic.List[object]]::new()
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hive-mind runtime tests " + [guid]::NewGuid().ToString('N'))

function Add-Test {
    param([string]$Name, [scriptblock]$Body)
    try { & $Body; $results.Add([pscustomobject]@{ Name = $Name; Status = 'PASS'; Detail = $null }) }
    catch { $results.Add([pscustomobject]@{ Name = $Name; Status = 'FAIL'; Detail = ($_.Exception.Message + "`n" + $_.ScriptStackTrace) }) }
}
function Assert-True { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw "Assertion failed: $Message" } }
function Assert-Equal { param($Expected, $Actual, [string]$Message) if ("$Expected" -ne "$Actual") { throw "Assertion failed: $Message (expected '$Expected', got '$Actual')" } }

# --------------------------------------------------------------------------- #
# Fake infrastructure
# --------------------------------------------------------------------------- #
function New-FakeRepo {
    param([string]$Root)
    New-Item -ItemType Directory -Path (Join-Path $Root 'apps/backend/app') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Root 'apps/frontend') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Root 'node_modules/vite/bin') -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $Root 'package.json') -Value '{ "name": "hivemind" }'
    Set-Content -LiteralPath (Join-Path $Root 'apps/backend/app/main.py') -Value '# entry'
    Set-Content -LiteralPath (Join-Path $Root 'apps/frontend/package.json') -Value '{ "name": "@hivemind/frontend" }'
    Set-Content -LiteralPath (Join-Path $Root 'node_modules/vite/bin/vite.js') -Value '// vite'
    $Root
}

function New-FakeState {
    @{
        Processes = @{}
        NextPid   = 2000
        Ports     = @{}
        Http      = @{}
        Now       = [datetime]::Parse('2026-07-20T00:00:00Z').ToUniversalTime()
        Sleeps    = 0
        Launches  = [System.Collections.Generic.List[int]]::new()
    }
}

function Add-FakeProcess {
    param([hashtable]$State, [string]$Name, [string]$CommandLine, [int]$ParentPid = 0)
    $procId = $State.NextPid; $State.NextPid++
    $State.Processes[$procId] = @{ Pid = $procId; Name = $Name; CreationTime = $State.Now.ToString('o'); CommandLine = $CommandLine; ParentPid = $ParentPid }
    $procId
}

function New-FakeContext {
    param([hashtable]$State, $Resolution, [string]$RuntimeHome, [hashtable]$Extra)
    $override = @{
        RuntimeHome             = $RuntimeHome
        BackendReadyTimeoutSec  = 3
        FrontendReadyTimeoutSec = 3
        PollIntervalSec         = 1
        ShutdownTimeoutSec      = 3
        HttpTimeoutSec          = 1
        ResolveWorkspace        = ({ param($Context) $Resolution }).GetNewClosure()
        GetProcessInfo          = ({ param($ProcessId)
                $id = [int]$ProcessId
                if ($State.Processes.ContainsKey($id)) {
                    $p = $State.Processes[$id]
                    return @{ Pid = $p.Pid; Name = $p.Name; CreationTime = $p.CreationTime; CommandLine = $p.CommandLine }
                }
                return $null
            }).GetNewClosure()
        GetChildProcessIds      = ({ param($ProcessId)
                $id = [int]$ProcessId
                @($State.Processes.Values | Where-Object { $_.ParentPid -eq $id } | ForEach-Object { [int]$_.Pid })
            }).GetNewClosure()
        StartManagedProcess     = ({ param($Spec)
                $procId = $State.NextPid; $State.NextPid++
                $leaf = Split-Path -Leaf $Spec.FilePath
                $name = if ($leaf -like '*.*') { $leaf } else { "$leaf.exe" }
                $cmd = ($Spec.FilePath + ' ' + (@($Spec.Arguments) -join ' '))
                $State.Processes[$procId] = @{ Pid = $procId; Name = $name; CreationTime = $State.Now.ToString('o'); CommandLine = $cmd; ParentPid = 0 }
                $State.Launches.Add($procId)
                if ($cmd -like '*--port 8787*') { $State.Ports[8787] = $procId }
                if ($cmd -like '*--port 5173*') { $State.Ports[5173] = $procId }
                @{ Pid = $procId }
            }).GetNewClosure()
        StopProcessId           = ({ param($ProcessId, $Force)
                $id = [int]$ProcessId
                if ($State.Processes.ContainsKey($id)) { $State.Processes.Remove($id) }
                foreach ($port in @($State.Ports.Keys)) { if ($State.Ports[$port] -eq $id) { $State.Ports.Remove($port) } }
            }).GetNewClosure()
        TestPortListener        = ({ param($Port)
                $p = [int]$Port
                if ($State.Ports.ContainsKey($p)) { return [int]$State.Ports[$p] }
                return $null
            }).GetNewClosure()
        InvokeHttpProbe         = ({ param($Url, $TimeoutSec)
                if ($State.Http.ContainsKey($Url)) { return $State.Http[$Url] }
                return @{ Ok = $false; StatusCode = 0; Body = $null; Error = 'connection refused' }
            }).GetNewClosure()
        NowUtc                  = ({ $State.Now }).GetNewClosure()
        Sleep                   = ({ param($Seconds) $State.Sleeps++; $State.Now = $State.Now.AddSeconds([double]$Seconds) }).GetNewClosure()
    }
    if ($Extra) { foreach ($k in $Extra.Keys) { $override[$k] = $Extra[$k] } }
    New-HiveMindRuntimeContext -Override $override
}

function New-ResolvedWorkspace {
    param([string]$Repo, [string]$Id = 'test-ws')
    @{ Status = 'resolved'; Error = $null; Message = $null; ConfigPath = 'x'; WorkspaceId = $Id; RepositoryRoot = $Repo; Resolved = $true; Diagnostics = @() }
}

function Set-HealthyServices {
    param([hashtable]$State, [hashtable]$Context)
    $State.Http[(Get-BackendHealthUrl $Context)] = @{ Ok = $true; StatusCode = 200; Body = '{"ok":true,"service":"hivemind-backend","version":"0.1.0"}'; Error = $null }
    $State.Http[(Get-FrontendUrl $Context)] = @{ Ok = $true; StatusCode = 200; Body = '<!doctype html><html></html>'; Error = $null }
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $repo = New-FakeRepo (Join-Path $tempRoot 'repo with spaces')

    # 1 - command dispatch + validation
    Add-Test '1 dispatch rejects an unknown command' {
        $threw = $false
        try { Invoke-HiveMindRuntime -Command 'bogus' } catch { $threw = $true }
        Assert-True $threw 'unknown command should be rejected by ValidateSet'
    }

    # 2 - workspace resolution feeds preflight
    Add-Test '2 preflight passes for a resolved Hive|Mind workspace' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt2'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        $pre = Invoke-RuntimePreflight -Context $ctx
        Assert-True $pre.Ok 'preflight should pass'
        Assert-Equal 'test-ws' $pre.WorkspaceId 'workspace id'
    }

    # 3 - path validation variants
    Add-Test '3 repository layout validation distinguishes failure cases' {
        Assert-Equal 'ok' (Test-HiveMindRepositoryLayout -RepositoryRoot $repo).Code 'good repo'
        Assert-Equal 'workspace_root_missing' (Test-HiveMindRepositoryLayout -RepositoryRoot $null).Code 'null root'
        Assert-Equal 'repository_root_absent' (Test-HiveMindRepositoryLayout -RepositoryRoot (Join-Path $tempRoot 'nope')).Code 'absent root'
        $notHive = New-Item -ItemType Directory -Path (Join-Path $tempRoot 'nothive') -Force
        Set-Content -LiteralPath (Join-Path $notHive.FullName 'package.json') -Value '{ "name": "something-else" }'
        Assert-Equal 'not_hivemind_repository' (Test-HiveMindRepositoryLayout -RepositoryRoot $notHive.FullName).Code 'wrong repo'
        $noBackend = New-FakeRepo (Join-Path $tempRoot 'nobackend')
        Remove-Item -LiteralPath (Join-Path $noBackend 'apps/backend/app/main.py') -Force
        Assert-Equal 'backend_files_missing' (Test-HiveMindRepositoryLayout -RepositoryRoot $noBackend).Code 'missing backend'
        $noFrontend = New-FakeRepo (Join-Path $tempRoot 'nofrontend')
        Remove-Item -LiteralPath (Join-Path $noFrontend 'apps/frontend/package.json') -Force
        Assert-Equal 'frontend_files_missing' (Test-HiveMindRepositoryLayout -RepositoryRoot $noFrontend).Code 'missing frontend'
    }

    # 4 - metadata serialize / validate round-trip and corruption handling
    Add-Test '4 runtime metadata round-trips and rejects corruption' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt4'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        $bpid = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python -m uvicorn app.main:app --port 8787'
        $fpid = Add-FakeProcess -State $state -Name 'node.exe' -CommandLine 'node vite --port 5173'
        $backend = New-RuntimeServiceRecord -Context $ctx -ProcessId $bpid -Signature 'app.main:app' -Url 'http://127.0.0.1:8787'
        $frontend = New-RuntimeServiceRecord -Context $ctx -ProcessId $fpid -Signature 'vite' -Url 'http://127.0.0.1:5173'
        $meta = ConvertTo-RuntimeMetadata -Context $ctx -WorkspaceId 'test-ws' -RepositoryRoot $repo -Backend $backend -Frontend $frontend -RuntimeState 'running' -StartedAt '2026-07-20T00:00:00Z'
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $meta
        $read = Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath
        Assert-True $read.Valid 'metadata should read back as valid'
        Assert-Equal 'test-ws' $read.Data.workspace_id 'workspace id round-trip'

        Set-Content -LiteralPath $paths.MetadataPath -Value '{ not valid json'
        Assert-True (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Malformed 'invalid json is malformed'

        Set-Content -LiteralPath $paths.MetadataPath -Value '{ "schema_version": "wrong.vX", "workspace_id": "x", "repository_path": "y", "backend": {"pid":1}, "frontend": {"pid":2} }'
        Assert-True (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Malformed 'wrong schema is malformed'

        Set-Content -LiteralPath $paths.MetadataPath -Value ('{ "schema_version": "hivemind-runtime.v1", "workspace_id": "x", "repository_path": "y", "frontend": {"pid":2} }')
        Assert-True (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Malformed 'missing backend field is malformed'

        Set-Content -LiteralPath $paths.MetadataPath -Value ('x' * 70000)  # exceeds the 64 KiB metadata cap
        Assert-True (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Malformed 'oversized metadata is malformed'
    }

    # 5 - process identity matching (pid reuse, signature, absence)
    Add-Test '5 managed process identity matching is strict' {
        $state = New-FakeState
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome (Join-Path $tempRoot 'rt5')
        $pid1 = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python -m uvicorn app.main:app --port 8787'
        $good = @{ pid = $pid1; name = 'python.exe'; creation_time = $state.Processes[$pid1].CreationTime; identity_signature = 'app.main:app' }
        Assert-True (Test-ManagedProcessIdentity -Context $ctx -Record $good) 'exact match should be ours'
        $badCreation = @{ pid = $pid1; name = 'python.exe'; creation_time = '1999-01-01T00:00:00.0000000Z'; identity_signature = 'app.main:app' }
        Assert-True (-not (Test-ManagedProcessIdentity -Context $ctx -Record $badCreation)) 'pid reuse (different creation time) is not ours'
        $badSignature = @{ pid = $pid1; name = 'python.exe'; creation_time = $state.Processes[$pid1].CreationTime; identity_signature = 'totally-different' }
        Assert-True (-not (Test-ManagedProcessIdentity -Context $ctx -Record $badSignature)) 'signature mismatch is not ours'
        $absent = @{ pid = 999999; name = 'python.exe'; creation_time = $state.Now.ToString('o'); identity_signature = 'app.main:app' }
        Assert-True (-not (Test-ManagedProcessIdentity -Context $ctx -Record $absent)) 'absent pid is not ours'
    }

    # 6 - happy-path start / status / stop integration + safe cleanup
    Add-Test '6 start then status healthy then stop, leaving unrelated processes alone' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt6'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        $bystander = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python some-unrelated-script.py'

        $start = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 0 $start.ExitCode 'start should succeed'
        Assert-Equal 'ok' $start.Payload.status 'start status ok'
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        Assert-True (Test-Path -LiteralPath $paths.MetadataPath) 'metadata written'
        Assert-True (Test-Path -LiteralPath $paths.LogDir) 'log dir created'
        Assert-Equal 'running' (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Data.runtime_state 'state running'

        $status = Invoke-RuntimeStatus -Context $ctx
        Assert-Equal 'healthy' $status.Payload.overall 'status should be healthy'

        $stop = Invoke-RuntimeStop -Context $ctx
        Assert-Equal 0 $stop.ExitCode 'stop should succeed'
        Assert-True (-not (Test-Path -LiteralPath $paths.MetadataPath)) 'metadata cleared after stop'
        Assert-True ($state.Processes.ContainsKey($bystander)) 'unrelated process must NOT be terminated'
        Assert-True ($state.Ports.Count -eq 0) 'managed ports released after stop'

        $status2 = Invoke-RuntimeStatus -Context $ctx
        Assert-Equal 'stopped' $status2.Payload.overall 'status should be stopped after stop'
    }

    # 7 - already-running: a second start is a safe no-op, no duplicate launch
    Add-Test '7 start is a safe no-op when already healthy' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt7'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        Invoke-RuntimeStart -Context $ctx | Out-Null
        $launchesAfterFirst = $state.Launches.Count
        $second = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 0 $second.ExitCode 'second start exit 0'
        Assert-Equal 'already-running' $second.Payload.status 'second start already-running'
        Assert-Equal $launchesAfterFirst $state.Launches.Count 'no duplicate processes launched'
        Invoke-RuntimeStop -Context $ctx | Out-Null
    }

    # 8 - already-stopped
    Add-Test '8 stop is safe when nothing is running' {
        $state = New-FakeState
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome (Join-Path $tempRoot 'rt8')
        $stop = Invoke-RuntimeStop -Context $ctx
        Assert-Equal 0 $stop.ExitCode 'stop exit 0'
        Assert-Equal 'already-stopped' $stop.Payload.status 'already-stopped'
    }

    # 9 - port conflict is detected before any launch
    Add-Test '9 start refuses to launch when a port is occupied by an unrelated process' {
        $state = New-FakeState
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome (Join-Path $tempRoot 'rt9')
        Set-HealthyServices -State $state -Context $ctx
        $state.Ports[8787] = 4242  # unrelated listener
        $start = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 2 $start.ExitCode 'port conflict exit 2'
        Assert-Equal 'PortConflict' $start.Payload.error 'port conflict error'
        Assert-Equal 0 $state.Launches.Count 'nothing should have been launched'
    }

    # 10 - partial runtime classification and refusal to start over it
    Add-Test '10 partial runtime is detected and start refuses' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt10'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        Invoke-RuntimeStart -Context $ctx | Out-Null
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        $meta = (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Data
        # Kill only the frontend behind the runtime's back -> partial.
        $ctx.StopProcessId.Invoke([int]$meta.frontend.pid, $true)
        $status = Invoke-RuntimeStatus -Context $ctx
        Assert-Equal 'partial' $status.Payload.overall 'partial detected'
        $start = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 2 $start.ExitCode 'start over partial exit 2'
        Assert-Equal 'AlreadyPresent' $start.Payload.error 'start refuses partial'
        Invoke-RuntimeStop -Context $ctx | Out-Null
    }

    # 11 - readiness timeout (bounded, deterministic via advancing clock)
    Add-Test '11 readiness wait times out without hanging' {
        $state = New-FakeState
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome (Join-Path $tempRoot 'rt11')
        $svcPid = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python -m uvicorn app.main:app --port 8787'
        # No Http entry -> never ready. Clock advances via Sleep.
        $wait = Wait-ServiceReady -Context $ctx -ProcessId $svcPid -Url 'http://127.0.0.1:8787/health' -Validator ${function:Test-BackendReadyProbe} -TimeoutSec 3 -ServiceName 'backend'
        Assert-True (-not $wait.Ready) 'should not become ready'
        Assert-Equal 'timeout' $wait.Reason 'timeout reason'
        Assert-True ($state.Sleeps -ge 1 -and $state.Sleeps -le 5) 'bounded number of polls'
    }

    # 12 - readiness detects an immediately-exited process
    Add-Test '12 readiness wait fails fast when the process exits' {
        $state = New-FakeState
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome (Join-Path $tempRoot 'rt12')
        $wait = Wait-ServiceReady -Context $ctx -ProcessId 918273 -Url 'http://127.0.0.1:8787/health' -Validator ${function:Test-BackendReadyProbe} -TimeoutSec 3 -ServiceName 'backend'
        Assert-True (-not $wait.Ready) 'not ready'
        Assert-Equal 'process-exited' $wait.Reason 'process-exited reason'
    }

    # 13 - rollback when one service never becomes ready
    Add-Test '13 start rolls back when the frontend never becomes reachable' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt13'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        # Backend healthy, frontend never reachable.
        $state.Http[(Get-BackendHealthUrl $ctx)] = @{ Ok = $true; StatusCode = 200; Body = '{"ok":true,"service":"hivemind-backend"}'; Error = $null }
        $start = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 2 $start.ExitCode 'start should fail'
        Assert-Equal 'FrontendNotReady' $start.Payload.error 'frontend not ready error'
        Assert-True $start.Payload.rolled_back 'should report rolled back'
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        Assert-True (-not (Test-Path -LiteralPath $paths.MetadataPath)) 'metadata removed on rollback'
        Assert-Equal 0 $state.Processes.Count 'all launched processes stopped on rollback'
    }

    # 14 - stale metadata detection + recovery on next start
    Add-Test '14 stale metadata is detected by status and cleaned by start' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt14'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        # Write metadata referencing pids that do not exist -> stale.
        $bpid = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python -m uvicorn app.main:app --port 8787'
        $fpid = Add-FakeProcess -State $state -Name 'node.exe' -CommandLine 'node vite --port 5173'
        $backend = New-RuntimeServiceRecord -Context $ctx -ProcessId $bpid -Signature 'app.main:app' -Url 'http://127.0.0.1:8787'
        $frontend = New-RuntimeServiceRecord -Context $ctx -ProcessId $fpid -Signature 'vite' -Url 'http://127.0.0.1:5173'
        $meta = ConvertTo-RuntimeMetadata -Context $ctx -WorkspaceId 'test-ws' -RepositoryRoot $repo -Backend $backend -Frontend $frontend -RuntimeState 'running' -StartedAt '2026-07-20T00:00:00Z'
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $meta
        # Now simulate a reboot: both processes are gone.
        $state.Processes.Remove($bpid); $state.Processes.Remove($fpid); $state.Ports.Clear()
        Assert-Equal 'stale' (Invoke-RuntimeStatus -Context $ctx).Payload.overall 'stale detected'
        Set-HealthyServices -State $state -Context $ctx
        $start = Invoke-RuntimeStart -Context $ctx
        Assert-Equal 0 $start.ExitCode 'start recovers from stale metadata'
        Assert-Equal 'ok' $start.Payload.status 'start ok after cleaning stale'
        Invoke-RuntimeStop -Context $ctx | Out-Null
    }

    # 15 - malformed metadata: stop removes it without terminating anything
    Add-Test '15 stop on malformed metadata is safe and does not kill processes' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt15'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        $bystander = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python unrelated.py'
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        New-Item -ItemType Directory -Path $paths.WorkspaceDir -Force | Out-Null
        Set-Content -LiteralPath $paths.MetadataPath -Value '{ corrupt'
        # Status must classify malformed metadata as stale BEFORE stop cleans it up.
        Assert-Equal 'stale' (Invoke-RuntimeStatus -Context $ctx).Payload.overall 'malformed reads as stale for status'
        $stop = Invoke-RuntimeStop -Context $ctx
        Assert-Equal 0 $stop.ExitCode 'malformed stop exit 0'
        Assert-Equal 'stale-cleaned' $stop.Payload.status 'stale-cleaned status'
        Assert-True (-not (Test-Path -LiteralPath $paths.MetadataPath)) 'malformed metadata removed'
        Assert-True ($state.Processes.ContainsKey($bystander)) 'no process terminated on malformed stop'
    }

    # 16 - degraded and starting classifications
    Add-Test '16 status distinguishes degraded and starting from healthy' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt16'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        $bpid = Add-FakeProcess -State $state -Name 'python.exe' -CommandLine 'python -m uvicorn app.main:app --port 8787'
        $fpid = Add-FakeProcess -State $state -Name 'node.exe' -CommandLine 'node vite --port 5173'
        $backend = New-RuntimeServiceRecord -Context $ctx -ProcessId $bpid -Signature 'app.main:app' -Url (Get-BackendUrl $ctx)
        $frontend = New-RuntimeServiceRecord -Context $ctx -ProcessId $fpid -Signature 'vite' -Url (Get-FrontendUrl $ctx)
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        # Frontend reachable, backend unhealthy, state running -> degraded.
        $state.Http[(Get-FrontendUrl $ctx)] = @{ Ok = $true; StatusCode = 200; Body = 'x'; Error = $null }
        $metaRunning = ConvertTo-RuntimeMetadata -Context $ctx -WorkspaceId 'test-ws' -RepositoryRoot $repo -Backend $backend -Frontend $frontend -RuntimeState 'running' -StartedAt 'x'
        Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $metaRunning
        Assert-Equal 'degraded' (Get-HiveMindRuntimeStatus -Context $ctx -MetadataPath $paths.MetadataPath -Probe).Overall 'degraded'
        # Same probes but state starting -> starting.
        $metaStarting = ConvertTo-RuntimeMetadata -Context $ctx -WorkspaceId 'test-ws' -RepositoryRoot $repo -Backend $backend -Frontend $frontend -RuntimeState 'starting' -StartedAt 'x'
        Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $metaStarting
        Assert-Equal 'starting' (Get-HiveMindRuntimeStatus -Context $ctx -MetadataPath $paths.MetadataPath -Probe).Overall 'starting'
    }

    # 17 - restart composes stop + start
    Add-Test '17 restart composes a clean stop and start' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt17'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        Invoke-RuntimeStart -Context $ctx | Out-Null
        $restart = Invoke-RuntimeRestart -Context $ctx
        Assert-Equal 0 $restart.ExitCode 'restart exit 0'
        Assert-Equal 'ok' $restart.Payload.status 'restart status ok'
        Invoke-RuntimeStop -Context $ctx | Out-Null
    }

    # 18 - verify is read-only and reports port ownership by the managed runtime
    Add-Test '18 verify passes and recognizes managed ports without mutating state' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt18'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        Invoke-RuntimeStart -Context $ctx | Out-Null
        $launchCount = $state.Launches.Count
        $verify = Invoke-RuntimeVerify -Context $ctx
        Assert-Equal 0 $verify.ExitCode 'verify exit 0 when healthy'
        Assert-True $verify.Payload.ok 'verify ok'
        Assert-Equal $launchCount $state.Launches.Count 'verify must not launch anything'
        Invoke-RuntimeStop -Context $ctx | Out-Null
    }

    # 19 - process-tree termination reaches descendants
    Add-Test '19 stop terminates child processes of the managed root' {
        $state = New-FakeState
        $rtHome = Join-Path $tempRoot 'rt19'
        $ctx = New-FakeContext -State $state -Resolution (New-ResolvedWorkspace $repo) -RuntimeHome $rtHome
        Set-HealthyServices -State $state -Context $ctx
        Invoke-RuntimeStart -Context $ctx | Out-Null
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $rtHome -WorkspaceId 'test-ws'
        $meta = (Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath).Data
        $childPid = Add-FakeProcess -State $state -Name 'node.exe' -CommandLine 'node child-worker' -ParentPid ([int]$meta.frontend.pid)
        Assert-True ($state.Processes.ContainsKey($childPid)) 'child exists before stop'
        Invoke-RuntimeStop -Context $ctx | Out-Null
        Assert-True (-not $state.Processes.ContainsKey($childPid)) 'child terminated with the managed tree'
    }

    # 20 - no-config resolution keeps status/stop safe
    Add-Test '20 no configured workspace yields stopped status and safe stop' {
        $state = New-FakeState
        $noConfig = @{ Status = 'no-config'; Error = 'WorkspaceConfigNotFoundError'; Message = 'none'; ConfigPath = $null; WorkspaceId = $null; RepositoryRoot = $null; Resolved = $false; Diagnostics = @() }
        $ctx = New-FakeContext -State $state -Resolution $noConfig -RuntimeHome (Join-Path $tempRoot 'rt20')
        Assert-Equal 'stopped' (Invoke-RuntimeStatus -Context $ctx).Payload.overall 'stopped when unconfigured'
        Assert-Equal 0 (Invoke-RuntimeStop -Context $ctx).ExitCode 'stop safe when unconfigured'
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
