"""Synthetic MCP subprocess for reliability tests; never connects to a desktop."""
import json
import os
from pathlib import Path
import sys
import time

root = Path(sys.argv[1])
names = ['get_desktop_state', 'get_window_state', 'list_windows', 'list_apps',
         'click', 'type_text', 'press_key', 'hotkey', 'scroll', 'start_session', 'end_session']
for line in sys.stdin:
    message = json.loads(line)
    if 'id' not in message:
        continue
    fault = (root / 'fault').read_text()
    method = message['method']
    if method == 'initialize':
        result = {'protocolVersion': '2024-11-05'}
    elif method == 'tools/list':
        result = {'tools': [{'name': name, 'inputSchema': {'properties': {'session': {}}}}
                            for name in names if fault != 'missing_tools' or name != 'click']}
    else:
        name = message['params']['name']
        with (root / 'events').open('a') as output:
            output.write(name + '\n'); output.flush(); os.fsync(output.fileno())
        if name == 'type_text' and fault == 'drop':
            sys.exit(0)  # Write was observed, but its result never reaches the client.
        if name == 'type_text' and fault == 'timeout':
            time.sleep(60)
        if name == 'start_session' and fault == 'session_error':
            result = {'isError': True}
        elif name == 'list_windows':
            result = {'structuredContent': {'windows': [{'pid': 12, 'window_id': 34, 'app_name': 'Fixture'}]}}
        elif name == 'get_window_state':
            result = {'structuredContent': {'elements': []}}
        else:
            result = {'structuredContent': {'ok': True}}
    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}), flush=True)
