"""Linux branches of the reviewed operator setup service (never loaded by Hermes)."""
import json
import secrets
import shlex
from pathlib import Path
from setup_support import ROOT, private_read, install_exact


def root_call(service,c,script):
    # Fresh Linux bootstrap grants temporary setup sudo. Once hardened, use only
    # the operator-owned recovery copy via stdin; never an argv/environment secret.
    password=private_read(service.hardening_state(c)/'guest-password')
    return service.call(service.guest_argv(c)+['sudo -k -S -p "" /bin/bash -s'],data=password+script,timeout=240)


def prerequisites(service,c):
    report=json.loads(private_read(service.hardening_state(c)/'provision.json'))
    if (report.get('phase')!='created' or report.get('guest_os')!='linux'
        or report.get('vm_name')!=c['vm_name'] or report.get('storage_dir')!=str(Path(c['storage_dir']).resolve())):
        raise ValueError('fresh_linux_provision_receipt_required')
    service.mac.verify_build(Path(c['lume_app']),linux=True)
    service.call(service.guest_argv(c)+['test "$(uname -s)" = Linux && test "$(systemd-detect-virt)" = apple'])


def harden(service,c):
    state=service.hardening_state(c);service.mac.private_dir(state)
    password=state/'guest-password'
    if password.exists():raise ValueError('existing_credentials_require_inspection')
    value='-'.join(''.join(secrets.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(4)) for _ in range(4))+'\n'
    install_exact(password,value.encode())
    # Query the authenticated connection's peer; never infer the host address
    # from documentation or pass a developer-specific network default.
    observed=service.call(service.guest_argv(c)+['printf "%s" "$SSH_CONNECTION"']).stdout.decode().split()
    if len(observed)!=4:raise ValueError('ssh_source_unavailable')
    import ipaddress
    source=str(ipaddress.ip_address(observed[0]))
    payload=(ROOT/'scripts/secure-linux-guest.py').read_bytes()
    command=('set -eu; umask 077; dir=$(mktemp -d); trap \'rm -rf "$dir"\' EXIT; '
             'cat > "$dir/harden.py"; sudo -n /usr/bin/python3 "$dir/harden.py" --user '+shlex.quote(c['guest_user'])+
             ' --ssh-source '+shlex.quote(source)+' --password-file "$HOME/.ownmachine-recovery-transfer" --apply')
    service.call(service.guest_argv(c)+['umask 077; set -C; cat > "$HOME/.ownmachine-recovery-transfer"'],data=value.encode())
    service.call(service.guest_argv(c)+[command],data=payload,timeout=240)
    install_exact(state/'linux-hardening.json',json.dumps({'schema_version':1,'hardened':True}).encode())


def verify_hardening(service,c):
    report=json.loads(private_read(service.hardening_state(c)/'linux-hardening.json'))
    if report!={'schema_version':1,'hardened':True}:raise ValueError('linux_hardening_incomplete')
    script=b'''set -eu
/usr/bin/python3 /usr/local/libexec/ownmachine-hardening-gate.py
/usr/bin/sshd -t
/usr/bin/sshd -T | grep -qi '^passwordauthentication no$'
/usr/bin/sshd -T | grep -qi '^permitrootlogin no$'
/usr/bin/systemctl is-active --quiet ownmachine-firewall.service
/usr/bin/nft list table inet ownmachine >/dev/null
'''
    root_call(service,c,script)
    result=service.call(service.guest_argv(c)+['sudo -k; if sudo -n /usr/bin/true >/dev/null 2>&1; then exit 1; fi; test -x "$HOME/.local/lib/ownmachine/vm-shutdown.sh"'])


def driver(service,c):
    command=('set -eu; umask 077; dir=$(mktemp -d); trap \'rm -rf "$dir"\' EXIT; '
             'cat > "$dir/linux-guest.py"; /usr/bin/python3 "$dir/linux-guest.py" install')
    service.call(service.guest_argv(c)+[command],data=(ROOT/'scripts/linux-guest.py').read_bytes(),timeout=900)
    if c.get('enable_experimental_input'):
        command=('set -eu; umask 077; set -C; cat > "$HOME/.local/lib/ownmachine/linux-input-module.py"; '
                 '/usr/bin/python3 "$HOME/.local/lib/ownmachine/linux-input-module.py" build --enable-experimental-input --apply; '
                 '/usr/bin/python3 "$HOME/.local/lib/ownmachine/linux-input-module.py" enable --enable-experimental-input --apply')
        service.call(service.guest_argv(c)+[command],data=(ROOT/'scripts/linux-input-module.py').read_bytes(),timeout=5400)


def ready(service,c):
    result=service.relay.guest_status(c['guest_ssh_alias'],service.guest_address(c),'linux')
    if not result['driver_ready']:raise ValueError('linux_graphical_session_or_driver_required')
    if c.get('enable_experimental_input') and not result.get('foreground_input_ready'):
        raise ValueError('linux_foreground_input_not_ready')
