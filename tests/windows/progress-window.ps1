# Execute the actual timer callback with a stub window; no GUI or system changes.
param([string]$SourceRoot = (Split-Path (Split-Path $PSScriptRoot)))
$ErrorActionPreference='Stop'
$root=Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $root | Out-Null
$tokens=$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $SourceRoot 'scripts/windows/show-setup-progress.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Progress parser failure'}
$call=$ast.Find({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Member.Value -eq 'Add_Tick'},$true)
$tick=$call.Arguments[0].ScriptBlock.GetScriptBlock()
$form=[pscustomobject]@{Closed=$false}
$form | Add-Member ScriptMethod Close { $this.Closed=$true }
$text=[pscustomobject]@{Text=''}
$messages=@{installing_openssh='Installing';awaiting_time_sync='Check time';failed='Inspect failure'}
try {
    foreach($phase in @('installing_openssh','awaiting_time_sync','failed','configured')) {
        $form.Closed=$false
        @{stage=$phase} | ConvertTo-Json | Set-Content (Join-Path $root 'bootstrap-status.json')
        & $tick
        if($form.Closed -ne ($phase -eq 'configured')){throw "Incorrect window lifetime at $phase"}
    }
    # Hardening must close even if an older checkpoint is unreadable or stale.
    Set-Content (Join-Path $root 'bootstrap-status.json') 'invalid json'
    $form.Closed=$false
    & $tick
    if($form.Closed){throw 'Unreadable progress hid a setup problem'}
    Set-Content (Join-Path $root 'hardened.json') '{}'
    & $tick
    if(-not $form.Closed){throw 'Hardened guest retained progress window'}
    'Actual progress callback closes on configured/hardened, preserves waiting/failure states.'
} finally { Remove-Item $root -Recurse -Force }
