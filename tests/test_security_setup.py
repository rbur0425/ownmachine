import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).parents[1]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
keys=load('host_keys','render-host-keys.py')
installer=load('secure_installer','install-hermes.py')

class SecuritySetupTests(unittest.TestCase):
    def key(self,char):
        return 'ssh-ed25519 '+base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20'+char*32).decode()
    def test_two_forced_roles_and_no_key_reuse(self):
        result=keys.render('/usr/bin/python3','/home/vm/relay.py',self.key(b'a'),self.key(b'b'))
        self.assertEqual(len(result.splitlines()),2)
        self.assertIn('--role agent"',result);self.assertIn('--role viewer"',result)
        self.assertTrue(all(row.startswith('restrict,command=') for row in result.splitlines()))
        with self.assertRaises(ValueError):keys.render('/python','/relay',self.key(b'a'),self.key(b'a'))
        for value in ('relative','/path\ncommand'):
            with self.assertRaises(ValueError):keys.render(value,'/relay',self.key(b'a'),self.key(b'b'))
    def test_fresh_profile_disables_host_execution_and_file_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            home=installer.install(Path(temp)/'home',installer.Config('agent-mac',str(Path(temp)/'control')))
            settings=json.loads((home/'config.yaml').read_text())
            self.assertEqual(set(settings['agent']['disabled_toolsets']),{'terminal','file','code_execution'})
            self.assertEqual(settings['computer_use']['permission_mode'],'standard')
