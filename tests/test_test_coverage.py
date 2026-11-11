import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('coverage_gate', Path(__file__).resolve().parents[1] / 'scripts/check-tests.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class CoveragePolicyTests(unittest.TestCase):
    def fixture(self, *, group='hermes', reason=None, outcome='skip', platform='darwin', available=False, required=False, registered=True):
        class Sample(unittest.TestCase):
            def runTest(self):
                if outcome == 'skip': self.skipTest(reason or gate.REASONS[group])
                if outcome == 'fail': self.fail('synthetic failure')
                if outcome == 'error': raise RuntimeError('synthetic error')
        test = Sample()
        policy = {'hermes': [], 'macos': []}
        if registered: policy[group] = [test.id()]
        return gate.run_suite(unittest.TestSuite([test]), policy, platform=platform,
                              hermes_available=available, require_hermes=required, stream=io.StringIO())

    def test_local_missing_hermes_is_explicit(self):
        report = self.fixture()
        self.assertTrue(report['ok'])
        self.assertFalse(report['hermes_available'])
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['skipped'][0]['category'], 'hermes')

    def test_required_hermes_cannot_skip(self):
        self.assertFalse(self.fixture(required=True)['ok'])
        self.assertFalse(self.fixture(available=True)['ok'])

    def test_mac_tests_only_skip_off_mac(self):
        self.assertTrue(self.fixture(group='macos', platform='linux', available=True)['ok'])
        self.assertFalse(self.fixture(group='macos', platform='darwin', available=True)['ok'])

    def test_new_skip_and_changed_reason_fail(self):
        self.assertFalse(self.fixture(registered=False)['ok'])
        report = self.fixture(reason='unexpected reason with private detail')
        self.assertFalse(report['ok'])
        self.assertNotIn('private detail', str(report))

    def test_failures_and_errors_stay_failures(self):
        for outcome in ('fail', 'error'):
            self.assertFalse(self.fixture(outcome=outcome)['ok'])

    def test_passed_count_is_actual_successes(self):
        report = self.fixture(outcome='pass', available=True, required=True)
        self.assertTrue(report['ok'])
        self.assertEqual(report['passed'], 1)
        self.assertEqual(report['skipped'], [])

    def test_missing_platform_test_fails(self):
        report = gate.run_suite(unittest.TestSuite(), {'hermes': ['removed.test'], 'macos': []},
                                platform='linux', hermes_available=True, stream=io.StringIO())
        self.assertFalse(report['ok'])
        self.assertEqual(report['missing_platform_tests'], ['removed.test'])

    def test_expected_failure_is_not_coverage(self):
        class ExpectedFailure(unittest.TestCase):
            @unittest.expectedFailure
            def runTest(self): self.fail('synthetic')
        report = gate.run_suite(unittest.TestSuite([ExpectedFailure()]), {'hermes': [], 'macos': []},
                                platform='linux', hermes_available=True, stream=io.StringIO())
        self.assertFalse(report['ok'])
        self.assertEqual(report['expected_failures'], 1)
