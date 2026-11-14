#!/usr/bin/env python3
"""Read-only role checks plus never-started domain/network ACL fixtures."""
import json, os, pathlib, subprocess, sys, tempfile, uuid
if os.geteuid()!=0:raise SystemExit('Administrator access required to impersonate runtime roles')
c=json.loads(pathlib.Path(sys.argv[1]).read_text())
def run(args,user=None):
 return subprocess.run((['runuser','-u',user,'--'] if user else [])+args,capture_output=True,text=True,timeout=15)
def virsh(args,user=None):return run(['virsh','-c','qemu:///system']+args,user)
fixture=str(uuid.uuid4());name='ownmachine-acl-fixture-'+fixture[:8]
xml=f'<domain type="kvm"><name>{name}</name><uuid>{fixture}</uuid><memory unit="MiB">128</memory><vcpu>1</vcpu><os><type arch="x86_64">hvm</type></os><devices/></domain>'
results=[]
network_fixture=str(uuid.uuid4())
network_name='ownmachine-net-fixture-'+network_fixture[:8]
with tempfile.NamedTemporaryFile(mode='w',suffix='.xml') as f:
 f.write(xml);f.flush()
 p=virsh(['define',f.name])
 if p.returncode:raise SystemExit('Could not define isolated diskless ACL fixture')
with tempfile.NamedTemporaryFile(mode='w',suffix='.xml') as f:
 f.write(f'<network><name>{network_name}</name><uuid>{network_fixture}</uuid></network>');f.flush()
 p=virsh(['net-define',f.name])
 if p.returncode:
  virsh(['undefine',fixture])
  raise SystemExit('Could not define isolated network ACL fixture')
try:
 for role in ('agent','viewer'):
  user=c[role+'_user']
  p=virsh(['list','--all','--uuid'],user)
  results.append(dict(check=role+'_sees_only_configured_domain',passed=p.returncode==0 and p.stdout.split()==[c['vm_uuid']]))
  p=virsh(['dumpxml',fixture],user)
  results.append(dict(check=role+'_other_domain_read_denied',passed=p.returncode!=0))
  p=virsh(['undefine',fixture],user)
  results.append(dict(check=role+'_other_domain_mutation_denied',passed=p.returncode!=0))
  p=virsh(['net-dumpxml',c['network_uuid']],user)
  results.append(dict(check=role+'_configured_network_read',passed=(p.returncode==0)==(role=='viewer')))
  p=virsh(['net-dumpxml',network_fixture],user)
  results.append(dict(check=role+'_other_network_read_denied',passed=p.returncode!=0))
  p=virsh(['net-undefine',network_fixture],user)
  results.append(dict(check=role+'_other_network_mutation_denied',passed=p.returncode!=0))
  p=virsh(['qemu-monitor-command',c['vm_uuid'],'{"execute":"query-status"}'],user)
  results.append(dict(check=role+'_qemu_monitor_denied',passed=p.returncode!=0))
  p=run(['/usr/bin/python3','-c','import socket,sys; s=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.close()',c['console_socket']],user)
  results.append(dict(check=role+'_console_access',passed=(p.returncode==0)==(role=='viewer')))
  p=run(['/usr/bin/python3','-c','import sys; open(sys.argv[1],"rb").close()',str(pathlib.Path(sys.argv[1]).parent/'guest-key')],user)
  results.append(dict(check=role+'_guest_key_access',passed=(p.returncode==0)==(role=='agent')))
finally:
 virsh(['undefine',fixture])
 virsh(['net-undefine',network_fixture])
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
