#!/usr/bin/env python3
"""Linux/KVM host adapter. Only the root-pinned domain and private console are accessible."""
import ipaddress
import grp
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import shlex
import socket
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=None
C={}
CONFIG=None
ENV={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C','LC_ALL':'C'}

def virsh(*args):
    return subprocess.run(['/usr/bin/virsh','-c','qemu:///system',*args],env=ENV,check=True,capture_output=True,text=True,timeout=15).stdout

def inspect():
    tree=ET.fromstring(virsh('dumpxml',C['vm_uuid']))
    if tree.findtext('uuid')!=C['vm_uuid'] or tree.findtext('name')!=C['vm_name']: raise ValueError('vm_identity_mismatch')
    graphics=tree.findall('./devices/graphics')
    if len(graphics)!=1 or graphics[0].get('type')!='vnc': raise ValueError('private_console_required')
    listens=graphics[0].findall('listen')
    if len(listens)!=1 or listens[0].get('type')!='socket' or listens[0].get('socket')!=C['console_socket']:
        raise ValueError('console_configuration_drift')
    if graphics[0].get('listen') or graphics[0].get('autoport')=='yes' or graphics[0].get('port') not in (None,'-1','0'):
        raise ValueError('tcp_console_refused')
    if tree.findall('./devices/filesystem') or tree.findall('./devices/hostdev') or tree.findall('./devices/redirdev'):
        raise ValueError('host_device_sharing_refused')
    interfaces=tree.findall('./devices/interface')
    if len(interfaces)!=1 or interfaces[0].get('type')!='network': raise ValueError('dedicated_network_required')
    source=interfaces[0].find('source')
    if source is None or source.get('network')!=C['network_name']:
        raise ValueError('network_identity_mismatch')
    return tree,virsh('domstate',C['vm_uuid']).strip()

def guest_argv(operation):
    ip=ipaddress.ip_address(C['guest_ip'])
    if ip not in ipaddress.ip_network(C['subnet']):raise ValueError('guest_outside_network')
    executable=C['driver_executable']
    username=C['guest_user']
    if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+\.exe',executable) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,19}',username):raise ValueError('invalid_guest_configuration')
    health=C['guest_health_script']
    if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+\.ps1',health):raise ValueError('invalid_guest_health_path')
    command=executable+' mcp --socket \\\\.\\pipe\\cua-driver' if operation=='mcp' else 'powershell -NoProfile -ExecutionPolicy Bypass -File '+health
    return ['/usr/bin/ssh','-F','/dev/null','-T','-i',C['guest_key'],'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=8','-o','UserKnownHostsFile='+C['guest_known_hosts'], username+'@'+str(ip),command]

def dispatch(role):
    if role not in ('agent','viewer') or pwd.getpwuid(os.getuid()).pw_name!=C[role+'_user']: raise ValueError('wrong_role')
    words=shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND',''))
    allowed={'status','mcp'} if role=='agent' else {'status','vnc','start','stop','restart'}
    if len(words)!=4 or words[0]!='ownmachine-host' or words[1] not in allowed or words[2:]!=['--vm',C['vm_name']]: raise ValueError('unsupported_operation')
    op=words[1]
    # Always permit a graceful shutdown even if a firewall has drifted.
    if op != 'stop': security_ready()
    tree,state=inspect()
    if op=='status':
        data={}
        flags={key:False for key in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user')}
        if role=='agent' and state=='running':
            p=subprocess.run(guest_argv('status'),env=ENV,capture_output=True,text=True,timeout=15)
            if p.returncode==0:
                data=json.loads(p.stdout.lstrip('\ufeff'));flags={key:data.get(key) is True for key in flags}
        if C.get('require_hardened'):
            flags['bootstrap_hardened']=data.get('bootstrap_hardened') is True
        ready=all(flags.values())
        print(json.dumps(dict(**flags,vm_name=C['vm_name'],vm_uuid=C['vm_uuid'],vm_state={'running':'running','shut off':'stopped'}.get(state,'unknown'),guest_os='windows',guest_profile='windows',backend='kvm',driver_ready=ready,driver_state='ready' if ready else 'not_running')))
        return
    if op=='mcp':
        if state!='running':raise ValueError('vm_not_running')
        probe=subprocess.run(guest_argv('status'),env=ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15,check=True)
        health=json.loads(probe.stdout.lstrip('\ufeff'))
        if not all(health.get(k) is True for k in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user')):
            raise ValueError('interactive_standard_session_required')
        if C.get('require_hardened') and health.get('bootstrap_hardened') is not True:raise ValueError('guest_hardening_required')
        os.execve('/usr/bin/ssh',guest_argv('mcp'),ENV)
    if op in ('start','stop','restart'):
        deadline=time.monotonic()+90
        def wait_for(expected):
            while virsh('domstate',C['vm_uuid']).strip()!=expected:
                if time.monotonic()>deadline:raise ValueError('lifecycle_timeout_no_force_stop')
                time.sleep(1)
        if op in ('stop','restart') and state!='shut off':
            virsh('shutdown',C['vm_uuid']);wait_for('shut off')
        if op in ('start','restart'):
            # After shutdown, inspect persistent XML again; it can differ from
            # the running definition that was checked before shutdown.
            security_ready()
            _,current=inspect()
            if current!='running':virsh('start',C['vm_uuid'])
            wait_for('running')
        print(json.dumps(dict(ok=True,operation=op,vm_state='stopped' if op=='stop' else 'running')))
        return
    graphics=tree.findall('./devices/graphics')
    if state!='running' or len(graphics)!=1 or graphics[0].get('type')!='vnc':raise ValueError('private_console_unavailable')
    listens=graphics[0].findall('listen')
    if len(listens)!=1 or listens[0].get('type')!='socket' or listens[0].get('socket')!=C['console_socket']:raise ValueError('unexpected_console_endpoint')
    path=Path(C['console_socket']); st=path.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_mode & 7 or st.st_uid!=pwd.getpwnam(C['qemu_user']).pw_uid:raise ValueError('unsafe_console_socket')
    parent=path.parent.lstat(); group=grp.getgrnam(C['console_group'])
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=st.st_uid
        or parent.st_gid!=group.gr_gid or parent.st_mode & 7
        or set(group.gr_mem)-{C['viewer_user'],C['qemu_user']}):
        raise ValueError('console_directory_not_private')
    if not os.access(path,os.W_OK):raise ValueError('console_socket_not_writable_'+oct(stat.S_IMODE(st.st_mode)))
    sock=socket.socket(socket.AF_UNIX);sock.connect(str(path))
    sys.stdout.write(json.dumps(dict(transport='private-unix',authentication='none'))+'\n');sys.stdout.flush()
    with sock,selectors.DefaultSelector() as sel:
        sel.register(sock,selectors.EVENT_READ,'console');sel.register(sys.stdin.buffer,selectors.EVENT_READ,'stdin')
        while True:
            for key,_ in sel.select():
                if key.data=='stdin':
                    data=os.read(sys.stdin.fileno(),65536)
                    if not data:return
                    sock.sendall(data)
                else:
                    data=sock.recv(65536)
                    if not data:return
                    sys.stdout.buffer.write(data);sys.stdout.buffer.flush()


def protected(path):
    path=Path(path)
    if not path.is_absolute(): raise ValueError('absolute_root_owned_path_required')
    for item in (path,*path.parents):
        st=item.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o022:
            raise ValueError('unsafe_root_owned_path')
    if not path.is_file(): raise ValueError('regular_file_required')
    return path


def configure(path):
    import uuid
    global C,CONFIG,ROOT
    CONFIG=protected(path)
    C=json.loads(CONFIG.read_text())
    required={'backend','vm_name','vm_uuid','network_uuid','network_name','agent_user','viewer_user','qemu_user',
              'console_group','console_socket','guest_ip','subnet','guest_user','guest_key',
              'guest_known_hosts','driver_executable','guest_health_script','security_helper'}
    if not isinstance(C,dict) or (not required<=set(C) or set(C)-required-{'require_hardened'}) or C['backend']!='kvm':
        raise ValueError('invalid_kvm_configuration')
    for field in ('vm_name','network_name','agent_user','viewer_user','qemu_user','console_group'):
        if not isinstance(C[field],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',C[field]):
            raise ValueError('invalid_kvm_identifier')
    if len({C['agent_user'],C['viewer_user'],C['qemu_user']})!=3: raise ValueError('separate_roles_required')
    for field in ('vm_uuid','network_uuid'):
        if str(uuid.UUID(C[field]))!=C[field]: raise ValueError('canonical_uuid_required')
    net=ipaddress.ip_network(C['subnet'])
    if net.version!=4 or not net.is_private or ipaddress.ip_address(C['guest_ip']) not in net:
        raise ValueError('invalid_guest_network')
    for field in ('console_socket','guest_key','guest_known_hosts','security_helper'):
        if not isinstance(C[field],str) or not Path(C[field]).is_absolute() or any(ord(x)<32 for x in C[field]):
            raise ValueError('invalid_absolute_path')
    if type(C.get('require_hardened',False)) is not bool:raise ValueError('invalid_hardening_gate')
    protected(C['security_helper'])
    protected(C['guest_known_hosts'])
    key=protected(C['guest_key']).stat()
    if key.st_gid!=pwd.getpwnam(C['agent_user']).pw_gid or stat.S_IMODE(key.st_mode)!=0o440:
        raise ValueError('agent_only_guest_key_required')
    agent=pwd.getpwnam(C['agent_user'])
    group=grp.getgrgid(agent.pw_gid)
    if set(group.gr_mem)-{C['agent_user']} or any(u.pw_gid==agent.pw_gid and u.pw_name!=C['agent_user'] for u in pwd.getpwall()):
        raise ValueError('private_agent_group_required')
    ROOT=CONFIG.parent
    guest_argv('status')


def security_ready():
    # sudoers permits only this exact read-only check with this root-owned config.
    result=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3',C['security_helper'],
                           '--check',str(CONFIG)],env=ENV,check=True,capture_output=True,text=True,timeout=15)
    data=json.loads(result.stdout)
    if data != {'ok':True,'vm_uuid':C['vm_uuid']}:
        raise ValueError('live_security_verification_required')


def main(role,path):
    os.umask(0o077)
    configure(path)
    dispatch(role)
    return 0
