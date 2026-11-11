import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('native_clipboard',Path(__file__).parents[1]/'scripts/native-clipboard-helper.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

class NativeClipboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.state=self.root/'testvm';self.state.mkdir()
        self.key=self.state/'guest_ed25519';self.key.write_text('fixture');self.key.chmod(0o600)
        (self.state/'guest_known_hosts').write_text('fixture')
        self.env={'OWNMACHINE_STATE_ROOT':str(self.root),'OWNMACHINE_GUEST_USER':'guest','OWNMACHINE_LUME_BIN':'/example/lume'}

    def test_dynamic_address_and_strict_key_auth(self):
        with patch.object(helper.subprocess,'check_output',return_value=json.dumps([{'name':'testvm','ipAddress':'192.0.2.3','status':'running'}])) as read:
            args=helper.ssh_args('testvm','/example/storage',self.env)
        self.assertIn('StrictHostKeyChecking=yes',args);self.assertIn('BatchMode=yes',args)
        self.assertIn('ForwardAgent=no',args);self.assertEqual(args[-1],'guest@192.0.2.3')
        self.assertIn(str(self.key),args);self.assertIn('--storage',read.call_args.args[0])
        self.assertNotIn('password',' '.join(args).lower())

    def test_invalid_identity_or_unsecured_key_does_not_connect(self):
        with patch.object(helper.subprocess,'check_output') as read:
            with self.assertRaises(ValueError): helper.ssh_args('../vm',env=self.env)
            self.key.chmod(0o644)
            with self.assertRaises(ValueError): helper.ssh_args('testvm',env=self.env)
            read.assert_not_called()

    def test_stopped_or_ambiguous_guest_is_rejected(self):
        for data in ([],[{'name':'testvm'}]*2,{'ipAddress':'192.0.2.3','status':'stopped'}):
            with patch.object(helper.subprocess,'check_output',return_value=json.dumps(data)):
                with self.assertRaises(ValueError): helper.ssh_args('testvm',env=self.env)

class NativeLauncherTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('native_launcher',Path(__file__).parents[1]/'scripts/ownmachine-native.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.binary=self.root/'native.app/Contents/MacOS/lume'
        self.binary.parent.mkdir(parents=True);self.binary.write_text('fixture')

    def test_running_guest_is_not_restarted_or_attached(self):
        with patch.object(self.module.subprocess,'check_output',return_value=json.dumps([{'name':'testvm','status':'running'}])), patch.object(self.module.subprocess,'call') as run:
            self.assertEqual(self.module.main(['--name','testvm','--lume',str(self.binary)]),1)
            run.assert_not_called()

    def test_stopped_guest_keeps_configuration_and_vnc_disabled(self):
        state=self.root/'state/testvm';state.mkdir(parents=True)
        (state/'guest_ed25519').write_text('fixture');(state/'guest_ed25519').chmod(0o600)
        (state/'guest_known_hosts').write_text('fixture')
        with patch.object(self.module.subprocess,'check_output',return_value=json.dumps([{'name':'testvm','status':'stopped'}])), patch.object(self.module.subprocess,'call',return_value=0) as run, patch('builtins.print'):
            self.assertEqual(self.module.main(['--name','testvm','--guest-user','guest','--storage','/example/storage','--state-root',str(self.root/'state'),'--lume',str(self.binary)]),0)
            self.assertIn('disabled',run.call_args.args[0]);self.assertIn('/example/storage',run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs['env']['OWNMACHINE_GUEST_USER'],'guest')
            self.assertEqual(run.call_args.kwargs['env']['LUME_CLIPBOARD_AUTOSYNC'],'0')

    def test_build_uses_selected_app_without_starting_guest(self):
        with patch.object(self.module.subprocess,'call',return_value=0) as run, patch.object(self.module.subprocess,'check_output') as query:
            self.assertEqual(self.module.main(['--build','--lume',str(self.binary)]),0)
            self.assertEqual(run.call_args.kwargs['env']['OWNMACHINE_NATIVE_APP'],str(self.root/'native.app'))
            query.assert_not_called()
