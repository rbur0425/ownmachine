# Runs once as SYSTEM after the standard user's first sign-in.
$ErrorActionPreference = 'Stop'
$seed = $PSScriptRoot
$cfg = Get-Content (Join-Path $seed 'guest.json') -Raw | ConvertFrom-Json
$root = Split-Path $seed
$driver = (Get-ChildItem (Join-Path $root 'driver') -Recurse -Filter cua-driver.exe | Select-Object -First 1).FullName
try {
    # ACPI shutdown must be a cold stop, not Windows Fast Startup kernel resume.
    & powercfg.exe /hibernate off
    if ($LASTEXITCODE -ne 0) { throw 'Cannot disable hybrid shutdown' }
    $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
    if ($cap.State -ne 'Installed') { Add-WindowsCapability -Online -Name $cap.Name | Out-Null }
    $sshDir = Join-Path $env:ProgramData 'ssh'
    New-Item -ItemType Directory -Force $sshDir | Out-Null
    Copy-Item (Join-Path $seed 'guest-host') (Join-Path $sshDir 'ssh_host_ed25519_key')
    Copy-Item (Join-Path $seed 'guest-host.pub') (Join-Path $sshDir 'ssh_host_ed25519_key.pub')
    & icacls.exe (Join-Path $sshDir 'ssh_host_ed25519_key') /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
    $desktop = Get-LocalUser $cfg.desktop_user
    $setup = Get-LocalUser $cfg.setup_user
    foreach ($item in @(@($desktop,'guest.pub'),@($setup,'guest-setup.pub'))) {
        $keyPath = Join-Path $sshDir ($item[0].Name + '_authorized_keys')
        Get-Content (Join-Path $seed $item[1]) | Set-Content $keyPath -Encoding ascii
        & icacls.exe $keyPath /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' (('*'+$item[0].SID.Value)+':R') | Out-Null
    }
    $sshd = @"
Port 22
PubkeyAuthentication yes
PasswordAuthentication no
AllowUsers $($cfg.desktop_user) $($cfg.setup_user)
AuthorizedKeysFile __PROGRAMDATA__/ssh/%u_authorized_keys
AllowTcpForwarding no
AllowAgentForwarding no
PermitTTY no
Subsystem sftp sftp-server.exe
"@
    $sshd | Set-Content (Join-Path $sshDir 'sshd_config') -Encoding ascii
    & "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -A
    & "$env:WINDIR\System32\OpenSSH\sshd.exe" -t
    if ($LASTEXITCODE -ne 0) { throw 'Invalid SSH configuration' }
    Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue | Disable-NetFirewallRule
    New-NetFirewallRule -Name OwnMachineSpikeSSH -DisplayName OwnMachineSpikeSSH -Direction Inbound -Protocol TCP -LocalPort 22 -RemoteAddress $cfg.host_address -Action Allow -Profile Any | Out-Null
    Set-Service sshd -StartupType Automatic
    Start-Service sshd
    # Avoid upstream autostart's Highest setting. This task is explicitly limited.
    $action = New-ScheduledTaskAction -Execute $driver -Argument 'serve'
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $desktop.Name
    $principal = New-ScheduledTaskPrincipal -UserId $desktop.SID.Value -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName OwnMachineSpikeDriver -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Start-ScheduledTask -TaskName OwnMachineSpikeDriver
    # Supported browser first-run policy; no user browser profile copied.
    $edge = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge'
    New-Item -Force $edge | Out-Null
    New-ItemProperty $edge -Name HideFirstRunExperience -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty $edge -Name BrowserSignin -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty $edge -Name SyncDisabled -Value 1 -PropertyType DWord -Force | Out-Null
    Disable-ScheduledTask -TaskName OwnMachineSpikeBootstrap | Out-Null
    [ordered]@{stage='configured';driver=$driver;desktop_sid=$desktop.SID.Value;ssh_password_auth=$false;driver_elevated=$false} | ConvertTo-Json | Set-Content (Join-Path $root 'bootstrap-status.json') -Encoding utf8
} catch {
    [ordered]@{stage='failed';message=$_.Exception.Message} | ConvertTo-Json | Set-Content (Join-Path $root 'bootstrap-status.json') -Encoding utf8
    throw
}
