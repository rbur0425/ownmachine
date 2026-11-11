import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine.config import Config
from ownmachine.lease import Lease
spec = importlib.util.spec_from_file_location('soak', Path(__file__).parents[1] / 'scripts/ownmachine-soak.py')
soak = importlib.util.module_from_spec(spec); spec.loader.exec_module(soak)


class SoakTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.config = Config(host_alias='example-mac', control_dir=str(self.root))
        self.lease = Lease(self.root / 'lease.db'); self.lease.transfer('human')
        self.backend = Mock(); self.backend.capture.return_value = SimpleNamespace(width=100,height=100,png_bytes_len=100)
        self.backend.list_apps.return_value = ['PRIVATE_APP']; self.backend.list_windows.return_value = ['PRIVATE_TITLE']
        self.factory = Mock(return_value=self.backend)
    def run_soak(self, **kwargs):
        return soak.run(self.config, samples=3, interval=.1, backend_factory=self.factory, sleep=lambda _: None, **kwargs)
    def test_reads_do_not_change_lease_or_dispatch_writes(self):
        before = self.lease.status(); report = self.run_soak()
        self.assertTrue(report['ok']); self.assertEqual(report['completed_samples'], 3)
        self.assertEqual(before, self.lease.status()); self.assertNotIn('PRIVATE', json.dumps(report))
        self.assertEqual([call[0] for call in self.backend.mock_calls], ['start', 'list_apps', 'list_windows', 'list_apps', 'list_windows', 'list_apps', 'list_windows', 'stop'])
    def test_capture_opt_in_never_stores_payload(self):
        report = self.run_soak(capture=True)
        self.assertTrue(report['ok']); self.backend.capture.assert_called_with(mode='vision', app='screen')
        self.backend.list_windows.assert_not_called()
        self.assertEqual(set(p.name for p in self.root.iterdir()), {'lease.db'})
    def test_control_change_stops_without_restoring_or_reclaiming(self):
        self.backend.list_windows.side_effect = lambda: self.lease.transfer('agent')
        report = self.run_soak()
        self.assertEqual(report['status'], 'control_changed'); self.assertFalse(report['ok'])
        self.assertEqual(report['completed_samples'], 1); self.assertEqual(self.lease.status()['controller'], 'agent')
        self.backend.stop.assert_called_once()
    def test_error_is_sanitized_and_not_retried(self):
        self.backend.list_apps.side_effect = RuntimeError('PRIVATE_TOKEN')
        report = self.run_soak()
        self.assertEqual(report['status'], 'native_read_failed'); self.assertNotIn('PRIVATE', json.dumps(report))
        self.backend.list_apps.assert_called_once(); self.backend.stop.assert_called_once()
    def test_busy_session_and_interrupt_are_reported(self):
        self.backend.start.side_effect = BlockingIOError()
        self.assertEqual(self.run_soak()['status'], 'native_session_busy')
        self.backend.start.side_effect = KeyboardInterrupt()
        self.assertEqual(self.run_soak()['status'], 'interrupted')
    def test_missing_lease_is_not_initialized(self):
        (self.root / 'lease.db').unlink()
        self.assertFalse(self.run_soak()['ok']); self.factory.assert_not_called()
        self.assertFalse((self.root / 'lease.db').exists())
    def test_invalid_counts_and_intervals_fail_before_connection(self):
        for samples, interval in ((0, 1), (10001, 1), (True, 1), (1, float('nan')), (1, 0), (1, 301)):
            with self.assertRaises(ValueError):
                soak.run(self.config, samples=samples, interval=interval, backend_factory=self.factory)
        self.factory.assert_not_called()
    def test_cli_report_private_and_existing_file_never_overwritten(self):
        from unittest.mock import patch
        import contextlib
        import io
        import os
        output = self.root / 'report.json'
        args = ['ownmachine-soak.py', '--host-alias', 'example-mac', '--control-dir', str(self.root / 'missing'), '--output', str(output)]
        with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(soak.main(), 1)
        self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
        before = output.read_bytes()
        self.assertEqual(json.loads(before)['status'], 'read_or_configuration_failed')
        with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(soak.main(), 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertFalse((self.root / 'missing').exists())
