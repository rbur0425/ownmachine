"""Spike regression: a new transport must never downgrade existing VNC auth."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'viewer'))
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
from stream import upstream_auth, StreamError
from ownmachine.config import Config

class WindowsConsoleTests(unittest.TestCase):
    def test_existing_profiles_refuse_unauthenticated_console(self):
        for profile in ('macos','omarchy','windows'):
            c=Config(host_alias='example',guest_profile=profile)
            with self.assertRaises(StreamError):
                upstream_auth({'transport':'private-unix','authentication':'none'},c,b'\x01')
            with self.assertRaises(StreamError):
                upstream_auth({'password':'abcdefgh'},c,b'\x01')
    def test_explicit_socket_requires_exact_attestation_and_server_offer(self):
        c=Config(host_alias='example',guest_profile='windows',console_transport='private-unix').validate()
        metadata={'transport':'private-unix','authentication':'none'}
        self.assertEqual(upstream_auth(metadata,c,b'\x01'),(1,None))
        for m,offered in (({},b'\x01'),({'password':'abcdefgh'},b'\x01'),(metadata,b'\x02'),(dict(metadata,password='extra'),b'\x01')):
            with self.assertRaises(StreamError):upstream_auth(m,c,offered)
    def test_lume_cannot_select_socket_mode(self):
        for profile in ('macos','omarchy'):
            with self.assertRaises(ValueError):Config(host_alias='example',guest_profile=profile,console_transport='private-unix').validate()
    def test_password_path_preserved(self):
        self.assertEqual(upstream_auth({'password':'abcdefgh'},Config(host_alias='example'),b'\x01\x02'),(2,'abcdefgh'))

class WindowsReadinessTests(unittest.TestCase):
    def test_readiness_requires_windows_session_evidence(self):
        import json
        import subprocess
        from unittest.mock import patch
        from ownmachine.workspace import status
        data=dict(guest_os='windows',guest_profile='windows',vm_state='running',
                  driver_ready=True,driver_state='ready',guest_reachable=True,
                  interactive_session=True,driver_running=True,standard_mode=True,standard_user=True)
        with patch('ownmachine.workspace.subprocess.run') as run:
            run.return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')
            result=status(Config(host_alias='example-host',guest_profile='windows'))
            self.assertTrue(result['driver_ready'])
            self.assertNotIn('screen_recording',result)
            self.assertEqual(status(Config(host_alias='example-host'))['code'],'guest_profile_mismatch')
            for key in ('guest_reachable','interactive_session','driver_running','standard_mode','standard_user'):
                run.return_value=subprocess.CompletedProcess([],0,json.dumps({**data,key:'true'}),'')
                self.assertFalse(status(Config(host_alias='example-host',guest_profile='windows'))['driver_ready'])
