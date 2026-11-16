"""Verify final file permissions under restrictive operator umasks."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
import kvm_backend
spec=importlib.util.spec_from_file_location('mode_installer',ROOT/'scripts/install-kvm-security.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class InstallModes(unittest.TestCase):
    def test_explicit_modes_and_idempotent_repair(self):
        # Parent ownership is independently checked in the live root fixture.
        with tempfile.TemporaryDirectory() as td:
            path=Path(td).resolve()/'guest.key'
            original=Path.lstat
            def root_owned(p):
                st=original(p)
                if p==path:return st
                fields=list(st);fields[0]=(fields[0]&~0o777)|0o755;fields[4]=0
                return os.stat_result(fields)
            for mask in (0o022,0o027,0o077):
                for mode in (0o440,0o644,0o755):
                    with self.subTest(mask=oct(mask),mode=oct(mode)):
                        path.unlink(missing_ok=True)
                        old=os.umask(mask)
                        try:
                            with patch.object(Path,'lstat',root_owned):installer.write(path,b'fixture',mode)
                            self.assertEqual(path.stat().st_mode&0o777,mode)
                            path.chmod(0o400)
                            with patch.object(Path,'lstat',root_owned),patch.object(kvm_backend,'protected'):
                                installer.write(path,b'fixture',mode)
                                with self.assertRaisesRegex(ValueError,'existing_install_differs'):
                                    installer.write(path,b'different',mode)
                            self.assertEqual(path.stat().st_mode&0o777,mode)
                        finally:os.umask(old)

if __name__=='__main__':unittest.main()
