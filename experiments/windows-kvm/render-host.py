#!/usr/bin/env python3
"""Render a new isolated domain/network; never defines, starts or overwrites a VM."""
import argparse
import ipaddress
import json
from pathlib import Path
import uuid
from xml.sax.saxutils import escape, quoteattr
p=argparse.ArgumentParser();p.add_argument('config',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();c=json.loads(a.config.read_text());a.output.mkdir(parents=True,exist_ok=True)
name=escape(c['vm_name']);ident=str(uuid.UUID(c['vm_uuid']))
net=ipaddress.ip_network(c['subnet']);gateway=str(net.network_address+1)
mac='52:54:00:'+':'.join(ident.replace('-','')[i:i+2] for i in (0,2,4))
network=f'''<network xmlns:dnsmasq="http://libvirt.org/schemas/network/dnsmasq/1.0"><name>{name}</name><uuid>{str(uuid.UUID(c["network_uuid"]))}</uuid><dns enable="no"/><forward mode="nat"/><bridge name={quoteattr(c['bridge'])} stp="on" delay="0"/><ip address={quoteattr(gateway)} netmask={quoteattr(str(net.netmask))}><dhcp><host mac={quoteattr(mac)} name="ownmachine-guest" ip={quoteattr(c['guest_ip'])}/></dhcp></ip><dnsmasq:options><dnsmasq:option value={quoteattr("dhcp-option=6,"+str(ipaddress.ip_address(c.get("dns_server","9.9.9.9"))))}/></dnsmasq:options></network>'''
root=Path(c['storage_dir'])
domain=f'''<domain type="kvm"><name>{name}</name><uuid>{ident}</uuid>
<memory unit="MiB">{int(c.get('memory_mib',8192))}</memory><vcpu>{int(c.get('vcpus',4))}</vcpu>
<os firmware="efi"><type arch="x86_64" machine="q35">hvm</type><firmware><feature enabled="yes" name="enrolled-keys"/><feature enabled="yes" name="secure-boot"/></firmware><boot dev="cdrom"/><boot dev="hd"/></os>
<features><acpi/><apic/><smm state="on"/></features><cpu mode="host-passthrough"/><clock offset="localtime"/>
<on_poweroff>destroy</on_poweroff><on_reboot>restart</on_reboot><on_crash>destroy</on_crash>
<devices><emulator>/usr/bin/qemu-system-x86_64</emulator>
<disk type="file" device="disk"><driver name="qemu" type="qcow2"/><source file={quoteattr(str(root/'state/windows.qcow2'))}/><target dev="sda" bus="sata"/></disk>
<disk type="file" device="cdrom"><driver name="qemu" type="raw"/><source file={quoteattr(str(root/'media/windows-enterprise-eval.iso'))}/><target dev="sdb" bus="sata"/><readonly/></disk>
<disk type="file" device="cdrom"><driver name="qemu" type="raw"/><source file={quoteattr(str(root/'state/bootstrap.iso'))}/><target dev="sdc" bus="sata"/><readonly/></disk>
<interface type="network"><mac address={quoteattr(mac)}/><source network={quoteattr(c['vm_name'])}/><model type="e1000e"/></interface>
<input type="tablet" bus="usb"/><controller type="usb" model="qemu-xhci"/>
<graphics type="vnc"><listen type="socket" socket={quoteattr(c['console_socket'])}/></graphics>
<video><model type="vga" vram="16384" heads="1" primary="yes"/></video>
<tpm model="tpm-crb"><backend type="emulator" version="2.0"/></tpm><memballoon model="none"/>
</devices></domain>'''
(a.output/'network.xml').write_text(network)
(a.output/'domain.xml').write_text(domain)
print('Domain and network templates rendered; VM not created.')
