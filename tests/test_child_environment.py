"""Real child-process checks: provider credentials never cross setup/CLI spawns."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugin'))
from ownmachine import setup_transport as setup, reminder_scheduler as scheduler
from ownmachine import setup_acceptance as acceptance
from test_onboarding_commands import Context


class ChildEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.allowed = dict(PATH=os.defpath, HOME='/example/operator',
                            SSH_AUTH_SOCK='/example/agent.sock', LANG='C')
        self.parent = dict(self.allowed, OPENAI_API_KEY='synthetic-provider-key',
                           ANTHROPIC_API_KEY='synthetic-other-key',
                           UNDECLARED_SECRET='synthetic-secret',
                           PYTHONPATH='/example/injected', PYTHONSTARTUP='/example/startup',
                           HERMES_HOME='/example/wrong-profile', LC_ALL='C')
        self.ctx = Context(dict(setup_host_alias='setup-only', setup_source_sha256='a'*64))
        self.plan = dict(host_alias='agent', vm_name='fixture', control_dir='/example/control')

    def assert_child_environment(self, child, expected):
        # Python locale coercion/macOS runtime can add these after exec.
        for name in ('LC_CTYPE', '__CF_USER_TEXT_ENCODING'):
            child.pop(name, None)
        self.assertEqual(child, expected)

    def test_setup_exchange_real_child_has_only_allowlisted_environment(self):
        script = 'import os,sys,json; sys.stdin.read(); print(json.dumps(dict(os.environ)))'
        with patch.dict(os.environ, self.parent, clear=True), \
                patch.object(setup.subprocess, 'Popen', wraps=subprocess.Popen) as spawn:
            child = setup.exchange([sys.executable, '-c', script], {}, 5)
        self.assertEqual(spawn.call_args.kwargs['env'], self.allowed)
        self.assert_child_environment(child, self.allowed)

    def test_retirement_child_has_minimal_environment_and_fixed_locale(self):
        run = subprocess.run
        observed = []
        def probe(argv, **kwargs):
            self.assertEqual(argv[0], 'ssh')
            self.assertEqual(kwargs['env'], dict(self.allowed, LANG='C', LC_ALL='C'))
            script = ('import os,sys,json; sys.stdin.read(); '
                      'print(json.dumps(dict(os.environ))); '
                      'sys.stderr.write("Permission denied (publickey).\\n"); sys.exit(255)')
            result = run([sys.executable, '-c', script], **kwargs)
            observed.append(json.loads(result.stdout))
            return result
        with patch.dict(os.environ, dict(self.parent, LANG='foreign', LC_ALL='foreign'), clear=True), \
                patch.object(setup.subprocess, 'run', side_effect=probe):
            setup.prove_retired(self.ctx, self.plan)
        self.assertEqual(len(observed), 1)
        self.assert_child_environment(observed[0], dict(self.allowed, LANG='C', LC_ALL='C'))

    def test_reminder_cli_child_binds_home_and_drops_secrets_and_python_overrides(self):
        run = subprocess.run
        def probe(argv, **kwargs):
            self.assertEqual(argv[0], sys.executable)
            self.assertEqual(kwargs['env'], dict(PATH=os.defpath, HOME='/example/operator', LANG='C', HERMES_HOME='/example/active'))
            self.assertEqual(argv[-3:], ['gateway', 'attach', '--json'])
            return run([sys.executable, '-c', 'import os,json; print(json.dumps(dict(os.environ)))'], **kwargs)
        ctx = SimpleNamespace(state=SimpleNamespace(data_dir='/example/active/plugins/ownmachine'))
        with patch.dict(os.environ, self.parent, clear=True), patch.object(scheduler.subprocess, 'run', side_effect=probe):
            child = json.loads(scheduler.cli(ctx, 'gateway', 'attach', '--json'))
        self.assert_child_environment(child, dict(PATH=os.defpath, HOME='/example/operator', LANG='C',
                                    HERMES_HOME='/example/active'))

    def test_missing_optional_environment_variables_are_not_copied(self):
        with patch.dict(os.environ, {'UNDECLARED_SECRET': 'fixture'}, clear=True), \
                patch.object(scheduler.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok')) as run:
            ctx = SimpleNamespace(state=SimpleNamespace(data_dir='/example/active/plugins/ownmachine'))
            self.assertEqual(scheduler.cli(ctx, 'version'), 'ok')
        self.assertEqual(run.call_args.kwargs['env'], {'HERMES_HOME': '/example/active'})

    def test_missing_pillow_reports_actionable_error_before_capture_or_retirement(self):
        backend = Mock()
        with patch.dict(sys.modules, {'PIL': None, 'PIL.Image': None,
                                     'ownmachine.provider': SimpleNamespace(OwnMachineBackend=backend)}), \
                patch.object(setup, 'dispatch', return_value={'ok': True}) as dispatch:
            with self.assertRaisesRegex(ValueError, 'requires_pillow_install_declared_plugin_dependencies'):
                acceptance.finish(self.ctx, self.plan, apply=True)
        self.assertEqual([call.args[2] for call in dispatch.call_args_list], ['verify'])
        backend.assert_not_called()
        self.assertEqual(self.ctx.state.get(acceptance.KEY)['stage'], 'screenshot_required')
