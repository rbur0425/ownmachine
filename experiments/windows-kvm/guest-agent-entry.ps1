# This is the only command admitted by the standard account's runtime SSH key.
$ErrorActionPreference = 'Stop'
$cfg = Get-Content (Join-Path $PSScriptRoot 'health-config.json') -Raw | ConvertFrom-Json
$healthPath = ($PSScriptRoot -replace '\\','/') + '/health.ps1'
$mcp = $cfg.driver + ' mcp --socket \\.\pipe\cua-driver'
$health = 'powershell -NoProfile -ExecutionPolicy Bypass -File ' + $healthPath
if ($env:SSH_ORIGINAL_COMMAND -ceq $mcp) {
    & $cfg.driver mcp --socket '\\.\pipe\cua-driver'
    exit $LASTEXITCODE
}
if ($env:SSH_ORIGINAL_COMMAND -ceq $health) {
    & $healthPath
    exit 0
}
[Console]::Error.WriteLine('unsupported_guest_operation')
exit 1
