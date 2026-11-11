#!/usr/bin/env python3
"""Read-only OwnMachine doctor, usable before Hermes profile installation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.config import Config
from ownmachine.diagnostics import diagnose, render


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-alias', required=True)
    parser.add_argument('--vm-name', default='ownmachine')
    parser.add_argument('--control-dir', required=True)
    parser.add_argument('--connect-timeout-seconds', type=int, default=15)
    parser.add_argument('--action-timeout-seconds', type=int, default=30)
    parser.add_argument('--json', action='store_true', dest='as_json')
    args=vars(parser.parse_args()); as_json=args.pop('as_json')
    report=diagnose(Config(**args))
    print(json.dumps(report) if as_json else render(report))
    return 0 if report['ok'] else 1

if __name__=='__main__': raise SystemExit(main())
