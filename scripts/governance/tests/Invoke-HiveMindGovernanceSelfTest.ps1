Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$governanceRoot=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $governanceRoot 'HiveMindGovernance.psm1') -Force
$results=[System.Collections.Generic.List[object]]::new()
$tempRoot=Join-Path ([System.IO.Path]::GetTempPath()) ("hive-mind-governance-tests-"+[guid]::NewGuid().ToString('N'))

function Invoke-TestGit { param([string]$Path,[string[]]$Arguments) $output=& git -C $Path @Arguments; if($LASTEXITCODE -ne 0){throw "Fixture git failed: $($output -join ' ')"}; @($output) }
function New-Fixture {
    param([string]$Parent=$tempRoot,[string]$Name='hive-mind',[string]$Remote='https://github.com/britbufkin1225-web/hive-mind.git')
    $path=Join-Path $Parent $Name; New-Item -ItemType Directory -Path $path -Force | Out-Null
    Invoke-TestGit $path @('init','--initial-branch=main') | Out-Null
    Invoke-TestGit $path @('config','user.name','Governance Self Test') | Out-Null
    Invoke-TestGit $path @('config','user.email','governance-self-test@example.invalid') | Out-Null
    Invoke-TestGit $path @('remote','add','origin',$Remote) | Out-Null
    Set-Content -LiteralPath (Join-Path $path 'fixture.txt') -Value 'baseline' -NoNewline
    Invoke-TestGit $path @('add','fixture.txt') | Out-Null; Invoke-TestGit $path @('commit','-m','fixture baseline') | Out-Null
    $baselineOutput=@(Invoke-TestGit $path @('rev-parse','HEAD')); $baseline=[string]$baselineOutput[0]; Invoke-TestGit $path @('switch','-c','phase-test') | Out-Null
    [pscustomobject]@{Path=$path;Baseline=$baseline;Remote=$Remote}
}
function Get-Arguments { param($Fixture)
    @{RepositoryPath=$Fixture.Path;ExpectedRemote='https://github.com/britbufkin1225-web/hive-mind.git';ExpectedBranch='phase-test';ExpectedBaseline=$Fixture.Baseline;CurrentPhase='Phase 38B';AgentName='codex';AgentRole='primary-implementer';CapabilityLevel='L3';CompositionMode='sequential-isolated';WriteAuthority='bounded-path-write';Phase36KStatus='paused-and-untouched';DisableCanonicalPathEnforcement=$true}
}
function Invoke-Fixture { param($Fixture) $arguments=Get-Arguments $Fixture; Invoke-HiveMindGovernancePreflight @arguments }
function Add-Test { param([string]$Name,[scriptblock]$Body)
    try { & $Body; $results.Add([pscustomobject]@{Name=$Name;Status='PASS';Detail=$null}) }
    catch { $results.Add([pscustomobject]@{Name=$Name;Status='FAIL';Detail=($_.Exception.Message+"`n"+$_.ScriptStackTrace)}) }
}
function Assert-True { param([bool]$Condition,[string]$Message) if(-not $Condition){throw $Message} }
function Has-Blocked { param($Result,[string]$Id) [bool]($Result.Checks | Where-Object { $_.CheckIdentifier -eq $Id -and $_.Status -eq 'BLOCKED' }) }
function New-ManifestObject { param($Fixture,[string]$Branch='phase-test',[string]$Baseline=$Fixture.Baseline)
    [ordered]@{
        manifest_version='agent-composition.v1';contract_version='agent-contribution.v1'
        project=[ordered]@{name='Hive|Mind';parent_label='devdevbuilds';repository_root=$Fixture.Path;remote_url='https://github.com/britbufkin1225-web/hive-mind.git'}
        phase=[ordered]@{id='Phase 38B';name='Test';status_at_start='Active';status_at_end='Implemented locally';paused_tracks=@('Phase 36K')}
        agent=[ordered]@{name='codex';assigned_role='primary-implementer';capability_level='L3';composition_mode='sequential-isolated'}
        authority=[ordered]@{write_authority='bounded-path-write';owned_paths=@();read_only_paths=@();forbidden_paths=@()}
        git=[ordered]@{expected_baseline=$Baseline;actual_baseline=$Baseline;merge_base=$Baseline;working_branch=$Branch;input_commit=$Baseline;output_commit=$Baseline;earlier_commits_preserved=$true;destructive_operations_used=$false}
        contribution=[ordered]@{objective='test';summary='test';changed_files=@();added_files=@();deleted_files=@();renamed_files=@();diff_statistics=[ordered]@{files_changed=0;insertions=0;deletions=0};scope_deviations=@()}
        validation=[ordered]@{commands=@();outcomes=@();tests_not_run=@();evidence_limitations=@()};reporting=[ordered]@{assumptions=@();known_limitations=@();blockers=@()}
        handoff=[ordered]@{recommended_next_actor='human-project-owner';recommended_next_role='independent-auditor-hardener';required_follow_up=@();safe_to_compose=$false;safe_to_push=$false;safe_to_open_pr=$false;independently_audited=$false;hardened=$false;pushed=$false;pr_opened=$false;merged=$false;local_main_normalized=$false;working_tree_clean=$true}
    }
}

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Add-Test '1 canonical-style valid repository identity' { $f=New-Fixture -Parent (Join-Path $tempRoot 'valid'); $r=Invoke-Fixture $f; $blocked=@($r.Checks|Where-Object Status -eq 'BLOCKED'); Assert-True ($r.OverallResult -eq 'PASS') ("Valid fixture baseline '$($f.Baseline)' was blocked: "+(($blocked|ForEach-Object CheckIdentifier) -join ', ')) }
    Add-Test '2 wrong repository path' { $f=New-Fixture -Parent (Join-Path $tempRoot 'wrongpath'); $a=Get-Arguments $f; $a.Remove('DisableCanonicalPathEnforcement'); $a.CanonicalRepositoryPath=Join-Path $tempRoot 'elsewhere/hive-mind'; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'repository.canonical-path') 'Wrong canonical path was accepted.' }
    Add-Test '3 OneDrive path rejection' { $f=New-Fixture -Parent (Join-Path $tempRoot 'OneDrive'); $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'repository.path.onedrive') 'OneDrive path was accepted.' }
    Add-Test '4 wrong folder name' { $f=New-Fixture -Parent (Join-Path $tempRoot 'folder') -Name 'hive mind'; $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'repository.folder') 'Wrong folder name was accepted.' }
    Add-Test '5 missing Git repository' { $path=Join-Path $tempRoot 'nogit/hive-mind'; New-Item -ItemType Directory -Path $path -Force|Out-Null; $f=[pscustomobject]@{Path=$path;Baseline=('0'*40)}; $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'repository.git') 'Non-Git directory was accepted.' }
    Add-Test '6 wrong remote' { $f=New-Fixture -Parent (Join-Path $tempRoot 'remote') -Remote 'https://github.com/example/wrong.git'; $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'repository.remote') 'Wrong remote was accepted.' }
    Add-Test '7 SSH and HTTPS remote normalization' { Assert-True ((ConvertTo-NormalizedRemote 'git@github.com:britbufkin1225-web/hive-mind.git') -eq (ConvertTo-NormalizedRemote 'https://github.com/britbufkin1225-web/hive-mind.git')) 'Equivalent remotes did not normalize equally.' }
    Add-Test '8 detached HEAD' { $f=New-Fixture -Parent (Join-Path $tempRoot 'detached'); Invoke-TestGit $f.Path @('checkout','--detach')|Out-Null; $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'git.detached-head') 'Detached HEAD was accepted.' }
    Add-Test '9 wrong branch' { $f=New-Fixture -Parent (Join-Path $tempRoot 'branch'); $a=Get-Arguments $f; $a.ExpectedBranch='different'; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'git.branch') 'Wrong branch was accepted.' }
    Add-Test '10 valid baseline ancestry' { $f=New-Fixture -Parent (Join-Path $tempRoot 'ancestry'); Set-Content (Join-Path $f.Path 'ahead.txt') 'ahead'; Invoke-TestGit $f.Path @('add','ahead.txt')|Out-Null; Invoke-TestGit $f.Path @('commit','-m','ahead')|Out-Null; $r=Invoke-Fixture $f; Assert-True (-not (Has-Blocked $r 'git.baseline-ancestor')) 'Valid ancestry was blocked.' }
    Add-Test '11 baseline mismatch' { $f=New-Fixture -Parent (Join-Path $tempRoot 'mismatch'); $a=Get-Arguments $f; $a.ExpectedBaseline='0'*40; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'git.baseline-exists') 'Missing baseline was accepted.' }
    Add-Test '12 divergent history' { $f=New-Fixture -Parent (Join-Path $tempRoot 'diverge'); Invoke-TestGit $f.Path @('switch','--orphan','unrelated')|Out-Null; Set-Content (Join-Path $f.Path 'other.txt') 'other'; Invoke-TestGit $f.Path @('add','--all')|Out-Null; Invoke-TestGit $f.Path @('commit','-m','unrelated')|Out-Null; Invoke-TestGit $f.Path @('branch','-M','phase-test')|Out-Null; $r=Invoke-Fixture $f; Assert-True (Has-Blocked $r 'git.baseline-ancestor') 'Divergent history was accepted.' }
    Add-Test '13 dirty tree with clean enforcement' { $f=New-Fixture -Parent (Join-Path $tempRoot 'dirty'); Set-Content (Join-Path $f.Path 'dirty.txt') 'dirty'; $a=Get-Arguments $f; $a.RequireCleanWorkingTree=$true; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'git.working-tree') 'Dirty tree was accepted.' }
    Add-Test '14 missing required session field' { $f=New-Fixture -Parent (Join-Path $tempRoot 'missing'); $a=Get-Arguments $f; $a.AgentName=' '; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'session.agent') 'Missing agent name was accepted.' }
    Add-Test '15 invalid capability level' { $f=New-Fixture -Parent (Join-Path $tempRoot 'capability'); $a=Get-Arguments $f; $a.CapabilityLevel='L9'; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'session.enum.capability') 'Invalid capability was accepted.' }
    Add-Test '16 invalid composition mode' { $f=New-Fixture -Parent (Join-Path $tempRoot 'composition'); $a=Get-Arguments $f; $a.CompositionMode='sequential-implementation'; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'session.enum.composition') 'Invalid composition mode was accepted.' }
    Add-Test '17 malformed manifest' { $f=New-Fixture -Parent (Join-Path $tempRoot 'malformed'); $path=Join-Path $f.Path 'manifest.json'; Set-Content $path '{bad'; $a=Get-Arguments $f; $a.ManifestPath=$path; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True ($r.InvocationError -and (Has-Blocked $r 'manifest.json')) 'Malformed manifest was accepted.' }
    Add-Test '18 manifest branch mismatch' { $f=New-Fixture -Parent (Join-Path $tempRoot 'manifestbranch'); $path=Join-Path $f.Path 'manifest.json'; New-ManifestObject $f -Branch 'wrong' | ConvertTo-Json -Depth 10 | Set-Content $path; $a=Get-Arguments $f; $a.ManifestPath=$path; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'manifest.match.git.working_branch') 'Manifest branch mismatch was accepted.' }
    Add-Test '19 manifest baseline mismatch' { $f=New-Fixture -Parent (Join-Path $tempRoot 'manifestbaseline'); $path=Join-Path $f.Path 'manifest.json'; New-ManifestObject $f -Baseline ('0'*40) | ConvertTo-Json -Depth 10 | Set-Content $path; $a=Get-Arguments $f; $a.ManifestPath=$path; $r=Invoke-HiveMindGovernancePreflight @a; Assert-True (Has-Blocked $r 'manifest.match.git.expected_baseline') 'Manifest baseline mismatch was accepted.' }
    Add-Test '20 human-readable output behavior' { $f=New-Fixture -Parent (Join-Path $tempRoot 'human'); $script=Join-Path $governanceRoot 'Invoke-HiveMindGovernancePreflight.ps1'; $a=Get-Arguments $f; $out=& $script @a; Assert-True (($out -join "`n") -match '\[PASS\]' -and ($out -join "`n") -match 'Overall: PASS') 'Human output lacks required status.' }
    Add-Test '21 valid JSON output' { $f=New-Fixture -Parent (Join-Path $tempRoot 'json'); $script=Join-Path $governanceRoot 'Invoke-HiveMindGovernancePreflight.ps1'; $a=Get-Arguments $f; $a.Json=$true; $out=& $script @a; $parsed=$out|ConvertFrom-Json; Assert-True ($parsed.OverallResult -eq 'PASS') 'JSON output did not parse as PASS.' }
    Add-Test '22 expected exit-code behavior' { $f=New-Fixture -Parent (Join-Path $tempRoot 'exit'); $script=Join-Path $governanceRoot 'Invoke-HiveMindGovernancePreflight.ps1'; $a=Get-Arguments $f; & $script @a | Out-Null; Assert-True ($LASTEXITCODE -eq 0) 'Passing exit code was not 0.'; $a.ExpectedBranch='wrong'; & $script @a | Out-Null; Assert-True ($LASTEXITCODE -eq 2) 'Blocking exit code was not 2.'; $a.ExpectedBranch='phase-test'; $bad=Join-Path $f.Path 'bad.json'; Set-Content $bad '{'; $a.ManifestPath=$bad; & $script @a | Out-Null; Assert-True ($LASTEXITCODE -eq 3) 'Malformed-input exit code was not 3.' }
}
finally { if(Test-Path -LiteralPath $tempRoot){ Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue } }

$passed=@($results|Where-Object Status -eq 'PASS').Count; $failed=@($results|Where-Object Status -eq 'FAIL').Count
$results | Format-Table -AutoSize
"Self-test total: $($results.Count) | Passed: $passed | Failed: $failed"
if($failed -gt 0){$results|Where-Object Status -eq 'FAIL'|ForEach-Object{"FAILDETAIL $($_.Name): $($_.Detail)"}}
if($failed -gt 0){exit 1}; exit 0
