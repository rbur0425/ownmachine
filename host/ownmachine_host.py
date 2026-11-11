#!/usr/bin/env python3
"""Restricted host preflight and opt-in guest MCP relay. Run through an SSH forced command.

Operator configuration: ~/.config/ownmachine/host.json (optional).
Supported fields: vm_name (default ownmachine), lume_path (absolute CLI path),
guest_ssh_alias (optional operator-owned guest SSH configuration), enable_mcp (default false).
No addresses, account names or credentials are part of this source.
"""
import secrets
import stat
import fcntl
import socket
import selectors
import sys
from urllib.parse import urlsplit, unquote
import time
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess


def configuration():
    path = Path.home() / '.config/ownmachine/host.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict) or set(data) - {'vm_name', 'lume_path', 'guest_ssh_alias', 'enable_mcp', 'enable_lifecycle', 'display_mode', 'enable_vnc', 'vnc_port', 'storage_dir'}:
        raise ValueError('invalid_host_configuration')
    storage_arguments(data)
    name = data.get('vm_name', 'ownmachine')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', name):
        raise ValueError('invalid_host_configuration')
    binary = data.get('lume_path')
    if binary is not None and (not isinstance(binary, str) or not Path(binary).is_absolute()):
        raise ValueError('invalid_host_configuration')
    guest = data.get('guest_ssh_alias')
    if guest is not None and (not isinstance(guest, str) or
            not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', guest)):
        raise ValueError('invalid_host_configuration')
    if type(data.get('enable_mcp', False)) is not bool:
        raise ValueError('invalid_host_configuration')
    if type(data.get('enable_lifecycle', False)) is not bool or data.get('display_mode','none') not in {'none','native'}:
        raise ValueError('invalid_host_configuration')
    if type(data.get('enable_vnc',False)) is not bool or type(data.get('vnc_port',0)) is not int or not 0<=data.get('vnc_port',0)<=65535:
        raise ValueError('invalid_host_configuration')
    if data.get('enable_vnc') is True and not 1024 <= data.get('vnc_port', 0) <= 65535:
        raise ValueError('fixed_vnc_port_required')
    return name, binary, guest



def storage_arguments(settings):
    value = settings.get('storage_dir')
    if value is None:
        return []
    if not isinstance(value, str) or not Path(value).is_absolute() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('invalid_storage_directory')
    return ['--storage', value]


def selected_storage(settings):
    storage_arguments(settings)
    return Path(settings.get('storage_dir', str(Path.home() / '.lume')))


# Fixed root-owned runtime location: an account-owned config cannot redirect trust.
FIREWALL_STATUS = Path('/private/var/run/ownmachine/firewall-status.json')


def firewall_ready(port, binary=None):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('fixed_vnc_port_required')
    path = FIREWALL_STATUS
    for parent in (path.parent, *path.parent.parents):
        info = parent.lstat()
        # macOS ships /private/var/run as root:daemon 0775. Only that fixed
        # system ancestor may be daemon-group writable; our directory/file may not.
        system_run = parent == Path('/private/var/run') and info.st_gid == 1
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o002
                or (info.st_mode & 0o020 and not system_run)):
            raise ValueError('unsafe_firewall_status')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                or info.st_size > 4096 or not 0 <= time.time() - info.st_mtime <= 45):
            raise ValueError('stale_or_unsafe_firewall_status')
        data = json.load(stream)
    if (not isinstance(data, dict) or data.get('port') != port or data.get('pf_enabled') is not True
            or data.get('rule_loaded') is not True or data.get('application_blocked') is not True):
        raise ValueError('firewall_not_ready')
    if binary is not None:
        resolved = Path(binary).resolve()
        if len(resolved.parents) < 3: raise ValueError('explicit_lume_app_required')
        app = resolved.parents[2]
        if app.suffix != '.app' or Path(binary).resolve() != app / 'Contents/MacOS/lume':
            raise ValueError('explicit_lume_app_required')
        probe = subprocess.run(['/usr/libexec/ApplicationFirewall/socketfilterfw', '--getappblocked', str(app)],
                               capture_output=True, text=True, timeout=5, check=True, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'})
        if 'is blocked.' not in probe.stdout:
            raise ValueError('configured_lume_app_not_blocked')


def private_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('unsafe_private_directory')
    path.chmod(0o700)
    return path


def private_file(path, content=None):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'w') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('unsafe_private_file')
        os.fchmod(stream.fileno(), 0o600)
        if content is not None:
            stream.truncate(0)
            stream.write(content)


def vnc_password(state):
    # Unescaped upstream VNC URLs require this alphabet: 66**8 (~48.4 bits).
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    password = ''.join(secrets.choice(alphabet) for _ in range(8))
    private_file(state / 'vnc-password', password)
    return password


def guest_status(alias, address):
    result = {'guest_reachable': False, 'driver_ready': False,
              'driver_state': 'guest_unreachable', 'accessibility': False,
              'screen_recording': False, 'capture_consent_verified': False}
    try:
        if not isinstance(address, str): return result
        ip = ipaddress.ip_address(address)
        if ip.is_loopback or ip.is_unspecified or ip.is_multicast:
            return result
        # The VM address comes only from Lume's selected guest. The alias supplies
        # operator-owned identity and HostKeyAlias, never model-controlled options.
        argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
                '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=2',
                '-o', 'ServerAliveCountMax=2', '-o', 'HostName=' + str(ip), alias,
                'exec "$HOME/.local/bin/cua-driver" permissions status --json']
        probe = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, timeout=8, check=False)
        if probe.returncode != 0:
            return result
        result['guest_reachable'] = True
        result['driver_state'] = 'invalid_response'
        if len(probe.stdout) > 65536:
            return result
        data = json.loads(probe.stdout)
        if not isinstance(data, dict): return result
        source = data.get('source')
        if not isinstance(source, dict) or source.get('bundle_id') != 'com.trycua.driver':
            return result
        if any(type(data.get(k)) is not bool for k in
               ('accessibility', 'screen_recording', 'daemon_running')):
            return result
        result['accessibility'] = data['accessibility']
        result['screen_recording'] = data['screen_recording']
        verification = data.get('direct_capture_verification')
        # This is a recorded consent check, not a fresh screenshot. Never expose
        # driver paths, errors, process metadata, or desktop contents to status.
        result['capture_consent_verified'] = (isinstance(verification, dict) and
            verification.get('bundle_id') == 'com.trycua.driver' and
            verification.get('source') == 'permissions_grant' and
            isinstance(verification.get('verified_at'), str) and
            bool(verification['verified_at']))
        if not (result['accessibility'] and result['screen_recording']):
            result['driver_state'] = 'permissions_required'
        elif not result['capture_consent_verified']:
            result['driver_state'] = 'capture_consent_required'
        elif not data['daemon_running']:
            result['driver_state'] = 'not_running'
        else:
            result.update(driver_state='ready', driver_ready=True)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        pass
    return result


def status(name='ownmachine', binary=None, guest_alias=None, storage_dir=None):
    candidates = [Path(binary)] if binary else [
        Path.home() / '.local/bin/lume', Path('/opt/homebrew/bin/lume'),
        Path('/usr/local/bin/lume')]
    executable = next((p for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    installed = executable is not None
    vm_state = 'lume_not_installed'
    vm = None
    if executable:
        env = {key: os.environ[key] for key in ('HOME', 'PATH', 'LANG') if key in os.environ}
        env['LUME_TELEMETRY_ENABLED'] = 'false'
        try:
            result = subprocess.run([str(executable), 'ls', '--format', 'json'] + storage_arguments({'storage_dir': storage_dir} if storage_dir else {}), env=env,
                                    capture_output=True, text=True, timeout=5, check=True)
            rows = json.loads(result.stdout)
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise ValueError('invalid_listing')
            vm = next((row for row in rows if row.get('name') == name), None)
            value = vm.get('status') if vm else None
            vm_state = 'absent' if vm is None else (value if value in {'running', 'stopped', 'provisioning'} else 'unknown')
        except (OSError, ValueError, subprocess.SubprocessError):
            vm_state = 'unknown'
    result = {'vm': name, 'host_reachable': True,
            'lume_installed': installed,
            'vm_state': vm_state,
            'driver_ready': False, 'driver_state': 'not_configured' if not guest_alias else 'vm_not_running',
            'viewer_state': 'not_probed', 'controller': 'not_initialized'}
    if guest_alias and vm_state == 'running':
        result.update(guest_status(guest_alias, vm.get('ipAddress')))
    return result


def mcp(name, binary, guest):
    config = json.loads((Path.home()/'.config/ownmachine/host.json').read_text())
    if config.get('enable_mcp') is not True or not guest:
        raise ValueError('mcp_not_enabled')
    candidates = [Path(binary)] if binary else [Path.home()/'.local/bin/lume',
        Path('/opt/homebrew/bin/lume'), Path('/usr/local/bin/lume')]
    executable = next((p for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    if executable is None: raise ValueError('lume_not_installed')
    result = subprocess.run([str(executable), 'ls', '--format', 'json'] + storage_arguments(config),
        capture_output=True, text=True, timeout=5, check=True)
    rows = json.loads(result.stdout)
    if not isinstance(rows, list): raise ValueError('invalid_listing')
    vm = next((x for x in rows if isinstance(x, dict) and x.get('name')==name), None)
    if not vm or vm.get('status') != 'running': raise ValueError('vm_not_running')
    address = vm.get('ipAddress')
    if not isinstance(address, str): raise ValueError('guest_unreachable')
    ip = ipaddress.ip_address(address)
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast: raise ValueError('invalid_guest_address')
    argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes', '-o', 'ConnectTimeout=5',
        '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
        '-o', 'HostName='+str(ip), guest, 'exec "$HOME/.local/lib/ownmachine/driver-mcp.sh"']
    os.execvp('ssh', argv)


def lifecycle(operation, name, binary, guest):
    settings=json.loads((Path.home()/'.config/ownmachine/host.json').read_text())
    if settings.get('enable_lifecycle') is not True or not guest:
        raise ValueError('lifecycle_not_enabled')
    candidates=[Path(binary)] if binary else [Path.home()/'.local/bin/lume',Path('/opt/homebrew/bin/lume'),Path('/usr/local/bin/lume')]
    executable=next((p for p in candidates if p.is_file() and os.access(p,os.X_OK)),None)
    if executable is None:raise ValueError('lume_not_installed')
    env={key:os.environ[key] for key in ('HOME','PATH','LANG') if key in os.environ}
    env['LUME_TELEMETRY_ENABLED']='false'
    def selected():
        probe=subprocess.run([str(executable),'ls','--format','json'] + storage_arguments(settings),env=env,
                             capture_output=True,text=True,timeout=5,check=True)
        rows=json.loads(probe.stdout)
        if not isinstance(rows,list):raise ValueError('invalid_listing')
        vm=next((x for x in rows if isinstance(x,dict) and x.get('name')==name),None)
        if vm is None:raise ValueError('vm_absent') # never let lume run pull/create an image
        return vm
    state=private_directory(Path.home()/'.local/state/ownmachine')
    private_directory(Path.home()/'.lume')
    private_directory(selected_storage(settings))
    with (state/'lifecycle.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        vm=selected()
        if vm.get('status') not in {'running','stopped'}:raise ValueError('vm_state_unknown')
        if operation in {'stop','restart'} and vm['status']=='running':
            address=vm.get('ipAddress')
            if not isinstance(address,str):raise ValueError('guest_unreachable')
            ip=ipaddress.ip_address(address)
            if ip.is_loopback or ip.is_unspecified or ip.is_multicast:raise ValueError('invalid_guest_address')
            command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
                '-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=5',
                '-o','HostName='+str(ip),guest,'exec "$HOME/.local/lib/ownmachine/vm-shutdown.sh"']
            result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=10)
            if result.returncode not in {0,255}:raise ValueError('guest_shutdown_refused')
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                vm=selected()
                if vm.get('status')=='stopped':break
                time.sleep(1)
            else:raise ValueError('guest_shutdown_timeout')
        if operation in {'start','restart'} and vm['status']=='stopped':
            command=[str(executable),'run',name,'--detach','--display',settings.get('display_mode','none'),
                     '--vnc','enabled' if settings.get('enable_vnc') is True else 'disabled']
            log = state / 'lume-detached.log'
            private_file(log)
            command += ['--log-file', str(log)] + storage_arguments(settings)
            if settings.get('enable_vnc') is True:
                firewall_ready(settings.get('vnc_port'), str(executable))
                vnc_password(state)
                command += ['--vnc-port',str(settings['vnc_port']),
                            '--vnc-password-file',str(state/'vnc-password')]
            subprocess.run(command,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=30,check=True)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                vm=selected()
                if vm.get('status')=='running':break
                time.sleep(1)
            else:raise ValueError('vm_start_timeout')
        expected='stopped' if operation=='stop' else 'running'
        if vm.get('status')!=expected:raise ValueError('vm_state_unknown')
        return {'ok':True,'operation':operation,'vm_state':expected}


def vnc(name,binary):
    settings=json.loads((Path.home()/'.config/ownmachine/host.json').read_text())
    if settings.get('enable_vnc') is not True:raise ValueError('vnc_not_enabled')
    private_directory(Path.home()/'.lume')
    private_directory(selected_storage(settings))
    candidates=[Path(binary)] if binary else [Path.home()/'.local/bin/lume',Path('/opt/homebrew/bin/lume'),Path('/usr/local/bin/lume')]
    executable=next((p for p in candidates if p.is_file() and os.access(p,os.X_OK)),None)
    if executable is None:raise ValueError('lume_not_installed')
    firewall_ready(settings.get('vnc_port'), str(executable))
    probe=subprocess.run([str(executable),'ls','--format','json'] + storage_arguments(settings),capture_output=True,text=True,timeout=5,check=True)
    rows=json.loads(probe.stdout)
    vm=next((x for x in rows if isinstance(x,dict) and x.get('name')==name),None)
    if not vm or vm.get('status')!='running':raise ValueError('vm_not_running')
    url=urlsplit(vm.get('vncUrl') or '')
    if url.scheme!='vnc' or url.hostname not in {'127.0.0.1','localhost','::1'} or url.port != settings['vnc_port'] or not url.password:
        raise ValueError('private_vnc_unavailable')
    # Never return this metadata to a model tool or browser. The viewer consumes it
    # over the authenticated SSH pipe and terminates upstream VNC authentication.
    password=unquote(url.password)
    if not re.fullmatch(r'[A-Za-z0-9._~-]{8}', password):
        raise ValueError('invalid_vnc_metadata')
    stored = Path.home()/'.local/state/ownmachine/vnc-password'
    fd = os.open(stored, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size != 8):
            raise ValueError('unsafe_vnc_password')
        if not secrets.compare_digest(password, stream.read(9)):
            raise ValueError('unmanaged_vnc_password')
    with socket.create_connection(('127.0.0.1',url.port),timeout=10) as connection:
        print(json.dumps({'password':password}),flush=True)
        connection.settimeout(None)
        with selectors.DefaultSelector() as selector:
            selector.register(sys.stdin.buffer,selectors.EVENT_READ,'stdin')
            selector.register(connection,selectors.EVENT_READ,'vnc')
            while True:
                firewall_ready(settings['vnc_port'], str(executable))
                for key,_ in selector.select(timeout=5):
                    if key.data=='stdin':
                        data=os.read(sys.stdin.fileno(),65536)
                        if not data:return
                        connection.sendall(data)
                    else:
                        data=connection.recv(65536)
                        if not data:return
                        sys.stdout.buffer.write(data);sys.stdout.buffer.flush()


def main(role='agent'):
    os.umask(0o077)
    try:
        if role not in {'agent','viewer'}:raise ValueError('invalid_role')
        name, binary, guest = configuration()
        allowed = {'status','mcp'} if role == 'agent' else {'status','vnc','start','stop','restart'}
        if os.environ.get('SSH_ORIGINAL_COMMAND') not in {f'ownmachine-host {op} --vm {name}' for op in allowed}:
            print(json.dumps({'code':'unsupported_operation'}))
            return 2
        if os.environ.get('SSH_ORIGINAL_COMMAND') == f'ownmachine-host vnc --vm {name}':
            vnc(name,binary)
            return 0
        for operation in ('start','stop','restart'):
            if os.environ.get('SSH_ORIGINAL_COMMAND') == f'ownmachine-host {operation} --vm {name}':
                print(json.dumps(lifecycle(operation,name,binary,guest)))
                return 0
        if os.environ.get('SSH_ORIGINAL_COMMAND') == f'ownmachine-host mcp --vm {name}':
            mcp(name, binary, guest)
            return 0
        if os.environ.get('SSH_ORIGINAL_COMMAND') != f'ownmachine-host status --vm {name}':
            print(json.dumps({'code': 'unsupported_operation'}))
            return 2
        settings_path = Path.home()/'.config/ownmachine/host.json'
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        print(json.dumps(status(name, binary, guest, settings.get('storage_dir'))))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps({'code': 'invalid_host_configuration'}))
        return 2


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--role',choices=['agent','viewer'],required=True)
    raise SystemExit(main(parser.parse_args().role))
