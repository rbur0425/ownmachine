#!/usr/bin/env python3
"""Operator-only first boot hardening for a fresh Lume unattended guest.

Run on the VM host. Initial SSH uses accept-new in a dedicated known-hosts file
for the newly created NAT guest; all subsequent connections require that key.
Private credentials remain in the operator's private state directory, never Git.
"""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import tempfile


def generate_guest_password():
    """Unique, typeable recovery credential: 16 random letters in four groups."""
    alphabet = 'abcdefghjkmnpqrstuvwxyz'
    return '-'.join(''.join(secrets.choice(alphabet) for _ in range(4))
                    for _ in range(4))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='ownmachine')
    parser.add_argument('--guest-user', default='lume')
    parser.add_argument('--guest-ip', required=True, help='Current guest IP from trusted Lume metadata')
    args = parser.parse_args()
    for value in (args.name, args.guest_user):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value): parser.error('Invalid identifier')
    ipaddress.ip_address(args.guest_ip)
    os.umask(0o077)
    state = Path.home() / '.local/state/ownmachine' / args.name
    state.mkdir(parents=True, exist_ok=True)
    password_file = state / 'guest-password'
    if password_file.exists():
        print('Credential file exists; inspect prior hardening state before retrying.', file=sys.stderr)
        return 2
    identity = state / 'guest_ed25519'
    if not identity.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'ownmachine-guest', '-f', str(identity)], check=True)
    known_hosts = state / 'guest_known_hosts'
    common = ['ssh', '-T', '-F', '/dev/null', '-o', 'ClearAllForwardings=yes', '-o', 'ConnectTimeout=10', '-o', 'ForwardAgent=no',
              '-o', 'IdentitiesOnly=yes', '-o', f'UserKnownHostsFile={known_hosts}',
              '-o', f'HostKeyAlias=ownmachine-guest-{args.name}', '-i', str(identity)]
    destination = f'{args.guest_user}@{args.guest_ip}'
    key_ssh = common + ['-o', 'StrictHostKeyChecking=yes', '-o', 'BatchMode=yes', destination]
    with tempfile.TemporaryDirectory(prefix='ownmachine-bootstrap-') as folder:
        askpass = Path(folder) / 'askpass'
        askpass.write_text("#!/bin/sh\nprintf '%s\\n' lume\n")
        askpass.chmod(0o700)
        env = {key: os.environ[key] for key in ('HOME', 'PATH', 'LANG') if key in os.environ}
        env.update(SSH_ASKPASS=str(askpass), SSH_ASKPASS_REQUIRE='force', DISPLAY='ownmachine')
        initial = common + ['-o', 'StrictHostKeyChecking=accept-new', '-o', 'PreferredAuthentications=password', destination]
        pub = identity.with_suffix('.pub').read_text()
        result = subprocess.run(initial + ['umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys'],
                                input=pub, text=True, capture_output=True, env=env, timeout=30)
        if result.returncode:
            print('Guest key bootstrap failed; no raw SSH diagnostics disclosed.', file=sys.stderr)
            return 1
    check = subprocess.run(key_ssh + ['true'], capture_output=True, timeout=20)
    if check.returncode:
        print('Key-only SSH verification failed.', file=sys.stderr)
        return 1
    password = generate_guest_password()
    # Store recovery material before changing anything; never silently retry.
    with password_file.open('x') as f: f.write(password + '\n')
    plain = password.encode() + b'\0' * (12 - len(password.encode()) % 12)
    xor = bytes([0x7d, 0x89, 0x52, 0x23, 0xd2, 0xbc, 0xdd, 0xea, 0xa3, 0xb9, 0x1f])
    kc = base64.b64encode(bytes(b ^ xor[i % len(xor)] for i, b in enumerate(plain))).decode()
    q = shlex.quote
    # Change the account password as its owner with the known old credential;
    # root-only reset can fail for macOS accounts with secure-token state.
    rotation = subprocess.run(key_ssh + ['/bin/sh -s'],
                              input=f'exec /usr/bin/dscl . -passwd /Users/{args.guest_user} lume {q(password)}\n',
                              text=True, capture_output=True, timeout=30)
    if rotation.returncode:
        print('Password rotation failed; inspect retained recovery material.', file=sys.stderr)
        return 1
    # Authenticate sudo using the new password over stdin.
    script = f'''set -eu
printf '%s' {q(kc)} | /usr/bin/base64 -D > /etc/kcpassword
chmod 600 /etc/kcpassword
mkdir -p /etc/ssh/sshd_config.d
printf '%s\\n' 'PasswordAuthentication no' 'KbdInteractiveAuthentication no' 'PermitRootLogin no' > /etc/ssh/sshd_config.d/00-ownmachine.conf
/usr/sbin/sshd -t
/usr/sbin/sshd -T | /usr/bin/grep -q '^passwordauthentication no$'
/usr/sbin/sshd -T | /usr/bin/grep -q '^kbdinteractiveauthentication no$'
'''
    result = subprocess.run(key_ssh + ['sudo -S -p "" /bin/sh -s'], input=password + '\n' + script,
                            text=True, capture_output=True, timeout=40)
    if result.returncode:
        print('Hardening outcome needs inspection; recovery credential retained.', file=sys.stderr)
        return 1
    # Keep the login keychain aligned with the new autologin password. A failure
    # here is reported, not hidden; no guest data has been imported yet.
    keychain = subprocess.run(key_ssh + ['/bin/sh -s'],
                              input=f'exec /usr/bin/security set-keychain-password -o lume -p {q(password)} "$HOME/Library/Keychains/login.keychain-db"\n',
                              text=True, capture_output=True, timeout=30)
    check = subprocess.run(key_ssh + ['sw_vers -productVersion'], capture_output=True, text=True, timeout=20)
    report = {'key_auth_verified': check.returncode == 0, 'password_rotated': True,
              'password_ssh_disabled': True, 'autologin_updated': True,
              'keychain_updated': keychain.returncode == 0,
              'guest_version': check.stdout.strip() if re.fullmatch(r'[0-9.]+\s*', check.stdout) else 'unknown'}
    (state / 'hardening.json').write_text(json.dumps(report))
    print(json.dumps(report))
    return 0 if check.returncode == 0 and keychain.returncode == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError):
        print('Guest operation failed or timed out; inspect private state before retrying.', file=sys.stderr)
        sys.exit(1)
