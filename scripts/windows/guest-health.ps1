$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cfg = Get-Content (Join-Path $root 'health-config.json') -Raw | ConvertFrom-Json
$lines = @()
$ok = $false
# Native stderr/nonzero exit must not turn a stopped driver into an SSH failure.
try {
    $lines = & $cfg.driver status 2>$null
    $ok = $LASTEXITCODE -eq 0
} catch { $lines = @(); $ok = $false }
$text = $lines -join "`n"
$daemonPid = if ($text -match '(?m)^\s*pid:\s*(\d+)') { [int]$Matches[1] } else { 0 }
$process = if ($daemonPid) { Get-Process -Id $daemonPid -ErrorAction SilentlyContinue } else { $null }
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$standard = -not ($id.Groups.Value -contains 'S-1-5-32-544')
$userMatches = $id.Name.Split('\')[-1] -eq $cfg.user
[ordered]@{
 bootstrap_hardened=(Test-Path (Join-Path $root 'hardened.json'))
 guest_reachable=$true
 interactive_session=($null -ne $process -and $process.SessionId -gt 0)
 driver_running=($ok -and $text -match '^Cua Driver daemon is running')
 standard_mode=($text -match '(?m)^\s*permission mode: standard ')
 standard_user=($standard -and $userMatches)
} | ConvertTo-Json -Compress
