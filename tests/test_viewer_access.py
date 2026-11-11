import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ownmachine-viewer-access.py'
TOKEN = 'private_test_token_' + 'x' * 32


class ViewerAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.requests = []
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append((self.path, self.headers.get('X-OwnMachine-Token')))
                self.send_response(owner.response_status)
                self.end_headers()
                self.wfile.write(owner.response_body)
            def log_message(self, *args):
                pass
        self.response_status = 200
        self.response_body = b'{"control":{"controller":"human"}}'
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.server.server_port
        thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.path = self.root / 'viewer-access.json'
        self.write_access()

    def write_access(self, **overrides):
        data = {'port': self.port, 'url': f'http://127.0.0.1:{self.port}/#{TOKEN}'}
        data.update(overrides)
        self.path.write_text(json.dumps(data))
        self.path.chmod(0o600)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--access-dir', str(self.root), *args],
                              capture_output=True, text=True, timeout=5,
                              env={**os.environ, 'HTTP_PROXY': 'http://127.0.0.1:1'})

    def test_default_authenticates_without_revealing_secret(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertEqual(self.requests, [('/api/state', TOKEN)])

    def test_url_remaps_only_local_port(self):
        result = self.run_cli('--show-url', '--local-port', '45678')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f'http://127.0.0.1:45678/#{TOKEN}')
        self.assertEqual(len(self.requests), 1)

    def test_token_explicit(self):
        result = self.run_cli('--show-token')
        self.assertEqual(result.stdout.strip(), TOKEN)
        self.assertEqual(result.returncode, 0)

    def test_tunnel_is_loopback_and_secret_free(self):
        result = self.run_cli('--ssh-target', 'operator@viewer.example', '--local-port', '45678')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'127.0.0.1:45678:127.0.0.1:{self.port}', result.stdout)
        self.assertIn('ExitOnForwardFailure=yes', result.stdout)
        self.assertNotIn(TOKEN, result.stdout)

    def test_stale_token_never_revealed(self):
        self.response_status = 403
        result = self.run_cli('--show-url')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

    def test_redirect_never_followed(self):
        self.response_status = 302
        result = self.run_cli('--show-url')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

    def test_unsafe_access_refused_without_network(self):
        for mode in (0o644, 0o666):
            self.path.chmod(mode)
            self.assertEqual(self.run_cli('--show-token').returncode, 1)
        self.path.unlink()
        target = self.root / 'target'
        target.write_text(TOKEN)
        self.path.symlink_to(target)
        self.assertEqual(self.run_cli('--show-token').returncode, 1)
        self.assertEqual(self.requests, [])

    def test_non_loopback_refused_without_network(self):
        self.write_access(url=f'http://viewer.example:{self.port}/#{TOKEN}')
        result = self.run_cli('--show-url')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertEqual(self.requests, [])

    def test_invalid_arguments_refused_without_network(self):
        for args in [('--local-port', '0'), ('--timeout-seconds', '121'),
                     ('--ssh-target=-oProxyCommand=bad',),
                     ('--ssh-target', 'host;echo bad'),
                     ('--show-url', '--show-token'),
                     ('--ssh-target', 'viewer.example', '--show-token')]:
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args).returncode, 2)
        self.assertEqual(self.requests, [])

    def test_invalid_response_does_not_echo_body(self):
        self.response_body = TOKEN.encode()
        result = self.run_cli('--show-token')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
