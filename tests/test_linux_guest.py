import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

guest = load('linux_guest_tested', 'scripts/linux-guest.py')
relay = load('linux_host_tested', 'host/ownmachine_host.py')

class LinuxGuestTests(unittest.TestCase):
    def test_readiness_never_fakes_macos_consent(self):
        with patch.object(guest, 'settings', return_value={'binary':'/driver'}), \
             patch.object(guest, 'session_environment', return_value={}), \
             patch.object(guest, 'call', return_value=subprocess.CompletedProcess([],0,'permission mode: standard (trusted_startup_configuration)')):
            result = guest.readiness()
        self.assertTrue(result['driver_ready'])
        self.assertNotIn('screen_recording', result)
        self.assertNotIn('capture_consent_verified', result)

    def test_wrong_authorization_mode_refuses_readiness(self):
        with patch.object(guest, 'settings', return_value={'binary':'/driver'}), \
             patch.object(guest, 'session_environment', return_value={}), \
             patch.object(guest, 'call', return_value=subprocess.CompletedProcess([],0,'permission mode: unrestricted (test)')):
            self.assertFalse(guest.readiness()['driver_ready'])

    def test_missing_graphical_session_fails_closed(self):
        with patch.object(guest, 'call', return_value=subprocess.CompletedProcess([],0,'PATH=/tmp\n')):
            with self.assertRaisesRegex(ValueError, 'graphical_session_required'):
                guest.session_environment()

    def test_shell_quoted_environment_is_not_evaluated(self):
        with patch.object(guest, 'call', return_value=subprocess.CompletedProcess([],0,"DISPLAY=$'bad'\n")):
            with self.assertRaisesRegex(ValueError, 'invalid_session_environment'):
                guest.session_environment()

    def test_settings_and_install_refuse_existing_symlinks(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(guest.Path, 'home', return_value=Path(directory).resolve()):
            root=Path(directory);config=root/'.config/ownmachine';config.mkdir(parents=True)
            target=root/'keep';target.write_text('unchanged')
            (config/'linux-driver.json').symlink_to(target)
            with self.assertRaises(OSError):guest.settings()
            with self.assertRaisesRegex(ValueError,'existing_installation'):
                guest.install(guest.VERSION,guest.SHA256)
            self.assertEqual(target.read_text(),'unchanged')

    def test_checksum_mismatch_does_not_publish_installation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(guest.Path, 'home', return_value=Path(directory).resolve()):
            archive=Path(directory)/'bad.tar.gz';archive.write_bytes(b'not a driver')
            with self.assertRaisesRegex(ValueError,'checksum_mismatch'):
                guest.install(guest.VERSION,guest.SHA256,archive)
            self.assertFalse((Path(directory)/'.config/ownmachine/linux-driver.json').exists())

    def test_linux_probe_strict_booleans_and_standard_mode(self):
        data=dict(schema_version=1,guest_os='linux',guest_profile='omarchy',graphical_session=True,
                  accessibility_bus=True,driver_running=True,standard_mode=True,driver_ready=True)
        for key,value,expected in [('standard_mode',True,True),('standard_mode',False,False),('driver_ready','true',False)]:
            response={**data,key:value}
            with patch.object(relay.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(response))) as command:
                result=relay.guest_status('guest-alias','192.0.2.15','linux')
            self.assertEqual(result['driver_ready'],expected)
            self.assertIn('linux-guest.py',command.call_args.args[0][-1])
            self.assertFalse(result['screen_recording'])

    def test_unknown_guest_profile_is_rejected(self):
        for data in [{'guest_os':'windows'},{'guest_os':'linux','guest_profile':'ubuntu'}, {'guest_os':'macos','guest_profile':'omarchy'}]:
            with self.assertRaises(ValueError):relay.guest_profile(data)
        self.assertEqual(relay.guest_profile({}),('macos','macos'))

hardener = load('linux_hardening_tested', 'scripts/secure-linux-guest.py')

class LinuxIsolationTests(unittest.TestCase):
    def test_every_new_support_parent_gets_desktop_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory).resolve()
            with patch.object(hardener.os,'chown') as ownership:
                hardener.user_support(home,os.getuid(),os.getgid())
            self.assertEqual([c.args[0] for c in ownership.call_args_list],
                             [home/'.local',home/'.local/lib',home/'.local/lib/ownmachine'])
            ownership.reset_mock()
            with patch.object(hardener.os,'chown') as unchanged:
                hardener.user_support(home,os.getuid(),os.getgid())
            unchanged.assert_not_called()

    def test_hardener_preserves_required_mode_under_private_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory).resolve()/'sudo-rule'
            previous=os.umask(0o077)
            try:hardener.install_file(path,'fixture\n',0o440)
            finally:os.umask(previous)
            self.assertEqual(path.stat().st_mode & 0o777,0o440)

    def test_guest_firewall_does_not_flush_other_tables(self):
        rules = hardener.firewall_rules('192.0.2.7')
        self.assertNotIn('flush ruleset', rules)
        self.assertIn('ip saddr 192.0.2.7 tcp dport 22 accept', rules)
        self.assertIn('policy drop', rules)
        self.assertIn('ip6 saddr 2001:db8::7', hardener.firewall_rules('2001:db8::7'))
        for address in ['127.0.0.1','0.0.0.0','224.0.0.1','::1','not-an-address']:
            with self.assertRaises(ValueError):hardener.firewall_rules(address)

    def test_explicit_relays_have_distinct_password_and_lock_storage(self):
        with patch.object(relay, 'CONFIG_PATH', None):
            default=relay.runtime_state()
        with patch.object(relay, 'CONFIG_PATH', Path('/operator/first.json')):
            first=relay.runtime_state()
        with patch.object(relay, 'CONFIG_PATH', Path('/operator/second.json')):
            second=relay.runtime_state()
        self.assertEqual(len({default,first,second}),3)
        self.assertEqual(first.parent,default/'relays')

    def test_hardener_refuses_symlink_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); target=root/'preserve';target.write_text('unchanged')
            link=root/'link';link.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'symlink_destination'):
                hardener.install_file(link,'replace')
            self.assertEqual(target.read_text(),'unchanged')

provision = load('linux_provision_tested', 'scripts/provision-linux-vm.py')

class LinuxProvisionTests(unittest.TestCase):
    def arguments(self,root):
        import argparse
        return argparse.Namespace(profile='omarchy',step='create',vm_name='test-vm',app=root/'app',
            storage_dir=root/'vms',state_dir=root/'state',iso=root/'installer.iso',iso_sha256='a'*64,
            cpu=4,memory_gb=8,disk_gb=64,min_free_gb=32,display='1900x1200',apply=False)

    def test_preview_does_not_build_or_create(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.arguments(Path(directory).resolve())
            with patch.object(provision.support,'run',side_effect=AssertionError('mutation')):
                result=provision.execute(args)
            self.assertEqual(result['vnc'],'disabled')
            self.assertFalse(args.state_dir.exists())

    def test_changed_checksum_and_existing_guest_fail_closed(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            args=self.arguments(Path(directory).resolve());args.apply=True;args.iso.write_bytes(b'iso')
            with patch.object(provision.platform,'system',return_value='Darwin'), patch.object(provision.platform,'machine',return_value='arm64'), patch.object(provision.os,'geteuid',return_value=501), patch.object(provision.support,'verify_build'), patch.object(provision,'listing',return_value={'name':args.vm_name}):
                with self.assertRaisesRegex(ValueError,'iso_checksum_mismatch'):provision.execute(args)
                args.iso_sha256=hashlib.sha256(b'iso').hexdigest()
                with self.assertRaisesRegex(ValueError,'existing_vm_preserved'):provision.execute(args)
            self.assertFalse((args.state_dir/'linux-create.json').exists())

if __name__ == '__main__':unittest.main()
