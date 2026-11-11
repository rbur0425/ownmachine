import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('upgrade_tool', Path(__file__).resolve().parents[1] / 'scripts/upgrade-hermes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        (self.source / 'plugin').mkdir(parents=True)
        (self.source / 'plugin/code.py').write_text('new version')
        (self.source / 'LICENSE').write_text('license')
        self.home = self.root / 'home'
        self.plugin = self.home / 'plugins/ownmachine'
        self.plugin.mkdir(parents=True)
        (self.plugin / 'code.py').write_text('old version')
        (self.plugin / 'LICENSE').write_text('license')
        self.receipt = self.home / 'ownmachine-install.json'
        self.receipt.write_text(json.dumps({'installer': 'ownmachine-fresh-home-v1', 'source_revision': 'old', 'plugin_files_sha256': module.inventory(self.plugin)}))
        self.old_receipt = self.receipt.read_bytes()
        (self.home / 'config.yaml').write_text('operator: settings\n')
        (self.home / 'lease.db').write_bytes(b'untouched')
        patch.object(module, 'ROOT', self.source).start()
        patch.object(module, 'revision', return_value='new-commit').start()
        self.addCleanup(patch.stopall)

    def apply(self):
        return module.upgrade(self.home, apply=True, runtime_stopped=True)

    def test_preview_is_read_only(self):
        before = sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*'))
        result = module.upgrade(self.home)
        self.assertFalse(result['applied'])
        self.assertEqual(result['updated'], ['code.py'])
        self.assertEqual(before, sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*')))
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)

    def test_upgrade_preserves_configuration_and_keeps_backup(self):
        result = self.apply()
        self.assertTrue(result['applied'])
        self.assertEqual((self.plugin / 'code.py').read_text(), 'new version')
        self.assertEqual((self.home / 'config.yaml').read_text(), 'operator: settings\n')
        self.assertEqual((self.home / 'lease.db').read_bytes(), b'untouched')
        backup = self.home / '.ownmachine-upgrades' / result['backup_id']
        self.assertEqual((backup / 'previous-plugin/code.py').read_text(), 'old version')
        self.assertEqual((backup / 'previous-receipt.json').read_bytes(), self.old_receipt)
        self.assertFalse((self.home / 'ownmachine-upgrade-pending.json').exists())
        self.assertFalse(self.apply()['changed'])

    def test_modified_extra_or_missing_files_refused(self):
        for kind in ('modified', 'extra', 'missing'):
            with self.subTest(kind=kind):
                path = self.plugin / ('extra' if kind == 'extra' else 'code.py')
                if kind == 'missing': path.unlink()
                else: path.write_text('modified')
                with self.assertRaises(ValueError): self.apply()
                if kind == 'extra': path.unlink()
                else: path.write_text('old version')
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)

    def test_runtime_confirmation_required(self):
        with self.assertRaises(ValueError): module.upgrade(self.home, apply=True)
        self.assertFalse((self.home / '.ownmachine-upgrade.lock').exists())

    def test_symlinks_and_pending_state_refused(self):
        for path in (self.plugin / 'alias', self.home / 'ownmachine-upgrade-pending.json'):
            path.symlink_to(self.root / 'absent')
            with self.assertRaises(ValueError): self.apply()
            path.unlink()
        (self.home / 'ownmachine-upgrade-pending.json').write_text('{}')
        with self.assertRaises(ValueError): self.apply()

    def test_lock_blocks_second_writer(self):
        with (self.home / '.ownmachine-upgrade.lock').open('w') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.apply()
        self.assertEqual((self.plugin / 'code.py').read_text(), 'old version')

    def test_activation_failure_restores_old_install(self):
        replace = os.replace
        def fail(source, target):
            if Path(source).name == 'candidate': raise OSError('synthetic failure')
            return replace(source, target)
        with patch.object(module.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError): self.apply()
        self.assertEqual((self.plugin / 'code.py').read_text(), 'old version')
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)
        self.assertFalse((self.home / 'ownmachine-upgrade-pending.json').exists())

    def test_receipt_failure_restores_old_install(self):
        replace = os.replace
        def fail(source, target):
            if Path(source).name == 'candidate-receipt.json': raise OSError('synthetic failure')
            return replace(source, target)
        with patch.object(module.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError): self.apply()
        self.assertEqual((self.plugin / 'code.py').read_text(), 'old version')
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)

    def test_failed_recovery_leaves_marker(self):
        replace = os.replace
        def fail(source, target):
            if Path(source).name in {'candidate', 'previous-plugin'}: raise OSError('synthetic failure')
            return replace(source, target)
        with patch.object(module.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError): self.apply()
        self.assertTrue((self.home / 'ownmachine-upgrade-pending.json').exists())
        with self.assertRaises(ValueError): self.apply()

    def test_source_symlink_refused_and_bytecode_ignored(self):
        (self.plugin / '__pycache__').mkdir()
        (self.plugin / '__pycache__/code.pyc').write_bytes(b'cache')
        self.assertTrue(module.upgrade(self.home)['changed'])
        (self.source / 'plugin/link').symlink_to(self.source / 'LICENSE')
        with self.assertRaises(ValueError): self.apply()
