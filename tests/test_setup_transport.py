import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_support import module
from ownmachine import onboarding as o, setup_transport as t
from test_onboarding_commands import Context, args
endpoint=module('tested_setup_endpoint','scripts/setup-endpoint.py')


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.plan=dict(o.DEFAULTS,target='remote',host_alias='runtime-agent',storage_dir='/example/storage')
        self.ctx=Context(dict(setup_plan=self.plan,setup_host_alias='setup-only',setup_source_sha256='a'*64))

    def receipt(self,argv,request,timeout):
        self.assertIn('StrictHostKeyChecking=yes',argv)
        self.assertEqual(argv[-1],'ownmachine-setup-v1')
        return {**{k:v for k,v in request.items() if k!='apply'},'ok':True,
                'outcomes':{request['step']:{'stage':'observed','observed_at':int(time.time())}}}

    def test_import_only_matching_channel_receipt_and_show_status(self):
        with patch.object(t,'exchange',side_effect=self.receipt):
            result=o.setup(self.ctx,args('setup','--run','preflight'))
        self.assertTrue(result['ok'])
        report,_=o.execute(self.ctx,args('status','--json'))
        self.assertEqual(json.loads(report)['execution']['outcomes']['preflight']['stage'],'observed')

    def test_mismatches_never_import_or_retry(self):
        for key in ('nonce','source_sha256','plan_digest','vm','step'):
            def altered(argv,request,timeout):
                result=self.receipt(argv,request,timeout);result[key]='wrong';return result
            with self.subTest(key=key),patch.object(t,'exchange',side_effect=altered) as call:
                with self.assertRaises(ValueError):t.dispatch(self.ctx,self.plan,'preflight')
                self.assertEqual(call.call_count,1)
                self.assertEqual(self.ctx.state.get(t.KEY)['stage'],'needs_inspection')

    def test_apply_and_separate_setup_identity_required(self):
        with self.assertRaises(ValueError):t.dispatch(self.ctx,self.plan,'build')
        self.ctx.settings['setup_host_alias']='runtime-agent'
        with self.assertRaises(ValueError):t.dispatch(self.ctx,self.plan,'preflight')

    def test_chat_does_not_block_or_execute_remote_mutations(self):
        o.register_commands(self.ctx)
        with patch.object(t,'exchange',side_effect=AssertionError('network')):
            self.assertIn('operator terminal',self.ctx.slash('setup --run build --apply'))

    def test_configuration_changes_invalidate_imported_progress(self):
        with patch.object(t,'exchange',side_effect=self.receipt):t.dispatch(self.ctx,self.plan,'preflight')
        self.ctx.settings['setup_source_sha256']='b'*64
        self.assertEqual(t.summary(self.ctx,self.plan)['stage'],'configuration_changed')

    def test_output_is_bounded_and_timeout_does_not_retry(self):
        with self.assertRaises(ValueError):t.exchange([sys.executable,'-c','import sys; sys.stdin.read(); print("x"*100000)'],{},5)
        with self.assertRaises(ValueError):t.exchange([sys.executable,'-c','import time; time.sleep(5)'],{},.05)

    def test_guide_is_release_pinned_or_full_commit(self):
        with patch.object(Path,'read_text',return_value='version: 9.8.7\n'):
            self.assertIn('/v9.8.7/',o.guide(self.ctx))
        self.ctx.settings['setup_guide_ref']='b'*40
        self.assertIn('/'+'b'*40+'/',o.guide(self.ctx))
        self.ctx.settings['setup_guide_ref']='develop'
        with self.assertRaises(ValueError):o.guide(self.ctx)

    def test_endpoint_refuses_wrong_identity_and_replay(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'home',return_value=Path(folder).resolve()):
            c=dict(source_sha256='a'*64,allowed_steps=['preflight'])
            req=dict(format=1,nonce='b'*64,source_sha256='a'*64,plan_digest=t.digest(self.plan),vm='ownmachine',step='preflight',apply=False)
            observed=dict(ok=True,stage='observed',free_gib=200,swift_available=True,cpu_count=32,memory_gib=128)
            with patch.object(endpoint,'command',return_value=['fixed']),patch.object(endpoint.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(observed))) as run:
                self.assertTrue(endpoint.execute(req,c,self.plan)['ok'])
                with self.assertRaises(ValueError):endpoint.execute(req,c,self.plan)
                self.assertEqual(run.call_count,1)
                progress=endpoint.execute(dict(req,nonce='c'*64,step='progress'),c,self.plan)
                self.assertEqual(progress['outcomes']['preflight']['stage'],'observed')
                with self.assertRaises(ValueError):endpoint.execute(dict(req,nonce='d'*64,vm='other'),c,self.plan)

    def test_endpoint_requires_preflight_before_creation(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'home',return_value=Path(folder).resolve()):
            c=dict(source_sha256='a'*64,allowed_steps=['build'])
            req=dict(format=1,nonce='b'*64,source_sha256='a'*64,plan_digest=t.digest(self.plan),vm='ownmachine',step='build',apply=True)
            with patch.object(endpoint,'command',side_effect=AssertionError('mutation')):
                with self.assertRaisesRegex(ValueError,'preflight'):endpoint.execute(req,c,self.plan)

    def test_source_fingerprint_refuses_unhashed_symlink_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'elsewhere').mkdir();(root/'scripts').symlink_to(root/'elsewhere')
            with patch.object(endpoint,'ROOT',root),self.assertRaisesRegex(ValueError,'symlinks'):
                endpoint.fingerprint()

    def test_future_or_corrupt_progress_is_preserved_before_network(self):
        for old in ({'format':2}, ['invalid']):
            self.ctx.state.set(t.KEY,old)
            with patch.object(t,'exchange',side_effect=AssertionError('network')):
                with self.assertRaisesRegex(ValueError,'invalid_setup_execution_state'):
                    t.dispatch(self.ctx,self.plan,'preflight')
            self.assertEqual(self.ctx.state.get(t.KEY),old)
