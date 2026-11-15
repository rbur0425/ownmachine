# Read-only standard-user window. Closing it never stops privileged bootstrap.
Add-Type -AssemblyName System.Windows.Forms
$root = $PSScriptRoot
$form = New-Object Windows.Forms.Form
$form.Text = 'OwnMachine setup progress'
$form.Width = 620
$form.Height = 300
$form.StartPosition = 'CenterScreen'
$form.TopMost = $false
$text = New-Object Windows.Forms.TextBox
$text.Multiline = $true
$text.ReadOnly = $true
$text.Dock = 'Fill'
$text.ScrollBars = 'Vertical'
$text.Font = New-Object Drawing.Font('Segoe UI',12)
$form.Controls.Add($text)
$messages = @{
 awaiting_first_signin='Waiting for the first desktop sign-in.'
 configuring_power='Configuring display and sleep settings.'
 installing_openssh='Installing Windows OpenSSH. This can take several minutes. Leave the VM running; do not recreate it. If it fails, inspect Windows optional-feature installation and network access.'
 configuring_ssh='Configuring restricted SSH access.'
 configuring_driver='Installing the standard-user driver task. It stays disabled until hardening.'
 clock_sync_pending='Preparing Windows Time synchronization.'
 synchronizing_clock='Synchronizing Windows Time with the configured servers.'
 awaiting_time_sync='Time synchronization needs attention. Check guest DNS and outbound UDP 123 to the configured time servers. In Hermes, run setup --run provision --apply to retry time synchronization only. Do not rebuild the VM.'
 configured='Bootstrap complete. Return to Hermes: setup --run provision --apply, then setup --run harden --apply, driver, permissions and verify. Keep the standard user signed in.'
 failed='Bootstrap failed. Ask the guest administrator to inspect the OwnMachine Bootstrap task history. Preserve this VM and its logs; do not rebuild or replay bootstrap.'
}
$timer = New-Object Windows.Forms.Timer
$timer.Interval = 1500
$timer.Add_Tick({
    try {
        $state = Get-Content (Join-Path $root 'bootstrap-status.json') -Raw | ConvertFrom-Json
        $message = $messages[$state.stage]
        if (-not $message) { $message = 'Waiting for a recognized setup checkpoint.' }
        $text.Text = "OwnMachine Windows setup`r`n`r`n$message`r`n`r`nThis window is read-only. Closing it does not stop setup. See the Windows onboarding guide, First-install progress and recovery."
    } catch { $text.Text = 'Waiting for setup progress. Closing this window does not stop setup.' }
})
$timer.Start()
try { [void]$form.ShowDialog() } finally { $timer.Stop(); $timer.Dispose(); $form.Dispose() }
