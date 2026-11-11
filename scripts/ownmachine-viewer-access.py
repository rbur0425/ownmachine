#!/usr/bin/env python3
"""Retrieve current private viewer access on the viewer machine, as its owner."""
import argparse
import http.client
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'viewer'))
from diagnostics import AccessError, read_access, read_state


def bounded_integer(lower, upper):
    def parse(value):
        number = int(value)
        if not lower <= number <= upper:
            raise argparse.ArgumentTypeError(f'Use an integer from {lower} to {upper}.')
        return number
    return parse


def ssh_target(value):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*', value):
        raise argparse.ArgumentTypeError('Use an SSH config alias or user@hostname, without options.')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--access-dir', required=True, type=Path)
    reveal = parser.add_mutually_exclusive_group()
    reveal.add_argument('--show-url', action='store_true', help='Print the bearer link to this private terminal.')
    reveal.add_argument('--show-token', action='store_true', help='Print only the token for the viewer unlock form.')
    parser.add_argument('--local-port', type=bounded_integer(1, 65535), help='Local SSH tunnel port; does not change the viewer listener.')
    parser.add_argument('--ssh-target', type=ssh_target, help='Print a loopback tunnel command to run on your computer; never executes SSH.')
    parser.add_argument('--timeout-seconds', type=bounded_integer(1, 120), default=10)
    args = parser.parse_args(argv)
    if args.ssh_target and (args.show_url or args.show_token):
        parser.error('Request the tunnel command separately from secret output.')
    try:
        port, token = read_access(args.access_dir.expanduser())
        read_state(port, token, args.timeout_seconds)
    except FileNotFoundError:
        print('Viewer access unavailable: start the viewer with this private access directory.', file=sys.stderr)
        return 1
    except AccessError:
        print('Viewer access refused: check the private file and run viewer doctor; restart may have rotated the token.', file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, AttributeError, http.client.HTTPException):
        print('Viewer access unavailable: run on the viewer machine as its owner; check the file and running listener with viewer doctor.', file=sys.stderr)
        return 1
    local_port = args.local_port or port
    if args.show_url:
        print(f'http://127.0.0.1:{local_port}/#{token}')
    elif args.show_token:
        print(token)
    elif args.ssh_target:
        command = ['ssh', '-N', '-o', 'ExitOnForwardFailure=yes', '-L',
                   f'127.0.0.1:{local_port}:127.0.0.1:{port}', args.ssh_target]
        print(shlex.join(command))
    else:
        print(f'Viewer authenticated on loopback port {port}.')
        print('Use --show-url or --show-token in a private terminal to retrieve access.')
        print('For remote access, use --ssh-target with your configured SSH alias.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
