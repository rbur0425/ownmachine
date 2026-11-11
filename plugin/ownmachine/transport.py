"""Bounded MCP JSON-lines client over one fixed SSH stdio stream. Never replays."""
import json
import os
import selectors
import signal
import subprocess
import threading
import time


class TransportError(RuntimeError):
    pass


class MCPTransport:
    MAX_FRAME = 16 * 1024 * 1024

    def __init__(self, config, argv=None):
        self.config = config
        self.argv = argv or config.ssh_argv('mcp')
        self.process = None
        self.buffer = bytearray()
        self.sequence = 0
        self.lock = threading.RLock()
        self.tools = {}

    def start(self):
        with self.lock:
            if self.process is not None: return
            env = {k: os.environ[k] for k in ('PATH', 'HOME', 'SSH_AUTH_SOCK', 'LANG') if k in os.environ}
            try:
                self.process = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env=env, start_new_session=True, bufsize=0)
                os.set_blocking(self.process.stdin.fileno(), False)
                os.set_blocking(self.process.stdout.fileno(), False)
                reply = self.request('initialize', {'protocolVersion': '2024-11-05',
                    'capabilities': {}, 'clientInfo': {'name': 'ownmachine', 'version': '0.1.0'}})
                if reply.get('protocolVersion') not in {'2024-11-05', '2025-03-26', '2025-06-18'}:
                    raise TransportError('unsupported_mcp_version')
                self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, time.monotonic()+5)
                cursor = None
                for _ in range(16):
                    data = self.request('tools/list', {'cursor': cursor} if cursor else {})
                    for tool in data.get('tools', []):
                        if isinstance(tool, dict) and isinstance(tool.get('name'), str):
                            self.tools[tool['name']] = tool.get('inputSchema', {})
                    cursor = data.get('nextCursor')
                    if not cursor: break
                else: raise TransportError('tool_listing_limit')
            except Exception:
                self.stop()
                raise TransportError('mcp_start_failed') from None

    def _wait(self, fd, event, deadline):
        if time.monotonic() >= deadline:
            raise TransportError('transport_timeout')
        with selectors.DefaultSelector() as selector:
            selector.register(fd, event)
            if not selector.select(max(0, deadline-time.monotonic())) or time.monotonic() >= deadline:
                raise TransportError('transport_timeout')

    def _send(self, message, deadline):
        data = json.dumps(message, separators=(',', ':')).encode()+b'\n'
        if len(data) > self.MAX_FRAME: raise TransportError('request_too_large')
        offset = 0
        while offset < len(data):
            self._wait(self.process.stdin, selectors.EVENT_WRITE, deadline)
            try: offset += os.write(self.process.stdin.fileno(), data[offset:])
            except BlockingIOError: continue

    def _read(self, deadline):
        if time.monotonic() >= deadline:
            raise TransportError('transport_timeout')
        while b'\n' not in self.buffer:
            if len(self.buffer) > self.MAX_FRAME: raise TransportError('response_too_large')
            self._wait(self.process.stdout, selectors.EVENT_READ, deadline)
            try: chunk = os.read(self.process.stdout.fileno(), 65536)
            except BlockingIOError: continue
            if not chunk: raise TransportError('transport_closed')
            self.buffer.extend(chunk)
        line, _, rest = self.buffer.partition(b'\n')
        self.buffer = bytearray(rest)
        if len(line) > self.MAX_FRAME: raise TransportError('response_too_large')
        result = json.loads(line)
        if time.monotonic() >= deadline:
            raise TransportError('transport_timeout')
        return result

    def request(self, method, params):
        with self.lock:
            if self.process is None: raise TransportError('transport_not_started')
            self.sequence += 1
            ident = self.sequence
            deadline = time.monotonic()+self.config.action_timeout_seconds
            try:
                self._send({'jsonrpc':'2.0', 'id':ident, 'method':method, 'params':params}, deadline)
                for _ in range(256):
                    msg = self._read(deadline)
                    if not isinstance(msg, dict) or msg.get('jsonrpc') != '2.0':
                        raise TransportError('invalid_mcp_message')
                    if 'method' in msg:
                        if 'id' in msg:
                            answer = {'result': {}} if msg['method']=='ping' else {
                                'error': {'code': -32601, 'message': 'Client capability not supported'}}
                            self._send({'jsonrpc':'2.0', 'id':msg['id'], **answer}, deadline)
                        continue
                    if msg.get('id') != ident: raise TransportError('unexpected_response')
                    if 'error' in msg: raise TransportError('remote_protocol_error')
                    if not isinstance(msg.get('result'), dict): raise TransportError('invalid_result')
                    return msg['result']
                raise TransportError('notification_limit')
            except Exception:
                self.stop()
                raise TransportError('transport_outcome_unknown') from None

    def call(self, name, arguments):
        if name not in self.tools: raise TransportError('unsupported_tool')
        return self.request('tools/call', {'name':name, 'arguments':arguments})

    def stop(self):
        with self.lock:
            p, self.process = self.process, None
            if p is not None:
                try:
                    p.stdin.close()
                    if p.poll() is None: os.killpg(p.pid, signal.SIGTERM)
                    p.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    try: os.killpg(p.pid, signal.SIGKILL)
                    except OSError: pass
                    p.wait()
                finally: p.stdout.close()
            self.buffer.clear()
            self.tools.clear()
