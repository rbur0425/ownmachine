#!/usr/bin/env python3
"""Explicit, guest-only experimental foreground input module build and activation.

Never hot-replaces a module. A compositor/toolchain change requires rebuilding
and a new graphical session. This does not certify background input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys

PIN='ef1e84d6c880ab8aee7587c3d0057a288e764b69'


def call(argv,env=None,timeout=60):
    return subprocess.run(argv,check=True,capture_output=True,text=True,env=env,timeout=timeout).stdout


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(value,stream)


def fingerprint():
    version=call(['pkg-config','--modversion','hyprland']).strip()
    compiler=call(['g++','-dumpfullversion']).strip()
    comment=call(['readelf','--string-dump=.comment',shutil.which('Hyprland')])
    if not re.search(r'GCC:.*\b'+re.escape(compiler)+r'\b',comment):
        raise ValueError('compositor_compiler_mismatch')
    return dict(version=version,compiler=compiler,compositor_sha256=digest(Path(shutil.which('Hyprland'))))


def load(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>8192 or info.st_uid!=os.getuid() or info.st_mode & 0o077:raise ValueError('unsafe_input_record')
        return json.load(stream)


def execute(args):
    if platform.system()!='Linux' or os.geteuid()==0:raise ValueError('linux_desktop_user_required')
    if not args.enable_experimental_input:raise ValueError('explicit_experimental_input_opt_in_required')
    if not args.apply:return dict(stage='planned',step=args.step)
    import importlib.util
    spec=importlib.util.spec_from_file_location('linux_input_driver',Path(__file__).with_name('linux-guest.py'))
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    env=driver.session_environment()
    root=Path.home()/'.local/share/ownmachine/input-module';driver.private_dir(root)
    record=root/'build.json'
    current=fingerprint()
    if args.step=='build':
        if record.exists():
            old=load(record)
            if old['fingerprint']!=current or old['source']!=PIN or digest(Path(old['module']))!=old['sha256']:
                raise ValueError('existing_input_build_requires_inspection')
            return dict(stage='verified',replayed=False)
        source=root/'source';build=root/'build'
        if source.exists() or build.exists():raise ValueError('partial_input_build_requires_inspection')
        call(['git','init',str(source)])
        call(['git','-C',str(source),'remote','add','origin','https://github.com/trycua/cua.git'])
        call(['git','-C',str(source),'fetch','--depth=1','--filter=blob:none','origin',PIN],timeout=900)
        call(['git','-C',str(source),'sparse-checkout','set','libs/cua-driver/hyprland-plugin'])
        call(['git','-C',str(source),'checkout','--detach',PIN],timeout=900)
        if call(['git','-C',str(source),'rev-parse','HEAD']).strip()!=PIN:raise ValueError('input_source_mismatch')
        env=dict(env,CUA_HYPRLAND_REQUIRE_XKBCOMMON='1')
        commands=[['cmake','-S',str(source/'libs/cua-driver/hyprland-plugin'),'-B',str(build),'-G','Ninja',
                   '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=g++','-DCUA_HYPRLAND_INPUT=ON',
                   '-DCUA_HYPRLAND_TEST_INPUT=OFF','-DCUA_HYPRLAND_INPUT_TRACE=OFF','-DBUILD_TESTING=ON',
                   '-DCUA_HYPRLAND_EXPECTED_VERSION='+current['version']],
                  ['cmake','--build',str(build),'--parallel',str(args.jobs)],
                  ['ctest','--test-dir',str(build),'--output-on-failure']]
        with (root/'build.log').open('x') as log:
            for command in commands:
                result=call(command,env=env,timeout=1800);log.write(result);log.flush()
                if command[0]=='ctest' and ('100% tests passed' not in result or re.search(r'Skipped|Not Run',result)):
                    raise ValueError('complete_input_tests_required')
        module=build/'cua-hyprland-plugin.so'
        save(record,dict(source=PIN,fingerprint=current,module=str(module),sha256=digest(module)))
        return dict(stage='verified',step='build',loaded=False)
    old=load(record);module=Path(old['module'])
    if old['source']!=PIN or old['fingerprint']!=current or digest(module)!=old['sha256']:
        raise ValueError('input_module_rebuild_required')
    if driver.foreground_input_ready(env):return dict(stage='verified',replayed=False)
    loaded=json.loads(call(['hyprctl','-j','plugin','list'],env=env))
    if any('cua' in str(item).lower() for item in loaded):raise ValueError('restart_desktop_before_module_replacement')
    call(['hyprctl','plugin','load',str(module)],env=env)
    # Enable through a real configuration reload; runtime keyword alone does
    # not reconcile the module's transport. Retain all existing user settings.
    path=Path.home()/'.config/hypr/ownmachine-input.lua'
    line='hl.config({plugin = {cua = {enabled = true}}})\n'
    if path.exists():
        if path.read_text()!=line:raise ValueError('existing_input_configuration_differs')
    else:driver.write_new(path,line.encode())
    main=Path.home()/'.config/hypr/hyprland.lua'
    include='dofile(os.getenv("HOME") .. "/.config/hypr/ownmachine-input.lua")'
    if main.is_symlink():raise ValueError('symlink_hyprland_configuration')
    content=main.read_text()
    if include not in content:
        with main.open('a') as stream:stream.write('\n'+include+'\n')
    call(['hyprctl','reload'],env=env)
    if not driver.foreground_input_ready(env):raise ValueError('input_transport_not_ready')
    # Opt-in persists only through this verifier, not a blind plugin load line.
    # A package/toolchain change fails before loading native code at next login.
    unit=Path.home()/'.config/systemd/user/ownmachine-input.service'
    content='''[Unit]
Description=OwnMachine explicitly enabled experimental foreground input
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 "%h/.local/lib/ownmachine/linux-input-module.py" enable --enable-experimental-input --apply
RemainAfterExit=yes
UMask=0077

[Install]
WantedBy=graphical-session.target
'''
    if unit.exists():
        if unit.is_symlink() or unit.read_text()!=content:raise ValueError('existing_input_unit_differs')
    else:driver.write_new(unit,content.encode())
    call(['systemctl','--user','daemon-reload'])
    call(['systemctl','--user','enable','ownmachine-input.service'])
    return dict(stage='verified',step='enable',foreground_only=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('step',choices=['build','enable']);p.add_argument('--jobs',type=int,default=2)
    p.add_argument('--enable-experimental-input',action='store_true');p.add_argument('--apply',action='store_true')
    a=p.parse_args();os.umask(0o077)
    if not 1<=a.jobs<=16:p.error('--jobs must be between 1 and 16')
    print(json.dumps(execute(a)))


if __name__=='__main__':main()
