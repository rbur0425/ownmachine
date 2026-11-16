#!/usr/bin/env python3
"""Grant only the configured viewer access to this spike's private console."""
import json, os, pathlib, pwd, stat, subprocess, sys
if os.geteuid()!=0: raise SystemExit('Run as administrator')
c=json.loads(pathlib.Path(sys.argv[1]).read_text())
p=pathlib.Path(c['console_socket']); d=p.parent
if d!=pathlib.Path('/var/lib/libvirt/ownmachine-spike-console'):raise SystemExit('Unexpected console directory')
viewer=pwd.getpwnam(c['viewer_user'])
if not d.is_dir() or d.is_symlink() or d.stat().st_mode & 7:raise SystemExit('Console directory is not private')
subprocess.run(['setfacl','-m',f'd:u:{viewer.pw_uid}:rwx,d:o::---',str(d)],check=True)
if p.exists():
    if not stat.S_ISSOCK(p.lstat().st_mode):raise SystemExit('Unexpected console file')
    subprocess.run(['setfacl','-m',f'u:{viewer.pw_uid}:rw',str(p)],check=True)
print('Private console ACL installed for the viewer; future sockets inherit it. VM was not restarted.')
