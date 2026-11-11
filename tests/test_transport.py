import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
from ownmachine.config import Config
from ownmachine.transport import MCPTransport, TransportError

SERVER = '''import json,sys,time
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m: continue
 method=m['method']
 if method=='initialize': r={'protocolVersion':'2024-11-05'}
 elif method=='tools/list': r={'tools':[{'name':'test','inputSchema':{'properties':{}}}]}
 else:
  args=m['params']['arguments']
  if args.get('fault')=='drop': sys.exit(0)
  if args.get('fault')=='timeout': time.sleep(5)
  if args.get('fault')=='id': m['id']+=1
  if args.get('fault')=='large': print('x'*20000,flush=True);continue
  print(json.dumps({'jsonrpc':'2.0','method':'notifications/message','params':{}}),flush=True)
  r={'content':[{'type':'text','text':'ok'}]}
 print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':r}),flush=True)
'''
class TransportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  path=Path(self.tmp.name)/'server.py';path.write_text(SERVER)
  self.client=MCPTransport(Config(host_alias='test',action_timeout_seconds=1),[sys.executable,'-u',str(path)])
  self.addCleanup(self.client.stop)
 def test_handshake_discovery_notification_and_close(self):
  self.client.start();self.assertIn('test',self.client.tools)
  self.assertEqual(self.client.call('test',{})['content'][0]['text'],'ok')
  process=self.client.process;self.client.stop();self.assertIsNotNone(process.poll())
 def test_connection_faults_never_replay(self):
  for fault in ('drop','timeout','id','large'):
   with self.subTest(fault=fault):
    self.client.start();self.client.MAX_FRAME=10000
    seq=self.client.sequence
    with self.assertRaisesRegex(TransportError,'transport_outcome_unknown'):
     self.client.call('test',{'fault':fault})
    self.assertEqual(self.client.sequence,seq+1)
    self.assertIsNone(self.client.process)
 def test_unknown_tool_is_not_dispatched(self):
  self.client.start();seq=self.client.sequence
  with self.assertRaises(TransportError):self.client.call('unknown',{})
  self.assertEqual(self.client.sequence,seq)

class DeadlineTests(unittest.TestCase):
 def test_expired_deadline_rejects_buffered_reply(self):
  import time
  client=MCPTransport(Config(host_alias='test'))
  client.buffer.extend(b'{"jsonrpc":"2.0","id":1,"result":{}}\n')
  with self.assertRaisesRegex(TransportError,'transport_timeout'):
   client._read(time.monotonic()-1)
 def test_expired_deadline_rejects_even_ready_fd(self):
  import time
  import selectors
  client=MCPTransport(Config(host_alias='test'))
  with tempfile.TemporaryFile() as ready:
   with self.assertRaisesRegex(TransportError,'transport_timeout'):
    client._wait(ready,selectors.EVENT_WRITE,time.monotonic()-1)
