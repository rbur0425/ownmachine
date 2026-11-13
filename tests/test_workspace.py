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
    @patch('ownmachine.workspace.subprocess.run')
    def test_linux_reports_linux_gates_and_rejects_profile_mismatch(self, run):
        data=dict(guest_os='linux',guest_profile='omarchy',vm_state='running',
                  driver_ready=True,driver_state='ready',guest_reachable=True,
                  graphical_session=True,accessibility_bus=True,driver_running=True,standard_mode=True)
        run.return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')
        result=status(Config(host_alias='example-mac',guest_profile='omarchy'))
        self.assertTrue(result['driver_ready'])
        for name in ('accessibility','screen_recording','capture_consent_verified'):
            self.assertNotIn(name,result)
        self.assertEqual(status(Config(host_alias='example-mac'))['code'],'guest_profile_mismatch')

    @patch('ownmachine.workspace.subprocess.run')
    def test_nonrunning_linux_guest_preserves_reachable_host_and_vm_state(self, run):
        for state in ('absent', 'stopped', 'provisioning', 'lume_not_installed', 'not_probed'):
            with self.subTest(state=state):
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps({
                    'vm_state': state, 'lume_installed': True, 'driver_state': 'vm_not_running'}), '')
                result = status(Config(host_alias='example-mac', guest_profile='omarchy'))
                self.assertTrue(result['host_reachable'])
                self.assertEqual(result['vm_state'], state)
                self.assertFalse(result['driver_ready'])
                self.assertNotIn('code', result)

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
