import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
sys.path.insert(0, str(Path(__file__).parents[1] / 'viewer'))
from ownmachine.config import Config
import diagnostics as viewer_diagnostics

STATE = {'viewer_mode': 'vnc', 'control': {'controller': 'human', 'pending': False},
         'view_only': False, 'stream_connected': True, 'operation': None}
TOKEN = 'PRIVATE_TEST_TOKEN_' + 'a' * 32


class ViewerDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = Config(host_alias='example-mac', control_dir=str(self.directory))
        self.file = self.directory / 'viewer-access.json'
        self.access()
        self.state_patch = patch.object(viewer_diagnostics, 'read_state', return_value=STATE.copy())
        self.state = self.state_patch.start()
        self.dependency = patch.object(viewer_diagnostics.importlib.util, 'find_spec', return_value=object()).start()
        self.probe = patch.object(viewer_diagnostics, 'probe_vnc').start()
        self.addCleanup(patch.stopall)
    def access(self, url=None):
        self.file.write_text(json.dumps({'port': 12345, 'url': url or 'http://127.0.0.1:12345/#' + TOKEN}))
        self.file.chmod(0o600)
    def codes(self, report):
        return {c['code'] for c in report['checks']}
    def test_default_does_not_probe_or_change_files(self):
        before = self.file.read_bytes()
        report = viewer_diagnostics.diagnose(self.config, access_dir=self.directory)
        self.assertTrue(report['ok']); self.probe.assert_not_called()
        self.assertEqual(before, self.file.read_bytes())
        self.assertEqual(list(self.directory.iterdir()), [self.file])
        self.assertNotIn(TOKEN, json.dumps(report))
        self.assertIn('firewall_requires_external_check', self.codes(report))
    def test_probe_is_explicit_and_sanitized(self):
        self.probe.side_effect = RuntimeError('password=' + TOKEN)
        report = viewer_diagnostics.diagnose(self.config, probe=True, access_dir=self.directory)
        self.assertFalse(report['ok']); self.assertNotIn(TOKEN, json.dumps(report))
        self.assertIn('vnc_connection_failed', self.codes(report))
    def test_unsafe_destinations_and_permissions_refused_before_http(self):
        for url in ('https://127.0.0.1:12345/#' + TOKEN,
                    'http://example.invalid:12345/#' + TOKEN,
                    'http://127.0.0.1:12345/path#' + TOKEN,
                    'http://127.0.0.1:12345/?token=private#' + TOKEN,
                    'http://user@127.0.0.1:12345/#' + TOKEN):
            self.access(url)
            self.assertFalse(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)['ok'])
        self.access(); self.file.chmod(0o644)
        self.assertFalse(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)['ok'])
        self.state.assert_not_called()
    def test_missing_symlink_and_oversized_files_refused(self):
        self.file.unlink()
        self.assertIn('viewer_not_started', self.codes(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)))
        target = self.directory / 'target'; target.write_text('{}'); target.chmod(0o600)
        self.file.symlink_to(target)
        self.assertFalse(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)['ok'])
        self.file.unlink(); self.file.write_text('x' * 4097); self.file.chmod(0o600)
        self.assertFalse(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)['ok'])
        self.state.assert_not_called()
    def test_pending_and_held_input_are_distinct(self):
        self.state.return_value = {**STATE, 'control': {'controller': 'human', 'pending': True}}
        self.assertIn('uncertain_outcome', self.codes(viewer_diagnostics.diagnose(self.config, access_dir=self.directory)))
        self.state.return_value = {**STATE, 'control': {'controller': 'human', 'pending': False, 'input_active': True}}
        report = viewer_diagnostics.diagnose(self.config, access_dir=self.directory)
        self.assertTrue(report['ok']); self.assertIn('human_input_active', self.codes(report))
    def test_frames_and_lifecycle_skip_vnc(self):
        for key, value in (('viewer_mode', 'frames'), ('operation', 'restart')):
            self.state.return_value = {**STATE, key: value}
            self.assertTrue(viewer_diagnostics.diagnose(self.config, probe=True, access_dir=self.directory)['ok'])
        self.probe.assert_not_called()
    def test_missing_dependency_and_bad_state(self):
        self.dependency.side_effect = ModuleNotFoundError()
        self.assertIn('vnc_dependency_missing', self.codes(viewer_diagnostics.diagnose(self.config, probe=True, access_dir=self.directory)))
        self.probe.assert_not_called()
        self.state.return_value = {'private': TOKEN}
        report = viewer_diagnostics.diagnose(self.config, access_dir=self.directory)
        self.assertFalse(report['ok']); self.assertNotIn(TOKEN, json.dumps(report))
    def test_real_http_uses_header_no_proxy_and_refuses_redirects(self):
        seen = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                seen.append((self.path, self.headers.get('X-OwnMachine-Token')))
                if len(seen) == 1:
                    body = json.dumps(STATE).encode(); self.send_response(200)
                    self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
                else:
                    self.send_response(302); self.send_header('Location', 'http://example.invalid/'); self.end_headers()
        self.state_patch.stop()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch.dict(os.environ, {'http_proxy': 'http://example.invalid:1'}):
                self.assertEqual(viewer_diagnostics.read_state(server.server_port, TOKEN, 2), STATE)
                with self.assertRaises(viewer_diagnostics.AccessError):
                    viewer_diagnostics.read_state(server.server_port, TOKEN, 2)
            self.assertEqual(seen, [('/api/state', TOKEN), ('/api/state', TOKEN)])
        finally:
            server.shutdown(); server.server_close(); thread.join()
