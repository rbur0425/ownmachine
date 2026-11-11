import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('viewer_service',ROOT/'scripts/render-viewer-service.py')
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
from ownmachine.config import Config

class ViewerServiceTests(unittest.TestCase):
    def test_configuration_is_preserved_without_shell_or_vm_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'source with spaces';(root/'viewer').mkdir(parents=True)
            (root/'viewer/server.py').touch()
            unit=service.render(root,sys.executable,Config('example','/state/with $ and %','guest'),45678,True,True)
        self.assertIn('"--vm-name" "guest"',unit)
        self.assertIn('"/state/with $$ and %%"',unit)
        self.assertIn('"--port" "45678"',unit)
        self.assertIn('"--read-only"',unit)
        self.assertIn('"--swap-red-blue"',unit)
        self.assertIn('Restart=on-failure',unit)
        self.assertNotIn('ExecStartPre',unit)
        self.assertNotIn('/bin/sh',unit)
    def test_arguments_cannot_inject_unit_directives(self):
        for value in ('/state\nExecStart=/bin/false','/state\r','/state\x00'):
            with self.assertRaises(ValueError):service.render(ROOT,sys.executable,Config('example',value))
        self.assertEqual(service.quote('a"b\\c'), '"a\\"b\\\\c"')
    def test_missing_source_and_invalid_port_refused(self):
        with self.assertRaises(ValueError):service.render('/missing-source',sys.executable,Config('example','/state'))
        with self.assertRaises(ValueError):service.render(ROOT,sys.executable,Config('example','/state'),65536)
