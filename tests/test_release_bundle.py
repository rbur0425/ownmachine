import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release_bundle', Path(__file__).parents[1] / 'scripts/release-bundle.py')
bundle = importlib.util.module_from_spec(spec); spec.loader.exec_module(bundle)


class CatalogLicenseTests(unittest.TestCase):
    def test_subdirectory_install_carries_the_project_license(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / 'plugin/LICENSE').read_bytes(), (root / 'LICENSE').read_bytes())


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.root = self.base / 'repo'; self.root.mkdir()
        self.git('init'); self.git('config', 'user.name', 'Test'); self.git('config', 'user.email', 'test@example.invalid')
        for name in ('LICENSE', 'plugin/plugin.yaml', 'plugin/__init__.py', 'scripts/install-hermes.py',
                     'viewer/vendor/novnc/LICENSE.txt', 'viewer/requirements.txt'):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name)
        (self.root / '.gitignore').write_text('*.key\n')
        self.commit()
    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL)
    def commit(self):
        self.git('add', '.'); self.git('commit', '-m', 'fixture')
    def test_repeated_builds_match_and_only_plugin_installs(self):
        (self.root / 'private.key').write_text('NEVER_SHIP')
        a = self.base / 'a'; b = self.base / 'b'
        sha = bundle.build(self.root, a); bundle.build(self.root, b)
        self.assertEqual(bundle.verify(a), sha)
        self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()}, {p.name: p.read_bytes() for p in b.iterdir()})
        plugin = bundle.members((a / f'ownmachine-plugin-{sha}.tar.gz').read_bytes())
        self.assertEqual(set(plugin), {'LICENSE', 'plugin.yaml', '__init__.py'})
        source = bundle.members((a / f'ownmachine-source-{sha}.tar.gz').read_bytes())
        self.assertNotIn('private.key', source); self.assertFalse(any(n.startswith('.git/') for n in source))
    def test_dirty_and_untracked_refused_without_output(self):
        for name in ('LICENSE', 'untracked'):
            path = self.root / name; original = path.read_text() if path.exists() else None
            path.write_text('changed')
            with self.assertRaises(ValueError): bundle.build(self.root, self.base / 'output')
            self.assertFalse((self.base / 'output').exists())
            if original is None: path.unlink()
            else: path.write_text(original)
    def test_existing_and_inside_source_outputs_refused(self):
        target = self.base / 'existing'; target.mkdir(); (target / 'keep').write_text('keep')
        with self.assertRaises(FileExistsError): bundle.build(self.root, target)
        self.assertEqual((target / 'keep').read_text(), 'keep')
        with self.assertRaises(ValueError): bundle.build(self.root, self.root / 'dist')
    def test_archive_tampering_detected(self):
        out = self.base / 'out'; sha = bundle.build(self.root, out)
        path = out / f'ownmachine-plugin-{sha}.tar.gz'; path.write_bytes(path.read_bytes() + b'bad')
        with self.assertRaises(ValueError): bundle.verify(out)
    def test_manifest_inventory_and_checksum_tampering_detected(self):
        out = self.base / 'out'; bundle.build(self.root, out)
        path = out / 'manifest.json'; data = json.loads(path.read_text())
        data['artifacts'][next(iter(data['artifacts']))]['files'] = {}
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): bundle.verify(out)
    def test_symlink_sources_refused(self):
        (self.root / 'plugin/link').symlink_to('../LICENSE'); self.commit()
        with self.assertRaises(ValueError): bundle.build(self.root, self.base / 'out')
    def test_unsafe_archive_members_refused_without_extraction(self):
        for name, kind in (('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)):
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode='w') as archive:
                item = tarfile.TarInfo(name); item.type = kind; archive.addfile(item)
            with self.assertRaises(ValueError): bundle.members(raw.getvalue())
    def test_partial_build_removes_only_its_output(self):
        with patch.object(bundle, 'packed', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): bundle.build(self.root, self.base / 'failed')
        self.assertFalse((self.base / 'failed').exists()); self.assertTrue((self.root / 'LICENSE').exists())
