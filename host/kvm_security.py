#!/usr/bin/env python3
"""Root-only persistent firewall apply and read-only, live runtime verification.

Runtime sudoers authorizes --check with one exact root-owned config only.
No request-supplied commands, nft text or output paths are accepted.
"""
import ipaddress
import xml.etree.ElementTree as ET
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from kvm_backend import protected

ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}


def run(*args):
    return subprocess.run(args,env=ENV,check=True,capture_output=True,text=True,timeout=10).stdout


def canonical(value):
    if isinstance(value,dict):
        return {k:canonical(v) for k,v in value.items() if k not in {'handle','index','position'}}
    if isinstance(value,list): return [canonical(v) for v in value if not (isinstance(v,dict) and 'metainfo' in v)]
    return value


def live_hash(table):
    data=json.loads(run('/usr/sbin/nft','-j','list','table','inet',table))
    return hashlib.sha256(json.dumps(canonical(data),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def polkit_configured(text):
    lines=[line.strip() for line in re.findall(r'^[ \t]*access_drivers[ \t]*=.*$',text,re.M)]
    return lines==['access_drivers = [ "polkit" ]']


def load(path):
    c=json.loads(protected(path).read_text())
    m=json.loads(protected(str(path)+'.security.json').read_text())
    if m['config_sha256']!=hashlib.sha256(Path(path).read_bytes()).hexdigest():
        raise ValueError('configuration_changed')
    if not re.fullmatch(r'ownmachine_[a-f0-9]{32}',m['table']): raise ValueError('invalid_table')
    for key in ('rules','policy','access_config'):
        data=protected(m[key]).read_bytes()
        if hashlib.sha256(data).hexdigest()!=m[key+'_sha256']: raise ValueError('security_file_changed')
    return c,m


def main():
    if os.geteuid()!=0 or len(sys.argv)!=3 or sys.argv[1] not in ('--check','--apply'):
        raise ValueError('root_pinned_operation_required')
    c,m=load(Path(sys.argv[2]))
    unit='ownmachine-kvm-'+c['vm_uuid'].replace('-','')+'.service'
    if sys.argv[1]=='--check' and run('/usr/bin/systemctl','is-enabled',unit).strip()!='enabled':
        raise ValueError('persistent_firewall_service_required')
    if sys.argv[1]=='--apply':
        # Only replace this installation's table, atomically. Never flush global rules.
        exists=subprocess.run(['/usr/sbin/nft','list','table','inet',m['table']],env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10).returncode==0
        text=(f"delete table inet {m['table']}\n" if exists else '')+Path(m['rules']).read_text()
        subprocess.run(['/usr/sbin/nft','-f','-'],input=text,env=ENV,check=True,capture_output=True,text=True,timeout=10)
    if sys.argv[1]=='--apply':
        # Boot ordering: this unit precedes libvirt. Never query/activate libvirt
        # while its Before= dependency is waiting for our oneshot to finish.
        if live_hash(m['table'])!=m['nft_sha256']: raise ValueError('live_firewall_drift')
        print(json.dumps({'ok':True,'vm_uuid':c['vm_uuid']}))
        return
    if run('/usr/bin/virsh','-c','qemu:///system','net-uuid',c['network_name']).strip()!=c['network_uuid']:
        raise ValueError('network_identity_mismatch')
    network=ET.fromstring(run('/usr/bin/virsh','-c','qemu:///system','net-dumpxml',c['network_uuid']))
    bridge=network.find('bridge'); address=network.find('ip'); forward=network.find('forward')
    if (bridge is None or bridge.get('name')!=m['bridge'] or address is None
            or str(ipaddress.ip_network(address.get('address')+'/'+address.get('netmask'),strict=False))!=c['subnet']
            or forward is None or forward.get('mode')!='nat'):
        raise ValueError('network_isolation_drift')
    info=run('/usr/bin/virsh','-c','qemu:///system','dominfo',c['vm_uuid'])
    if not re.search(r'^Autostart:\s+disable\s*$',info,re.M): raise ValueError('autostart_must_be_disabled')
    if live_hash(m['table'])!=m['nft_sha256']: raise ValueError('live_firewall_drift')
    access=Path(m['access_config']).read_text()
    if not polkit_configured(access):
        raise ValueError('libvirt_acl_required')
    print(json.dumps({'ok':True,'vm_uuid':c['vm_uuid']}))


if __name__=='__main__':
    try: main()
    except Exception:
        print(json.dumps({'ok':False,'code':'kvm_security_not_ready'}))
        raise SystemExit(2)
