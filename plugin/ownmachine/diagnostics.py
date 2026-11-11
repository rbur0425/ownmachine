"""Read-only readiness checks with bounded, non-secret recovery advice."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import time
from .transport import MCPTransport, TransportError
from .workspace import status

REQUIRED_TOOLS = frozenset({'get_desktop_state', 'get_window_state', 'list_windows',
    'list_apps', 'click', 'type_text', 'press_key', 'hotkey', 'scroll',
    'start_session', 'end_session'})


def diagnose(config, permission_mode="standard"):
    checks = []
    def add(name, level, code, remedy=''):
        checks.append(dict(check=name, status=level, code=code, remedy=remedy))
    def result():
        return {'ok': not any(c['status']=='fail' for c in checks), 'checks': checks,
                'scope': 'Read-only readiness; no screenshot, input, VM startup, or control transfer.'}
    try:
        config.validate()
        if not config.control_dir: raise ValueError()
    except (ValueError, TypeError):
        add('configuration','fail','invalid_configuration',
            'Set host_alias to an SSH alias, vm_name to the relay VM, and control_dir to the absolute shared directory. Timeouts must be integers from 1 to 120.')
        return result()
    add('configuration','pass','configured')
    if permission_mode != 'standard':
        add('permission_mode','fail','unsupported_permission_mode','Set computer_use.permission_mode to standard. OwnMachine refuses bounded and unrestricted modes.')
        return result()
    add('permission_mode','pass','standard_permission_mode')
    if not shutil.which('ssh'):
        add('ssh','fail','ssh_missing','Install an OpenSSH client in the environment running Hermes.')
        return result()
    add('ssh','pass','ssh_available')
    directory = Path(config.control_dir)
    try:
        if not directory.exists() or not (directory/'lease.db').exists():
            add('control','warn','control_not_initialized','New control state starts paused. Use the operator control command or viewer when ready; share this directory across all writers.')
        else:
            with closing(sqlite3.connect((directory/'lease.db').as_uri()+'?mode=ro', uri=True, timeout=1)) as db:
                row = db.execute('SELECT controller, generation, pending FROM lease WHERE id=1').fetchone()
            if (row is None or row[0] not in {'agent','human','paused'} or
                    type(row[1]) is not int or row[1]<0 or row[2] not in (0,1)):
                raise ValueError()
            if row[2]:
                add('control','fail','uncertain_outcome','Inspect the guest before acknowledging the uncertain action through the operator viewer or control command. Never replay it automatically.')
            elif row[0]!='agent':
                add('control','warn','control_'+row[0],'Agent input is intentionally blocked. Return control explicitly when ready; the agent must recapture.')
            else: add('control','pass','agent_control')
    except (OSError, sqlite3.Error, ValueError):
        add('control','fail','control_unreadable','Check directory ownership and the shared lease database. Do not delete or replace control state to bypass a pending action.')
    try:
        viewer=json.loads((directory/'viewer-status.json').read_text())
        heartbeat=viewer.get('heartbeat')
        live=type(heartbeat) in (int,float) and 0<=time.time()-heartbeat<20
    except (OSError,ValueError,AttributeError): live=False
    add('viewer','pass' if live else 'warn','viewer_running' if live else 'viewer_offline',
        '' if live else 'Optional: start the loopback viewer and open its private access link. The native provider does not require it.')
    remote = status(config)
    if not remote.get('host_reachable') or remote.get('code'):
        code=remote.get('code')
        code=code if code in {'host_unreachable','ssh_connection_failed','invalid_host_response'} else 'host_unreachable'
        add('host','fail',code,'Check the configured SSH alias, network, verified host key, key authentication, and restricted relay installation. Do not disable host-key checking.')
        return result()
    add('host','pass','host_reachable')
    if not remote.get('lume_installed'):
        add('vm','fail','lume_missing','Install the pinned Lume release on the Mac host and check the relay lume_path.')
        return result()
    if remote.get('vm_state')!='running':
        state=remote.get('vm_state')
        code='vm_'+state if state in {'stopped','absent','provisioning','unknown','not_probed'} else 'vm_unknown'
        add('vm','fail',code,'Check the named VM with Lume on the host. Provision an absent VM explicitly; start an existing stopped VM with the operator lifecycle command.')
        return result()
    add('vm','pass','vm_running')
    state=remote.get('driver_state')
    if state in {'not_configured','guest_unreachable','invalid_response','not_probed','vm_not_running'}:
        add('guest','fail','guest_not_ready','Check guest GUI login, the relay guest SSH configuration, verified guest key, and guest readiness helper. Guest addresses are resolved dynamically.')
        return result()
    add('guest','pass','guest_reachable')
    for key, label in [('accessibility','Accessibility'),('screen_recording','Screen Recording')]:
        add(key,'pass' if remote.get(key) else 'fail',key+'_granted' if remote.get(key) else key+'_required',
            '' if remote.get(key) else 'Open the guided permission setup inside the guest and approve '+label+'. Follow any restart prompt, then rerun doctor.')
    add('capture_consent','pass' if remote.get('capture_consent_verified') else 'fail',
        'capture_consent_recorded' if remote.get('capture_consent_verified') else 'capture_consent_required',
        '' if remote.get('capture_consent_verified') else 'Complete the guided capture check in the guest and approve the macOS capture prompt. Doctor does not trigger or approve it.')
    if not remote.get('driver_ready'):
        add('driver','fail','driver_not_ready','Finish guest permission setup and start the signed CuaDriver app in the logged-in desktop session. Check the pinned driver version and login launcher.')
        return result()
    add('driver','pass','driver_ready')
    transport=MCPTransport(config)
    try:
        transport.start()
        if not REQUIRED_TOOLS <= transport.tools.keys():
            add('mcp','fail','incompatible_driver_tools','Install the supported pinned guest driver and MCP launcher; required native input or capture tools are missing.')
        else: add('mcp','pass','mcp_ready')
    except TransportError:
        add('mcp','fail','mcp_unavailable','Enable MCP in the host relay and install the guest MCP launcher. Check the signed standard-mode daemon and pinned version. No input was sent.')
    finally: transport.stop()
    return result()


def render(report):
    lines=['OwnMachine doctor: '+('READY' if report['ok'] else 'NEEDS ATTENTION')]
    for check in report['checks']:
        lines.append(f"[{check['status'].upper()}] {check['check']}: {check['code']}")
        if check['remedy']: lines.append('  '+check['remedy'])
    lines.append(report['scope'])
    return '\n'.join(lines)
