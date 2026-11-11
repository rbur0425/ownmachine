import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from ownmachine import reminder_scheduler as s


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.ctx=SimpleNamespace(state=SimpleNamespace(data_dir=Path('/profile/plugin-data/ownmachine')))
        self.attach=dict(url='ws://127.0.0.1:12345/api/ws',protocol='hermes-gateway-v1',
                         protocols=['hermes-gateway-v1','ticket-test'],client_code_sha='revision',
                         endpoint=dict(code_sha='revision',profile_id='/profile'))

    def test_public_rpc_and_notifications(self):
        socket=MagicMock();socket.subprotocol='hermes-gateway-v1'
        socket.recv.side_effect=[json.dumps({'method':'notice'}),json.dumps(dict(id=1,result=dict(success=True,jobs=[])))]
        with patch.object(s,'cli',return_value=json.dumps(self.attach)),patch('websockets.sync.client.connect') as connect:
            connect.return_value.__enter__.return_value=socket
            self.assertEqual(s.jobs(self.ctx),[])
            self.assertNotIn('origin',connect.call_args.kwargs)
            self.assertIsNone(connect.call_args.kwargs['proxy'])
            sent=json.loads(socket.send.call_args.args[0]);self.assertEqual(sent['method'],'cron.manage')
            self.assertTrue(sent['params']['include_disabled'])

    def test_identity_mismatches_never_connect_or_expose_ticket(self):
        for change in [dict(url='ws://example.org/api/ws'),dict(url='ws://127.0.0.1/api/ws?token=secret'),
                       dict(client_code_sha='other'),dict(endpoint=dict(code_sha='revision',profile_id='/other'))]:
            with self.subTest(change=change),patch.object(s,'cli',return_value=json.dumps(dict(self.attach,**change))),patch('websockets.sync.client.connect') as connect:
                with self.assertRaisesRegex(ValueError,'scheduler_unavailable') as error:s.jobs(self.ctx)
                self.assertNotIn('ticket-test',str(error.exception));connect.assert_not_called()

    def test_missing_method_fails_closed(self):
        socket=MagicMock();socket.subprotocol='hermes-gateway-v1'
        socket.recv.return_value=json.dumps(dict(id=1,error=dict(code=-32601,message='secret')))
        with patch.object(s,'cli',return_value=json.dumps(self.attach)),patch('websockets.sync.client.connect') as connect:
            connect.return_value.__enter__.return_value=socket
            with self.assertRaisesRegex(ValueError,'scheduler_unavailable'):s.jobs(self.ctx)

    def test_total_receive_deadline(self):
        socket=MagicMock();socket.subprotocol='hermes-gateway-v1'
        socket.recv.return_value=json.dumps({'method':'notice'})
        with patch.object(s,'cli',return_value=json.dumps(self.attach)),patch('websockets.sync.client.connect') as connect,patch.object(s.time,'monotonic',side_effect=[0,1,16]):
            connect.return_value.__enter__.return_value=socket
            with self.assertRaises(ValueError):s.jobs(self.ctx)
            self.assertEqual(socket.recv.call_count,1)
