"""Fail closed before guest desktop/driver startup, including resumed setup."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from setup_support import module

gate=module('tested_hardening_gate','scripts/linux-hardening-gate.py')
guest=module('tested_gated_driver','scripts/linux-guest.py')
services=module('tested_gated_services','scripts/setup-services.py')
installer=module('tested_gated_installer','scripts/install-linux-desktop.py')

class HardeningGateTests(unittest.TestCase):
    def test_missing_receipt_blocks_driver_before_download_or_mutation(self):
        with patch.object(guest.Path,'lstat',side_effect=FileNotFoundError), patch.object(guest,'private_dir') as mkdir, patch.object(guest.urllib.request,'urlopen') as download:
            with self.assertRaises(FileNotFoundError):guest.install(guest.VERSION,guest.SHA256)
            mkdir.assert_not_called();download.assert_not_called()
            self.assertFalse(guest.readiness()['driver_ready'])

    def test_untrusted_receipt_or_ancestor_is_rejected(self):
        for mode,uid in ((0o100666,0),(0o120644,0),(0o100644,1000)):
            with self.subTest(mode=mode,uid=uid),patch.object(guest.Path,'lstat',return_value=SimpleNamespace(st_uid=uid,st_mode=mode)):
                with self.assertRaisesRegex(ValueError,'untrusted'):guest.require_hardening()
                with self.assertRaisesRegex(ValueError,'untrusted'):gate.trusted(Path('/etc/ownmachine/hardened.json'))

    def test_receipt_does_not_allow_reintroduced_passwordless_sudo(self):
        with patch.object(guest.Path,'lstat',return_value=SimpleNamespace(st_uid=0,st_mode=0o100644)),patch.object(guest.Path,'is_file',return_value=True),patch.object(guest.Path,'read_text',return_value=json.dumps(dict(schema_version=1,uid=1000))),patch.object(guest.os,'getuid',return_value=1000),patch.object(guest,'call'),patch.object(guest.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            with self.assertRaisesRegex(ValueError,'passwordless_sudo'):guest.require_hardening()

    def test_fresh_and_resumed_driver_stages_recheck_hardening(self):
        for operation in (services.preflight_mutation,services.verify,services.apply):
            with self.subTest(operation=operation.__name__),patch.object(services,'verify_hardening',side_effect=ValueError('not_hardened')),patch.object(services,'call') as connect,patch.object(services,'install_driver') as install:
                with self.assertRaisesRegex(ValueError,'not_hardened'):operation('driver',{'guest_profile':'omarchy'})
                connect.assert_not_called();install.assert_not_called()

    def test_boot_gate_requires_current_policy_not_just_receipt(self):
        with patch.object(gate,'trusted'),patch.object(gate.Path,'read_text',return_value=json.dumps(dict(schema_version=1,user='desktop',uid=1000))),patch.object(gate,'live_policy',side_effect=ValueError('firewall_disabled')):
            with self.assertRaisesRegex(ValueError,'firewall_disabled'):gate.check()

    def test_failed_live_check_never_publishes_receipt(self):
        with patch.object(gate,'live_policy',side_effect=ValueError('unsafe_policy')),patch.object(gate.os,'open') as create:
            with self.assertRaisesRegex(ValueError,'unsafe_policy'):gate.seal('desktop')
            create.assert_not_called()

    def test_desktop_prefix_is_valid_shell_and_installs_boot_guard(self):
        script=installer.hardening_gate_script()
        subprocess.run(['bash','-n'],input=script.encode(),check=True)
        self.assertIn('Requires=ownmachine-firewall.service',script)
        self.assertIn('ExecStartPre=/usr/bin/python3 /usr/local/libexec/ownmachine-hardening-gate.py',script)
        self.assertIn('os.O_EXCL|os.O_NOFOLLOW',script)

    def test_live_policy_refuses_accept_firewall_and_unrestricted_sudo(self):
        ssh='\n'.join(('passwordauthentication no','kbdinteractiveauthentication no','permitrootlogin no','allowtcpforwarding no','allowagentforwarding no'))
        for policy,returncode in [('accept',1),('drop',0)]:
            nft=json.dumps({'nftables':[{'chain':{'name':name,'policy':policy}} for name in ('input','forward')]})
            with self.subTest(policy=policy),patch.object(gate.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=1000)),patch.object(gate,'run',side_effect=[ssh,'',nft,'']),patch.object(gate.subprocess,'run',return_value=SimpleNamespace(returncode=returncode)):
                with self.assertRaises(ValueError):gate.live_policy('desktop')
