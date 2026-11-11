import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.config import Config
from ownmachine.diagnostics import diagnose, render, REQUIRED_TOOLS
from ownmachine.lease import Lease

READY=dict(host_reachable=True,lume_installed=True,vm_state='running',
    driver_state='ready',driver_ready=True,guest_reachable=True,accessibility=True,
    screen_recording=True,capture_consent_verified=True)

class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/'control'
        self.config=Config(host_alias='example-mac',control_dir=str(self.directory))
        self.remote=patch('ownmachine.diagnostics.status',return_value=READY.copy()).start()
        self.ssh=patch('ownmachine.diagnostics.shutil.which',return_value='/usr/bin/ssh').start()
        self.transport=patch('ownmachine.diagnostics.MCPTransport').start()
        self.transport.return_value.tools={k:{} for k in REQUIRED_TOOLS}
        self.addCleanup(patch.stopall)
    def codes(self,report): return {c['code'] for c in report['checks']}
    def test_ready_does_not_create_state_or_dispatch(self):
        report=diagnose(self.config)
        self.assertTrue(report['ok']);self.assertFalse(self.directory.exists())
        self.transport.return_value.call.assert_not_called()
        self.transport.return_value.stop.assert_called_once()
        self.assertIn('control_not_initialized',self.codes(report))
    def test_configuration_fails_before_network(self):
        self.assertFalse(diagnose(Config())['ok']);self.remote.assert_not_called()
    def test_unsupported_permission_mode_fails_without_network(self):
        for mode in ("bounded", "unrestricted", "unknown"):
            self.assertIn("unsupported_permission_mode",self.codes(diagnose(self.config,mode)))
        self.remote.assert_not_called()
    def test_missing_ssh(self):
        self.ssh.return_value=None
        self.assertIn('ssh_missing',self.codes(diagnose(self.config)));self.remote.assert_not_called()
    def test_host_failure_is_sanitized(self):
        self.remote.return_value={'host_reachable':False,'code':'secret.example/password'}
        report=diagnose(self.config)
        self.assertIn('host_unreachable',self.codes(report));self.assertNotIn('secret.example',json.dumps(report))
        self.transport.assert_not_called()
    def test_stopped_vm_not_started(self):
        self.remote.return_value={**READY,'vm_state':'stopped'}
        self.assertIn('vm_stopped',self.codes(diagnose(self.config)));self.transport.assert_not_called()
    def test_lume_missing(self):
        self.remote.return_value={**READY,'lume_installed':False}
        self.assertIn('lume_missing',self.codes(diagnose(self.config)))
    def test_guest_unreachable(self):
        self.remote.return_value={**READY,'driver_state':'guest_unreachable','driver_ready':False}
        self.assertIn('guest_not_ready',self.codes(diagnose(self.config)))
    def test_permissions_have_individual_remedies(self):
        self.remote.return_value={**READY,'driver_state':'permissions_required',
            'driver_ready':False,'accessibility':False,'screen_recording':False,'capture_consent_verified':False}
        report=diagnose(self.config)
        self.assertTrue({'accessibility_required','screen_recording_required','capture_consent_required'}<=self.codes(report))
        self.assertIn('guided',render(report));self.transport.assert_not_called()
    def test_missing_tools_fails(self):
        self.transport.return_value.tools={}
        self.assertIn('incompatible_driver_tools',self.codes(diagnose(self.config)))
    def test_mcp_failure_closes_without_details(self):
        from ownmachine.transport import TransportError
        self.transport.return_value.start.side_effect=TransportError('private detail')
        report=diagnose(self.config)
        self.assertIn('mcp_unavailable',self.codes(report));self.assertNotIn('private detail',json.dumps(report))
        self.transport.return_value.stop.assert_called_once()
    def test_pending_marker_unchanged(self):
        lease=Lease(self.directory/'lease.db');lease.transfer('agent')
        with self.assertRaises(RuntimeError):
            with lease.write(lease.status()['generation']): raise RuntimeError()
        before=lease.status()
        self.assertIn('uncertain_outcome',self.codes(diagnose(self.config)))
        self.assertEqual(before,lease.status())
    def test_paused_warning_not_transport_failure(self):
        lease=Lease(self.directory/'lease.db')
        report=diagnose(self.config)
        self.assertTrue(report['ok']);self.assertIn('control_paused',self.codes(report))
        self.assertEqual(lease.status()['generation'],0)
    def test_corrupt_database_not_replaced(self):
        self.directory.mkdir();p=self.directory/'lease.db';p.write_text('broken')
        self.assertIn('control_unreadable',self.codes(diagnose(self.config)))
        self.assertEqual(p.read_text(),'broken')
    def test_live_viewer_does_not_read_access_token(self):
        import time
        self.directory.mkdir()
        (self.directory/'viewer-status.json').write_text(json.dumps({'heartbeat':time.time()}))
        (self.directory/'viewer-access.json').write_text('SECRET')
        report=diagnose(self.config)
        self.assertIn('viewer_running',self.codes(report));self.assertNotIn('SECRET',json.dumps(report))

class InstallTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'scripts/install-hermes.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'hermes-home'
        self.config=Config(host_alias='example-mac',vm_name='custom-vm',control_dir=str(self.root/'shared-control'))
    def test_fresh_home_has_only_plugin_and_portable_config(self):
        self.module.install(self.home,self.config)
        settings=json.loads((self.home/'config.yaml').read_text())
        self.assertEqual(settings['plugins']['entries']['ownmachine']['settings'],vars(self.config))
        self.assertEqual(settings['computer_use']['permission_mode'],'standard')
        self.assertTrue((self.home/'plugins/ownmachine/plugin.yaml').is_file())
        self.assertEqual((self.home/'plugins/ownmachine/LICENSE').read_bytes(), (self.module.ROOT/'LICENSE').read_bytes())
        self.assertFalse((self.home/'plugins/ownmachine/scripts').exists())
        self.assertFalse(Path(self.config.control_dir).exists())
        self.assertEqual((self.home.stat().st_mode & 0o777),0o700)
        receipt=json.loads((self.home/'ownmachine-install.json').read_text())
        self.assertTrue(receipt['plugin_files_sha256']['plugin.yaml'])
    def test_existing_home_refused_unchanged(self):
        self.home.mkdir();(self.home/'config.yaml').write_text('keep')
        with self.assertRaises(ValueError):self.module.install(self.home,self.config)
        self.assertEqual((self.home/'config.yaml').read_text(),'keep')
    def test_symlink_home_refused(self):
        self.home.symlink_to(self.root/'missing')
        with self.assertRaises(ValueError):self.module.install(self.home,self.config)
    def test_shared_directory_required(self):
        with self.assertRaises(ValueError):self.module.install(self.home,Config(host_alias='example'))
        self.assertFalse(self.home.exists())
    def test_copy_failure_rolls_back_only_new_home(self):
        with patch.object(self.module.shutil,'copytree',side_effect=OSError()):
            with self.assertRaises(OSError): self.module.install(self.home,self.config)
        self.assertFalse(self.home.exists())
        self.assertTrue(self.root.exists())

    def test_license_copy_failure_rolls_back_new_home(self):
        original=self.module.shutil.copyfile
        def copy(source,destination,*args,**kwargs):
            if Path(source)==self.module.ROOT/'LICENSE': raise OSError('license copy failed')
            return original(source,destination,*args,**kwargs)
        with patch.object(self.module.shutil,'copyfile',side_effect=copy):
            with self.assertRaisesRegex(OSError,'license copy failed'): self.module.install(self.home,self.config)
        self.assertFalse(self.home.exists())
