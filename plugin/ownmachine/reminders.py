"""Explicit, profile-bound onboarding nudges through public Hermes APIs only."""
import contextlib
import datetime as dt
from zoneinfo import ZoneInfo
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import time
from .onboarding_state import digest

KEY = 'setup_reminders'
MESSAGE = 'OwnMachine setup is waiting. Run /ownmachine status to review progress, or /ownmachine setup to continue. Nothing has been provisioned by this reminder.'


def clock(): return int(time.time())


@contextlib.contextmanager
def locked(ctx):
    directory = Path(ctx.state.data_dir)
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('unsafe_reminder_state_directory')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(directory/'reminders.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def load(ctx):
    record = ctx.state.get(KEY, default=None)
    if record is None:
        return dict(format=1, enabled=False, count=0, last_nudge_at=0, rank=-1, phase='off')
    if (not isinstance(record,dict) or record.get('format') != 1 or type(record.get('enabled')) is not bool
            or type(record.get('count')) is not int or not 0 <= record['count'] <= 3
            or type(record.get('last_nudge_at')) is not int or type(record.get('rank')) is not int):
        raise ValueError('invalid_reminder_state')
    return record


def identity(ctx):
    plan = ctx.get_config('setup_plan', {})
    return digest(dict(plan=plan, source=ctx.get_config('setup_source_sha256',''),
                       alias=ctx.get_config('setup_host_alias',''), ssh=ctx.get_config('setup_ssh_config','')))


def canonical_plan(ctx):
    from .onboarding import DEFAULTS, FIELDS
    saved=ctx.get_config('setup_plan',{})
    return {k:saved.get(k,DEFAULTS[k]) for k in FIELDS} if isinstance(saved,dict) and saved else {}


def completed(ctx):
    record = ctx.state.get('setup_acceptance', default={})
    from .setup_acceptance import matches
    return matches(ctx, canonical_plan(ctx), record) and record.get('stage') == 'complete'


def rank(ctx):
    from .setup_transport import STEPS
    record = ctx.state.get('setup_execution', default={})
    if (not isinstance(record,dict)
            or record.get('plan_digest') != digest(canonical_plan(ctx))
            or record.get('source_sha256') != ctx.get_config('setup_source_sha256', '')
            or record.get('transport_digest') != digest(dict(alias=ctx.get_config('setup_host_alias', ''), config=ctx.get_config('setup_ssh_config', '')))):
        return -1
    outcomes = record.get('outcomes',{})
    return max((i for i,s in enumerate(STEPS) if isinstance(outcomes.get(s),dict)
                and outcomes[s].get('stage') == 'verified'), default=-1)


def target(ctx, source=None):
    if source is None:
        configured = ctx.get_config('setup_reminder_destination', {})
        if not configured: return {'kind':'terminal'}
        candidate = dict(configured)
    else:
        from .onboarding import authorized_sender
        if not authorized_sender(ctx,source): raise ValueError('reminder_sender_not_authorized')
        origin = source['source']
        candidate = dict(platform=source['platform'], user_id=origin.user_id, chat_id=origin.chat_id)
        thread = getattr(origin,'thread_id',None)
        if thread is not None: candidate['thread_id'] = str(thread)
    if set(candidate)-{'platform','user_id','chat_id','thread_id'} or not all(candidate.get(k) for k in ('platform','user_id','chat_id')):
        raise ValueError('invalid_reminder_destination')
    if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_@.!#/-]{1,256}',v) for v in candidate.values()):
        raise ValueError('unsupported_reminder_destination')
    return candidate


def destination_allowed(ctx, record):
    saved = record.get('destination',{})
    if record.get('authority') == 'terminal':
        if record.get('mode') == 'next-visit': return saved == {'kind':'terminal'}
        try:return target(ctx) == saved
        except (ValueError,TypeError):return False
    grants = ctx.get_config('setup_allowed_senders',[])
    return isinstance(grants,list) and any(isinstance(g,dict) and all(g.get(k)==saved.get(k) for k in ('platform','user_id','chat_id')) for g in grants)


def refresh(ctx, record):
    if record.get('identity') != identity(ctx) or completed(ctx) or (record.get('enabled') and not destination_allowed(ctx,record)):
        record.update(enabled=False, phase='disabled_requires_review')
    current = rank(ctx)
    if current > record['rank']:
        record.update(rank=current, count=0)
    return record


def cancel(ctx, record):
    record.update(enabled=False, phase='off')
    record.pop('reservation', None)
    record.pop('proposal', None)
    ctx.state.set(KEY, record)
    if record.get('intent'):
        from .scheduled_reminders import cancel as cancel_job
        try: record=cancel_job(ctx,record)
        except (ValueError,OSError,RuntimeError): record['phase']='off_cleanup_pending'
        ctx.state.set(KEY,record)
    return record


def limit(ctx):
    value=ctx.get_config('setup_reminder_limit',3)
    if type(value) is not int or not 1 <= value <= 3:raise ValueError('invalid_reminder_limit')
    return value


def execute(ctx,args,source=None):
    now=clock()
    with locked(ctx):
        record=refresh(ctx,load(ctx))
        action=args.remind_action
        if action=='emit':
            from .scheduled_reminders import emit
            return emit(ctx,record,getattr(args,'token',None),now)
        if action=='off': return json.dumps(cancel(ctx,record))
        if record.get('intent'):
            from .scheduled_reminders import reconcile
            try:
                record=reconcile(ctx,record)
                record['scheduler_available']=True
            except (ValueError,OSError,RuntimeError):
                record['scheduler_available']=False
                if action!='status':raise
        if action=='status':
            ctx.state.set(KEY,record);return json.dumps(record)
        if action!='later':raise ValueError('invalid_reminder_action')
        if not ctx.get_config('setup_plan',{}) or completed(ctx):raise ValueError('no_pending_setup')
        mode=args.mode
        dest=({'kind':'terminal'} if source is None and mode=='next-visit' else target(ctx,source))
        if mode=='tomorrow' and dest.get('kind')=='terminal':
            return 'Scheduled delivery needs an explicit setup_reminder_destination. No job was created; next-visit is available.'
        if mode=='tomorrow':
            from .reminder_scheduler import jobs
            jobs(ctx)  # Refuse before preview/consent when no matching gateway is ready.
        proposal=record.get('proposal')
        confirm=getattr(args,'confirm',None)
        if not confirm:
            proposal=dict(token=secrets.token_hex(16),mode=mode,destination=dest,created_at=now,
                          due=now+86400,identity=identity(ctx),authority='terminal' if source is None else 'chat')
            record['proposal']=proposal;ctx.state.set(KEY,record)
            when=(dt.datetime.fromtimestamp(proposal['due'],ZoneInfo(ctx.get_config('setup_reminder_timezone','UTC'))).isoformat() if mode=='tomorrow' else 'your next eligible Hermes visit (or OwnMachine command)')
            return 'Preview only: '+when+'; destination '+json.dumps(dest)+'. Confirm with remind later --mode '+mode+' --confirm '+proposal['token']+'. No reminder was enabled by this preview.'
        if (not isinstance(proposal,dict) or proposal.get('token')!=confirm or proposal.get('mode')!=mode
                or proposal.get('destination')!=dest or proposal.get('identity')!=identity(ctx)
                or not 0<=now-proposal.get('created_at',0)<=900):raise ValueError('reminder_confirmation_expired_or_changed')
        record=cancel(ctx,record)
        if record.get('phase')=='off_cleanup_pending':raise ValueError('reminder_cleanup_required')
        if record['count']>=limit(ctx):record['count']=0  # explicit fresh consent after exhaustion
        record.update(enabled=True,mode=mode,destination=dest,authority=proposal['authority'],identity=identity(ctx),
                      consented_at=now,due=proposal['due'],rank=max(record['rank'],rank(ctx)),phase='armed')
        record.pop('proposal',None)
        if mode=='next-visit':ctx.state.set(KEY,record);return 'OwnMachine reminder enabled for the next matching visit or command. No scheduled job was created.'
        from .scheduled_reminders import arm
        return arm(ctx,record)


def nudge(ctx,source,deliver=None):
    """Deliver a consent-bound nudge from an authenticated visit or command."""
    if not load(ctx).get('enabled'): return
    expected={'kind':'terminal'} if source is None else target(ctx,source)
    with locked(ctx):
        record=refresh(ctx,load(ctx))
        if (not record['enabled'] or record.get('mode')!='next-visit' or completed(ctx)
                or record.get('destination')!=expected or record['count']>=limit(ctx)
                or clock()-record['last_nudge_at']<86400 or record.get('reservation')):
            ctx.state.set(KEY,record);return
        reservation=secrets.token_hex(16);record['reservation']=reservation;ctx.state.set(KEY,record)
    try: accepted=deliver(MESSAGE) is True if deliver is not None else getattr(ctx.post_message(MESSAGE),'ok',False) is True
    except Exception: accepted=False
    with locked(ctx):
        record=load(ctx)
        if record.get('reservation')!=reservation:return
        record.pop('reservation',None)
        if accepted:
            record['count']=min(3,record['count']+1);record['last_nudge_at']=clock()
        ctx.state.set(KEY,record)


def register_hooks(ctx):
    if not callable(getattr(ctx,'register_hook',None)): return
    def local_open(session_id=None,platform=None,reason=None,**kwargs):
        if platform not in ('cli','tui','desktop') or reason not in ('create','resume'): return
        try: nudge(ctx,None)
        except (ValueError,OSError,RuntimeError): pass
    async def admitted(platform=None,source=None,**kwargs):
        # This hook fires only AFTER Hermes authenticates/admit-checks a real
        # inbound message. It never consumes or changes the user's message.
        from types import SimpleNamespace
        import asyncio
        if not isinstance(source,dict): return
        context=dict(platform=platform,source=SimpleNamespace(**{k:source.get(k) for k in ('user_id','chat_id','thread_id')}))
        try: await asyncio.to_thread(nudge,ctx,context)
        except (ValueError,OSError,RuntimeError): pass
    ctx.register_hook('on_session_open',local_open)
    ctx.register_hook('post_gateway_admission',admitted)
