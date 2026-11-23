import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import kvm_disk
import omarchy_kvm
spec = importlib.util.spec_from_file_location('firstboot', SCRIPTS / 'omarchy/first-boot.py')
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name)
        self.src = self.parent / 'build'
        self.owner = pwd.getpwuid(os.getuid())
        self.size = 1024**3
        self.header = bytearray(104)
        struct.pack_into('>4sI', self.header, 0, b'QFI\xfb', 3)
        struct.pack_into('>Q', self.header, 24, self.size)

    def copy(self):
        with patch.object(kvm_disk, 'require_trusted_parent'), patch.object(
            kvm_disk.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({'format': 'qcow2', 'virtual-size': self.size}))) as parser:
            out = kvm_disk.import_disk(self.src, self.parent, 'fixture', self.owner.pw_uid,
                                       self.owner, self.size, hashlib.sha256(self.header).hexdigest())
            self.assertEqual(parser.call_count, 1)
            return out

    def test_publish_independent_disk_reuse_only_unchanged_import(self):
        self.src.write_bytes(self.header)
        out = self.copy()
        self.assertNotEqual(out.stat().st_ino, self.src.stat().st_ino)
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
        inode = out.stat().st_ino
        self.assertEqual(self.copy().stat().st_ino, inode)
        out.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "existing_runtime_disk_requires_inspection"):
            self.copy()
        self.assertEqual(out.read_bytes(), b"changed")
        out.write_bytes(self.header)
        self.src.write_bytes(b'new build')
        self.assertEqual(out.read_bytes(), self.header)

    def test_build_consumes_the_same_downloaded_bytes_that_were_verified(self):
        pins = {}
        config = {'guest_user':'omarchy'}
        for name in omarchy_kvm.PINS:
            filename = name.replace('_wheel','-fixture.whl')
            path = self.parent/filename
            path.write_bytes(name.encode())
            config[name] = str(path)
            pins[name] = hashlib.sha256(name.encode()).hexdigest()
        def build(state, verified):
            for name in pins:
                Path(config[name]).write_bytes(b'changed download')
                self.assertEqual(Path(verified[name]).read_bytes(),name.encode())
        with patch.dict(omarchy_kvm.PINS,pins),patch.object(omarchy_kvm,'build_verified_disk',side_effect=build) as consumer:
            omarchy_kvm.prepare_disk(self.parent,config)
            with self.assertRaisesRegex(ValueError,'artifact_hash_mismatch'):
                omarchy_kvm.prepare_disk(self.parent,config)
            self.assertEqual(consumer.call_count,1)

    def test_refuse_untrusted_parent(self):
        with self.assertRaises(ValueError):
            kvm_disk.require_trusted_parent(self.parent)

    def test_linked_and_special_inputs_refused(self):
        target = self.parent / 'ordinary-file'
        target.write_bytes(self.header)
        self.src.symlink_to(target)
        with self.assertRaises(OSError):
            self.copy()
        self.src.unlink()
        os.link(target, self.src)
        with self.assertRaises(ValueError):
            self.copy()
        self.src.unlink()
        os.mkfifo(self.src)
        with self.assertRaises(ValueError):
            self.copy()
        self.assertFalse((self.parent / 'fixture.qcow2').exists())

    def test_nonstandalone_headers_refused_before_parsing(self):
        for offset in (8, 16, 32, 60, 64, 72, 79):
            with self.subTest(offset=offset):
                self.header[offset] = 1
                self.src.write_bytes(self.header)
                with self.assertRaisesRegex(ValueError, 'standalone'):
                    self.copy()
                self.header[offset] = 0
                self.assertFalse((self.parent / 'fixture.qcow2').exists())


class RecoveryTests(unittest.TestCase):
    def test_reuse_only_exact_private_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'authorized_keys'
            user = pwd.getpwuid(os.getuid())
            boot.ensure_key(p, b'fixture', user)
            inode = p.stat().st_ino
            boot.ensure_key(p, b'fixture', user)
            self.assertEqual(inode, p.stat().st_ino)
            for content, mode in [(b'other', 0o600), (b'fixture', 0o644)]:
                p.write_bytes(content)
                p.chmod(mode)
                with self.assertRaises(ValueError):
                    boot.ensure_key(p, b'fixture', user)
                self.assertEqual(p.read_bytes(), content)
            link = Path(tmp) / 'other'
            link.symlink_to(p)
            with self.assertRaises(OSError):
                boot.ensure_key(link, b'fixture', user)

    def test_ready_tools_are_probed_without_reinstallation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(boot, 'ROOT', Path(tmp)):
            binaries = Path(tmp) / 'tools/bin'
            binaries.mkdir(parents=True)
            for name in ('python', 'cmake', 'ninja'):
                path = binaries / name
                path.touch()
                path.chmod(0o700)
            with patch.object(boot.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                boot.install_tools()
                self.assertFalse(any('venv' in c.args[0] or 'install' in c.args[0] for c in run.call_args_list))
