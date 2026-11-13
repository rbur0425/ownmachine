#!/usr/bin/env python3
"""Root-owned first graphical boot gate for the managed Omarchy guest.

Installed before the upstream desktop installer can enable SDDM. A receipt is
published only by the hardener after live policy verification. Administrators
can intentionally change this policy; it is not a boundary against guest root.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess

RECEIPT = Path('/etc/ownmachine/hardened.json')


def trusted(path):
    for item in (path, *path.parents):
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError('untrusted_hardening_receipt')
    if not path.is_file():
        raise ValueError('hardening_receipt_required')


def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30).stdout


def live_policy(user):
    account = pwd.getpwnam(user)
    if account.pw_uid < 1000:
        raise ValueError('desktop_user_required')
    effective = run(['/usr/bin/sshd', '-T']).lower().splitlines()
    for setting in ('passwordauthentication no', 'kbdinteractiveauthentication no',
                    'permitrootlogin no', 'allowtcpforwarding no', 'allowagentforwarding no'):
        if setting not in effective:
            raise ValueError('guest_ssh_policy_incomplete')
    run(['/usr/bin/systemctl', 'is-active', '--quiet', 'ownmachine-firewall.service'])
    rules = json.loads(run(['/usr/bin/nft', '-j', 'list', 'table', 'inet', 'ownmachine']))
    chains = {entry['chain']['name']: entry['chain'] for entry in rules['nftables'] if 'chain' in entry}
    if any(chains.get(name, {}).get('policy') != 'drop' for name in ('input', 'forward')):
        raise ValueError('guest_firewall_policy_incomplete')
    probe = subprocess.run(['/usr/bin/runuser', '-u', user, '--', '/usr/bin/sudo', '-n', '-k', '/usr/bin/true'], capture_output=True, timeout=10)
    if probe.returncode == 0:
        raise ValueError('unrestricted_passwordless_sudo_remains')
    return account.pw_uid


def check():
    trusted(RECEIPT)
    receipt = json.loads(RECEIPT.read_text())
    if receipt.get('schema_version') != 1 or live_policy(receipt['user']) != receipt['uid']:
        raise ValueError('hardening_receipt_mismatch')


def seal(user):
    uid = live_policy(user)
    content = json.dumps(dict(schema_version=1, user=user, uid=uid)) + '\n'
    if RECEIPT.exists() or RECEIPT.is_symlink():
        trusted(RECEIPT)
        if RECEIPT.read_text() != content:
            raise ValueError('hardening_receipt_mismatch')
        return
    for item in (RECEIPT.parent, *RECEIPT.parent.parents):
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError('unsafe_hardening_directory')
    fd = os.open(RECEIPT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o644)
        stream.write(content); stream.flush(); os.fsync(stream.fileno())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', metavar='USER')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('guest_root_required')
    if args.seal:
        seal(args.seal)
    else:
        check()
