#!/usr/bin/env python3
"""Prepare the managed desktop on first boot, including after an interruption."""
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile

ROOT = Path('/opt/ownmachine-kvm')
RECEIPT = Path('/etc/ownmachine/hardened.json')


def ensure_key(path, expected, account):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        # Publish only a complete file and never replace an existing key.
        with tempfile.NamedTemporaryFile(dir=path.parent) as tmp:
            tmp.write(expected)
            tmp.flush()
            os.fchmod(tmp.fileno(), 0o600)
            os.fsync(tmp.fileno())
            try:
                os.link(tmp.name, path)
            except FileExistsError:
                pass
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
                or (info.st_uid, info.st_gid) != (account.pw_uid, account.pw_gid)
                or stream.read(len(expected) + 1) != expected):
            raise ValueError('unexpected_guest_key')


def install_keys(account):
    if os.geteuid() != account.pw_uid or os.getegid() != account.pw_gid:
        raise ValueError('desktop_identity_required')
    ssh = Path(account.pw_dir) / '.ssh'
    ssh.mkdir(mode=0o700, exist_ok=True)
    info = ssh.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('unexpected_ssh_directory')
    for role, target in [('runtime', 'authorized_keys'), ('setup', 'ownmachine-setup')]:
        key = (ROOT / (role + '.pub')).read_text().strip()
        line = f'restrict,command="/usr/bin/python3 {ROOT}/guest-entry.py {role}" {key}\n'
        ensure_key(ssh / target, line.encode(), account)


def install_tools():
    tools = ROOT / 'tools'
    python = tools / 'bin/python'
    if not os.access(python, os.X_OK) or subprocess.run(
            [str(python), '-I', '-c', 'import pip, sys; sys.exit(sys.prefix != sys.argv[1])', str(tools)],
            capture_output=True).returncode:
        subprocess.run([sys.executable, '-m', 'venv', str(tools)], check=True)
    probe = [str(python), '-I', '-c',
             "from importlib.metadata import version; import sys; "
             "sys.exit((version('cmake'), version('ninja')) != ('4.4.5', '1.13.2'))"]
    binaries = [str(tools / 'bin' / name) for name in ('cmake', 'ninja')]
    def working():
        return (not subprocess.run(probe, capture_output=True).returncode
                and all(os.access(binary, os.X_OK) and
                        subprocess.run([binary, '--version'], capture_output=True).returncode == 0
                        for binary in binaries))
    if not working():
        subprocess.run([str(python), '-m', 'pip', 'install', '--force-reinstall', '--no-index',
                        '--find-links', str(ROOT), 'cmake==4.4.5', 'ninja==1.13.2'], check=True)
        if not working():
            raise ValueError('guest_build_tools_incomplete')


def main():
    conf = json.loads((ROOT / 'guest.json').read_text())
    user = conf['user']
    account = pwd.getpwnam(user)
    if sys.argv[1:] == ['--keys']:
        install_keys(account)
        return
    if account.pw_uid < 1000 or os.geteuid() != 0 or sys.argv[1:]:
        raise ValueError('guest_desktop_account_required')
    if not RECEIPT.exists():
        subprocess.run(['runuser', '-u', user, '--', sys.executable, __file__, '--keys'], check=True)
        install_tools()
        subprocess.run([sys.executable, str(ROOT / 'secure-linux-guest.py'), '--hypervisor', 'kvm',
                        '--user', user, '--ssh-source', conf['source'], '--password-file',
                        str(ROOT / 'password'), '--apply'], check=True)
    if not RECEIPT.is_file():
        raise ValueError('hardening_receipt_required')
    for name in ('password', 'setup.pub'):
        (ROOT / name).unlink(missing_ok=True)
    (ROOT / 'firstboot.complete').touch(mode=0o600)


if __name__ == '__main__':
    main()
