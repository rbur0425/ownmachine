"""Bounded read-only host diagnostics. Never forward raw SSH diagnostics."""
import json
import os
import subprocess


def status(config):
    argv = config.ssh_argv('status')
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'SSH_AUTH_SOCK', 'LANG') if key in os.environ}
    try:
        result = subprocess.run(argv, env=env, capture_output=True, text=True,
                                timeout=config.connect_timeout_seconds + config.action_timeout_seconds + 5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {'host_reachable': False, 'code': 'host_unreachable'}
    if result.returncode != 0:
        return {'host_reachable': False, 'code': 'ssh_connection_failed'}
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict): raise ValueError()
        # Strict field/value allowlist: remote paths, IPs, VNC URLs and arbitrary
        # driver diagnostics never flow into the model-facing result.
        states = {'not_configured', 'vm_not_running', 'guest_unreachable',
                  'invalid_response', 'permissions_required', 'capture_consent_required',
                  'not_running', 'ready'}
        state = data.get('driver_state')
        state = state if isinstance(state, str) and state in states else 'not_probed'
        flags = {key: data.get(key) is True for key in
                 ('guest_reachable', 'accessibility', 'screen_recording', 'capture_consent_verified')}
        # A stopped/absent guest cannot report its OS through the guest probe.
        # Preserve the reachable host and VM diagnosis instead of inventing an
        # OS mismatch. Running guests still require the exact profile below.
        if data.get('vm_state') in {'stopped', 'provisioning', 'absent', 'lume_not_installed', 'not_probed'}:
            return {'host_reachable': True, 'lume_installed': data.get('lume_installed') is True,
                    'vm_state': data['vm_state'], 'driver_ready': False,
                    'driver_state': 'vm_not_running', 'viewer_state': 'not_probed',
                    'controller': 'not_initialized'}
        linux = data.get('guest_os') == 'linux' and data.get('guest_profile') == 'omarchy'
        if linux != (config.guest_profile == 'omarchy'):
            return {'host_reachable': True, 'driver_ready': False, 'code': 'guest_profile_mismatch'}
        linux_flags = {key: data.get(key) is True for key in
                       ('graphical_session', 'accessibility_bus', 'driver_running', 'standard_mode')} if linux else {}
        readiness = all(linux_flags.values()) and flags['guest_reachable'] if linux else all(flags.values())
        ready = (state == 'ready' and data.get('vm_state') == 'running' and readiness
                 and data.get('driver_ready') is True)
        if state == 'ready' and not ready: state = 'invalid_response'
        if linux:
            # False macOS TCC booleans mislead models into requesting consent
            # that does not exist on Linux. Return the actual Linux gates only.
            flags = {'guest_reachable': flags['guest_reachable']}
        return {**flags, **linux_flags, **({'guest_os': 'linux', 'guest_profile': 'omarchy'} if linux else {}), 'host_reachable': True,
                'lume_installed': data.get('lume_installed') is True,
                'vm_state': data.get('vm_state') if data.get('vm_state') in
                    {'not_probed', 'lume_not_installed', 'running', 'stopped', 'provisioning', 'absent', 'unknown'} else 'unknown',
                'driver_ready': ready, 'driver_state': state,
                'viewer_state': 'not_probed', 'controller': 'not_initialized'}
    except (ValueError, TypeError):
        return {'host_reachable': True, 'code': 'invalid_host_response'}
