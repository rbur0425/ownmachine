#!/usr/bin/env python3
"""Dedicated temporary SSH forced-command setup endpoint. Never a runtime-key role."""
import argparse
import base64
import shlex
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from setup_support import ROOT, mac, private_read

sys.path.insert(0, str(ROOT/'plugin'))
from ownmachine.onboarding import DEFAULTS, FIELDS, validate_plan
from ownmachine.onboarding_state import digest
from ownmachine.setup_transport import STEPS, READ_ONLY


def fingerprint():
    entries = {}
    for base in ('scripts','host','plugin','viewer','patches'):
        if (ROOT/base).is_symlink(): raise ValueError('source_symlinks_refused')
        for path in sorted((ROOT/base).rglob('*')):
            if path.is_symlink(): raise ValueError('source_symlinks_refused')
            if path.is_file() and '__pycache__' not in path.parts:
                entries[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(entries)


def configuration(path):
    c = json.loads(private_read(path))
    permitted = {'plan_file','services_file','app','build_dir','ipsw','preset','allowed_steps','source_sha256','setup_public_key_file','use_existing_build','iso','iso_sha256'}
    if not isinstance(c,dict) or set(c)-permitted or c.get('source_sha256') != fingerprint():
        raise ValueError('unreviewed_source')
    if 'use_existing_build' in c and type(c['use_existing_build']) is not bool: raise ValueError('invalid_build_adoption')
    for key in ('plan_file','services_file','app','build_dir','iso'):
        if key in c and (not isinstance(c[key],str) or not Path(c[key]).is_absolute()):
            raise ValueError('absolute_operator_paths_required')
    if not isinstance(c.get('allowed_steps'),list) or not c['allowed_steps'] or any(s not in STEPS for s in c['allowed_steps']):
        raise ValueError('explicit_stage_allowlist_required')
    payload = json.loads(private_read(Path(c['plan_file'])))
    if not isinstance(payload,dict): raise ValueError('invalid_plan')
    raw = payload.get('plan',payload)
    if not isinstance(raw,dict) or raw.get('schema_version',1)!=1: raise ValueError('invalid_plan_version')
    plan = {key: raw.get(key, DEFAULTS[key]) for key in FIELDS}
    validate_plan(plan)
    expected_os={'omarchy':'linux','windows':'windows','macos':'macos'}[plan.get('guest_profile','macos')]
    if payload.get('guest_os',expected_os)!=expected_os:raise ValueError('guest_profile_mismatch')
    if 'iso_sha256' in c and (not isinstance(c['iso_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',c['iso_sha256'])):raise ValueError('invalid_iso_checksum')
    c['_config_path'] = str(path.resolve())
    return c,plan


def command(c,plan,step,apply):
    if plan.get('guest_profile')=='windows':
        return [sys.executable,str(ROOT/'scripts/setup-windows.py'),'--config',c['services_file'],'--plan-file',c['plan_file'],'--step',step]+(['--apply'] if apply else [])
    if step in {'linux-boot-installer','linux-boot-system','linux-start-desktop','linux-base','linux-desktop'}:
        if plan.get('guest_profile')!='omarchy':raise ValueError('linux_stage_requires_omarchy')
        from setup_support import module
        service=module('linux_endpoint_services','scripts/setup-services.py').config(Path(c['services_file']))
        if service['vm_name']!=plan['vm_name'] or service.get('storage_dir')!=plan['storage_dir'] or service.get('guest_profile')!='omarchy':raise ValueError('service_plan_mismatch')
        if step.startswith('linux-boot-') or step=='linux-start-desktop':
            argv=[sys.executable,str(ROOT/'scripts/setup-linux-boot.py'),'--config',c['services_file'],'--step',step,'--apply']
            if step=='linux-boot-installer':
                for key in ('iso','iso_sha256'):
                    if key not in c: raise ValueError('verified_iso_required')
                    argv+=['--'+key.replace('_','-'),str(c[key])]
            return argv
        return [sys.executable,str(ROOT/'scripts/install-linux-desktop.py'),'--config',c['services_file'],'--step',step.removeprefix('linux-'),'--apply']
    if step in {'build','provision'} and plan.get('guest_profile')=='omarchy':
        argv=[sys.executable,str(ROOT/'scripts/setup-linux.py'),'--plan-file',c['plan_file'],'--step',step,'--apply']
        for key in ('app','build_dir','iso','iso_sha256'):
            if key in c:argv+=['--'+key.replace('_','-'),str(c[key])]
        if step=='build' and c.get('use_existing_build'):argv.append('--use-existing-build')
        return argv
    if step in {'build','provision'}:
        argv = [sys.executable,str(ROOT/'scripts/setup-mac.py'),'--plan-file',c['plan_file'],'--step',step,'--apply']
        if step=='build' and c.get('use_existing_build'): argv.append('--use-existing-build')
        for key in ('app','build_dir','ipsw','preset'):
            if key in c: argv += ['--'+key.replace('_','-'),str(c[key])]
        return argv
    # Both configuration files must identify the same VM/storage. Request text
    # never supplies executable paths, SSH targets, keys or service configuration.
    from setup_support import module
    services = module('endpoint_services','scripts/setup-services.py')
    service = services.config(Path(c['services_file']))
    if service['vm_name'] != plan['vm_name'] or service.get('storage_dir') != plan['storage_dir'] or service.get('guest_profile','macos')!=plan.get('guest_profile','macos'):
        raise ValueError('service_plan_mismatch')
    argv = [sys.executable,str(ROOT/'scripts/setup-services.py'),'--config',c['services_file'],'--step',step]
    if apply: argv += ['--apply']
    return argv


from contextlib import contextmanager
import threading


@contextmanager
def heartbeat(request):
    stopped = threading.Event()
    start = time.monotonic()
    def send():
        sequence = 0
        while not stopped.wait(5):
            sequence += 1
            event = {k: request[k] for k in ('format','nonce','source_sha256','plan_digest','vm','step')}
            event.update(event='running', sequence=sequence, elapsed_seconds=int(time.monotonic()-start))
            try: print(json.dumps(event), flush=True)
            except (BrokenPipeError, OSError): return
    thread = threading.Thread(target=send, daemon=True) if request.get('stream') else None
    if thread: thread.start()
    try: yield
    finally:
        stopped.set()
        if thread: thread.join()


def execute(request,c,plan):
    expected={'format','nonce','source_sha256','plan_digest','vm','step','apply'}
    if isinstance(request, dict) and request.get('step') == 'retire': expected.add('capture')
    if isinstance(request, dict) and 'stream' in request:
        expected.add('stream')
        if request['stream'] is not True: raise ValueError('invalid_stream_request')
    if (not isinstance(request,dict) or set(request)!=expected or type(request['format']) is not int or request['format']!=1
            or not isinstance(request['nonce'],str) or not re.fullmatch('[a-f0-9]{64}',request['nonce'])
            or request['source_sha256']!=c['source_sha256'] or request['plan_digest']!=digest(plan)
            or request['vm']!=plan['vm_name'] or type(request['apply']) is not bool
            or request['step'] not in (*c['allowed_steps'],'progress')):
        raise ValueError('request_identity_mismatch')
    step=request['step']
    if step not in READ_ONLY and not request['apply']: raise ValueError('explicit_apply_required')
    state=Path.home()/'.local/state/ownmachine'/plan['vm_name']/'setup-endpoint'
    mac.private_dir(state)
    fd=os.open(state/'endpoint.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=state/'progress.json'
        saved=json.loads(private_read(path)) if path.exists() else dict(format=1,plan_digest=digest(plan),source_sha256=c['source_sha256'],nonces=[],outcomes={})
        if saved.get('format')!=1 or saved.get('plan_digest')!=digest(plan) or saved.get('source_sha256')!=c['source_sha256']:
            raise ValueError('endpoint_progress_identity_changed')
        if (state/'retirement.json').exists(): raise ValueError('setup_retirement_requires_operator_inspection')
        if request['nonce'] in saved['nonces']: raise ValueError('replayed_request')
        if len(saved['nonces']) >= 4096: raise ValueError('setup_session_limit_reached')
        saved['nonces']=saved['nonces']+[request['nonce']]
        mac.write_state(path,saved)
        if step!='progress':
            old=saved['outcomes'].get(step,{})
            if old.get('stage') in {'running','needs_inspection'} and step not in READ_ONLY:
                raise ValueError('uncertain_previous_step')
            if step in {'build','provision'}:
                preflight = saved['outcomes'].get('preflight', {})
                if preflight.get('stage') != 'observed' or time.time()-preflight.get('observed_at',0) > 300:
                    raise ValueError('fresh_remote_preflight_required')
            if step == 'retire':
                verified = saved['outcomes'].get('verify', {})
                proof = request.get('capture')
                if (verified.get('stage') != 'checks_passed' or not 0 <= time.time()-verified.get('observed_at',0) <= 300
                        or not isinstance(proof,dict) or set(proof) != {'sha256','width','height','captured_at'}
                        or not isinstance(proof.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',proof['sha256'])
                        or any(type(proof.get(k)) is not int or not 1 <= proof[k] <= 8192 for k in ('width','height'))
                        or type(proof.get('captured_at')) is not int or not 0 <= time.time()-proof['captured_at'] <= 300):
                    raise ValueError('fresh_verification_and_capture_required')
                from setup_support import module
                retirement = module('endpoint_retirement','scripts/retire-setup-key.py')
                if plan.get('guest_profile')=='windows':
                    windows=module('retiring_windows','scripts/setup-windows.py')
                    import windows_provision
                    service=windows.configuration(Path(c['services_file']),plan)
                    windows_provision.retire(service,state)
                retirement.retire(c,state)
                saved['outcomes'][step]=dict(stage='verified',observed_at=int(time.time()))
                mac.write_state(path,saved)
                return {**{k:v for k,v in request.items() if k not in {'apply','stream','capture'}},'ok':True,'outcomes':{step:saved['outcomes'][step]}}
            argv=command(c,plan,step,request['apply'])
            saved['outcomes'][step]=dict(stage='running',observed_at=int(time.time()))
            mac.write_state(path,saved)
            stage='needs_inspection'
            try:
                # Child writes only a bounded final result on stdout, never logs.
                with heartbeat(request):
                    result=subprocess.run(argv,capture_output=True,text=True,timeout=7300)
                if len(result.stdout)<=65536:
                    report=json.loads(result.stdout)
                    if isinstance(report,dict) and result.returncode==0 and report.get('ok') is True and report.get('stage') in {'verified','checks_passed','observed'}:
                        stage=report['stage']
                        if step=='preflight' and (report.get('free_gib',0)<plan['min_free_gb'] or not report.get('kvm_available' if plan.get('guest_profile')=='windows' else 'swift_available')
                                or report.get('cpu_count',0)<plan['cpu'] or report.get('memory_gib',0)<plan['memory_gb']):
                            stage='needs_attention'
                    elif isinstance(report,dict) and result.returncode==2 and report.get('stage') in {'needs_attention','blocked'}:
                        stage='needs_attention'
            except (OSError,ValueError,subprocess.SubprocessError):
                pass
            saved['outcomes'][step]=dict(stage=stage,observed_at=int(time.time()))
            mac.write_state(path,saved)
        outcomes=saved['outcomes'] if step=='progress' else {step:saved['outcomes'][step]}
        ok=not any(v['stage'] in {'running','needs_attention','needs_inspection'} for v in outcomes.values())
        return {**{k:v for k,v in request.items() if k not in {'apply','stream'}},'ok':ok,'outcomes':outcomes}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--fingerprint',action='store_true')
    parser.add_argument('--render-key',type=Path,help='Render a forced-command entry for a dedicated setup public key; never install it')
    args=parser.parse_args()
    # A dropped setup client must not terminate a disk mutation. The endpoint
    # retains its lock and records completion; reconnect imports progress.
    import signal
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.umask(0o077)
    if args.fingerprint:
        print(fingerprint());return 0
    if args.render_key:
        if not args.config or not args.config.is_absolute(): parser.error('absolute config path required')
        fields=args.render_key.read_text().strip().split()
        if len(fields)<2 or fields[0]!='ssh-ed25519': parser.error('Ed25519 public key required')
        raw=base64.b64decode(fields[1],validate=True)
        if len(raw)!=51 or raw[:19]!=b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20': parser.error('invalid public key')
        argv=[sys.executable,str(Path(__file__).resolve()),'--config',str(args.config)]
        if any(any(ord(c)<32 or ord(c)==127 for c in value) for value in argv): parser.error('invalid path')
        forced=shlex.join(argv).replace('\\','\\\\').replace(chr(34),'\\'+chr(34))
        print('restrict,command="'+forced+'" ssh-ed25519 '+fields[1]+' ownmachine-setup')
        return 0
    try:
        if os.geteuid()==0 or os.environ.get('SSH_ORIGINAL_COMMAND')!='ownmachine-setup-v1' or not args.config:
            raise ValueError('dedicated_forced_command_required')
        raw=sys.stdin.buffer.read(16385)
        if len(raw)>16384:raise ValueError('oversized_request')
        c,plan=configuration(args.config)
        print(json.dumps(execute(json.loads(raw),c,plan)),flush=True)
        return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        print(json.dumps({'code':'setup_request_refused'}));return 2


if __name__=='__main__':raise SystemExit(main())
