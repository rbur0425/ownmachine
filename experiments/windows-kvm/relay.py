#!/usr/bin/env python3
"""Spike-only forced command. One configured VM, no shell or arbitrary libvirt calls."""
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

ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'host.json').read_text())
ENV={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'LANG':'C','LC_ALL':'C'}

def virsh(*args):
    return subprocess.run(['/usr/bin/virsh','-c','qemu:///system',*args],env=ENV,check=True,capture_output=True,text=True,timeout=15).stdout

def inspect():
    tree=ET.fromstring(virsh('dumpxml',C['vm_uuid']))
    if tree.findtext('uuid')!=C['vm_uuid'] or tree.findtext('name')!=C['vm_name']: raise ValueError('vm_identity_mismatch')
    return tree,virsh('domstate',C['vm_uuid']).strip()

def guest_argv(operation):
    ip=ipaddress.ip_address(C['guest_ip'])
    if ip not in ipaddress.ip_network(C['subnet']):raise ValueError('guest_outside_network')
    executable=C.get('driver_executable','C:/ProgramData/OwnMachineSpike/driver/cua-driver-rs-0.49.3-windows-x86_64/cua-driver.exe')
    username=C.get('guest_user','ownmachine')
    if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+\.exe',executable) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,19}',username):raise ValueError('invalid_guest_configuration')
    health=C.get('guest_health_script','C:/ProgramData/OwnMachineSpike/health.ps1')
    if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+\.ps1',health):raise ValueError('invalid_guest_health_path')
    command=executable+' mcp --socket \\\\.\\pipe\\cua-driver' if operation=='mcp' else 'powershell -NoProfile -ExecutionPolicy Bypass -File '+health
    return ['/usr/bin/ssh','-F','/dev/null','-T','-i',str(ROOT/'guest-key'),'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=8','-o','UserKnownHostsFile='+str(ROOT/'guest-known-hosts'), username+'@'+str(ip),command]

def main():
    role=sys.argv[1] if len(sys.argv)==2 else ''
    if role not in ('agent','viewer') or pwd.getpwuid(os.getuid()).pw_name!=C[role+'_user']: raise ValueError('wrong_role')
    words=shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND',''))
    allowed={'status','mcp'} if role=='agent' else {'status','vnc','start','stop','restart'}
    if len(words)!=4 or words[0]!='ownmachine-host' or words[1] not in allowed or words[2:]!=['--vm',C['vm_name']]: raise ValueError('unsupported_operation')
    op=words[1];tree,state=inspect()
    if op=='status':
        flags={key:False for key in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user')}
        if role=='agent' and state=='running':
            p=subprocess.run(guest_argv('status'),env=ENV,capture_output=True,text=True,timeout=15)
            if p.returncode==0:
                data=json.loads(p.stdout.lstrip('\ufeff'));flags={key:data.get(key) is True for key in flags}
        ready=all(flags.values())
        print(json.dumps(dict(**flags,vm_name=C['vm_name'],vm_uuid=C['vm_uuid'],vm_state={'running':'running','shut off':'stopped'}.get(state,'unknown'),guest_os='windows',guest_profile='windows',backend='kvm',driver_ready=ready,driver_state='ready' if ready else 'not_running')))
        return
    if op=='mcp':
        if state!='running':raise ValueError('vm_not_running')
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
            if virsh('domstate',C['vm_uuid']).strip()!='running':virsh('start',C['vm_uuid'])
            wait_for('running')
        print(json.dumps(dict(ok=True,operation=op,vm_state='stopped' if op=='stop' else 'running')))
        return
    graphics=tree.findall('./devices/graphics')
    if state!='running' or len(graphics)!=1 or graphics[0].get('type')!='vnc':raise ValueError('private_console_unavailable')
    listens=graphics[0].findall('listen')
    if len(listens)!=1 or listens[0].get('type')!='socket' or listens[0].get('socket')!=C['console_socket']:raise ValueError('unexpected_console_endpoint')
    path=Path(C['console_socket']); st=path.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=pwd.getpwnam('libvirt-qemu').pw_uid:raise ValueError('unsafe_console_socket')
    parent=path.parent.lstat(); group=grp.getgrnam(C['console_group'])
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=st.st_uid
        or parent.st_gid!=group.gr_gid or parent.st_mode & 7
        or set(group.gr_mem)-{C['viewer_user'],'libvirt-qemu'}):
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

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as exc:
        # virsh diagnostics contain no guest credentials; the plugin status
        # parser still exposes only its strict readiness allowlist.
        print(json.dumps(dict(ok=False,error='libvirt_operation_failed',detail=(exc.stderr or '')[:1000])),file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__)),file=sys.stderr)
        sys.exit(1)
