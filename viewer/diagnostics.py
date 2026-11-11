"""Operator-only viewer checks. Never imported by the model-facing plugin."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit


class AccessError(ValueError):
    pass


def read_access(directory):
    """Refuse unsafe files and arbitrary destinations before sending the token."""
    path = Path(directory) / 'viewer-access.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 4096):
            raise AccessError('unsafe_access_file')
        data = json.loads(stream.read(4097))
    if not isinstance(data, dict):
        raise AccessError('invalid_access_file')
    port = data.get('port')
    url = urlsplit(data.get('url', ''))
    if (type(port) is not int or not 1 <= port <= 65535
            or url.scheme != 'http' or url.netloc != f'127.0.0.1:{port}'
            or url.path != '/' or url.query
            or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', url.fragment)):
        raise AccessError('invalid_access_file')
    return port, url.fragment


def read_state(port, token, timeout):
    # Direct loopback socket: no proxy environment, redirects or token in URL.
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('GET', '/api/state', headers={'X-OwnMachine-Token': token})
        response = connection.getresponse()
        if response.status == 403:
            raise AccessError('viewer_authentication_failed')
        if response.status != 200:
            raise AccessError('viewer_http_failed')
        body = response.read(65537)
        if len(body) > 65536:
            raise AccessError('invalid_viewer_state')
        state = json.loads(body)
        if not isinstance(state, dict):
            raise AccessError('invalid_viewer_state')
        return state
    finally:
        connection.close()


def probe_vnc(config):
    # Shared RFB handshake only: no framebuffer request, clipboard or input.
    from stream import Upstream
    upstream = Upstream(config)
    upstream.close()


def diagnose(config, *, probe=False, access_dir=None):
    checks = []
    def add(name, level, code, remedy=''):
        checks.append(dict(check=name, status=level, code=code, remedy=remedy))
    def result():
        return {'ok': not any(c['status'] == 'fail' for c in checks), 'checks': checks,
                'scope': 'Operator viewer diagnostics only. No capture, input, control transfer or VM lifecycle. Firewall and browser interaction require independent checks.'}
    try:
        config.validate()
        if not config.control_dir:
            raise ValueError()
    except (ValueError, TypeError):
        add('configuration', 'fail', 'invalid_configuration', 'Use a configured SSH alias, VM name, absolute shared control directory and timeouts from 1 to 120.')
        return result()
    try:
        port, token = read_access(access_dir or Path.home()/'.local/state/ownmachine-viewer'/config.vm_name)
    except FileNotFoundError:
        add('access', 'fail', 'viewer_not_started', 'Start the viewer using this shared control directory. Run this doctor on the viewer machine as its owner.')
        return result()
    except (OSError, ValueError, TypeError, AttributeError):
        add('access', 'fail', 'invalid_or_unsafe_access_file', 'Check that the viewer owns a regular, private access file (0600), without a symlink. Restart the viewer to regenerate malformed state; do not share its contents.')
        return result()
    add('access', 'pass', 'private_loopback_access')
    try:
        state = read_state(port, token, config.action_timeout_seconds)
    except AccessError as error:
        code = str(error)
        if code not in {'viewer_authentication_failed', 'viewer_http_failed', 'invalid_viewer_state'}:
            code = 'invalid_viewer_state'
        add('http', 'fail', code, 'Use the current viewer access file. Restart rotates its token; reopen the new private link. Check viewer ownership and control state locally.')
        return result()
    except (OSError, ValueError, http.client.HTTPException):
        add('http', 'fail', 'viewer_unreachable', 'Check that the viewer is running on this machine. Confirm its actual port in the private access file; an occupied preferred port may have changed it.')
        return result()
    finally:
        del token
    add('http', 'pass', 'viewer_authenticated')
    mode = state.get('viewer_mode')
    control = state.get('control')
    if (mode not in {'vnc', 'frames'} or not isinstance(control, dict)
            or control.get('controller') not in {'paused', 'human', 'agent'}
            or type(control.get('pending')) is not bool
            or type(state.get('view_only')) is not bool):
        add('state', 'fail', 'invalid_viewer_state', 'Install matching viewer code and restart the viewer. Do not reset the shared lease.')
        return result()
    if control['pending']:
        add('control', 'fail', 'uncertain_outcome', 'Inspect the guest before explicitly acknowledging through operator controls. Never replay input or delete the lease.')
    elif control.get('input_active'):
        add('control', 'warn', 'human_input_active', 'A key or mouse button is held. The doctor leaves it alone; release it before transferring control.')
    else:
        add('control', 'pass' if control['controller'] == 'human' else 'warn', 'control_' + control['controller'],
            '' if control['controller'] == 'human' else 'Browser input is intentionally disabled. Reserve for human use when ready; the doctor never changes control.')
    if state['view_only']:
        add('input', 'warn', 'viewer_read_only', 'The viewer was started with --read-only. Restart without that flag only if browser input is intended.')
    if state.get('operation'):
        add('lifecycle', 'warn', 'operation_in_progress', 'Wait for the existing lifecycle operation; this check does not retry it.')
    if mode == 'frames':
        add('mode', 'warn', 'screenshot_fallback', 'For direct streaming input, complete noVNC onboarding and start with --viewer-mode vnc.')
        return result()
    add('mode', 'pass', 'streaming_enabled')
    root = Path(__file__).parent
    if not (root / 'vendor/novnc/core/rfb.js').is_file():
        add('assets', 'fail', 'novnc_assets_missing', 'Restore the complete matching viewer directory, including vendored noVNC and licenses.')
    else:
        add('assets', 'pass', 'novnc_assets_present')
    try:
        available = importlib.util.find_spec('Crypto.Cipher.DES') is not None
    except (ImportError, ValueError):
        available = False
    add('dependency', 'pass' if available else 'fail', 'vnc_dependency_ready' if available else 'vnc_dependency_missing',
        '' if available else 'Run this doctor with the viewer Python environment. Install viewer/requirements.txt into that environment.')
    if state.get('stream_connected') is True:
        add('browser', 'pass', 'browser_stream_present')
    else:
        add('browser', 'warn', 'no_browser_stream', 'Open the current private link through the loopback SSH tunnel. Browser authentication and same-origin WebSocket access are required.')
    if probe and available:
        if state.get('operation'):
            add('vnc', 'warn', 'probe_skipped_during_lifecycle', 'Rerun after the current operation finishes.')
        else:
            try:
                probe_vnc(config)
            except Exception:
                add('vnc', 'fail', 'vnc_connection_failed', 'Check the verified SSH alias, running VM, host enable_vnc setting, fixed VNC port and matching relay. Never disable host-key checks. Raw upstream details are intentionally omitted.')
            else:
                add('vnc', 'pass', 'vnc_shared_handshake_ready')
    elif not probe:
        add('vnc', 'warn', 'vnc_not_probed', 'Use --probe-vnc for a bounded shared authentication handshake; it sends no desktop input or capture request.')
    add('firewall', 'warn', 'firewall_requires_external_check', 'Verify from another machine that direct host VNC access is blocked. A successful SSH handshake or localhost URL does not establish firewall coverage.')
    return result()
