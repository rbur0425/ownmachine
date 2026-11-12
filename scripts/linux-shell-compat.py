#!/usr/bin/env python3
"""Qualify the pinned Omarchy palette against Qt 6.12's Color singleton.

All inputs are validated before writes. This is an operator provisioning helper,
not a runtime modification of Hermes or the user's applications.
"""
import hashlib
import json
from pathlib import Path
import re


def apply(root, manifest):
    changes=[]
    for relative, expected in manifest.items():
        path=root/relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts or path.is_symlink():
            raise ValueError('unsafe_shell_patch_path')
        original=path.read_bytes()
        if hashlib.sha256(original).hexdigest()!=expected:
            raise ValueError('pinned_shell_source_mismatch')
        text=original.decode()
        if 'OwnMachineCommons' in text:raise ValueError('shell_alias_collision')
        text=re.sub(r'(?<![\w.])Color\.', 'OwnMachineCommons.Color.', text)
        # An explicit namespace avoids Qt's unqualified singleton precedence.
        lines=text.splitlines(keepends=True)
        index=next((i for i,line in enumerate(lines) if line.startswith('import ')),None)
        if index is None:raise ValueError('shell_imports_missing')
        lines.insert(index,'import qs.Commons as OwnMachineCommons\n')
        changes.append((path,''.join(lines)))
    for path,text in changes:
        path.write_text(text)
        path.chmod(0o644)
    return len(changes)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps({'patched_files':apply(args.root,json.loads(args.manifest.read_text()))}))
