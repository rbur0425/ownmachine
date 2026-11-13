#!/usr/bin/env python3
"""Explicit root hardening inside a fresh Apple-virtualized Linux guest only."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import stat
import subprocess
import tempfile


def command(argv, **kwargs):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30, **kwargs)


def firewall_rules(source):
    address = ipaddress.ip_address(source)
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        raise ValueError('invalid_ssh_source')
    family = 'ip' if address.version == 4 else 'ip6'
    return f'''destroy table inet ownmachine
 table inet ownmachine {{
 chain input {{
  type filter hook input priority 0; policy drop;
  ct state established,related accept
  iifname "lo" accept
  {family} saddr {address} tcp dport 22 accept
  udp sport 67 udp dport 68 accept
  udp sport 547 udp dport 546 accept
  ip protocol icmp accept
  meta l4proto ipv6-icmp accept
 }}
 chain forward {{ type filter hook forward priority 0; policy drop; }}
 chain output {{ type filter hook output priority 0; policy accept; }}
}}
'''


def install_file(path, value, mode=0o600):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink_destination')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    if path.exists() and path.read_text() != value:
        raise ValueError('existing_configuration_differs')
    if path.exists():
        info=path.stat()
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != mode:
            raise ValueError('unsafe_existing_configuration')
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'w') as stream:
        # The operator deliberately uses umask 077. Sudo requires exactly 0440,
        # so apply the reviewed destination mode to the open, exclusive inode.
        os.fchmod(stream.fileno(), mode)
        stream.write(value);stream.flush();os.fsync(stream.fileno())


def user_support(home, uid, gid):
    support=home/'.local/lib/ownmachine'
    for directory in (home/'.local', home/'.local/lib', support):
        if directory.is_symlink():raise ValueError('symlink_destination')
        if not directory.exists():
            directory.mkdir(mode=0o700)
            os.chown(directory,uid,gid)
        info=directory.stat()
        if info.st_uid!=uid or info.st_mode & 0o022:
            raise ValueError('unsafe_guest_support_directory')
    return support


def harden(user, source, password_file):
    if not re.fullmatch('[a-z_][a-z0-9_-]{0,31}', user) or user == 'root':
        raise ValueError('desktop_user_required')
    # Refuse before password rotation or policy mutation if desktop setup did
    # not install the root-owned boot gate.
    gate = Path('/usr/local/libexec/ownmachine-hardening-gate.py')
    for item in (gate, *gate.parents):
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError('trusted_desktop_hardening_gate_required')
    if not gate.is_file():raise ValueError('desktop_hardening_gate_required')
    account = pwd.getpwnam(user)
    if account.pw_uid < 1000:raise ValueError('desktop_user_required')
    home = Path(account.pw_dir)
    fd = os.open(password_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid not in {0, account.pw_uid} or info.st_mode & 0o077 or info.st_size > 129:
            raise ValueError('private_recovery_password_required')
        password = stream.read().rstrip('\n')
    if not re.fullmatch(r'[A-Za-z0-9._~-]{16,128}', password):
        raise ValueError('unique_recovery_password_required')
    authorized = home/'.ssh/authorized_keys'
    if authorized.is_symlink() or not authorized.is_file() or not any('ssh-ed25519 ' in line for line in authorized.read_text().splitlines()):
        raise ValueError('pair_guest_key_before_hardening')
    wheel=Path('/etc/sudoers.d/10-wheel')
    if wheel.is_symlink() or (wheel.exists() and wheel.read_text().strip() not in {'%wheel ALL=(ALL:ALL) NOPASSWD: ALL','%wheel ALL=(ALL:ALL) ALL'}):
        raise ValueError('review_existing_sudo_policy')
    rules = firewall_rules(source)
    command(['nft','--check','-f','-'], input=rules)
    dropin = 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nAllowTcpForwarding no\nX11Forwarding no\nAllowAgentForwarding no\n'
    install_file(Path('/etc/ssh/sshd_config.d/00-ownmachine.conf'), dropin)
    command(['sshd','-t'])
    effective = command(['sshd','-T']).stdout.lower().splitlines()
    for required in ('passwordauthentication no','kbdinteractiveauthentication no','permitrootlogin no','allowtcpforwarding no','allowagentforwarding no'):
        if required not in effective:raise ValueError('conflicting_ssh_policy')
    install_file(Path('/etc/ownmachine/guest-firewall.nft'),rules)
    unit='''[Unit]
Description=OwnMachine guest inbound firewall
Before=sshd.service
After=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nft -f /etc/ownmachine/guest-firewall.nft

[Install]
WantedBy=multi-user.target
'''
    install_file(Path('/etc/systemd/system/ownmachine-firewall.service'),unit,0o644)
    # Root-owned exact shutdown authorization; never grant generic systemctl/shell.
    sudo_rule = user + ' ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff\n'
    with tempfile.NamedTemporaryFile(mode='w') as rule:
        rule.write(sudo_rule);rule.flush()
        command(['visudo','-cf',rule.name])
    install_file(Path('/etc/sudoers.d/ownmachine-shutdown'),sudo_rule,0o440)
    support=user_support(home,account.pw_uid,account.pw_gid)
    helper=support/'vm-shutdown.sh'
    install_file(helper,'#!/bin/sh\nexec /usr/bin/sudo -n /usr/bin/systemctl poweroff\n',0o700)
    os.chown(support,account.pw_uid,account.pw_gid);os.chown(helper,account.pw_uid,account.pw_gid)
    # Remove only the exact upstream unattended passwordless rule, preserving
    # administrator customizations. Unknown rules require operator inspection.
    # Establish recovery access before removing unattended sudo.
    command(['chpasswd'], input=user + ':' + password + '\n')
    if wheel.exists():
        fd=os.open(wheel,os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        with os.fdopen(fd,'w') as stream:
            stream.write('%wheel ALL=(ALL:ALL) ALL\n');stream.flush();os.fsync(stream.fileno())
        wheel.chmod(0o440)
    command(['visudo','-c'])
    Path(password_file).unlink()
    command(['passwd','-l','root'])
    command(['systemctl','daemon-reload'])
    command(['systemctl','enable','--now','ownmachine-firewall.service'])
    command(['systemctl','reload','sshd'])
    for unit_name in ('docker.service','docker.socket','cups.service','cups.socket','cups.path','bluetooth.service'):
        subprocess.run(['systemctl','disable','--now',unit_name],capture_output=True,timeout=30)
    subprocess.run(['gpasswd','-d',user,'docker'],capture_output=True,timeout=10)
    # A noninteractive escalation probe must fail; exact poweroff is not run here.
    probe=subprocess.run(['runuser','-u',user,'--','sudo','-n','/usr/bin/true'],capture_output=True,timeout=10)
    if probe.returncode == 0:raise ValueError('unrestricted_passwordless_sudo_remains')
    # The receipt is public policy metadata; recovery material remains private.
    Path('/etc/ownmachine').chmod(0o755)
    command(['/usr/bin/python3','/usr/local/libexec/ownmachine-hardening-gate.py','--seal',user])
    return dict(hardened=True,guest_os='linux',ssh='key_only',firewall='loaded',sudo='exact_shutdown_only')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user',required=True)
    parser.add_argument('--ssh-source',required=True,help='Host-side source address observed over the verified guest SSH connection')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--password-file',type=Path,help='Private guest-side recovery-password transfer file, consumed after rotation; keep the recovery copy on the host, never pass it in argv')
    args=parser.parse_args()
    firewall_rules(args.ssh_source)
    if not args.apply:
        print(json.dumps(dict(stage='planned',guest_os='linux',next='Run as root inside the fresh guest after pairing its key.')));return
    if platform.system()!='Linux' or os.geteuid()!=0 or command(['systemd-detect-virt']).stdout.strip()!='apple':
        raise ValueError('apple_virtualized_linux_guest_root_required')
    if args.password_file is None:raise ValueError('private_recovery_password_required')
    print(json.dumps(harden(args.user,args.ssh_source,args.password_file)))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print('Linux hardening requires inspection: '+type(error).__name__)
        raise SystemExit(2)
