import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('provision', Path(__file__).parents[1] / 'scripts/provision-vm.py')
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        for p in [patch.object(provision.Path, 'home', return_value=self.home),
                  patch.object(provision.sys, 'argv', ['provision', '--verification-vnc-port', '55000']),
                  patch.object(provision.os, 'umask')]:
            p.start()
            self.addCleanup(p.stop)

    @patch.object(provision.subprocess, 'run')
    def test_existing_vm_never_recreated(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '[{"name":"ownmachine"}]')
        self.assertEqual(provision.main(), 2)
        self.assertEqual(run.call_count, 1)

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_low_disk_refuses_creation(self, run, usage):
        run.return_value = subprocess.CompletedProcess([], 0, '[]')
        usage.return_value.free = 50 * 1024**3
        self.assertEqual(provision.main(), 2)
        self.assertEqual(run.call_count, 1)

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_create_uses_fixed_arguments(self, run, usage):
        usage.return_value.free = 200 * 1024**3
        run.side_effect = [subprocess.CompletedProcess([], 0, '[]'), subprocess.CompletedProcess([], 0)]
        self.assertEqual(provision.main(), 0)
        args = run.call_args.args[0]
        self.assertEqual(args[1:3], ['create', 'ownmachine'])
        self.assertEqual(args[-2:], ['--network', 'nat'])
        self.assertIn('--verification-vnc', args)
        self.assertEqual(args[args.index('--verification-vnc')+1], 'disabled')
        self.assertNotIn('--vnc-port', args)
        self.assertEqual(run.call_args.kwargs['env']['LUME_TELEMETRY_ENABLED'], 'false')
        self.assertNotIn('shell', run.call_args.kwargs)
        state = json.loads((self.home / '.local/state/ownmachine/ownmachine/provision.json').read_text())
        self.assertEqual(state['phase'], 'created')

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_timeout_no_retry(self, run, usage):
        usage.return_value.free = 200 * 1024**3
        run.side_effect = [subprocess.CompletedProcess([], 0, '[]'), subprocess.TimeoutExpired('lume', 5400)]
        self.assertEqual(provision.main(), 1)
        self.assertEqual(run.call_count, 2)
        state = json.loads((self.home / '.local/state/ownmachine/ownmachine/provision.json').read_text())
        self.assertEqual(state['code'], 'provision_timeout_no_retry')

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_preflight_is_read_only_and_reports_sparse_capacity(self, run, usage):
        usage.return_value.free = 43 * 1024**3
        with patch.object(provision.sys, 'argv', ['provision', '--preflight']), patch('builtins.print') as output:
            self.assertEqual(provision.main(), 2)
        data = json.loads(output.call_args.args[0])
        self.assertEqual(data['virtual_disk_gib'], 64)
        self.assertEqual(data['required_free_gib'], 60)
        self.assertEqual(data['additional_free_gib'], 17)
        self.assertFalse((self.home / '.local').exists())
        run.assert_not_called()

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_sparse_disk_does_not_require_full_virtual_capacity(self, run, usage):
        usage.return_value.free = 65 * 1024**3
        run.side_effect = [subprocess.CompletedProcess([], 0, '[]'), subprocess.CompletedProcess([], 0)]
        with patch.object(provision.sys, 'argv', ['provision', '--verification-vnc-port', '55000', '--disk-gb', '100']):
            self.assertEqual(provision.main(), 0)
        args = run.call_args.args[0]
        self.assertEqual(args[args.index('--disk-size')+1], '100GB')
        self.assertEqual(args[args.index('--memory')+1], '8GB')

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_configurable_budget_and_second_capacity_check(self, run, usage):
        usage.side_effect = [type('Space', (), {'free': 80 * 1024**3})(), type('Space', (), {'free': 65 * 1024**3})()]
        run.return_value = subprocess.CompletedProcess([], 0, '[]')
        with patch.object(provision.sys, 'argv', ['provision', '--verification-vnc-port', '55000', '--min-free-gb', '70']):
            self.assertEqual(provision.main(), 2)
        self.assertEqual(run.call_count, 1)

    @patch.object(provision.shutil, 'disk_usage')
    @patch.object(provision.subprocess, 'run')
    def test_storage_is_passed_to_listing_and_create(self, run, usage):
        usage.return_value.free = 200 * 1024**3
        run.side_effect = [subprocess.CompletedProcess([], 0, '[]'), subprocess.CompletedProcess([], 0)]
        storage = self.home / 'selected-storage'
        with patch.object(provision.sys, 'argv', ['provision', '--storage-dir', str(storage)]):
            self.assertEqual(provision.main(), 0)
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[argv.index('--storage') + 1], str(storage))
        self.assertEqual(usage.call_args.args[0], self.home)
