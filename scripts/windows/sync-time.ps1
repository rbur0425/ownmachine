# Narrow, repeatable setup operation; no guest shell or caller-supplied arguments.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
. (Join-Path $root 'bootstrap-progress.ps1')
$mutex = New-Object Threading.Mutex($false,'Global\OwnMachineBootstrapTime')
$locked = $false
function Invoke-TimeCommand([string]$Executable,[string]$Arguments) {
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = Join-Path $env:WINDIR ('System32\' + $Executable)
    $start.Arguments = $Arguments
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(20000)) { $process.Kill(); throw 'time_command_timeout' }
        if ($process.ExitCode -ne 0) { throw 'time_command_failed' }
    } finally { $process.Dispose() }
}
try {
    $locked = $mutex.WaitOne(0)
    if (-not $locked) { throw 'time_sync_already_running' }
    $status = Get-Content (Join-Path $root 'bootstrap-status.json') -Raw | ConvertFrom-Json
    if ($status.stage -notin @('clock_sync_pending','awaiting_time_sync')) { throw 'time_sync_retry_not_ready' }
    $cfg = Get-Content (Join-Path $root 'time-config.json') -Raw | ConvertFrom-Json
    $peers = @($cfg.time_servers)
    if ($peers.Count -lt 1 -or $peers.Count -gt 5) { throw 'invalid_time_servers' }
    foreach ($peer in $peers) {
        if ($peer -isnot [string] -or $peer.Length -gt 253 -or $peer -notmatch '^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$') { throw 'invalid_time_servers' }
    }
    Write-BootstrapProgress 'synchronizing_clock'
    try {
        Set-TimeZone -Id $cfg.time_zone
        # Workgroup trigger defaults otherwise leave W32Time stopped.
        Invoke-TimeCommand 'sc.exe' 'triggerinfo w32time delete'
        Set-Service W32Time -StartupType Automatic
        Start-Service W32Time
        $peerList = ($peers | ForEach-Object { $_ + ',0x8' }) -join ' '
        Invoke-TimeCommand 'w32tm.exe' ('/config /manualpeerlist:"' + $peerList + '" /syncfromflags:manual /update')
        # No /nowait: success must wait for the resynchronization operation.
        Invoke-TimeCommand 'w32tm.exe' '/resync /rediscover'
        Write-BootstrapProgress 'configured'
        [ordered]@{ok=$true;configured=$true;time_synchronized=$true} | ConvertTo-Json -Compress
    } catch {
        Write-BootstrapProgress 'awaiting_time_sync'
        [ordered]@{ok=$false;configured=$false;code='windows_time_sync_required'} | ConvertTo-Json -Compress
    }
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
