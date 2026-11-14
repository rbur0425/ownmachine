#!/usr/bin/env python3
"""Administrator handoff: register one fresh, never-booted Windows domain.

Creates only the reviewed new domain/network/accounts; does not start Windows,
restart libvirt, or modify existing domains. Refuses preexisting identities.
"""
import argparse
import grp
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import pwd
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from windows_provision import settings,sha
from setup_support import ROOT


def call(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=120).stdout


def absent(*args):return subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--services-file',type=Path,required=True);a.add_argument('--plan-file',type=Path,required=True);args=a.parse_args()
    if os.geteuid()!=0:a.error('Administrator authentication required')
    c=json.loads(args.services_file.read_text());payload=json.loads(args.plan_file.read_text());plan=payload.get('plan',payload);p=settings(c,plan)
    state=Path(plan['storage_dir']);prefix=Path(p['runtime_prefix'])
    expected_runtime=prefix/(p['vm_uuid'].replace('-','')+'.json')
    if str(expected_runtime)!=c['runtime_config']:raise ValueError('runtime_configuration_path_mismatch')
    sys.path.insert(0,str(ROOT/'host'))
    from kvm_security import polkit_configured
    if not polkit_configured(Path('/etc/libvirt/libvirtd.conf').read_text()):
        raise ValueError('enable_libvirt_polkit_and_restart_with_operator_before_installing')
    for role in ('agent','viewer'):
        if not re_full_key((state/(role+'.pub')).read_text().strip()):raise ValueError('invalid_runtime_public_key')
    for path in (state,*state.parents,Path(p['windows_iso']),*Path(p['windows_iso']).parents):
        if path.is_symlink():raise ValueError('symlink_storage_refused')
    pwd.getpwnam(p['qemu_user'])
    if Path(p['console_socket']).parent.exists():raise ValueError('console_directory_exists')
    # First-run only. An interrupted administrative installation needs inspection;
    # never silently adopt a domain or user just because a name happens to match.
    if prefix.exists():raise ValueError('existing_installation_requires_inspection')
    for key in ('agent_user','viewer_user'):
        try:pwd.getpwnam(p[key])
        except KeyError:pass
        else:raise ValueError('runtime_account_exists')
    try:grp.getgrnam(p['console_group'])
    except KeyError:pass
    else:raise ValueError('console_group_exists')
    for identity in (plan['vm_name'],p['vm_uuid']):
        if not absent('virsh','-c','qemu:///system','dominfo',identity):raise ValueError('domain_exists')
    for identity in (plan['vm_name'],p['network_uuid']):
        if not absent('virsh','-c','qemu:///system','net-info',identity):raise ValueError('network_exists')
    if not absent('ip','link','show',p['bridge']):raise ValueError('bridge_exists')
    for identity in call('virsh','-c','qemu:///system','net-list','--all','--uuid').split():
        tree=ET.fromstring(call('virsh','-c','qemu:///system','net-dumpxml',identity))
        for address in tree.findall('ip'):
            if address.get('family')=='ipv6':continue
            old=ipaddress.ip_network(address.get('address')+'/'+(address.get('netmask') or address.get('prefix')),strict=False)
            if old.overlaps(ipaddress.ip_network(p['subnet'])):raise ValueError('network_overlap')
    receipt=json.loads((state/'build.json').read_text())
    if receipt['identity']!=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest():raise ValueError('build_configuration_changed')
    if set(receipt['files'])!={'domain.xml','network.xml','bootstrap.iso','install.json'}:raise ValueError('invalid_build_receipt')
    if json.loads((state/'render.json').read_text())!={**p,'storage_dir':str(state)}:raise ValueError('render_configuration_changed')
    for name,digest in receipt['files'].items():
        if sha(state/name)!=digest:raise ValueError('built_artifact_changed')
    if sha(p['windows_iso'])!=p['windows_iso_sha256']:raise ValueError('windows_iso_changed')
    # Re-render, compare and then define, never accept arbitrary supplied XML.
    with tempfile.TemporaryDirectory() as directory:
        call(sys.executable,str(ROOT/'scripts/windows/render-domain.py'),str(state/'render.json'),directory)
        for name in ('domain.xml','network.xml'):
            if (Path(directory)/name).read_bytes()!=(state/name).read_bytes():raise ValueError('unexpected_domain_template')
    for path in (prefix.parent,*prefix.parent.parents):
        st=path.stat()
        if path.is_symlink() or st.st_uid!=0 or st.st_mode & 0o022:raise ValueError('unsafe_runtime_parent')
    disk=state/'windows.qcow2'
    fd=os.open(disk,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
    call('qemu-img','create','-f','qcow2',str(disk),str(plan['disk_gb'])+'G')
    qemu=pwd.getpwnam(p['qemu_user'])
    for path in (disk,state/'bootstrap.iso'):
        os.chown(path,qemu.pw_uid,qemu.pw_gid);path.chmod(0o600)
    # Traversal only through private parents, no recursive sharing with runtime users.
    for path in (state,*state.parents,Path(p['windows_iso']).parent,*Path(p['windows_iso']).parent.parents):
        if path.is_symlink():raise ValueError('symlink_storage_refused')
        if path.stat().st_mode & 0o001==0:call('setfacl','-m','u:'+p['qemu_user']+':--x',str(path))
    call('groupadd','--system',p['console_group'])
    for role in ('agent','viewer'):
        call('useradd','--create-home','--shell','/bin/bash','--groups','libvirt',p[role+'_user'])
    call('usermod','-aG',p['console_group'],p['viewer_user']);call('usermod','-aG',p['console_group'],p['qemu_user'])
    console=Path(p['console_socket']).parent;console.mkdir(mode=0o750)
    os.chown(console,qemu.pw_uid,grp.getgrnam(p['console_group']).gr_gid)
    call('setfacl','-m','d:u:'+p['viewer_user']+':rwx,d:o::---',str(console))
    call('virsh','-c','qemu:///system','net-define',str(state/'network.xml'))
    call('virsh','-c','qemu:///system','define',str(state/'domain.xml'))
    # Verify libvirt's normalized definition before installing any runtime keys.
    actual=ET.fromstring(call('virsh','-c','qemu:///system','dumpxml',p['vm_uuid']))
    graphics=actual.findall('./devices/graphics')
    if len(graphics)!=1 or graphics[0].get('socket')!=p['console_socket'] or graphics[0].get('autoport')=='yes':
        raise ValueError('libvirt_did_not_preserve_private_console')
    listeners=graphics[0].findall('listen')
    if len(listeners)!=1 or listeners[0].get('type')!='socket' or listeners[0].get('socket')!=p['console_socket']:
        raise ValueError('libvirt_did_not_preserve_private_console')
    # install-kvm-security validates existing ACL configuration and pins all code.
    call(sys.executable,str(ROOT/'scripts/install-kvm-security.py'),'--config',str(state/'install.json'),'--prefix',str(prefix))
    installed=prefix/(p['vm_uuid'].replace('-','')+'.json')
    if str(installed)!=c['runtime_config']:raise ValueError('runtime_configuration_path_mismatch')
    for role in ('agent','viewer'):
        user=pwd.getpwnam(p[role+'_user']);home=Path(user.pw_dir);home.chmod(0o700)
        directory=home/'.ssh';directory.mkdir(mode=0o700);os.chown(directory,user.pw_uid,user.pw_gid)
        command=shlex.join(['/usr/bin/python3',str(prefix/'ownmachine_host.py'),'--role',role,'--config',str(installed)])
        public=(state/(role+'.pub')).read_text().strip()
        if not re_full_key(public):raise ValueError('invalid_runtime_public_key')
        fd=os.open(directory/'authorized_keys',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:f.write('restrict,command="'+command.replace('\\','\\\\').replace('"','\\"')+'" '+public+'\n');os.fchown(f.fileno(),user.pw_uid,user.pw_gid)
    # Only add AllowUsers if the host already maintains that allowlist.
    effective=call('/usr/sbin/sshd','-T')
    users=[p['agent_user'],p['viewer_user']]
    text=('AllowUsers '+' '.join(users)+'\n' if any(line.startswith('allowusers ') for line in effective.splitlines()) else '')
    text+='Match User '+','.join(users)+'\n AuthenticationMethods publickey\n PasswordAuthentication no\n KbdInteractiveAuthentication no\n AllowTcpForwarding no\n AllowStreamLocalForwarding no\n AllowAgentForwarding no\n X11Forwarding no\n PermitTTY no\nMatch all\n'
    fragment=Path('/etc/ssh/sshd_config.d')/('20-ownmachine-'+p['vm_uuid']+'.conf')
    with fragment.open('x') as f:f.write(text)
    call('/usr/sbin/sshd','-t');call('systemctl','reload',p.get('ssh_service','ssh'))
    call('virsh','-c','qemu:///system','net-start',p['network_uuid'])
    call('virsh','-c','qemu:///system','net-autostart',p['network_uuid'])
    print('Fresh domain registered and stopped. Persistent security and both runtime roles installed. Resume Hermes firewall/keys/viewer checks, then provision.')


def re_full_key(value):
    import re
    return re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [A-Za-z0-9_-]+)?',value)


if __name__=='__main__':main()
