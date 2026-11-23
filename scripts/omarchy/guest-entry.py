#!/usr/bin/env python3
"""Forced SSH entry points inside the Omarchy KVM desktop."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('/opt/ownmachine-kvm')
HOME=Path.home()
SUPPORT=HOME/'.local/lib/ownmachine'


def main():
    os.umask(0o077)
    role=sys.argv[1]
    command=os.environ.get('SSH_ORIGINAL_COMMAND','')
    if command=='ownmachine-guest status':
        result=subprocess.run([sys.executable,str(ROOT/'linux-guest.py'),'status'],check=True,text=True,capture_output=True)
        data=json.loads(result.stdout)
        data.update(guest_reachable=True,bootstrap_hardened=Path('/etc/ownmachine/hardened.json').is_file())
        print(json.dumps(data))
    elif role=='runtime' and command=='ownmachine-guest mcp':
        os.execl(sys.executable,sys.executable,str(ROOT/'linux-guest.py'),'mcp')
    elif role=='setup' and command=='ownmachine-guest driver':
        if not (HOME/'.config/ownmachine/linux-driver.json').exists():
            subprocess.run([sys.executable,str(ROOT/'linux-guest.py'),'install','--artifact',str(ROOT/'driver.tar.gz')],check=True,stdout=sys.stderr)
        import shutil
        shutil.copyfile(ROOT/'linux-input-module.py',SUPPORT/'linux-input-module.py')
        env={**os.environ,'PATH':str(ROOT/'tools/bin')+':'+os.environ['PATH']}
        for step in ('build','enable'):
            subprocess.run([sys.executable,str(SUPPORT/'linux-input-module.py'),step,'--source-archive',str(ROOT/'input.tar'),'--enable-experimental-input','--apply'],env=env,check=True,stdout=sys.stderr)
        print(json.dumps({'ok':True}))
    elif role=='setup' and command=='ownmachine-guest retire':
        (HOME/'.ssh/ownmachine-setup').unlink()
        print(json.dumps({'ok':True,'retired':True}))
    else:
        return 64
    return 0

if __name__=='__main__':
    sys.exit(main())
