import io
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine import onboarding as o


class Context:
    def __init__(self, settings=None):
        self.settings = deepcopy(settings or {})
        self.cli = None
        self.slash = None
    def get_config(self, key, default=None):
        return self.settings.get(key, default)
    def set_config(self, key, value):
        self.settings[key] = value
    def register_cli_command(self, **kwargs):
        self.cli = kwargs
    def register_command(self, name, **kwargs):
        self.slash = kwargs['handler']


def args(*argv):
    p = o.Parser()
    o.add_arguments(p)
    return p.parse_args(argv)


class OnboardingCommandsTests(unittest.TestCase):
    def setUp(self):
        capture = redirect_stdout(io.StringIO())
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def test_registration_is_side_effect_free_and_has_all_entrypoints(self):
        ctx = Context()
        with patch.object(o, 'diagnose', side_effect=AssertionError('network')), patch('builtins.input', side_effect=AssertionError('prompt')):
            o.register_commands(ctx)
        self.assertEqual(ctx.settings, {})
        self.assertEqual(ctx.cli['name'], 'ownmachine')
        self.assertIn('hermes ownmachine doctor', ctx.slash('help'))
        self.assertIn('NEEDS INPUT', ctx.slash('setup'))

    def test_noninteractive_never_prompts_or_saves(self):
        ctx = Context(); o.register_commands(ctx)
        with patch('sys.stdin.isatty', return_value=False), patch('builtins.input', side_effect=AssertionError('prompt')):
            self.assertEqual(ctx.cli['handler_fn'](args('setup')), 2)
            ctx.slash('setup --target remote')
        self.assertEqual(ctx.settings, {})

    def test_resume_keeps_resources_and_does_not_create_directories(self):
        ctx = Context()
        with tempfile.TemporaryDirectory() as folder:
            absent = str(Path(folder) / 'not-created')
            o.setup(ctx, args('setup', '--target', 'remote', '--storage-dir', absent,
                             '--memory-gb', '12', '--display', '1900x1200', '--save'))
            result = o.setup(ctx, args('setup'))
            self.assertEqual(result['plan']['memory_gb'], 12)
            self.assertFalse(Path(absent).exists())
            self.assertFalse(result['connection_saved'])
            self.assertEqual(result['stage'], 'planned')

    def test_existing_connection_requires_explicit_connect_and_replace(self):
        ctx = Context({'unrelated': 'keep'})
        values = ['setup', '--target', 'existing', '--host-alias', 'example-mac', '--control-dir', '/example/control']
        o.setup(ctx, args(*values, '--save'))
        self.assertNotIn('host_alias', ctx.settings)
        o.setup(ctx, args(*values, '--connect'))
        self.assertEqual(ctx.settings['host_alias'], 'example-mac')
        self.assertEqual(ctx.settings['unrelated'], 'keep')
        with self.assertRaises(o.InputError):
            o.setup(ctx, args('setup', '--host-alias', 'different', '--connect'))
        self.assertEqual(ctx.settings['host_alias'], 'example-mac')
        o.setup(ctx, args('setup', '--host-alias', 'different', '--connect', '--replace'))
        self.assertEqual(ctx.settings['host_alias'], 'different')

    def test_partial_connection_write_rolls_back(self):
        ctx = Context({'host_alias': 'old', 'vm_name': 'oldvm', 'control_dir': '/old'})
        write = ctx.set_config
        failed = False
        def fail_once(key, value):
            nonlocal failed
            if key == 'vm_name' and not failed:
                failed = True
                raise OSError('disk error')
            write(key, value)
        ctx.set_config = fail_once
        with self.assertRaises(OSError):
            o.setup(ctx, args('setup', '--target', 'existing', '--host-alias', 'new',
                             '--vm-name', 'newvm', '--control-dir', '/new', '--connect', '--replace'))
        self.assertEqual(ctx.settings, {'host_alias': 'old', 'vm_name': 'oldvm', 'control_dir': '/old'})

    def test_remote_plan_does_not_inspect_local_capacity(self):
        with patch.object(o.shutil, 'disk_usage', side_effect=AssertionError('wrong host')):
            report = o.setup(Context(), args('setup', '--target', 'remote', '--storage-dir', '/vm'))
        self.assertTrue(any(x['status'] == 'pending' for x in report['checks']))

    def test_local_preflight_blocks_wrong_host_and_low_storage(self):
        with patch.object(o.platform, 'system', return_value='Linux'):
            report = o.setup(Context(), args('setup', '--target', 'local'))
            self.assertFalse(report['ok'])
        with tempfile.TemporaryDirectory() as folder, patch.object(o.shutil, 'disk_usage') as usage:
            usage.return_value.free = 1024 ** 3
            report = o.setup(Context(), args('setup', '--target', 'local', '--storage-dir', folder, '--min-free-gb', '2'))
            self.assertFalse(report['ok'])

    def test_invalid_and_injected_values_never_saved(self):
        for options in [('--host-alias', '-oProxyCommand=bad'), ('--memory-gb', '0'),
                        ('--storage-dir', 'relative'), ('--display', 'bad'), ('--control-dir', '/a\nb')]:
            ctx = Context()
            with self.assertRaises(ValueError):
                o.setup(ctx, args('setup', '--target', 'remote', '--save', *options))
            self.assertEqual(ctx.settings, {})
        ctx = Context({'setup_plan': {'schema_version': 99}})
        with self.assertRaises(o.InputError): o.setup(ctx, args('setup'))

    def test_doctor_is_read_only_and_returns_failure(self):
        ctx = Context(); o.register_commands(ctx)
        before = deepcopy(ctx.settings)
        text, code = o.execute(ctx, args('doctor'))
        self.assertEqual(code, 1)
        self.assertIn('invalid_configuration', text)
        self.assertEqual(before, ctx.settings)
        self.assertIn('NEEDS ATTENTION', ctx.slash('doctor'))

    def test_chat_help_and_errors_do_not_exit_session(self):
        ctx = Context(); o.register_commands(ctx)
        with patch('builtins.input', side_effect=AssertionError('prompt')):
            self.assertIn('terminal', ctx.slash('setup --help'))
            self.assertIn('Invalid', ctx.slash('setup --unknown'))
            self.assertIn('invalid', ctx.slash('setup "'))

    def test_terminal_wizard_preview_and_decline(self):
        ctx = Context(); o.register_commands(ctx)
        with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True), patch('builtins.input', side_effect=['remote', '', '', '/vm', 'demo', 'no']):
            self.assertEqual(ctx.cli['handler_fn'](args('setup')), 0)
        self.assertEqual(ctx.settings, {})

try:
    import hermes_cli
    HERMES_AVAILABLE = True
except ImportError:
    HERMES_AVAILABLE = False


@unittest.skipUnless(HERMES_AVAILABLE, 'Requires installed Hermes public provider contract')
class HermesOnboardingTests(unittest.TestCase):
    def test_real_cli_and_slash_discovery_resume_and_read_only_doctor(self):
        import json
        import os
        import shutil
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'profile'; home.mkdir()
            shutil.copytree(Path(__file__).parents[1]/'plugin', home/'plugins/ownmachine',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            (home/'config.yaml').write_text(json.dumps({'plugins': {'isolation': 'in_process',
                'enabled': ['ownmachine'], 'entries': {'ownmachine': {'enabled': True}}}}))
            env = {**os.environ, 'HERMES_HOME': str(home)}
            env.pop('SSH_AUTH_SOCK', None)
            def cli(*argv):
                code = 'import sys; from hermes_cli.main import main; sys.argv=["hermes",*sys.argv[1:]]; raise SystemExit(main())'
                return subprocess.run([sys.executable, '-c', code, 'ownmachine', *argv],
                                      env=env, capture_output=True, text=True, timeout=120)
            first = cli('setup', '--json')
            self.assertEqual(first.returncode, 2, first.stderr)
            self.assertEqual(json.loads(first.stdout)['stage'], 'needs_input')
            saved = cli('setup', '--target', 'remote', '--memory-gb', '12', '--save', '--json')
            self.assertEqual(saved.returncode, 0, saved.stderr)
            self.assertTrue(json.loads(saved.stdout)['saved'])
            resumed = cli('setup', '--json')
            self.assertEqual(json.loads(resumed.stdout)['plan']['memory_gb'], 12)
            before = (home/'config.yaml').read_bytes()
            doctor = cli('doctor', '--json')
            self.assertEqual(doctor.returncode, 1, doctor.stderr)
            self.assertEqual(json.loads(doctor.stdout)['checks'][0]['code'], 'invalid_configuration')
            self.assertEqual((home/'config.yaml').read_bytes(), before)
            code = ('from hermes_cli.plugins import get_plugin_command_handler; '
                    'h=get_plugin_command_handler("ownmachine"); assert h is not None; '
                    'assert "PLANNED" in h("setup"); assert "NEEDS ATTENTION" in h("doctor"); '
                    'print("slash discovery passed")')
            slash = subprocess.run([sys.executable, '-c', code], env=env,
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(slash.returncode, 0, slash.stderr)
            # The host isolation mode must still expose chat setup; CLI requires in-process.
            # Use Hermes's own writer instead of assuming its YAML serialization.
            code = 'from hermes_cli.config import load_config, save_config; c=load_config(); c["plugins"]["isolation"]="host"; save_config(c)'
            result = subprocess.run([sys.executable, '-c', code], env=env,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            code = ('from hermes_cli.plugins import get_plugin_command_handler; '
                    'h=get_plugin_command_handler("ownmachine"); assert h is not None; '
                    'assert "in_process" in h("setup"); print("host chat setup passed")')
            result = subprocess.run([sys.executable, '-c', code], env=env,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
