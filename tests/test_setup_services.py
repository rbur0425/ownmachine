import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from setup_support import module, events
s = module('tested_setup_services', 'scripts/setup-services.py')
p = module('tested_ssh_pair', 'scripts/pair-ssh.py')


def public(n):
    return 'ssh-ed25519 ' + base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes([n])*32).decode()


class ServicesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        for mocked in (patch.object(Path, 'home', return_value=self.home),
                       patch.object(s.platform, 'system', return_value='Darwin'),
                       patch.object(s.platform, 'machine', return_value='arm64'),
                       patch.object(os, 'geteuid', return_value=1000)):
            mocked.start(); self.addCleanup(mocked.stop)
        self.config = self.home/'services.json'
        self.c = dict(vm_name='testvm', storage_dir=str(self.home/'storage'), lume_app=str(self.home/'Lume.app'),
                      guest_ssh_alias='test-guest', vnc_port=5555, python=sys.executable,
                      agent_public_key=str(self.home/'agent.pub'), viewer_public_key=str(self.home/'viewer.pub'),
                      agent_host_alias='test-agent', viewer_host_alias='test-viewer',
                      control_dir=str(self.home/'control'), access_dir=str(self.home/'access'),
                      viewer_python=sys.executable, viewer_port=0)
        Path(self.c['agent_public_key']).write_text(public(1))
        Path(self.c['viewer_public_key']).write_text(public(2))
        self.config.write_text(json.dumps(self.c))
        self.args = SimpleNamespace(config=self.config, step='relay', apply=False)

    def test_preview_never_connects_or_writes(self):
        before = set(self.home.rglob('*'))
        with patch.object(s, 'call', side_effect=AssertionError('network')):
            self.assertEqual(s.execute(self.args)['stage'], 'planned')
        self.assertEqual(set(self.home.rglob('*')), before)

    def test_relay_storage_preserved_and_resume_verifies(self):
        self.args.apply=True
        with patch.object(s, 'firewall'), patch.object(s.mac, 'verify_build'):
            self.assertEqual(s.execute(self.args)['stage'], 'verified')
            self.assertFalse(s.execute(self.args)['replayed'])
        installed=json.loads((self.home/'.config/ownmachine/host.json').read_text())
        self.assertEqual(installed['storage_dir'], self.c['storage_dir'])
        self.assertTrue(installed['enable_vnc'])
        (self.home/'.config/ownmachine/host.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'differs'):s.execute(self.args)

    def test_keys_preserve_other_entries_and_refuse_unrestricted_duplicate(self):
        directory=self.home/'.ssh';directory.mkdir(mode=0o700)
        path=directory/'authorized_keys';path.write_text(public(3)+' unrelated\n');path.chmod(0o600)
        s.install_keys(self.c);s.verify('keys',self.c)
        first=path.read_bytes();s.install_keys(self.c);self.assertEqual(path.read_bytes(),first)
        self.assertIn(public(3),path.read_text())
        path.write_text(public(1)+' unrestricted\n')
        with self.assertRaisesRegex(ValueError,'different_authorization'):s.install_keys(self.c)
        self.assertIn('unrestricted',path.read_text())

    def test_same_keys_and_symlink_refused(self):
        Path(self.c['viewer_public_key']).write_text(public(1))
        with self.assertRaises(ValueError):s.install_keys(self.c)
        path=self.home/'target';path.write_text('preserve')
        (self.home/'.ssh').mkdir(mode=0o700, exist_ok=True)
        (self.home/'.ssh/authorized_keys').symlink_to(path)
        Path(self.c['viewer_public_key']).write_text(public(2))
        with self.assertRaises(OSError):s.install_keys(self.c)
        self.assertEqual(path.read_text(),'preserve')

    def test_driver_transfers_only_reviewed_scripts_over_strict_ssh(self):
        with patch.object(s,'guest_address',return_value='192.0.2.40'),patch.object(s,'call') as call:
            s.install_driver(self.c)
        argv=call.call_args.args[0]
        self.assertIn('StrictHostKeyChecking=yes',argv)
        self.assertIn('HostName=192.0.2.40',argv)
        self.assertNotIn('sudo',argv[-1])
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(call.call_args.kwargs['data'])) as tar:
            self.assertEqual(set(tar.getnames()),{'install-guest-driver.sh','install-permission-guide.sh','install-guest-mcp.sh'})

    def test_permissions_are_checked_not_automatically_granted(self):
        with patch.object(s,'guest_address',return_value='192.0.2.40'),patch.object(s.relay,'guest_status',return_value={'driver_ready':False}):
            with self.assertRaisesRegex(ValueError,'consent_required'):s.verify('permissions',self.c)
        with patch.object(s,'guest_address',return_value='192.0.2.40'),patch.object(s.relay,'guest_status',return_value={'driver_ready':True}):
            s.verify('permissions',self.c)

    def test_viewer_plist_is_portable_and_private_access_separate(self):
        import plistlib
        path,content=s.viewer_files(self.c)
        data=plistlib.loads(content)
        self.assertEqual(data['Umask'],0o077)
        self.assertIn(self.c['access_dir'],data['ProgramArguments'])
        self.assertIn(self.c['viewer_host_alias'],data['ProgramArguments'])
        with self.assertRaisesRegex(ValueError,'separate'):
            s.viewer_files(dict(self.c,access_dir=self.c['control_dir']))

    def test_failed_mutation_is_not_replayed(self):
        self.args.apply=True
        with patch.object(s,'apply',side_effect=ValueError('fixture_failure')):
            with self.assertRaises(ValueError):s.execute(self.args)
        with patch.object(s,'apply',side_effect=AssertionError('replay')):
            with self.assertRaisesRegex(ValueError,'inspection'):s.execute(self.args)

    def test_event_output_never_contains_config_or_log_data(self):
        from contextlib import redirect_stdout
        out=io.StringIO()
        with redirect_stdout(out),events(True,'firewall'):pass
        rows=[json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([r['event'] for r in rows],['started','finished'])
        self.assertEqual(set(rows[0]),{'format','event','step','elapsed_seconds'})

    def test_pairing_uses_confirmed_host_key_and_actual_openssh(self):
        hostkey=self.home/'host.pub';hostkey.write_text(public(4))
        fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(public(4).split()[1])).digest()).decode().rstrip('=')
        args=SimpleNamespace(alias='test-host',user='example',host='mac.example.invalid',port=2222,
                             host_key=hostkey,confirm_fingerprint=fingerprint,role='agent',apply=False)
        self.assertEqual(p.prepare(args)['stage'],'planned')
        self.assertFalse((self.home/'.ssh').exists())
        args.confirm_fingerprint='SHA256:wrong'
        with self.assertRaisesRegex(ValueError,'mismatch'):p.prepare(args)
        args.confirm_fingerprint=fingerprint;args.apply=True
        self.assertEqual(p.prepare(args)['stage'],'paired')
        identity=self.home/'.ssh/ownmachine-agent-test-host/id_ed25519'
        self.assertEqual(identity.stat().st_mode&0o777,0o600)
        self.assertEqual(p.prepare(args)['stage'],'paired')
        contents=(self.home/'.ssh/config').read_text()
        self.assertEqual(contents.count('Include '),1)
        self.assertNotIn('PRIVATE KEY',json.dumps(p.prepare(args)))

    def test_linux_service_installs_user_unit_and_waits_for_readiness(self):
        with patch.object(s.platform,'system',return_value='Linux'),patch.object(s,'call') as call,patch.object(s,'viewer_check') as check:
            s.apply('viewer',self.c)
            unit=self.home/'.config/systemd/user/ownmachine-viewer.service'
            self.assertIn('NoNewPrivileges=yes',unit.read_text())
            self.assertIn(self.c['access_dir'],unit.read_text())
            self.assertEqual(unit.stat().st_mode&0o777,0o600)
            self.assertEqual([c.args[0] for c in call.call_args_list],
                             [['systemctl','--user','daemon-reload'],['systemctl','--user','enable','--now','ownmachine-viewer.service']])
            check.assert_called_once()

    def test_final_check_exercises_both_wrong_role_denials(self):
        good=subprocess.CompletedProcess([],0,json.dumps({'vm_state':'running','driver_ready':True}).encode())
        denied=subprocess.CompletedProcess([],2,json.dumps({'code':'unsupported_operation'}).encode())
        with patch.object(s,'call',return_value=good),patch.object(s.subprocess,'run',return_value=denied) as run,patch.object(s,'viewer_check') as viewer:
            s.verify('verify',self.c)
            self.assertEqual(run.call_args_list[1].args[0][-3:],[ 'vnc','--vm','testvm'])
            self.assertEqual(run.call_args_list[3].args[0][-3:],[ 'mcp','--vm','testvm'])
            viewer.assert_called_once_with(self.c,probe=True)
        with patch.object(s,'call',return_value=good),patch.object(s.subprocess,'run',return_value=good),patch.object(s,'viewer_check'):
            with self.assertRaisesRegex(ValueError,'not_restricted'):s.verify('verify',self.c)
