#!/usr/bin/env python3
"""Operator-side, resumable native build and macOS provisioning. Never runs sudo."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))
from ownmachine.onboarding import DEFAULTS, FIELDS, validate_plan

REVISION = '666c196f42dc9c83dbe075e20318f16c3e3a6d84'
PATCHES = ('lume-0.7.0-key-clipboard.patch', 'lume-0.7.0-private-vnc-password.patch')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def private_dir(path):
    if not path.is_absolute():
        raise ValueError('Paths must be absolute')
    for item in reversed((path, *path.parents)):
        if item.is_symlink():
            raise ValueError('Symlink directory refused')
        if not item.exists():
            item.mkdir(mode=0o700)
    stat = path.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError('Execution directories must be owned by this account and mode 0700')


def write_state(path, state):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.checkpoint-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(state, out, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_state(path):
    if any(p.is_symlink() for p in path.parents):
        raise ValueError('Symlink checkpoint directory refused')
    if not path.exists() and not path.is_symlink():
        return None
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        import stat
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 65536:
            raise ValueError('Unsafe checkpoint')
        result = json.load(stream)
    if not isinstance(result, dict) or result.get('schema_version') != 1 or result.get('stage') not in ('running', 'verified', 'needs_inspection'):
        raise ValueError('Unknown checkpoint; preserved for inspection')
    return result


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, timeout=60, capture_output=True, text=True,
                          env=dict(os.environ, LUME_TELEMETRY_ENABLED='false'), **kwargs)


def verify_build(app):
    resources = app / 'Contents/Resources'
    if (resources / 'ownmachine-upstream-revision').read_text().strip() != REVISION:
        raise ValueError('Unexpected Lume revision')
    actual = [line.split()[0] for line in (resources / 'ownmachine-patch-sha256').read_text().splitlines()]
    expected = [hashlib.sha256((ROOT / 'patches' / p).read_bytes()).hexdigest() for p in PATCHES]
    if actual != expected:
        raise ValueError('Lume patches differ')
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)])
    exe = str(app / 'Contents/MacOS/lume')
    if '--verification-vnc' not in run([exe, 'create', '--help']).stdout or '--vnc-password-file' not in run([exe, 'run', '--help']).stdout:
        raise ValueError('Required protected provisioning features unavailable')


def verify_guest(exe, plan):
    rows = json.loads(run([str(exe), 'ls', '--format', 'json', '--storage', plan['storage_dir']]).stdout)
    matches = [v for v in rows if v.get('name') == plan['vm_name']]
    if len(matches) != 1:
        raise ValueError('Guest not found uniquely')
    vm = matches[0]
    if (vm.get('os', '').lower() != 'macos' or vm.get('cpuCount') != plan['cpu']
            or vm.get('memorySize') != plan['memory_gb'] * 1024**3
            or vm.get('diskSize', {}).get('total') != plan['disk_gb'] * 1024**3
            or vm.get('display') != plan['display'] or vm.get('status') != 'stopped'):
        raise ValueError('Guest configuration or stopped state differs; inspect it')


def execute(args):
    payload = json.loads(args.plan_file.read_text())
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON plan object')
    if payload.get('guest_os', 'macos') != 'macos':
        raise ValueError('Only macOS guests are supported')
    supplied = payload.get('plan', payload)
    if not isinstance(supplied, dict) or supplied.get('schema_version', 1) != 1:
        raise ValueError('Unsupported plan version')
    plan = {k: supplied.get(k, DEFAULTS[k]) for k in FIELDS}
    validate_plan(plan)
    if plan['target'] == 'existing':
        raise ValueError('Use Hermes --connect for an existing installation')
    if not plan['storage_dir']:
        raise ValueError('Choose an absolute Mac storage_dir before execution')
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() == 0:
        raise ValueError('Run on Apple Silicon macOS as the dedicated non-root operator account')
    if not args.app.is_absolute() or not args.build_dir.is_absolute():
        raise ValueError('App and build paths must be absolute')
    files = ['scripts/setup-mac.py', 'scripts/provision-vm.py', 'scripts/build-native-lume.sh',
             'plugin/ownmachine/onboarding.py'] + ['patches/' + p for p in PATCHES]
    identity = digest(dict(plan=plan, app=str(args.app), build_dir=str(args.build_dir),
                          ipsw=args.ipsw, preset=args.preset,
                          source={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}))
    state_dir = Path.home() / '.local/state/ownmachine' / plan['vm_name'] / 'setup'
    path = state_dir / (args.step + '.json')
    old = read_state(path)
    if old and old.get('identity') != identity:
        raise ValueError('Plan, paths or source changed; checkpoint preserved for inspection')
    if old and old['stage'] != 'verified':
        raise ValueError('Previous step was interrupted or failed; inspect logs and resources before any retry')
    report = dict(ok=True, step=args.step, stage='planned', guest_os='macos',
                  next='Apply this step explicitly on the Mac; no runtime SSH key grants provisioning access.',
                  remaining=['firewall', 'guest hardening and driver', 'permissions', 'keys and viewer', 'desktop acceptance'])
    if not args.apply:
        report['stage'] = old['stage'] if old else 'planned'
        report['scope'] = 'Read-only plan/checkpoint inspection; no readiness claim.'
        return report
    private_dir(state_dir)
    fd = os.open(state_dir / 'execution.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Re-read under lock: a competing process may have completed while we waited.
        if read_state(path) != old:
            raise ValueError('Checkpoint changed; inspect status again')
        exe = args.app / 'Contents/MacOS/lume'
        verify = (lambda: verify_build(args.app)) if args.step == 'build' else (lambda: verify_guest(exe, plan))
        if old:
            if args.step == 'provision':
                verify_build(args.app)
            verify()
            return dict(report, stage='verified', next='Previously completed step reverified; nothing repeated.')
        if args.step == 'build':
            if args.app.exists() or args.app.is_symlink():
                raise ValueError('Existing app is not owned by this execution checkpoint; will not replace it')
            ancestor = args.build_dir
            while not ancestor.exists():
                ancestor = ancestor.parent
            if shutil.disk_usage(ancestor).free < plan['min_free_gb'] * 1024**3:
                raise ValueError('Insufficient build-volume working headroom')
            run(['/usr/bin/xcrun', '--find', 'swift'])
            private_dir(args.build_dir)
            command = ['/bin/bash', str(ROOT / 'scripts/build-native-lume.sh')]
        else:
            verify_build(args.app)
            private_dir(Path(plan['storage_dir']))
            private_dir(Path.home() / '.lume')
            command = [sys.executable, str(ROOT / 'scripts/provision-vm.py'), '--name', plan['vm_name'], '--lume', str(exe), '--storage-dir', plan['storage_dir'], '--ipsw', args.ipsw, '--preset', args.preset]
            for key in ('cpu', 'memory_gb', 'disk_gb', 'min_free_gb', 'display'):
                command += ['--' + key.replace('_', '-'), str(plan[key])]
            run(command + ['--preflight'])
        state = dict(schema_version=1, identity=identity, stage='running')
        write_state(path, state)
        try:
            logfd = os.open(state_dir / (args.step + '.log'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(logfd, 'w') as log:
                subprocess.run(command, check=True, timeout=7200, stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, LUME_TELEMETRY_ENABLED='false',
                                        OWNMACHINE_NATIVE_APP=str(args.app), OWNMACHINE_NATIVE_BUILD_ROOT=str(args.build_dir)))
            verify()
        except BaseException:
            write_state(path, dict(state, stage='needs_inspection'))
            raise
        write_state(path, dict(state, stage='verified'))
        return dict(report, stage='verified', next='Continue with the next reviewed setup step; desktop is not ready yet.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-file', required=True, type=Path)
    parser.add_argument('--step', choices=['build', 'provision'], required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--events', action='store_true', help='Print sanitized NDJSON liveness events during execution')
    parser.add_argument('--ipsw', default='latest', help='macOS restore image accepted by the pinned provisioner')
    parser.add_argument('--preset', choices=['tahoe', 'sequoia'], default='tahoe')
    parser.add_argument('--app', type=Path, default=Path.home() / '.local/share/ownmachine/native-lume.app')
    parser.add_argument('--build-dir', type=Path, default=Path.home() / 'Library/Caches/ownmachine/native-lume')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        from setup_support import events
        with events(args.events, args.step): result = execute(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # Do not emit subprocess output or operator paths into model-facing reports.
        print(json.dumps(dict(ok=False, stage='blocked', reason=str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                              next='Inspect the private Mac execution logs. No automatic destructive repair is attempted.')))
        return 2


if __name__ == '__main__':
    sys.exit(main())
