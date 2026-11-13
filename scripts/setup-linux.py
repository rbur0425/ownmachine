#!/usr/bin/env python3
"""Authenticated-endpoint build/create stages for the experimental Linux profile."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from setup_support import ROOT, mac, module, private_read
sys.path.insert(0,str(ROOT/'plugin'))
from ownmachine.onboarding import DEFAULTS,FIELDS,validate_plan


def execute(a):
    payload=json.loads(private_read(a.plan_file));raw=payload.get('plan',payload)
    plan={k:raw.get(k,DEFAULTS[k]) for k in FIELDS};validate_plan(plan)
    if plan['guest_profile']!='omarchy':raise ValueError('omarchy_profile_required')
    if not a.apply:return dict(ok=True,step=a.step,stage='planned')
    if a.step=='build':
        if a.use_existing_build:
            mac.verify_build(a.app,linux=True)
        else:
            directory=Path.home()/'.local/state/ownmachine'/plan['vm_name']/'setup';mac.private_dir(directory)
            fd=os.open(directory/'linux-build.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as log:
                subprocess.run(['/bin/bash',str(ROOT/'scripts/build-native-lume.sh')],stdout=log,stderr=subprocess.STDOUT,timeout=7200,check=True,
                    env=dict(os.environ,OWNMACHINE_LINUX_GUESTS='1',OWNMACHINE_NATIVE_APP=str(a.app),OWNMACHINE_NATIVE_BUILD_ROOT=str(a.build_dir)))
            mac.verify_build(a.app,linux=True)
    else:
        if a.iso is None or a.iso_sha256 is None:raise ValueError('verified_iso_required')
        runner=module('linux_create_runner','scripts/provision-linux-vm.py')
        args=SimpleNamespace(profile='omarchy',step='create',vm_name=plan['vm_name'],app=a.app,
             storage_dir=Path(plan['storage_dir']),state_dir=Path.home()/'.local/state/ownmachine'/plan['vm_name']/'linux-create',
             iso=a.iso,iso_sha256=a.iso_sha256,cpu=plan['cpu'],memory_gb=plan['memory_gb'],disk_gb=plan['disk_gb'],
             min_free_gb=plan['min_free_gb'],display=plan['display'],apply=True)
        runner.execute(args)
    return dict(ok=True,step=a.step,stage='verified')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan-file',type=Path,required=True);p.add_argument('--step',choices=['build','provision'],required=True)
    p.add_argument('--app',type=Path,required=True);p.add_argument('--build-dir',type=Path,required=True)
    p.add_argument('--iso',type=Path);p.add_argument('--iso-sha256');p.add_argument('--use-existing-build',action='store_true');p.add_argument('--apply',action='store_true')
    a=p.parse_args();os.umask(0o077)
    try:print(json.dumps(execute(a)))
    except (ValueError,OSError,subprocess.SubprocessError):
        print(json.dumps(dict(ok=False,step=a.step,stage='needs_attention',code='linux_setup_requires_inspection')));raise SystemExit(2)

if __name__=='__main__':main()
