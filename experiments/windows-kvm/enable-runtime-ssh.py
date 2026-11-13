#!/usr/bin/env python3
"""Add only the dedicated spike identities to the host's SSH allowlist."""
import json, os, re, subprocess, sys
from pathlib import Path
if os.geteuid()!=0:raise SystemExit('Run with administrator authentication')
c=json.loads(Path(sys.argv[1]).read_text())
users=[c['agent_user'],c['viewer_user']]
if any(not re.fullmatch('[a-z][a-z0-9-]{1,30}',x) for x in users):raise SystemExit('Invalid account')
p=Path('/etc/ssh/sshd_config.d/10-ownmachine-windows-spike.conf')
if p.exists():raise SystemExit('Existing SSH fragment needs review')
p.write_text('AllowUsers '+' '.join(users)+'\nMatch User '+','.join(users)+'\n    AuthenticationMethods publickey\n    PasswordAuthentication no\n    KbdInteractiveAuthentication no\n    AllowTcpForwarding no\n    AllowStreamLocalForwarding no\n    AllowAgentForwarding no\n    X11Forwarding no\n    PermitTTY no\nMatch all\n')
try:subprocess.run(['/usr/sbin/sshd','-t'],check=True)
except Exception:p.unlink();raise
subprocess.run(['systemctl','reload','ssh'],check=True)
print('Only the two spike accounts added; key-only authentication and forwarding restrictions enforced.')
for user in users:
    r=subprocess.run(['runuser','-u',user,'--','virsh','-c','qemu:///system','list','--all'],capture_output=True,text=True)
    print(user,'libvirt listing exit:',r.returncode,r.stdout.strip(),r.stderr.strip())
