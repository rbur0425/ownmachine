#!/usr/bin/env python3
"""Bounded AST regression rules; not whole-program taint analysis."""
import ast
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = {'PATH', 'HOME', 'SSH_AUTH_SOCK', 'LANG', 'LC_ALL', 'HERMES_HOME'}
BOUNDARIES = {'plugin/ownmachine/transport.py', 'plugin/ownmachine/setup_transport.py',
              'plugin/ownmachine/lifecycle.py', 'plugin/ownmachine/workspace.py',
              'plugin/ownmachine/reminder_scheduler.py', 'viewer/stream.py'}


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + '.' + node.attr
    return ''


def safe_env(node, bindings, seen=frozenset()):
    if isinstance(node, ast.Name) and node.id not in seen:
        values = bindings.get(node.id, [])
        return bool(values) and all(safe_env(v, bindings, seen | {node.id}) for v in values)
    if isinstance(node, ast.DictComp) and len(node.generators) == 1:
        g = node.generators[0]
        return (isinstance(g.target, ast.Name) and isinstance(g.iter, (ast.Tuple, ast.List))
                and all(isinstance(k, ast.Constant) and k.value in KEYS for k in g.iter.elts)
                and isinstance(node.key, ast.Name) and node.key.id == g.target.id
                and isinstance(node.value, ast.Subscript) and dotted(node.value.value) == 'os.environ'
                and isinstance(node.value.slice, ast.Name) and node.value.slice.id == g.target.id)
    if isinstance(node, ast.Dict):
        return all(safe_env(v, bindings, seen) if k is None else
                   isinstance(k, ast.Constant) and k.value in KEYS
                   for k, v in zip(node.keys, node.values))
    return False


def scan(text, path):
    tree = ast.parse(text)
    results = []
    bindings = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, []).append(n.value)
    def flag(n, rule, message):
        results.append({'path': path, 'line': n.lineno, 'rule': rule, 'message': message,
                        'fingerprint': hashlib.sha256(ast.get_source_segment(text, n).encode()).hexdigest()})
    access_opens = control_dirs = 0
    for n in ast.walk(tree):
        if isinstance(n, (ast.List, ast.Tuple)) and any(isinstance(x, ast.Constant) and x.value == '--vnc-password' for x in n.elts):
            flag(n, 'OM003', 'VNC passwords must use a private file, never argv.')
        if not isinstance(n, ast.Call):
            continue
        name = dotted(n.func)
        kw = {k.arg: k.value for k in n.keywords}
        if name in {'subprocess.Popen', 'subprocess.run', 'subprocess.call', 'subprocess.check_output', 'runner'}:
            if path in BOUNDARIES and not safe_env(kw.get('env'), bindings):
                flag(n, 'OM001', 'Transport child requires an explicit allowlisted environment.')
            if 'shell' in kw and not (isinstance(kw['shell'], ast.Constant) and kw['shell'].value is False):
                flag(n, 'OM002', 'Shell execution requires review; use an argument list.')
        if name == 'os.system':
            flag(n, 'OM002', 'Use an argument-list subprocess, not os.system.')
        if name.startswith(('subprocess.', 'os.exec')):
            if any(isinstance(x, ast.Constant) and x.value == '--vnc-password' for a in n.args for x in ast.walk(a)):
                flag(n, 'OM003', 'VNC passwords must use a private file, never argv.')
        if name in {'print', 'logging.debug', 'logging.info', 'logging.warning', 'logging.error'}:
            if any((isinstance(x, ast.Name) and x.id in {'password', 'vnc_password', 'guest_password', 'token'})
                   or (isinstance(x, ast.Attribute) and x.attr in {'password', 'token'})
                   for a in n.args for x in ast.walk(a)):
                flag(n, 'OM004', 'Do not log secret variables.')
        if path == 'viewer/server.py' and name == 'os.open' and n.args and dotted(n.args[0]) == 'path':
            access_opens += 1
            flags = {dotted(x) for x in ast.walk(n.args[1])} if len(n.args) > 1 else set()
            if (not {'os.O_CREAT', 'os.O_NOFOLLOW'} <= flags or len(n.args) < 3
                    or not isinstance(n.args[2], ast.Constant) or n.args[2].value != 0o600):
                flag(n, 'OM005', 'Viewer access creation requires O_CREAT|O_NOFOLLOW and 0600.')
        if path == 'plugin/ownmachine/lease.py' and name == 'self.path.parent.mkdir':
            control_dirs += 1
            mode = kw.get('mode')
            if not isinstance(mode, ast.Constant) or mode.value != 0o700:
                flag(n, 'OM006', 'Control directory creation requires explicit 0700.')
    # A refactor cannot silently remove these audited creation sites from coverage.
    for needed, count, rule in [('viewer/server.py', access_opens, 'OM005'),
                                ('plugin/ownmachine/lease.py', control_dirs, 'OM006')]:
        if path == needed and count != 1:
            results.append({'path': path, 'line': 1, 'rule': rule,
                            'message': 'Audited creation site changed; update the rule and regression tests.'})
    return results


def main():
    findings = []
    for directory in ('plugin', 'host', 'viewer', 'scripts', 'experiments'):
        for p in sorted((ROOT / directory).rglob('*.py')):
            if 'vendor' not in p.parts:
                findings.extend(scan(p.read_text(), p.relative_to(ROOT).as_posix()))
    exceptions = json.loads((ROOT / 'ci/security-exceptions.json').read_text())
    accepted = []
    for exception in exceptions:
        matches = [f for f in findings if all(f.get(k) == exception[k] for k in ('path', 'rule', 'fingerprint'))]
        if len(matches) != 1 or not exception.get('reason'):
            findings.append({'path': exception['path'], 'rule': 'OM000', 'message': 'Stale or invalid security exception.'})
        else:
            accepted.extend(matches)
    findings = [f for f in findings if f not in accepted]
    print(json.dumps({'findings': findings, 'reviewed_exceptions': accepted, 'ok': not findings}, indent=2))
    return int(bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
