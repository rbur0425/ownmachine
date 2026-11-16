#!/usr/bin/env python3
"""Administrator activation of an already installed KVM runtime.

Checks both roles before replacing their single existing forced-command key.
Preserves key material, refuses ambiguous authorized_keys, and saves a backup.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import subprocess
import sys
import stat


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--test-drift',action='store_true');a=p.parse_args()
    if os.geteuid()!=0:p.error('Administrator authentication required')
    for path in (a.config.parent/'kvm_backend.py',a.config.parent,*a.config.parent.parents):
        st=path.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o022:raise ValueError('untrusted_runtime_path')
    sys.path.insert(0,str(a.config.parent))
    from kvm_backend import protected,configure
    protected(a.config.parent/'kvm_backend.py');configure(a.config)
    c=json.loads(a.config.read_text());relay=protected(a.config.parent/'ownmachine_host.py')
    env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}
    def probe(role,op):
        user=pwd.getpwnam(c[role+'_user'])
        return subprocess.run(['/usr/sbin/runuser','-u',user.pw_name,'--','/usr/bin/env',
            'SSH_ORIGINAL_COMMAND=ownmachine-host '+op+' --vm '+c['vm_name'],
            '/usr/bin/python3',str(relay),'--role',role,'--config',str(a.config)],
            env=env,capture_output=True,text=True,input='',timeout=25)
    for role in ('agent','viewer'):
        r=probe(role,'status')
        if r.returncode or json.loads(r.stdout).get('vm_uuid')!=c['vm_uuid']:
            raise ValueError('production_'+role+'_status_failed: '+r.stdout[:200])
        r=probe(role,'start' if role=='agent' else 'mcp')
        if r.returncode==0:raise ValueError('role_boundary_failed')
    if a.test_drift:
        m=json.loads(protected(str(a.config)+'.security.json').read_text())
        # An additional DROP only makes the existing policy more restrictive.
        subprocess.run(['/usr/sbin/nft','add','rule','inet',m['table'],'input','iifname',m['bridge'],'drop'],check=True)
        try:
            if probe('agent','status').returncode==0:raise ValueError('drift_was_not_refused')
        finally:
            subprocess.run(['/usr/bin/python3',c['security_helper'],'--apply',str(a.config)],check=True)
        if probe('agent','status').returncode:raise ValueError('restoration_failed')
    for role in ('agent','viewer'):
        user=pwd.getpwnam(c[role+'_user']);path=Path(user.pw_dir)/'.ssh/authorized_keys'
        parent=path.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=user.pw_uid or parent.st_mode & 0o077:
            raise ValueError('unsafe_ssh_directory')
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
            with os.fdopen(fd) as f:
                st=os.fstat(f.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_uid!=user.pw_uid or st.st_mode & 0o077 or st.st_size>16384:
                    raise ValueError('unsafe_authorized_keys')
                text=f.read()
            lines=[s for s in text.splitlines() if s.strip()]
            if len(lines)!=1:raise ValueError('ambiguous_authorized_keys')
            match=re.fullmatch(r'restrict,command="(?:[^"\\]|\\.)+" (ssh-ed25519 [A-Za-z0-9+/=]+(?: [A-Za-z0-9_-]+)?)',lines[0])
            if not match:raise ValueError('unexpected_key_format')
            command=shlex.join(['/usr/bin/python3',str(relay),'--role',role,'--config',str(a.config)])
            replacement='restrict,command="'+command.replace('\\','\\\\').replace('"','\\"')+'" '+match[1]+'\n'
            if text==replacement:continue
            backup='authorized_keys.before-production-kvm'
            fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
            with os.fdopen(fd,'w') as f:f.write(text)
            temporary='authorized_keys.production-new'
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
            with os.fdopen(fd,'w') as f:
                os.fchown(f.fileno(),user.pw_uid,user.pw_gid);f.write(replacement)
            os.rename(temporary,path.name,src_dir_fd=directory,dst_dir_fd=directory)
        finally:os.close(directory)
    print('Production role probes and refusal checks passed; runtime keys now use the root-owned KVM relay.')
    if a.test_drift:print('Extra restrictive-rule drift was refused; intended firewall restored and rechecked.')


if __name__=='__main__':main()
