#!/usr/bin/env python3
"""Explicit administrator update of only the configured KVM firewall table.

Runtime checks fail closed while files and live rules differ. Keeps a root-only
backup of the prior policy and manifest; restarts only the dedicated firewall unit.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);a=p.parse_args()
    if os.geteuid()!=0:p.error('Administrator authentication required')
    # Import reviewed source alongside this script; the installed helper verifies
    # its root-owned configuration and trust files before any mutation.
    source=Path(__file__).resolve().parent/'install-kvm-security.py'
    spec=importlib.util.spec_from_file_location('kvm_install',source)
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    sys.path.insert(0,str(source.parent.parent/'host'))
    from kvm_backend import protected
    from kvm_security import load,live_hash
    c,m=load(a.config)
    table='ownmachine_'+uuid.UUID(c['vm_uuid']).hex
    if table!=m['table']:raise ValueError('table_identity_mismatch')
    rules=protected(m['rules']);manifest=protected(str(a.config)+'.security.json')
    content=installer.firewall({'bridge':m['bridge']},table)
    payload='delete table inet '+table+'\n'+content
    subprocess.run(['/usr/sbin/nft','--check','-f','-'],input=payload,text=True,check=True)
    helper=protected(c['security_helper'])
    for path in (rules,manifest,helper):
        backup=path.with_name(path.name+'.before-reply-fix')
        if not backup.exists():
            fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as f:f.write(path.read_bytes())
    def replace(path,data):
        temp=path.with_name(path.name+'.reply-fix-new')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    replace(helper,(source.parent.parent/'host/kvm_security.py').read_bytes())
    replace(rules,content.encode())
    subprocess.run(['/usr/sbin/nft','-f','-'],input=payload,text=True,check=True)
    m['rules_sha256']=hashlib.sha256(rules.read_bytes()).hexdigest();m['nft_sha256']=live_hash(table)
    replace(manifest,json.dumps(m,sort_keys=True).encode())
    subprocess.run(['systemctl','restart','ownmachine-kvm-'+uuid.UUID(c['vm_uuid']).hex+'.service'],check=True)
    subprocess.run(['/usr/bin/python3',c['security_helper'],'--check',str(a.config)],check=True)
    print('Reply-only guest traffic restored; guest-initiated host connections stay blocked. Dedicated firewall service restarted and verified.')


if __name__=='__main__':main()
