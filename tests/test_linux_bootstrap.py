"""Private installer seed preserves archive modes and rejects partial input."""
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from setup_support import module
bootstrap=module('tested_linux_bootstrap','scripts/prepare-linux-bootstrap.py')


class BootstrapTests(unittest.TestCase):
    def test_cpio_roundtrip_and_truncated_payload(self):
        data=bootstrap.pack([('./etc/example',stat.S_IFREG|0o600,b'fixture')])
        rows=list(bootstrap.records(data))
        self.assertEqual([r[0] for r in rows],['./etc/example','TRAILER!!!'])
        with self.assertRaisesRegex(ValueError,'truncated'):
            list(bootstrap.records(data[:120]))

    def test_seed_has_no_password_or_anonymous_web_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for name in ('host','host.pub','guest.pub'):
                (root/name).write_bytes(b'fixture\n');(root/name).chmod(0o600)
            entries={name:(mode,content) for name,mode,content in bootstrap.seed(root)}
            self.assertEqual(entries['./etc/systemd/system/ttyd.service'][1],b'/dev/null')
            self.assertEqual(entries['./etc/systemd/system/sshd.service'][1],b'/dev/null')
            self.assertEqual(entries['./etc/ssh/ssh_host_ed25519_key'][0],stat.S_IFREG|0o600)
            config=entries['./etc/ownmachine-bootstrap/sshd_config'][1]
            self.assertIn(b'PasswordAuthentication no',config)
            self.assertIn(b'AllowTcpForwarding no',config)
            self.assertIn(b'ClientIdentifier=mac',entries['./etc/systemd/network/00-ownmachine-bootstrap.network'][1])
            self.assertEqual(entries['./root/.ssh/authorized_keys'][1],b'restrict fixture\n')

    def test_checksum_failure_creates_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();iso=root/'source.iso';iso.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'checksum'):
                bootstrap.prepare(iso,'0'*64,root/'output')
            self.assertFalse((root/'output').exists())


if __name__=='__main__':unittest.main()
