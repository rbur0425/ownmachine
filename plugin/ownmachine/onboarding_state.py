"""Profile-scoped progress via Hermes's atomic state API; never provisioning proof."""
import hashlib
import json
import time

KEY = 'onboarding'
STAGES = {'await_host_setup', 'await_verification', 'preflight_blocked'}


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load(ctx):
    record = ctx.state.get(KEY, default=None)
    if record is None:
        return None
    if (not isinstance(record, dict) or set(record) != {'schema_version', 'stage', 'plan_digest', 'created_at', 'updated_at', 'last_completed', 'blocked_checks'}
            or record.get('schema_version') != 1
            or record.get('stage') not in STAGES
            or not isinstance(record.get('plan_digest'), str)
            or len(record['plan_digest']) != 64
            or any(type(record.get(k)) is not int for k in ('created_at', 'updated_at'))
            or record['created_at'] < 0 or record['updated_at'] < record['created_at']
            or record.get('last_completed') not in ('plan_saved', 'connection_saved')
            or not isinstance(record.get('blocked_checks'), list)
            or any(k not in ('ssh_client', 'local_mac', 'storage') for k in record['blocked_checks'])):
        raise ValueError('invalid_onboarding_state')
    return record


def checkpoint(ctx, plan, checks, *, connected=False, previous=None):
    stamp = int(time.time())
    fingerprint = digest(plan)
    same = previous and previous['plan_digest'] == fingerprint
    connection_matches = all(ctx.get_config(k, '') == plan[k] for k in ('host_alias', 'vm_name', 'control_dir'))
    connection_saved = connected or bool(same and connection_matches and previous['last_completed'] == 'connection_saved')
    blocked = [c['check'] for c in checks if c['status'] == 'fail']
    record = {'schema_version': 1, 'plan_digest': fingerprint,
              'stage': 'preflight_blocked' if blocked else 'await_verification' if connection_saved else 'await_host_setup',
              'last_completed': 'connection_saved' if connection_saved else 'plan_saved',
              'blocked_checks': blocked,
              'created_at': previous['created_at'] if same else stamp,
              'updated_at': max(stamp, previous['updated_at']) if same else stamp}
    ctx.state.set(KEY, record)
    return record


def summary(ctx, plan):
    record = load(ctx)
    if record is None:
        return {'stage': 'plan_saved_without_checkpoint' if plan else 'not_started',
                'next': 'Run setup to review your choices; use --save to record a checkpoint.'}
    if not plan or record['plan_digest'] != digest(plan):
        return {'stage': 'plan_changed', 'next': 'Saved choices changed. Run setup to review and save a fresh checkpoint; old progress is not reused.'}
    if record['last_completed'] == 'connection_saved' and any(ctx.get_config(k, '') != plan[k] for k in ('host_alias', 'vm_name', 'control_dir')):
        return {'stage': 'connection_changed', 'next': 'Connection settings changed after the checkpoint. Review them with setup before reconnecting; run doctor against the current settings.'}
    messages = {
        'preflight_blocked': 'Resolve the listed preflight checks, then rerun setup --save.',
        'await_host_setup': 'Configure the dedicated setup endpoint and run setup --run preflight; use approved stages from the operator terminal.',
        'await_verification': 'Run doctor to check the configured relay. Configuration saved does not mean the desktop is ready.'}
    return {**record, 'next': messages[record['stage']]}
