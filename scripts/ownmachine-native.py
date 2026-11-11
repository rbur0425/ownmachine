#!/usr/bin/env python3
"""Build, check or start the optional key-aware native viewer."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', default='ownmachine')
    p.add_argument('--guest-user', default='lume')
    p.add_argument('--storage')
    p.add_argument('--clipboard-sync', action='store_true', help='Opt into continuous bidirectional clipboard sync; default is toolbar transfers only')
    p.add_argument('--state-root', type=Path, default=Path.home()/'.local/state/ownmachine')
    p.add_argument('--lume', type=Path, default=Path(os.environ.get('OWNMACHINE_NATIVE_APP', str(Path.home()/'.local/share/ownmachine/native-lume.app')))/'Contents/MacOS/lume')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--build', action='store_true', help='Build the optional app, then exit without starting a VM')
    mode.add_argument('--check', action='store_true', help='Check viewer, VM and strict key authentication without input or clipboard access')
    a = p.parse_args(argv)
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', x) for x in (a.name, a.guest_user)):
        p.error('Invalid guest identifier')
    a.lume = a.lume.expanduser().absolute()
    helper = ROOT/'native-clipboard-helper.py'
    env = os.environ.copy()
    env.update(LUME_CLIPBOARD_HELPER=str(helper), OWNMACHINE_LUME_BIN=str(a.lume),
               OWNMACHINE_STATE_ROOT=str(a.state_root.expanduser().resolve()), OWNMACHINE_GUEST_USER=a.guest_user,
               LUME_TELEMETRY_ENABLED='false', LUME_CLIPBOARD_AUTOSYNC='1' if a.clipboard_sync else '0')
    if a.build:
        if a.lume.parts[-3:] != ('Contents', 'MacOS', 'lume'):
            p.error('--build requires an app path ending in Contents/MacOS/lume')
        env['OWNMACHINE_NATIVE_APP'] = str(a.lume.parents[2])
        return subprocess.call(['/bin/bash', str(ROOT/'build-native-lume.sh')], env=env)
    if not a.lume.is_file() or not os.access(helper, os.X_OK):
        print('Native viewer is not installed. Run scripts/ownmachine-native.py --build first, or select the installed app with --lume.', file=sys.stderr)
        return 1
    try:
        command = [str(a.lume), 'get', a.name, '--format', 'json']
        if a.storage: command += ['--storage', a.storage]
        data = json.loads(subprocess.check_output(command, env=env, stderr=subprocess.DEVNULL, timeout=15))
        rows = data if isinstance(data, list) else [data]
        matches = [row for row in rows if isinstance(row, dict) and row.get('name') == a.name]
        if len(matches) != 1: raise ValueError('Selected VM is missing or ambiguous; provision it first.')
        status = matches[0].get('status')
        if a.check:
            if status != 'running': raise ValueError('Start the guest and complete graphical login before checking guest SSH.')
            spec = importlib.util.spec_from_file_location('ownmachine_native_clipboard', helper)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            ssh = module.ssh_args(a.name, a.storage or '', env)
            result = subprocess.run(ssh+['true'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=10)
            if result.returncode: raise ValueError('Guest key authentication failed. Check the selected account, key and verified known hosts.')
            print('Native viewer check passed: selected guest is running and strict key SSH works. Test toolbar copy/paste in a disposable field; this check sends no clipboard or input.')
            return 0
        if status != 'stopped':
            raise ValueError('Guest is already running or busy. Shut it down normally before switching its owning viewer; attach alone cannot change clipboard configuration.')
        state = a.state_root.expanduser()/a.name
        key = state/'guest_ed25519'
        if not key.is_file() or key.stat().st_mode & 0o077 or not (state/'guest_known_hosts').is_file():
            raise ValueError('Guest key/known-hosts missing or key permissions too broad. Complete secure-guest.py first.')
        command = [str(a.lume), 'run', a.name, '--detach', '--display', 'native', '--vnc', 'disabled']
        if a.storage: command += ['--storage', a.storage]
        print('Native clipboard uses the selected guest key. '+('Continuous clipboard sync enabled.' if a.clipboard_sync else 'Use the Copy/Paste toolbar buttons; continuous sync is off.'))
        return subprocess.call(command, env=env)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        message = str(error) if type(error) is ValueError else 'Unable to query the selected viewer or guest. Check installation and VM state.'
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
