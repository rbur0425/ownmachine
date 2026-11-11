import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('onboarding_check', Path(__file__).resolve().parents[1] / 'scripts/ownmachine-check.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def report(status='pass', code='ready'):
    return {'ok': status != 'fail', 'checks': [{'check': 'fixture', 'status': status, 'code': code, 'remedy': 'synthetic advice'}]}


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.control = Path(self.temp.name) / 'not-created'
        self.config = module.Config(host_alias='example-mac', control_dir=str(self.control))
        self.native = patch.object(module, 'native_diagnose', return_value=report()).start()
        self.viewer = patch.object(module, 'viewer_diagnose', return_value=report()).start()
        self.addCleanup(patch.stopall)

    def test_both_checks_without_mutation(self):
        result = module.check(self.config)
        self.assertTrue(result['ok'])
        self.assertEqual(result['counts'], {'pass': 2, 'warn': 0, 'fail': 0})
        self.native.assert_called_once_with(self.config)
        self.viewer.assert_called_once_with(self.config, probe=False, access_dir=None)
        self.assertFalse(self.control.exists())
        self.assertEqual(len(result['manual_checks']), 3)

    def test_failure_does_not_hide_other_component(self):
        self.native.return_value = report('fail', 'guest_not_ready')
        self.viewer.return_value = report('fail', 'viewer_authentication_failed')
        result = module.check(self.config)
        self.assertFalse(result['ok'])
        self.assertEqual(result['counts']['fail'], 2)
        self.assertEqual(result['first_failure']['code'], 'guest_not_ready')
        self.viewer.assert_called_once()

    def test_exception_is_sanitized_and_other_check_runs(self):
        self.native.side_effect = RuntimeError('SECRET_TOKEN private.example')
        result = module.check(self.config)
        self.assertFalse(result['ok'])
        self.assertNotIn('SECRET_TOKEN', json.dumps(result))
        self.assertNotIn('private.example', module.render(result))
        self.viewer.assert_called_once()

    def test_native_scope_does_not_access_viewer(self):
        result = module.check(self.config, scope='native')
        self.assertTrue(result['ok'])
        self.assertEqual(result['counts']['warn'], 1)
        self.viewer.assert_not_called()
        self.assertIn('viewer_not_checked', module.render(result))

    def test_configuration_fails_before_any_check(self):
        for config, options in [(module.Config(), {}), (self.config, {'scope': 'other'}),
                                (self.config, {'scope': 'native', 'probe_vnc': True})]:
            self.assertFalse(module.check(config, **options)['ok'])
        self.native.assert_not_called()
        self.viewer.assert_not_called()

    def test_vnc_probe_only_when_explicit(self):
        module.check(self.config, probe_vnc=True)
        self.viewer.assert_called_once_with(self.config, probe=True, access_dir=None)

    def test_warnings_preserve_intentional_human_control(self):
        self.native.return_value = report('warn', 'control_human')
        result = module.check(self.config)
        self.assertTrue(result['ok'])
        self.assertIsNone(result['first_failure'])
        self.assertEqual(result['counts']['warn'], 1)
        self.assertIn('MANUAL — NOT VERIFIED', module.render(result))

    def test_malformed_or_inconsistent_doctor_fails_closed(self):
        for value in ({}, {'ok': True, 'checks': []}, {'ok': True, 'checks': report('fail')['checks']},
                      {'ok': True, 'checks': [{'check': 'x', 'status': 'pass', 'code': 'x'}]}):
            self.native.return_value = value
            self.assertFalse(module.check(self.config)['ok'])
