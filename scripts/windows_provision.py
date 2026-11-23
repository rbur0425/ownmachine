"""Reviewed Windows inputs, resumable artifact preparation and guest stages."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time
import uuid
from setup_support import ROOT, private_read, install_exact, mac

DRIVER_SHA256='1f8caf9b0a5577c559d95f12cfc55584bad32edffe5b49f5e700ed3ddc573566'
ENV={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}


def run(argv,timeout=60,**kwargs):
    return subprocess.run(argv,env=ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,check=True,timeout=timeout,**kwargs)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def settings(c,plan):
    p=c.get('provision')
    required={'vm_uuid','network_uuid','bridge','subnet','guest_ip','dns_server','windows_iso','windows_iso_sha256',
              'driver_zip','accept_evaluation_terms','operator_user','agent_user','viewer_user','qemu_user','console_group',
              'console_socket','host_address','host_known_hosts','runtime_prefix','guest_user','guest_setup_user','guest_install_root',
              'viewer_python','viewer_control_dir','access_dir','viewer_port'}
    linux=plan.get('guest_profile')=='omarchy-kvm'
    if linux:
        required -= {'windows_iso','windows_iso_sha256','driver_zip','accept_evaluation_terms','guest_setup_user','guest_install_root'}
        required |= {'image','driver_archive','input_archive','cmake_wheel','ninja_wheel','firmware_code','firmware_vars'}
    if not isinstance(p,dict) or (not required<=set(p) or set(p)-required-({'guestfs_appliance'} if linux else set())-{'host_ssh_port','ssh_service','viewer_swap_red_blue','display_idle_minutes','sleep_idle_minutes','time_zone','time_servers'}):raise ValueError('explicit_windows_provisioning_configuration_required')
    if not linux and p['accept_evaluation_terms'] is not True:raise ValueError('evaluation_terms_consent_required')
    for name in ('display_idle_minutes','sleep_idle_minutes'):
        if type(p.get(name,0)) is not int or not 0<=p.get(name,0)<=1440:raise ValueError('invalid_guest_idle_minutes')
    if not isinstance(p.get('time_zone','UTC'),str) or not re.fullmatch(r'[A-Za-z0-9 ()_+.-]{1,80}',p.get('time_zone','UTC')):raise ValueError('invalid_guest_time_zone')
    peers=p.get('time_servers',['time.windows.com'])
    if not isinstance(peers,list) or not 1<=len(peers)<=5 or any(not isinstance(x,str) or len(x)>253 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',x) for x in peers):raise ValueError('invalid_time_servers')
    for name in ('operator_user','agent_user','viewer_user','qemu_user','console_group','guest_user') + (() if linux else ('guest_setup_user',)):
        if not isinstance(p[name],str) or not re.fullmatch('[a-z][a-z0-9_-]{0,19}',p[name]):raise ValueError('invalid_account')
    if len({p[k] for k in ('operator_user','agent_user','viewer_user','qemu_user')})!=4 or (not linux and p['guest_user']==p['guest_setup_user']):raise ValueError('separate_accounts_required')
    for name in ('vm_uuid','network_uuid'):
        if str(uuid.UUID(p[name]))!=p[name]:raise ValueError('canonical_uuid_required')
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,14}',p['bridge']):raise ValueError('invalid_bridge')
    net=ipaddress.ip_network(p['subnet']);guest=ipaddress.ip_address(p['guest_ip'])
    if net.version!=4 or not net.is_private or guest not in net or guest in (net.network_address,net.broadcast_address,net.network_address+1):raise ValueError('invalid_network')
    ipaddress.ip_address(p['dns_server'])
    if not re.fullmatch('[A-Za-z0-9.-]+',p['host_address']):raise ValueError('invalid_host_address')
    if type(p.get('host_ssh_port',22)) is not int or not 1<=p.get('host_ssh_port',22)<=65535:raise ValueError('invalid_host_port')
    if not re.fullmatch('[A-Za-z0-9_-]+',p.get('ssh_service','ssh')):raise ValueError('invalid_ssh_service')
    for name in ('host_known_hosts','runtime_prefix','console_socket','viewer_python','viewer_control_dir','access_dir') + (('image','driver_archive','input_archive','cmake_wheel','ninja_wheel','firmware_code','firmware_vars') if linux else ('windows_iso','driver_zip')):
        value=p[name]
        if not isinstance(value,str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value) or '..' in Path(value).parts:raise ValueError('safe_absolute_path_required')
    if 'guestfs_appliance' in p and not Path(p['guestfs_appliance']).is_absolute():raise ValueError('absolute_appliance_path_required')
    if not linux and not re.fullmatch(r'C:/[A-Za-z0-9_/-]+',p['guest_install_root']):raise ValueError('invalid_guest_install_root')
    if type(p.get('viewer_swap_red_blue',False)) is not bool:raise ValueError('invalid_viewer_color_override')
    if type(p['viewer_port']) is not int or not 0<=p['viewer_port']<=65535:raise ValueError('invalid_viewer_port')
    if not linux and not re.fullmatch('[a-f0-9]{64}',p['windows_iso_sha256']):raise ValueError('verified_windows_media_required')
    if set(p) & set(plan):raise ValueError('ambiguous_provisioning_configuration')
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',plan['vm_name']):raise ValueError('invalid_vm_name')
    for name in ('storage_dir',):
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+',plan[name]) or '..' in Path(plan[name]).parts:raise ValueError('safe_absolute_path_required')
    return {'display_idle_minutes':0,'sleep_idle_minutes':0,'time_zone':'UTC','time_servers':['time.windows.com'],**p,**plan}


def write(path,obj):
    install_exact(path,(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode())


def build(c,plan):
    p=settings(c,plan);state=Path(plan['storage_dir'])
    mac.private_dir(state)
    identity=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()
    receipt=state/'build.json'
    if receipt.exists():
        saved=json.loads(private_read(receipt))
        if saved['identity']!=identity:raise ValueError('build_configuration_changed')
        for name,digest in saved['files'].items():
            if sha(state/name)!=digest:raise ValueError('built_artifact_changed')
        return
    # Refuse adoption or replay of an uncertain build. No existing disk is touched.
    if any(state.iterdir()):raise ValueError('nonempty_fresh_build_directory')
    write(state/'build-intent.json',{'identity':identity})
    linux=plan.get('guest_profile')=='omarchy-kvm'
    if not linux and (sha(p['windows_iso'])!=p['windows_iso_sha256'] or sha(p['driver_zip'])!=DRIVER_SHA256):raise ValueError('installation_media_hash_mismatch')
    for name in ('agent','viewer','guest','guest-setup','guest-host'):
        run(['ssh-keygen','-t','ed25519','-N','','-C','ownmachine-'+name,'-f',str(state/name)])
    python=Path(p['viewer_python'])
    if python.name!='python' or python.parent.name!='bin':raise ValueError('viewer_venv_python_required')
    if not python.exists():
        if python.parent.parent.exists():raise ValueError('existing_viewer_environment_requires_inspection')
        run([sys.executable,'-m','venv',str(python.parent.parent)],timeout=120)
        run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(ROOT/'viewer/requirements.txt')],timeout=300)
    run([str(python),'-c',"import importlib.metadata; assert importlib.metadata.version('pycryptodome')=='3.23.0'"])
    # A media hash is mandatory; firmware selection remains libvirt-managed.
    config={**p,'storage_dir':str(state)};write(state/'render.json',config)
    if linux:
        from omarchy_kvm import prepare_disk
        prepare_disk(state,p)
    else:
        run([sys.executable,str(ROOT/'scripts/windows/render-seed.py'),'--config',str(state/'render.json'),'--private-dir',str(state),
             '--driver-zip',p['driver_zip'],'--driver-sha256',DRIVER_SHA256,'--output',str(state/'seed'),'--accept-evaluation-terms'],timeout=300)
        guest=json.loads(private_read(state/'seed/guest.json'))
        install_exact(state/'guest-password',(guest['desktop_password']+'\n').encode())
        run(['xorriso','-as','mkisofs','-J','-r','-V','OWNBOOT','-o',str(state/'bootstrap.iso'),str(state/'seed')],timeout=300)
    run([sys.executable,str(ROOT/'scripts/windows/render-domain.py'),str(state/'render.json'),str(state)])
    pub=(state/'guest-host.pub').read_text().split()
    install_exact(state/'guest-known-hosts',(p['guest_ip']+' '+pub[0]+' '+pub[1]+'\n').encode())
    install_exact(state/'host-known-hosts',Path(p['host_known_hosts']).read_bytes())
    blocks=[]
    for role in ('agent','viewer'):
        alias=c[role+'_alias']
        blocks.append(f"Host {alias}\n HostName {p['host_address']}\n Port {p.get('host_ssh_port',22)}\n User {p[role+'_user']}\n IdentityFile {state/role}\n UserKnownHostsFile {state/'host-known-hosts'}\n IdentitiesOnly yes\n IdentityAgent none\n StrictHostKeyChecking yes\n BatchMode yes\n ForwardAgent no\n ClearAllForwardings yes\n")
    blocks.append(f"Host ownmachine-guest-setup\n HostName {p['guest_ip']}\n User {p.get('guest_setup_user',p['guest_user'])}\n IdentityFile {state/'guest-setup'}\n UserKnownHostsFile {state/'guest-known-hosts'}\n IdentitiesOnly yes\n IdentityAgent none\n StrictHostKeyChecking yes\n BatchMode yes\n ForwardAgent no\n ClearAllForwardings yes\n")
    install_exact(Path(c['ssh_config']),('\n'.join(blocks)).encode())
    # Viewer uses its owner's OpenSSH config through a small fixed wrapper.
    wrapper=state/'ssh-bin';wrapper.mkdir(mode=0o700)
    import shlex
    install_exact(wrapper/'ssh',('#!/bin/sh\nexec /usr/bin/ssh -F '+shlex.quote(c['ssh_config'])+' "$@"\n').encode());(wrapper/'ssh').chmod(0o700)
    runtime=runtime_settings(p,plan,state)
    write(state/'install.json',dict(runtime=runtime,bridge=p['bridge']))
    files={name:sha(state/name) for name in ('domain.xml','network.xml','omarchy.qcow2' if linux else 'bootstrap.iso','install.json')}
    write(receipt,dict(identity=identity,files=files))


def runtime_settings(p, plan, state):
    runtime={k:p[k] for k in ('vm_uuid','network_uuid','agent_user','viewer_user','qemu_user','console_group','console_socket','guest_ip','subnet','guest_user')}
    runtime.update(backend='kvm',vm_name=plan['vm_name'],network_name=plan['vm_name'],guest_key=str(state/'guest'),guest_known_hosts=str(state/'guest-known-hosts'),
                   driver_executable=p.get('guest_install_root','')+'/driver/cua-driver-rs-0.49.3-windows-x86_64/cua-driver.exe',guest_health_script=p.get('guest_install_root','')+'/health.ps1',require_hardened=True)
    if plan.get('guest_profile') == 'omarchy-kvm':
        runtime.pop('guest_health_script')
        runtime.pop('driver_executable')
        runtime['guest_profile']='omarchy-kvm'
    return runtime


def guest(c,operation):
    timeout = 120
    if operation == 'driver':
        # Omarchy configures, compiles and tests the module (up to 1800s each).
        timeout = 6900 if c.get('_profile') == 'omarchy-kvm' else 1800
    result=run(['ssh','-F',c['ssh_config'],'-T','ownmachine-guest-setup','ownmachine-guest '+operation],timeout=timeout)
    if len(result.stdout)>65536:raise ValueError('oversized_guest_response')
    return json.loads(result.stdout.lstrip('\ufeff'))


def empty_cdrom(disk):
    # Live libvirt XML can retain an index-only source after successful eject.
    # Never treat file/device/network attributes or child elements as empty.
    source=disk.find('source')
    return source is None or (set(source.attrib)<= {'index'}
        and ('index' not in source.attrib or source.get('index').isdigit())
        and not len(source) and not (source.text or '').strip())


def media_ejected(c):
    import xml.etree.ElementTree as ET
    runtime=json.loads(Path(c['runtime_config']).read_text())
    for flags in ([],['--inactive']):
        # XML is generated by local libvirt via fixed virsh commands, not guest/network XML.
        tree=ET.fromstring(run(['virsh','-c','qemu:///system','dumpxml',runtime['vm_uuid'],*flags]).stdout)
        if not all(empty_cdrom(d) for d in tree.findall('./devices/disk') if d.get('device')=='cdrom'):
            return False
    return True


def eject(c):
    runtime=json.loads(Path(c['runtime_config']).read_text())
    import xml.etree.ElementTree as ET
    # XML is generated by local libvirt via fixed virsh commands, not guest/network XML.
    tree=ET.fromstring(run(['virsh','-c','qemu:///system','dumpxml',runtime['vm_uuid']]).stdout)
    if tree.findtext('name')!=c['vm_name']:raise ValueError('domain_mismatch')
    for disk in tree.findall('./devices/disk'):
        if disk.get('device')=='cdrom' and not empty_cdrom(disk):
            target=disk.find('target').get('dev')
            if target not in ('sdb','sdc'):raise ValueError('unexpected_media_target')
            run(['virsh','-c','qemu:///system','change-media',runtime['vm_uuid'],target,'--eject','--live','--config'])
    if not media_ejected(c):raise ValueError('installation_media_still_attached')


def user_unit(*args):
    env={**ENV,'XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(os.getuid())+'/bus'}
    return subprocess.run(['systemctl','--user',*args],env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,check=True,timeout=30)


def viewer_argv(c,p):
    argv=[p['viewer_python'],str(ROOT/'viewer/server.py'),'--host-alias',c['viewer_alias'],'--vm-name',p['vm_name'],
          '--guest-profile',p.get('guest_profile','windows'),'--console-transport','private-unix','--control-dir',p['viewer_control_dir'],
          '--access-dir',p['access_dir'],'--port',str(p['viewer_port'])]
    if p.get('viewer_swap_red_blue',False):argv.append('--swap-red-blue')
    return argv


def viewer(c,plan,apply):
    p=settings(c,plan);state=Path(plan['storage_dir']);unit='ownmachine-viewer-'+plan['vm_name']+'.service'
    if apply:
        if plan.get('guest_profile')=='omarchy-kvm':
            # SQLite normally creates a 0644 database; that masks a named
            # Hermes writer in a default ACL even when the directory is shared.
            control=Path(p['viewer_control_dir'])
            control.mkdir(mode=0o700,parents=True,exist_ok=True)
            if any(x.is_symlink() for x in (control,*control.parents)) or control.stat().st_mode & 7:
                raise ValueError('private_shared_control_directory_required')
            try:
                fd=os.open(control/'lease.db',os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_RDWR,0o660)
            except FileExistsError:
                if (control/'lease.db').is_symlink() or not (control/'lease.db').is_file():
                    raise ValueError('invalid_existing_control_database')
            else:
                os.close(fd)
        import shlex
        argv=viewer_argv(c,p)
        # Values contain no control chars or systemd expansion operators.
        content='[Unit]\nDescription=OwnMachine private KVM viewer\n[Service]\nEnvironment=PATH='+str(state/'ssh-bin')+':/usr/bin:/bin\nExecStart='+shlex.join(argv)+'\nRestart=on-failure\n[Install]\nWantedBy=default.target\n'
        path=Path.home()/'.config/systemd/user'/unit;install_exact(path,content.encode())
        user_unit('daemon-reload');user_unit('enable','--now',unit)
    user_unit('is-active',unit)


def console(c):
    # Probe only this configured viewer key. No token or GUI frame leaves the host.
    proc=subprocess.Popen(['ssh','-F',c['ssh_config'],'-T',c['viewer_alias'],'ownmachine-host vnc --vm '+c['vm_name']],env=ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    data=b'';deadline=time.monotonic()+20
    try:
        with selectors.DefaultSelector() as sel:
            sel.register(proc.stdout,selectors.EVENT_READ)
            while time.monotonic()<deadline:
                if not sel.select(max(0,deadline-time.monotonic())):break
                chunk=os.read(proc.stdout.fileno(),4096)
                if not chunk:break
                data+=chunk
                if len(data)>8192:raise ValueError('invalid_console_response')
                if b'\n' in data:
                    line,rfb=data.split(b'\n',1)
                    if len(rfb)>=12:
                        if json.loads(line)!={'transport':'private-unix','authentication':'none'} or not re.fullmatch(rb'RFB 003\.00[378]\n',rfb[:12]):raise ValueError('private_console_required')
                        return
        raise ValueError('private_console_unavailable')
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        for f in (proc.stdin,proc.stdout):f.close()


def retire(c,state):
    marker=state/'windows-retirement.json'
    linux = c.get('_profile') == 'omarchy-kvm'
    if marker.exists() and not linux:
        raise ValueError('guest_retirement_requires_inspection')
    previous = json.loads(private_read(marker)) if marker.exists() else {}
    binding = {'vm_uuid': c['_vm_uuid'], 'ssh_config_sha256': sha(c['ssh_config'])} if linux else {}
    if previous and (any(previous.get(k) != v for k,v in binding.items())
                     or previous.get('stage') not in {'retiring', 'rejected', 'retired'}):
        raise ValueError('guest_retirement_requires_inspection')
    if previous.get('stage') == 'retired':
        return
    if previous.get('stage') != 'rejected':
        attempt = dict(binding, stage='retiring')
        if linux:
            attempt['key_sha256'] = hashlib.sha256(private_read(Path(c['storage_dir'])/'guest-setup')).hexdigest()
        if previous and previous != attempt:
            raise ValueError('guest_retirement_requires_inspection')
        mac.write_state(marker,attempt)
        try:
            result=guest(c,'retire')
        except subprocess.CalledProcessError as exc:
            # A previous attempt may already have revoked this exact key.
            if not previous or exc.returncode != 255:
                raise
        else:
            if result!={'ok':True,'retired':True}:raise ValueError('guest_retirement_failed')
        check=subprocess.run(['ssh','-F',c['ssh_config'],'-T','ownmachine-guest-setup','ownmachine-guest status'],env=ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
        if check.returncode!=255 or 'Permission denied' not in check.stderr:raise ValueError('guest_setup_key_rejection_not_proven')
        if linux:
            mac.write_state(marker,dict(binding,stage='rejected'))
    # Remove only known temporary installation artifacts after positive rejection.
    # VM disks, runtime viewer credentials and the operator's login password stay.
    import shutil
    storage=Path(c['storage_dir'])
    if storage.is_symlink():raise ValueError('symlink_storage_refused')
    for name in ('guest-setup','guest-host','bootstrap.iso'):
        path=storage/name
        if path.is_symlink():raise ValueError('symlink_artifact_refused')
        path.unlink(missing_ok=True)
    seed=storage/'seed'
    if seed.is_symlink():raise ValueError('symlink_artifact_refused')
    if seed.exists():shutil.rmtree(seed)
    mac.write_state(marker,dict(binding,stage='retired',guest_key_rejected=True,bootstrap_artifacts_removed=True))
