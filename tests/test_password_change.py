import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('password_change', Path(__file__).parents[1] / 'scripts/change-guest-password.py')
change = importlib.util.module_from_spec(spec)
spec.loader.exec_module(change)


class PasswordChangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = self.home / '.local/state/ownmachine/ownmachine'
        self.state.mkdir(parents=True)
        (self.state / 'guest-password').write_text('old-fixture-password\n')
        self.new = self.home / 'new-password'
        self.new.write_text('new-fixture-password\n')
        for p in [patch.object(change.Path, 'home', return_value=self.home),
                  patch.object(change.sys, 'argv', ['change', '--password-file', str(self.new)]),
                  patch.object(change.os, 'umask'),
                  patch.object(change.subprocess, 'check_output', return_value='[{"name":"ownmachine","status":"running","ipAddress":"192.0.2.1"}]')]:
            p.start(); self.addCleanup(p.stop)

    @patch.object(change.subprocess, 'run')
    def test_success_persists_verified_password_without_printing(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        out = io.StringIO()
        with contextlib.redirect_stdout(out): change.main()
        self.assertEqual((self.state / 'guest-password').read_text(), self.new.read_text())
        self.assertFalse((self.state / 'guest-password.pending').exists())
        self.assertNotIn('fixture-password', out.getvalue())
        self.assertTrue(json.loads(out.getvalue())['keychain_verified'])

    @patch.object(change.subprocess, 'run')
    def test_failure_keeps_both_recovery_values(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1)]
        with self.assertRaises(RuntimeError): change.main()
        self.assertEqual((self.state / 'guest-password').read_text(), 'old-fixture-password\n')
        self.assertEqual((self.state / 'guest-password.pending').read_text(), self.new.read_text())

    @patch.object(change.subprocess, 'run')
    def test_pending_change_refuses_retry(self, run):
        (self.state / 'guest-password.pending').write_text('fixture')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): change.main()
        run.assert_not_called()
