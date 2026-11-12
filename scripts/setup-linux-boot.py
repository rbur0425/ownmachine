#!/usr/bin/env python3
"""Guarded Linux boot transitions for the authenticated setup endpoint."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from setup_support import ROOT, mac, module, private_read

services = module('boot_services', 'scripts/setup-services.py')
STAGES = ('linux-boot-installer', 'linux-boot-system', 'linux-start-desktop')


def vm(c):
    rows = json.loads(services.call([str(services.binary(c)), 'ls', '--format', 'json', '--storage', c['storage_dir']]).stdout)
    matches = [row for row in rows if row.get('name') == c['vm_name']]
    if len(matches) != 1 or matches[0].get('os', '').lower() != 'linux':
        raise ValueError('selected_linux_guest_required')
    return matches[0]


def wait(predicate, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate(): return
        except (ValueError, OSError, subprocess.SubprocessError):
            pass
        time.sleep(2)
    raise ValueError('boot_transition_timeout_inspect_checkpoint')


def connection(c, live):
    result = dict(c)
    if live:
        if not c.get('guest_bootstrap_ssh_alias'): raise ValueError('pinned_bootstrap_alias_required')
        result['guest_ssh_alias'] = c['guest_bootstrap_ssh_alias']
    return result


def ready(c, step):
    live = step == 'linux-boot-installer'
    guard = ('test "$(id -u)" = 0 && grep -qx \'NAME="Archboot"\' /etc/os-release && '
             'test "$(findmnt -n -o SOURCE /)" = /dev/zram0') if live else (
             'test "$(id -u)" -ne 0 && test "$(findmnt -n -o SOURCE /)" != /dev/zram0')
    guard += ' && test "$(systemd-detect-virt)" = apple'
    if step == 'linux-start-desktop': guard += ' && systemctl --user is-active --quiet graphical-session.target'
    services.call(services.guest_argv(connection(c, live)) + [guard], timeout=15)
    return True


def shutdown(c, live):
    command = 'systemctl poweroff' if live else '"$HOME/.local/lib/ownmachine/vm-shutdown.sh"'
    try:
        services.call(services.guest_argv(connection(c, live)) + [command], timeout=30)
    except subprocess.CalledProcessError as error:
        if error.returncode != 255: raise
    wait(lambda: vm(c).get('status') == 'stopped', 120)


def execute(path, step, iso=None, iso_sha256=None):
    c = services.config(path)
    if c.get('guest_profile') != 'omarchy' or step not in STAGES or os.geteuid() == 0:
        raise ValueError('nonroot_omarchy_boot_required')
    mac.verify_build(Path(c['lume_app']), linux=True)
    state = services.hardening_state(c)
    receipt = json.loads(private_read(state / 'provision.json'))
    if (receipt.get('phase') != 'created' or receipt.get('guest_os') != 'linux'
        or receipt.get('vm_name') != c['vm_name'] or receipt.get('storage_dir') != str(Path(c['storage_dir']).resolve())):
        raise ValueError('fresh_linux_provision_receipt_required')
    if step == 'linux-boot-installer':
        if iso is None or not iso.is_absolute(): raise ValueError('verified_private_installer_required')
        with iso.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != iso_sha256: raise ValueError('iso_checksum_mismatch')
        # The bootstrap credentials/host pin must already be independently paired.
        connection(c, True)
        prerequisite = Path(receipt['checkpoint_dir']) / 'linux-create.json'
    else:
        prerequisite = state / 'setup' / ('linux-base.json' if step == 'linux-boot-system' else 'service-harden.json')
    if json.loads(private_read(prerequisite)).get('stage') != 'verified':
        raise ValueError('verified_previous_stage_required')
    directory = state / 'setup'; mac.private_dir(directory)
    identity = mac.digest(dict(config=c, step=step, iso=str(iso), iso_sha256=iso_sha256, source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    checkpoint = directory / (step + '.json')
    fd = os.open(directory / 'linux-boot.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old = mac.read_state(checkpoint)
        if old:
            if old.get('identity') != identity or old.get('stage') != 'verified':
                raise ValueError('uncertain_boot_requires_inspection')
            # Re-observe without rebooting or mounting the installer again.
            ready(c, step)
            return dict(ok=True, step=step, stage='verified', replayed=False)
        status = vm(c).get('status')
        if status not in ('running', 'stopped'): raise ValueError('unknown_guest_state')
        if step == 'linux-boot-installer' and status != 'stopped': raise ValueError('installer_requires_stopped_guest')
        if step == 'linux-start-desktop':
            services.verify('relay', c)
            services.verify_hardening(c)
            services.firewall(c)
        record = dict(schema_version=1, identity=identity, stage='running')
        mac.write_state(checkpoint, record)
        try:
            if status == 'running': shutdown(c, step == 'linux-boot-system')
            if step == 'linux-start-desktop':
                services.relay.CONFIG_PATH = Path(c.get('relay_config', str(Path.home()/'.config/ownmachine/host.json')))
                services.relay.lifecycle('start', c['vm_name'], str(services.binary(c)), c['guest_ssh_alias'])
            else:
                command = [str(services.binary(c)), 'run', c['vm_name'], '--storage', c['storage_dir'], '--display', 'none', '--vnc', 'disabled']
                if step == 'linux-boot-installer': command += ['--mount', str(iso)]
                logfd = os.open(directory/(step+'.log'), os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
                with os.fdopen(logfd, 'wb') as log:
                    subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                     start_new_session=True, env=dict(os.environ, LUME_TELEMETRY_ENABLED='false'))
            wait(lambda: ready(c, step))
        except BaseException:
            mac.write_state(checkpoint, dict(record, stage='needs_inspection')); raise
        mac.write_state(checkpoint, dict(record, stage='verified'))
        return dict(ok=True, step=step, stage='verified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--step', choices=STAGES, required=True)
    parser.add_argument('--iso', type=Path); parser.add_argument('--iso-sha256')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    if not args.apply:
        print(json.dumps(dict(ok=True, step=args.step, stage='planned'))); return 0
    try:
        print(json.dumps(execute(args.config, args.step, args.iso, args.iso_sha256)))
    except (ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps(dict(ok=False, step=args.step, stage='needs_attention', code='boot_requires_inspection')))
        return 2
    return 0

if __name__ == '__main__': raise SystemExit(main())
