#!/usr/bin/env python3
"""Operator-only guest creation; settings and logs stay outside plugin source."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='ownmachine')
    parser.add_argument('--cpu', type=int, default=4)
    parser.add_argument('--memory-gb', type=int, default=8)
    parser.add_argument('--disk-gb', type=int, default=64)
    parser.add_argument('--min-free-gb', type=int, default=60, help='Host free-space budget for restore, sparse guest allocation and working headroom; not the virtual disk capacity.')
    parser.add_argument('--verification-vnc-port', type=int, help='Deprecated compatibility argument; patched unattended creation has no VNC listener.')
    parser.add_argument('--preflight', action='store_true', help='Report capacity without creating files, downloading or contacting Lume.')
    parser.add_argument('--display', default='1900x1200')
    parser.add_argument('--storage-dir', type=Path, help='Absolute Lume storage path; omitted preserves Lume defaults.')
    parser.add_argument('--ipsw', default='latest')
    parser.add_argument('--preset', choices=['tahoe', 'sequoia'], default='tahoe')
    parser.add_argument('--lume', default=str(Path.home() / '.local/bin/lume'))
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', args.name):
        parser.error('Invalid VM name')
    if not (2 <= args.cpu <= 32 and 8 <= args.memory_gb <= 128 and 50 <= args.disk_gb <= 1000):
        parser.error('Resource allocation outside supported bounds')
    match = re.fullmatch(r'(\d{3,4})x(\d{3,4})', args.display)
    if not match or not all(640 <= int(v) <= 4096 for v in match.groups()):
        parser.error('Display must be WIDTHxHEIGHT with dimensions between 640 and 4096')
    if not 32 <= args.min_free_gb <= 2000:
        parser.error('Host free-space budget must be between 32 and 2000 GiB')
    storage = args.storage_dir or Path.home()
    if not storage.is_absolute():
        parser.error('Storage directory must be absolute')
    ancestor = storage
    while not ancestor.exists():
        ancestor = ancestor.parent
    storage_args = ['--storage', str(storage)] if args.storage_dir else []
    free = shutil.disk_usage(ancestor).free
    required = args.min_free_gb * 1024**3
    capacity = {'ok': free >= required, 'available_gib': round(free / 1024**3, 2),
                'required_free_gib': args.min_free_gb, 'additional_free_gib': round(max(0, required-free) / 1024**3, 2),
                'virtual_disk_gib': args.disk_gb, 'guest_memory_gib': args.memory_gb,
                'scope': 'Selected-volume capacity estimate only; restore caches may use the home volume. Sparse disks grow; restore and installation peak vary. Not a guarantee that installation fits.'}
    if args.preflight:
        print(json.dumps(capacity, sort_keys=True))
        return 0 if capacity['ok'] else 2
    if args.verification_vnc_port is not None and not 1024 <= args.verification_vnc_port <= 65535:
        parser.error('Legacy verification port must be between 1024 and 65535; it is no longer used.')
    os.umask(0o077)
    state = Path.home() / '.local/state/ownmachine' / args.name
    state.mkdir(parents=True, exist_ok=True)
    lock = (state / 'provision.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        print('Provisioning already in progress', file=sys.stderr)
        return 2
    def report(phase, **fields):
        path = state / 'provision.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(phase=phase, **fields)))
        temp.replace(path)
    env = dict(os.environ, LUME_TELEMETRY_ENABLED='false')
    try:
        raw = subprocess.run([args.lume, 'ls', '--format', 'json'] + storage_args, env=env,
                             capture_output=True, text=True, timeout=30, check=True)
        vms = json.loads(raw.stdout)
        if not isinstance(vms, list): raise ValueError('unexpected VM listing')
        if any(vm.get('name') == args.name for vm in vms):
            report('refused', code='vm_already_exists')
            return 2
        # Sparse virtual capacity is not physically preallocated. Check the
        # operator's peak-install budget, again immediately before creation.
        if shutil.disk_usage(ancestor).free < required:
            report('refused', code='insufficient_disk_headroom', required_free_gib=args.min_free_gb)
            return 2
        report('creating', cpu=args.cpu, memory_gb=args.memory_gb, disk_gb=args.disk_gb)
        with (state / 'provision.log').open('w') as log:
            result = subprocess.run([args.lume, 'create', args.name, '--ipsw', args.ipsw,
                '--unattended', args.preset, '--cpu', str(args.cpu), '--memory', f'{args.memory_gb}GB',
                '--disk-size', f'{args.disk_gb}GB', '--display', args.display,
                '--verification-vnc', 'disabled', '--network', 'nat'] + storage_args,
                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=5400)
        report('created' if result.returncode == 0 else 'failed', exit_code=result.returncode)
        return result.returncode
    except subprocess.TimeoutExpired:
        report('needs_inspection', code='provision_timeout_no_retry')
        return 1
    except (OSError, ValueError, subprocess.CalledProcessError):
        report('needs_inspection', code='provision_error_no_retry')
        return 1
    finally:
        lock.close()


if __name__ == '__main__':
    sys.exit(main())
