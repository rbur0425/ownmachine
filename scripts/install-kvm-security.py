#!/usr/bin/env python3
"""Install persistent per-VM KVM security. Explicit administrator execution only.

Adopts existing dedicated runtime accounts and a reviewed guest; creates no VM,
changes no SSH key, restarts no libvirt service, and never flushes global rules.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]


def firewall(c,table):
    bridge=c['bridge']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,14}',bridge): raise ValueError('invalid_bridge')
    return f'''table inet {table} {{
 chain input {{ type filter hook input priority -20; policy accept;
  iifname "{bridge}" ct direction reply ct state established,related accept
  iifname "{bridge}" udp dport {{ 53, 67 }} accept
  iifname "{bridge}" tcp dport 53 accept
  iifname "{bridge}" drop
 }}
 chain forward {{ type filter hook forward priority -20; policy accept;
  iifname "{bridge}" ip daddr {{ 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 }} drop
  iifname "{bridge}" meta nfproto ipv6 drop
 }}
}}
'''


def policy(c):
    return '''polkit.addRule(function(action, subject) {
 if (action.id.indexOf("org.libvirt.api.") !== 0) return;
 var agent = subject.user === AGENT, viewer = subject.user === VIEWER;
 if (!agent && !viewer) return;
 var driver = action.lookup("connect_driver");
 if (viewer && (driver === "QEMU" || driver === "network")) {
  if (["org.libvirt.api.connect.getattr","org.libvirt.api.connect.read","org.libvirt.api.connect.search-networks"].indexOf(action.id)>=0) return polkit.Result.YES;
  if (action.lookup("network_uuid") === NETWORK && ["org.libvirt.api.network.getattr","org.libvirt.api.network.read","org.libvirt.api.network-port.create","org.libvirt.api.network-port.delete","org.libvirt.api.network-port.getattr","org.libvirt.api.network-port.read"].indexOf(action.id)>=0) return polkit.Result.YES;
 }
 if (driver !== "QEMU") return polkit.Result.NO;
 if (["org.libvirt.api.connect.getattr","org.libvirt.api.connect.read","org.libvirt.api.connect.search-domains"].indexOf(action.id)>=0) return polkit.Result.YES;
 if (action.lookup("domain_uuid") !== UUID) return polkit.Result.NO;
 var allowed=["org.libvirt.api.domain.getattr","org.libvirt.api.domain.read"];
 if (viewer) allowed=allowed.concat(["org.libvirt.api.domain.start","org.libvirt.api.domain.init-control"]);
 return allowed.indexOf(action.id)>=0 ? polkit.Result.YES : polkit.Result.NO;
});
'''.replace('AGENT',json.dumps(c['agent_user'])).replace('VIEWER',json.dumps(c['viewer_user'])).replace('NETWORK',json.dumps(c['network_uuid'])).replace('UUID',json.dumps(c['vm_uuid']))


def write(path,data,mode=0o644):
    from kvm_backend import protected
    for parent in (path.parent,*path.parent.parents):
        st=parent.lstat()
        if parent.is_symlink() or st.st_uid!=0 or st.st_mode & 0o022: raise ValueError('unsafe_install_parent')
    if path.exists() or path.is_symlink():
        protected(path)
        if path.read_bytes()!=data: raise ValueError('existing_install_differs_'+path.name)
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream: stream.write(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True,help='Reviewed JSON: runtime object plus bridge')
    parser.add_argument('--prefix',type=Path,default=Path('/usr/local/lib/ownmachine-kvm'))
    args=parser.parse_args()
    if os.geteuid()!=0: parser.error('Administrator authentication required')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(args.prefix)): raise ValueError('invalid_install_prefix')
    sys.path.insert(0,str(ROOT/'host'))
    from kvm_backend import protected
    from kvm_security import live_hash, polkit_configured
    data=json.loads(args.config.read_text()); c=data['runtime']
    identity=uuid.UUID(c['vm_uuid']).hex
    for key in ('agent_user','viewer_user','qemu_user'):
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',c[key]): raise ValueError('invalid_account')
        if pwd.getpwnam(c[key]).pw_uid==0: raise ValueError('non_root_accounts_required')
    access=Path('/etc/libvirt/libvirtd.conf'); protected(access)
    if not polkit_configured(access.read_text()):
        raise ValueError('enable_libvirt_polkit_and_restart_with_operator_before_installing')
    args.prefix.mkdir(mode=0o755,parents=True,exist_ok=True)
    for name in ('ownmachine_host.py','kvm_backend.py','kvm_security.py'):
        write(args.prefix/name,(ROOT/'host'/name).read_bytes())
    config=args.prefix/(identity+'.json')
    c['security_helper']=str(args.prefix/'kvm_security.py')
    # Runtime credentials live outside the operator-writable spike directory.
    # Only the agent's primary group can read the private guest key.
    key=args.prefix/(identity+'-guest-key')
    write(key,Path(c['guest_key']).read_bytes(),0o440)
    os.chown(key,0,pwd.getpwnam(c['agent_user']).pw_gid)
    known=args.prefix/(identity+'-guest-known-hosts')
    write(known,Path(c['guest_known_hosts']).read_bytes())
    c['guest_key']=str(key);c['guest_known_hosts']=str(known)
    write(config,(json.dumps(c,sort_keys=True,indent=2)+'\n').encode())
    from kvm_backend import configure
    configure(config)
    table='ownmachine_'+identity
    rules=args.prefix/(identity+'.nft'); write(rules,firewall(data,table).encode())
    rule=Path('/etc/polkit-1/rules.d')/('00-ownmachine-'+identity+'.rules')
    write(rule,policy(c).encode())
    subprocess.run(['/usr/sbin/nft','--check','-f',str(rules)],check=True)
    # No receipt is published until the live rule is installed and inspected.
    exists=subprocess.run(['/usr/sbin/nft','list','table','inet',table],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    payload=(f'delete table inet {table}\n' if exists else '')+rules.read_text()
    subprocess.run(['/usr/sbin/nft','-f','-'],input=payload,text=True,check=True)
    manifest={'bridge':data['bridge'],'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'table':table,'nft_sha256':live_hash(table)}
    for key,path in (('rules',rules),('policy',rule),('access_config',access)):
        manifest[key]=str(path);manifest[key+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    write(Path(str(config)+'.security.json'),json.dumps(manifest,sort_keys=True).encode())
    unit='ownmachine-kvm-'+identity+'.service'
    text=f'''[Unit]
Description=OwnMachine dedicated VM firewall
After=nftables.service
Before=libvirtd.service virtqemud.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {args.prefix}/kvm_security.py --apply {config}
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
'''
    write(Path('/etc/systemd/system')/unit,text.encode())
    sudo=f"{c['agent_user']},{c['viewer_user']} ALL=(root) NOPASSWD: /usr/bin/python3 {args.prefix}/kvm_security.py --check {config}\n"
    sudo_path=Path('/etc/sudoers.d')/('ownmachine-kvm-'+identity)
    # Validate a protected staging file before activating sudoers.
    staged=args.prefix/(identity+'.sudoers'); write(staged,sudo.encode(),0o440)
    subprocess.run(['/usr/sbin/visudo','-cf',str(staged)],check=True)
    write(sudo_path,sudo.encode(),0o440)
    subprocess.run(['/usr/bin/virsh','-c','qemu:///system','autostart','--disable',c['vm_uuid']],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now',unit],check=True)
    subprocess.run(['/usr/bin/python3',c['security_helper'],'--check',str(config)],check=True)
    print('Persistent security installed. Runtime keys are unchanged; verify before switching their forced command to '+str(args.prefix/'ownmachine_host.py')+' --role ROLE --config '+str(config))


if __name__=='__main__':main()
