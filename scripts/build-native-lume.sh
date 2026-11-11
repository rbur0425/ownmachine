#!/bin/bash
# Local build with protected-file VNC passwords and native clipboard support.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo 'Requires Apple Silicon macOS' >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
revision=666c196f42dc9c83dbe075e20318f16c3e3a6d84
build_root=${OWNMACHINE_NATIVE_BUILD_ROOT:-"$HOME/Library/Caches/ownmachine/native-lume"}
app=${OWNMACHINE_NATIVE_APP:-"$HOME/.local/share/ownmachine/native-lume.app"}
[ ! -e "$app" ] || { echo 'Native build exists; inspect it before replacing.' >&2; exit 1; }
mkdir -p "$build_root"
if [ ! -d "$build_root/source/.git" ]; then
  git clone --filter=blob:none --no-checkout https://github.com/trycua/cua.git "$build_root/source"
fi
git -C "$build_root/source" checkout --detach "$revision"
[ -z "$(git -C "$build_root/source" status --porcelain)" ] || { echo 'Build source has changes; use a fresh build directory.' >&2; exit 1; }
git -C "$build_root/source" apply "$root/patches/lume-0.7.0-key-clipboard.patch"
git -C "$build_root/source" apply "$root/patches/lume-0.7.0-private-vnc-password.patch"
swift build --package-path "$build_root/source/libs/lume" -c release --product lume --force-resolved-versions
bin=$(swift build --package-path "$build_root/source/libs/lume" -c release --show-bin-path)
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$bin/lume" "$app/Contents/MacOS/lume"
cp "$build_root/source/libs/lume/resources/Info.plist" "$app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier org.ownmachine.lume' "$app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName OwnMachine Lume' "$app/Contents/Info.plist"
cp -R "$bin/lume_lume.bundle" "$app/Contents/Resources/"
# This is an explicitly local, ad-hoc build, not the notarized vendor app.
printf '%s\n' "$revision" > "$app/Contents/Resources/ownmachine-upstream-revision"
shasum -a 256 "$root/patches/lume-0.7.0-key-clipboard.patch" "$root/patches/lume-0.7.0-private-vnc-password.patch" > "$app/Contents/Resources/ownmachine-patch-sha256"
codesign --force --sign - --entitlements "$build_root/source/libs/lume/resources/lume.local.entitlements" "$app"
codesign --verify --deep --strict "$app"
echo "Built local OwnMachine Lume: $app"
echo 'Start it with scripts/ownmachine-native.py after a normal guest shutdown. No host reboot is needed.'
