"""Authenticated RFB 3.8 bridge. No upstream password reaches the browser.

Only standard client messages are admitted. Every key/pointer event passes the
shared human lease. A held key/button keeps that transaction open until release;
control transfer cannot race a pressed modifier or drag. Unknown writes fail closed.
"""
import base64
import hashlib
import json
import os
import selectors
import socket
import sqlite3
import struct
import subprocess
import threading
import time
from ownmachine.lease import Lease, LeaseError


class StreamError(RuntimeError): pass


def exact_socket(sock,n):
    data=bytearray()
    while len(data)<n:
        part=sock.recv(n-len(data))
        if not part:raise EOFError()
        data.extend(part)
    return bytes(data)


class WebSocket:
    def __init__(self,sock):
        self.sock=sock;self.buffer=bytearray();self.lock=threading.Lock();self.fragment=False
    def send(self,data,opcode=2):
        header=bytes([0x80|opcode])
        n=len(data)
        header+=bytes([n]) if n<126 else b'\x7e'+struct.pack('>H',n) if n<65536 else b'\x7f'+struct.pack('>Q',n)
        with self.lock:self.sock.sendall(header+data)
    def read(self,n):
        while len(self.buffer)<n:
            a,b=exact_socket(self.sock,2)
            final=bool(a&128);opcode=a&15;size=b&127
            if a&0x70 or not b&128:raise StreamError('invalid_websocket')
            if size==126:size=struct.unpack('>H',exact_socket(self.sock,2))[0]
            elif size==127:size=struct.unpack('>Q',exact_socket(self.sock,8))[0]
            if size>65536 or len(self.buffer)+size>131072:raise StreamError('message_too_large')
            mask=exact_socket(self.sock,4);raw=exact_socket(self.sock,size)
            data=bytes(value^mask[i%4] for i,value in enumerate(raw))
            if opcode>=8:
                if not final or size>125:raise StreamError('invalid_websocket')
                if opcode==8:raise EOFError()
                if opcode==9:self.send(data,10)
                elif opcode!=10:raise StreamError('invalid_websocket')
                continue
            if opcode not in (0,2) or (opcode==0)!=self.fragment:raise StreamError('invalid_websocket')
            self.fragment=not final;self.buffer.extend(data)
        result=bytes(self.buffer[:n]);del self.buffer[:n];return result
    def close(self):
        try:self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:pass


def websocket_accept(key):
    try:
        if len(base64.b64decode(key,validate=True))!=16:raise ValueError()
    except (ValueError,TypeError):raise StreamError('invalid_websocket_key') from None
    return base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()


class Upstream:
    def __init__(self,config):
        self.process=None
        try:
            from Crypto.Cipher import DES
            env={k:os.environ[k] for k in ('PATH','HOME','SSH_AUTH_SOCK','LANG') if k in os.environ}
            self.process=subprocess.Popen(config.ssh_argv('vnc'),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,env=env,bufsize=0,start_new_session=True)
            metadata=bytearray()
            deadline=time.monotonic()+config.connect_timeout_seconds+5
            while not metadata.endswith(b'\n'):
                if len(metadata)>4096:raise StreamError('invalid_metadata')
                metadata.extend(self.read(1,deadline))
            password=json.loads(metadata)['password']
            if not isinstance(password,str) or not 1<=len(password)<=256:raise StreamError('invalid_metadata')
            version=self.read(12,deadline)
            if not version.startswith(b'RFB 003.'):raise StreamError('unsupported_rfb_version')
            self.send(b'RFB 003.008\n')
            count=self.read(1,deadline)[0]
            if count==0 or 2 not in self.read(count,deadline):raise StreamError('vnc_authentication_required')
            self.send(b'\x02')
            challenge=self.read(16,deadline)
            key=password.encode('latin-1')[:8].ljust(8,b'\x00')
            key=bytes(int(f'{value:08b}'[::-1],2) for value in key)
            self.send(DES.new(key,DES.MODE_ECB).encrypt(challenge))
            del password,key,metadata
            if self.read(4,deadline)!=b'\x00'*4:raise StreamError('vnc_authentication_failed')
            self.send(b'\x01') # Always shared: never disconnect another trusted viewer.
            header=self.read(24,deadline);length=struct.unpack('>I',header[20:24])[0]
            if length>4096:raise StreamError('invalid_server_name')
            self.read(length,deadline)
            name=b'OwnMachine'
            self.header=header[:20]+struct.pack('>I',len(name))+name
        except BaseException:
            self.close();raise
    def read(self,n,deadline):
        data=bytearray()
        with selectors.DefaultSelector() as poll:
            poll.register(self.process.stdout,selectors.EVENT_READ)
            while len(data)<n:
                if not poll.select(max(0,deadline-time.monotonic())):raise StreamError('vnc_timeout')
                part=os.read(self.process.stdout.fileno(),n-len(data))
                if not part:raise EOFError()
                data.extend(part)
        return bytes(data)
    def send(self,data):
        # Bound even a wedged SSH stdin. Input is never replayed.
        fd=self.process.stdin.fileno();os.set_blocking(fd,False)
        deadline=time.monotonic()+5
        with selectors.DefaultSelector() as poll:
            poll.register(fd,selectors.EVENT_WRITE)
            while data:
                if not poll.select(max(0,deadline-time.monotonic())):raise StreamError('vnc_write_timeout')
                try:data=data[os.write(fd,data):]
                except BlockingIOError:continue
    def close(self):
        if self.process:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
            for f in (self.process.stdin,self.process.stdout):f.close()
            self.process=None


def client_message(ws):
    kind=ws.read(1)[0]
    lengths={0:19,3:9,4:7,5:5,150:9}
    if kind in lengths:
        data=bytes([kind])+ws.read(lengths[kind])
        if kind==4 and (data[1] not in (0,1) or data[2:4]!=b'\x00\x00'):raise StreamError('invalid_key_event')
        if kind==5 and data[1]&128:raise StreamError('extended_pointer_refused')
        return kind,data
    if kind==2:
        head=ws.read(3);count=struct.unpack('>H',head[1:])[0]
        if count>256:raise StreamError('too_many_encodings')
        return kind,b'\x02'+head+ws.read(count*4)
    if kind==6:
        head=ws.read(7);size=abs(struct.unpack('>i',head[3:])[0])
        if size>65536:raise StreamError('clipboard_too_large')
        ws.read(size);return kind,b'' # Clipboard changes are not admitted.
    # Refuse extended keys, resize, file transfer and vendor power commands.
    raise StreamError('unsupported_rfb_message')


class InputGate:
    def __init__(self,lease,generation,send,enabled=True):
        self.lease=lease;self.generation=generation;self.send=send;self.enabled=enabled
        self.keys=set();self.buttons=0;self.position=b'\x00'*4;self.transaction=None;self.since=0;self.lock=threading.RLock()
    @property
    def active(self):return self.transaction is not None
    def _finish(self,error=None):
        transaction=self.transaction;self.transaction=None
        if transaction:
            if error:transaction.__exit__(type(error),error,None)
            else:transaction.__exit__(None,None,None)
    def dispatch(self,kind,data):
        with self.lock:return self._dispatch(kind,data)
    def _dispatch(self,kind,data):
        if not self.enabled:return False
        if kind==4 and data[1] and len(self.keys)>=256:raise StreamError('too_many_held_keys')
        if not self.transaction:
            transaction=self.lease.write(self.generation,controller='human')
            try:transaction.__enter__()
            except LeaseError:return False
            self.transaction=transaction;self.since=time.monotonic()
        try:
            self.send(data)
            if kind==4:
                key=data[4:8]
                if data[1]:self.keys.add(key)
                else:self.keys.discard(key)
            else:self.buttons=data[1];self.position=data[2:6]
            if not self.keys and not self.buttons:self._finish()
            return True
        except BaseException as error:
            self._finish(error);raise
    def release(self):
        with self.lock:return self._release()
    def _release(self):
        if self.transaction:
            try:
                for key in self.keys:self.send(b'\x04\x00\x00\x00'+key)
                if self.buttons:self.send(b'\x05\x00'+self.position)
                self.keys.clear();self.buttons=0;self._finish()
            except BaseException as error:self._finish(error);raise


class Bridge:
    def __init__(self,viewer,ws,upstream):
        self.viewer=viewer;self.ws=ws;self.upstream=upstream
        self.generation=viewer.lease.status()['generation']
        self.done=threading.Event();self.closed=threading.Event();self.gate=None
    def stop(self):self.done.set();self.ws.close()
    def run(self):
        try:
            self.ws.sock.settimeout(10)
            self.ws.send(b'RFB 003.008\n')
            if self.ws.read(12)!=b'RFB 003.008\n':raise StreamError('unsupported_rfb_version')
            self.ws.send(b'\x01\x01') # Authentication already enforced by HTTP cookie + Origin.
            if self.ws.read(1)!=b'\x01':raise StreamError('invalid_security_type')
            self.ws.send(b'\x00'*4)
            self.ws.read(1);self.ws.send(self.upstream.header)
            self.ws.sock.settimeout(None)
            lease=Lease(self.viewer.directory/'lease.db',timeout=1)
            self.gate=InputGate(lease,self.generation,self.upstream.send,self.viewer.allow_input)
            def pump():
                try:
                    with selectors.DefaultSelector() as poll:
                        poll.register(self.upstream.process.stdout,selectors.EVENT_READ)
                        while not self.done.is_set():
                            if lease.status()['generation']!=self.generation:break
                            if self.gate.active and time.monotonic()-self.gate.since>30:break
                            if poll.select(.25):
                                data=os.read(self.upstream.process.stdout.fileno(),65536)
                                if not data:break
                                self.ws.send(data)
                except (OSError,EOFError,LeaseError,sqlite3.Error):pass
                finally:self.stop()
            thread=threading.Thread(target=pump,daemon=True);thread.start()
            while not self.done.is_set():
                kind,data=client_message(self.ws)
                if kind in (4,5):
                    with self.viewer.stream_lock:
                        owner=self.viewer.input_owner
                        if owner not in (None,self):continue
                        if owner is None:self.viewer.input_owner=self
                    self.gate.dispatch(kind,data)
                elif kind==2:
                    # Exclude client-message extensions: keep standard encoding,
                    # cursor/resize notifications and continuous framebuffer updates.
                    codes=struct.unpack('>'+str((len(data)-4)//4)+'i',data[4:])
                    codes=[x for x in codes if x not in (-258,-309,-312,-313,-316,-1063131698)]
                    self.upstream.send(b'\x02\x00'+struct.pack('>H',len(codes))+b''.join(struct.pack('>i',x) for x in codes))
                elif kind!=6:self.upstream.send(data)
        except (OSError,EOFError,ValueError,StreamError,LeaseError,sqlite3.Error):pass
        finally:
            self.done.set()
            if self.gate:
                try:self.gate.release()
                except (OSError,StreamError):pass
            self.upstream.close();self.ws.close()
            with self.viewer.stream_lock:
                self.viewer.streams.discard(self)
                if self.viewer.input_owner is self:self.viewer.input_owner=None
            self.closed.set()
