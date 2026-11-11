import importlib.util
import json
import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine.config import Config
from ownmachine.lease import Lease, LeaseError


def held_write(path, generation, started, release):
    with Lease(path).write(generation):
        started.set()
        release.wait(5)


def takeover(path, finished):
    Lease(path).transfer('human')
    finished.set()


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'lease.db'
        self.lease = Lease(self.path)

    def test_missing_state_pauses(self):
        self.assertEqual(self.lease.status()['controller'], 'paused')
        with self.assertRaisesRegex(LeaseError, 'paused'):
            with self.lease.write(0): self.fail('must not dispatch')

    def test_resume_requires_fresh_generation(self):
        old = self.lease.transfer('agent')['generation']
        self.lease.transfer('human')
        current = self.lease.transfer('agent')['generation']
        with self.assertRaisesRegex(LeaseError, 'stale_target'):
            with self.lease.write(old): self.fail('must not dispatch')
        with self.lease.write(current): pass
        self.assertFalse(self.lease.status()['pending'])

    def test_unknown_write_is_not_replayed(self):
        generation = self.lease.transfer('agent')['generation']
        with self.assertRaises(TimeoutError):
            with self.lease.write(generation): raise TimeoutError('simulated timeout')
        with self.assertRaisesRegex(LeaseError, 'transport_outcome_unknown'):
            with Lease(self.path).write(generation): self.fail('must not replay')

    def test_human_refuses_write(self):
        generation = self.lease.transfer('human')['generation']
        with self.assertRaisesRegex(LeaseError, 'human_takeover'):
            with self.lease.write(generation): self.fail('must not dispatch')

    def test_takeover_waits_for_inflight_write(self):
        generation = self.lease.transfer('agent')['generation']
        ctx = multiprocessing.get_context('spawn')
        started, release, finished = ctx.Event(), ctx.Event(), ctx.Event()
        writer = ctx.Process(target=held_write, args=(self.path, generation, started, release))
        human = ctx.Process(target=takeover, args=(self.path, finished))
        writer.start()
        try:
            self.assertTrue(started.wait(5))
            human.start()
            self.assertFalse(finished.wait(.2))
            release.set()
            self.assertTrue(finished.wait(5))
        finally:
            release.set()
            writer.join(5)
            if human.pid: human.join(5)
        self.assertEqual(writer.exitcode, 0)
        self.assertEqual(human.exitcode, 0)
        self.assertEqual(self.lease.status()['controller'], 'human')

    def test_crashed_writer_leaves_unknown_marker(self):
        generation = self.lease.transfer('agent')['generation']
        ctx = multiprocessing.get_context('spawn')
        started, release = ctx.Event(), ctx.Event()
        writer = ctx.Process(target=held_write, args=(self.path, generation, started, release))
        writer.start()
        try:
            self.assertTrue(started.wait(5))
        finally:
            writer.terminate()
            writer.join(5)
        self.assertTrue(self.lease.status()['pending'])
        with self.assertRaisesRegex(LeaseError, 'transport_outcome_unknown'):
            with self.lease.write(generation): self.fail('must not dispatch')

    def test_command_injection_rejected(self):
        for bad in ['host;id', '$(id)', '`id`', 'a\nb', '../host', '-oProxyCommand=id', 'host name', '192.0.2.1']:
            for field in ['host_alias', 'vm_name']:
                with self.subTest(value=bad, field=field), self.assertRaises(ValueError):
                    Config(**dict({'host_alias': 'ownmachine-studio'}, **{field: bad})).ssh_argv('mcp')

    def test_transport_is_fixed_and_noninteractive(self):
        argv = Config(host_alias='ownmachine-studio').ssh_argv('mcp')
        self.assertIn('StrictHostKeyChecking=yes', argv)
        self.assertIn('BatchMode=yes', argv)
        self.assertIn('ForwardAgent=no', argv)
        self.assertEqual(argv[-5:], ['ownmachine-studio', 'ownmachine-host', 'mcp', '--vm', 'ownmachine'])
        with self.assertRaises(ValueError): Config(host_alias='ownmachine-studio').ssh_argv('delete')

    def test_timeout_validation(self):
        for bad in [0, -1, 121, True, '15']:
            with self.assertRaises(ValueError):
                Config(host_alias='ownmachine-studio', action_timeout_seconds=bad).validate()

    def test_registration_is_readonly_and_truthful(self):
        spec = importlib.util.spec_from_file_location('test_ownmachine_plugin', Path(__file__).parents[1] / 'plugin/__init__.py', submodule_search_locations=[str(Path(__file__).parents[1] / 'plugin')])
        module = importlib.util.module_from_spec(spec)
        import sys
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        class Context:
            def get_config(self, key, default=None): return default
            def register_tool(self, **kwargs): self.tool = kwargs
            def register_middleware(self, kind, callback): self.middleware = (kind, callback)
        context = Context()
        module.register(context)
        self.assertEqual(context.tool['name'], 'ownmachine_status')
        self.assertEqual(context.middleware[0], 'tool_execution')
        status = json.loads(context.tool['handler']({}))
        self.assertFalse(status['native_provider_ready'])
        self.assertFalse(status['configured'])
        self.assertIsNone(status['host_reachable'])


if __name__ == '__main__': unittest.main()
