import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_support import module
retirement=module('tested_retirement','scripts/retire-setup-key.py')
from ownmachine import setup_acceptance as a, setup_transport as t
from test_onboarding_commands import Context
from test_native_provider import OwnMachineBackend


class RetirementTests(unittest.TestCase):
    def test_exact_key_removed_and_other_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(Path,'home',return_value=Path(tmp).resolve()):
            h=Path(tmp).resolve();(h/'.ssh').mkdir(mode=0o700);state=h/'state';state.mkdir(mode=0o700)
            public=h/'setup.pub';public.write_text('ssh-ed25519 '+base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20'+b'a'*32).decode());public.chmod(0o600)
            c=dict(_config_path=str(h/'endpoint.json'),setup_public_key_file=str(public))
            entry,_=retirement.entry(Path(c['_config_path']),public)
            keys=h/'.ssh/authorized_keys';other=b'# owner\nrestrict ssh-ed25519 unrelated comment\n\n'
            keys.write_bytes(other+entry.encode()+b'\n');keys.chmod(0o600)
            retirement.retire(c,state)
            self.assertEqual(keys.read_bytes(),other)
            self.assertEqual(keys.stat().st_mode&0o777,0o600)
            self.assertEqual(json.loads((state/'retirement.json').read_text())['stage'],'retired')
            with self.assertRaises(ValueError):retirement.retire(c,state)

    def test_different_authorization_is_never_removed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(Path,'home',return_value=Path(tmp).resolve()):
            h=Path(tmp).resolve();(h/'.ssh').mkdir();p=h/'.ssh/authorized_keys';p.write_text('ssh-ed25519 fixture owner\n');p.chmod(0o600)
            with patch.object(retirement,'entry',return_value=('restrict ssh-ed25519 fixture','fixture')):
                with self.assertRaises(ValueError):retirement.retire(dict(_config_path='/unused',setup_public_key_file='/unused'),h)
            self.assertEqual(p.read_text(),'ssh-ed25519 fixture owner\n')

    def test_failed_capture_never_retires_key(self):
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan=dict(host_alias='agent',vm_name='vm',control_dir='/control')
        with patch.object(t,'dispatch',return_value={'ok':True}) as dispatch,patch.object(a,'capture',side_effect=ValueError('permission_required')):
            with self.assertRaises(ValueError):a.finish(ctx,plan,True)
            self.assertEqual([c.args[2] for c in dispatch.call_args_list],['verify'])

    def test_read_only_verify_does_not_retire(self):
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan=dict(host_alias='agent',vm_name='vm',control_dir='/control')
        with patch.object(t,'dispatch',return_value={'ok':True}) as dispatch,patch.object(a,'capture',return_value={'sha256':'a'*64,'width':10,'height':10,'captured_at':1}):
            result=a.finish(ctx,plan)
            self.assertEqual(result['stage'],'screenshot_verified')
            self.assertEqual(dispatch.call_count,1)

    def test_changed_transport_cannot_reuse_acceptance(self):
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan={'vm_name':'fixture'}
        record=dict(a.identity(ctx,plan),stage='complete')
        self.assertTrue(a.matches(ctx,plan,record))
        ctx.settings['setup_ssh_config']='/different/config'
        self.assertFalse(a.matches(ctx,plan,record))

    def test_retirement_ack_without_ssh_denial_never_completes(self):
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan=dict(host_alias='agent',vm_name='vm',control_dir='/control')
        with patch.object(t,'dispatch',return_value={'ok':True}),patch.object(a,'capture',return_value={}),patch.object(t,'prove_retired',side_effect=ValueError('key_still_works')):
            with self.assertRaises(ValueError):a.finish(ctx,plan,True)
        self.assertEqual(ctx.state.get(a.KEY)['stage'],'retiring')

    def test_completed_acceptance_does_not_reuse_retired_transport(self):
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan=dict(host_alias='agent',vm_name='vm',control_dir='/control')
        ctx.state.set(a.KEY,dict(a.identity(ctx,plan),stage='complete'))
        with patch.object(t,'dispatch') as dispatch:
            self.assertEqual(a.finish(ctx,plan,True)['stage'],'complete')
            dispatch.assert_not_called()

    def test_status_reports_completed_acceptance_without_remote_call(self):
        from ownmachine import onboarding as o
        from test_onboarding_commands import args
        plan=dict(o.DEFAULTS,host_alias='agent',control_dir='/control')
        ctx=Context(dict(setup_plan=plan,setup_host_alias='setup',setup_source_sha256='a'*64))
        ctx.state.set(a.KEY,dict(a.identity(ctx,plan),stage='complete'))
        with patch.object(t,'dispatch') as dispatch:
            text,code=o.execute(ctx,args('status','--json'))
            self.assertEqual(json.loads(text)['stage'],'complete')
            self.assertEqual(code,0)
            dispatch.assert_not_called()

    @unittest.skipIf(OwnMachineBackend is None, 'Requires installed Hermes public provider contract')
    def test_local_blank_plan_alias_uses_explicit_runtime_alias(self):
        from ownmachine import onboarding as o
        from ownmachine.provider import OwnMachineBackend
        from test_native_provider import FakeTransport
        with tempfile.TemporaryDirectory() as tmp:
            plan=dict(o.DEFAULTS,target='local',control_dir=tmp)
            ctx=Context(dict(host_alias='paired-local-agent',control_dir=tmp))
            transport=FakeTransport();original=transport.call
            def call(name,args):
                return original('get_window_state' if name=='get_desktop_state' else name,args)
            transport.call=call
            backend=OwnMachineBackend(o.configuration(ctx),transport=transport)
            with patch('ownmachine.provider.OwnMachineBackend',return_value=backend):
                proof=a.capture(ctx,plan)
            self.assertEqual(proof['width'],100)
            bound=a.identity(ctx,plan)
            ctx.settings['host_alias']='another-agent'
            self.assertFalse(a.matches(ctx,plan,bound))
            plan['target']='remote'
            with self.assertRaisesRegex(ValueError,'runtime_plan_mismatch'):
                a.capture(ctx,plan)

    def test_client_capture_failure_has_separate_actionable_status(self):
        from test_onboarding_commands import args
        ctx=Context(dict(setup_host_alias='setup',setup_source_sha256='a'*64))
        plan=dict(host_alias='agent',vm_name='vm',control_dir='/control')
        with patch.object(t,'dispatch',return_value={'ok':True}),patch.object(a,'capture',side_effect=ValueError('runtime_plan_mismatch')):
            with self.assertRaises(ValueError):a.finish(ctx,plan,True)
        message=a.failure_guidance(ctx,args('setup','--run','verify'),ValueError())
        self.assertIn('Host verification passed',message)
        self.assertIn('NOT been retired',message)
