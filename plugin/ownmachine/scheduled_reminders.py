"""Consent-bound one-shot scheduling using public Hermes interfaces."""
import datetime as dt
import json
import os
import secrets
import sys
from . import reminder_scheduler as scheduler


def name(record): return 'ownmachine-reminder-'+record['intent']


def matching(ctx, record):
    rows=[j for j in scheduler.jobs(ctx) if j.get('name')==name(record)]
    if len(rows)>1: raise ValueError('duplicate_reminder_jobs_require_inspection')
    return rows


def valid(record, job):
    return (job.get('job_id')==record.get('job_id') and job.get('name')==name(record)
            and job.get('deliver')==record.get('deliver') and job.get('no_agent') is True
            and job.get('script')==name(record)+'.py')


def reconcile(ctx, record):
    if not record.get('intent'): return record
    rows=matching(ctx,record)
    if not rows:
        record.update(enabled=False,phase='job_missing_requires_review')
        return record
    job=rows[0]
    if not record.get('job_id'):
        record['job_id']=job['job_id']
        record.update(enabled=False,phase='scheduling_unknown')
    if not valid(record,job):
        record.update(enabled=False,phase='job_changed_requires_review')
    elif record.get('emitted_at'):
        if job.get('last_status')=='ok' and not job.get('last_delivery_error') and not job.get('last_delivery_unverified'):
            record['count']=min(3,record['count']+1)
            record['last_nudge_at']=max(record['last_nudge_at'],record.pop('emitted_at'))
            record.update(enabled=False,phase='delivered')
        elif job.get('last_status') in ('error','delivery_failed','cancelled'):
            record.update(enabled=False,phase='delivery_failed')
    return record


def cancel(ctx,record):
    if not record.get('intent'): return record
    for job in matching(ctx,record):
        # Persisted disabled consent already makes future helper executions silent.
        scheduler.cli(ctx,'cron','cancel',job['job_id'],'--reason','OwnMachine reminder disabled')
        scheduler.rpc(ctx,'remove',job['job_id'])
    record.pop('intent',None);record.pop('job_id',None);record.pop('emitted_at',None)
    return record


def helper(ctx, token):
    from .reminders import MESSAGE
    home=scheduler.home(ctx);directory=home/'scripts'
    if any(p.is_symlink() for p in (directory,*directory.parents)): raise ValueError('unsafe_script_directory')
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    filename='ownmachine-reminder-'+token+'.py'
    argv=[sys.executable,'-c','import sys; from hermes_cli.main import main; sys.argv=["hermes","ownmachine","remind","emit","--token",sys.argv[1]]; raise SystemExit(main())',token]
    code=('import os, subprocess, sys\n'+'os.environ["HERMES_HOME"]='+repr(str(home))+'\n'
          +'try:\n    result=subprocess.run('+repr(argv)+',capture_output=True,text=True,timeout=120)\n'
          +'except Exception:\n    sys.exit(0)\n'
          +'if result.returncode: sys.exit(0)\n'
          +'text=result.stdout.strip()\n'
          +'if text=='+repr(MESSAGE)+': print(text)\n'
          +'elif text: sys.exit(0)\n')
    fd=os.open(directory/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:f.write(code)
    return filename


def arm(ctx,record):
    from .reminders import KEY
    record.update(intent=secrets.token_hex(16),phase='creating')
    dest=record['destination'];record['deliver']=':'.join(dest[k] for k in ('platform','chat_id','thread_id') if dest.get(k))
    ctx.state.set(KEY,record)
    try:
        script=helper(ctx,record['intent'])
        scheduler.create(ctx,name=name(record),schedule=dt.datetime.fromtimestamp(record['due'],dt.timezone.utc).isoformat(),deliver=record['deliver'],script=script)
        rows=matching(ctx,record)
        if len(rows)!=1: raise ValueError('scheduled_job_not_unique')
        record['job_id']=rows[0]['job_id']
        if not valid(record,rows[0]) or rows[0].get('enabled') is not False or rows[0].get('next_run_at'):
            scheduler.rpc(ctx,'remove',record['job_id'])
            raise ValueError('scheduled_job_not_bound_paused')
        record['phase']='armed';ctx.state.set(KEY,record)
        scheduler.rpc(ctx,'resume',record['job_id'])
    except Exception:
        record.update(enabled=False,phase='scheduling_unknown');ctx.state.set(KEY,record)
        raise ValueError('reminder_outcome_uncertain_use_status_or_off_do_not_repeat') from None
    return 'One reminder scheduled for the approved destination. Hermes gateway must remain running; no model is invoked.'


def emit(ctx,record,token,now):
    from .reminders import KEY,MESSAGE,limit
    if (not record['enabled'] or record.get('mode')!='tomorrow' or record.get('intent')!=token
            or record.get('emitted_at') or not record.get('job_id') or record['count']>=limit(ctx)
            or not record.get('due',0)<=now<=record.get('due',0)+3600
            or now-record['last_nudge_at']<86400):
        ctx.state.set(KEY,record);return ''
    rows=matching(ctx,record)
    if len(rows)!=1 or not valid(record,rows[0]):
        record.update(enabled=False,phase='job_changed_requires_review');ctx.state.set(KEY,record);return ''
    record.update(emitted_at=now,phase='awaiting_delivery_receipt');ctx.state.set(KEY,record)
    return MESSAGE
