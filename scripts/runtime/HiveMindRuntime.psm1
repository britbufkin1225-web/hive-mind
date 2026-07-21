Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Phase 39C - managed local runtime engine for Hive|Mind.
#
# This module owns the logic behind the operator-facing runtime commands
# (start / status / stop / restart / verify). Design rationale:
#
# * Reuse, never duplicate, Phase 39B. The active repository workspace is
#   resolved exclusively through the authoritative repository-workspace CLI
#   (apps/backend/app/console/repository_workspace_cli.py). This module never
#   re-implements workspace path resolution, parsing, or persistence.
# * Own only two managed processes. A managed launch starts exactly the backend
#   (uvicorn) and the frontend (vite) and records a bounded, human-inspectable
#   metadata document plus identity fingerprints so shutdown can target *only*
#   those processes and never terminate anything by generic executable name.
# * Injectable seams for determinism. Every side effect - process creation and
#   inspection, HTTP probing, TCP port probing, the clock, and sleeping - is
#   reached through a "context" of script blocks. Self-tests replace the context
#   with in-memory fakes, so the full start/status/stop control flow is exercised
#   without launching a real process or opening a real socket.
# * Local-only and secret-free. Runtime metadata and logs live outside the Git
#   working tree under the operator's local application-data directory, keyed by
#   workspace id, and never contain credentials, tokens, or source content.
#
# Exit-code convention (matched to the Phase 39B tooling): 0 success,
# 2 operation/runtime failure, 3 usage/invalid invocation.

$script:RuntimeSchemaVersion = 'hivemind-runtime.v1'
$script:MaxRuntimeMetadataBytes = 65536

# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
function Get-RuntimeProp {
    # Safe property read that tolerates StrictMode and missing members, so JSON
    # documents (from ConvertFrom-Json) and fake objects can be inspected without
    # throwing on absent fields.
    param([AllowNull()]$Object, [Parameter(Mandatory)][string]$Name, [AllowNull()]$Default = $null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            $value = $Object[$Name]
            if ($null -eq $value) { return $Default }
            return $value
        }
        return $Default
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $Default }
    $value = $property.Value
    if ($null -eq $value) { return $Default }
    $value
}

function Format-RuntimeInstant {
    param([AllowNull()]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [datetime]) { return $Value.ToUniversalTime().ToString('o') }
    "$Value"
}

function ConvertTo-CanonicalInstant {
    # Normalize a timestamp to a single canonical UTC ISO-8601 form regardless of
    # whether it arrives as a string or as a [datetime]. ConvertFrom-Json silently
    # rehydrates ISO strings into [datetime] objects whose default string form
    # ("07/20/2026 00:00:00") differs from the round-trip 'o' form we write, which
    # would otherwise make an identity comparison spuriously fail after metadata is
    # read back from disk. Comparing canonical instants defeats that.
    param([AllowNull()]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [datetime]) {
        $dt = [datetime]$Value
        if ($dt.Kind -eq [System.DateTimeKind]::Unspecified) { $dt = [datetime]::SpecifyKind($dt, [System.DateTimeKind]::Utc) }
        return $dt.ToUniversalTime().ToString('o')
    }
    if ($Value -is [datetimeoffset]) { return ([datetimeoffset]$Value).UtcDateTime.ToString('o') }
    $text = "$Value"
    $parsed = [datetimeoffset]::MinValue
    if ([datetimeoffset]::TryParse($text, [cultureinfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal, [ref]$parsed)) {
        return $parsed.UtcDateTime.ToString('o')
    }
    $text
}

# --------------------------------------------------------------------------- #
# Default context (real side effects). Tests supply their own context.
# --------------------------------------------------------------------------- #
function Get-HiveMindRepositoryRootFromModule {
    # This module lives at scripts/runtime; the repository root is two levels up.
    Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

function Resolve-RuntimeHome {
    # Resolution order mirrors the Phase 39B config file: an explicit override
    # first (used by tests and CI for full isolation), then the OS-appropriate
    # per-user application-data directory, then a safe home fallback. Nothing is
    # ever written inside the repository working tree.
    param([hashtable]$Environment)
    $env = if ($Environment) { $Environment } else {
        $table = @{}
        foreach ($item in [System.Environment]::GetEnvironmentVariables().GetEnumerator()) { $table[$item.Key] = $item.Value }
        $table
    }
    $override = if ($env.ContainsKey('HIVEMIND_RUNTIME_HOME')) { $env['HIVEMIND_RUNTIME_HOME'] } else { $null }
    if ($override -and $override.Trim()) { return (Join-Path $override 'runtime') }
    if ([System.IO.Path]::DirectorySeparatorChar -eq '\') {
        $base = if ($env.ContainsKey('LOCALAPPDATA') -and $env['LOCALAPPDATA'] -and $env['LOCALAPPDATA'].Trim()) {
            $env['LOCALAPPDATA']
        } else {
            $userHome = if ($env.ContainsKey('USERPROFILE') -and $env['USERPROFILE']) { $env['USERPROFILE'] } else { [System.Environment]::GetFolderPath('UserProfile') }
            Join-Path (Join-Path $userHome 'AppData') 'Local'
        }
        return (Join-Path (Join-Path $base 'HiveMind') 'runtime')
    }
    $xdg = if ($env.ContainsKey('XDG_STATE_HOME') -and $env['XDG_STATE_HOME'] -and $env['XDG_STATE_HOME'].Trim()) { $env['XDG_STATE_HOME'] } else { $null }
    $base = if ($xdg) { $xdg } else {
        $userHome = if ($env.ContainsKey('HOME') -and $env['HOME']) { $env['HOME'] } else { [System.Environment]::GetFolderPath('UserProfile') }
        Join-Path $userHome '.local/state'
    }
    Join-Path (Join-Path $base 'hive-mind') 'runtime'
}

function Get-HiveMindRuntimePaths {
    # Compute the metadata and log paths for one workspace id under the runtime
    # home. The paths are deterministic and workspace-scoped so two distinct
    # workspaces never share runtime state.
    param([Parameter(Mandatory)][string]$RuntimeHome, [Parameter(Mandatory)][string]$WorkspaceId)
    $safeId = ($WorkspaceId -replace '[^A-Za-z0-9._-]', '_')
    if (-not $safeId) { $safeId = 'workspace' }
    $dir = Join-Path $RuntimeHome $safeId
    $logs = Join-Path $dir 'logs'
    [pscustomobject][ordered]@{
        WorkspaceDir  = $dir
        MetadataPath  = Join-Path $dir 'runtime.json'
        LogDir        = $logs
        BackendOutLog = Join-Path $logs 'backend.out.log'
        BackendErrLog = Join-Path $logs 'backend.err.log'
        FrontendOutLog = Join-Path $logs 'frontend.out.log'
        FrontendErrLog = Join-Path $logs 'frontend.err.log'
    }
}

function Resolve-HiveMindWorkspaceViaCli {
    # Default workspace resolver: shell out to the Phase 39B authoritative CLI and
    # normalize its JSON into the shape the runtime engine consumes. This is the
    # *only* place the runtime touches workspace configuration.
    param([hashtable]$Context)
    $python = $Context.PythonExecutable
    $cli = $Context.WorkspaceCliPath
    if (-not (Test-Path -LiteralPath $cli)) {
        return @{ Status = 'error'; Error = 'WorkspaceCliMissing'; Message = "repository workspace CLI not found at $cli"; ConfigPath = $null; WorkspaceId = $null; RepositoryRoot = $null; Resolved = $false; Diagnostics = @() }
    }
    $args = [System.Collections.Generic.List[string]]::new()
    $args.Add('--json')
    if ($Context.WorkspaceConfigPath) { $args.Add('--config-path'); $args.Add($Context.WorkspaceConfigPath) }
    $args.Add('validate')
    $raw = & $python $cli @args 2>&1
    $exit = $LASTEXITCODE
    $text = (@($raw) | ForEach-Object { "$_" }) -join "`n"
    $json = $null
    try { if ($text.Trim()) { $json = $text | ConvertFrom-Json -ErrorAction Stop } } catch { $json = $null }

    if ($exit -eq 3) {
        return @{ Status = 'error'; Error = (Get-RuntimeProp $json 'error' 'UsageError'); Message = (Get-RuntimeProp $json 'message' $text); ConfigPath = (Get-RuntimeProp $json 'config_path'); WorkspaceId = $null; RepositoryRoot = $null; Resolved = $false; Diagnostics = @() }
    }
    if ($exit -ne 0) {
        $err = Get-RuntimeProp $json 'error' 'WorkspaceOperationError'
        $status = if ($err -eq 'WorkspaceConfigNotFoundError') { 'no-config' } else { 'error' }
        return @{ Status = $status; Error = $err; Message = (Get-RuntimeProp $json 'message' $text); ConfigPath = (Get-RuntimeProp $json 'config_path'); WorkspaceId = $null; RepositoryRoot = $null; Resolved = $false; Diagnostics = @() }
    }

    $active = Get-RuntimeProp $json 'active_resolution'
    $activeId = Get-RuntimeProp $active 'active_workspace_id'
    $diag = @(Get-RuntimeProp $active 'diagnostics' @())
    if (-not $activeId) {
        return @{ Status = 'no-active'; Error = $null; Message = 'no active workspace is selected'; ConfigPath = (Get-RuntimeProp $json 'config_path'); WorkspaceId = $null; RepositoryRoot = $null; Resolved = $false; Diagnostics = $diag }
    }
    $resolved = [bool](Get-RuntimeProp $active 'resolved' $false)
    return @{
        Status         = if ($resolved) { 'resolved' } else { 'unresolved' }
        Error          = $null
        Message        = $null
        ConfigPath     = (Get-RuntimeProp $json 'config_path')
        WorkspaceId    = "$activeId"
        RepositoryRoot = (Get-RuntimeProp $active 'repository_root')
        Resolved       = $resolved
        Diagnostics    = $diag
    }
}

function Get-DefaultProcessInfo {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $null }
    $ci = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if (-not $ci) { return $null }
    @{
        Pid          = [int]$ci.ProcessId
        Name         = [string]$ci.Name
        CreationTime = (Format-RuntimeInstant $ci.CreationDate)
        CommandLine  = [string]$ci.CommandLine
    }
}

function Get-DefaultChildProcessIds {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return @() }
    @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.ProcessId })
}

function Start-DefaultManagedProcess {
    param([hashtable]$Spec)
    $params = @{
        FilePath               = $Spec.FilePath
        ArgumentList           = $Spec.Arguments
        WorkingDirectory       = $Spec.WorkingDirectory
        RedirectStandardOutput = $Spec.StdOutLog
        RedirectStandardError  = $Spec.StdErrLog
        WindowStyle            = 'Hidden'
        PassThru               = $true
    }
    $proc = Start-Process @params
    @{ Pid = [int]$proc.Id }
}

function Stop-DefaultProcessId {
    param([int]$ProcessId, [switch]$Force)
    if ($ProcessId -le 0) { return }
    Stop-Process -Id $ProcessId -Force:$Force -ErrorAction SilentlyContinue
}

function Test-DefaultPortListener {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $null }
    [int]$conn.OwningProcess
}

function Invoke-DefaultHttpProbe {
    param([string]$Url, [int]$TimeoutSec)
    try {
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -MaximumRedirection 0 -ErrorAction Stop
        return @{ Ok = $true; StatusCode = [int]$resp.StatusCode; Body = [string]$resp.Content; Error = $null }
    } catch {
        $sc = 0
        $resp = $null
        try { $resp = $_.Exception.Response } catch { $resp = $null }
        if ($resp) { try { $sc = [int]$resp.StatusCode } catch { $sc = 0 } }
        return @{ Ok = $false; StatusCode = $sc; Body = $null; Error = $_.Exception.Message }
    }
}

function New-HiveMindRuntimeContext {
    # Build a fully-wired context with real side effects. Callers (and tests) may
    # override any key by passing a partial hashtable in -Override.
    param([hashtable]$Override)
    $repoRoot = Get-HiveMindRepositoryRootFromModule
    $context = @{
        # Runtime configuration - defaults follow the repository's real dev
        # configuration (ports 8787 / 5173). The host binds to loopback: this is a
        # local-first developer runtime, and loopback avoids exposing the services
        # on the LAN or triggering a Windows Firewall prompt. Health/reachability
        # probes use the same loopback address.
        HostAddress             = '127.0.0.1'
        BackendPort             = 8787
        FrontendPort            = 5173
        BackendHealthPath       = '/health'
        # Bounded, deterministic waits.
        BackendReadyTimeoutSec  = 45
        FrontendReadyTimeoutSec = 45
        PollIntervalSec         = 1
        ShutdownTimeoutSec      = 15
        HttpTimeoutSec          = 5
        # Toolchain + reused Phase 39B CLI.
        RepositoryRoot          = $repoRoot
        PythonExecutable        = 'python'
        NodeExecutable          = 'node'
        WorkspaceCliPath        = (Join-Path $repoRoot 'apps/backend/app/console/repository_workspace_cli.py')
        WorkspaceConfigPath     = $null
        RuntimeHome             = (Resolve-RuntimeHome)
        # Injectable seams (all real by default).
        ResolveWorkspace        = { param($Context) Resolve-HiveMindWorkspaceViaCli -Context $Context }
        GetProcessInfo          = { param($ProcessId) Get-DefaultProcessInfo -ProcessId $ProcessId }
        GetChildProcessIds      = { param($ProcessId) Get-DefaultChildProcessIds -ProcessId $ProcessId }
        StartManagedProcess     = { param($Spec) Start-DefaultManagedProcess -Spec $Spec }
        StopProcessId           = { param($ProcessId, $Force) Stop-DefaultProcessId -ProcessId $ProcessId -Force:$Force }
        TestPortListener        = { param($Port) Test-DefaultPortListener -Port $Port }
        InvokeHttpProbe         = { param($Url, $TimeoutSec) Invoke-DefaultHttpProbe -Url $Url -TimeoutSec $TimeoutSec }
        NowUtc                  = { [datetime]::UtcNow }
        Sleep                   = { param($Seconds) Start-Sleep -Seconds $Seconds }
    }
    if ($Override) { foreach ($key in $Override.Keys) { $context[$key] = $Override[$key] } }
    $context
}

# --------------------------------------------------------------------------- #
# URLs
# --------------------------------------------------------------------------- #
function Get-BackendUrl { param([hashtable]$Context) "http://$($Context.HostAddress):$($Context.BackendPort)" }
function Get-BackendHealthUrl { param([hashtable]$Context) (Get-BackendUrl $Context) + $Context.BackendHealthPath }
function Get-FrontendUrl { param([hashtable]$Context) "http://$($Context.HostAddress):$($Context.FrontendPort)" }

# --------------------------------------------------------------------------- #
# Repository layout validation (independent of Git, self-contained identity)
# --------------------------------------------------------------------------- #
function Test-HiveMindRepositoryLayout {
    # Confirm the resolved repository root exists and *is* the Hive|Mind
    # repository, and that the backend and frontend project files a managed launch
    # depends on are present. This is deliberately self-contained (no Git call) so
    # it works even where Git is unavailable, and it distinguishes the specific
    # failure cases the phase enumerates (missing repo / wrong repo / missing
    # backend files / missing frontend files).
    param([AllowNull()][AllowEmptyString()][string]$RepositoryRoot)
    $problems = [System.Collections.Generic.List[string]]::new()
    if (-not $RepositoryRoot) {
        return @{ Ok = $false; Code = 'workspace_root_missing'; Problems = @('no repository root was resolved'); RepositoryRoot = $null }
    }
    if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
        return @{ Ok = $false; Code = 'repository_root_absent'; Problems = @("repository root does not exist: $RepositoryRoot"); RepositoryRoot = $RepositoryRoot }
    }
    $rootPackage = Join-Path $RepositoryRoot 'package.json'
    $isHiveMind = $false
    if (Test-Path -LiteralPath $rootPackage -PathType Leaf) {
        try {
            $pkg = Get-Content -Raw -LiteralPath $rootPackage | ConvertFrom-Json -ErrorAction Stop
            if ((Get-RuntimeProp $pkg 'name') -eq 'hivemind') { $isHiveMind = $true }
        } catch { $isHiveMind = $false }
    }
    if (-not $isHiveMind) {
        return @{ Ok = $false; Code = 'not_hivemind_repository'; Problems = @("path is not the Hive|Mind repository (root package.json name != 'hivemind'): $RepositoryRoot"); RepositoryRoot = $RepositoryRoot }
    }
    $backendMain = Join-Path $RepositoryRoot 'apps/backend/app/main.py'
    if (-not (Test-Path -LiteralPath $backendMain -PathType Leaf)) { $problems.Add("backend entry point missing: apps/backend/app/main.py") }
    $frontendPackage = Join-Path $RepositoryRoot 'apps/frontend/package.json'
    if (-not (Test-Path -LiteralPath $frontendPackage -PathType Leaf)) { $problems.Add("frontend project file missing: apps/frontend/package.json") }
    if ($problems.Count -gt 0) {
        $code = if ($problems[0] -like '*backend*') { 'backend_files_missing' } else { 'frontend_files_missing' }
        return @{ Ok = $false; Code = $code; Problems = @($problems); RepositoryRoot = $RepositoryRoot }
    }
    @{ Ok = $true; Code = 'ok'; Problems = @(); RepositoryRoot = $RepositoryRoot }
}

function Resolve-ViteBin {
    # Vite is a workspace devDependency and is normally hoisted to the repository
    # root node_modules; fall back to the frontend-local install. Returns $null
    # (with no side effect) when the dependency is not installed, so the caller
    # can emit a clear "run npm install" diagnostic instead of guessing.
    param([Parameter(Mandatory)][string]$RepositoryRoot)
    foreach ($candidate in @(
            (Join-Path $RepositoryRoot 'node_modules/vite/bin/vite.js'),
            (Join-Path $RepositoryRoot 'apps/frontend/node_modules/vite/bin/vite.js'))) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $null
}

# --------------------------------------------------------------------------- #
# Runtime metadata: serialize / read / validate (bounded, atomic)
# --------------------------------------------------------------------------- #
function New-RuntimeServiceRecord {
    param([hashtable]$Context, [Parameter(Mandatory)][int]$ProcessId, [Parameter(Mandatory)][string]$Signature, [Parameter(Mandatory)][string]$Url)
    $info = & $Context.GetProcessInfo $ProcessId
    @{
        pid                = $ProcessId
        name               = (Get-RuntimeProp $info 'Name')
        creation_time      = (Get-RuntimeProp $info 'CreationTime')
        command_line       = (Get-RuntimeProp $info 'CommandLine')
        identity_signature = $Signature
        url                = $Url
    }
}

function ConvertTo-RuntimeMetadata {
    param(
        [Parameter(Mandatory)][hashtable]$Context,
        [Parameter(Mandatory)][string]$WorkspaceId,
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][hashtable]$Backend,
        [Parameter(Mandatory)][hashtable]$Frontend,
        [Parameter(Mandatory)][string]$RuntimeState,
        [AllowNull()][string]$StartedAt
    )
    [ordered]@{
        schema_version  = $script:RuntimeSchemaVersion
        workspace_id    = $WorkspaceId
        repository_path = $RepositoryRoot
        started_at      = $StartedAt
        launcher_pid    = $PID
        runtime_state   = $RuntimeState
        backend         = $Backend
        frontend        = $Frontend
    }
}

function Write-HiveMindRuntimeMetadata {
    # Persist atomically: write a temp sibling then replace, so an interrupted
    # write can never leave a half-written metadata file behind.
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Metadata)
    $json = $Metadata | ConvertTo-Json -Depth 8
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json + "`n")
    if ($bytes.Length -gt $script:MaxRuntimeMetadataBytes) {
        throw "runtime metadata is $($bytes.Length) bytes, exceeding the $script:MaxRuntimeMetadataBytes-byte limit"
    }
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $tmp = "$Path.tmp-$([guid]::NewGuid().ToString('N'))"
    try {
        [System.IO.File]::WriteAllBytes($tmp, $bytes)
        # Move-Item -Force maps to MoveFileEx with MOVEFILE_REPLACE_EXISTING, so
        # the swap is a single filesystem operation whether or not a prior file
        # exists - a partially written temp file can never replace a good one.
        Move-Item -LiteralPath $tmp -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
    }
}

function Read-HiveMindRuntimeMetadata {
    # Bounded, corruption-resistant read. Returns a discriminated result:
    #   Present=$false                      -> no metadata (runtime never started / cleaned)
    #   Present=$true, Malformed=$true      -> file exists but is unusable
    #   Present=$true, Valid=$true, Data=.. -> a usable metadata document
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return @{ Present = $false; Valid = $false; Malformed = $false; Data = $null; Error = $null }
    }
    try { $size = (Get-Item -LiteralPath $Path).Length } catch { $size = 0 }
    if ($size -gt $script:MaxRuntimeMetadataBytes) {
        return @{ Present = $true; Valid = $false; Malformed = $true; Data = $null; Error = 'metadata file exceeds size limit' }
    }
    $data = $null
    try {
        $text = Get-Content -Raw -LiteralPath $Path -ErrorAction Stop
        if (-not $text -or -not $text.Trim()) { return @{ Present = $true; Valid = $false; Malformed = $true; Data = $null; Error = 'metadata file is empty' } }
        $data = $text | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return @{ Present = $true; Valid = $false; Malformed = $true; Data = $null; Error = 'metadata is not valid JSON' }
    }
    if ((Get-RuntimeProp $data 'schema_version') -ne $script:RuntimeSchemaVersion) {
        return @{ Present = $true; Valid = $false; Malformed = $true; Data = $data; Error = 'unsupported or missing schema_version' }
    }
    foreach ($field in @('workspace_id', 'repository_path', 'backend', 'frontend')) {
        if ($null -eq (Get-RuntimeProp $data $field)) {
            return @{ Present = $true; Valid = $false; Malformed = $true; Data = $data; Error = "metadata missing required field '$field'" }
        }
    }
    foreach ($svc in @('backend', 'frontend')) {
        $record = Get-RuntimeProp $data $svc
        if ($null -eq (Get-RuntimeProp $record 'pid')) {
            return @{ Present = $true; Valid = $false; Malformed = $true; Data = $data; Error = "metadata service '$svc' missing pid" }
        }
    }
    @{ Present = $true; Valid = $true; Malformed = $false; Data = $data; Error = $null }
}

function Remove-HiveMindRuntimeMetadata {
    param([Parameter(Mandatory)][string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) { Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue }
}

# --------------------------------------------------------------------------- #
# Process identity + managed service state
# --------------------------------------------------------------------------- #
function Test-ManagedProcessIdentity {
    # A recorded pid is only "ours" if a live process with that pid still matches
    # the recorded name, creation time, and identity signature. Creation time
    # defeats pid reuse; the command-line signature defeats an unrelated process
    # that merely reused the pid at the same instant. Any mismatch -> not ours.
    param([hashtable]$Context, [AllowNull()]$Record)
    if ($null -eq $Record) { return $false }
    $recordedPid = [int](Get-RuntimeProp $Record 'pid' 0)
    if ($recordedPid -le 0) { return $false }
    $live = & $Context.GetProcessInfo $recordedPid
    if ($null -eq $live) { return $false }
    $recordedName = Get-RuntimeProp $Record 'name'
    $liveName = Get-RuntimeProp $live 'Name'
    if ($recordedName -and $liveName -and ($recordedName -ne $liveName)) { return $false }
    $recordedCreation = ConvertTo-CanonicalInstant (Get-RuntimeProp $Record 'creation_time')
    $liveCreation = ConvertTo-CanonicalInstant (Get-RuntimeProp $live 'CreationTime')
    if ($recordedCreation -and $liveCreation -and ($recordedCreation -ne $liveCreation)) { return $false }
    $signature = Get-RuntimeProp $Record 'identity_signature'
    $liveCommand = Get-RuntimeProp $live 'CommandLine'
    if ($signature) {
        if (-not $liveCommand) { return $false }
        if ($liveCommand -notlike "*$signature*") { return $false }
    }
    $true
}

function Get-ManagedServiceState {
    param([hashtable]$Context, [AllowNull()]$Record, [Parameter(Mandatory)][string]$HealthUrl, [Parameter(Mandatory)][scriptblock]$Validator, [switch]$Probe)
    $recordedPid = [int](Get-RuntimeProp $Record 'pid' 0)
    $alive = Test-ManagedProcessIdentity -Context $Context -Record $Record
    $healthy = $false
    $statusCode = 0
    if ($Probe -and $alive) {
        $result = & $Context.InvokeHttpProbe $HealthUrl $Context.HttpTimeoutSec
        $statusCode = [int](Get-RuntimeProp $result 'StatusCode' 0)
        $healthy = [bool](& $Validator $result)
    }
    [pscustomobject][ordered]@{
        Pid        = $recordedPid
        Alive      = $alive
        Healthy    = $healthy
        StatusCode = $statusCode
        Url        = (Get-RuntimeProp $Record 'url')
    }
}

# --------------------------------------------------------------------------- #
# Readiness validators
# --------------------------------------------------------------------------- #
function Test-BackendReadyProbe {
    param($Probe)
    if (-not (Get-RuntimeProp $Probe 'Ok' $false)) { return $false }
    if ([int](Get-RuntimeProp $Probe 'StatusCode' 0) -ne 200) { return $false }
    $body = Get-RuntimeProp $Probe 'Body'
    if (-not $body) { return $false }
    try {
        $json = $body | ConvertFrom-Json -ErrorAction Stop
        $ok = [bool](Get-RuntimeProp $json 'ok' $false)
        $service = "$(Get-RuntimeProp $json 'service')"
        return ($ok -and $service.StartsWith('hivemind'))
    } catch { return $false }
}

function Test-FrontendReadyProbe {
    param($Probe)
    if (Get-RuntimeProp $Probe 'Ok' $false) { return $true }
    $sc = [int](Get-RuntimeProp $Probe 'StatusCode' 0)
    ($sc -ge 200 -and $sc -lt 500)
}

function Wait-ServiceReady {
    # Bounded readiness loop. Fails fast if the managed process exits, otherwise
    # polls the URL on a fixed interval until the validator passes or the deadline
    # is reached. Deadline and sleep flow through the context so tests are
    # deterministic and never actually wait.
    param(
        [hashtable]$Context, [int]$ProcessId, [string]$Url, [scriptblock]$Validator,
        [int]$TimeoutSec, [string]$ServiceName
    )
    $deadline = (& $Context.NowUtc).AddSeconds($TimeoutSec)
    $lastError = $null
    $lastStatus = 0
    while ($true) {
        if ($null -eq (& $Context.GetProcessInfo $ProcessId)) {
            return @{ Ready = $false; Reason = 'process-exited'; StatusCode = $lastStatus; Error = "$ServiceName process exited before it became ready" }
        }
        $probe = & $Context.InvokeHttpProbe $Url $Context.HttpTimeoutSec
        $lastStatus = [int](Get-RuntimeProp $probe 'StatusCode' 0)
        $lastError = Get-RuntimeProp $probe 'Error'
        if (& $Validator $probe) {
            return @{ Ready = $true; Reason = 'ready'; StatusCode = $lastStatus; Error = $null }
        }
        if ((& $Context.NowUtc) -ge $deadline) {
            return @{ Ready = $false; Reason = 'timeout'; StatusCode = $lastStatus; Error = "$ServiceName did not become ready within ${TimeoutSec}s ($lastError)" }
        }
        & $Context.Sleep $Context.PollIntervalSec
    }
}

# --------------------------------------------------------------------------- #
# Identity-gated process-tree termination
# --------------------------------------------------------------------------- #
function Stop-ManagedProcessTree {
    # Terminate a managed process and any descendants it spawned, but ONLY after
    # the recorded root pid passes the identity check. Descendants are discovered
    # live from the verified root, so the tree walk can never wander onto an
    # unrelated process. Leaves are terminated before their parents; a bounded
    # wait confirms exit, with a single forceful escalation if needed.
    param([hashtable]$Context, [AllowNull()]$Record)
    $rootPid = [int](Get-RuntimeProp $Record 'pid' 0)
    if (-not (Test-ManagedProcessIdentity -Context $Context -Record $Record)) {
        return @{ Stopped = $false; Reason = 'identity-mismatch'; Pid = $rootPid }
    }

    # Collect the tree (root + descendants) via a bounded breadth-first walk.
    $order = [System.Collections.Generic.List[int]]::new()
    $queue = [System.Collections.Generic.Queue[int]]::new()
    $seen = [System.Collections.Generic.HashSet[int]]::new()
    $queue.Enqueue($rootPid) | Out-Null
    $seen.Add($rootPid) | Out-Null
    $guard = 0
    while ($queue.Count -gt 0 -and $guard -lt 512) {
        $guard++
        $current = $queue.Dequeue()
        $order.Add($current)
        foreach ($child in @(& $Context.GetChildProcessIds $current)) {
            if ($seen.Add($child)) { $queue.Enqueue($child) | Out-Null }
        }
    }

    # Terminate leaves first (reverse discovery order), root last.
    $order.Reverse()
    foreach ($procId in $order) { & $Context.StopProcessId $procId $true }

    # Bounded confirmation that the root actually exited, with one escalation.
    $deadline = (& $Context.NowUtc).AddSeconds($Context.ShutdownTimeoutSec)
    while ($null -ne (& $Context.GetProcessInfo $rootPid)) {
        if ((& $Context.NowUtc) -ge $deadline) {
            & $Context.StopProcessId $rootPid $true
            if ($null -ne (& $Context.GetProcessInfo $rootPid)) {
                return @{ Stopped = $false; Reason = 'did-not-exit'; Pid = $rootPid }
            }
            break
        }
        & $Context.Sleep $Context.PollIntervalSec
    }
    @{ Stopped = $true; Reason = 'stopped'; Pid = $rootPid }
}

# --------------------------------------------------------------------------- #
# Status classification
# --------------------------------------------------------------------------- #
function Get-HiveMindRuntimeStatus {
    # Pure-ish status computation: reads metadata, checks managed-process identity,
    # and (when -Probe) checks health/reachability, then classifies the overall
    # runtime. Never mutates metadata or starts anything.
    param([hashtable]$Context, [Parameter(Mandatory)][string]$MetadataPath, [switch]$Probe)
    $meta = Read-HiveMindRuntimeMetadata -Path $MetadataPath
    $backendHealthUrl = Get-BackendHealthUrl $Context
    $frontendUrl = Get-FrontendUrl $Context

    if (-not $meta.Present) {
        return [pscustomobject][ordered]@{
            Overall = 'stopped'; MetadataPresent = $false; MetadataMalformed = $false
            Backend = $null; Frontend = $null; Data = $null; Error = $null
            BackendUrl = (Get-BackendUrl $Context); FrontendUrl = $frontendUrl
        }
    }
    if ($meta.Malformed) {
        return [pscustomobject][ordered]@{
            Overall = 'stale'; MetadataPresent = $true; MetadataMalformed = $true
            Backend = $null; Frontend = $null; Data = $meta.Data; Error = $meta.Error
            BackendUrl = (Get-BackendUrl $Context); FrontendUrl = $frontendUrl
        }
    }

    $data = $meta.Data
    $backendRecord = Get-RuntimeProp $data 'backend'
    $frontendRecord = Get-RuntimeProp $data 'frontend'
    $backend = Get-ManagedServiceState -Context $Context -Record $backendRecord -HealthUrl $backendHealthUrl -Validator ${function:Test-BackendReadyProbe} -Probe:$Probe
    $frontend = Get-ManagedServiceState -Context $Context -Record $frontendRecord -HealthUrl $frontendUrl -Validator ${function:Test-FrontendReadyProbe} -Probe:$Probe
    $runtimeState = "$(Get-RuntimeProp $data 'runtime_state')"

    $aliveCount = @($backend, $frontend | Where-Object { $_.Alive }).Count
    if ($aliveCount -eq 0) { $overall = 'stale' }
    elseif ($aliveCount -eq 1) { $overall = 'partial' }
    else {
        if ($Probe) {
            if ($backend.Healthy -and $frontend.Healthy) { $overall = 'healthy' }
            elseif ($runtimeState -eq 'starting') { $overall = 'starting' }
            else { $overall = 'degraded' }
        } else {
            $overall = if ($runtimeState -eq 'starting') { 'starting' } else { 'running' }
        }
    }

    [pscustomobject][ordered]@{
        Overall = $overall; MetadataPresent = $true; MetadataMalformed = $false
        Backend = $backend; Frontend = $frontend; Data = $data; Error = $null
        BackendUrl = (Get-BackendUrl $Context); FrontendUrl = $frontendUrl
    }
}

# --------------------------------------------------------------------------- #
# Command results
# --------------------------------------------------------------------------- #
function New-RuntimeResult {
    param([int]$ExitCode, [System.Collections.IDictionary]$Payload, [string[]]$Lines)
    [pscustomobject]@{ ExitCode = $ExitCode; Payload = $Payload; Lines = @($Lines) }
}

# --------------------------------------------------------------------------- #
# Preflight shared by start / verify
# --------------------------------------------------------------------------- #
function Invoke-RuntimePreflight {
    # Resolve the workspace (Phase 39B), validate the repository layout, and check
    # the toolchain. Returns a structured result the caller turns into diagnostics.
    param([hashtable]$Context)
    $resolution = & $Context.ResolveWorkspace $Context
    $checks = [System.Collections.Generic.List[object]]::new()
    $add = { param($id, $ok, $detail) $checks.Add([pscustomobject]@{ Check = $id; Ok = [bool]$ok; Detail = $detail }) }

    $status = Get-RuntimeProp $resolution 'Status'
    $workspaceOk = ($status -eq 'resolved' -or $status -eq 'unresolved')
    & $add 'workspace-configured' ($status -ne 'no-config' -and $status -ne 'error') (Get-RuntimeProp $resolution 'Message' $status)
    & $add 'workspace-active' $workspaceOk "status=$status"

    $repoRoot = Get-RuntimeProp $resolution 'RepositoryRoot'
    $layout = Test-HiveMindRepositoryLayout -RepositoryRoot $repoRoot
    & $add 'repository-layout' $layout.Ok ($layout.Problems -join '; ')

    $viteBin = if ($layout.Ok) { Resolve-ViteBin -RepositoryRoot $repoRoot } else { $null }

    # Toolchain availability (never installs anything).
    $pythonOk = [bool](Get-Command $Context.PythonExecutable -ErrorAction SilentlyContinue)
    & $add 'python-available' $pythonOk "$($Context.PythonExecutable)"
    $nodeOk = [bool](Get-Command $Context.NodeExecutable -ErrorAction SilentlyContinue)
    & $add 'node-available' $nodeOk "$($Context.NodeExecutable)"
    & $add 'frontend-dependencies' ([bool]$viteBin) $(if ($viteBin) { $viteBin } else { 'vite not installed (run npm install)' })

    $overallOk = -not ($checks | Where-Object { -not $_.Ok })
    @{
        Ok           = [bool]$overallOk
        Resolution   = $resolution
        Layout       = $layout
        ViteBin      = $viteBin
        RepositoryRoot = $repoRoot
        WorkspaceId  = (Get-RuntimeProp $resolution 'WorkspaceId')
        Checks       = @($checks)
    }
}

# --------------------------------------------------------------------------- #
# START
# --------------------------------------------------------------------------- #
function Invoke-RuntimeStart {
    param([hashtable]$Context)
    $lines = [System.Collections.Generic.List[string]]::new()
    $preflight = Invoke-RuntimePreflight -Context $Context
    $resolution = $preflight.Resolution

    if (-not $preflight.Ok) {
        $failed = @($preflight.Checks | Where-Object { -not $_.Ok } | ForEach-Object { "$($_.Check): $($_.Detail)" })
        $lines.Add('[FAIL] runtime start preflight failed')
        foreach ($f in $failed) { $lines.Add("  - $f") }
        $lines.Add('  next: configure a workspace (scripts/workspaces) or install dependencies, then retry.')
        return New-RuntimeResult 2 ([ordered]@{ command = 'start'; status = 'error'; error = 'PreflightFailed'; failures = $failed; workspace = $resolution }) $lines.ToArray()
    }

    $workspaceId = $preflight.WorkspaceId
    $repoRoot = $preflight.RepositoryRoot
    $paths = Get-HiveMindRuntimePaths -RuntimeHome $Context.RuntimeHome -WorkspaceId $workspaceId

    # Already-running / stale handling.
    $current = Get-HiveMindRuntimeStatus -Context $Context -MetadataPath $paths.MetadataPath -Probe
    switch ($current.Overall) {
        'healthy' {
            $lines.Add('[PASS] Hive|Mind runtime is already running (managed).')
            $lines.Add("  backend:  $($current.BackendUrl)  (pid $($current.Backend.Pid))")
            $lines.Add("  frontend: $($current.FrontendUrl)  (pid $($current.Frontend.Pid))")
            return New-RuntimeResult 0 ([ordered]@{ command = 'start'; status = 'already-running'; workspace_id = $workspaceId; backend_url = $current.BackendUrl; frontend_url = $current.FrontendUrl }) $lines.ToArray()
        }
        { $_ -in @('partial', 'degraded', 'starting') } {
            $lines.Add("[FAIL] a managed runtime is already present in state '$($current.Overall)'.")
            $lines.Add('  next: run `stop` (or `restart`) before starting again.')
            return New-RuntimeResult 2 ([ordered]@{ command = 'start'; status = 'error'; error = 'AlreadyPresent'; runtime_state = $current.Overall; workspace_id = $workspaceId }) $lines.ToArray()
        }
        'stale' {
            $lines.Add('[info] clearing stale runtime metadata from a previous session.')
            Remove-HiveMindRuntimeMetadata -Path $paths.MetadataPath
        }
    }

    # Port pre-check (both ports) before launching anything, so a known conflict
    # never produces a partial start.
    foreach ($portCheck in @(
            @{ Name = 'backend'; Port = $Context.BackendPort },
            @{ Name = 'frontend'; Port = $Context.FrontendPort })) {
        $owner = & $Context.TestPortListener $portCheck.Port
        if ($null -ne $owner) {
            $ownerInfo = & $Context.GetProcessInfo ([int]$owner)
            $ownerName = Get-RuntimeProp $ownerInfo 'Name' 'unknown'
            $lines.Add("[FAIL] $($portCheck.Name) port $($portCheck.Port) is already in use by pid $owner ($ownerName).")
            $lines.Add('  next: stop the conflicting process or free the port, then retry.')
            return New-RuntimeResult 2 ([ordered]@{ command = 'start'; status = 'error'; error = 'PortConflict'; service = $portCheck.Name; port = $portCheck.Port; owning_pid = [int]$owner; owning_process = $ownerName }) $lines.ToArray()
        }
    }

    # Ensure the log directory exists.
    if (-not (Test-Path -LiteralPath $paths.LogDir)) { New-Item -ItemType Directory -Path $paths.LogDir -Force | Out-Null }

    $backendUrl = Get-BackendUrl $Context
    $frontendUrl = Get-FrontendUrl $Context
    $startedAt = Format-RuntimeInstant (& $Context.NowUtc)
    $launched = [System.Collections.Generic.List[hashtable]]::new()

    # Roll back everything launched so far, then clear metadata.
    $rollback = {
        param($reason)
        foreach ($rec in @($launched)) { Stop-ManagedProcessTree -Context $Context -Record $rec | Out-Null }
        Remove-HiveMindRuntimeMetadata -Path $paths.MetadataPath
    }

    # ---- Backend ----
    $backendArgs = @('-m', 'uvicorn', 'app.main:app', '--app-dir', 'apps/backend', '--host', $Context.HostAddress, '--port', "$($Context.BackendPort)")
    $backendStart = & $Context.StartManagedProcess @{ FilePath = $Context.PythonExecutable; Arguments = $backendArgs; WorkingDirectory = $repoRoot; StdOutLog = $paths.BackendOutLog; StdErrLog = $paths.BackendErrLog }
    $backendPid = [int](Get-RuntimeProp $backendStart 'Pid' 0)
    $backendRecord = New-RuntimeServiceRecord -Context $Context -ProcessId $backendPid -Signature 'app.main:app' -Url $backendUrl
    $launched.Add($backendRecord)

    # ---- Frontend ----
    $frontendArgs = @($preflight.ViteBin, '--host', $Context.HostAddress, '--port', "$($Context.FrontendPort)")
    $frontendStart = & $Context.StartManagedProcess @{ FilePath = $Context.NodeExecutable; Arguments = $frontendArgs; WorkingDirectory = (Join-Path $repoRoot 'apps/frontend'); StdOutLog = $paths.FrontendOutLog; StdErrLog = $paths.FrontendErrLog }
    $frontendPid = [int](Get-RuntimeProp $frontendStart 'Pid' 0)
    $frontendRecord = New-RuntimeServiceRecord -Context $Context -ProcessId $frontendPid -Signature 'vite' -Url $frontendUrl
    $launched.Add($frontendRecord)

    # Persist "starting" metadata immediately so an interruption during readiness
    # still leaves a stop-able record (no orphaned managed processes).
    $metadata = ConvertTo-RuntimeMetadata -Context $Context -WorkspaceId $workspaceId -RepositoryRoot $repoRoot -Backend $backendRecord -Frontend $frontendRecord -RuntimeState 'starting' -StartedAt $startedAt
    Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $metadata

    # ---- Bounded readiness ----
    $backendReady = Wait-ServiceReady -Context $Context -ProcessId $backendPid -Url (Get-BackendHealthUrl $Context) -Validator ${function:Test-BackendReadyProbe} -TimeoutSec $Context.BackendReadyTimeoutSec -ServiceName 'backend'
    if (-not $backendReady.Ready) {
        & $rollback 'backend-not-ready'
        $lines.Add("[FAIL] backend did not become healthy: $($backendReady.Error)")
        $lines.Add("  logs: $($paths.BackendErrLog)")
        $lines.Add('  the runtime was rolled back; no managed processes remain.')
        return New-RuntimeResult 2 ([ordered]@{ command = 'start'; status = 'error'; error = 'BackendNotReady'; reason = $backendReady.Reason; workspace_id = $workspaceId; backend_log = $paths.BackendErrLog; rolled_back = $true }) $lines.ToArray()
    }

    $frontendReady = Wait-ServiceReady -Context $Context -ProcessId $frontendPid -Url $frontendUrl -Validator ${function:Test-FrontendReadyProbe} -TimeoutSec $Context.FrontendReadyTimeoutSec -ServiceName 'frontend'
    if (-not $frontendReady.Ready) {
        & $rollback 'frontend-not-ready'
        $lines.Add("[FAIL] frontend did not become reachable: $($frontendReady.Error)")
        $lines.Add("  logs: $($paths.FrontendErrLog)")
        $lines.Add('  the runtime was rolled back; no managed processes remain.')
        return New-RuntimeResult 2 ([ordered]@{ command = 'start'; status = 'error'; error = 'FrontendNotReady'; reason = $frontendReady.Reason; workspace_id = $workspaceId; frontend_log = $paths.FrontendErrLog; rolled_back = $true }) $lines.ToArray()
    }

    # Both ready -> promote to running.
    $metadata['runtime_state'] = 'running'
    Write-HiveMindRuntimeMetadata -Path $paths.MetadataPath -Metadata $metadata

    $lines.Add('[PASS] Hive|Mind runtime is up.')
    $lines.Add("  workspace: $workspaceId  ($repoRoot)")
    $lines.Add("  backend:   $backendUrl$($Context.BackendHealthPath)  (pid $backendPid, healthy)")
    $lines.Add("  frontend:  $frontendUrl  (pid $frontendPid, reachable)")
    $lines.Add("  metadata:  $($paths.MetadataPath)")
    $lines.Add("  logs:      $($paths.LogDir)")
    New-RuntimeResult 0 ([ordered]@{
            command = 'start'; status = 'ok'; workspace_id = $workspaceId; repository_path = $repoRoot
            backend_url = $backendUrl; frontend_url = $frontendUrl; backend_pid = $backendPid; frontend_pid = $frontendPid
            metadata_path = $paths.MetadataPath; log_dir = $paths.LogDir
        }) $lines.ToArray()
}

# --------------------------------------------------------------------------- #
# STOP
# --------------------------------------------------------------------------- #
function Invoke-RuntimeStop {
    param([hashtable]$Context, [AllowNull()][string]$WorkspaceId)
    $lines = [System.Collections.Generic.List[string]]::new()

    # Resolve the workspace id so we know which runtime metadata to read. Stop must
    # never depend on live application state, only on recorded managed metadata.
    if (-not $WorkspaceId) {
        $resolution = & $Context.ResolveWorkspace $Context
        $WorkspaceId = Get-RuntimeProp $resolution 'WorkspaceId'
        if (-not $WorkspaceId) {
            $lines.Add('[info] no active workspace resolved; nothing managed to stop.')
            return New-RuntimeResult 0 ([ordered]@{ command = 'stop'; status = 'no-workspace' }) $lines.ToArray()
        }
    }
    $paths = Get-HiveMindRuntimePaths -RuntimeHome $Context.RuntimeHome -WorkspaceId $WorkspaceId
    $meta = Read-HiveMindRuntimeMetadata -Path $paths.MetadataPath

    if (-not $meta.Present) {
        $lines.Add('[info] no runtime metadata found; runtime is already stopped.')
        return New-RuntimeResult 0 ([ordered]@{ command = 'stop'; status = 'already-stopped'; workspace_id = $WorkspaceId }) $lines.ToArray()
    }
    if ($meta.Malformed) {
        # We cannot trust pids from a malformed file, so we must not terminate
        # anything. Normalizing (removing) the unusable file is safe and leaves a
        # deterministic clean state.
        Remove-HiveMindRuntimeMetadata -Path $paths.MetadataPath
        $lines.Add("[info] runtime metadata was malformed ($($meta.Error)); removed it without terminating any process.")
        return New-RuntimeResult 0 ([ordered]@{ command = 'stop'; status = 'stale-cleaned'; workspace_id = $WorkspaceId; detail = $meta.Error }) $lines.ToArray()
    }

    $data = $meta.Data
    $results = [ordered]@{}
    $anyFailed = $false
    foreach ($svc in @('frontend', 'backend')) {
        $record = Get-RuntimeProp $data $svc
        if (-not (Test-ManagedProcessIdentity -Context $Context -Record $record)) {
            $lines.Add("[info] $svc process (pid $(Get-RuntimeProp $record 'pid')) is not the recorded managed process; skipping.")
            $results[$svc] = 'not-running'
            continue
        }
        $stop = Stop-ManagedProcessTree -Context $Context -Record $record
        if ($stop.Stopped) {
            $lines.Add("[ok] stopped $svc (pid $($stop.Pid)).")
            $results[$svc] = 'stopped'
        } else {
            $lines.Add("[FAIL] could not stop $svc (pid $($stop.Pid)): $($stop.Reason).")
            $results[$svc] = "failed:$($stop.Reason)"
            $anyFailed = $true
        }
    }

    if ($anyFailed) {
        $lines.Add('[FAIL] one or more managed processes did not stop; metadata retained for inspection.')
        return New-RuntimeResult 2 ([ordered]@{ command = 'stop'; status = 'error'; error = 'StopIncomplete'; workspace_id = $WorkspaceId; services = $results }) $lines.ToArray()
    }

    Remove-HiveMindRuntimeMetadata -Path $paths.MetadataPath
    $lines.Add('[PASS] Hive|Mind runtime stopped; runtime metadata cleared.')
    New-RuntimeResult 0 ([ordered]@{ command = 'stop'; status = 'ok'; workspace_id = $WorkspaceId; services = $results }) $lines.ToArray()
}

# --------------------------------------------------------------------------- #
# STATUS
# --------------------------------------------------------------------------- #
function Invoke-RuntimeStatus {
    param([hashtable]$Context)
    $lines = [System.Collections.Generic.List[string]]::new()
    $resolution = & $Context.ResolveWorkspace $Context
    $workspaceId = Get-RuntimeProp $resolution 'WorkspaceId'
    $repoRoot = Get-RuntimeProp $resolution 'RepositoryRoot'
    $workspaceStatus = Get-RuntimeProp $resolution 'Status'

    $lines.Add("workspace:        $(if ($workspaceId) { $workspaceId } else { '(none)' })  [$workspaceStatus]")
    $lines.Add("repository_path:  $(if ($repoRoot) { $repoRoot } else { '(unresolved)' })")

    if (-not $workspaceId) {
        $lines.Add('overall:          stopped (no active workspace configured)')
        return New-RuntimeResult 0 ([ordered]@{ command = 'status'; status = 'ok'; overall = 'stopped'; workspace = $resolution }) $lines.ToArray()
    }

    $paths = Get-HiveMindRuntimePaths -RuntimeHome $Context.RuntimeHome -WorkspaceId $workspaceId
    $state = Get-HiveMindRuntimeStatus -Context $Context -MetadataPath $paths.MetadataPath -Probe

    $lines.Add("metadata:         $(if ($state.MetadataPresent) { $paths.MetadataPath } else { '(none)' })")
    if ($state.MetadataMalformed) { $lines.Add("metadata_error:   $($state.Error)") }
    if ($state.Backend) {
        $lines.Add("backend:          alive=$($state.Backend.Alive)  healthy=$($state.Backend.Healthy)  pid=$($state.Backend.Pid)  $($state.BackendUrl)$($Context.BackendHealthPath)")
    } else {
        $lines.Add("backend:          $($state.BackendUrl)$($Context.BackendHealthPath)  (not managed)")
    }
    if ($state.Frontend) {
        $lines.Add("frontend:         alive=$($state.Frontend.Alive)  reachable=$($state.Frontend.Healthy)  pid=$($state.Frontend.Pid)  $($state.FrontendUrl)")
    } else {
        $lines.Add("frontend:         $($state.FrontendUrl)  (not managed)")
    }
    $lines.Add("overall:          $($state.Overall)")

    $payload = [ordered]@{
        command = 'status'; status = 'ok'; overall = $state.Overall
        workspace_id = $workspaceId; repository_path = $repoRoot
        metadata_present = $state.MetadataPresent; metadata_malformed = $state.MetadataMalformed
        backend_url = $state.BackendUrl; frontend_url = $state.FrontendUrl
    }
    if ($state.Backend) { $payload['backend'] = @{ alive = $state.Backend.Alive; healthy = $state.Backend.Healthy; pid = $state.Backend.Pid; status_code = $state.Backend.StatusCode } }
    if ($state.Frontend) { $payload['frontend'] = @{ alive = $state.Frontend.Alive; reachable = $state.Frontend.Healthy; pid = $state.Frontend.Pid; status_code = $state.Frontend.StatusCode } }
    New-RuntimeResult 0 $payload $lines.ToArray()
}

# --------------------------------------------------------------------------- #
# RESTART  (compose stop + start; no separate process management)
# --------------------------------------------------------------------------- #
function Invoke-RuntimeRestart {
    param([hashtable]$Context)
    $lines = [System.Collections.Generic.List[string]]::new()
    $stop = Invoke-RuntimeStop -Context $Context
    foreach ($l in $stop.Lines) { $lines.Add($l) }
    if ($stop.ExitCode -ne 0) {
        $lines.Add('[FAIL] restart aborted because stop did not complete cleanly.')
        return New-RuntimeResult $stop.ExitCode ([ordered]@{ command = 'restart'; status = 'error'; error = 'StopFailed'; stop = $stop.Payload }) $lines.ToArray()
    }
    $start = Invoke-RuntimeStart -Context $Context
    foreach ($l in $start.Lines) { $lines.Add($l) }
    New-RuntimeResult $start.ExitCode ([ordered]@{ command = 'restart'; status = (Get-RuntimeProp $start.Payload 'status'); start = $start.Payload }) $lines.ToArray()
}

# --------------------------------------------------------------------------- #
# VERIFY  (read-only: configuration, files, toolchain, ports, health)
# --------------------------------------------------------------------------- #
function Invoke-RuntimeVerify {
    param([hashtable]$Context)
    $lines = [System.Collections.Generic.List[string]]::new()
    $preflight = Invoke-RuntimePreflight -Context $Context
    foreach ($check in $preflight.Checks) {
        $mark = if ($check.Ok) { 'PASS' } else { 'FAIL' }
        $lines.Add("[$mark] $($check.Check)  $($check.Detail)")
    }

    # Port availability: free, or owned by our own healthy managed runtime.
    $workspaceId = $preflight.WorkspaceId
    $portFindings = [ordered]@{}
    $portsOk = $true
    $managedBackendPid = 0
    $managedFrontendPid = 0
    if ($workspaceId) {
        $paths = Get-HiveMindRuntimePaths -RuntimeHome $Context.RuntimeHome -WorkspaceId $workspaceId
        $state = Get-HiveMindRuntimeStatus -Context $Context -MetadataPath $paths.MetadataPath
        if ($state.Backend) { $managedBackendPid = [int]$state.Backend.Pid }
        if ($state.Frontend) { $managedFrontendPid = [int]$state.Frontend.Pid }
    }
    foreach ($portCheck in @(
            @{ Name = 'backend'; Port = $Context.BackendPort; Managed = $managedBackendPid },
            @{ Name = 'frontend'; Port = $Context.FrontendPort; Managed = $managedFrontendPid })) {
        $owner = & $Context.TestPortListener $portCheck.Port
        if ($null -eq $owner) {
            $lines.Add("[PASS] port-$($portCheck.Name) ($($portCheck.Port)) is free")
            $portFindings[$portCheck.Name] = @{ port = $portCheck.Port; free = $true; owning_pid = $null }
        } elseif ([int]$owner -eq $portCheck.Managed -and $portCheck.Managed -gt 0) {
            $lines.Add("[PASS] port-$($portCheck.Name) ($($portCheck.Port)) is held by the managed runtime (pid $owner)")
            $portFindings[$portCheck.Name] = @{ port = $portCheck.Port; free = $false; owning_pid = [int]$owner; managed = $true }
        } else {
            $ownerInfo = & $Context.GetProcessInfo ([int]$owner)
            $lines.Add("[FAIL] port-$($portCheck.Name) ($($portCheck.Port)) is in use by pid $owner ($(Get-RuntimeProp $ownerInfo 'Name' 'unknown'))")
            $portFindings[$portCheck.Name] = @{ port = $portCheck.Port; free = $false; owning_pid = [int]$owner; managed = $false }
            $portsOk = $false
        }
    }

    $ok = $preflight.Ok -and $portsOk
    $lines.Add("verify: $(if ($ok) { 'PASS' } else { 'FAIL' })")
    $checkPayload = @($preflight.Checks | ForEach-Object { @{ check = $_.Check; ok = $_.Ok; detail = $_.Detail } })
    New-RuntimeResult ($(if ($ok) { 0 } else { 2 })) ([ordered]@{
            command = 'verify'; status = $(if ($ok) { 'ok' } else { 'error' }); ok = $ok
            workspace_id = $workspaceId; checks = $checkPayload; ports = $portFindings
        }) $lines.ToArray()
}

# --------------------------------------------------------------------------- #
# Top-level dispatch
# --------------------------------------------------------------------------- #
function Invoke-HiveMindRuntime {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateSet('start', 'status', 'stop', 'restart', 'verify')][string]$Command,
        [string]$WorkspaceConfigPath,
        [hashtable]$ContextOverride,
        [hashtable]$Context
    )
    if (-not $Context) {
        $override = @{}
        if ($WorkspaceConfigPath) { $override['WorkspaceConfigPath'] = $WorkspaceConfigPath }
        if ($ContextOverride) { foreach ($k in $ContextOverride.Keys) { $override[$k] = $ContextOverride[$k] } }
        $Context = New-HiveMindRuntimeContext -Override $override
    }
    switch ($Command) {
        'start' { return Invoke-RuntimeStart -Context $Context }
        'status' { return Invoke-RuntimeStatus -Context $Context }
        'stop' { return Invoke-RuntimeStop -Context $Context }
        'restart' { return Invoke-RuntimeRestart -Context $Context }
        'verify' { return Invoke-RuntimeVerify -Context $Context }
    }
}

Export-ModuleMember -Function `
    Invoke-HiveMindRuntime, New-HiveMindRuntimeContext, Resolve-RuntimeHome, `
    Get-HiveMindRuntimePaths, Test-HiveMindRepositoryLayout, Resolve-ViteBin, `
    ConvertTo-RuntimeMetadata, New-RuntimeServiceRecord, Write-HiveMindRuntimeMetadata, `
    Read-HiveMindRuntimeMetadata, Remove-HiveMindRuntimeMetadata, Test-ManagedProcessIdentity, `
    Get-ManagedServiceState, Wait-ServiceReady, Stop-ManagedProcessTree, Get-HiveMindRuntimeStatus, `
    Invoke-RuntimePreflight, Invoke-RuntimeStart, Invoke-RuntimeStop, Invoke-RuntimeStatus, `
    Invoke-RuntimeRestart, Invoke-RuntimeVerify, Test-BackendReadyProbe, Test-FrontendReadyProbe, `
    Get-BackendUrl, Get-BackendHealthUrl, Get-FrontendUrl, Get-RuntimeProp, Format-RuntimeInstant
