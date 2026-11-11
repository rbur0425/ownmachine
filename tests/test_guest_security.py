import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('secure_guest', Path(__file__).parents[1] / 'scripts/secure-guest.py')
secure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secure)


class GuestSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = self.home / '.local/state/ownmachine/ownmachine'
        self.state.mkdir(parents=True)
        (self.state / 'guest_ed25519').write_text('fixture')
        (self.state / 'guest_ed25519.pub').write_text('ssh-ed25519 fixture')
        for p in [patch.object(secure.Path, 'home', return_value=self.home),
                  patch.object(secure.sys, 'argv', ['secure-guest', '--guest-ip', '192.0.2.1']),
                  patch.object(secure.os, 'umask')]:
            p.start()
            self.addCleanup(p.stop)

    @patch.object(secure.subprocess, 'run')
    def test_bootstrap_then_pinned_key_and_redacted_result(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '26.1\n', '')
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(secure.main(), 0)
        secret = (self.state / 'guest-password').read_text().strip()
        self.assertRegex(secret, r'^[a-hjkmnp-z]{4}(?:-[a-hjkmnp-z]{4}){3}$')
        self.assertNotIn(secret, out.getvalue())
        self.assertIn('StrictHostKeyChecking=accept-new', run.call_args_list[0].args[0])
        for call in run.call_args_list[1:]:
            self.assertIn('StrictHostKeyChecking=yes', call.args[0])
            self.assertIn('BatchMode=yes', call.args[0])
        self.assertTrue(json.loads(out.getvalue())['password_rotated'])

    @patch.object(secure.subprocess, 'run')
    def test_no_rotation_without_key_verification(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 255)]
        with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(secure.main(), 1)
        self.assertFalse((self.state / 'guest-password').exists())
        self.assertEqual(run.call_count, 2)

    @patch.object(secure.subprocess, 'run')
    def test_existing_credentials_refuse_automatic_retry(self, run):
        (self.state / 'guest-password').write_text('fixture')
        with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(secure.main(), 2)
        run.assert_not_called()
