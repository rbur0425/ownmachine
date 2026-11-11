#!/usr/bin/env python3
"""Trusted operator only; never register this interface as a model tool."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.lease import Lease


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-dir',required=True,type=Path)
    parser.add_argument('controller',choices=['status','paused','human','agent'])
    args=parser.parse_args()
    if not args.control_dir.is_absolute(): parser.error('control directory must be absolute')
    lease=Lease(args.control_dir/'lease.db')
    print(json.dumps(lease.status() if args.controller=='status' else lease.transfer(args.controller)))

if __name__=='__main__': main()
