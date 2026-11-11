import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_onboarding_commands import Context, args
from ownmachine import reminders as r


class ReminderTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.ctx=Context(dict(setup_plan={'vm_name':'fixture'},setup_reminder_destination=dict(platform='test',user_id='owner',chat_id='chat')))
        self.ctx.state.data_dir=Path(temp.name).resolve()/'profile/plugin-data/ownmachine'
        self.entries=[];self.calls=[]
        def dispatch(name, fields):
            self.assertEqual(name,'cronjob_manage');self.calls.append(fields)
            action=fields['action']
            if action=='list':return json.dumps(dict(success=True,jobs=self.entries))
            if action=='create':
                self.assertTrue(fields['paused']);self.assertTrue(fields['no_agent']);self.assertEqual(fields['failure_deliver'],'local')
                job=dict(fields,job_id='job1');self.entries.append(job)
                return json.dumps(dict(success=True,job_id='job1',job=job,gateway_running=True))
            if action=='remove':self.entries=[]
            return json.dumps(dict(success=True))
        self.ctx.dispatch_tool=dispatch
        self.now=2000000000
        patcher=patch.object(r,'clock',side_effect=lambda:self.now);patcher.start();self.addCleanup(patcher.stop)

    def run_command(self,*command):return r.execute(self.ctx,args('remind',*command))
    def consent(self,mode='next-visit'):
        preview=self.run_command('later','--mode',mode)
        self.assertIn('Preview only',preview)
        token=r.load(self.ctx)['proposal']['token']
        return self.run_command('later','--mode',mode,'--confirm',token)

    def test_next_visit_has_no_job_and_daily_limit(self):
        self.consent('next-visit');self.assertEqual(self.calls,[])
        delivered=[]
        def post(text):
            delivered.append(text)
            return True
        r.nudge(self.ctx,None,post);r.nudge(self.ctx,None,post)
        self.assertEqual(len(delivered),1)
        for _ in range(4):
            self.now+=86400
            r.nudge(self.ctx,None,post)
        self.assertEqual(len(delivered),3)
        self.assertEqual(r.load(self.ctx)['count'],3)

    def test_changed_host_disables_and_failed_delivery_does_not_count(self):
        self.consent('next-visit');r.nudge(self.ctx,None,lambda text:False)
        self.assertEqual(r.load(self.ctx)['count'],0)
        self.ctx.settings['setup_host_alias']='changed'
        r.nudge(self.ctx,None,lambda text:self.fail('message'))
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_stage_retry_never_resets_budget_but_verified_advance_does(self):
        self.consent('next-visit');r.nudge(self.ctx,None,lambda text:True)
        self.ctx.state.set('setup_execution',dict(plan_digest=r.digest(r.canonical_plan(self.ctx)),source_sha256='',transport_digest=r.digest(dict(alias='',config='')),outcomes={'build':{'stage':'verified'}}))
        self.run_command('status');self.assertEqual(r.load(self.ctx)['count'],0)
        self.now+=86400;r.nudge(self.ctx,None,lambda text:True)
        self.run_command('status');self.assertEqual(r.load(self.ctx)['count'],1)

    def test_unknown_state_is_preserved(self):
        self.ctx.state.set(r.KEY,{'format':99})
        with self.assertRaises(ValueError):self.run_command('off')
        self.assertEqual(self.ctx.state.get(r.KEY),{'format':99})


    def test_scheduled_mode_requires_live_gateway(self):
        with patch('ownmachine.reminder_scheduler.jobs',side_effect=ValueError('unavailable')):
            with self.assertRaises(ValueError):self.run_command('later','--mode','tomorrow')
        self.assertEqual(self.calls,[])
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_preview_alone_never_enables(self):
        self.run_command('later','--mode','next-visit')
        r.nudge(self.ctx,None,lambda text:self.fail('unexpected delivery'))
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_expired_confirmation_preserves_disabled_state(self):
        self.run_command('later','--mode','next-visit')
        token=r.load(self.ctx)['proposal']['token'];self.now+=901
        with self.assertRaises(ValueError):self.run_command('later','--mode','next-visit','--confirm',token)
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_opt_out_and_completion_suppress_nudges(self):
        self.consent();self.run_command('off')
        r.nudge(self.ctx,None,lambda text:self.fail('unexpected delivery'))
        self.consent()
        from ownmachine.setup_acceptance import identity
        self.ctx.state.set('setup_acceptance',dict(identity(self.ctx,r.canonical_plan(self.ctx)),stage='complete'))
        r.nudge(self.ctx,None,lambda text:self.fail('unexpected delivery'))
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_unacknowledged_reservation_blocks_duplicate_delivery(self):
        self.consent();record=r.load(self.ctx);record['reservation']='interrupted'
        self.ctx.state.set(r.KEY,record)
        r.nudge(self.ctx,None,lambda text:self.fail('duplicate delivery'))
        self.run_command('off');self.assertNotIn('reservation',r.load(self.ctx))

    def test_chat_confirmation_is_bound_to_authorized_thread(self):
        self.ctx.settings['setup_allowed_senders']=[dict(platform='test',user_id='owner',chat_id='chat')]
        source=dict(platform='test',source=SimpleNamespace(user_id='owner',chat_id='chat',thread_id='one'))
        r.execute(self.ctx,args('remind','later','--mode','next-visit'),source)
        token=r.load(self.ctx)['proposal']['token']
        source['source'].thread_id='two'
        with self.assertRaises(ValueError):r.execute(self.ctx,args('remind','later','--mode','next-visit','--confirm',token),source)
        source['source'].thread_id='one'
        r.execute(self.ctx,args('remind','later','--mode','next-visit','--confirm',token),source)
        source['source'].thread_id='two'
        r.nudge(self.ctx,source,lambda text:self.fail('wrong thread'))
        source['source'].thread_id='one'
        delivered=[]
        r.nudge(self.ctx,source,lambda text:delivered.append(text) or True)
        self.assertEqual(delivered,[r.MESSAGE])
        self.ctx.settings['setup_allowed_senders']=[]
        self.assertFalse(r.refresh(self.ctx,r.load(self.ctx))['enabled'])

    def test_default_preview_and_confirmation_use_next_visit_in_terminal_and_chat(self):
        self.ctx.settings['setup_allowed_senders']=[dict(platform='test',user_id='owner',chat_id='chat')]
        chat=dict(platform='test',source=SimpleNamespace(user_id='owner',chat_id='chat',thread_id='one'))
        for source in (None,chat):
            with self.subTest(source='terminal' if source is None else 'chat'):
                r.execute(self.ctx,args('remind','off'),source)
                preview=r.execute(self.ctx,args('remind','later'),source)
                self.assertIn('Preview only',preview)
                record=r.load(self.ctx)
                self.assertFalse(record['enabled'])
                self.assertEqual(record['proposal']['mode'],'next-visit')
                r.execute(self.ctx,args('remind','later','--confirm',record['proposal']['token']),source)
                self.assertTrue(r.load(self.ctx)['enabled'])
                self.assertEqual(r.load(self.ctx)['mode'],'next-visit')
        self.assertEqual(self.calls,[])

    def test_only_verified_local_visit_hook_is_registered(self):
        hooks={};self.ctx.register_hook=lambda name,fn:hooks.__setitem__(name,fn)
        r.register_hooks(self.ctx)
        with patch.object(r,'nudge') as nudge:
            hooks['on_session_open'](platform='cron',reason='create')
            nudge.assert_not_called()
            hooks['on_session_open'](platform='cli',reason='resume')
            nudge.assert_called_once_with(self.ctx,None)
        self.assertNotIn('post_gateway_admission',hooks)
