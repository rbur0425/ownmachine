import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_mac', ROOT / 'scripts/setup-mac.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.plan = dict(m.DEFAULTS, target='remote', storage_dir=str(self.home / 'guests'))
        self.planfile = self.home / 'plan.json'
        self.planfile.write_text(json.dumps(dict(guest_os='macos', plan=self.plan)))
        self.args = SimpleNamespace(plan_file=self.planfile, step='build', apply=False,
                                    app=self.home / 'native.app', build_dir=self.home / 'build', ipsw='latest', preset='tahoe')
        for target, value in [('platform.system', 'Darwin'), ('platform.machine', 'arm64')]:
            p = patch.object(m.platform, target.split('.')[1], return_value=value)
            p.start(); self.addCleanup(p.stop)
        p = patch.object(m.os, 'geteuid', return_value=1000)
        p.start(); self.addCleanup(p.stop)
        p = patch.object(m.shutil, 'disk_usage', return_value=SimpleNamespace(free=200 * 1024**3))
        p.start(); self.addCleanup(p.stop)
        p = patch.object(m.Path, 'home', return_value=self.home)
        p.start(); self.addCleanup(p.stop)

    def test_dry_run_creates_nothing_and_never_runs_commands(self):
        before = list(self.home.iterdir())
        with patch.object(m.subprocess, 'run', side_effect=AssertionError('mutation')):
            self.assertEqual(m.execute(self.args)['stage'], 'planned')
        self.assertEqual(list(self.home.iterdir()), before)

    def test_build_verify_resume_and_changed_plan(self):
        self.args.apply = True
        with patch.object(m, 'run'), patch.object(m, 'verify_build') as verify, patch.object(m.subprocess, 'run') as command:
            self.assertEqual(m.execute(self.args)['stage'], 'verified')
            self.assertEqual(command.call_count, 1)
            self.assertEqual(m.execute(self.args)['stage'], 'verified')
            self.assertEqual(command.call_count, 1)
            self.assertEqual(verify.call_count, 2)
        checkpoint = self.home / '.local/state/ownmachine/ownmachine/setup/build.json'
        self.assertEqual(checkpoint.stat().st_mode & 0o777, 0o600)
        self.assertEqual(checkpoint.parent.stat().st_mode & 0o777, 0o700)
        self.plan['cpu'] = 6
        self.planfile.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError, 'changed'):
            m.execute(self.args)

    def test_failure_is_not_retried(self):
        self.args.apply = True
        with patch.object(m, 'run'), patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('build', 7200)):
            with self.assertRaises(subprocess.TimeoutExpired):
                m.execute(self.args)
        with patch.object(m.subprocess, 'run', side_effect=AssertionError('retry')):
            with self.assertRaisesRegex(ValueError, 'interrupted or failed'):
                m.execute(self.args)

    def test_existing_app_never_overwritten(self):
        self.args.app.mkdir()
        self.args.apply = True
        with self.assertRaisesRegex(ValueError, 'will not replace'):
            m.execute(self.args)

    def test_existing_build_adoption_requires_successful_verification(self):
        self.args.app.mkdir();self.args.apply=True;self.args.use_existing_build=True
        with patch.object(m,'verify_build',side_effect=ValueError('invalid_build')), patch.object(m.subprocess,'run') as command:
            with self.assertRaisesRegex(ValueError,'invalid_build'):m.execute(self.args)
            command.assert_not_called()

    def test_existing_build_adoption_does_not_rebuild(self):
        self.args.app.mkdir();self.args.apply=True;self.args.use_existing_build=True
        with patch.object(m,'verify_build'), patch.object(m.subprocess,'run') as command:
            self.assertEqual(m.execute(self.args)['stage'],'verified')
            command.assert_not_called()

    def test_provision_uses_explicit_storage_and_verifies(self):
        self.args.apply = True; self.args.step = 'provision'
        with patch.object(m, 'verify_build'), patch.object(m, 'run') as preflight, patch.object(m, 'verify_guest') as verify, patch.object(m.subprocess, 'run') as command:
            self.assertEqual(m.execute(self.args)['stage'], 'verified')
            argv = command.call_args.args[0]
            self.assertEqual(argv[argv.index('--storage-dir') + 1], self.plan['storage_dir'])
            self.assertIn('--preflight', preflight.call_args.args[0])
            verify.assert_called_once()

    def test_guest_wrong_state_refused(self):
        vm = dict(name='ownmachine', os='macOS', cpuCount=4, display='1900x1200', status='running')
        with patch.object(m, 'run', return_value=SimpleNamespace(stdout=json.dumps([vm]))):
            with self.assertRaisesRegex(ValueError, 'stopped'):
                m.verify_guest('lume', self.plan)

    def test_symlink_state_and_other_os_refused(self):
        target = self.home / 'state'; target.write_text('{}')
        link = self.home / 'link'; link.symlink_to(target)
        with self.assertRaises(OSError): m.read_state(link)
        self.planfile.write_text(json.dumps(dict(guest_os='linux', plan=self.plan)))
        with self.assertRaisesRegex(ValueError, 'Only macOS'): m.execute(self.args)

    def test_resource_bounds_match_provisioner(self):
        for key, value in [('cpu', 1), ('memory_gb', 7), ('disk_gb', 49), ('min_free_gb', 31), ('display', '500x500')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_plan(dict(self.plan, **{key: value}))

    def test_verified_guest_checks_every_resource(self):
        vm = dict(name='ownmachine', os='macOS', cpuCount=4, memorySize=8 * 1024**3,
                  diskSize={'total': 64 * 1024**3}, display='1900x1200', status='stopped')
        with patch.object(m, 'run', return_value=SimpleNamespace(stdout=json.dumps([vm]))):
            m.verify_guest('lume', self.plan)
        for key, value in [('memorySize', 0), ('diskSize', {'total': 0}), ('os', 'linux')]:
            with self.subTest(key=key), patch.object(m, 'run', return_value=SimpleNamespace(stdout=json.dumps([dict(vm, **{key: value})]))):
                with self.assertRaises(ValueError): m.verify_guest('lume', self.plan)

    def test_execution_lock_blocks_competing_runner(self):
        self.args.apply = True
        directory = self.home / '.local/state/ownmachine/ownmachine/setup'
        m.private_dir(directory)
        with (directory / 'execution.lock').open('w') as lock:
            m.fcntl.flock(lock, m.fcntl.LOCK_EX | m.fcntl.LOCK_NB)
            with patch.object(m.subprocess, 'run', side_effect=AssertionError('parallel mutation')):
                with self.assertRaises(BlockingIOError): m.execute(self.args)
