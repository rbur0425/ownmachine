#!/usr/bin/env python3
"""Read-only, independent file/boot verification using operator setup SSH access."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--ssh-config', type=Path, required=True)
p.add_argument('--host-alias', required=True)
p.add_argument('--guest-path', required=True)
p.add_argument('--expected', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', a.host_alias):
    p.error('Invalid SSH alias')
request = base64.b64encode(json.dumps({'path': a.guest_path, 'expected': a.expected}).encode()).decode()
script = '''$ErrorActionPreference = 'Stop'
$r = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('REQUEST')) | ConvertFrom-Json
$exists = Test-Path -LiteralPath $r.path -PathType Leaf
$result = [ordered]@{exists=$exists;content_matches=$false;sha256=$null;bytes=$null;boot_time_utc=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')}
if ($exists) {
 $result.content_matches = [IO.File]::ReadAllText($r.path) -ceq $r.expected
 $result.sha256 = (Get-FileHash -LiteralPath $r.path -Algorithm SHA256).Hash.ToLowerInvariant()
 $result.bytes = (Get-Item -LiteralPath $r.path).Length
}
$result | ConvertTo-Json -Compress
'''.replace('REQUEST', request)
command = 'powershell -NoProfile -NonInteractive -EncodedCommand ' + base64.b64encode(script.encode('utf-16le')).decode()
env = {k: os.environ[k] for k in ('PATH', 'HOME', 'SSH_AUTH_SOCK', 'LANG') if k in os.environ}
result = subprocess.run(['ssh', '-F', str(a.ssh_config), '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', a.host_alias, command], env=env, capture_output=True, text=True, timeout=45, check=True)
data = json.loads(result.stdout.lstrip('\ufeff'))
fd = os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
print(json.dumps(data))
raise SystemExit(0 if data['exists'] and data['content_matches'] else 1)
