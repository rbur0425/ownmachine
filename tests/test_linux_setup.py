"""Linux onboarding rejects unsafe/replayed installation and preserves profile routing."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'plugin'))
from setup_support import module
installer=module('tested_linux_desktop','scripts/install-linux-desktop.py')
services=installer.services
endpoint=module('tested_linux_endpoint','scripts/setup-endpoint.py')

class LinuxSetupTests(unittest.TestCase):
    def test_first_run_units_install_with_arm_command_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();target=root/'units';commands=root/'bin';commands.mkdir()
            names=['bt-agent','omarchy-recover-internal-monitor','omarchy-sleep-lock',
                   'omarchy-migrate-notify','omarchy-fcitx5','omarchy-crash-watch']
            for name in names:
                executable='fcitx5' if name=='omarchy-fcitx5' else name
                (source/(name+'.service')).write_text('[Service]\nExecStart=/usr/bin/'+executable+'\n')
                if executable.startswith('omarchy-'):(commands/executable).touch()
            code=installer.user_units_script().split("<<'OWNMACHINE_UNITS'\n",1)[1].split('\nOWNMACHINE_UNITS',1)[0]
            code=code.replace('/usr/share/omarchy/default/systemd/user',str(source)).replace('/usr/lib/systemd/user',str(target)).replace('/usr/local/bin',str(commands))
            subprocess.run([sys.executable,'-c',code],check=True)
            self.assertIn('ExecStart='+str(commands/'omarchy-crash-watch'),(target/'omarchy-crash-watch.service').read_text())
            self.assertIn('ExecStart=/usr/bin/fcitx5',(target/'omarchy-fcitx5.service').read_text())
            self.assertEqual((target/'omarchy-crash-watch.service').stat().st_mode & 0o777,0o644)
            (source/'omarchy-sleep-lock.service').unlink()
            result=subprocess.run([sys.executable,'-c',code],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'pinned_user_units_missing',result.stderr)

    def test_hardening_verification_accepts_openssh_setting_case(self):
        import setup_linux
        from types import SimpleNamespace
        for policy in ('PasswordAuthentication no\nPermitRootLogin no', 'passwordauthentication no\npermitrootlogin no'):
            def root_check(service, config, script):
                for line in script.decode().splitlines():
                    if 'sshd -T' in line:
                        command=line.split('|',1)[1]
                        subprocess.run(command,shell=True,input=policy.encode(),check=True)
            service=SimpleNamespace(hardening_state=lambda c:Path('/unused'),guest_argv=lambda c:['ssh'],call=lambda argv:None)
            with patch.object(setup_linux,'private_read',return_value=b'{"schema_version":1,"hardened":true}'),patch.object(setup_linux,'root_call',side_effect=root_check):
                setup_linux.verify_hardening(service,{})

    def test_linux_resource_limits_do_not_lower_macos_limits(self):
        from ownmachine.onboarding import DEFAULTS,validate_plan,InputError
        plan=dict(DEFAULTS,target='remote',guest_profile='omarchy',min_free_gb=24,disk_gb=32)
        validate_plan(plan)
        with self.assertRaises(InputError):validate_plan(dict(plan,guest_profile='macos'))

    def test_macos_plan_cannot_select_linux_mutation(self):
        with self.assertRaisesRegex(ValueError,'requires_omarchy'):
            endpoint.command({}, {'guest_profile':'macos'}, 'linux-base', True)

    def test_linux_configuration_propagates_into_viewer_and_relay(self):
        import plistlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            c=dict(vm_name='fixture',guest_profile='omarchy',guest_ssh_alias='guest',
                   storage_dir=str(root/'vms'),lume_app=str(root/'Lume.app'),vnc_port=5555,
                   viewer_host_alias='viewer',control_dir=str(root/'control'),access_dir=str(root/'private'),
                   viewer_python=sys.executable,viewer_port=0)
            self.assertEqual(services.host_settings(c)['guest_os'],'linux')
            with patch.object(services.platform,'system',return_value='Darwin'):
                _,data=services.viewer_files(c)
            argv=plistlib.loads(data)['ProgramArguments']
            self.assertEqual(argv[argv.index('--guest-profile')+1],'omarchy')

    def test_keyring_failure_precedes_disk_stage_and_uses_bootstrap_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();state=root/'state';state.mkdir(mode=0o700)
            c=dict(vm_name='fixture',guest_profile='omarchy',guest_user='desktop',guest_ssh_alias='desktop-key',guest_bootstrap_ssh_alias='live-key',storage_dir=str(root/'vms'),lume_app=str(root/'Lume.app'))
            receipt=state/'provision.json';receipt.write_text(json.dumps(dict(phase='created',guest_os='linux',vm_name='fixture',storage_dir=c['storage_dir'])));receipt.chmod(0o600)
            with patch.object(services,'config',return_value=c),patch.object(services,'hardening_state',return_value=state),patch.object(installer.mac,'verify_build'),patch.object(installer.os,'geteuid',return_value=501),patch.object(services,'guest_argv',side_effect=lambda cfg:['ssh',cfg['guest_ssh_alias']]),patch.object(installer,'download',return_value='exit 99'),patch.object(services,'call',side_effect=[None,subprocess.CalledProcessError(1,[])]) as call:
                with self.assertRaises(subprocess.CalledProcessError):installer.execute(root/'config','base',True)
            self.assertEqual(call.call_args_list[1].args[0][1],'live-key')
            self.assertIn('pacman-init.service',call.call_args_list[1].args[0][-1])
            self.assertIn('test "$state" = exited',call.call_args_list[1].args[0][-1])
            self.assertFalse((state/'setup/linux-base.json').exists())

    def test_relay_install_path_is_operator_configurable(self):
        c=dict(vm_name='fixture',guest_profile='omarchy',guest_ssh_alias='guest',storage_dir='/private/guest-vms',lume_app='/private/Lume.app',vnc_port=5555,relay_path='/private/isolated/relay.py',relay_config='/private/isolated/host.json')
        files=services.desired_relay(c)
        self.assertEqual(files[0][0],Path(c['relay_path']))
        self.assertEqual(files[1][0],Path(c['relay_config']))

    def test_install_guard_failure_never_records_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();state=root/'state';state.mkdir(mode=0o700)
            c=dict(vm_name='fixture',guest_profile='omarchy',guest_user='desktop',storage_dir=str(root/'vms'),lume_app=str(root/'Lume.app'))
            receipt=state/'provision.json';receipt.write_text(json.dumps(dict(phase='created',guest_os='linux',vm_name='fixture',storage_dir=c['storage_dir'])));receipt.chmod(0o600)
            with patch.object(services,'config',return_value=c),patch.object(services,'hardening_state',return_value=state),patch.object(installer.mac,'verify_build'),patch.object(installer.os,'geteuid',return_value=501),patch.object(services,'guest_argv',return_value=['ssh','pinned-guest']),patch.object(installer,'download',return_value='exit 99'),patch.object(services,'call',side_effect=subprocess.CalledProcessError(1,[])):
                with self.assertRaises(subprocess.CalledProcessError):installer.execute(root/'config','base',True)
            self.assertFalse((state/'setup/linux-base.json').exists())

    def test_uncertain_install_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();state=root/'state';state.mkdir(mode=0o700)
            c=dict(vm_name='fixture',guest_profile='omarchy',guest_user='desktop',storage_dir=str(root/'vms'),lume_app=str(root/'Lume.app'))
            receipt=state/'provision.json';receipt.write_text(json.dumps(dict(phase='created',guest_os='linux',vm_name='fixture',storage_dir=c['storage_dir'])));receipt.chmod(0o600)
            (state/'setup').mkdir(mode=0o700)
            checkpoint=state/'setup/linux-base.json';checkpoint.write_text(json.dumps(dict(schema_version=1,stage='needs_inspection',identity='old')));checkpoint.chmod(0o600)
            with patch.object(services,'config',return_value=c),patch.object(services,'hardening_state',return_value=state),patch.object(installer.mac,'verify_build'),patch.object(installer.os,'geteuid',return_value=501),patch.object(services,'call',side_effect=AssertionError('must not connect')):
                with self.assertRaisesRegex(ValueError,'requires_inspection'):installer.execute(root/'config','base',True)

if __name__=='__main__':unittest.main()
