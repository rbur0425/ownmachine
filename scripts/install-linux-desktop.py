#!/usr/bin/env python3
"""Explicit base/desktop stages over an independently pinned guest SSH identity.

Only the base stage erases a disk, and only an empty /dev/vda inside an Apple
virtualized Archboot live environment belonging to a newly created VM.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import urllib.request
from setup_support import ROOT, mac, module, private_read, install_exact

services=module('linux_desktop_services','scripts/setup-services.py')
PIN='36c576698e7265a84fb3469c8b9d2c9824df6931'
DIGESTS={'base':'f62d7d5e5c93201b010a60d71fe6f8d9a7a0adb472fc0e86dcc4d5064def61d4',
         'desktop':'6208dfdad21c42f353661fdd7bcc67adec2250415f8db056abc75a41068e9fbe'}


def download(stage):
    name='install-arch.sh' if stage=='base' else 'install-omarchy.sh'
    url=f'https://raw.githubusercontent.com/trycua/cua/{PIN}/docs/public/scripts/omarchy-arm64-lume/{name}'
    with urllib.request.urlopen(url,timeout=60) as response:content=response.read(131073)
    if len(content)>131072 or hashlib.sha256(content).hexdigest()!=DIGESTS[stage]:raise ValueError('installer_checksum_mismatch')
    return content.decode()


def execute(config_path,stage,apply):
    c=services.config(config_path)
    if c.get('guest_profile')!='omarchy':raise ValueError('omarchy_profile_required')
    if not apply:return dict(ok=True,stage='planned',step='linux-'+stage)
    if os.geteuid()==0:raise ValueError('non_root_operator_required')
    mac.verify_build(Path(c['lume_app']),linux=True)
    state=services.hardening_state(c);mac.private_dir(state)
    receipt=json.loads(private_read(state/'provision.json'))
    if receipt.get('guest_os')!='linux' or receipt.get('phase')!='created' or receipt.get('vm_name')!=c['vm_name'] or receipt.get('storage_dir')!=str(Path(c['storage_dir']).resolve()):raise ValueError('fresh_linux_provision_receipt_required')
    identity=mac.digest(dict(config=c,source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),installer=DIGESTS[stage]))
    checkpoint=state/'setup'/('linux-'+stage+'.json');mac.private_dir(checkpoint.parent)
    import fcntl
    fd=os.open(state/'setup/linux-install.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=mac.read_state(checkpoint)
        if old:
            if old.get('identity')!=identity or old.get('stage')!='verified':raise ValueError('linux_install_requires_inspection')
            return dict(ok=True,step='linux-'+stage,stage='verified',replayed=False)
        argv=services.guest_argv(c)
        source=download(stage)
        if stage=='base':
            # Validate before recording a mutation. The live SSH key was confirmed
            # in the native console, never accepted with StrictHostKeyChecking=no.
            guard='''test "$(id -u)" = 0 && test "$(systemd-detect-virt)" = apple && grep -qx 'NAME="Archboot"' /etc/os-release && test "$(findmnt -n -o SOURCE /)" = /dev/zram0 && test -z "$(wipefs -n --noheadings -o TYPE /dev/vda)" && test "$(lsblk -nr -o NAME /dev/vda | wc -l)" -eq 1 && ! findmnt /mnt >/dev/null'''
            services.call(argv+[guard])
            user=c['guest_user']
            if user=='root':raise ValueError('non_root_desktop_user_required')
            # The reviewed upstream base script fixes this username. Replace exact
            # audited literals only after checksum verification, never arbitrary text.
            source=source.replace('useradd -m -G wheel -s /bin/bash omarchy','useradd -m -G wheel -s /bin/bash '+shlex.quote(user))
            source=source.replace("read -r -p 'Type ERASE to continue: ' confirmation",'confirmation=ERASE')
            prefix='set -euo pipefail\numask 022\npacman -Sy --noconfirm --needed gptfdisk\n'
            suffix='''
# Preserve the operator-confirmed host identity across the live-to-installed boot.
cp -a /etc/ssh/ssh_host_* /mnt/etc/ssh/
install -d -m 700 /mnt/home/USER/.ssh
install -m 600 /root/.ssh/authorized_keys /mnt/home/USER/.ssh/authorized_keys
arch-chroot /mnt chown -R USER:USER /home/USER/.ssh
printf 'PasswordAuthentication no\\nKbdInteractiveAuthentication no\\nPermitRootLogin no\\n' > /mnt/etc/ssh/sshd_config.d/00-ownmachine-bootstrap.conf
arch-chroot /mnt pacman -S --noconfirm --needed nftables python
arch-chroot /mnt python3 -c 'import secrets; print("USER:"+secrets.token_urlsafe(32))' | arch-chroot /mnt chpasswd
'''.replace('USER',user)
            script=prefix+source+'\n'+suffix
            command='/bin/bash -s'
        else:
            services.call(argv+['test "$(id -u)" -ne 0 && test "$(systemd-detect-virt)" = apple && test ! -e /etc/omarchy-source-commit && sudo -n true'])
            script='export OMARCHY_USER='+shlex.quote(c['guest_user'])+'\n'+source+'\npacman -S --needed --noconfirm mousepad at-spi2-core\n'
            # Customize only the freshly copied, pinned upstream defaults.
            script+='\npython3 - '+shlex.quote(c['guest_user'])+' '+str(c.get('display_scale',1))+" <<'OWNMACHINE_DISPLAY'\n"+'''import pathlib,pwd,sys
home=pathlib.Path(pwd.getpwnam(sys.argv[1]).pw_dir)
scale=int(sys.argv[2])
path=home/'.config/hypr/monitors.lua'
text=path.read_text()
for old,new in [('local omarchy_gdk_scale = 2','local omarchy_gdk_scale = '+str(scale)),('local omarchy_monitor_scale = "auto"','local omarchy_monitor_scale = '+str(scale))]:
    if text.count(old)!=1:raise ValueError('unexpected_pinned_monitor_configuration')
    text=text.replace(old,new)
path.write_text(text)
path=home/'.config/hypr/looknfeel.lua'
with path.open('a') as stream:stream.write('\\nhl.config({ animations = { enabled = false } })\\n')
path=home/'.config/hypr/bindings.lua'
with path.open('a') as stream:stream.write('\\nhl.unbind("SUPER + RETURN")\\no.bind("SUPER + RETURN", "Terminal", "foot")\\n')
OWNMACHINE_DISPLAY
'''
            script+='\nrunuser -u '+shlex.quote(c['guest_user'])+' -- env OMARCHY_PATH=/usr/share/omarchy OMARCHY_THEME_HEADLESS=1 /usr/share/omarchy/bin/omarchy-theme-set '+shlex.quote(c.get('desktop_theme','catppuccin'))+'\n'
            command='sudo -n /bin/bash -s'
        record=dict(schema_version=1,identity=identity,stage='running')
        mac.write_state(checkpoint,record)
        try:
            services.call(argv+[command],data=script.encode(),timeout=7200)
            verification='test -s /mnt/boot/loader/entries/arch.conf && test "$(stat -c %a /mnt/etc)" = 755' if stage=='base' else 'test "$(cat /etc/omarchy-source-commit)" = 13f18b2cb7286fb54f87daf571a031aa6af3d8f0'
            services.call(argv+[verification])
        except BaseException:
            mac.write_state(checkpoint,dict(record,stage='needs_inspection'));raise
        mac.write_state(checkpoint,dict(record,stage='verified'))
        return dict(ok=True,step='linux-'+stage,stage='verified',next='Shut down the guest and boot its installed disk without the ISO.' if stage=='base' else 'Restart the guest to begin its graphical session, then run hardening and driver setup.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--step',choices=['base','desktop'],required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args();os.umask(0o077)
    try:print(json.dumps(execute(a.config,a.step,a.apply)))
    except (ValueError,OSError,subprocess.SubprocessError):
        print(json.dumps(dict(ok=False,step='linux-'+a.step,stage='needs_attention',code='linux_install_requires_inspection')));raise SystemExit(2)

if __name__=='__main__':main()
