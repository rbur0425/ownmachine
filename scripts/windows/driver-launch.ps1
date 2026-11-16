# Scheduled only as the standard interactive user, never SYSTEM or Highest.
$ErrorActionPreference = 'Stop'
$cfg = Get-Content (Join-Path $PSScriptRoot 'health-config.json') -Raw | ConvertFrom-Json
if (-not (Test-Path (Join-Path $PSScriptRoot 'hardened.json'))) { throw 'guest_not_hardened' }
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $cfg.driver
$start.Arguments = 'serve'
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $start
try {
    if (-not $process.Start()) { throw 'driver_start_failed' }
    $process.WaitForExit()
    exit $process.ExitCode
} finally { $process.Dispose() }
