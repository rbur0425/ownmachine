#!/usr/bin/env python3
"""Reviewed spike-only host setup. Configuration is operator-owned, never bundled."""
import grp
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import shlex
import subprocess
import sys
import uuid

def run(*args):
    subprocess.run(args, check=True)

if os.geteuid() != 0:
    raise SystemExit('Administrator authentication required')
c = json.loads(Path(sys.argv[1]).read_text())
for k in ('agent_user', 'viewer_user', 'operator_user', 'console_group', 'vm_name', 'bridge'):
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,30}', c[k]):
        raise SystemExit('Invalid identifier: '+k)
uuid.UUID(c['vm_uuid'])
uuid.UUID(c['network_uuid'])
net = ipaddress.ip_network(c['subnet'])
if net.version != 4 or not net.is_private or ipaddress.ip_address(c['guest_ip']) not in net:
    raise SystemExit('Invalid guest network')
operator = pwd.getpwnam(c['operator_user'])
for k in ('source_dir', 'storage_dir'):
    p = Path(c[k])
    if not p.is_absolute() or any(x.is_symlink() for x in (p, *p.parents)):
        raise SystemExit('Unsafe path')
conf = Path('/etc/libvirt/libvirtd.conf')
text = conf.read_text()
active = re.findall(r'^\s*access_drivers\s*=.*$', text, re.M)
if active and active != ['access_drivers = [ "polkit" ]']:
    raise SystemExit('Existing access driver needs operator review')
backup = conf.with_name('libvirtd.conf.ownmachine-spike-before')
if not backup.exists(): shutil.copy2(conf, backup)
try: grp.getgrnam(c['console_group'])
except KeyError: run('groupadd', '--system', c['console_group'])
for role in ('agent', 'viewer'):
    user = c[role+'_user']
    try:
        pwd.getpwnam(user)
        raise SystemExit('Account already exists; inspect before rerunning: '+user)
    except KeyError: pass
    run('useradd', '--create-home', '--shell', '/bin/bash', '--groups', 'libvirt', user)
    entry = pwd.getpwnam(user)
    home = Path(entry.pw_dir)
    home.chmod(0o700)
    ssh = home/'.ssh'; ssh.mkdir(mode=0o700)
    key = c[role+'_public_key']
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [A-Za-z0-9_-]+)?', key):
        raise SystemExit('Invalid public key')
    command = shlex.join(['/usr/bin/python3', c['source_dir']+'/relay.py', role])
    command = command.replace('\\', '\\\\').replace('"', '\\"')
    auth = ssh/'authorized_keys'
    auth.write_text('restrict,command="'+command+'" '+key+'\n')
    auth.chmod(0o600)
    for p in (ssh, auth): os.chown(p, entry.pw_uid, entry.pw_gid)
run('usermod', '-aG', c['console_group'], c['viewer_user'])
run('usermod', '-aG', c['console_group'], 'libvirt-qemu')
console = Path('/var/lib/libvirt/ownmachine-spike-console')
console.mkdir(mode=0o750)
os.chown(console, pwd.getpwnam('libvirt-qemu').pw_uid, grp.getgrnam(c['console_group']).gr_gid)
console.chmod(0o750)
run('setfacl', '-m', f"d:u:{c['viewer_user']}:rwx,d:o::---", str(console))
c['console_socket'] = str(console/(c['vm_uuid']+'.sock'))
runtime = Path(c['source_dir']); runtime.mkdir(parents=True, mode=0o755, exist_ok=True)
os.chown(runtime, operator.pw_uid, operator.pw_gid); runtime.chmod(0o755)
# Only this operator can update spike code; runtime identities cannot.
storage = Path(c['storage_dir']); storage.chmod(0o711)
public_config = runtime/'host.json'
public_config.write_text(json.dumps(c, indent=2)+'\n'); public_config.chmod(0o644)
os.chown(public_config, operator.pw_uid, operator.pw_gid)
rule = '''polkit.addRule(function(action, subject) {
  if (action.id.indexOf("org.libvirt.api.") !== 0) return;
  var agent = subject.user === AGENT, viewer = subject.user === VIEWER;
  if (!agent && !viewer) {
    if (subject.user === "root" || subject.isInGroup("libvirt")) return polkit.Result.YES;
    return;
  }
  if (action.lookup("connect_driver") !== "QEMU") return polkit.Result.NO;
  var allowed = ["org.libvirt.api.connect.getattr", "org.libvirt.api.connect.read", "org.libvirt.api.connect.search-domains"];
  if (allowed.indexOf(action.id) >= 0) return polkit.Result.YES;
  if (action.lookup("domain_uuid") !== UUID) return polkit.Result.NO;
  allowed = ["org.libvirt.api.domain.getattr", "org.libvirt.api.domain.read"];
  if (viewer) allowed = allowed.concat(["org.libvirt.api.domain.start", "org.libvirt.api.domain.init-control"]);
  return allowed.indexOf(action.id) >= 0 ? polkit.Result.YES : polkit.Result.NO;
});
'''.replace('AGENT',json.dumps(c['agent_user'])).replace('VIEWER',json.dumps(c['viewer_user'])).replace('UUID',json.dumps(c['vm_uuid']))
Path('/etc/polkit-1/rules.d/00-ownmachine-spike.rules').write_text(rule)
if not active: conf.write_text(text+'\naccess_drivers = [ "polkit" ]\n')
run('systemctl', 'restart', 'libvirtd')
# Only this dedicated bridge is affected. No global flush, Docker edits or SSH policy change.
fw = f'''table inet ownmachine_windows_spike {{
 chain input {{ type filter hook input priority -20; policy accept;
  iifname "{c['bridge']}" ct state established,related accept
  iifname "{c['bridge']}" udp dport {{ 53, 67 }} accept
  iifname "{c['bridge']}" tcp dport 53 accept
  iifname "{c['bridge']}" drop
 }}
 chain forward {{ type filter hook forward priority -20; policy accept;
  iifname "{c['bridge']}" ip daddr {{ 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 }} drop
  iifname "{c['bridge']}" meta nfproto ipv6 drop
 }}
}}
'''
fwpath = Path('/etc/ownmachine-windows-spike.nft');fwpath.write_text(fw)
run('nft','--check','-f',str(fwpath))
run('nft','-f',str(fwpath))
print('Dedicated runtime identities, domain ACLs and bridge firewall installed. No VM created.')
print('Firewall is spike-session state only; a host restart requires revalidation before starting the guest.')
