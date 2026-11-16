#!/usr/bin/env python3
"""Audit current resolved runtime dependencies from their source declarations."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dependencies = yaml.safe_load((ROOT / 'plugin/plugin.yaml').read_text())['python_dependencies']
    with tempfile.TemporaryDirectory(prefix='ownmachine-audit-') as temp:
        requirements = Path(temp) / 'requirements.txt'
        requirements.write_text('\n'.join(dependencies) + '\n' + (ROOT / 'viewer/requirements.txt').read_text())
        # pip-audit resolves the declared ranges and transitive dependencies in isolation.
        env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'SSL_CERT_FILE', 'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY') if k in os.environ}
        return subprocess.run([sys.executable, '-m', 'pip_audit', '-r', str(requirements),
                               '--format', 'json', '--output', str(args.output.resolve())],
                              env=env, timeout=600, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
