#!/usr/bin/env python3
"""Diagnose the local operator viewer without changing VM or control state."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))
sys.path.insert(0, str(ROOT / 'viewer'))
from ownmachine.config import Config
from ownmachine.diagnostics import render
from diagnostics import diagnose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-alias', required=True)
    parser.add_argument('--vm-name', default='ownmachine')
    parser.add_argument('--control-dir', required=True)
    parser.add_argument('--connect-timeout-seconds', type=int, default=15)
    parser.add_argument('--action-timeout-seconds', type=int, default=30)
    parser.add_argument('--access-dir', required=True)
    parser.add_argument('--probe-vnc', action='store_true')
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = vars(parser.parse_args())
    as_json = args.pop('as_json'); probe = args.pop('probe_vnc')
    access_dir = args.pop('access_dir')
    report = diagnose(Config(**args), probe=probe, access_dir=access_dir)
    print(json.dumps(report) if as_json else render(report))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
