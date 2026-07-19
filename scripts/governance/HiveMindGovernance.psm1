Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Roles = @('primary-implementer','independent-auditor-hardener','specialist-contributor','read-only-scout','integration-composer','human-project-owner')
$script:Capabilities = @('L0','L1','L2','L3','L4')
$script:CompositionModes = @('sequential-isolated','sequential-audit','parallel-read-only','parallel-isolated','integration-composition','adversarial-verification')
$script:WriteAuthorities = @('none','documentation-only','tests-only','bounded-path-write','full-locked-phase-scope')

function New-GovernanceCheck {
    param([string]$Id,[string]$Category,[ValidateSet('PASS','WARNING','BLOCKED')][string]$Status,[string]$Message,[AllowNull()]$Expected,[AllowNull()]$Actual,[AllowNull()]$Evidence)
    [pscustomobject][ordered]@{ CheckIdentifier=$Id; Category=$Category; Status=$Status; Severity=if($Status -eq 'BLOCKED'){'Error'}elseif($Status -eq 'WARNING'){'Warning'}else{'Information'}; Message=$Message; Expected=$Expected; Actual=$Actual; Evidence=$Evidence }
}

function Invoke-GovernanceGit {
    param([string]$RepositoryPath,[string[]]$Arguments,[switch]$AllowFailure)
    $output = & git -C $RepositoryPath @Arguments
    $exitCode = $LASTEXITCODE
    if (-not $AllowFailure -and $exitCode -ne 0) { throw "git $($Arguments[0]) failed (exit $exitCode): $($output -join ' ')" }
    [pscustomobject]@{ ExitCode=$exitCode; Output=@($output | ForEach-Object { "$_" }) }
}

function ConvertTo-NormalizedPath {
    param([Parameter(Mandatory)][string]$Path)
    [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]@([System.IO.Path]::DirectorySeparatorChar,[System.IO.Path]::AltDirectorySeparatorChar)).Replace('\','/')
}

function ConvertTo-NormalizedRemote {
    param([Parameter(Mandatory)][string]$Remote)
    $value = $Remote.Trim()
    if ($value -match '^git@github\.com:(?<repo>.+?)(?:\.git)?$') { return ('github.com/' + $Matches.repo.TrimEnd('/')).ToLowerInvariant() }
    if ($value -match '^ssh://git@github\.com/(?<repo>.+?)(?:\.git)?/?$') { return ('github.com/' + $Matches.repo.TrimEnd('/')).ToLowerInvariant() }
    try {
        $uri = [Uri]$value
        $path = $uri.AbsolutePath.Trim('/'); if ($path.EndsWith('.git',[StringComparison]::OrdinalIgnoreCase)) { $path=$path.Substring(0,$path.Length-4) }
        return ($uri.Host.ToLowerInvariant() + '/' + $path.ToLowerInvariant())
    } catch { return $value.TrimEnd('/').TrimEnd('.git').ToLowerInvariant() }
}

function Get-ObjectProperty {
    param([AllowNull()]$Object,[string]$Name)
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    $property.Value
}

function Test-RequiredValue {
    param([System.Collections.Generic.List[object]]$Checks,[string]$Id,[string]$Category,[string]$Name,[AllowNull()]$Value)
    $missing = $null -eq $Value -or ($Value -is [string] -and [string]::IsNullOrWhiteSpace($Value))
    $Checks.Add((New-GovernanceCheck $Id $Category $(if($missing){'BLOCKED'}else{'PASS'}) $(if($missing){"Required value '$Name' is missing."}else{"Required value '$Name' is present."}) 'non-empty' $Value $null))
}

function Test-Manifest {
    param([System.Collections.Generic.List[object]]$Checks,[string]$ManifestPath,[hashtable]$Expected)
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) { $Checks.Add((New-GovernanceCheck 'manifest.file' 'Manifest' 'BLOCKED' 'Manifest file does not exist.' $ManifestPath $null $null)); return $true }
    try { $manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json -ErrorAction Stop }
    catch { $Checks.Add((New-GovernanceCheck 'manifest.json' 'Manifest' 'BLOCKED' 'Manifest is not valid JSON.' 'valid JSON' $null $_.Exception.Message)); return $true }
    $required = @(
        @('manifest_version',(Get-ObjectProperty $manifest 'manifest_version')),
        @('contract_version',(Get-ObjectProperty $manifest 'contract_version')),
        @('project',(Get-ObjectProperty $manifest 'project')),
        @('phase',(Get-ObjectProperty $manifest 'phase')),
        @('agent',(Get-ObjectProperty $manifest 'agent')),
        @('authority',(Get-ObjectProperty $manifest 'authority')),
        @('git',(Get-ObjectProperty $manifest 'git')),
        @('contribution',(Get-ObjectProperty $manifest 'contribution')),
        @('validation',(Get-ObjectProperty $manifest 'validation')),
        @('reporting',(Get-ObjectProperty $manifest 'reporting')),
        @('handoff',(Get-ObjectProperty $manifest 'handoff'))
    )
    foreach($item in $required){ Test-RequiredValue $Checks "manifest.required.$($item[0])" 'Manifest' $item[0] $item[1] }
    $project=Get-ObjectProperty $manifest 'project'; $phase=Get-ObjectProperty $manifest 'phase'; $agent=Get-ObjectProperty $manifest 'agent'; $authority=Get-ObjectProperty $manifest 'authority'; $git=Get-ObjectProperty $manifest 'git'
    foreach($name in @('name','parent_label','repository_root','remote_url')){ Test-RequiredValue $Checks "manifest.required.project.$name" 'Manifest' "project.$name" (Get-ObjectProperty $project $name) }
    foreach($name in @('id','name','status_at_start','status_at_end','paused_tracks')){ Test-RequiredValue $Checks "manifest.required.phase.$name" 'Manifest' "phase.$name" (Get-ObjectProperty $phase $name) }
    foreach($name in @('name','assigned_role','capability_level','composition_mode')){ Test-RequiredValue $Checks "manifest.required.agent.$name" 'Manifest' "agent.$name" (Get-ObjectProperty $agent $name) }
    foreach($name in @('write_authority','owned_paths','read_only_paths','forbidden_paths')){ Test-RequiredValue $Checks "manifest.required.authority.$name" 'Manifest' "authority.$name" (Get-ObjectProperty $authority $name) }
    foreach($name in @('expected_baseline','actual_baseline','merge_base','working_branch','input_commit','output_commit','earlier_commits_preserved','destructive_operations_used')){ Test-RequiredValue $Checks "manifest.required.git.$name" 'Manifest' "git.$name" (Get-ObjectProperty $git $name) }
    $comparisons=@(
        @('repository_root',(Get-ObjectProperty $project 'repository_root'),$Expected.RepositoryPath,'path'),
        @('remote_url',(Get-ObjectProperty $project 'remote_url'),$Expected.Remote,'remote'),
        @('phase.id',(Get-ObjectProperty $phase 'id'),$Expected.Phase,'text'),
        @('agent.name',(Get-ObjectProperty $agent 'name'),$Expected.AgentName,'text'),
        @('agent.assigned_role',(Get-ObjectProperty $agent 'assigned_role'),$Expected.AgentRole,'text'),
        @('agent.capability_level',(Get-ObjectProperty $agent 'capability_level'),$Expected.Capability,'text'),
        @('agent.composition_mode',(Get-ObjectProperty $agent 'composition_mode'),$Expected.CompositionMode,'text'),
        @('authority.write_authority',(Get-ObjectProperty $authority 'write_authority'),$Expected.WriteAuthority,'text'),
        @('git.expected_baseline',(Get-ObjectProperty $git 'expected_baseline'),$Expected.Baseline,'text'),
        @('git.working_branch',(Get-ObjectProperty $git 'working_branch'),$Expected.Branch,'text')
    )
    foreach($comparison in $comparisons){
        $actual=$comparison[1]; $expectedValue=$comparison[2]
        $equal = if($comparison[3] -eq 'path' -and $actual){(ConvertTo-NormalizedPath $actual) -ieq (ConvertTo-NormalizedPath $expectedValue)}elseif($comparison[3] -eq 'remote' -and $actual){(ConvertTo-NormalizedRemote $actual) -eq (ConvertTo-NormalizedRemote $expectedValue)}else{"$actual" -ceq "$expectedValue"}
        $Checks.Add((New-GovernanceCheck "manifest.match.$($comparison[0])" 'Manifest' $(if($equal){'PASS'}else{'BLOCKED'}) $(if($equal){"Manifest $($comparison[0]) matches."}else{"Manifest $($comparison[0]) conflicts with the session."}) $expectedValue $actual $null))
    }
    foreach($name in @('objective','summary','changed_files','added_files','deleted_files','renamed_files','diff_statistics','scope_deviations')){ Test-RequiredValue $Checks "manifest.required.contribution.$name" 'Manifest' "contribution.$name" (Get-ObjectProperty (Get-ObjectProperty $manifest 'contribution') $name) }
    foreach($name in @('commands','outcomes','tests_not_run','evidence_limitations')){ Test-RequiredValue $Checks "manifest.required.validation.$name" 'Manifest' "validation.$name" (Get-ObjectProperty (Get-ObjectProperty $manifest 'validation') $name) }
    foreach($name in @('assumptions','known_limitations','blockers')){ Test-RequiredValue $Checks "manifest.required.reporting.$name" 'Manifest' "reporting.$name" (Get-ObjectProperty (Get-ObjectProperty $manifest 'reporting') $name) }
    foreach($name in @('recommended_next_actor','recommended_next_role','required_follow_up','safe_to_compose','safe_to_push','safe_to_open_pr','independently_audited','hardened','pushed','pr_opened','merged','local_main_normalized','working_tree_clean')){ Test-RequiredValue $Checks "manifest.required.handoff.$name" 'Manifest' "handoff.$name" (Get-ObjectProperty (Get-ObjectProperty $manifest 'handoff') $name) }
    return $false
}

function Invoke-HiveMindGovernancePreflight {
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
        [switch]$DisableCanonicalPathEnforcement
    )
    $checks=[System.Collections.Generic.List[object]]::new(); $invocationError=$false
    $resolved=$null
    try { $resolved=ConvertTo-NormalizedPath $RepositoryPath } catch { $checks.Add((New-GovernanceCheck 'repository.path.resolve' 'Repository' 'BLOCKED' 'Repository path cannot be resolved.' $RepositoryPath $null $_.Exception.Message)); $invocationError=$true }
    $exists=$resolved -and (Test-Path -LiteralPath $resolved -PathType Container)
    $checks.Add((New-GovernanceCheck 'repository.path.exists' 'Repository' $(if($exists){'PASS'}else{'BLOCKED'}) $(if($exists){'Repository path exists.'}else{'Repository path does not exist.'}) 'existing directory' $resolved $null))
    if($resolved){
        $oneDrive=$resolved -match '(?i)(^|/)OneDrive(/|$)'; $checks.Add((New-GovernanceCheck 'repository.path.onedrive' 'Repository' $(if($oneDrive){'BLOCKED'}else{'PASS'}) $(if($oneDrive){'OneDrive repository paths are forbidden.'}else{'Repository path is outside OneDrive.'}) 'outside OneDrive' $resolved $null))
        $folder=Split-Path -Leaf $resolved; $checks.Add((New-GovernanceCheck 'repository.folder' 'Repository' $(if($folder -ceq 'hive-mind'){'PASS'}else{'BLOCKED'}) 'Repository folder must be named exactly hive-mind.' 'hive-mind' $folder $null))
        if(-not $DisableCanonicalPathEnforcement){ $canonical=ConvertTo-NormalizedPath $CanonicalRepositoryPath; $checks.Add((New-GovernanceCheck 'repository.canonical-path' 'Repository' $(if($resolved -ieq $canonical){'PASS'}else{'BLOCKED'}) 'Repository must match the canonical path.' $canonical $resolved $null)) }
    }
    foreach($field in @(@('phase',$CurrentPhase),@('branch',$ExpectedBranch),@('baseline',$ExpectedBaseline),@('agent',$AgentName),@('role',$AgentRole),@('capability',$CapabilityLevel),@('composition',$CompositionMode),@('write-authority',$WriteAuthority))){ Test-RequiredValue $checks "session.$($field[0])" 'Session' $field[0] $field[1] }
    foreach($enum in @(@('role',$AgentRole,$script:Roles),@('capability',$CapabilityLevel,$script:Capabilities),@('composition',$CompositionMode,$script:CompositionModes),@('write-authority',$WriteAuthority,$script:WriteAuthorities))){ $valid=$enum[2] -ccontains $enum[1]; $checks.Add((New-GovernanceCheck "session.enum.$($enum[0])" 'Session' $(if($valid){'PASS'}else{'BLOCKED'}) "Session $($enum[0]) must use a Phase 38A value." ($enum[2] -join ', ') $enum[1] $null)) }
    $phaseLock=$Phase36KStatus -ceq 'paused-and-untouched'; $checks.Add((New-GovernanceCheck 'session.phase36k' 'Session' $(if($phaseLock){'PASS'}else{'BLOCKED'}) 'Phase 36K must remain paused and untouched.' 'paused-and-untouched' $Phase36KStatus $null))
    if($ExpectedBranch -ceq 'main'){ $checks.Add((New-GovernanceCheck 'git.feature-branch' 'Git' 'BLOCKED' 'A feature contribution cannot use main.' 'non-main branch' $ExpectedBranch $null)) }
    if($exists){
        $inside=Invoke-GovernanceGit $resolved @('rev-parse','--is-inside-work-tree') -AllowFailure
        $isGit=$inside.ExitCode -eq 0 -and $inside.Output[0] -eq 'true'; $checks.Add((New-GovernanceCheck 'repository.git' 'Repository' $(if($isGit){'PASS'}else{'BLOCKED'}) 'Repository must be a Git working tree.' 'true' $(if($inside.Output.Count){$inside.Output[0]}else{$null}) ($inside.Output -join ' ')))
        if($isGit){
            $top=(Invoke-GovernanceGit $resolved @('rev-parse','--show-toplevel')).Output[0]; $topNorm=ConvertTo-NormalizedPath $top; $checks.Add((New-GovernanceCheck 'repository.top-level' 'Repository' $(if($topNorm -ieq $resolved){'PASS'}else{'BLOCKED'}) 'Git top-level must equal the supplied repository path.' $resolved $topNorm $null))
            $remoteResult=Invoke-GovernanceGit $resolved @('remote','get-url','origin') -AllowFailure; $actualRemote=if($remoteResult.ExitCode -eq 0){$remoteResult.Output[0]}else{$null}; $remoteOk=$actualRemote -and (ConvertTo-NormalizedRemote $actualRemote) -eq (ConvertTo-NormalizedRemote $ExpectedRemote); $checks.Add((New-GovernanceCheck 'repository.remote' 'Repository' $(if($remoteOk){'PASS'}else{'BLOCKED'}) 'Origin must match the expected repository.' $ExpectedRemote $actualRemote $(if($actualRemote){ConvertTo-NormalizedRemote $actualRemote}else{$remoteResult.Output -join ' '})))
            $branchResult=Invoke-GovernanceGit $resolved @('symbolic-ref','--quiet','--short','HEAD') -AllowFailure; $branch=if($branchResult.ExitCode -eq 0){$branchResult.Output[0]}else{$null}; $checks.Add((New-GovernanceCheck 'git.detached-head' 'Git' $(if($branch){'PASS'}else{'BLOCKED'}) $(if($branch){'HEAD is attached.'}else{'HEAD is detached.'}) 'attached HEAD' $branch $null)); $checks.Add((New-GovernanceCheck 'git.branch' 'Git' $(if($branch -ceq $ExpectedBranch){'PASS'}else{'BLOCKED'}) 'Current branch must match the expected branch.' $ExpectedBranch $branch $null))
            $baselineFormat=$ExpectedBaseline -match '^[0-9a-fA-F]{40}$'; $checks.Add((New-GovernanceCheck 'git.baseline-format' 'Git' $(if($baselineFormat){'PASS'}else{'BLOCKED'}) 'Expected baseline must be a full 40-character commit id.' '40 hexadecimal characters' $ExpectedBaseline $null))
            $baselineExists=$false; if($baselineFormat){ $cat=Invoke-GovernanceGit $resolved @('cat-file','-e',"$ExpectedBaseline`^{commit}") -AllowFailure; $baselineExists=$cat.ExitCode -eq 0 }; $checks.Add((New-GovernanceCheck 'git.baseline-exists' 'Git' $(if($baselineExists){'PASS'}else{'BLOCKED'}) 'Expected baseline must exist as a commit.' $ExpectedBaseline $(if($baselineExists){$ExpectedBaseline}else{$null}) $null))
            if($baselineExists){
                $ancestor=Invoke-GovernanceGit $resolved @('merge-base','--is-ancestor',$ExpectedBaseline,'HEAD') -AllowFailure; $checks.Add((New-GovernanceCheck 'git.baseline-ancestor' 'Git' $(if($ancestor.ExitCode -eq 0){'PASS'}else{'BLOCKED'}) 'Branch must descend from the expected baseline.' $ExpectedBaseline $(if($ancestor.ExitCode -eq 0){'ancestor'}else{'not ancestor'}) $null))
                $merge=Invoke-GovernanceGit $resolved @('merge-base','HEAD',$ExpectedBaseline) -AllowFailure; $mergeValue=if($merge.ExitCode -eq 0){$merge.Output[0]}else{$null}; $checks.Add((New-GovernanceCheck 'git.merge-base' 'Git' $(if($mergeValue -ceq $ExpectedBaseline){'PASS'}else{'BLOCKED'}) 'Merge-base must equal the expected baseline.' $ExpectedBaseline $mergeValue $null))
                $counts=Invoke-GovernanceGit $resolved @('rev-list','--left-right','--count',"$ExpectedBaseline...HEAD"); $parts=$counts.Output[0] -split '\s+'; $behind=[int]$parts[0]; $ahead=[int]$parts[1]; $checks.Add((New-GovernanceCheck 'git.divergence' 'Git' $(if($behind -eq 0){'PASS'}else{'BLOCKED'}) 'Branch must not diverge behind the locked baseline.' 'behind=0' "behind=$behind;ahead=$ahead" $counts.Output[0])); if($ahead -eq 0){$checks.Add((New-GovernanceCheck 'git.ahead' 'Git' 'WARNING' 'Branch is zero commits ahead; implementation may not have started.' 'ahead>0 after implementation' 'ahead=0' $null))}
            }
            $status=(Invoke-GovernanceGit $resolved @('status','--porcelain','--untracked-files=all')).Output; $clean=$status.Count -eq 0; $checks.Add((New-GovernanceCheck 'git.working-tree' 'Git' $(if($RequireCleanWorkingTree -and -not $clean){'BLOCKED'}elseif($clean){'PASS'}else{'WARNING'}) $(if($clean){'Working tree is clean.'}elseif($RequireCleanWorkingTree){'Working tree is dirty and clean state is required.'}else{'Working tree is dirty but clean state was not required.'}) 'clean' $(if($clean){'clean'}else{$status -join '; '}) $null))
            $checks.Add((New-GovernanceCheck 'git.fetch-freshness' 'Git' 'WARNING' 'The validator does not fetch; remote-tracking references may be stale.' 'caller-managed fetch' 'not fetched' $null))
        }
    }
    if($ManifestPath){
        $manifestFull=[System.IO.Path]::GetFullPath($ManifestPath)
        if($resolved -and -not (ConvertTo-NormalizedPath $manifestFull).StartsWith($resolved + '/', [StringComparison]::OrdinalIgnoreCase)){
            $checks.Add((New-GovernanceCheck 'manifest.location' 'Manifest' 'BLOCKED' 'Manifest must be inside the repository.' "$resolved/" (ConvertTo-NormalizedPath $manifestFull) $null)); $invocationError=$true
        } else {
            $manifestExpected=@{RepositoryPath=$resolved;Remote=$ExpectedRemote;Phase=$CurrentPhase;AgentName=$AgentName;AgentRole=$AgentRole;Capability=$CapabilityLevel;CompositionMode=$CompositionMode;WriteAuthority=$WriteAuthority;Baseline=$ExpectedBaseline;Branch=$ExpectedBranch}
            $manifestInvalid=Test-Manifest -Checks $checks -ManifestPath $manifestFull -Expected $manifestExpected
            $invocationError=$manifestInvalid -or $invocationError
        }
    }
    $blocked=@($checks | Where-Object Status -eq 'BLOCKED').Count; $warnings=@($checks | Where-Object Status -eq 'WARNING').Count
    [pscustomobject][ordered]@{ OverallResult=if($blocked){'BLOCKED'}else{'PASS'}; BlockingFailureCount=$blocked; WarningCount=$warnings; InvocationError=[bool]$invocationError; Checks=@($checks); Metadata=[pscustomobject]@{RepositoryPath=$resolved;ExpectedBranch=$ExpectedBranch;ExpectedBaseline=$ExpectedBaseline;Phase=$CurrentPhase;Agent=$AgentName} }
}

Export-ModuleMember -Function Invoke-HiveMindGovernancePreflight,ConvertTo-NormalizedRemote
