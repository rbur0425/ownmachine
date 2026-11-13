import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_support import module
compat=module('tested_shell_compat','scripts/linux-shell-compat.py')

class ShellCompatibilityTests(unittest.TestCase):
    def test_validates_all_sources_before_changing_any(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=b'import QtQuick\nimport qs.Commons\nItem { property color ink: Color.menu.text }\n'
            (root/'a.qml').write_bytes(original);(root/'b.qml').write_text('changed')
            manifest={name:hashlib.sha256(original).hexdigest() for name in ('a.qml','b.qml')}
            with self.assertRaisesRegex(ValueError,'pinned_shell_source_mismatch'):compat.apply(root,manifest)
            self.assertEqual((root/'a.qml').read_bytes(),original)
            (root/'b.qml').write_bytes(original)
            self.assertEqual(compat.apply(root,manifest),2)
            self.assertIn('OwnMachineCommons.Color.menu.text',(root/'a.qml').read_text())
            self.assertIn('import qs.Commons as OwnMachineCommons',(root/'a.qml').read_text())
            self.assertEqual((root/'a.qml').stat().st_mode & 0o777,0o644)
            with self.assertRaisesRegex(ValueError,'pinned_shell_source_mismatch'):compat.apply(root,manifest)
