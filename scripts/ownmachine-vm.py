#!/usr/bin/env python3
"""Trusted-operator lifecycle controls. Keeps the VM paused for agent input."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.config import Config
from ownmachine.lifecycle import operate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['start','stop','restart'])
    parser.add_argument('--host-alias',required=True)
    parser.add_argument('--guest-profile', choices=['macos','omarchy'], default='macos')
    parser.add_argument('--vm-name',default='ownmachine')
    parser.add_argument('--control-dir',required=True)
    args=parser.parse_args()
    config=Config(host_alias=args.host_alias,vm_name=args.vm_name,guest_profile=args.guest_profile,control_dir=args.control_dir)
    print(json.dumps(operate(config,args.operation)))

if __name__=='__main__':main()
