#!/usr/bin/env python3
"""Explicit administrator update of root-owned relay code, with hashed backups.

Does not change configuration, keys, firewall policy, services or VM state.
New SSH connections use the updated code; active sessions retain their process.
"""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--source-dir',type=Path,required=True)
    a=p.parse_args()
    if os.geteuid()!=0:p.error('Administrator authentication required')
    for path in (a.config,a.config.parent,*a.config.parent.parents):
        st=path.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o022:raise ValueError('unsafe_runtime_path')
    prepared=[]
    for name in ('ownmachine_host.py','kvm_backend.py','kvm_security.py'):
        content=(a.source_dir/name).read_bytes();compile(content,name,'exec')
        destination=a.config.parent/name;st=destination.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o022:raise ValueError('unsafe_runtime_file')
        old=destination.read_bytes()
        if old==content:continue
        backup=destination.with_name(name+'.before-'+hashlib.sha256(old).hexdigest()[:16])
        if not backup.exists():
            fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as f:f.write(old);os.fchmod(f.fileno(),0o600)
        prepared.append((destination,content))
    for destination,content in prepared:
        temp=destination.with_name(destination.name+'.update-new')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
        with os.fdopen(fd,'wb') as f:f.write(content);f.flush();os.fchmod(f.fileno(),0o644);os.fsync(f.fileno())
        os.replace(temp,destination)
    print('Root-owned relay code updated with backups; no keys, VM, services or firewall rules changed.')


if __name__=='__main__':
    try: main()
    except FileNotFoundError:
        print('Runtime update refused: a config, source or installed runtime file is missing. Check --config and --source-dir on this host. No automatic retry was attempted.',file=sys.stderr)
        raise SystemExit(1)
    except (OSError,ValueError,SyntaxError):
        print('Runtime update refused: inspect file ownership, permissions, valid Python source and any .update-new file from an interrupted update. Do not change keys or bypass the root-owned path checks.',file=sys.stderr)
        raise SystemExit(1)
