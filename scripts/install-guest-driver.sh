#!/bin/bash
# Run explicitly INSIDE the fresh macOS guest, never on the personal host desktop.
set -euo pipefail
[ "$(uname -s)" = Darwin ] || { echo 'Requires macOS guest' >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || { echo 'Run as the guest desktop user' >&2; exit 1; }
app=/Applications/CuaDriver.app
cli="$HOME/.local/bin/cua-driver"
if [ -e "$app" ] || [ -e "$cli" ] || [ -e "$HOME/.cua-driver/config.json" ]; then
  echo 'Existing driver installation/configuration found; inspect before replacing.' >&2
  exit 1
fi
script_dir=$(cd "$(dirname "$0")" && pwd)
[ -f "$script_dir/install-permission-guide.sh" ] || { echo 'Run from the complete source scripts directory' >&2; exit 1; }
version=0.44.0
sha=7699d7ebd3d3319cbd066af9fc679dc7439adad6c5c84cc46956aa9880106e37
export CUA_DRIVER_RS_TELEMETRY_ENABLED=0
umask 077
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
  "https://github.com/trycua/cua/releases/download/cua-driver-rs-v${version}/cua-driver-rs-${version}-darwin-universal.tar.gz" \
  -o "$task_tmp/driver.tar.gz"
printf '%s  %s\n' "$sha" "$task_tmp/driver.tar.gz" | shasum -a 256 -c -
tar -xzf "$task_tmp/driver.tar.gz" -C "$task_tmp"
source_app="$task_tmp/cua-driver-rs-${version}-darwin-universal/CuaDriver.app"
codesign --verify --deep --strict '-R=anchor apple generic and certificate leaf[subject.OU] = "YCK386LBJ7"' "$source_app"
ditto "$source_app" "$app"
codesign --verify --deep --strict "$app"
mkdir -p "$HOME/.local/bin" "$HOME/.cua-driver"
printf '%s\n' '{"telemetry_enabled":false}' > "$HOME/.cua-driver/config.json"
printf '#!/bin/sh\nexport CUA_DRIVER_RS_TELEMETRY_ENABLED=0\nexec "%s/Contents/MacOS/cua-driver" "$@"\n' "$app" > "$cli"
chmod 755 "$cli"
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f "$app"
"$cli" --version
# Default onboarding at next GUI login. The signed app asks; only humans grant.
/bin/bash "$script_dir/install-permission-guide.sh"
