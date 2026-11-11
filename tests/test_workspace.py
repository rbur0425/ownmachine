from pathlib import Path
import json
import subprocess
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine.config import Config
from ownmachine.workspace import status


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(host_alias='ownmachine-studio')

    @patch('ownmachine.workspace.subprocess.run')
    def test_allowlist_removes_remote_secrets(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({
            'vm_state': 'vnc://secret@private-host', 'password': 'secret',
            'lume_installed': False}), '')
        result = status(self.config)
        self.assertEqual(result['vm_state'], 'unknown')
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs['timeout'], 50)

    @patch('ownmachine.workspace.subprocess.run')
    def test_ssh_errors_are_not_exposed(self, run):
        run.return_value = subprocess.CompletedProcess([], 255, '', 'secret diagnostics')
        self.assertEqual(status(self.config), {'host_reachable': False, 'code': 'ssh_connection_failed'})

    @patch('ownmachine.workspace.subprocess.run')
    def test_timeout_never_retries(self, run):
        run.side_effect = subprocess.TimeoutExpired('ssh', 20)
        self.assertEqual(status(self.config)['code'], 'host_unreachable')
        self.assertEqual(run.call_count, 1)

    @patch('ownmachine.workspace.subprocess.run')
    def test_invalid_response(self, run):
        for payload in ['null', '[]', 'broken']:
            run.return_value = subprocess.CompletedProcess([], 0, payload, '')
            self.assertEqual(status(self.config)['code'], 'invalid_host_response')

    @patch('ownmachine.workspace.subprocess.run')
    def test_readiness_requires_consistent_evidence(self, run):
        data = dict(vm_state='running', driver_ready=True, driver_state='ready',
                    guest_reachable=True, accessibility=True, screen_recording=True,
                    capture_consent_verified=True, secret='do not expose')
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps(data), '')
        self.assertTrue(status(self.config)['driver_ready'])
        self.assertNotIn('secret', json.dumps(status(self.config)))
        for flag in ('guest_reachable', 'accessibility', 'screen_recording', 'capture_consent_verified'):
            run.return_value = subprocess.CompletedProcess([], 0, json.dumps(dict(data, **{flag: 'true'})), '')
            self.assertFalse(status(self.config)['driver_ready'])
            self.assertEqual(status(self.config)['driver_state'], 'invalid_response')
