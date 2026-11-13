# Temporary administrator key: only fixed status, hardening and retirement.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cfg = Get-Content (Join-Path $root 'health-config.json') -Raw | ConvertFrom-Json
$operation = $env:SSH_ORIGINAL_COMMAND
if ($operation -notin @('ownmachine-guest status','ownmachine-guest harden','ownmachine-guest retire')) { throw 'unsupported_setup_operation' }
$status = Get-Content (Join-Path $root 'bootstrap-status.json') -Raw | ConvertFrom-Json
if ($operation -eq 'ownmachine-guest status') {
    [ordered]@{configured=($status.stage -eq 'configured'); hardened=(Test-Path (Join-Path $root 'hardened.json')); secure_boot=(Confirm-SecureBootUEFI); tpm_ready=(Get-Tpm).TpmReady; driver_signature=((Get-AuthenticodeSignature $cfg.driver).Status -eq 'Valid'); driver_unchanged=((Get-FileHash $cfg.driver -Algorithm SHA256).Hash -eq $cfg.driver_sha256)} | ConvertTo-Json -Compress
    exit 0
}
if ($status.stage -ne 'configured') { throw 'bootstrap_incomplete' }
if ($operation -eq 'ownmachine-guest harden') {
    if (Get-Volume | Where-Object FileSystemLabel -eq 'OWNBOOT') { throw 'eject_bootstrap_media_before_hardening' }
    $winlogon = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
    Set-ItemProperty $winlogon -Name AutoAdminLogon -Value '0'
    Remove-ItemProperty $winlogon -Name DefaultPassword -ErrorAction SilentlyContinue
    Remove-ItemProperty $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName ($cfg.task_prefix+'Bootstrap') -Confirm:$false -ErrorAction SilentlyContinue
    $pending = Join-Path $root 'bootstrap'
    if (Test-Path $pending) { Remove-Item $pending -Recurse -Force }
    $answers = @('Panther\unattend.xml','Panther\Unattend\unattend.xml','System32\Sysprep\unattend.xml')
    foreach ($path in $answers) {
        Remove-Item (Join-Path $env:WINDIR $path) -Force -ErrorAction SilentlyContinue
    }
    $login = Get-ItemProperty $winlogon
    if ($login.AutoAdminLogon -ne '0' -or $login.PSObject.Properties['DefaultPassword'] -or $login.PSObject.Properties['AutoLogonCount'] -or (Test-Path $pending)) { throw 'hardening_failed' }
    foreach ($path in $answers) { if (Test-Path (Join-Path $env:WINDIR $path)) { throw 'answer_file_cleanup_failed' } }
    $task = Get-ScheduledTask -TaskName ($cfg.task_prefix+'Driver')
    if ($task.Principal.RunLevel -ne 'Limited' -or $task.Principal.LogonType -ne 'Interactive') { throw 'unsafe_driver_task' }
    if (-not (Confirm-SecureBootUEFI) -or -not (Get-Tpm).TpmReady) { throw 'guest_platform_not_ready' }
    [ordered]@{bootstrap_removed=$true;autologon_disabled=$true} | ConvertTo-Json | Set-Content (Join-Path $root 'hardened.json') -Encoding utf8
    Enable-ScheduledTask -TaskName ($cfg.task_prefix+'Driver') | Out-Null
    Start-ScheduledTask -TaskName ($cfg.task_prefix+'Driver')
    [ordered]@{ok=$true;hardened=$true} | ConvertTo-Json -Compress
    exit 0
}
if (-not (Test-Path (Join-Path $root 'hardened.json'))) { throw 'hardening_required' }
$key = Join-Path $env:ProgramData ('ssh\'+$cfg.setup_user+'_authorized_keys')
Set-Content $key -Value '' -Encoding ascii
Disable-LocalUser -Name $cfg.setup_user
[ordered]@{retired=$true} | ConvertTo-Json | Set-Content (Join-Path $root 'setup-retired.json') -Encoding utf8
[ordered]@{ok=$true;retired=$true} | ConvertTo-Json -Compress
