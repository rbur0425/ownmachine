"""Experimental input requires explicit consent and a matching compiler."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from setup_support import module
inputs=module('tested_linux_input_module','scripts/linux-input-module.py')

class InputModuleTests(unittest.TestCase):
    def test_no_opt_in_never_probes_or_loads(self):
        with patch.object(inputs.platform,'system',return_value='Linux'),patch.object(inputs.os,'geteuid',return_value=1000),patch.object(inputs,'call',side_effect=AssertionError('must not execute')):
            with self.assertRaisesRegex(ValueError,'opt_in'):
                inputs.execute(SimpleNamespace(enable_experimental_input=False,apply=True,step='enable'))

    def test_preview_is_read_only(self):
        with patch.object(inputs.platform,'system',return_value='Linux'),patch.object(inputs.os,'geteuid',return_value=1000),patch.object(inputs,'call',side_effect=AssertionError('must not execute')):
            self.assertEqual(inputs.execute(SimpleNamespace(enable_experimental_input=True,apply=False,step='build'))['stage'],'planned')

    def test_compiler_mismatch_is_refused_before_build(self):
        with patch.object(inputs,'call',side_effect=['0.57.2\n','16.1.1\n','GCC: 15.2.0']),patch.object(inputs.shutil,'which',return_value='/usr/bin/Hyprland'),patch.object(inputs,'digest',side_effect=AssertionError('must stop before recording')):
            with self.assertRaisesRegex(ValueError,'compiler_mismatch'):inputs.fingerprint()

if __name__=='__main__':unittest.main()
