#!/usr/bin/env python3
"""Prepare guest-only keys and harden the verified image before graphical login."""
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys

ROOT=Path('/opt/ownmachine-kvm')
def main():
    conf=json.loads((ROOT/'guest.json').read_text())
    user=conf['user']
    account=pwd.getpwnam(user)
    if account.pw_uid<1000 or os.geteuid()!=0:
        raise ValueError('guest_desktop_account_required')
    ssh=Path(account.pw_dir)/'.ssh'
    ssh.mkdir(mode=0o700,exist_ok=True)
    if ssh.is_symlink():raise ValueError('unexpected_ssh_directory')
    os.chown(ssh,account.pw_uid,account.pw_gid)
    for role,target in [('runtime','authorized_keys'),('setup','ownmachine-setup')]:
        key=(ROOT/(role+'.pub')).read_text().strip()
        with (ssh/target).open('x') as stream:
            os.fchmod(stream.fileno(),0o600)
            os.fchown(stream.fileno(),account.pw_uid,account.pw_gid)
            stream.write(f'restrict,command="/usr/bin/python3 {ROOT}/guest-entry.py {role}" {key}\n')
    subprocess.run([sys.executable,'-m','venv',str(ROOT/'tools')],check=True)
    subprocess.run([str(ROOT/'tools/bin/pip'),'install','--no-index','--find-links',str(ROOT),'cmake','ninja'],check=True)
    subprocess.run([sys.executable,str(ROOT/'secure-linux-guest.py'),'--hypervisor','kvm','--user',user,'--ssh-source',conf['source'],'--password-file',str(ROOT/'password'),'--apply'],check=True)
    (ROOT/'setup.pub').unlink()

if __name__=='__main__':
    main()
