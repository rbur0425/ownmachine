#!/usr/bin/env python3
"""Windows/KVM stages behind the authenticated setup endpoint.

Fresh provisioning uses reviewed media and a separate administrator registration
handoff. Guest setup is restricted to fixed bootstrap/hardening/retirement commands;
no fallback to a macOS installer or generic shell is permitted.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
from setup_support import private_read, module

ENV={k:os.environ[k] for k in ('PATH','HOME','SSH_AUTH_SOCK','LANG') if k in os.environ}


def configuration(path,plan,require_runtime=True):
    c=json.loads(private_read(path))
    if not isinstance(c,dict) or (not {'vm_name','storage_dir','runtime_config','agent_alias','viewer_alias','ssh_config'}<=set(c) or set(c)-{'vm_name','storage_dir','runtime_config','agent_alias','viewer_alias','ssh_config','provision','driver_ready_timeout_seconds'}):
        raise ValueError('invalid_windows_services')
    readiness_timeout(c)
    if c['vm_name']!=plan['vm_name'] or c['storage_dir']!=plan['storage_dir']:raise ValueError('service_plan_mismatch')
    for key in ('runtime_config','ssh_config'):
        if not isinstance(c[key],str) or not Path(c[key]).is_absolute():raise ValueError('absolute_path_required')
    for key in ('agent_alias','viewer_alias'):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',c[key]):raise ValueError('invalid_runtime_alias')
    if c['agent_alias']==c['viewer_alias']:raise ValueError('separate_runtime_aliases_required')
    if not require_runtime:return c
    adapter=module('windows_setup_backend','host/kvm_backend.py')
    runtime=json.loads(adapter.protected(c['runtime_config']).read_text())
    if runtime.get('backend')!='kvm' or runtime.get('vm_name')!=plan['vm_name']:
        raise ValueError('runtime_plan_mismatch')
    if runtime.get('guest_profile','windows')!=plan['guest_profile']:raise ValueError('runtime_plan_mismatch')
    c['_profile']=plan['guest_profile']
    c['_vm_uuid']=runtime['vm_uuid']
    return c


def probe(c,role,operation='status',timeout=20):
    argv=['ssh','-F',c['ssh_config'],'-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=8',c[role+'_alias'],'ownmachine-host '+operation+' --vm '+c['vm_name']]
    result=subprocess.run(argv,env=ENV,capture_output=True,text=True,timeout=timeout)
    if operation!='status':return result.returncode!=0
    if result.returncode!=0 or len(result.stdout)>65536:raise ValueError('runtime_probe_failed')
    data=json.loads(result.stdout)
    if data.get('vm_uuid')!=c['_vm_uuid'] or data.get('vm_name')!=c['vm_name'] or data.get('backend')!='kvm' or data.get('guest_profile')!=c.get('_profile','windows'):
        raise ValueError('production_windows_relay_required')
    return data


def readiness_timeout(c):
    timeout=c.get('driver_ready_timeout_seconds',30)
    if type(timeout) is not int or not 0<=timeout<=120:raise ValueError('invalid_driver_ready_timeout')
    return timeout


def wait_driver(c,report=None):
    # Read-only polling: never launch, restart, log in or change a control gate.
    deadline=time.monotonic()+readiness_timeout(c)
    if report is None:report=probe(c,'agent')
    while report.get('driver_ready') is not True:
        if (report.get('vm_state')!='running' or report.get('guest_reachable') is not True
                or report.get('bootstrap_hardened') is not True
                or report.get('driver_state')=='health_check_failed'):
            break
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        time.sleep(min(2,remaining))
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        try:report=probe(c,'agent',timeout=min(20,remaining))
        except subprocess.TimeoutExpired:break
    return report


def attention(code):
    return dict(ok=False,stage='needs_attention',code=code)


def readiness_result(report, linux=False):
    if linux:
        if report.get('guest_reachable') is not True:return attention('omarchy_guest_unreachable')
        if report.get('driver_state')=='health_check_failed':return attention('omarchy_guest_health_check_failed')
        if report.get('bootstrap_hardened') is not True:return attention('omarchy_hardening_required')
        if report.get('graphical_session') is not True:return attention('graphical_session_required')
        if report.get('driver_state')=='foreground_input_unavailable':return attention('foreground_input_unavailable')
        return attention('omarchy_driver_required')
    code=('windows_hardening_required' if report.get('bootstrap_hardened') is not True else
          'windows_driver_start_required' if report.get('guest_reachable') is True else
          'standard_interactive_guest_login_required')
    return dict(ok=False,stage='needs_attention',code=code)


def preflight(plan):
    path=Path(plan['storage_dir'])
    if not path.is_absolute():raise ValueError('windows_storage_required')
    while not path.exists():path=path.parent
    checks={'linux_x86_64':platform.system()=='Linux' and platform.machine() in ('x86_64','amd64'),
            'kvm_available':Path('/dev/kvm').exists(),
            'tools_available':all(shutil.which(x) for x in ('virsh','qemu-system-x86_64','qemu-img','nft','ssh-keygen','setfacl')+(('guestfish',) if plan.get('guest_profile')=='omarchy-kvm' else ('swtpm','xorriso')))}
    free=shutil.disk_usage(path).free//(1024**3)
    memory=os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')//(1024**3) if platform.system()=='Linux' else 0
    ok=all(checks.values()) and free>=plan['min_free_gb'] and (os.cpu_count() or 0)>=plan['cpu'] and memory>=plan['memory_gb']
    return dict(ok=ok,stage='observed' if ok else 'needs_attention',checks=checks,free_gib=free,memory_gib=memory,cpu_count=os.cpu_count() or 0,kvm_available=checks['kvm_available'])


def execute(c,plan,step,apply=False):
    import windows_provision as w
    linux=plan.get('guest_profile')=='omarchy-kvm'
    if step=='preflight':return preflight(plan)
    if step in ('build','provision','harden') and not apply:raise ValueError('explicit_apply_required')
    if step=='build':
        w.build(c,plan);return dict(ok=True,stage='verified')
    if step=='provision':
        report=probe(c,'viewer')
        if report['vm_state']=='stopped':
            w.run(['ssh','-F',c['ssh_config'],'-T',c['viewer_alias'],'ownmachine-host start --vm '+c['vm_name']])
        try:result=w.guest(c,'status')
        except (ValueError,subprocess.SubprocessError):return attention('omarchy_bootstrap_pending' if linux else 'windows_installation_in_progress')
        if linux:return dict(ok=True,stage='verified') if result.get('bootstrap_hardened') is True else attention('omarchy_hardening_required')
        phase=result.get('bootstrap_stage')
        if phase=='awaiting_time_sync':
            result=w.guest(c,'sync-time')
            if result.get('configured') is not True:
                return dict(ok=False,stage='needs_attention',code='windows_time_sync_required')
        if result.get('configured') is True:return dict(ok=True,stage='verified')
        return dict(ok=False,stage='needs_attention',code='windows_bootstrap_failed' if phase=='failed' else 'windows_bootstrap_in_progress')
    if step=='harden':
        if linux:
            hardened=w.guest(c,'status').get('bootstrap_hardened') is True
            return dict(ok=True,stage='verified') if hardened else attention('omarchy_hardening_required')
        if w.guest(c,'status').get('configured') is not True:raise ValueError('bootstrap_must_finish_before_hardening')
        w.eject(c);result=w.guest(c,'harden')
        if result.get('hardened') is not True:raise ValueError('guest_hardening_failed')
        return dict(ok=True,stage='verified')
    if step=='driver':
        result=w.guest(c,'status')
        if linux:
            if result.get('bootstrap_hardened') is not True:return attention('omarchy_hardening_required')
            if result.get('graphical_session') is not True:return attention('graphical_session_required')
            if result.get('foreground_input_ready') is not True or result.get('driver_ready') is not True:
                try:
                    installed=w.guest(c,'driver')
                except subprocess.CalledProcessError:
                    return attention('omarchy_driver_required')
                if installed.get('ok') is not True:return attention('omarchy_driver_required')
            report=wait_driver(c);ok=report.get('foreground_input_ready') is True and report.get('driver_ready') is True
            return dict(ok=True,stage='verified') if ok else readiness_result(report,linux=True)
        if not all(result.get(k) is True for k in ('configured','hardened','secure_boot','tpm_ready','driver_signature','driver_unchanged')):raise ValueError('guest_driver_validation_failed')
        report=wait_driver(c)
        if report.get('driver_ready') is not True:return readiness_result(report)
        return dict(ok=True,stage='verified')
    if step in ('viewer','viewer-check'):
        w.viewer(c,plan,apply and step=='viewer')
        return dict(ok=True,stage='checks_passed' if step=='viewer-check' else 'verified')
    if step in ('firewall','relay','keys','permissions','verify'):
        agent=probe(c,'agent');viewer=probe(c,'viewer')
        if agent.get('vm_uuid')!=viewer.get('vm_uuid'):raise ValueError('runtime_roles_disagree')
        if not probe(c,'agent','vnc') or not probe(c,'viewer','mcp'):raise ValueError('runtime_roles_not_restricted')
        if step in ('permissions','verify'):
            agent=wait_driver(c,agent)
            if agent.get('driver_ready') is not True:return readiness_result(agent,linux)
        # Final acceptance must additionally prove viewer connectivity, before the
        # client capture and setup-key retirement can be authorized.
        if step=='verify':
            if (not linux and not w.media_ejected(c)) or agent.get('bootstrap_hardened') is not True:raise ValueError('guest_hardening_required')
            w.viewer(c,plan,False);w.console(c)
        return dict(ok=True,stage='verified' if step in ('relay','keys') else 'checks_passed',vm_uuid=agent['vm_uuid'])
    if linux:return attention('omarchy_setup_check_failed')
    return dict(ok=False,stage='blocked',code='windows_stage_not_integrated',next='See docs/windows-production-plan.md; preserve the saved plan and do not mark this stage complete manually.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--plan-file',type=Path,required=True)
    p.add_argument('--step',required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    profile=None
    try:
        payload=json.loads(private_read(a.plan_file));plan=payload.get('plan',payload)
        profile=plan.get('guest_profile')
        if profile not in {'windows','omarchy-kvm'}:raise ValueError('windows_profile_required')
        c=configuration(a.config,plan,require_runtime=a.step not in ('preflight','build'));result=execute(c,plan,a.step,a.apply)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        result=attention({'omarchy-kvm':'omarchy_setup_check_failed','windows':'windows_setup_check_failed'}.get(profile,'kvm_setup_check_failed'))
    print(json.dumps(result));return 0 if result['ok'] else 2


if __name__=='__main__':raise SystemExit(main())
