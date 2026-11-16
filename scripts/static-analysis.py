#!/usr/bin/env python3
"""Run all deterministic analyzers; preserve every report and fail on gate errors."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    shell = [p for p in files if p.endswith('.sh') and not p.startswith('viewer/vendor/')]
    commands = {
        'ruff': ['ruff', 'check', '--output-format', 'json', '.'],
        'bandit': ['bandit', '-q', '-r', 'plugin', 'host', 'viewer', 'scripts', 'experiments', '-x', 'viewer/vendor',
                   '--severity-level', 'high', '-f', 'json'],
        'shellcheck': ['shellcheck', '--format=json', *shell],
        'actionlint': ['actionlint', '-color=false'],
        'zizmor': ['zizmor', '--offline', '--min-severity', 'high', '--format', 'json', '.github/workflows'],
        'mypy': ['mypy', '--config-file', 'mypy.ini'],
        'ownmachine': [sys.executable, 'scripts/security-rules.py'],
    }
    results = {}
    for name, argv in commands.items():
        try:
            if not shutil.which(argv[0]):
                raise RuntimeError('Required analyzer is missing: ' + argv[0])
            with (output / (name + '.txt')).open('w') as out, (output / (name + '.stderr')).open('w') as err:
                result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=300, check=False)
            results[name] = result.returncode
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            (output / (name + '.stderr')).write_text(str(exc))
            results[name] = 2
    # Informational medium/low-severity inventory is retained, never hidden by the gate.
    with (output / 'bandit-all.json').open('w') as out, (output / 'bandit-all.stderr').open('w') as err:
        try:
            result = subprocess.run(['bandit', '-q', '-r', 'plugin', 'host', 'viewer', 'scripts', 'experiments',
                                     '-x', 'viewer/vendor', '-f', 'json'], cwd=ROOT, stdout=out, stderr=err,
                                    timeout=300, check=False)
            if result.returncode not in (0, 1):
                results['bandit-inventory'] = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            err.write(str(exc))
            results['bandit-inventory'] = 2
    try:
        if json.loads((output / 'bandit-all.json').read_text()).get('errors'):
            results['bandit-inventory'] = 2
    except (OSError, ValueError):
        results['bandit-inventory'] = 2
    with (output / 'zizmor-all.json').open('w') as out, (output / 'zizmor-all.stderr').open('w') as err:
        try:
            result = subprocess.run(['zizmor', '--offline', '--no-exit-codes', '--format', 'json',
                                     '.github/workflows'], cwd=ROOT, stdout=out, stderr=err,
                                    timeout=300, check=False)
            if result.returncode:
                results['zizmor-inventory'] = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            err.write(str(exc))
            results['zizmor-inventory'] = 2
    report = {'ok': all(code == 0 for code in results.values()), 'exit_codes': results}
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(not report['ok'])


if __name__ == '__main__':
    raise SystemExit(main())
