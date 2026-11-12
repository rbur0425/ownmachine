import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_support import module
endpoint=module('tested_viewer_check','scripts/viewer-check-endpoint.py')
services=module('tested_viewer_services','scripts/setup-services.py')

class ViewerCheckTests(unittest.TestCase):
    def test_only_fixed_readiness_operations_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();config=root/'check.json'
            config.write_text(json.dumps(dict(host_alias='viewer-key',vm_name='guest',guest_profile='omarchy',control_dir=str(root/'shared'),access_dir=str(root/'private'))));config.chmod(0o600)
            with patch.object(endpoint.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'{"ok":true}')) as call:
                result=endpoint.execute(config,'ownmachine-viewer-check probe --vm guest')
                self.assertTrue(result['ok']);self.assertIn('--probe-vnc',call.call_args.args[0])
                for command in ('ownmachine-host start --vm guest','ownmachine-viewer-check probe --vm another','ownmachine-viewer-check probe --vm guest; sh',''):
                    with self.assertRaisesRegex(ValueError,'unsupported_operation'):endpoint.execute(config,command)
                self.assertEqual(call.call_count,1)

    def test_remote_probe_requires_exact_profile_vm_and_success(self):
        config=dict(vm_name='guest',guest_profile='omarchy',viewer_probe_ssh_alias='viewer-check')
        good=dict(ok=True,vm_name='guest',guest_profile='omarchy',scope='viewer_readiness_only')
        with patch.object(services,'call',return_value=SimpleNamespace(stdout=json.dumps(good).encode())) as call:
            services.viewer_check(config,True)
            self.assertIn('StrictHostKeyChecking=yes',call.call_args.args[0])
            self.assertEqual(call.call_args.args[0][-4:],['ownmachine-viewer-check','probe','--vm','guest'])
        for changed in ({'vm_name':'other'},{'guest_profile':'macos'},{'ok':False},{'extra':True}):
            with patch.object(services,'call',return_value=SimpleNamespace(stdout=json.dumps(dict(good,**changed)).encode())):
                with self.assertRaisesRegex(ValueError,'remote_viewer_not_ready'):services.viewer_check(config)
        with self.assertRaisesRegex(ValueError,'install_remote_viewer'):services.preflight_mutation('viewer',config)
