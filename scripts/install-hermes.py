#!/usr/bin/env python3
"""Install OwnMachine into a NEW dedicated Hermes home; never alter an existing home."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.config import Config

ROOT=Path(__file__).resolve().parents[1]


def install(home, config):
    config.validate()
    if not config.control_dir: raise ValueError('shared_control_directory_required')
    home=Path(home).expanduser().absolute()
    if home.exists() or home.is_symlink(): raise ValueError('hermes_home_already_exists')
    for path in (home.resolve(), Path(config.control_dir).resolve()):
        if path==ROOT or ROOT in path.parents: raise ValueError('runtime_directory_inside_source')
    if not home.parent.is_dir(): raise ValueError('hermes_home_parent_missing')
    source=ROOT/'plugin'
    if any(p.is_symlink() for p in source.rglob('*')): raise ValueError('source_symlink_refused')
    license_path=ROOT/'LICENSE'
    if license_path.is_symlink() or not license_path.is_file(): raise ValueError('source_license_missing')
    revision=None
    try:
        if not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],stderr=subprocess.DEVNULL).strip():
            revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError): pass
    home.mkdir(mode=0o700)  # Atomic claim; no existing profile can be overwritten.
    try:
        target=home/'plugins/ownmachine'
        shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
        shutil.copyfile(license_path,target/'LICENSE')
        settings={'plugins':{'isolation':'in_process','entries':{'ownmachine':{
            'enabled':True,'settings':vars(config)}}},
            'computer_use':{'backend':'ownmachine','permission_mode':'standard'},
            'agent':{'disabled_toolsets':['terminal','file','code_execution']}}
        # A new profile uses the installed Hermes schema, not a guessed version.
        try:
            from hermes_cli.config_defaults import DEFAULT_CONFIG
        except ImportError:
            DEFAULT_CONFIG = {}
        version = DEFAULT_CONFIG.get('_config_version')
        if type(version) is int and version > 0:
            settings['_config_version'] = version
        # JSON is valid YAML; no YAML library is needed before Hermes is installed.
        path=home/'config.yaml'
        path.write_text(json.dumps(settings,indent=2)+'\n'); path.chmod(0o600)
        digests={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(target.rglob('*')) if p.is_file()}
        receipt={'source_revision':revision,'plugin_files_sha256':digests,
                 'installer':'ownmachine-fresh-home-v1'}
        path=home/'ownmachine-install.json'
        path.write_text(json.dumps(receipt,indent=2)+'\n'); path.chmod(0o600)
    except BaseException:
        shutil.rmtree(home)
        raise
    return home


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home',required=True)
    parser.add_argument('--host-alias',required=True)
    parser.add_argument('--vm-name',default='ownmachine')
    parser.add_argument('--guest-profile',choices=['macos','omarchy'],default='macos')
    parser.add_argument('--control-dir',required=True)
    parser.add_argument('--connect-timeout-seconds',type=int,default=15)
    parser.add_argument('--action-timeout-seconds',type=int,default=30)
    args=vars(parser.parse_args());home=args.pop('hermes_home')
    try: install(home,Config(**args))
    except (ValueError,OSError):
        print('Installation refused or failed. Use a complete source checkout including LICENSE, a new home with an existing writable parent, a valid SSH alias, and an absolute shared control directory outside source. Existing homes are never overwritten.',file=sys.stderr)
        return 1
    print('OwnMachine installed in the requested new Hermes home. Run Hermes plugin validation and computer-use doctor with HERMES_HOME set to that home. Model credentials must be configured separately.')
    return 0

if __name__=='__main__': raise SystemExit(main())
