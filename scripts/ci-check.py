#!/usr/bin/env python3
"""Offline CI gate: tests, repeatable bundles and isolated install validation."""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check(require_hermes=False):
    sys.path.insert(0, str(ROOT / 'plugin'))
    try:
        from ownmachine.provider import OwnMachineBackend
        hermes_available = OwnMachineBackend is not None
    except ImportError:
        hermes_available = False
    if require_hermes and not hermes_available:
        raise RuntimeError('Hermes provider contract unavailable: configure the CI image and Python interpreter before enabling this required gate.')
    with tempfile.TemporaryDirectory(prefix='ownmachine-ci-') as folder:
        work = Path(folder).resolve()
        env = os.environ.copy()
        env.pop('SSH_AUTH_SOCK', None)
        env['HERMES_HOME'] = str(work / 'isolated-hermes')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        def run(*args):
            subprocess.run(args, cwd=ROOT, env=env, check=True)
        test_command = [sys.executable, str(ROOT / 'scripts/check-tests.py')]
        if require_hermes:
            test_command.append('--require-hermes')
        completed = subprocess.run(test_command, cwd=ROOT, env=env, check=True,
                                   stdout=subprocess.PIPE, text=True)
        coverage = json.loads(completed.stdout)
        if not coverage['ok']:
            raise RuntimeError('Test coverage policy failed.')
        run('git', 'diff', '--check')
        script = ROOT / 'scripts/release-bundle.py'
        spec = importlib.util.spec_from_file_location('bundle_gate', script)
        bundle = importlib.util.module_from_spec(spec); spec.loader.exec_module(bundle)
        revision = bundle.build(ROOT, work / 'first')
        bundle.build(ROOT, work / 'second')
        bundle.verify(work / 'first'); bundle.verify(work / 'second')
        first = {p.name: p.read_bytes() for p in (work / 'first').iterdir()}
        second = {p.name: p.read_bytes() for p in (work / 'second').iterdir()}
        if first != second:
            raise RuntimeError('Repeated bundle builds differ.')
        def unpack(kind):
            target = work / kind; target.mkdir()
            files = bundle.members((work / 'first' / f'ownmachine-{kind}-{revision}.tar.gz').read_bytes())
            # Verified regular files only, in our newly created directory.
            for name, (content, executable) in files.items():
                path = target / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content); path.chmod(0o755 if executable else 0o644)
            return target
        plugin = unpack('plugin'); source = unpack('source')
        run(sys.executable, str(source / 'scripts/install-hermes.py'),
            '--hermes-home', str(work / 'fresh-home'), '--host-alias', 'example-mac',
            '--control-dir', str(work / 'unused-control'))
        if (work / 'unused-control').exists():
            raise RuntimeError('Fresh installation unexpectedly initialized control state.')
        if (work / 'fresh-home/plugins/ownmachine/LICENSE').read_bytes() != (ROOT / 'LICENSE').read_bytes():
            raise RuntimeError('Fresh installation lost the project license.')
        # Exercise an upgrade only in this disposable, never-started home.
        fresh_home = work / 'fresh-home'
        installed = fresh_home / 'plugins/ownmachine'
        fixture_file = next(iter(sorted(installed.rglob('*.py'))))
        fixture_file.write_bytes(fixture_file.read_bytes() + b'\n# prior-version CI fixture\n')
        receipt_path = fresh_home / 'ownmachine-install.json'
        receipt = json.loads(receipt_path.read_text())
        receipt['plugin_files_sha256'][str(fixture_file.relative_to(installed))] = hashlib.sha256(fixture_file.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        configuration = (fresh_home / 'config.yaml').read_bytes()
        run(sys.executable, str(source / 'scripts/upgrade-hermes.py'),
            '--hermes-home', str(fresh_home), '--apply', '--runtime-stopped')
        if (fresh_home / 'config.yaml').read_bytes() != configuration:
            raise RuntimeError('Upgrade changed configuration.')
        if (fresh_home / 'ownmachine-upgrade-pending.json').exists():
            raise RuntimeError('Upgrade did not finish.')
        for path in plugin.rglob('*'):
            if path.is_file() and (installed / path.relative_to(plugin)).read_bytes() != path.read_bytes():
                raise RuntimeError('Upgraded package differs from verified artifact.')
        if hermes_available:
            cli = 'import sys; from hermes_cli.main import main; sys.argv=["hermes","plugins","validate",sys.argv[1]]; raise SystemExit(main())'
            for directory in (ROOT / 'plugin', plugin, work / 'fresh-home/plugins/ownmachine'):
                run(sys.executable, '-c', cli, str(directory))
        return {'ok': True, 'source_revision': revision,
                'hermes_contract_and_validation': hermes_available,
                'test_coverage': coverage,
                'repeatable_bundles': True, 'fresh_home_installation': True, 'offline_upgrade': True,
                'scope': 'Offline fixtures and package validation; no hardware test or deployment.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-hermes', action='store_true')
    args = parser.parse_args()
    try:
        report = check(args.require_hermes)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('CI gate failed: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
