import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from setup_support import module
boot=module('tested_linux_boot','scripts/setup-linux-boot.py')
endpoint=module('tested_boot_endpoint','scripts/setup-endpoint.py')

class LinuxBootTests(unittest.TestCase):
    def test_transition_routes_only_for_linux(self):
        for step in boot.STAGES:
            with self.assertRaisesRegex(ValueError,'requires_omarchy'):
                endpoint.command({},dict(guest_profile='macos'),step,True)

    def test_boot_requires_verified_creation_and_never_adopts_running_vm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();state=root/'state';state.mkdir(mode=0o700);create=root/'create';create.mkdir()
            iso=root/'installer';iso.write_bytes(b'iso')
            import hashlib
            c=dict(guest_profile='omarchy',vm_name='test',storage_dir=str(root/'vms'),lume_app='/example/Lume.app',guest_bootstrap_ssh_alias='live')
            for path,data in [(state/'provision.json',dict(phase='created',guest_os='linux',vm_name='test',storage_dir=c['storage_dir'],checkpoint_dir=str(create))), (create/'linux-create.json',dict(stage='verified'))]:
                path.write_text(json.dumps(data));path.chmod(0o600)
            with patch.object(boot.services,'config',return_value=c),patch.object(boot.services,'hardening_state',return_value=state),patch.object(boot.mac,'verify_build'),patch.object(boot.os,'geteuid',return_value=501),patch.object(boot,'vm',return_value=dict(status='running')),patch.object(boot.subprocess,'Popen') as launch:
                with self.assertRaisesRegex(ValueError,'stopped_guest'):
                    boot.execute(root/'config','linux-boot-installer',iso,hashlib.sha256(b'iso').hexdigest())
                launch.assert_not_called()
                self.assertFalse((state/'setup/linux-boot-installer.json').exists())

    def test_verified_transition_is_observed_without_launch_or_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();state=root/'state';state.mkdir(mode=0o700);(state/'setup').mkdir(mode=0o700)
            c=dict(guest_profile='omarchy',vm_name='test',storage_dir=str(root/'vms'),lume_app='/example/Lume.app')
            records={state/'provision.json':dict(phase='created',guest_os='linux',vm_name='test',storage_dir=c['storage_dir']),
                     state/'setup/linux-base.json':dict(stage='verified'),
                     state/'setup/linux-boot-system.json':dict(schema_version=1,stage='verified',identity='fixed')}
            for path,data in records.items():path.write_text(json.dumps(data));path.chmod(0o600)
            with patch.object(boot.services,'config',return_value=c),patch.object(boot.services,'hardening_state',return_value=state),patch.object(boot.mac,'verify_build'),patch.object(boot.mac,'digest',return_value='fixed'),patch.object(boot.os,'geteuid',return_value=501),patch.object(boot,'ready',return_value=True) as ready,patch.object(boot,'vm',side_effect=AssertionError('no lifecycle replay')):
                result=boot.execute(root/'config','linux-boot-system')
                self.assertFalse(result['replayed']);ready.assert_called_once()
                records[state/'setup/linux-boot-system.json']['stage']='running'
                (state/'setup/linux-boot-system.json').write_text(json.dumps(records[state/'setup/linux-boot-system.json']))
                with self.assertRaisesRegex(ValueError,'uncertain_boot'):
                    boot.execute(root/'config','linux-boot-system')
                self.assertEqual(ready.call_count,1)

    def test_installer_connection_never_falls_back_to_desktop_identity(self):
        with self.assertRaisesRegex(ValueError,'pinned_bootstrap'):
            boot.connection(dict(guest_ssh_alias='desktop'),True)
        self.assertEqual(boot.connection(dict(guest_ssh_alias='desktop',guest_bootstrap_ssh_alias='live'),True)['guest_ssh_alias'],'live')

    def test_shutdown_requires_observed_stopped_state_even_if_ssh_disconnects(self):
        with patch.object(boot.services,'guest_argv',return_value=['ssh','pinned']),patch.object(boot.services,'call',side_effect=subprocess.CalledProcessError(255,[])),patch.object(boot,'wait') as wait:
            boot.shutdown({},False)
            wait.assert_called_once()

if __name__=='__main__':unittest.main()
