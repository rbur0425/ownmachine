"""Native computer_use screenshot acceptance; never return desktop pixels to chat."""
import base64
import hashlib
import io
import time
from .onboarding_state import digest

KEY = 'setup_acceptance'


def identity(ctx, plan):
    return dict(format=1, plan_digest=digest(plan),
                source_sha256=ctx.get_config('setup_source_sha256', ''),
                transport_digest=digest(dict(alias=ctx.get_config('setup_host_alias', ''),
                                             config=ctx.get_config('setup_ssh_config', ''))))


def matches(ctx, plan, record):
    return isinstance(record, dict) and all(record.get(k) == v for k, v in identity(ctx, plan).items())


def capture(ctx, plan):
    from .onboarding import configuration
    from .provider import OwnMachineBackend
    from PIL import Image
    config = configuration(ctx).validate()
    if any(getattr(config, k) != plan[k] for k in ('host_alias', 'vm_name', 'control_dir')) or not config.control_dir:
        raise ValueError('runtime_plan_mismatch')
    backend = OwnMachineBackend(config)
    try:
        control = backend.lease.status()
        if control['controller'] == 'human' or control['pending']:
            raise ValueError('human_control_or_uncertain_input')
        backend.start()
        result = backend.capture(mode='vision', app='desktop')
        raw = base64.b64decode(result.png_b64, validate=True)
        if len(raw) > 32*1024*1024: raise ValueError('oversized_capture')
        with Image.open(io.BytesIO(raw)) as picture:
            if picture.format != 'PNG' or picture.size != (result.width, result.height):
                raise ValueError('invalid_capture')
            picture.verify()
        current = backend.lease.status()
        if current != control: raise ValueError('control_changed_during_capture')
        return dict(sha256=hashlib.sha256(raw).hexdigest(), width=result.width, height=result.height,
                    captured_at=int(time.time()))
    finally:
        backend.stop()


def finish(ctx, plan, apply=False):
    from . import setup_transport as transport
    from .onboarding import configuration
    from .workspace import status
    previous = ctx.state.get(KEY, default=None)
    if previous is not None and (not isinstance(previous, dict) or previous.get('format') != 1):
        raise ValueError('invalid_acceptance_state')
    transport.settings(ctx, plan)
    binding = identity(ctx, plan)
    if matches(ctx, plan, previous):
        if previous.get('stage') == 'complete':
            return dict(ok=True, **previous, scope='Previously accepted setup; no new remote checks were run.')
        if previous.get('stage') == 'retiring':
            raise ValueError('retirement_outcome_requires_operator_inspection')
    ctx.state.set(KEY, dict(binding, stage='verifying'))
    result = transport.dispatch(ctx, plan, 'verify')
    if not result['ok']: return result
    try:
        proof = capture(ctx, plan)
    except Exception:
        ctx.state.set(KEY, dict(binding, stage='screenshot_required'))
        raise
    ctx.state.set(KEY, dict(binding, stage='screenshot_verified', screenshot=proof))
    if not apply:
        return dict(ok=True, stage='screenshot_verified', screenshot=proof,
                    next='Run setup --run verify --apply to repeat checks and automatically retire setup access.')
    ctx.state.set(KEY, dict(binding, stage='retiring', screenshot=proof))
    retired = transport.dispatch(ctx, plan, 'retire', True, capture=proof)
    if not retired['ok']: return retired
    # An acknowledgement alone is insufficient: prove the SSH key is now refused
    # and that the separate runtime identity still reaches the running guest.
    transport.prove_retired(ctx, plan)
    runtime = status(configuration(ctx))
    if not runtime.get('host_reachable') or not runtime.get('driver_ready'):
        raise ValueError('runtime_check_after_retirement_failed')
    complete = dict(binding, stage='complete', screenshot=proof, completed_at=int(time.time()),
                    setup_key_rejected=True, runtime_verified=True)
    ctx.state.set(KEY, complete)
    from . import reminders
    try:
        with reminders.locked(ctx):
            cleanup = reminders.cancel(ctx, reminders.load(ctx))
        complete['reminder_cleanup_pending'] = cleanup.get('phase') == 'off_cleanup_pending'
    except (ValueError, OSError, RuntimeError):
        complete['reminder_cleanup_pending'] = True
    ctx.state.set(KEY, complete)
    return dict(ok=True, **complete, scope='Setup accepted; no desktop task, backup or reboot certification.')
