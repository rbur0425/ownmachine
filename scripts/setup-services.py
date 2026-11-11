#!/usr/bin/env python3
"""Explicit operator stages for the Mac relay, guest consent and private viewer."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shlex
import subprocess
import sys
import tarfile
from setup_support import ROOT, mac, module, private_read, install_exact, events

relay = module('setup_host_relay', 'host/ownmachine_host.py')
keys = module('setup_host_keys', 'scripts/render-host-keys.py')
STEPS = ('preflight', 'firewall', 'relay', 'keys', 'driver', 'permissions', 'viewer', 'verify')
MUTATIONS = {'relay', 'keys', 'driver', 'viewer'}
FIELDS = {'vm_name', 'storage_dir', 'lume_app', 'vnc_port', 'guest_ssh_alias', 'python',
          'agent_public_key', 'viewer_public_key', 'agent_host_alias', 'viewer_host_alias',
          'control_dir', 'access_dir', 'viewer_port', 'viewer_python'}


def config(path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) - FIELDS:
        raise ValueError('invalid_service_configuration')
    data = {**dict(vm_name='ownmachine', vnc_port=0, viewer_port=0, python=sys.executable,
                viewer_python=sys.executable), **data}
    for name, value in data.items():
        if name.endswith('port'):
            if type(value) is not int or not 0 <= value <= 65535:
                raise ValueError('invalid_port')
        elif not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError('invalid_text')
        elif name.endswith('alias') or name == 'vm_name':
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
                raise ValueError('invalid_identifier')
        elif not Path(value).is_absolute():
            raise ValueError('absolute_paths_required')
    return data


def call(argv, *, data=None, timeout=60):
    return subprocess.run(argv, input=data, capture_output=True, timeout=timeout, check=True,
                          env=dict(os.environ, LUME_TELEMETRY_ENABLED='false'))


def binary(c):
    app = Path(c['lume_app'])
    if app.suffix != '.app': raise ValueError('lume_app_required')
    return app / 'Contents/MacOS/lume'


def host_settings(c):
    if not 1024 <= c['vnc_port'] <= 65535: raise ValueError('fixed_vnc_port_required')
    return dict(vm_name=c['vm_name'], storage_dir=c['storage_dir'], lume_path=str(binary(c)),
                guest_ssh_alias=c['guest_ssh_alias'], enable_mcp=True, enable_lifecycle=True,
                enable_vnc=True, vnc_port=c['vnc_port'], display_mode='none')


def firewall(c):
    relay.firewall_ready(c['vnc_port'], str(binary(c)))


def guest_address(c):
    import ipaddress
    rows = json.loads(call([str(binary(c)), 'ls', '--format', 'json', '--storage', c['storage_dir']]).stdout)
    matches = [row for row in rows if row.get('name') == c['vm_name']]
    if len(matches) != 1 or matches[0].get('status') != 'running':
        raise ValueError('selected_guest_not_running')
    address = ipaddress.ip_address(matches[0].get('ipAddress', ''))
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        raise ValueError('invalid_guest_address')
    return str(address)


def guest_argv(c):
    return ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'IdentitiesOnly=yes', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
            '-o', 'ConnectTimeout=10', '-o', 'HostName=' + guest_address(c), c['guest_ssh_alias']]


def desired_relay(c):
    return ((Path.home()/'.local/lib/ownmachine/ownmachine_host.py', (ROOT/'host/ownmachine_host.py').read_bytes()),
            (Path.home()/'.config/ownmachine/host.json', json.dumps(host_settings(c), sort_keys=True).encode()))


def key_lines(c):
    return keys.render(c['python'], Path.home()/'.local/lib/ownmachine/ownmachine_host.py',
                       Path(c['agent_public_key']).read_text(), Path(c['viewer_public_key']).read_text()).splitlines()


def install_keys(c):
    lines = key_lines(c)
    path = Path.home()/'.ssh/authorized_keys'
    mac.private_dir(path.parent)
    current = private_read(path).decode() if path.exists() or path.is_symlink() else ''
    for line in lines:
        blob = line.split(' ssh-ed25519 ', 1)[1].split()[0]
        occurrences = [old for old in current.splitlines() if blob in old.split()]
        if occurrences and occurrences != [line]:
            raise ValueError('public_key_already_has_different_authorization')
    missing = [line for line in lines if line not in current.splitlines()]
    if missing:
        # Atomic replacement; preserve unrelated administrator/operator entries.
        import tempfile
        fd, name = tempfile.mkstemp(dir=path.parent, prefix='.ownmachine-keys-')
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(current.rstrip('\n') + ('\n' if current else '') + '\n'.join(missing) + '\n')
                stream.flush(); os.fsync(stream.fileno())
            # Refuse a concurrent edit rather than losing someone else's key.
            now = private_read(path).decode() if path.exists() or path.is_symlink() else ''
            if now != current: raise ValueError('authorized_keys_changed')
            os.replace(name, path)
        finally:
            if os.path.exists(name): os.unlink(name)


def install_driver(c):
    # Only reviewed fixed-name scripts are sent over already pinned, key-only SSH.
    names = ('install-guest-driver.sh', 'install-permission-guide.sh', 'install-guest-mcp.sh')
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w') as tar:
        for name in names:
            content = (ROOT/'scripts'/name).read_bytes()
            info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o600
            tar.addfile(info, io.BytesIO(content))
    suffix = hashlib.sha256(archive.getvalue()).hexdigest()[:16]
    directory = '"$HOME/.local/share/ownmachine/setup-' + suffix + '"'
    command = ('set -eu; umask 077; mkdir -p ' + directory + '; /usr/bin/tar -xf - -C ' + directory +
               '; /bin/bash ' + directory + '/install-guest-driver.sh; /bin/bash ' + directory + '/install-guest-mcp.sh')
    call(guest_argv(c) + [command], data=archive.getvalue(), timeout=900)


def viewer_files(c):
    from ownmachine.config import Config
    cfg = Config(c['viewer_host_alias'], c['control_dir'], c['vm_name']).validate()
    access, control = Path(c['access_dir']).resolve(), Path(c['control_dir']).resolve()
    if access == control or access in control.parents or control in access.parents:
        raise ValueError('viewer_access_must_be_separate')
    if platform.system() == 'Darwin':
        argv = [c['viewer_python'], str(ROOT/'viewer/server.py'), '--host-alias', cfg.host_alias,
                '--vm-name', cfg.vm_name, '--control-dir', cfg.control_dir, '--access-dir', c['access_dir'], '--port', str(c['viewer_port'])]
        data = dict(Label='org.ownmachine.viewer', ProgramArguments=argv, RunAtLoad=True,
                    KeepAlive={'SuccessfulExit': False}, ThrottleInterval=10, Umask=0o077,
                    StandardOutPath=str(access/'service.log'), StandardErrorPath=str(access/'service-error.log'))
        return Path.home()/'Library/LaunchAgents/org.ownmachine.viewer.plist', plistlib.dumps(data)
    if platform.system() == 'Linux':
        renderer = module('setup_viewer_renderer', 'scripts/render-viewer-service.py')
        return Path.home()/'.config/systemd/user/ownmachine-viewer.service', renderer.render(ROOT, Path(c['viewer_python']), cfg, c['viewer_port'], access_dir=access).encode()
    raise ValueError('unsupported_viewer_supervisor')


def viewer_check(c, probe=False):
    argv = [c['viewer_python'], str(ROOT/'scripts/ownmachine-viewer-doctor.py'),
            '--host-alias', c['viewer_host_alias'], '--vm-name', c['vm_name'],
            '--control-dir', c['control_dir'], '--access-dir', c['access_dir'], '--json']
    if probe: argv.append('--probe-vnc')
    result = json.loads(call(argv, timeout=90).stdout)
    if result.get('ok') is not True: raise ValueError('viewer_not_ready')


def verify(step, c):
    if step == 'relay':
        for path, expected in desired_relay(c):
            if private_read(path) != expected: raise ValueError('relay_installation_differs')
    elif step == 'keys':
        installed = private_read(Path.home()/'.ssh/authorized_keys').decode().splitlines()
        for line in key_lines(c):
            blob = line.split(' ssh-ed25519 ', 1)[1].split()[0]
            if [old for old in installed if blob in old.split()] != [line]:
                raise ValueError('restricted_key_verification_failed')
    elif step == 'driver':
        command = 'test "$("$HOME/.local/bin/cua-driver" --version)" = "cua-driver 0.44.0" && test -f "$HOME/Library/LaunchAgents/org.ownmachine.permission-guide.plist" && test -x "$HOME/.local/lib/ownmachine/driver-mcp.sh"'
        call(guest_argv(c) + [command])
    elif step == 'permissions':
        result = relay.guest_status(c['guest_ssh_alias'], guest_address(c))
        if not result['driver_ready']: raise ValueError('guest_permission_or_capture_consent_required')
    elif step == 'firewall':
        firewall(c)
    elif step == 'viewer':
        path, expected = viewer_files(c)
        if private_read(path) != expected: raise ValueError('viewer_service_differs')
        viewer_check(c)
    elif step == 'verify':
        from ownmachine.config import Config
        for alias, role in ((c['agent_host_alias'], 'agent'), (c['viewer_host_alias'], 'viewer')):
            cfg = Config(alias, c['control_dir'], c['vm_name'])
            result = json.loads(call(cfg.ssh_argv('status')).stdout)
            if result.get('vm_state') != 'running' or result.get('driver_ready') is not True:
                raise ValueError('runtime_not_ready')
            # Exercise rejection without invoking a permitted operation or mutation.
            argv = cfg.ssh_argv('status')[:-4] + ['ownmachine-denied-operation']
            denied = subprocess.run(argv, capture_output=True, timeout=30)
            if denied.returncode != 2 or json.loads(denied.stdout).get('code') != 'unsupported_operation':
                raise ValueError('runtime_key_not_restricted')
            forbidden = 'vnc' if role == 'agent' else 'mcp'
            denied = subprocess.run(cfg.ssh_argv(forbidden), stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
            if denied.returncode != 2 or json.loads(denied.stdout).get('code') != 'unsupported_operation':
                raise ValueError('runtime_roles_not_separated')
        viewer_check(c, probe=True)


def preflight_mutation(step, c):
    # Missing prerequisites are safe to fix and retry: no running checkpoint yet.
    if step == 'relay':
        firewall(c)
        mac.verify_build(Path(c['lume_app']))
        host_settings(c)
    elif step == 'keys':
        verify('relay', c)
        key_lines(c)
    elif step == 'driver':
        call(guest_argv(c) + ['test "$(/usr/bin/id -u)" -ne 0 && /usr/bin/sw_vers -productVersion'])
    elif step == 'viewer':
        viewer_files(c)
        call([c['viewer_python'], '-c', 'from Crypto.Cipher import DES'])


def apply(step, c):
    if step == 'relay':
        mac.private_dir(Path(c['storage_dir']))
        for path, content in desired_relay(c): install_exact(path, content)
    elif step == 'keys':
        install_keys(c)
    elif step == 'driver':
        install_driver(c)
    elif step == 'viewer':
        path, content = viewer_files(c)
        mac.private_dir(Path(c['access_dir']))
        install_exact(path, content)
        if platform.system() == 'Darwin':
            call(['/bin/launchctl', 'bootstrap', 'gui/' + str(os.getuid()), str(path)])
        else:
            call(['systemctl', '--user', 'daemon-reload'])
            call(['systemctl', '--user', 'enable', '--now', 'ownmachine-viewer.service'])
        # Startup is asynchronous; check readiness with a bounded wait.
        import time
        for attempt in range(20):
            try:
                viewer_check(c)
                break
            except (ValueError, subprocess.SubprocessError, OSError):
                if attempt == 19: raise
                time.sleep(1)


def execute(args):
    c = config(args.config)
    step = args.step
    if os.geteuid() == 0: raise ValueError('run_as_dedicated_non_root_account')
    if step not in ('viewer', 'verify') and (platform.system() != 'Darwin' or platform.machine() != 'arm64'):
        raise ValueError('run_on_apple_silicon_mac')
    if step == 'preflight':
        import shutil
        path = Path(c['storage_dir'])
        while not path.exists(): path = path.parent
        return dict(ok=True, step=step, stage='observed', machine=platform.machine(),
                    free_gib=round(shutil.disk_usage(path).free/1024**3, 2),
                    swift_available=call(['/usr/bin/xcrun', '--find', 'swift']).returncode == 0,
                    scope='Actual host observation; guest, ports and runtime identities still need checks.')
    if not args.apply and step in MUTATIONS:
        return dict(ok=True, step=step, stage='planned', next='Review configuration, then explicitly apply on the correct account.')
    if step not in MUTATIONS:
        if step == 'permissions' and args.apply:
            command = ('uid=$(/usr/bin/id -u); domain=gui/$uid; '
                       '/bin/launchctl print "$domain/org.ownmachine.permission-guide" >/dev/null 2>&1 || '
                       '/bin/launchctl bootstrap "$domain" "$HOME/Library/LaunchAgents/org.ownmachine.permission-guide.plist"; '
                       '/bin/launchctl kickstart "$domain/org.ownmachine.permission-guide"')
            call(guest_argv(c) + [command])
        verify(step, c)
        return dict(ok=True, step=step, stage='checks_passed',
                    scope='Readiness only; browser input, external firewall and desktop task acceptance remain manual.')
    state = Path.home()/'.local/state/ownmachine'/c['vm_name']/'setup'
    mac.private_dir(state)
    identity = mac.digest(dict(config=c, source={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for base in ('scripts', 'host', 'viewer', 'plugin') for p in sorted((ROOT/base).rglob('*'))
                           if p.is_file() and '__pycache__' not in p.parts}))
    checkpoint = state / ('service-' + step + '.json')
    fd = os.open(state/'execution.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        old = mac.read_state(checkpoint)
        if old:
            if old.get('identity') != identity or old['stage'] != 'verified':
                raise ValueError('previous_execution_requires_inspection')
            verify(step, c)
            return dict(ok=True, step=step, stage='verified', replayed=False)
        preflight_mutation(step, c)
        record = dict(schema_version=1, identity=identity, stage='running')
        mac.write_state(checkpoint, record)
        try:
            apply(step, c)
            verify(step, c)
        except BaseException:
            mac.write_state(checkpoint, dict(record, stage='needs_inspection'))
            raise
        mac.write_state(checkpoint, dict(record, stage='verified'))
        return dict(ok=True, step=step, stage='verified', desktop_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--step', choices=STEPS, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--events', action='store_true', help='NDJSON liveness events while a step runs; no raw logs')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        with events(args.events, args.step): result = execute(args)
        print(json.dumps(result), flush=True)
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch('[a-z_]+', str(exc)) else 'operation_failed'
        print(json.dumps(dict(ok=False, step=args.step, stage='needs_attention', code=code,
                             next='Check required configuration and the stage guide; uncertain mutations require inspection. No destructive retry.')))
        return 2


if __name__ == '__main__': raise SystemExit(main())
