#!/usr/bin/env python3
"""Endpoint-owned exact setup-key removal, preserving all unrelated authorizations."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from setup_support import private_read, mac, ROOT


def entry(config_path, public_path):
    fields = private_read(public_path).decode().strip().split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519': raise ValueError('invalid_setup_public_key')
    raw = base64.b64decode(fields[1], validate=True)
    if len(raw) != 51 or raw[:19] != b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20':
        raise ValueError('invalid_setup_public_key')
    command = shlex.join([sys.executable, str(ROOT/'scripts/setup-endpoint.py'), '--config', str(config_path)])
    command = command.replace('\\', '\\\\').replace('"', '\\"')
    return 'restrict,command="'+command+'" ssh-ed25519 '+fields[1]+' ownmachine-setup', fields[1]


def retire(c, state):
    expected, blob = entry(Path(c['_config_path']), Path(c['setup_public_key_file']))
    path = Path.home()/'.ssh/authorized_keys'
    receipt = state/'retirement.json'
    fd = os.open(path.parent/'ownmachine-keys.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        before = private_read(path)
        lines = before.decode().splitlines(keepends=True)
        matches = [line for line in lines if blob in line.split()]
        if matches != [expected+'\n']:
            raise ValueError('setup_key_missing_or_differently_authorized')
        after = ''.join(line for line in lines if line != expected+'\n').encode()
        record = dict(format=1, stage='removing', key_sha256=hashlib.sha256(blob.encode()).hexdigest(),
                      remaining_sha256=hashlib.sha256(after).hexdigest())
        mac.write_state(receipt, record)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.retire-setup-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(after); stream.flush(); os.fsync(stream.fileno())
            if private_read(path) != before: raise ValueError('authorized_keys_changed')
            os.replace(temporary, path)
            if private_read(path) != after: raise ValueError('retirement_requires_inspection')
            directory = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        mac.write_state(receipt, dict(record, stage='retired'))
