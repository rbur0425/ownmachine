#!/usr/bin/env python3
"""Operator-only password change; supply a private file, never a password argument."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='ownmachine')
    parser.add_argument('--guest-user', default='lume')
    parser.add_argument('--password-file', type=Path, required=True)
    parser.add_argument('--lume', default=str(Path.home() / '.local/bin/lume'))
    args = parser.parse_args()
    for value in (args.name, args.guest_user):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value): parser.error('Invalid identifier')
    new = args.password_file.read_text().rstrip('\n')
    if len(new) < 10 or any(c in new for c in '\n\r\0'):
        parser.error('Use at least 10 characters without line breaks or NULs')
    os.umask(0o077)
    state = Path.home() / '.local/state/ownmachine' / args.name
    current = state / 'guest-password'
    pending = state / 'guest-password.pending'
    old = current.read_text().rstrip('\n')
    if pending.exists(): parser.error('Pending password change exists; inspect before retrying')
    rows = json.loads(subprocess.check_output([args.lume, 'ls', '--format', 'json'], text=True, timeout=20))
    vm = next(row for row in rows if row['name'] == args.name)
    if vm.get('status') != 'running' or not vm.get('ipAddress'):
        parser.error('Configured guest must be running with an assigned address')
    ssh = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=yes',
           '-o', f'UserKnownHostsFile={state}/guest_known_hosts', '-o', f'HostKeyAlias=ownmachine-guest-{args.name}',
           '-i', str(state / 'guest_ed25519'), f"{args.guest_user}@{vm['ipAddress']}"]
    def call(command, data=None):
        result = subprocess.run(ssh + [command], input=data, capture_output=True, text=True, timeout=30)
        if result.returncode: raise RuntimeError('Password change incomplete; inspect private recovery files')
    q = shlex.quote
    call('true')
    with pending.open('x') as f: f.write(new + '\n')
    call(f'/usr/bin/dscl . -passwd /Users/{args.guest_user} {q(old)} {q(new)}')
    plain = new.encode() + b'\0' * (12 - len(new.encode()) % 12)
    key = bytes([0x7d, 0x89, 0x52, 0x23, 0xd2, 0xbc, 0xdd, 0xea, 0xa3, 0xb9, 0x1f])
    encoded = base64.b64encode(bytes(b ^ key[i % len(key)] for i, b in enumerate(plain))).decode()
    call('sudo -S -p "" /bin/sh -s', new + '\n' + f"set -eu\nprintf '%s' {q(encoded)} | /usr/bin/base64 -D > /etc/kcpassword\nchmod 600 /etc/kcpassword\n")
    call(f'/usr/bin/security set-keychain-password -o {q(old)} -p {q(new)} "$HOME/Library/Keychains/login.keychain-db"')
    call(f'/usr/bin/dscl . -authonly {args.guest_user} {q(new)}')
    call(f'/usr/bin/security unlock-keychain -p {q(new)} "$HOME/Library/Keychains/login.keychain-db"')
    pending.replace(current)
    print(json.dumps({'password_changed': True, 'autologin_updated': True, 'keychain_verified': True}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, StopIteration, RuntimeError, subprocess.SubprocessError):
        print('Password operation incomplete. Inspect private recovery files; do not retry blindly.', file=sys.stderr)
        sys.exit(1)
