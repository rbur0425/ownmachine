import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_reminders as fixtures
from test_onboarding_commands import args
from ownmachine import reminders as r, scheduled_reminders as s, reminder_scheduler as gateway


class ScheduledTests(unittest.TestCase):
    run_command = fixtures.ReminderTests.run_command
    consent = fixtures.ReminderTests.consent
    def setUp(self):
        fixtures.ReminderTests.setUp(self)
        self.jobs=[]
        def create(ctx,**kw):self.jobs.append(dict(job_id='fixture',enabled=False,no_agent=True,next_run_at=None,**kw))
        def rpc(ctx,action='list',job_id=None):
            if action=='resume':self.jobs[0]['enabled']=True
            if action=='remove':self.jobs=[]
            return {'success':True,'jobs':self.jobs}
        for name,value in [('jobs',lambda ctx:self.jobs),('create',create),('rpc',rpc),('cli',lambda *a:'')]:
            p=patch.object(gateway,name,side_effect=value);p.start();self.addCleanup(p.stop)

    def test_schedule_emission_binding_and_acknowledged_count(self):
        self.consent('tomorrow');record=r.load(self.ctx);token=record['intent']
        self.assertEqual(self.run_command('emit','--token',token),'')
        self.now+=86400
        self.assertEqual(self.run_command('emit','--token',token),r.MESSAGE)
        self.assertEqual(r.load(self.ctx)['count'],0)
        self.assertEqual(self.run_command('emit','--token',token),'')
        self.jobs[0]['last_status']='ok';self.jobs[0]['last_delivery_unverified']=['test:chat']
        self.run_command('status');self.assertEqual(r.load(self.ctx)['count'],0)
        self.jobs[0]['last_delivery_unverified']=[]
        self.run_command('status');self.run_command('status')
        self.assertEqual(r.load(self.ctx)['count'],1)
        self.assertFalse(r.load(self.ctx).get('notice_pending'))

    def test_edited_destination_is_silent_and_disabled(self):
        self.consent('tomorrow');token=r.load(self.ctx)['intent'];self.now+=86400
        self.jobs[0]['deliver']='different:chat'
        self.assertEqual(self.run_command('emit','--token',token),'')
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_optout_removes_job_and_late_helper_stays_silent(self):
        self.consent('tomorrow');token=r.load(self.ctx)['intent']
        self.run_command('off');self.now+=86400
        self.assertEqual(self.jobs,[])
        self.assertEqual(self.run_command('emit','--token',token),'')

    def test_unknown_creation_never_repeats(self):
        self.run_command('later','--mode','tomorrow');token=r.load(self.ctx)['proposal']['token']
        with patch.object(gateway,'create',side_effect=RuntimeError('lost acknowledgement')):
            with self.assertRaises(ValueError):self.run_command('later','--mode','tomorrow','--confirm',token)
        self.assertEqual(r.load(self.ctx)['phase'],'scheduling_unknown')
        self.assertFalse(r.load(self.ctx)['enabled'])

    def test_helper_errors_exit_zero_and_print_nothing(self):
        self.consent('tomorrow')
        record=r.load(self.ctx);script=gateway.home(self.ctx)/'scripts'/(s.name(record)+'.py')
        import subprocess,sys
        # This fixture has no installed Hermes plugin; failure must be silent success.
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0)
        self.assertFalse(result.stdout)

    def test_offline_status_preserves_consent_but_reports_unavailable(self):
        self.consent('tomorrow')
        with patch.object(gateway,'jobs',side_effect=ValueError('offline')):
            state=json.loads(self.run_command('status'))
        self.assertTrue(state['enabled']);self.assertFalse(state['scheduler_available'])

    def test_skipped_job_explained_once_on_next_authorized_visit(self):
        self.consent('tomorrow');self.jobs[0]['last_status']='ok'
        seen=[]
        r.nudge(self.ctx,None,lambda text:seen.append(text) or True)
        self.run_command('status')
        r.nudge(self.ctx,None,lambda text:seen.append(text) or True)
        self.assertEqual(seen,[r.SKIPPED_MESSAGE])
        self.assertEqual(r.load(self.ctx)['count'],0)

    def test_optout_suppresses_skipped_notice(self):
        self.consent('tomorrow');self.jobs[0]['last_status']='ok';self.run_command('status')
        self.run_command('off')
        r.nudge(self.ctx,None,lambda text:self.fail('opted out'))
