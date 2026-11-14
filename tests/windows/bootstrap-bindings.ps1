# Run with Windows PowerShell. Execute the actual argument expressions against
# strict stubs: parser-only checks do not catch split dynamic parameter values.
param([string]$PrepareSource, [string]$FinishSource)
$ErrorActionPreference = 'Stop'
$cfg = @{task_prefix='PortablePrefix'; host_address='192.0.2.1'}
$action=$trigger=$principal=$settings=$null
$script:names = [System.Collections.Generic.List[string]]::new()
function Register-ScheduledTask {
    [CmdletBinding()]param([string]$TaskName,$Action,$Trigger,$Principal,$Settings)
    $script:names.Add($TaskName)
}
function Disable-ScheduledTask {
    [CmdletBinding()]param([string]$TaskName)
    $script:names.Add($TaskName)
}
function New-NetFirewallRule {
    [CmdletBinding()]param([string]$Name,[string]$DisplayName,$Direction,$Protocol,$LocalPort,$RemoteAddress,$Action,$Profile)
    if($Name -ne $DisplayName){throw 'Firewall labels differ'}
    $script:names.Add($Name)
}
foreach($source in @($PrepareSource,$FinishSource)) {
    foreach($line in ($source -split "`n")) {
        if($line.Trim() -match '^(Register-ScheduledTask|Disable-ScheduledTask|New-NetFirewallRule) ') {
            Invoke-Expression $line
        }
    }
}
$expected = 'PortablePrefixBootstrap,PortablePrefixSSH,PortablePrefixDriver,PortablePrefixDriver,PortablePrefixBootstrap'
if(($script:names -join ',') -ne $expected){throw 'Unexpected bootstrap names or commands'}
'Bootstrap parameter-binding regression passed (five real command expressions; no system changes).'
