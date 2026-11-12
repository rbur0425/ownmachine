#!/usr/bin/env python3
"""Prepare a private, key-only Archboot image from an operator-verified ISO.

Host operator utility, never part of the Hermes plugin. Requires xorriso,
mtools and zstd. The output contains a per-guest host private key and must
never be published or shared. No VM disk is changed by this command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid
from setup_support import install_exact, private_read


def records(data, start=0):
    offset=start
    while True:
        begin=offset
        if data[offset:offset+6] != b'070701':raise ValueError('unsupported_cpio')
        fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        size,namesize=fields[6],fields[11]
        if not 1 <= namesize <= 4096:raise ValueError('invalid_cpio_name')
        end=offset+110+namesize
        if end > len(data) or data[end-1] != 0:raise ValueError('truncated_cpio')
        name=data[offset+110:end-1].decode()
        offset=(end+3)//4*4;offset=(offset+size+3)//4*4
        if offset > len(data):raise ValueError('truncated_cpio')
        yield name,begin,offset
        if name=='TRAILER!!!':return


def pack(entries):
    output=bytearray()
    for index,(name,mode,content) in enumerate([*entries,('TRAILER!!!',0,b'')]):
        name=name.encode()+b'\0'
        fields=[0x70000000+index,mode,0,0,1,0,len(content),0,0,0,0,len(name),0]
        output+=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name
        output+=b'\0'*(-len(output)%4);output+=content;output+=b'\0'*(-len(output)%4)
    output+=b'\0'*(-len(output)%512)
    return bytes(output)


def seed(directory):
    reg=stat.S_IFREG;link=stat.S_IFLNK
    return [
        ('./etc/ownmachine-bootstrap',stat.S_IFDIR|0o700,b''),
        ('./root/.ssh',stat.S_IFDIR|0o700,b''),
        ('./root/.ssh/authorized_keys',reg|0o600,b'restrict '+private_read(directory/'guest.pub')),
        ('./etc/ssh/ssh_host_ed25519_key',reg|0o600,private_read(directory/'host')),
        ('./etc/ssh/ssh_host_ed25519_key.pub',reg|0o644,private_read(directory/'host.pub')),
        ('./etc/machine-id',reg|0o444,(uuid.uuid4().hex+'\n').encode()),
        ('./etc/ownmachine-bootstrap/sshd_config',reg|0o600,b'''Port 22
HostKey /etc/ssh/ssh_host_ed25519_key
AuthorizedKeysFile /root/.ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
AllowUsers root
AllowTcpForwarding no
X11Forwarding no
PermitTunnel no
UsePAM no
'''),
        ('./etc/systemd/network/00-ownmachine-bootstrap.network',reg|0o644,b'''[Match]
Name=en* eth*
[Network]
DHCP=yes
LinkLocalAddressing=no
[DHCPv4]
ClientIdentifier=mac
'''),
        ('./etc/systemd/system/sshd.service',link|0o777,b'/dev/null'),
        ('./etc/systemd/system/sshd.socket',link|0o777,b'/dev/null'),
        ('./etc/systemd/system/ttyd.service',link|0o777,b'/dev/null'),
        ('./etc/systemd/system/ownmachine-bootstrap.service',reg|0o644,b'''[Unit]
Description=OwnMachine temporary key-only installer access
ConditionVirtualization=apple
Wants=systemd-networkd.service systemd-resolved.service
After=systemd-networkd.service
[Service]
ExecStart=/usr/bin/sshd -D -e -f /etc/ownmachine-bootstrap/sshd_config
Restart=on-failure
[Install]
WantedBy=multi-user.target
'''),
        ('./etc/systemd/system/multi-user.target.wants/ownmachine-bootstrap.service',link|0o777,b'../ownmachine-bootstrap.service')]


def run(argv,log):
    subprocess.run(argv,check=True,stdout=log,stderr=log,timeout=900)


def prepare(iso,digest,directory):
    if not iso.is_absolute() or not directory.is_absolute() or not re.fullmatch('[a-f0-9]{64}',digest):
        raise ValueError('absolute_paths_and_verified_sha256_required')
    if any(p.is_symlink() for p in (directory,*directory.parents)):raise ValueError('symlink_directory')
    with iso.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:raise ValueError('iso_checksum_mismatch')
    for command in ('xorriso','mcopy','zstd','ssh-keygen'):
        if not shutil.which(command):raise ValueError('missing_dependency_'+command)
    # Refuse a partial run rather than overwriting keys or blessing a new image.
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.umask(0o077)
    with (directory/'build.log').open('xb') as log:
        for name in ('guest','host'):
            run(['ssh-keygen','-q','-t','ed25519','-N','','-C','ownmachine-bootstrap','-f',str(directory/name)],log)
            (directory/(name+'.pub')).chmod(0o600)
        entries=seed(directory)
        run(['xorriso','-osirrox','on','-indev',str(iso),'-extract','/efi.img',str(directory/'efi.img')],log)
        (directory/'efi.img').chmod(0o600)
        run(['mcopy','-i',str(directory/'efi.img'),'::/boot/initrd-aarch64.img',str(directory/'original.img')],log)
        original=(directory/'original.img').read_bytes();offset=0
        while original[offset:offset+4] != b'\x28\xb5\x2f\xfd':
            for _,_,offset in records(original,offset):pass
            while offset<len(original) and original[offset]==0:offset+=1
            if offset>=len(original):raise ValueError('compressed_root_missing')
        install_exact(directory/'root.zst',original[offset:])
        run(['zstd','-q','-d',str(directory/'root.zst'),'-o',str(directory/'root.cpio')],log)
        root=(directory/'root.cpio').read_bytes();replaced={n for n,_,_ in entries}
        with (directory/'merged.cpio').open('xb') as stream:
            for name,begin,end in records(root):
                if name!='TRAILER!!!' and name not in replaced:stream.write(root[begin:end])
            stream.write(pack(entries))
        run(['zstd','-q','-19','-T2',str(directory/'merged.cpio'),'-o',str(directory/'merged.zst')],log)
        install_exact(directory/'initrd.img',original[:offset]+(directory/'merged.zst').read_bytes())
        run(['mcopy','-o','-i',str(directory/'efi.img'),str(directory/'initrd.img'),'::/boot/initrd-aarch64.img'],log)
        image=directory/'bootstrap.iso'
        run(['xorriso','-indev',str(iso),'-outdev',str(image),'-map',str(directory/'efi.img'),'/efi.img','-boot_image','any','replay','-commit'],log)
        image.chmod(0o600)
    alias='ownmachine-bootstrap-'+uuid.uuid4().hex
    install_exact(directory/'known_hosts',alias.encode()+b' '+private_read(directory/'host.pub'))
    with image.open('rb') as stream:output_digest=hashlib.file_digest(stream,'sha256').hexdigest()
    result=dict(schema_version=1,source_sha256=digest,iso=str(image),iso_sha256=output_digest,
                identity_file=str(directory/'guest'),known_hosts=str(directory/'known_hosts'),host_key_alias=alias,
                scope='guest SSH identity; root login is removed by installed-guest hardening')
    install_exact(directory/'bootstrap.json',(json.dumps(result,indent=2)+'\n').encode())
    # Only generated build intermediates; retain keys, image, receipt and log.
    for name in ('efi.img','original.img','root.zst','root.cpio','merged.cpio','merged.zst','initrd.img'):
        (directory/name).unlink()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--iso-sha256',required=True)
    parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.iso,args.iso_sha256,args.state_dir)))


if __name__=='__main__':main()
