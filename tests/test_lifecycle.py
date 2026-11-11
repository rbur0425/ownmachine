import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
from ownmachine.config import Config
from ownmachine.lease import Lease,LeaseError
from ownmachine.lifecycle import operate,LifecycleError

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.config=Config(host_alias='example-mac',control_dir=self.tmp.name)
        self.lease=Lease(Path(self.tmp.name)/'lease.db')
    def test_success_invalidates_captures_and_stays_paused(self):
        old=self.lease.transfer('agent')['generation']
        def runner(argv,**kwargs):
            state=self.lease.status()
            self.assertEqual(state['controller'],'paused');self.assertTrue(state['pending'])
            self.assertNotIn('shell',kwargs);self.assertIn('StrictHostKeyChecking=yes',argv)
            return subprocess.CompletedProcess(argv,0,json.dumps({'ok':True,'vm_state':'running','secret':'not forwarded'}))
        result=operate(self.config,'start',runner)
        self.assertNotIn('secret',json.dumps(result))
        self.assertGreater(self.lease.status()['generation'],old)
        self.assertFalse(self.lease.status()['pending'])
        self.assertEqual(self.lease.status()['controller'],'paused')
    def test_timeout_is_not_replayed_and_needs_review(self):
        calls=[]
        def runner(*args,**kwargs):calls.append(1);raise subprocess.TimeoutExpired('ssh',120)
        with self.assertRaises(LifecycleError):operate(self.config,'restart',runner)
        self.assertEqual(len(calls),1);self.assertTrue(self.lease.status()['pending'])
        with self.assertRaises(LeaseError):self.lease.transfer('agent',acknowledge=False)
        with self.assertRaises(LeaseError):operate(self.config,'start',runner)
        self.assertEqual(len(calls),1)
        self.lease.transfer('paused',acknowledge=True)
        self.assertFalse(self.lease.status()['pending'])
    def test_failed_and_wrong_state_responses_are_not_success(self):
        for code,body in [(1,'secret'),(0,'[]'),(0,'{"ok":true,"vm_state":"running"}')]:
            self.lease.transfer('paused')
            def runner(*a,**k):return subprocess.CompletedProcess([],code,body)
            with self.assertRaises(LifecycleError):operate(self.config,'stop',runner)
            self.assertTrue(self.lease.status()['pending'])
    def test_invalid_operation_never_dispatches(self):
        def runner(*a,**k):self.fail('must not dispatch')
        with self.assertRaises(ValueError):operate(self.config,'delete',runner)
