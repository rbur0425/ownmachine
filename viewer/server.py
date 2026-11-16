"""Private browser desktop and trusted-operator controls."""
import argparse
from contextlib import ExitStack
import base64
import fcntl
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import json
import os
import re
from pathlib import Path
import secrets
import stat
import signal
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import uuid
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ownmachine.config import Config
from ownmachine.lease import Lease, LeaseError
from ownmachine.lifecycle import operate, LifecycleError
from ownmachine.transport import MCPTransport, TransportError
from ownmachine.workspace import status as host_status


class Viewer:
    def __init__(self,config,interval=1.0,max_dimension=1280,allow_input=True,mode="frames",quality=6,compression=2,swap_red_blue=False,access_dir=None):
        if not .25<=interval<=10 or type(max_dimension) is not int or not 640<=max_dimension<=3840:
            raise ValueError("invalid_viewer_configuration")
        if mode not in {'frames','vnc'} or type(quality) is not int or not 0<=quality<=9 or type(compression) is not int or not 0<=compression<=9:
            raise ValueError('invalid_stream_configuration')
        self.mode=mode;self.quality=quality;self.compression=compression;self.swap_red_blue=swap_red_blue
        self.stream_lock=threading.Lock();self.streams=set();self.input_owner=None
        self.stream_start_lock=threading.Lock()
        self.config=config.validate()
        if not config.control_dir:raise ValueError('shared_control_directory_required')
        self.directory=Path(config.control_dir)
        self.access_directory=Path(access_dir or Path.home()/'.local/state/ownmachine-viewer'/config.vm_name).expanduser().absolute()
        shared=self.directory.resolve(); private=self.access_directory.resolve()
        if private == shared or shared in private.parents or private in shared.parents:
            raise ValueError('viewer_access_must_be_separate')
        self.access_directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        info=self.access_directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('unsafe_viewer_access_directory')
        self.lease=Lease(self.directory/'lease.db',timeout=5)
        self.owner=(self.directory/'viewer.lock').open('a')
        try:fcntl.flock(self.owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self.owner.close();raise
        self.token=secrets.token_urlsafe(32)
        self.interval=interval
        self.max_dimension=max_dimension
        self.allow_input=allow_input
        self.session=None
        self.frames={}
        self.frame_id=None
        self.capture_id=None
        self.dimensions=None
        self.client=MCPTransport(config)
        self.done=threading.Event()
        self.suspended=threading.Event()
        self.operation_lock=threading.Lock()
        self.state_lock=threading.Lock()
        self.frame=None
        self.frame_time=0
        self.capture_error='connecting'
        self.host={'vm_state':'not_probed','driver_ready':False}
        self.operation=None
        self.threads=[]

    def start(self):
        for target in ((self._frames,self._status) if self.mode=='frames' else (self._status,)):
            t=threading.Thread(target=target,daemon=True);t.start();self.threads.append(t)

    def close(self):
        self.done.set()
        self.stop_streams()
        self.client.stop()
        for t in self.threads:t.join(timeout=1)
        (self.access_directory/'viewer-access.json').unlink(missing_ok=True)
        (self.directory/'viewer-status.json').unlink(missing_ok=True)
        self.owner.close()

    def _frames(self):
        while not self.done.is_set():
            if self.operation_lock.acquire(timeout=.1):
                try:
                    if not self.suspended.is_set():self.capture()
                finally:self.operation_lock.release()
            self.done.wait(self.interval)

    def capture(self):
        try:
            before=self.lease.status()['generation']
            if self.client.process is None:
                self.client.start();self.session='ownmachine-viewer-'+uuid.uuid4().hex[:12]
            reply=self.client.call('get_desktop_state',{'session':self.session,'max_image_dimension':self.max_dimension})
            if reply.get('isError'):raise ValueError('capture_unavailable')
            part=next(p for p in reply.get('content',[]) if p.get('type')=='image')
            frame=base64.b64decode(part['data'],validate=True)
            if frame[:8]!=b'\x89PNG\r\n\x1a\n' or len(frame)<24 or len(frame)>16*1024*1024:raise ValueError('invalid_capture')
            dims=struct.unpack('>II',frame[16:24])
            data=reply.get('structuredContent',{})
            capture_id=data.get('capture_id')
            if not isinstance(capture_id,str) or not all(0<d<=8192 for d in dims):raise ValueError('invalid_capture')
            if before!=self.lease.status()['generation']:raise ValueError('control_changed')
            with self.state_lock:
                self.frame=frame;self.frame_time=time.time();self.capture_error=None
                self.frame_id=uuid.uuid4().hex;self.capture_id=capture_id;self.dimensions=dims
                self.frames={k:v for k,v in self.frames.items() if time.time()-v['time']<=5}
                self.frames[self.frame_id]={'time':self.frame_time,'generation':before,'dimensions':dims}
        except Exception:
            self.client.stop()
            with self.state_lock:
                self.frame=None;self.frames.clear();self.capture_error='capture_unavailable'

    def input(self,payload):
        if self.mode=='vnc':raise LeaseError('viewer_read_only')
        if not self.allow_input:raise LeaseError('viewer_read_only')
        if not isinstance(payload,dict):raise ValueError('invalid_request')
        kind=payload.get('kind')
        fields={'click':{'x','y','button','count'},'text':{'text'},'key':{'keys'},'scroll':{'direction','amount'}}
        if not isinstance(kind,str) or kind not in fields or set(payload)-fields[kind]-{'kind','frame_id'}:
            raise ValueError('invalid_request')
        frame_id=payload.get('frame_id')
        if not isinstance(frame_id,str):raise ValueError('invalid_frame')
        args={};name={'click':'click','text':'type_text','key':'hotkey','scroll':'scroll'}[kind]
        if kind=='click':
            x,y=payload.get('x'),payload.get('y')
            if type(x) is not int or type(y) is not int:raise ValueError('invalid_coordinates')
            button,count=payload.get('button','left'),payload.get('count',1)
            if button not in ('left','right') or type(count) is not int or count not in (1,2):raise ValueError('invalid_click')
            args=dict(x=x,y=y,button=button,count=count)
        elif kind=='text':
            text=payload.get('text')
            if not isinstance(text,str) or not 1<=len(text)<=4096 or '\x00' in text:raise ValueError('invalid_text')
            args={'text':text}
        elif kind=='key':
            keys=payload.get('keys')
            allowed={'enter','tab','escape','backspace','delete','up','down','left','right','space','home','end','pageup','pagedown','cmd','shift','alt','ctrl'}|set('abcdefghijklmnopqrstuvwxyz0123456789')
            if not isinstance(keys,list) or not 1<=len(keys)<=4 or any(not isinstance(k,str) or k not in allowed for k in keys):raise ValueError('invalid_keys')
            name='press_key' if len(keys)==1 else 'hotkey'
            args={'key':keys[0]} if len(keys)==1 else {'keys':keys}
        else:
            direction,amount=payload.get('direction'),payload.get('amount',3)
            if direction not in ('up','down','left','right') or type(amount) is not int or not 1<=amount<=10:raise ValueError('invalid_scroll')
            args={'direction':direction,'amount':amount}
        if not self.operation_lock.acquire(timeout=5):raise LeaseError('operation_in_progress')
        try:
            with self.state_lock:
                frame=self.frames.get(frame_id)
                if not frame or time.time()-frame['time']>5 or not self.frame or frame['dimensions']!=self.dimensions:
                    raise LeaseError('fresh_frame_required')
                if kind=='click' and not (0<=x<self.dimensions[0] and 0<=y<self.dimensions[1]):raise ValueError('invalid_coordinates')
                args.update(scope='desktop',session=self.session)
                if kind=='click':args['capture_id']=self.capture_id
            props=self.client.tools.get(name,{}).get('properties',{})
            if not set(args)<=set(props):raise ValueError('unsupported_driver_tool')
            try:
                with self.lease.write(frame['generation'],controller='human'):
                    reply=self.client.call(name,args)
                    data=reply.get('structuredContent',{})
                    if not data:
                        for part in reply.get('content',[]):
                            if part.get('type')=='text':
                                try:data=json.loads(part['text'])
                                except (ValueError,KeyError):pass
                    if not isinstance(data,dict) or reply.get('isError') or data.get('ok') is False or data.get('code') in {'transport_outcome_unknown','timeout_outcome_unknown'}:
                        raise LeaseError('input_failed_review_required')
                return {'ok':True,'verified':data.get('verified') is True}
            finally:
                # Consume all old frames, even on failure: a retry must never duplicate input.
                with self.state_lock:self.frames.clear();self.frame=None
        finally:self.operation_lock.release()

    def _status(self):
        while not self.done.is_set():
            result=host_status(self.config)
            if self.done.is_set():return
            with self.state_lock:self.host=result
            marker={'heartbeat':time.time(),'state':'running'}
            path=self.directory/'viewer-status.json'
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(marker));tmp.replace(path)
            self.done.wait(5)

    def stop_streams(self):
        with self.stream_lock:streams=list(self.streams)
        for stream in streams:stream.stop()
        for stream in streams:
            if not stream.closed.wait(7):raise LeaseError('stream_still_closing')

    def snapshot(self):
        with self.stream_lock, ExitStack() as locks:
            gates=[stream.gate for stream in self.streams if stream.gate]
            for gate in gates:locks.enter_context(gate.lock)
            control=self.lease.status()
            active=any(gate.active for gate in gates)
            connected=bool(self.streams)
        # pending is durably set during a held key/drag. Distinguish that live
        # transaction from uncertainty after a failed/disconnected write.
        if active:control={**control,'pending':False,'input_active':True}
        with self.state_lock:
            return {'host':dict(self.host),'control':control,
                    'frame_age':round(time.time()-self.frame_time,1) if self.frame else None,
                    'capture_error':self.capture_error or ('stale_capture' if self.frame and time.time()-self.frame_time>5 else None),
                    'operation':self.operation,'view_only':not self.allow_input,'frame_interval':self.interval,
                    'viewer_mode':self.mode,'stream_connected':connected,'quality':self.quality,'compression':self.compression,'swap_red_blue':self.swap_red_blue}

    def action(self,payload):
        if not isinstance(payload,dict) or set(payload)-{'action','acknowledge'}:
            raise ValueError('invalid_request')
        action=payload.get('action')
        if not isinstance(action,str) or action not in {'start','stop','restart','paused','human','agent'}:
            raise ValueError('unsupported_action')
        if not self.operation_lock.acquire(timeout=5):raise LeaseError('operation_in_progress')
        try:
            self.suspended.set()
            with self.stream_start_lock:self.stop_streams()
            if action in {'paused','human','agent'}:
                result=self.lease.transfer(action,acknowledge=payload.get('acknowledge') is True)
                with self.state_lock:self.frames.clear();self.frame=None
                return result
            if 'acknowledge' in payload:raise ValueError('review_control_state_before_lifecycle')
            self.suspended.set()
            with self.state_lock:self.operation=action;self.frame=None;self.frames.clear()
            # End only this read-only connection; native backends retain their own sessions.
            self.client.stop()
            return operate(self.config,action)
        finally:
            with self.state_lock:self.operation=None
            self.suspended.clear()
            self.operation_lock.release()


class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,viewer):
        self.viewer=viewer
        super().__init__(address,Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass # no URLs, headers, frames, tokens or typed content in access logs
    def send(self,status,body,content_type='application/json',headers=None):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        for key,value in (headers or {}).items():self.send_header(key,str(value))
        self.end_headers()
        self.wfile.write(body)
    def error(self,status,code):self.send(status,json.dumps({'error':code}).encode())
    def host_allowed(self):
        host=self.headers.get('Host','')
        match=re.fullmatch(r'(?:127\.0\.0\.1|localhost):([0-9]{1,5})',host)
        return bool(match and 0<int(match.group(1))<=65535)
    def authorized(self):
        token=self.headers.get('X-OwnMachine-Token','')
        if not token:
            try:
                cookie=SimpleCookie(self.headers.get('Cookie',''))
                name='ownmachine_session_'+str(self.server.server_port)
                if name in cookie:token=cookie[name].value
            except Exception:return False
        if not token.isascii():return False
        origin=self.headers.get('Origin')
        return (self.host_allowed() and (origin is None or origin=='http://'+self.headers.get('Host'))
                and secrets.compare_digest(token,self.server.viewer.token))
    def do_GET(self):
        if not self.host_allowed():return self.error(403,'invalid_host')
        path=urlsplit(self.path).path
        if path.startswith('/vendor/novnc/'):
            root=Path(__file__).parent/'vendor/novnc'
            file=(Path(__file__).parent/path.lstrip('/')).resolve()
            if not file.is_relative_to(root.resolve()) or file.suffix!='.js' or not file.is_file():return self.error(404,'not_found')
            return self.send(200,file.read_bytes(),'text/javascript')
        if path in {'/','/app.js','/style.css'}:
            name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
            mime={'/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[path]
            return self.send(200,(Path(__file__).parent/name).read_bytes(),mime)
        if not self.authorized():return self.error(403,'authentication_required')
        if path=='/api/stream':return self.stream()
        if path=='/api/state':
            try:return self.send(200,json.dumps(self.server.viewer.snapshot()).encode())
            except (sqlite3.Error,LeaseError):return self.error(409,'control_busy')
        if path=='/api/frame':
            with self.server.viewer.state_lock:
                frame_id=self.server.viewer.frame_id
                frame=self.server.viewer.frame if time.time()-self.server.viewer.frame_time<=5 else None
            if frame is None:return self.error(503,'capture_unavailable')
            return self.send(200,frame,'image/png',{'X-OwnMachine-Frame':frame_id or ''})
        return self.error(404,'not_found')
    def stream(self):
        from stream import Upstream, Bridge, WebSocket, websocket_accept, StreamError
        viewer=self.server.viewer
        if viewer.mode!='vnc':return self.error(409,'streaming_not_enabled')
        if self.headers.get('Origin')!='http://'+self.headers.get('Host',''):return self.error(403,'invalid_origin')
        if self.headers.get('Upgrade','').lower()!='websocket' or 'upgrade' not in self.headers.get('Connection','').lower() or self.headers.get('Sec-WebSocket-Version')!='13':
            return self.error(400,'invalid_websocket')
        upstream=None;bridge=None;upgraded=False
        try:
            accept=websocket_accept(self.headers.get('Sec-WebSocket-Key',''))
            with viewer.stream_start_lock:
                if viewer.suspended.is_set() or viewer.done.is_set():return self.error(409,'operation_in_progress')
                with viewer.stream_lock:
                    if len(viewer.streams)>=4:return self.error(409,'viewer_connection_limit')
                upstream=Upstream(viewer.config)
                bridge=Bridge(viewer,WebSocket(self.connection),upstream)
                with viewer.stream_lock:viewer.streams.add(bridge)
            self.protocol_version="HTTP/1.1"
            self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
            self.send_header('Sec-WebSocket-Accept',accept)
            if 'binary' in self.headers.get('Sec-WebSocket-Protocol','').split(','):self.send_header('Sec-WebSocket-Protocol','binary')
            self.end_headers();self.wfile.flush();upgraded=True
            self.connection.settimeout(None);self.close_connection=True
            bridge.run()
        except (OSError,ValueError,KeyError,TypeError,EOFError,StreamError,ImportError,subprocess.SubprocessError):
            if bridge:
                bridge.stop()
                with viewer.stream_lock:viewer.streams.discard(bridge)
                bridge.closed.set()
            if upstream:upstream.close()
            if not upgraded:self.error(503,'stream_unavailable')

    def do_POST(self):
        if self.path=='/api/session':
            if not self.host_allowed() or self.headers.get('Origin')!='http://'+self.headers.get('Host',''):
                return self.error(403,'invalid_origin')
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=512 or self.headers.get('Content-Type')!='application/json':raise ValueError()
                self.connection.settimeout(5)
                data=json.loads(self.rfile.read(length))
                token=data.get('token') if isinstance(data,dict) else None
                if not isinstance(token,str) or not token.isascii() or not secrets.compare_digest(token,self.server.viewer.token):
                    return self.error(403,'authentication_required')
                cookie='ownmachine_session_'+str(self.server.server_port)+'='+token+'; HttpOnly; SameSite=Strict; Path=/'
                return self.send(200,b'{"ok":true}',headers={'Set-Cookie':cookie})
            except (ValueError,TypeError,OSError):return self.error(400,'invalid_request')
        if not self.authorized():return self.error(403,'authentication_required')
        if self.path not in {'/api/action','/api/input'}:return self.error(404,'not_found')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768 or self.headers.get('Content-Type')!='application/json':
                return self.error(400,'invalid_request')
            self.connection.settimeout(5)
            payload=json.loads(self.rfile.read(length))
            result=(self.server.viewer.input(payload) if self.path=='/api/input' else self.server.viewer.action(payload))
            return self.send(200,json.dumps(result).encode())
        except (ValueError,TypeError):return self.error(400,'invalid_request')
        except LeaseError as error:
            code=str(error)
            known={'fresh_frame_required','stale_target','paused','human_takeover','viewer_read_only','operation_in_progress','operator_review_required','input_failed_review_required','transport_outcome_unknown'}
            return self.error(409,code if code in known else 'operation_failed_inspect_control_state')
        except (LifecycleError,TransportError):return self.error(409,'operation_failed_inspect_control_state')
        except (OSError,sqlite3.Error):return self.error(409,'control_busy')


def bind_server(viewer, requested_port=0):
    """Bind atomically; never probe a port and race another process for it."""
    try:
        return Server(('127.0.0.1',requested_port),viewer)
    except OSError as error:
        if requested_port and error.errno==errno.EADDRINUSE:
            return Server(('127.0.0.1',0),viewer)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-alias',required=True)
    parser.add_argument('--guest-profile', choices=['macos','omarchy','windows'], default='macos')
    parser.add_argument('--vm-name',default='ownmachine')
    parser.add_argument('--control-dir',required=True)
    parser.add_argument('--access-dir',help='Private viewer-user directory outside shared control state')
    parser.add_argument('--port',type=int,default=0,help='Requested port; 0 selects a free OS-assigned port (default). An occupied requested port also falls back to a free port.')
    parser.add_argument('--viewer-mode',choices=['vnc'],default='vnc')
    parser.add_argument('--console-transport',choices=['password-vnc','private-unix'],default='password-vnc')
    parser.add_argument('--swap-red-blue',action='store_true',help='Correct servers that ignore the requested RGB pixel order')
    parser.add_argument('--quality',type=int,default=6,help='noVNC quality 0–9')
    parser.add_argument('--compression',type=int,default=2,help='noVNC compression 0–9')
    parser.add_argument('--frame-interval',type=float,default=1.0,help='Capture interval in seconds, 0.25–10')
    parser.add_argument('--max-image-dimension',type=int,default=1280,help='Preview long edge, 640–3840 pixels')
    parser.add_argument('--read-only',action='store_true',help='Disable browser input on the server')
    parser.add_argument('--connect-timeout-seconds',type=int,default=15)
    parser.add_argument('--action-timeout-seconds',type=int,default=30)
    args=parser.parse_args()
    if not 0<=args.port<=65535:parser.error('invalid port')
    os.umask(0o077)
    viewer=Viewer(Config(host_alias=args.host_alias,vm_name=args.vm_name,guest_profile=args.guest_profile,console_transport=args.console_transport,control_dir=args.control_dir,connect_timeout_seconds=args.connect_timeout_seconds,action_timeout_seconds=args.action_timeout_seconds),interval=args.frame_interval,max_dimension=args.max_image_dimension,allow_input=not args.read_only,mode=args.viewer_mode,quality=args.quality,compression=args.compression,swap_red_blue=args.swap_red_blue,access_dir=args.access_dir)
    server=None
    try:
        server=bind_server(viewer,args.port)
        access={'url':f'http://127.0.0.1:{server.server_port}/#{viewer.token}','port':server.server_port}
        path=viewer.access_directory/'viewer-access.json'
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        with os.fdopen(fd,'w') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise ValueError('unsafe_viewer_access_file')
            os.fchmod(stream.fileno(),0o600); stream.truncate(0)
            json.dump(access,stream)
        print(f'OwnMachine viewer listening on 127.0.0.1:{server.server_port}. Private access link: {path}',flush=True)
        signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
        viewer.start();server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        if server:server.server_close()
        viewer.close()

if __name__=='__main__':main()
