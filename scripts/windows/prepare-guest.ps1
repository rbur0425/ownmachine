# Runs only in the disposable guest during specialize, as SYSTEM.
$ErrorActionPreference = 'Stop'
$media = (Get-Volume | Where-Object FileSystemLabel -eq 'OWNBOOT').DriveLetter
if (-not $media) { throw 'Bootstrap media missing' }
$seed = "${media}:\"
$cfg = Get-Content (Join-Path $seed 'guest.json') -Raw | ConvertFrom-Json
$root = $cfg.install_root
New-Item -ItemType Directory -Force $root | Out-Null
& icacls.exe $root /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
try {
    foreach ($name in @($cfg.desktop_user,$cfg.setup_user)) {
        if (Get-LocalUser -Name $name -ErrorAction SilentlyContinue) { throw 'Guest account already exists; refusing replay' }
        $value = if ($name -eq $cfg.desktop_user) { $cfg.desktop_password } else { $cfg.setup_password }
        New-LocalUser -Name $name -Password (ConvertTo-SecureString $value -AsPlainText -Force) -Description 'OwnMachine Windows workspace' | Out-Null
    }
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $cfg.desktop_user
    Add-LocalGroupMember -SID 'S-1-5-32-544' -Member $cfg.setup_user
    # Driver archive was digest- and Sigstore-verified by the operator before seeding.
    $zip = Join-Path $seed 'driver.zip'
    if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cfg.driver_sha256) { throw 'Driver hash mismatch' }
    Expand-Archive $zip (Join-Path $root 'driver') -Force
    $driver = (Get-ChildItem (Join-Path $root 'driver') -Recurse -Filter cua-driver.exe | Select-Object -First 1).FullName
    if (-not $driver -or (Get-AuthenticodeSignature $driver).Status -ne 'Valid') { throw 'Signed driver missing' }
    [Environment]::SetEnvironmentVariable('CUA_DRIVER_RS_TELEMETRY_ENABLED','0','Machine')
    [Environment]::SetEnvironmentVariable('CUA_DRIVER_PERMISSION_MODE','standard','Machine')
    foreach ($file in @('guest-health.ps1','guest-agent-entry.ps1','setup-entry.ps1')) { Copy-Item (Join-Path $seed $file) (Join-Path $root $file) }
    Copy-Item (Join-Path $root 'guest-health.ps1') (Join-Path $root 'health.ps1')
    [ordered]@{user=$cfg.desktop_user; setup_user=$cfg.setup_user; driver=($driver -replace '\\','/'); task_prefix=$cfg.task_prefix; driver_sha256=(Get-FileHash $driver -Algorithm SHA256).Hash} | ConvertTo-Json | Set-Content (Join-Path $root 'health-config.json') -Encoding utf8
    $pending = Join-Path $root 'bootstrap'
    New-Item -ItemType Directory -Force $pending | Out-Null
    & icacls.exe $pending /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
    foreach ($file in @('guest.json','guest-host','guest-host.pub','guest.pub','guest-setup.pub','finish-guest.ps1')) {
        Copy-Item (Join-Path $seed $file) (Join-Path $pending $file)
    }
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $pending 'finish-guest.ps1') + '"')
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $cfg.desktop_user
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount
    Register-ScheduledTask -TaskName ($cfg.task_prefix+'Bootstrap') -Action $action -Trigger $trigger -Principal $principal | Out-Null
    [ordered]@{stage='awaiting_first_signin'} | ConvertTo-Json | Set-Content (Join-Path $root 'bootstrap-status.json') -Encoding utf8
} catch {
    [ordered]@{stage='failed';message=$_.Exception.Message} | ConvertTo-Json | Set-Content (Join-Path $root 'bootstrap-status.json') -Encoding utf8
    throw
}
