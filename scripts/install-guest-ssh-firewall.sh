#!/bin/bash
# Operator-only: block guests on a selected VM network from host SSH, not the LAN.
set -euo pipefail
if [[ $(id -u) != 0 || $(uname -s) != Darwin ]]; then
  echo 'Run with sudo on the Mac VM host.' >&2; exit 1
fi
interface=${1:-}
port=${2:-22}
if [[ ! $interface =~ ^bridge[0-9]+$ || ! $port =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
  echo 'Usage: sudo bash install-guest-ssh-firewall.sh GUEST_BRIDGE [HOST_SSH_PORT]' >&2; exit 1
fi
/sbin/ifconfig "$interface" >/dev/null
/sbin/pfctl -sr 2>/dev/null | /usr/bin/grep -Fq 'anchor "com.apple/*"'
mkdir -p /etc/pf.anchors /usr/local/libexec
rules=/etc/pf.anchors/com.apple.ownmachine-guest-ssh
printf 'block drop in quick on %s proto tcp from any to self port %s\n' "$interface" "$port" > "$rules"
chown root:wheel "$rules"; chmod 600 "$rules"
/sbin/pfctl -n -a com.apple/ownmachine-guest-ssh -f "$rules"
helper=/usr/local/libexec/ownmachine-guest-ssh-firewall
cat > "$helper" <<'HELPER'
#!/bin/bash
set -euo pipefail
export LC_ALL=C
/sbin/pfctl -sr 2>/dev/null | /usr/bin/grep -Fq 'anchor "com.apple/*"'
/sbin/pfctl -a com.apple/ownmachine-guest-ssh -f /etc/pf.anchors/com.apple.ownmachine-guest-ssh
if ! /sbin/pfctl -s info 2>/dev/null | /usr/bin/grep -q '^Status: Enabled'; then /sbin/pfctl -E; fi
HELPER
chown root:wheel "$helper"; chmod 700 "$helper"
cat > /Library/LaunchDaemons/org.ownmachine.guest-ssh-firewall.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>org.ownmachine.guest-ssh-firewall</string>
<key>ProgramArguments</key><array><string>/usr/local/libexec/ownmachine-guest-ssh-firewall</string></array>
<key>RunAtLoad</key><true/>
<key>StartInterval</key><integer>15</integer>
</dict></plist>
PLIST
chown root:wheel /Library/LaunchDaemons/org.ownmachine.guest-ssh-firewall.plist
chmod 644 /Library/LaunchDaemons/org.ownmachine.guest-ssh-firewall.plist
"$helper"
launchctl bootout system/org.ownmachine.guest-ssh-firewall 2>/dev/null || true
launchctl bootstrap system /Library/LaunchDaemons/org.ownmachine.guest-ssh-firewall.plist
printf 'Installed guest-to-host SSH rule for %s, port %s. Verify from a guest and from the authorized LAN client. Existing PF states are not flushed.\n' "$interface" "$port"
