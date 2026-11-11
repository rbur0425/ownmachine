#!/usr/bin/env python3
"""Operator-only key pairing with out-of-band host-key confirmation; no SSH scan trust."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from setup_support import mac, install_exact, private_read


def prepare(args):
    for value in (args.alias, args.user):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value): raise ValueError('invalid_identifier')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*', args.host) or not 1 <= args.port <= 65535:
        raise ValueError('invalid_host_or_port')
    fields = args.host_key.read_text().strip().split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519': raise ValueError('ed25519_host_public_key_required')
    blob = base64.b64decode(fields[1], validate=True)
    if len(blob) != 51 or blob[:19] != b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20':
        raise ValueError('invalid_host_key')
    fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
    if fingerprint != args.confirm_fingerprint: raise ValueError('host_fingerprint_mismatch')
    root = Path.home()/'.ssh'/('ownmachine-' + args.role + '-' + args.alias)
    known = root/'known_hosts'
    identity = root/'id_ed25519'
    ssh_config = Path.home()/'.ssh/config'
    include = 'Include ' + json.dumps(str(root/'config'))
    host = 'ownmachine-' + args.role + '-' + args.alias
    fragment = '\n'.join(['Host ' + args.alias, '  HostName ' + args.host, '  User ' + args.user,
                          '  Port ' + str(args.port), '  IdentityFile ' + json.dumps(str(identity)),
                          '  UserKnownHostsFile ' + json.dumps(str(known)), '  HostKeyAlias ' + host,
                          '  IdentitiesOnly yes', '  StrictHostKeyChecking yes', '  BatchMode yes',
                          '  ForwardAgent no', '  ClearAllForwardings yes', 'Host *', ''])
    report = dict(ok=True, role=args.role, stage='planned', host_fingerprint=fingerprint,
                  next='Run separately as each runtime owner. Copy only its public key to the Mac key-install stage.')
    if not args.apply: return report
    if os.geteuid() == 0: raise ValueError('run_as_runtime_account_not_root')
    mac.private_dir(Path.home()/'.ssh')
    mac.private_dir(root)
    import fcntl
    fd = os.open(root/'pair.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Install the confirmed host identity before generating any client key.
        install_exact(known, (host + ' ssh-ed25519 ' + fields[1] + '\n').encode())
        install_exact(root/'config', fragment.encode())
        if not identity.exists() and not identity.is_symlink():
            if identity.with_suffix('.pub').exists(): raise ValueError('partial_keypair')
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'ownmachine-' + args.role,
                            '-f', str(identity)], check=True, capture_output=True, timeout=30)
        private_read(identity)  # permission/type check, never returned to the caller
        derived = subprocess.run(['ssh-keygen', '-y', '-f', str(identity)], check=True, capture_output=True, timeout=10).stdout.decode().strip()
        public = identity.with_suffix('.pub').read_text().strip()
        if public.split()[:2] != derived.split()[:2]: raise ValueError('keypair_mismatch')
        current = private_read(ssh_config).decode() if ssh_config.exists() or ssh_config.is_symlink() else ''
        if include not in current.splitlines():
            # Do not silently shadow an explicit existing alias.
            for line in current.splitlines():
                words = line.strip().split()
                if words and words[0].lower() == 'host' and args.alias in words[1:]:
                    raise ValueError('ssh_alias_already_configured')
            import tempfile
            fd, name = tempfile.mkstemp(dir=ssh_config.parent, prefix='.ownmachine-ssh-')
            try:
                with os.fdopen(fd, 'w') as stream:
                    stream.write(include + '\n' + current)
                    stream.flush(); os.fsync(stream.fileno())
                now = private_read(ssh_config).decode() if ssh_config.exists() or ssh_config.is_symlink() else ''
                if now != current: raise ValueError('ssh_config_changed')
                os.replace(name, ssh_config)
            finally:
                if os.path.exists(name): os.unlink(name)
        # Inspect effective configuration: an earlier Include must not redirect this alias.
        effective = subprocess.run(['ssh', '-F', str(ssh_config), '-G', args.alias], check=True, capture_output=True, text=True, timeout=10).stdout
        parsed = dict(line.split(' ', 1) for line in effective.splitlines() if ' ' in line)
        identities = [line.split(' ', 1)[1] for line in effective.splitlines() if line.startswith('identityfile ')]
        if (parsed.get('hostname', '').lower() != args.host.lower() or parsed.get('user') != args.user
                or parsed.get('stricthostkeychecking') != 'true' or parsed.get('hostkeyalias') != host
                or parsed.get('identitiesonly') != 'yes' or identities != [str(identity)]):
            raise ValueError('effective_ssh_configuration_differs')
    return dict(report, stage='paired', public_key_file=str(identity.with_suffix('.pub')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=['agent', 'viewer', 'setup'], required=True)
    parser.add_argument('--alias', required=True)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=22)
    parser.add_argument('--user', required=True)
    parser.add_argument('--host-key', type=Path, required=True)
    parser.add_argument('--confirm-fingerprint', required=True, help='SHA256 fingerprint verified independently on the Mac console')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(prepare(args)))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps(dict(ok=False, stage='needs_attention', next='Inspect pairing locally; do not bypass host-key verification.')))
        return 2


if __name__ == '__main__': raise SystemExit(main())
