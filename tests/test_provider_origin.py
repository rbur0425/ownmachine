import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine import origin


class ProviderOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = sys.modules.get('hermes_constants')
        self.addCleanup(self._restore)

    def _restore(self):
        if self.saved is None:
            sys.modules.pop('hermes_constants', None)
        else:
            sys.modules['hermes_constants'] = self.saved

    def _home(self, install):
        home = Path(self.tmp.name) / 'home'
        plugin = home / 'plugins' / 'ownmachine'
        if install == 'copy':
            plugin.mkdir(parents=True)
            (plugin / '__init__.py').write_text('')
        elif install == 'this':
            plugin.parent.mkdir(parents=True)
            plugin.symlink_to(origin.PACKAGE_ROOT, target_is_directory=True)
        fake = types.ModuleType('hermes_constants')
        fake.get_hermes_home = lambda: home
        sys.modules['hermes_constants'] = fake
        return home

    def test_other_profile_install_fails_closed(self):
        self._home('copy')
        self.assertEqual(origin.mismatch(), 'ownmachine_provider_loaded_from_other_profile')
        with self.assertRaisesRegex(RuntimeError, 'ownmachine_provider_loaded_from_other_profile'):
            origin.require_active_install()

    def test_active_install_passes_through_symlink(self):
        self._home('this')
        self.assertIsNone(origin.mismatch())
        origin.require_active_install()

    def test_in_place_upgrade_requires_restart(self):
        self._home('this')
        saved = origin.LOADED_IDENTITY
        self.addCleanup(setattr, origin, 'LOADED_IDENTITY', saved)
        origin.LOADED_IDENTITY = 'identity-before-upgrade'
        self.assertEqual(origin.mismatch(), 'ownmachine_plugin_changed_since_load')

    def test_profile_without_install_is_not_judged(self):
        self._home(None)
        self.assertIsNone(origin.mismatch())

    def test_missing_hermes_constants_is_not_judged(self):
        sys.modules['hermes_constants'] = types.ModuleType('hermes_constants')
        self.assertIsNone(origin.mismatch())


if __name__ == '__main__':
    unittest.main()
