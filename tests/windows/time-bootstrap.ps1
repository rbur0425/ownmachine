# Exercise actual synchronization control flow with OS commands stubbed. No clock changes.
param([string]$SourceRoot = (Split-Path (Split-Path $PSScriptRoot)))
$ErrorActionPreference = 'Stop'
$fixture = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $fixture | Out-Null
$tokens=$errors=$null
$source = Get-Content (Join-Path $SourceRoot 'scripts/windows/sync-time.ps1') -Raw
$ast = [Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Time script parse failed' }
$fn = $ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-TimeCommand'},$true)
# Stub only the external-process boundary; execute the production state machine.
$source = $source.Remove($fn.Extent.StartOffset,$fn.Extent.EndOffset-$fn.Extent.StartOffset)
$source = $source.Replace('$root = $PSScriptRoot', '$root = $fixture')
Copy-Item (Join-Path $SourceRoot 'scripts/windows/bootstrap-progress.ps1') $fixture
@{time_zone='UTC';time_servers=@('time.example','192.0.2.4')} | ConvertTo-Json | Set-Content (Join-Path $fixture 'time-config.json')
function Set-TimeZone { param($Id) if($Id -ne 'UTC'){throw 'zone lost'} }
function Set-Service { param($Name,$StartupType) if($Name -ne 'W32Time' -or $StartupType -ne 'Automatic'){throw 'service policy lost'} }
function Start-Service { param($Name) }
function Invoke-TimeCommand {
    param($Executable,$Arguments)
    $script:calls.Add("$Executable $Arguments")
    if ($script:failSync -and $Arguments -eq '/resync /rediscover') { throw 'simulated network failure' }
}
function Assert-Stage($expected) {
    $actual = (Get-Content (Join-Path $fixture 'bootstrap-status.json') -Raw | ConvertFrom-Json).stage
    if ($actual -ne $expected) { throw "Expected $expected; got $actual" }
}
try {
    $root=$fixture
    . (Join-Path $fixture 'bootstrap-progress.ps1')
    $script:calls = [Collections.Generic.List[string]]::new()
    $script:failSync=$true
    Write-BootstrapProgress 'clock_sync_pending'
    $result = Invoke-Expression $source | ConvertFrom-Json
    if($result.ok){throw 'Failed sync was accepted'}
    Assert-Stage 'awaiting_time_sync'
    $script:failSync=$false
    $result = Invoke-Expression $source | ConvertFrom-Json
    if(-not $result.time_synchronized){throw 'Successful retry failed'}
    Assert-Stage 'configured'
    if(-not ($script:calls -contains 'w32tm.exe /config /manualpeerlist:"time.example,0x8 192.0.2.4,0x8" /syncfromflags:manual /update')){throw 'Peer configuration lost'}
    $count=$script:calls.Count
    $refused=$false
    try { Invoke-Expression $source | Out-Null } catch { $refused=$true }
    if(-not $refused -or $script:calls.Count -ne $count){throw 'Completed bootstrap was replayed'}
    Write-BootstrapProgress 'awaiting_time_sync'
    @{time_zone='UTC';time_servers=@('bad" /unsafe')} | ConvertTo-Json | Set-Content (Join-Path $fixture 'time-config.json')
    $refused=$false
    try { Invoke-Expression $source | Out-Null } catch { $refused=$true }
    if(-not $refused -or $script:calls.Count -ne $count){throw 'Unsafe peers reached native commands'}
    Assert-Stage 'awaiting_time_sync'
    # Parse every shipped guest script, including the read-only GUI.
    foreach($file in Get-ChildItem (Join-Path $SourceRoot 'scripts/windows') -Filter '*.ps1') {
        $tokens=$errors=$null
        [void][Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
        if($errors.Count){throw "Parse failed: $($file.Name)"}
    }
    & (Join-Path $SourceRoot 'tests/windows/progress-window.ps1') -SourceRoot $SourceRoot
    & (Join-Path $SourceRoot 'tests/windows/bootstrap-bindings.ps1') -PrepareSource (Get-Content (Join-Path $SourceRoot 'scripts/windows/prepare-guest.ps1') -Raw) -FinishSource (Get-Content (Join-Path $SourceRoot 'scripts/windows/finish-guest.ps1') -Raw)
    'Clock failure/retry, no replay, peer validation, checkpoint and script parser tests passed. OS effects were stubbed.'
} finally { Remove-Item $fixture -Recurse -Force }
