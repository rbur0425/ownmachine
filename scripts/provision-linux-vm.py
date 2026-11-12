#!/usr/bin/env python3
"""Create an isolated Omarchy installer VM; resume never overwrites a guest disk.

The boot stage opens the signed, operator-verified ARM64 ISO in the native
console. Base/desktop installation remains an explicit guest-side handoff.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('linux_setup_support',ROOT/'scripts/setup-mac.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)


def validate(args):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',args.vm_name):raise ValueError('invalid_vm_name')
    if args.profile!='omarchy':raise ValueError('unsupported_linux_profile')
    for path in (args.app,args.storage_dir,args.state_dir,args.iso):
        if not path.is_absolute() or any(ord(c)<32 for c in str(path)):raise ValueError('absolute_paths_required')
    if not re.fullmatch('[a-f0-9]{64}',args.iso_sha256):raise ValueError('verified_iso_sha256_required')
    if not 2<=args.cpu<=32 or not 8<=args.memory_gb<=128 or not 32<=args.disk_gb<=1000 or not 16<=args.min_free_gb<=2000:
        raise ValueError('invalid_resource_limits')
    match=re.fullmatch(r'(\d{3,4})x(\d{3,4})',args.display)
    if not match or not all(640<=int(v)<=4096 for v in match.groups()):raise ValueError('invalid_display')


def listing(args):
    rows=support.run([str(args.app/'Contents/MacOS/lume'),'ls','--format','json','--storage',str(args.storage_dir)]).stdout
    rows=json.loads(rows)
    if not isinstance(rows,list):raise ValueError('invalid_vm_listing')
    matches=[r for r in rows if r.get('name')==args.vm_name]
    if len(matches)>1:raise ValueError('ambiguous_vm')
    return matches[0] if matches else None


def matches(vm,args):
    return (vm and vm.get('os','').lower()=='linux' and vm.get('cpuCount')==args.cpu
        and vm.get('memorySize')==args.memory_gb*1024**3 and vm.get('display')==args.display
        and vm.get('diskSize',{}).get('total')==args.disk_gb*1024**3)


def execute(args):
    validate(args)
    if not args.apply:return {'stage':'planned','guest_os':'linux','guest_profile':args.profile,'vnc':'disabled','step':args.step}
    if platform.system()!='Darwin' or platform.machine()!='arm64' or os.geteuid()==0:
        raise ValueError('apple_silicon_nonroot_required')
    support.verify_build(args.app,linux=True)
    with args.iso.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=args.iso_sha256:raise ValueError('iso_checksum_mismatch')
    support.private_dir(args.state_dir);support.private_dir(args.storage_dir)
    identity=support.digest({k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k not in {'step','apply'}})
    lock=os.open(args.state_dir/'provision.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(lock,'w'):
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        checkpoint=args.state_dir/'linux-create.json'
        old=support.read_state(checkpoint)
        if old and old.get('identity')!=identity:raise ValueError('configuration_changed_inspect_checkpoint')
        vm=listing(args)
        if args.step=='create':
            if old:
                if old.get('stage')=='verified' and matches(vm,args):return old
                raise ValueError('interrupted_creation_requires_inspection')
            if vm or (args.storage_dir/args.vm_name).exists():raise ValueError('existing_vm_preserved')
            if shutil.disk_usage(args.storage_dir).free<args.min_free_gb*1024**3:raise ValueError('insufficient_free_storage')
            state=dict(schema_version=1,identity=identity,stage='running',guest_os='linux',guest_profile=args.profile)
            support.write_state(checkpoint,state)
            argv=[str(args.app/'Contents/MacOS/lume'),'create',args.vm_name,'--os','linux','--cpu',str(args.cpu),
                '--memory',str(args.memory_gb)+'GB','--disk-size',str(args.disk_gb)+'GB','--display',args.display,
                '--storage',str(args.storage_dir),'--network','nat','--verification-vnc','disabled']
            try:
                support.run(argv)
                vm=listing(args)
                if not matches(vm,args) or vm.get('status')!='stopped':raise ValueError('created_vm_mismatch')
            except Exception:
                state['stage']='needs_inspection';support.write_state(checkpoint,state);raise
            state['stage']='verified';support.write_state(checkpoint,state);return state
        if not old or old.get('stage')!='verified' or not matches(vm,args):raise ValueError('verified_create_required')
        if vm.get('status')!='stopped':raise ValueError('guest_must_be_stopped')
        # Never detach the installer, mount host directories, or open weak VNC.
        argv=[str(args.app/'Contents/MacOS/lume'),'run',args.vm_name,'--storage',str(args.storage_dir),
              '--display','native','--vnc','disabled','--mount',str(args.iso)]
        return_code=subprocess.call(argv,env=dict(os.environ,LUME_TELEMETRY_ENABLED='false'))
        if return_code:raise ValueError('native_installer_failed')
        return {'stage':'guest_install_handoff','guest_os':'linux','vnc':'disabled'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['omarchy'],default='omarchy')
    parser.add_argument('--step',choices=['create','boot'],required=True)
    parser.add_argument('--vm-name',default='ownmachine-omarchy')
    for key in ('app','storage-dir','state-dir','iso'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--iso-sha256',required=True,help='SHA-256 from the independently verified signed Archboot manifest')
    for key,value in [('cpu',4),('memory-gb',8),('disk-gb',64),('min-free-gb',32)]:parser.add_argument('--'+key,type=int,default=value)
    parser.add_argument('--display',default='1900x1200')
    parser.add_argument('--apply',action='store_true')
    try:print(json.dumps(execute(parser.parse_args()),sort_keys=True))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('Linux provision requires inspection: '+str(error),file=sys.stderr);raise SystemExit(2)

if __name__=='__main__':main()
