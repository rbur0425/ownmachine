#!/bin/bash
# Operator-only macOS firewall installation. Never replaces the global PF ruleset.
set -euo pipefail
if [[ $(id -u) != 0 || $(uname -s) != Darwin ]]; then
  echo 'Run this installer with sudo on the Mac VM host.' >&2; exit 1
fi
port=${1:-}
app=${2:-}
if [[ ! $port =~ ^[0-9]+$ ]] || (( port < 1024 || port > 65535 )) ||
   [[ $app != /*/*.app || ! -x $app/Contents/MacOS/lume || $app == *$'\n'* ]]; then
  echo 'Usage: sudo bash install-vnc-firewall.sh VNC_PORT /absolute/path/to/lume.app' >&2; exit 1
fi
if ! /sbin/pfctl -sr 2>/dev/null | /usr/bin/grep -Fq 'anchor "com.apple/*"'; then
  echo 'Loaded PF rules must include the standard com.apple/* anchor; no global rules were changed.' >&2; exit 1
fi
# No user-owned helper is ever executed as root. Only fixed system utilities run.
mkdir -p /etc/pf.anchors /usr/local/libexec
rules=/etc/pf.anchors/com.apple.ownmachine
printf 'block drop in quick on ! lo0 proto tcp from any to any port %s\n' "$port" > "$rules"
chown root:wheel "$rules"; chmod 600 "$rules"
/sbin/pfctl -n -a com.apple/ownmachine -f "$rules"
helper=/usr/local/libexec/ownmachine-vnc-firewall
printf '#!/bin/bash\nset -euo pipefail\nexport LC_ALL=C\nport=%q\napp=%q\n' "$port" "$app" > "$helper"
cat >> "$helper" <<'HELPER'
state=/private/var/run/ownmachine
if [[ -L $state || ( -e $state && ! -d $state ) ]]; then exit 1; fi
mkdir -p "$state"; chown root:wheel "$state"; chmod 755 "$state"
status="$state/firewall-status.json"
trap 'echo "Firewall verification failed; no readiness status published." >&2; rm -f "$status" "$state/status.$$"' EXIT
/sbin/pfctl -sr 2>/dev/null | /usr/bin/grep -Fq 'anchor "com.apple/*"'
/sbin/pfctl -a com.apple/ownmachine -f /etc/pf.anchors/com.apple.ownmachine
if ! /sbin/pfctl -s info 2>/dev/null | /usr/bin/grep -q '^Status: Enabled'; then
  /sbin/pfctl -E
fi
fw=/usr/libexec/ApplicationFirewall/socketfilterfw
"$fw" --setglobalstate on
# macOS registers this signed executable by its enclosing bundle. Query the
# bundle: querying Contents/MacOS/lume separately misleadingly says permitted.
if ! "$fw" --getappblocked "$app" | /usr/bin/grep -q 'is blocked\.'; then
  "$fw" --add "$app"
  "$fw" --blockapp "$app"
fi
/sbin/pfctl -s info 2>/dev/null | /usr/bin/grep -q '^Status: Enabled'
/sbin/pfctl -a com.apple/ownmachine -sr 2>/dev/null | /usr/bin/grep -Eq "^block drop in quick on ! lo0 proto tcp from any to any port = $port$"
"$fw" --getglobalstate | /usr/bin/grep -q 'State = 1'
"$fw" --getappblocked "$app" | /usr/bin/grep -q 'is blocked\.'
# A short-lived, root-owned attestation; relay refuses stale or account-written files.
printf '{"port":%s,"pf_enabled":true,"rule_loaded":true,"application_blocked":true}\n' "$port" > "$state/status.$$"
chown root:wheel "$state/status.$$"; chmod 644 "$state/status.$$"
mv -f "$state/status.$$" "$status"
trap - EXIT
HELPER
chown root:wheel "$helper"; chmod 700 "$helper"
cat > /Library/LaunchDaemons/org.ownmachine.vnc-firewall.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>org.ownmachine.vnc-firewall</string>
<key>ProgramArguments</key><array><string>/usr/local/libexec/ownmachine-vnc-firewall</string></array>
<key>RunAtLoad</key><true/>
<key>StartInterval</key><integer>15</integer>
</dict></plist>
PLIST
chown root:wheel /Library/LaunchDaemons/org.ownmachine.vnc-firewall.plist
chmod 644 /Library/LaunchDaemons/org.ownmachine.vnc-firewall.plist
"$helper"
launchctl bootout system/org.ownmachine.vnc-firewall 2>/dev/null || true
launchctl bootstrap system /Library/LaunchDaemons/org.ownmachine.vnc-firewall.plist
printf 'OwnMachine VNC port %s is restricted to loopback; application firewall blocks Lume inbound. Set matching vnc_port.\n' "$port"
