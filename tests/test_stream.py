import io
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import json
sys.path.insert(0,str(Path(__file__).parents[1]/'viewer'))
sys.path.insert(0,str(Path(__file__).parents[1]/'plugin'))
from stream import Upstream, WebSocket, StreamError, InputGate, client_message, websocket_accept
from ownmachine.lease import Lease

class StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.lease=Lease(Path(self.temp.name)/'lease.db',timeout=1)
        self.sent=[]
    def gate(self,controller='human'):
        state=self.lease.transfer(controller)
        return InputGate(self.lease,state['generation'],self.sent.append)
    def test_all_input_denied_without_human_lease(self):
        for state in ('paused','agent'):
            gate=self.gate(state)
            self.assertFalse(gate.dispatch(4,b'\x04\x01\x00\x00\x00\x00\x00a'))
            self.assertFalse(gate.dispatch(5,b'\x05\x01\x00\x00\x00\x00'))
        self.assertFalse(self.sent)
    def test_stale_generation_and_readonly_refuse_input(self):
        gate=self.gate();self.lease.transfer('human')
        self.assertFalse(gate.dispatch(5,b'\x05\x00\x00\x01\x00\x02'))
        gate=self.gate();gate.enabled=False
        self.assertFalse(gate.dispatch(5,b'\x05\x00\x00\x01\x00\x02'))
        self.assertFalse(self.sent)
    def test_held_key_blocks_transfer_and_disconnect_releases(self):
        gate=self.gate();gate.dispatch(4,b'\x04\x01\x00\x00\x00\x00\xff\xe3')
        self.assertTrue(gate.active);self.assertTrue(self.lease.status()['pending'])
        finished=threading.Event()
        worker=threading.Thread(target=lambda:(self.lease.transfer('agent'),finished.set()));worker.start()
        self.assertFalse(finished.wait(.1))
        gate.release();worker.join(2)
        self.assertTrue(finished.is_set());self.assertFalse(self.lease.status()['pending'])
        self.assertEqual(self.sent[-1],b'\x04\x00\x00\x00\x00\x00\xff\xe3')
    def test_drag_holds_lock_until_button_release(self):
        gate=self.gate();gate.dispatch(5,b'\x05\x01\x00\x01\x00\x02')
        self.assertTrue(gate.active)
        gate.dispatch(5,b'\x05\x00\x00\x03\x00\x04')
        self.assertFalse(gate.active);self.assertFalse(self.lease.status()['pending'])
    def test_write_failure_never_replays_and_leaves_pending(self):
        gate=self.gate()
        def broken(data):self.sent.append(data);raise OSError('broken')
        gate.send=broken
        with self.assertRaises(OSError):gate.dispatch(5,b'\x05\x00\x00\x01\x00\x02')
        self.assertTrue(self.lease.status()['pending']);self.assertEqual(len(self.sent),1)
        self.assertFalse(gate.dispatch(5,b'\x05\x00\x00\x01\x00\x02'))
        self.assertEqual(len(self.sent),1)
    def test_clipboard_and_privileged_messages_not_forwarded(self):
        class Reader:
            def __init__(self,data):self.data=io.BytesIO(data)
            def read(self,n):return self.data.read(n)
        self.assertEqual(client_message(Reader(b'\x06\x00\x00\x00'+struct.pack('>I',3)+b'abc')),(6,b''))
        for kind in (250,251,255):
            with self.assertRaises(StreamError):client_message(Reader(bytes([kind])))
    def test_rfb_frames_can_span_websocket_fragments(self):
        a,b=socket.socketpair();self.addCleanup(a.close);self.addCleanup(b.close)
        def frame(data,opcode,final):
            mask=b'abcd';return bytes([(128 if final else 0)|opcode,128|len(data)])+mask+bytes(v^mask[i%4] for i,v in enumerate(data))
        a.sendall(frame(b'\x04\x01\x00',2,False)+frame(b'\x00\x00\x00\x00a',0,True))
        kind,data=client_message(WebSocket(b));self.assertEqual(kind,4);self.assertEqual(len(data),8)
    def test_unmasked_and_text_websocket_frames_refused(self):
        for payload in (b'\x82\x01a',b'\x81\x81abcd\x00'):
            a,b=socket.socketpair()
            try:
                a.sendall(payload)
                with self.assertRaises(StreamError):WebSocket(b).read(1)
            finally:a.close();b.close()
    def test_websocket_key_validation(self):
        self.assertEqual(websocket_accept('dGhlIHNhbXBsZSBub25jZQ=='),'s3pPLMBiTxaQ9kYGzzhZRbK+xOo=')
        with self.assertRaises(StreamError):websocket_accept('bad')
    def test_malformed_keys_and_extended_pointer_refused(self):
        for payload in (b'\x04\x02\x00\x00\x00\x00\x00a',
                        b'\x04\x01\x01\x00\x00\x00\x00a',
                        b'\x05\x80\x00\x00\x00\x00'):
            with self.assertRaises(StreamError):client_message(io.BytesIO(payload))

    def test_upstream_name_length_keeps_rfb_messages_aligned(self):
        # Exercise the handshake output consumed by a real RFB client. A stale
        # seven-byte brand length leaves "ine" as bogus server message bytes.
        upstream_name=b'private-host-name'
        geometry=struct.pack('>HH',1900,1200)+bytes(16)
        wire=io.BytesIO(json.dumps({'password':'fixture'}).encode()+b'\n'+
            b'RFB 003.008\n'+b'\x01\x02'+bytes(16)+bytes(4)+
            geometry+struct.pack('>I',len(upstream_name))+upstream_name)
        def read(instance,n,deadline):
            result=wire.read(n)
            if len(result)!=n:raise EOFError()
            return result
        cipher=SimpleNamespace(DES=SimpleNamespace(MODE_ECB=1,new=lambda *a:SimpleNamespace(encrypt=lambda data:bytes(16))))
        with patch.dict(sys.modules,{'Crypto':SimpleNamespace(),'Crypto.Cipher':cipher}), \
             patch('stream.subprocess.Popen',return_value=Mock()), \
             patch.object(Upstream,'read',read),patch.object(Upstream,'send'):
            connection=Upstream(SimpleNamespace(connect_timeout_seconds=1,ssh_argv=lambda operation:['ssh']))
        framed=io.BytesIO(connection.header+b'\x00\x00\x00\x00')
        header=framed.read(24)
        self.assertEqual(header[:20],geometry)
        self.assertEqual(framed.read(struct.unpack('>I',header[20:])[0]),b'OwnMachine')
        self.assertEqual(framed.read(),bytes(4))
        self.assertNotIn(upstream_name,connection.header)
