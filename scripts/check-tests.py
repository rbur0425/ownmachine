#!/usr/bin/env python3
"""Run offline tests with explicit platform coverage and fail on unknown skips."""
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REASONS = {'hermes': 'Requires installed Hermes public provider contract',
           'macos': 'Requires macOS plutil and launch-agent format'}


def test_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from test_ids(test)
        else:
            yield test.id()


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = 0

    def addSuccess(self, test):
        self.passed += 1
        super().addSuccess(test)


def run_suite(suite, policy, *, platform, hermes_available, require_hermes=False, stream=None):
    discovered = set(test_ids(suite))
    required = set(policy['hermes']) | set(policy['macos'])
    allowed = {}
    if not hermes_available and not require_hermes:
        allowed.update((name, REASONS['hermes']) for name in policy['hermes'])
    if platform != 'darwin':
        allowed.update((name, REASONS['macos']) for name in policy['macos'])
    result = unittest.TextTestRunner(stream=stream or sys.stderr, verbosity=2,
                                     resultclass=Result).run(suite)
    skipped = [{'test': test.id(), 'expected': allowed.get(test.id()) == reason,
                'category': next((key for key, value in REASONS.items()
                                  if value == reason and test.id() in policy[key]), 'unrecognized')}
               for test, reason in result.skipped]
    missing = sorted(required - discovered)
    ok = (result.wasSuccessful() and not result.expectedFailures and not missing
          and all(item['expected'] for item in skipped)
          and (hermes_available or not require_hermes) and result.testsRun > 0)
    return {'ok': bool(ok), 'platform': platform, 'hermes_available': hermes_available,
            'hermes_required': require_hermes, 'tests_run': result.testsRun,
            'passed': result.passed, 'failures': len(result.failures),
            'errors': len(result.errors), 'expected_failures': len(result.expectedFailures),
            'unexpected_successes': len(result.unexpectedSuccesses),
            'skipped': skipped, 'missing_platform_tests': missing,
            'scope': 'Offline test coverage only; separate platform runs and hardware acceptance are required.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-hermes', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'plugin'))
    try:
        from ownmachine.provider import OwnMachineBackend
    except ImportError:
        OwnMachineBackend = None
    policy = json.loads((ROOT / 'ci/test-platforms.json').read_text())
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    report = run_suite(suite, policy, platform=sys.platform,
                       hermes_available=OwnMachineBackend is not None,
                       require_hermes=args.require_hermes)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
