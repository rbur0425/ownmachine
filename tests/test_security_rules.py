"""Regression probes must detect insecure changes, not merely scan green code."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('security_rules', ROOT / 'scripts/security-rules.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class SecurityRulesTests(unittest.TestCase):
    def codes(self, text, path='plugin/ownmachine/transport.py'):
        return {f['rule'] for f in rules.scan(text, path)}

    def test_environment_inheritance_and_copy_refused(self):
        for env in ['', ',env=os.environ', ',env=dict(os.environ)', ',env=os.environ.copy()',
                    ',env={**os.environ,"LANG":"C"}']:
            with self.subTest(env=env):
                self.assertIn('OM001', self.codes('subprocess.Popen(argv'+env+')'))

    def test_explicit_allowlist_and_locale_override_pass(self):
        source = '''env={k:os.environ[k] for k in ('PATH','HOME','SSH_AUTH_SOCK','LANG') if k in os.environ}
subprocess.Popen(argv,env={**env,'LC_ALL':'C','LANG':'C'})'''
        self.assertFalse(self.codes(source))
        self.assertIn('OM001', self.codes(source.replace("'PATH'", "'OPENAI_API_KEY'")))

    def test_shell_and_password_argv_refused(self):
        self.assertIn('OM002', self.codes('subprocess.run(command,shell=True,env={})'))
        self.assertIn('OM003', self.codes("argv=['lume','--vnc-password',password]\nsubprocess.run(argv,env={})"))
        self.assertIn('OM003', self.codes("subprocess.run(['lume','run','vm','--vnc-password',password],env={})"))
        self.assertNotIn('OM003', self.codes("subprocess.run(['lume','run','vm','--vnc-password-file',path],env={})"))

    def test_secret_logging_refused(self):
        self.assertIn('OM004', self.codes('print(f"password={password}")'))
        self.assertFalse(self.codes('print({"password_rotated": True})'))

    def test_private_viewer_creation_contract(self):
        safe = 'os.open(path,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)'
        self.assertFalse(self.codes(safe, 'viewer/server.py'))
        for bad in [safe.replace('|os.O_NOFOLLOW',''), safe.replace('0o600','0o644'), 'path.write_text(token)']:
            self.assertIn('OM005', self.codes(bad, 'viewer/server.py'))

    def test_control_directory_mode(self):
        self.assertFalse(self.codes('self.path.parent.mkdir(mode=0o700,parents=True)', 'plugin/ownmachine/lease.py'))
        self.assertIn('OM006', self.codes('self.path.parent.mkdir(parents=True)', 'plugin/ownmachine/lease.py'))


if __name__ == '__main__':
    unittest.main()
