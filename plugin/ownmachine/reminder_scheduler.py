"""Public Hermes CLI + authenticated gateway RPC; no private stores or core imports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit


def home(ctx):
    return Path(ctx.state.data_dir).parent.parent


def cli(ctx, *args):
    # Hermes itself resolves credentials and profile authority. The plugin never
    # opens auth files, a control socket, or a scheduler store.
    command = [sys.executable, '-c',
               'import sys; from hermes_cli.main import main; sys.argv=["hermes",*sys.argv[1:]]; raise SystemExit(main())', *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=40,
                                env=dict(os.environ, HERMES_HOME=str(home(ctx))))
        if result.returncode or len(result.stdout) > 1024*1024:
            raise ValueError('hermes_command_unavailable')
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise ValueError('hermes_command_unavailable') from None


def rpc(ctx, action='list', job_id=None):
    from websockets.sync.client import connect
    try:
        attach = json.loads(cli(ctx, 'gateway', 'attach', '--json'))
        url = urlsplit(attach['url'])
        if (url.scheme != 'ws' or url.hostname not in ('127.0.0.1', '::1')
                or url.path != '/api/ws' or url.username or url.password or url.query or url.fragment
                or attach.get('protocol') != 'hermes-gateway-v1'
                or attach.get('client_code_sha') != attach.get('endpoint', {}).get('code_sha')
                or attach.get('endpoint', {}).get('profile_id') != str(home(ctx))):
            raise ValueError('gateway_identity_mismatch')
        if action not in ('list','remove','pause','resume'):
            raise ValueError('unsupported_scheduler_operation')
        params = dict(action=action, include_disabled=True) if action == 'list' else dict(action=action, name=job_id)
        with connect(attach['url'], subprotocols=attach['protocols'], proxy=None,
                     open_timeout=10, close_timeout=2, max_size=1024*1024) as socket:
            if socket.subprotocol != 'hermes-gateway-v1': raise ValueError('gateway_protocol_mismatch')
            socket.send(json.dumps(dict(jsonrpc='2.0',id=1,method='cron.manage',params=params)))
            deadline = time.monotonic() + 15
            for _ in range(32):
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise ValueError("scheduler_result_timeout")
                response=json.loads(socket.recv(timeout=remaining))
                if response.get('id') != 1: continue
                result=response.get('result')
                if not isinstance(result,dict) or result.get('success') is not True:
                    raise ValueError('scheduler_operation_refused')
                return result
        raise ValueError('scheduler_result_missing')
    except Exception:
        # Attach tickets and arbitrary gateway errors must never enter chat/logs.
        raise ValueError('scheduler_unavailable_start_matching_profile_gateway') from None


def jobs(ctx):
    result=rpc(ctx)
    if not isinstance(result.get('jobs'),list): raise ValueError('invalid_scheduler_response')
    return result['jobs']


def create(ctx, *, name, schedule, deliver, script):
    # CLI accepts no-agent/paused/script flags that cron.manage add does not yet
    # expose. Do not parse its human output; identify the paused result via RPC.
    cli(ctx, 'cron', 'create', schedule, 'OwnMachine consent-bound reminder; no desktop or model action.',
        '--name', name, '--deliver', deliver, '--failure-deliver', 'local', '--repeat', '1',
        '--script', script, '--no-agent', '--paused', '--paused-reason', 'OwnMachine durable consent binding',
        '--catch-up', 'off')
