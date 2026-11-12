#!/usr/bin/env python3
"""Read-only onboarding checks for native access and the local browser viewer."""
from dataclasses import replace
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))
sys.path.insert(0, str(ROOT / 'viewer'))
from ownmachine.config import Config
from ownmachine.diagnostics import diagnose as native_diagnose
from diagnostics import diagnose as viewer_diagnose

MANUAL = [
    {'check': 'browser_input', 'instruction': 'Open the current private viewer link, reserve human control and test typing/clicking in a disposable document.'},
    {'check': 'external_firewall', 'instruction': 'From another machine confirm direct host VNC is blocked while the SSH-backed viewer works; repeat after host reboot.'},
    {'check': 'guest_persistence', 'instruction': 'Save work before an explicitly requested graceful restart and verify the saved document and application profile afterward.'},
]


def check(config, *, scope='all', probe_vnc=False, access_dir=None, viewer_host_alias=None):
    checks = []
    def finish():
        counts = {level: sum(c['status'] == level for c in checks) for level in ('pass', 'warn', 'fail')}
        first = next((dict(c) for c in checks if c['status'] == 'fail'), None)
        return {'format': 1, 'ok': counts['fail'] == 0, 'requested_scope': scope,
                'counts': counts, 'first_failure': first, 'checks': checks,
                'manual_checks': [dict(item) for item in MANUAL],
                'scope': 'Read-only readiness in the current environment, not release certification. No capture, input, control transfer, permission approval or VM lifecycle.'}
    try:
        config.validate()
        if not config.control_dir or scope not in {'all', 'native'} or (probe_vnc and scope != 'all'):
            raise ValueError()
    except (ValueError, TypeError):
        checks.append({'check': 'configuration', 'status': 'fail', 'code': 'invalid_configuration',
                       'remedy': 'Supply an SSH alias, VM name, absolute shared control directory and timeouts from 1 to 120. VNC probing requires all checks.'})
        return finish()
    selected = [('native', lambda: native_diagnose(config))]
    if scope == 'all':
        selected.append(('viewer', lambda: viewer_diagnose(replace(config,host_alias=viewer_host_alias) if viewer_host_alias else config, probe=probe_vnc, access_dir=access_dir)))
    for name, diagnose in selected:
        try:
            result = diagnose()
            rows = result['checks']
            if not isinstance(rows, list) or not rows or any(
                    not isinstance(row, dict) or row.get('status') not in {'pass', 'warn', 'fail'}
                    or any(not isinstance(row.get(field), str) for field in ('check', 'code', 'remedy'))
                    for row in rows):
                raise ValueError()
            if type(result.get('ok')) is not bool or result['ok'] != (not any(row['status'] == 'fail' for row in rows)):
                raise ValueError()
            # Forward only the established doctors' sanitized check fields.
            checks.extend({'check': name + '.' + row['check'], **{k: row[k] for k in ('status', 'code', 'remedy')}} for row in rows)
        except Exception:
            checks.append({'check': name + '.diagnostics', 'status': 'fail', 'code': 'diagnostics_unavailable',
                           'remedy': 'Run the corresponding standalone doctor in its configured environment. Check matching source and dependencies; raw exception details are omitted.'})
    if scope == 'native':
        checks.append({'check': 'viewer', 'status': 'warn', 'code': 'viewer_not_checked',
                       'remedy': 'Browser checks were not requested. Run all checks on the viewer machine as its owner when using the browser desktop.'})
    return finish()


def render(report):
    lines = ['OwnMachine onboarding: ' + ('CHECKS PASSED' if report['ok'] else 'NEEDS ATTENTION')]
    if report['first_failure']:
        first = report['first_failure']
        lines += ['Fix first: ' + first['check'] + ': ' + first['code'], '  ' + first['remedy']]
    for row in report['checks']:
        lines.append(f"[{row['status'].upper()}] {row['check']}: {row['code']}")
        if row['remedy']:
            lines.append('  ' + row['remedy'])
    for row in report['manual_checks']:
        lines.append('[MANUAL — NOT VERIFIED] ' + row['check'] + ': ' + row['instruction'])
    lines.append(report['scope'])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-alias', required=True)
    parser.add_argument('--guest-profile', choices=['macos','omarchy'], default='macos')
    parser.add_argument('--vm-name', default='ownmachine')
    parser.add_argument('--control-dir', required=True)
    parser.add_argument('--connect-timeout-seconds', type=int, default=15)
    parser.add_argument('--action-timeout-seconds', type=int, default=30)
    parser.add_argument('--access-dir')
    parser.add_argument('--viewer-host-alias')
    parser.add_argument('--scope', choices=('all', 'native'), default='all')
    parser.add_argument('--probe-vnc', action='store_true')
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = vars(parser.parse_args())
    as_json = args.pop('as_json'); scope = args.pop('scope'); probe = args.pop('probe_vnc')
    access_dir=args.pop('access_dir'); viewer_alias=args.pop('viewer_host_alias')
    report = check(Config(**args), scope=scope, probe_vnc=probe, access_dir=access_dir, viewer_host_alias=viewer_alias)
    print(json.dumps(report, sort_keys=True) if as_json else render(report))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
