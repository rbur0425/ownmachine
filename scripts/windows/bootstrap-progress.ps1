# Non-secret, machine-readable checkpoints. Writers run as SYSTEM/setup admin.
function Write-BootstrapProgress([string]$Stage) {
    $path = Join-Path $root 'bootstrap-status.json'
    $temp = Join-Path $root ('progress-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [ordered]@{stage=$Stage;updated_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content $temp -Encoding utf8
        if (Test-Path $path) { [IO.File]::Replace($temp,$path,[NullString]::Value) }
        else { [IO.File]::Move($temp,$path) }
    } finally { Remove-Item $temp -Force -ErrorAction SilentlyContinue }
}
