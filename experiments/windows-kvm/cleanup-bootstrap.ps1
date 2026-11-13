# Run only inside the disposable guest after bootstrap completion.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:ProgramData 'OwnMachineSpike'
$status = Get-Content (Join-Path $root 'bootstrap-status.json') -Raw | ConvertFrom-Json
if ($status.stage -ne 'configured') { throw 'Bootstrap incomplete; refusing cleanup' }
$winlogon = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $winlogon -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $winlogon -Name DefaultPassword -ErrorAction SilentlyContinue
Remove-ItemProperty $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName OwnMachineSpikeBootstrap -Confirm:$false
Remove-Item (Join-Path $root 'bootstrap') -Recurse -Force
# These exact cached answer files were generated for this fresh disposable VM.
foreach ($path in @('Panther\unattend.xml','Panther\Unattend\unattend.xml','System32\Sysprep\unattend.xml')) {
    Remove-Item (Join-Path $env:WINDIR $path) -Force -ErrorAction SilentlyContinue
}
[ordered]@{autologon_disabled=((Get-ItemProperty $winlogon).AutoAdminLogon -eq '0');bootstrap_removed=(-not(Test-Path (Join-Path $root 'bootstrap')))} | ConvertTo-Json
