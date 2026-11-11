"""OwnMachine readiness tool and native ComputerUseProvider registration."""
import json
import shutil
from .ownmachine.config import Config
from .ownmachine.workspace import status as host_status


def register(ctx):
    from .ownmachine.onboarding import register_commands
    register_commands(ctx)
    from .ownmachine.middleware import control_gate_result
    # Hermes category discovery uses a provider-only collector without middleware.
    # The full plugin context still registers the control-gate verdict middleware.
    if hasattr(ctx, "register_middleware"):
        ctx.register_middleware("tool_execution", control_gate_result)
    if hasattr(ctx, "register_computer_use_provider"):
        from .ownmachine.provider import OwnMachineProvider
        ctx.register_computer_use_provider(OwnMachineProvider())
    def status(args=None, **kwargs):
        config = Config(**{key: ctx.get_config(key, value) for key, value in vars(Config()).items()})
        try:
            config.validate()
            configured = True
        except ValueError:
            configured = False
        result = {"implementation": "viewer_lifecycle", "configured": configured,
                           "ssh_available": shutil.which("ssh") is not None,
                           "host_reachable": None, "vm_state": "not_probed",
                           "driver_ready": False, "viewer_state": "not_configured",
                           "controller": "not_initialized", "native_provider_ready": False, "native_provider_implemented": True}
        if configured:
            result.update(host_status(config))
            if config.control_dir:
                from pathlib import Path
                from .ownmachine.lease import Lease
                path = Path(config.control_dir)/'lease.db'
                control = Lease(path).status() if path.exists() else {'controller':'paused','pending':False}
                result.update(controller=control['controller'], uncertain_outcome=control['pending'])
                import time
                try:
                    viewer = json.loads((Path(config.control_dir)/'viewer-status.json').read_text())
                    heartbeat = viewer.get('heartbeat')
                    result['viewer_state'] = 'running' if type(heartbeat) in (int,float) and 0 <= time.time()-heartbeat < 20 else 'offline'
                except (OSError, ValueError, AttributeError): result['viewer_state'] = 'offline'
                result['native_provider_ready'] = bool(result.get('driver_ready') and
                    control['controller']=='agent' and not control['pending'])
        return json.dumps(result)
    ctx.register_tool(name="ownmachine_status", toolset="ownmachine", schema={
        "name": "ownmachine_status", "description": "Report OwnMachine readiness and bounded read-only host preflight when configured. Reports the configured VM and optional guest driver permissions; capture consent is recorded evidence, not a fresh screenshot.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}, handler=status)
