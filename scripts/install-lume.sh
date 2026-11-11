#!/bin/bash
# Operator-run, pinned installation on the dedicated Apple Silicon Mac account.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo 'Requires Apple Silicon macOS' >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || { echo 'Run as the dedicated non-root host account' >&2; exit 1; }
version=0.7.0
sha=66ae137164f5428ef73f90994850db49f1270dec298653f9f806debe29d529fc
app="$HOME/.local/share/lume/lume.app"
cli="$HOME/.local/bin/lume"
export LUME_TELEMETRY_ENABLED=false
umask 077
if [ -L "$HOME/.lume" ]; then echo 'Symlinked Lume state refused; use private storage.' >&2; exit 1; fi
mkdir -p "$HOME/.lume"
chmod 700 "$HOME/.lume"
if [ -e "$cli" ] || [ -e "$app" ]; then
  echo 'Existing Lume installation found; inspect it before replacing.' >&2
  exit 1
fi
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
  "https://github.com/trycua/cua/releases/download/lume-v${version}/lume-${version}-darwin-arm64.tar.gz" \
  -o "$task_tmp/lume.tar.gz"
printf '%s  %s\n' "$sha" "$task_tmp/lume.tar.gz" | shasum -a 256 -c -
tar -xzf "$task_tmp/lume.tar.gz" -C "$task_tmp"
test -x "$task_tmp/lume.app/Contents/MacOS/lume"
codesign --verify --deep --strict '-R=anchor apple generic and certificate leaf[subject.OU] = "YCK386LBJ7"' "$task_tmp/lume.app"
mkdir -p "$(dirname "$app")" "$(dirname "$cli")"
mv "$task_tmp/lume.app" "$app"
printf '#!/bin/sh\nexec "%s/Contents/MacOS/lume" "$@"\n' "$app" > "$cli"
chmod 755 "$cli"
"$cli" config telemetry disable
"$cli" --version
# No LaunchAgent, updater, HTTP service, VM creation, or shell profile changes.
