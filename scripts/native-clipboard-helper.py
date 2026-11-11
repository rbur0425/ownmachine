#!/usr/bin/env python3
"""Lume clipboard transport for an explicitly selected, key-hardened guest.

Invoked only by the native viewer. Never reads a password, weakens host-key
checking, or logs clipboard contents. This is not a network service.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def ssh_args(vm, storage='', env=None):
    env = os.environ if env is None else env
    user = env.get('OWNMACHINE_GUEST_USER', 'lume')
    for value in (vm, user):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
            raise ValueError('Invalid guest identifier')
    root = Path(env.get('OWNMACHINE_STATE_ROOT', str(Path.home()/'.local/state/ownmachine'))).expanduser()
    state = root / vm
    key, known = state/'guest_ed25519', state/'guest_known_hosts'
    if not key.is_file() or not known.is_file() or key.stat().st_mode & 0o077:
        raise ValueError('Guest key/known-hosts missing or key permissions too broad')
    lume = env.get('OWNMACHINE_LUME_BIN', str(Path.home()/'.local/bin/lume'))
    args = [lume, 'get', vm, '--format', 'json']
    if storage: args += ['--storage', storage]
    details = json.loads(subprocess.check_output(args, timeout=15, stderr=subprocess.DEVNULL))
    if isinstance(details,list):
        matches=[d for d in details if d.get('name')==vm]
        if len(matches)!=1: raise ValueError('Ambiguous guest')
        details=matches[0]
    ip = str(ipaddress.ip_address(details['ipAddress']))
    if details.get('status') != 'running':
        raise ValueError('Guest is not running')
    return ['/usr/bin/ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=5',
            '-o','ForwardAgent=no','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
            '-o',f'UserKnownHostsFile={known}','-o',f'HostKeyAlias=ownmachine-guest-{vm}',
            '-i',str(key),f'{user}@{ip}']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vm',required=True)
    parser.add_argument('--storage',default='')
    parser.add_argument('--command',required=True)
    args=parser.parse_args()
    try:
        # The trusted viewer constructs the clipboard command. Pass it as one
        # remote argument; never interpolate it into a local shell.
        result=subprocess.run(ssh_args(args.vm,args.storage)+[args.command],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=35)
        sys.stdout.buffer.write(result.stdout)
        return result.returncode
    except (ValueError,KeyError,OSError,subprocess.SubprocessError):
        print('Native clipboard unavailable; check guest key, known hosts and running state.',file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
