#!/bin/bash
# Explicit operator setup inside the guest, invoked with sudo. Never run by plugin.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" -eq 0 ] || { echo 'Run with sudo inside the macOS guest' >&2; exit 1; }
account="${1:-${SUDO_USER:-}}"
[[ "$account" =~ ^[A-Za-z][A-Za-z0-9_-]*$ ]] && [ "$account" != root ] || exit 1
[ "$(id -u "$account")" -ne 0 ] || exit 1
guest_home=$(dscl . -read "/Users/$account" NFSHomeDirectory | sed 's/^NFSHomeDirectory: //')
[ -d "$guest_home" ] || exit 1
umask 077
rule=$(mktemp /private/tmp/ownmachine-shutdown.XXXXXX)
trap 'rm -f "$rule"' EXIT
printf '%s ALL=(root) NOPASSWD: /sbin/shutdown -h now\n' "$account" > "$rule"
/usr/sbin/visudo -cf "$rule" >/dev/null
mkdir -p /etc/sudoers.d
install -o root -g wheel -m 440 "$rule" /etc/sudoers.d/ownmachine-shutdown
support="$guest_home/.local/lib/ownmachine"
/usr/bin/sudo -H -u "$account" /bin/mkdir -p "$support"
cat > "$support/vm-shutdown.sh" <<'HELPER'
#!/bin/bash
set -euo pipefail
# No force-stop fallback. Files/disks are retained; shutdown ends running apps.
exec /usr/bin/sudo -n /sbin/shutdown -h now
HELPER
chown "$account:$(id -gn "$account")" "$support/vm-shutdown.sh"
chmod 700 "$support/vm-shutdown.sh"
echo 'Installed exact guest shutdown permission. No VM was stopped.'
