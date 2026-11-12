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
