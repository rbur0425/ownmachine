"""Build a private fresh Omarchy disk from verified upstream artifacts."""
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import tempfile
from setup_support import ROOT, install_exact
from windows_provision import sha

PINS={
    'image':'fea962bb66bef8f922900018f8241e50a2d1a00268715541882479016235dc9f',
    'driver_archive':'a9b89435e4257467749e5da12770d74882e1e250925e3079b05a392f824b0e71',
    'input_archive':'bea7f5a549db16abb7388002a1b63a8d100c704e95587e17082393901fc9f459',
    'cmake_wheel':'85625a9b6d5e88ff99c7eb79123d85570844e77ac076366cf75c609cc0b1b579',
    'ninja_wheel':'65a24341b5ac09fcadcc37082660be40a94174e51a937fabf6e2cae26225fa2c',
}

def prepare_disk(state,p):
    if p['guest_user']!='omarchy':raise ValueError('upstream_image_account_required')
    for key,expected in PINS.items():
        if sha(p[key])!=expected:raise ValueError('artifact_hash_mismatch_'+key)
    env=dict(os.environ,LIBGUESTFS_BACKEND='direct')
    if p.get('guestfs_appliance'):
        env['LIBGUESTFS_PATH']=p['guestfs_appliance']
    disk=state/'omarchy.qcow2'
    if disk.exists():raise ValueError('fresh_disk_required')
    subprocess.run(['qemu-img','convert','-f','qcow2','-O','qcow2',p['image'],str(disk)],check=True)
    subprocess.run(['qemu-img','resize','-q','-f','qcow2',str(disk),str(p['disk_gb'])+'G'],check=True)
    password=secrets.token_urlsafe(24)
    install_exact(state/'guest-password',(password+'\n').encode())
    with tempfile.TemporaryDirectory(dir=state) as tmp:
        root=Path(tmp);app=root/'opt/ownmachine-kvm';app.mkdir(parents=True)
        def put(name,content,mode=0o644):
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content);dest.chmod(mode)
        assets={ROOT/'scripts'/name:name for name in ('linux-guest.py','secure-linux-guest.py','linux-input-module.py')}
        assets.update({ROOT/'scripts/omarchy'/name:name for name in ('first-boot.py','guest-entry.py')})
        assets.update({Path(p['driver_archive']):'driver.tar.gz',Path(p['input_archive']):'input.tar',state/'guest.pub':'runtime.pub',state/'guest-setup.pub':'setup.pub'})
        for key in ('cmake_wheel','ninja_wheel'):
            assets[Path(p[key])]=Path(p[key]).name
        for src,name in assets.items():
            shutil.copyfile(src,app/name);(app/name).chmod(0o644)
        put('opt/ownmachine-kvm/guest.json',json.dumps(dict(user=p['guest_user'],source=str(ipaddress.ip_network(p['subnet']).network_address+1))))
        put('opt/ownmachine-kvm/password',password+'\n',0o600)
        put('etc/ssh/ownmachine_host_ed25519_key',(state/'guest-host').read_text(),0o600)
        put('etc/ssh/sshd_config.d/00-00-ownmachine.conf','HostKey /etc/ssh/ownmachine_host_ed25519_key\nAuthorizedKeysFile .ssh/authorized_keys .ssh/ownmachine-setup\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nAllowTcpForwarding no\nAllowAgentForwarding no\n')
        put('usr/local/libexec/ownmachine-hardening-gate.py',(ROOT/'scripts/linux-hardening-gate.py').read_text(),0o755)
        put('etc/systemd/logind.conf.d/99-ownmachine-kvm.conf','[Login]\nHandlePowerKey=poweroff\nPowerKeyIgnoreInhibited=yes\n')
        put('etc/systemd/system/ownmachine-firstboot.service','[Unit]\nDescription=Harden OwnMachine guest\nAfter=sshd.service\nWants=sshd.service\nBefore=display-manager.service\nConditionPathExists=!/etc/ownmachine/hardened.json\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /opt/ownmachine-kvm/first-boot.py\n')
        put('etc/systemd/system/display-manager.service.d/ownmachine.conf','[Unit]\nRequires=ownmachine-firstboot.service\nAfter=ownmachine-firstboot.service\n[Service]\nExecStartPre=/usr/bin/python3 /usr/local/libexec/ownmachine-hardening-gate.py\n')
        archive=state/'seed.tar'
        try:
            with tarfile.open(archive,'x') as tar:
                for path in sorted(root.rglob('*')):
                    if path.is_dir():continue
                    info=tar.gettarinfo(str(path),str(path.relative_to(root)))
                    info.uid=info.gid=0;info.uname=info.gname='root'
                    with path.open('rb') as stream:tar.addfile(info,stream)
            # Extract inside the libguestfs appliance. Host never mounts guest filesystems.
            args=['guestfish','--rw','-a',str(disk),'-m','/dev/sda2:/:subvol=@']
            commands='\n'.join('mkdir-p /'+str(path.relative_to(root)) for path in sorted(root.rglob('*')) if path.is_dir())
            subprocess.run(args,input=commands+'\ntar-in '+str(archive)+' /\n',text=True,check=True,env=env)
        finally:
            archive.unlink(missing_ok=True)
