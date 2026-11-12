"""Operator setup RPC over pinned OpenSSH; only channel-bound receipts are imported."""
import contextvars
import json
import os
from pathlib import Path
import selectors
import re
import secrets
import subprocess
import time
from .onboarding_state import digest

STEPS = ('preflight', 'build', 'provision', 'linux-base', 'linux-desktop', 'firewall', 'relay', 'keys', 'harden', 'driver', 'permissions', 'viewer', 'viewer-check', 'verify', 'retire')
READ_ONLY = {'preflight', 'firewall', 'permissions', 'viewer-check', 'verify', 'progress'}
KEY = 'setup_execution'
EVENT = contextvars.ContextVar('ownmachine_setup_event', default=None)
CANCEL = contextvars.ContextVar('ownmachine_setup_cancel', default=None)


def settings(ctx, plan):
    alias = ctx.get_config('setup_host_alias', '')
    source = ctx.get_config('setup_source_sha256', '')
    timeout = ctx.get_config('setup_timeout_seconds', 120)
    if (not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', alias)
            or alias == plan.get('host_alias') or alias == ctx.get_config('host_alias', '')
            or not isinstance(source, str) or not re.fullmatch('[a-f0-9]{64}', source)
            or type(timeout) is not int or not 5 <= timeout <= 7500):
        raise ValueError('invalid_setup_transport_settings')
    ssh_config = ctx.get_config('setup_ssh_config', '')
    if not isinstance(ssh_config,str) or (ssh_config and (not Path(ssh_config).is_absolute() or any(ord(c)<32 for c in ssh_config))):
        raise ValueError('invalid_setup_ssh_config')
    return alias, source, timeout


def summary(ctx, plan):
    record = ctx.state.get(KEY, default=None)
    if record is None: return {'stage': 'not_started'}
    if not isinstance(record, dict) or record.get('format') != 1:
        raise ValueError('invalid_setup_execution_state')
    alias, source, _ = settings(ctx, plan)
    if record.get('plan_digest') != digest(plan) or record.get('source_sha256') != source or record.get('host_alias') != alias or record.get('transport_digest') != digest({'alias':alias,'config':ctx.get_config('setup_ssh_config','')}):
        return {'stage': 'configuration_changed', 'next': 'Review setup identity before executing another step.'}
    return record


def exchange(argv, request, timeout):
    cancel = CANCEL.get()
    if cancel is not None and cancel.is_set(): raise ValueError('setup_cancelled')
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = bytearray()
    total = sequence = 0
    try:
        process.stdin.write(json.dumps(request).encode())
        process.stdin.close()
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                cancel = CANCEL.get()
                if cancel is not None and cancel.is_set(): raise ValueError("setup_cancelled")
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise ValueError('setup_timeout')
                if not selector.select(min(remaining, 1)): continue
                data = os.read(process.stdout.fileno(), 4096)
                if not data: break
                output.extend(data)
                total += len(data)
                if total > 4*1024*1024: raise ValueError('oversized_setup_stream')
                while request.get('stream') and b'\n' in output:
                    line, _, rest = output.partition(b'\n')
                    message = json.loads(line)
                    if not isinstance(message, dict) or 'event' not in message: break
                    binding = {k:request[k] for k in ('format','nonce','source_sha256','plan_digest','vm','step')}
                    if (set(message) != set(binding)|{'event','sequence','elapsed_seconds'}
                            or any(message.get(k) != v for k,v in binding.items())
                            or message['event'] != 'running' or type(message['sequence']) is not int
                            or message['sequence'] != sequence+1 or type(message['elapsed_seconds']) is not int
                            or not 0 <= message['elapsed_seconds'] <= 7500):
                        raise ValueError('invalid_setup_event')
                    sequence += 1
                    output = bytearray(rest)
                    callback = EVENT.get()
                    if callback: callback(message)
                if len(output) > 65536: raise ValueError('oversized_setup_receipt')
        if process.wait(timeout=max(.01, deadline-time.monotonic())) != 0:
            raise ValueError('setup_channel_failed')
        return json.loads(output)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        if not process.stdin.closed: process.stdin.close()


def dispatch(ctx, plan, step, apply=False, *, capture=None):
    if step not in (*STEPS, 'progress') or type(apply) is not bool:
        raise ValueError('invalid_setup_step')
    if step not in READ_ONLY and not apply:
        raise ValueError('explicit_apply_required')
    alias, source, timeout = settings(ctx, plan)
    nonce = secrets.token_hex(32)
    request = dict(format=1, nonce=nonce, source_sha256=source, plan_digest=digest(plan),
                   vm=plan['vm_name'], step=step, apply=apply)
    if step == 'retire': request['capture'] = capture
    if EVENT.get() is not None: request['stream'] = True
    binding = {k: request[k] for k in ('format','nonce','source_sha256','plan_digest','vm','step')}
    pending = dict(binding, host_alias=alias, transport_digest=digest({'alias':alias,'config':ctx.get_config('setup_ssh_config','')}), stage='awaiting_remote_result', observed_at=int(time.time()))
    # Persist uncertainty before sending anything; never replay automatically.
    previous = ctx.state.get(KEY, default=None)
    if previous is not None and (not isinstance(previous,dict) or type(previous.get('format')) is not int or previous.get('format') != 1):
        raise ValueError('invalid_setup_execution_state')
    ctx.state.set(KEY, pending)
    argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'IdentitiesOnly=yes', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
            '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
            alias, 'ownmachine-setup-v1']
    if ctx.get_config('setup_ssh_config',''):
        argv[1:1] = ['-F',ctx.get_config('setup_ssh_config','')]
    try:
        receipt = exchange(argv, request, timeout)
        if (not isinstance(receipt, dict) or set(receipt) != set(binding) | {'ok', 'outcomes'}
                or any(receipt.get(k) != v for k,v in binding.items()) or type(receipt['ok']) is not bool
                or not isinstance(receipt['outcomes'], dict)):
            raise ValueError('invalid_setup_receipt')
        allowed = set(STEPS) if step == 'progress' else {step}
        for name, outcome in receipt['outcomes'].items():
            if name not in allowed or not isinstance(outcome, dict) or set(outcome) != {'stage', 'observed_at'}:
                raise ValueError('invalid_setup_outcome')
            if outcome['stage'] not in {'verified','checks_passed','observed','needs_attention','needs_inspection','running'} or type(outcome['observed_at']) is not int or not 0 <= outcome['observed_at'] <= time.time()+60:
                raise ValueError('invalid_setup_outcome')
        if step != 'progress' and set(receipt['outcomes']) != {step}:
            raise ValueError('missing_setup_outcome')
        for name, outcome in receipt['outcomes'].items():
            expected = 'observed' if name == 'preflight' else 'checks_passed' if name in READ_ONLY else 'verified'
            if outcome['stage'] in {'observed','checks_passed','verified'} and outcome['stage'] != expected:
                raise ValueError('wrong_stage_postcondition')
        failed = any(x['stage'] in {'needs_attention','needs_inspection','running'} for x in receipt['outcomes'].values())
        if receipt['ok'] == failed:
            raise ValueError('inconsistent_setup_outcome')
        outcomes = {}
        if step != 'progress' and isinstance(previous, dict) and all(previous.get(k) == pending[k] for k in ('host_alias','source_sha256','plan_digest','transport_digest')):
            outcomes.update(previous.get('outcomes', {}))
        outcomes.update(receipt['outcomes'])
        imported = dict(pending, stage='remote_observed' if receipt['ok'] else 'needs_attention', outcomes=outcomes)
        ctx.state.set(KEY, imported)
        return dict(ok=receipt['ok'], **imported, scope='Authenticated setup progress, not completed desktop acceptance. No screenshot or browser input verified.')
    except (OSError, ValueError, subprocess.SubprocessError):
        ctx.state.set(KEY, dict(pending, stage='needs_inspection'))
        raise ValueError('setup_outcome_uncertain_use_progress_do_not_replay') from None


def prove_retired(ctx, plan):
    alias, _, _ = settings(ctx, plan)
    argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'IdentitiesOnly=yes', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
            '-o', 'IdentityAgent=none', '-o', 'PreferredAuthentications=publickey',
            '-o', 'ConnectTimeout=10', alias, 'ownmachine-setup-v1']
    if ctx.get_config('setup_ssh_config', ''): argv[1:1] = ['-F',ctx.get_config('setup_ssh_config','')]
    result = subprocess.run(argv, input=b'{}', capture_output=True, timeout=20,
                            env=dict(os.environ, LC_ALL='C', LANG='C'))
    if result.returncode != 255 or b'Permission denied (publickey' not in result.stderr:
        raise ValueError('setup_key_revocation_not_proven')
