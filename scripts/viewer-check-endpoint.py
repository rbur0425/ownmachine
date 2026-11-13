#!/usr/bin/env python3
"""Read-only SSH forced command for a separately owned remote viewer.

Install under the viewer account with a dedicated check-only key. Configuration
is operator-owned; request text cannot supply paths, addresses or credentials.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from setup_support import ROOT, private_read


def execute(path, original):
    c=json.loads(private_read(path))
    required={'host_alias','vm_name','guest_profile','control_dir','access_dir'}
    if not isinstance(c,dict) or set(c)!=required:raise ValueError('invalid_viewer_check_configuration')
    sys.path.insert(0,str(ROOT/'plugin'))
    from ownmachine.config import Config
    config=Config(c['host_alias'],c['control_dir'],c['vm_name'],guest_profile=c['guest_profile']).validate()
    access=Path(c['access_dir']);control=Path(c['control_dir'])
    if not access.is_absolute() or access==control or access in control.parents or control in access.parents:
        raise ValueError('viewer_access_must_be_separate')
    commands={f'ownmachine-viewer-check status --vm {config.vm_name}':False,
              f'ownmachine-viewer-check probe --vm {config.vm_name}':True}
    if original not in commands:raise ValueError('unsupported_operation')
    argv=[sys.executable,str(ROOT/'scripts/ownmachine-viewer-doctor.py'),'--json']
    for key,value in c.items():argv+=['--'+key.replace('_','-'),value]
    if commands[original]:argv.append('--probe-vnc')
    result=subprocess.run(argv,capture_output=True,timeout=100)
    report=json.loads(result.stdout)
    return dict(ok=result.returncode==0 and report.get('ok') is True,vm_name=config.vm_name,
                guest_profile=config.guest_profile,scope='viewer_readiness_only')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args();os.umask(0o077)
    try:
        result=execute(a.config,os.environ.get('SSH_ORIGINAL_COMMAND',''))
        print(json.dumps(result));return 0 if result['ok'] else 1
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,TypeError):
        print(json.dumps({'ok':False,'code':'viewer_check_refused'}));return 2

if __name__=='__main__':raise SystemExit(main())
