"""Real subprocess transport + durable lease + installed Hermes ABC; no hardware."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'plugin'))
from ownmachine.config import Config
from ownmachine.lease import LeaseError
from ownmachine.transport import MCPTransport
try:
    from ownmachine.provider import OwnMachineBackend
except ModuleNotFoundError:
    OwnMachineBackend = None


@unittest.skipIf(OwnMachineBackend is None, 'Requires installed Hermes public provider contract')
class RecoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.fault('none')
        self.config = Config(host_alias='synthetic-fixture', control_dir=str(self.root / 'control'), action_timeout_seconds=1)
        self.transport = MCPTransport(self.config, [sys.executable, '-u', str(Path(__file__).parent / 'fixtures/recovery_server.py'), str(self.root)])
        self.backend = OwnMachineBackend(self.config, transport=self.transport)
        self.addCleanup(self.backend.stop)
        self.backend.start(); self.backend.lease.transfer('agent')
    def fault(self, mode):
        (self.root / 'fault').write_text(mode)
    def writes(self):
        return (self.root / 'events').read_text().splitlines().count('type_text')
    def capture(self):
        self.backend.capture(mode='ax', app='Fixture')
    def test_lost_reply_reconnect_never_replays_and_requires_review(self):
        for mode in ('drop', 'timeout'):
            with self.subTest(mode=mode):
                self.fault('none'); self.backend.lease.transfer('agent'); self.capture()
                previous = self.writes(); self.fault(mode)
                self.assertEqual(self.backend.type_text('synthetic').code, 'transport_outcome_unknown')
                self.assertEqual(self.writes(), previous + 1)
                self.assertIsNone(self.transport.process)
                self.assertTrue(self.backend.lease.status()['pending'])
                self.fault('none'); self.capture()
                self.assertEqual(self.backend.type_text('must-not-replay').code, 'transport_outcome_unknown')
                self.assertEqual(self.writes(), previous + 1)
                with self.assertRaises(LeaseError): self.backend.lease.transfer('agent', acknowledge=False)
                self.backend.lease.transfer('agent', acknowledge=True)
                self.assertEqual(self.backend.type_text('stale').code, 'stale_target')
                self.capture(); self.assertTrue(self.backend.type_text('new-action').ok)
                self.assertEqual(self.writes(), previous + 2)
    def test_reconnect_checks_tools_and_closes_incompatible_stream(self):
        self.capture(); self.fault('drop'); self.backend.type_text('synthetic')
        self.fault('missing_tools')
        with self.assertRaisesRegex(RuntimeError, 'incompatible_driver_tools'): self.capture()
        self.assertIsNone(self.transport.process); self.assertTrue(self.backend.lease.status()['pending'])
        self.assertEqual(self.writes(), 1)
    def test_reconnect_rejects_failed_session_without_dispatch(self):
        self.capture(); self.fault('drop'); self.backend.type_text('synthetic')
        self.fault('session_error')
        with self.assertRaisesRegex(RuntimeError, 'driver_session_failed'): self.capture()
        self.assertIsNone(self.transport.process); self.assertTrue(self.backend.lease.status()['pending'])
        self.assertEqual(self.writes(), 1)
    def test_thirty_cycles_and_human_handoff_have_no_duplicate_writes(self):
        for cycle in range(30):
            self.capture(); self.assertTrue(self.backend.type_text('synthetic').ok)
            self.assertEqual(self.writes(), cycle + 1)
            self.backend.lease.transfer('human')
            self.assertEqual(self.backend.type_text('blocked').code, 'human_takeover')
            self.assertEqual(self.writes(), cycle + 1)
            self.backend.lease.transfer('agent')
            self.assertEqual(self.backend.type_text('stale').code, 'stale_target')
        self.assertFalse(self.backend.lease.status()['pending'])
