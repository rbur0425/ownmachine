import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('host_relay', Path(__file__).parents[1] / 'host/ownmachine_host.py')
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        p = patch.object(relay.Path, 'home', return_value=self.home)
        p.start()
        self.addCleanup(p.stop)

    def configure(self, data):
        path = self.home / '.config/ownmachine/host.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_default_configuration_is_account_independent(self):
        self.assertEqual(relay.configuration(), ('ownmachine', None, None))
        binary = self.home / '.local/bin/lume'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\n')
        binary.chmod(0o700)
        self.assertTrue(relay.status()['lume_installed'])

    def test_custom_vm_and_binary(self):
        binary = self.home / 'custom-lume'
        binary.write_text('#!/bin/sh\n')
        binary.chmod(0o700)
        self.configure({'vm_name': 'workstation', 'lume_path': str(binary)})
        name, path, guest = relay.configuration()
        self.assertTrue(relay.status(name, path)['lume_installed'])
        self.assertEqual(relay.status(name, path)['vm'], 'workstation')

    def test_invalid_config(self):
        for data in [[], {'vm_name': 'x;id'}, {'lume_path': 'relative'}, {'unknown': True},
                     {'guest_ssh_alias': '-oProxyCommand=id'}, {'guest_ssh_alias': 'host;id'}, {'enable_vnc':'yes'}, {'vnc_port':True}, {'vnc_port':65536}]:
            self.configure(data)
            with self.assertRaises(ValueError): relay.configuration()

    def test_forced_command_matches_only_configured_vm(self):
        self.configure({'vm_name': 'workstation'})
        for command, expected in [('ownmachine-host status --vm workstation', 0),
                                  ('ownmachine-host status --vm ownmachine', 2), ('uname -a', 2)]:
            with patch.dict(relay.os.environ, SSH_ORIGINAL_COMMAND=command), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(relay.main(), expected)

    def test_errors_do_not_disclose_paths(self):
        self.configure({'lume_path': 'invalid'})
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(relay.main(), 2)
        self.assertEqual(json.loads(out.getvalue()), {'code': 'invalid_host_configuration'})


class LiveStateParsingTests(unittest.TestCase):
    @patch.object(relay.subprocess, 'run')
    @patch.object(relay.os, 'access', return_value=True)
    @patch.object(relay.Path, 'is_file', return_value=True)
    def test_only_configured_vm_state_is_returned(self, is_file, access, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps([
            {'name': 'other', 'status': 'running', 'vncUrl': 'secret'},
            {'name': 'ownmachine', 'status': 'stopped', 'vncUrl': 'secret'}]))
        result = relay.status()
        self.assertEqual(result['vm_state'], 'stopped')
        self.assertNotIn('secret', json.dumps(result))
        run.return_value = subprocess.CompletedProcess([], 0, '[]')
        self.assertEqual(relay.status()['vm_state'], 'absent')
        run.return_value = subprocess.CompletedProcess([], 0, '{}')
        self.assertEqual(relay.status()['vm_state'], 'unknown')

class GuestProbeTests(unittest.TestCase):
    def payload(self, **changes):
        return dict({'accessibility': True, 'screen_recording': True,
                     'daemon_running': True, 'source': {'bundle_id': 'com.trycua.driver'},
                     'direct_capture_verification': {'bundle_id': 'com.trycua.driver',
                         'source': 'permissions_grant', 'verified_at': '2026-11-10T12:00:00Z'}}, **changes)

    def probe(self, data):
        with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 0, json.dumps(data), 'private diagnostic')) as run:
            result = relay.guest_status('guest-alias', '192.0.2.20')
            return result, run

    def test_success_uses_fixed_key_only_command(self):
        result, run = self.probe(self.payload(secret='private diagnostic'))
        self.assertTrue(result['driver_ready'])
        self.assertNotIn('private', json.dumps(result))
        argv = run.call_args.args[0]
        self.assertIn('StrictHostKeyChecking=yes', argv)
        self.assertIn('HostName=192.0.2.20', argv)
        self.assertEqual(argv[-2], 'guest-alias')
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs['timeout'], 8)

    def test_missing_grants_capture_consent_and_stopped_daemon(self):
        for changes, expected in [({'accessibility': False}, 'permissions_required'),
                ({'screen_recording': False}, 'permissions_required'),
                ({'direct_capture_verification': None}, 'capture_consent_required'),
                ({'daemon_running': False}, 'not_running')]:
            with self.subTest(expected=expected):
                result, _ = self.probe(self.payload(**changes))
                self.assertEqual(result['driver_state'], expected)
                self.assertFalse(result['driver_ready'])

    def test_untrusted_or_malformed_responses_fail_closed(self):
        for data in [None, [], self.payload(accessibility='true'),
                     self.payload(source={'bundle_id': 'other.app'})]:
            result, _ = self.probe(data)
            self.assertEqual(result['driver_state'], 'invalid_response')
            self.assertFalse(result['driver_ready'])

    @patch.object(relay.subprocess, 'run')
    def test_timeout_and_invalid_addresses_never_retry(self, run):
        run.side_effect = subprocess.TimeoutExpired('ssh', 8)
        self.assertFalse(relay.guest_status('guest', '192.0.2.20')['driver_ready'])
        self.assertEqual(run.call_count, 1)
        run.reset_mock()
        for address in [None, 123, 'x;id', '127.0.0.1', '::1', '0.0.0.0']:
            self.assertFalse(relay.guest_status('guest', address)['driver_ready'])
        run.assert_not_called()

    @patch.object(relay, 'guest_status')
    @patch.object(relay.subprocess, 'run')
    @patch.object(relay.os, 'access', return_value=True)
    @patch.object(relay.Path, 'is_file', return_value=True)
    def test_stopped_vm_never_contacts_guest(self, is_file, access, run, probe):
        run.return_value = subprocess.CompletedProcess([], 0, '[{"name":"ownmachine","status":"stopped"}]')
        self.assertEqual(relay.status(guest_alias='guest')['driver_state'], 'vm_not_running')
        probe.assert_not_called()


class MCPRelayTests(unittest.TestCase):
    def test_mcp_requires_explicit_host_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);config=home/'.config/ownmachine/host.json'
            config.parent.mkdir(parents=True);config.write_text('{}')
            with patch.object(relay.Path,'home',return_value=home), patch.object(relay.os,'execvp') as execute:
                with self.assertRaises(ValueError): relay.mcp('ownmachine',None,'guest')
                execute.assert_not_called()

class HostLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        p=patch.object(relay.Path,'home',return_value=self.home);p.start();self.addCleanup(p.stop)
        config=self.home/'.config/ownmachine/host.json';config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'enable_lifecycle':True,'display_mode':'none'}))
        self.binary=self.home/'lume';self.binary.write_text('');self.binary.chmod(0o700)
    def listing(self,state):
        return subprocess.CompletedProcess([],0,json.dumps([{'name':'ownmachine','status':state,'ipAddress':'192.0.2.20'}]))
    @patch.object(relay.subprocess,'run')
    def test_start_running_is_idempotent(self,run):
        run.return_value=self.listing('running')
        self.assertEqual(relay.lifecycle('start','ownmachine',str(self.binary),'guest')['vm_state'],'running')
        self.assertEqual(run.call_count,1)
    @patch.object(relay.subprocess,'run')
    def test_stop_uses_guest_shutdown_without_force_fallback(self,run):
        run.side_effect=[self.listing('running'),subprocess.CompletedProcess([],255),self.listing('stopped')]
        self.assertEqual(relay.lifecycle('stop','ownmachine',str(self.binary),'guest')['vm_state'],'stopped')
        commands=[c.args[0] for c in run.call_args_list]
        self.assertIn('vm-shutdown.sh',commands[1][-1])
        self.assertTrue(all('--force' not in c and 'stop' not in c for c in commands))
    @patch.object(relay.subprocess,'run')
    def test_absent_vm_is_never_created(self,run):
        run.return_value=subprocess.CompletedProcess([],0,'[]')
        with self.assertRaises(ValueError):relay.lifecycle('start','ownmachine',str(self.binary),'guest')
        self.assertEqual(run.call_count,1)
    @patch.object(relay.subprocess,'run')
    def test_shutdown_refusal_never_powers_off(self,run):
        run.side_effect=[self.listing('running'),subprocess.CompletedProcess([],1)]
        with self.assertRaises(ValueError):relay.lifecycle('restart','ownmachine',str(self.binary),'guest')
        self.assertEqual(run.call_count,2)

    @patch.object(relay.time,'monotonic',side_effect=[0,46])
    @patch.object(relay.subprocess,'run')
    def test_shutdown_timeout_never_uses_force(self,run,clock):
        run.side_effect=[self.listing('running'),subprocess.CompletedProcess([],0)]
        with self.assertRaisesRegex(ValueError,'guest_shutdown_timeout'):
            relay.lifecycle('restart','ownmachine',str(self.binary),'guest')
        self.assertEqual(run.call_count,2)

class VNCRelayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.config=self.home/'.config/ownmachine/host.json';self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({'enable_vnc':True}))
        self.binary=self.home/'lume';self.binary.write_text('');self.binary.chmod(0o700)
        self.patch=patch.object(relay.Path,'home',return_value=self.home);self.patch.start();self.addCleanup(self.patch.stop)
    def test_vnc_is_explicit_opt_in(self):
        self.config.write_text('{}')
        with self.assertRaisesRegex(ValueError,'vnc_not_enabled'):relay.vnc('ownmachine',str(self.binary))
    def test_nonloopback_unconfigured_stopped_and_missing_vnc_refused(self):
        for vm in ({'name':'other','status':'running','vncUrl':'vnc://:secret@127.0.0.1:5555'},
                   {'name':'ownmachine','status':'stopped','vncUrl':'vnc://:secret@127.0.0.1:5555'},
                   {'name':'ownmachine','status':'running','vncUrl':'vnc://:secret@192.0.2.1:5555'},
                   {'name':'ownmachine','status':'running','vncUrl':None}):
            with patch.object(relay.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps([vm]))),patch.object(relay.socket,'create_connection') as connect:
                with self.assertRaises(ValueError):relay.vnc('ownmachine',str(self.binary))
                connect.assert_not_called()

class SecurityBoundaryTests(unittest.TestCase):
    setUp = HostTests.setUp
    configure = HostTests.configure
    def test_vnc_requires_fixed_unprivileged_port(self):
        for port in (None, 0, 1, 1023, 65536, True, '57279'):
            self.configure({'enable_vnc':True,'vnc_port':port})
            with self.assertRaises(ValueError):relay.configuration()
        for port in (1024,65535):
            self.configure({'enable_vnc':True,'vnc_port':port})
            relay.configuration()

    def test_roles_cannot_cross_boundary(self):
        self.configure({})
        with patch.object(relay,'vnc') as vnc, patch.object(relay,'lifecycle') as lifecycle, patch.object(relay,'mcp') as mcp:
            for role, operations in [('agent',('vnc','start','stop','restart')),('viewer',('mcp',))]:
                for op in operations:
                    with patch.dict(relay.os.environ,SSH_ORIGINAL_COMMAND=f'ownmachine-host {op} --vm ownmachine'),contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(relay.main(role),2)
            vnc.assert_not_called();lifecycle.assert_not_called();mcp.assert_not_called()
            for role,op in [('agent','mcp'),('viewer','vnc')]:
                with patch.dict(relay.os.environ,SSH_ORIGINAL_COMMAND=f'ownmachine-host {op} --vm ownmachine'),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(relay.main(role),0)
            vnc.assert_called_once();mcp.assert_called_once()

    def test_password_is_url_safe_and_private(self):
        state=relay.private_directory(self.home/'state')
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        with patch.object(relay.secrets,'choice',side_effect=list('Az09-._~')) as choose:
            password=relay.vnc_password(state)
        self.assertEqual(password,'Az09-._~')
        self.assertTrue(all(call.args==(alphabet,) for call in choose.call_args_list))
        self.assertEqual((state/'vnc-password').read_text(),password)
        self.assertEqual((state/'vnc-password').stat().st_mode&0o777,0o600)
        self.assertEqual(state.stat().st_mode&0o777,0o700)
        target=self.home/'untouched';target.write_text('untouched')
        (state/'vnc-password').unlink();(state/'vnc-password').symlink_to(target)
        with self.assertRaises(OSError):relay.vnc_password(state)
        self.assertEqual(target.read_text(),'untouched')

    def test_every_password_character_survives_upstream_url_round_trip(self):
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        self.assertEqual(len(set(alphabet)),66)
        state=relay.private_directory(self.home/'state')
        for char in alphabet:
            with patch.object(relay.secrets,'choice',return_value=char):
                password=relay.vnc_password(state)
            url=relay.urlsplit(f'vnc://:{password}@127.0.0.1:5555')
            self.assertEqual(relay.unquote(url.password),password)
            self.assertEqual(url.hostname,'127.0.0.1')
            self.assertEqual(url.port,5555)

    def test_firewall_status_missing_stale_wrong_port_and_unsafe_refused(self):
        import stat
        from types import SimpleNamespace
        marker=self.home/'firewall-status.json'
        good=dict(st_mode=stat.S_IFREG|0o644,st_uid=0,st_size=100,st_mtime=100)
        directory=SimpleNamespace(st_mode=stat.S_IFDIR|0o755,st_uid=0)
        data={'port':5555,'pf_enabled':True,'rule_loaded':True,'application_blocked':True}
        with patch.object(relay,'FIREWALL_STATUS',marker),patch.object(relay.Path,'lstat',return_value=directory),patch.object(relay.time,'time',return_value=110):
            with self.assertRaises(OSError):relay.firewall_ready(5555)
            marker.write_text(json.dumps(data))
            with patch.object(relay.os,'fstat',return_value=SimpleNamespace(**good)):
                relay.firewall_ready(5555)
                with self.assertRaises(ValueError):relay.firewall_ready(5556)
                for key in ('pf_enabled','rule_loaded','application_blocked'):
                    marker.write_text(json.dumps({**data,key:False}))
                    with self.assertRaises(ValueError):relay.firewall_ready(5555)
            marker.write_text(json.dumps(data))
            for changes in ({'st_uid':501},{'st_mode':stat.S_IFREG|0o666},{'st_mtime':0},{'st_mtime':120}):
                with patch.object(relay.os,'fstat',return_value=SimpleNamespace(**{**good,**changes})):
                    with self.assertRaises(ValueError):relay.firewall_ready(5555)
            marker.unlink();marker.symlink_to(self.home/'target')
            with self.assertRaises(OSError):relay.firewall_ready(5555)

    def test_vnc_does_not_connect_without_matching_managed_port_password_and_firewall(self):
        binary=self.home/'lume';binary.touch();binary.chmod(0o700)
        self.configure({'enable_vnc':True,'vnc_port':5555})
        state=relay.private_directory(self.home/'.local/state/ownmachine')
        relay.private_file(state/'vnc-password','Strong8_')
        def listing(port=5555,password='Strong8_'):
            return subprocess.CompletedProcess([],0,json.dumps([{'name':'ownmachine','status':'running','vncUrl':f'vnc://:{password}@127.0.0.1:{port}'}]))
        with patch.object(relay.socket,'create_connection') as connect,patch.object(relay,'firewall_ready',side_effect=ValueError('not_ready')):
            with self.assertRaises(ValueError):relay.vnc('ownmachine',str(binary))
            connect.assert_not_called()
        for result in (listing(5556),listing(password='weak'),listing(password='Other8__')):
            with patch.object(relay,'firewall_ready'),patch.object(relay.subprocess,'run',return_value=result),patch.object(relay.socket,'create_connection') as connect:
                with self.assertRaises(ValueError):relay.vnc('ownmachine',str(binary))
                connect.assert_not_called()
        with patch.object(relay,'firewall_ready'),patch.object(relay.subprocess,'run',return_value=listing()),patch.object(relay.socket,'create_connection',side_effect=RuntimeError('reached_socket')) as connect:
            with self.assertRaisesRegex(RuntimeError,'reached_socket'):relay.vnc('ownmachine',str(binary))
            connect.assert_called_once_with(('127.0.0.1',5555),timeout=10)

class HardenedLaunchTests(unittest.TestCase):
    setUp = HostLifecycleTests.setUp
    listing = HostLifecycleTests.listing
    def test_start_uses_private_log_and_explicit_password_after_firewall(self):
        config=self.home/'.config/ownmachine/host.json'
        config.write_text(json.dumps({'enable_lifecycle':True,'enable_vnc':True,'vnc_port':5555}))
        with patch.object(relay,'firewall_ready') as firewall,patch.object(relay.subprocess,'run') as run:
            run.side_effect=[self.listing('stopped'),subprocess.CompletedProcess([],0),self.listing('running')]
            relay.lifecycle('start','ownmachine',str(self.binary),'guest')
        firewall.assert_called_once_with(5555)
        command=run.call_args_list[1].args[0]
        self.assertNotIn('--vnc-password',command)
        state=self.home/'.local/state/ownmachine'
        self.assertEqual(command[command.index('--vnc-password-file')+1],str(state/'vnc-password'))
        password=(state/'vnc-password').read_text()
        self.assertEqual(len(password),8)
        self.assertNotIn(password,' '.join(command))
        self.assertEqual(command[command.index('--log-file')+1],str(state/'lume-detached.log'))
        self.assertEqual((state/'lume-detached.log').stat().st_mode&0o777,0o600)
        self.assertEqual((self.home/'.lume').stat().st_mode&0o777,0o700)
    def test_missing_firewall_refuses_start_before_launch(self):
        config=self.home/'.config/ownmachine/host.json'
        config.write_text(json.dumps({'enable_lifecycle':True,'enable_vnc':True,'vnc_port':5555}))
        with patch.object(relay,'firewall_ready',side_effect=ValueError('not_ready')),patch.object(relay.subprocess,'run',return_value=self.listing('stopped')) as run:
            with self.assertRaises(ValueError):relay.lifecycle('start','ownmachine',str(self.binary),'guest')
            self.assertEqual(run.call_count,1)
