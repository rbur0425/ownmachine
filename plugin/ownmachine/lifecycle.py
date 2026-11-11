"""Operator-only lifecycle client. No model tool is registered for these actions."""
import json
import os
from pathlib import Path
import subprocess
from .lease import Lease


class LifecycleError(RuntimeError):
    pass


def operate(config, operation, runner=subprocess.run):
    config.validate()
    if operation not in {'start','stop','restart'}: raise ValueError('unsupported_operation')
    if not config.control_dir: raise ValueError('shared_control_directory_required')
    lease=Lease(Path(config.control_dir)/'lease.db')
    env={k:os.environ[k] for k in ('PATH','HOME','SSH_AUTH_SOCK','LANG') if k in os.environ}
    with lease.lifecycle():
        try:
            result=runner(config.ssh_argv(operation), stdin=subprocess.DEVNULL,
                          capture_output=True,text=True,env=env,timeout=120,check=False)
            if result.returncode: raise LifecycleError('lifecycle_failed_review_required')
            data=json.loads(result.stdout)
            expected='stopped' if operation=='stop' else 'running'
            if not isinstance(data,dict) or data.get('ok') is not True or data.get('vm_state')!=expected:
                raise LifecycleError('lifecycle_failed_review_required')
            return {'ok':True,'operation':operation,'vm_state':expected,'controller':'paused'}
        except (OSError,ValueError,subprocess.SubprocessError):
            raise LifecycleError('lifecycle_outcome_unknown') from None
