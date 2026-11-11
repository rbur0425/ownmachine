#!/usr/bin/env python3
"""Render two restricted authorized_keys entries; never create or install keys."""
import argparse
import base64
from pathlib import Path
import shlex


def render(python, relay, agent_key, viewer_key):
    for path in (python, relay):
        if not Path(path).is_absolute() or any(ord(c)<32 or ord(c)==127 for c in str(path)):
            raise ValueError('absolute_executable_paths_required')
    keys=[]
    for key in (agent_key, viewer_key):
        fields=key.strip().split()
        if len(fields)<2 or fields[0]!='ssh-ed25519':
            raise ValueError('ed25519_public_key_required')
        raw=base64.b64decode(fields[1],validate=True)
        if len(raw)!=51 or raw[:19]!=b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20':
            raise ValueError('invalid_public_key')
        keys.append(' '.join(fields[:2]))
    if keys[0]==keys[1]:raise ValueError('separate_keys_required')
    lines=[]
    for role,key in zip(('agent','viewer'),keys):
        command=shlex.join([str(python),str(relay),'--role',role])
        command=command.replace('\\','\\\\').replace('"','\\"')
        lines.append(f'restrict,command="{command}" {key} ownmachine-{role}')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',required=True)
    parser.add_argument('--relay',required=True)
    parser.add_argument('--agent-public-key',required=True,type=Path)
    parser.add_argument('--viewer-public-key',required=True,type=Path)
    args=parser.parse_args()
    try:
        print(render(args.python,args.relay,args.agent_public_key.read_text(),args.viewer_public_key.read_text()),end='')
    except (OSError,ValueError):parser.error('Use two different valid Ed25519 public keys and absolute executable paths.')

if __name__=='__main__':main()
