#!/bin/bash
# Operator-run guest setup. Existing signed daemon and human TCC grants required.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" -ne 0 ] || exit 1
umask 077
mkdir -p "$HOME/.local/lib/ownmachine"
cat > "$HOME/.local/lib/ownmachine/driver-mcp.sh" <<'MCP'
#!/bin/bash
set -euo pipefail
export CUA_DRIVER_RS_TELEMETRY_ENABLED=0
driver="$HOME/.local/bin/cua-driver"
# Do not silently use a different runtime or authorization policy.
[ "$("$driver" --version)" = 'cua-driver 0.44.0' ] || exit 2
status=$("$driver" status)
[[ "$status" == *'permission mode: standard ('* ]] || exit 2
exec "$driver" mcp
MCP
chmod 700 "$HOME/.local/lib/ownmachine/driver-mcp.sh"
echo 'Guest MCP launcher installed. No permissions were granted.'
# Bring the signed driver back after the guest's graphical login. No KeepAlive:
# quitting the app intentionally does not cause a relaunch loop.
mkdir -p "$HOME/Library/LaunchAgents"
plist="$HOME/Library/LaunchAgents/org.ownmachine.driver.plist"
/usr/bin/plutil -create xml1 "$plist"
/usr/bin/plutil -insert Label -string org.ownmachine.driver "$plist"
/usr/bin/plutil -insert ProgramArguments -json '["/usr/bin/open","-g","-a","/Applications/CuaDriver.app","--args","serve","--no-permissions-gate"]' "$plist"
/usr/bin/plutil -insert EnvironmentVariables -json '{"CUA_DRIVER_RS_TELEMETRY_ENABLED":"0"}' "$plist"
/usr/bin/plutil -insert RunAtLoad -bool true "$plist"
/usr/bin/plutil -insert LimitLoadToSessionType -string Aqua "$plist"
chmod 600 "$plist"
echo 'Signed driver launch scheduled for graphical login.'
