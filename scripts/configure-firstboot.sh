#!/bin/bash
# Explicit operator post-install defaults for a local-account macOS guest.
# Run with sudo inside the guest AFTER unattended account creation.
set -euo pipefail
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" -eq 0 ] || { echo 'Run with sudo inside the macOS guest' >&2; exit 1; }
[ -f /var/db/.AppleSetupDone ] || { echo 'Complete unattended account creation first' >&2; exit 1; }
guest_user="${SUDO_USER:?Run through sudo from the guest desktop account}"
[ "$guest_user" != root ] || exit 1
version=$(/usr/bin/sw_vers -productVersion)
build=$(/usr/bin/sw_vers -buildVersion)
user_defaults() { /usr/bin/sudo -H -u "$guest_user" /usr/bin/defaults "$@"; }
for key in DidSeeCloudSetup DidSeePrivacy DidSeeSiriSetup DidSeeScreenTime DidSeeAppearanceSetup DidSeeAccessibility DidSeeTouchIDSetup DidSeeTrueToneSetup; do
  user_defaults write com.apple.SetupAssistant "$key" -bool true
  /usr/bin/defaults write /Library/Preferences/com.apple.SetupAssistant "$key" -bool true
done
for key in LastSeenCloudProductVersion LastSeenDiagnosticsProductVersion LastPreLoginTasksPerformedVersion; do
  user_defaults write com.apple.SetupAssistant "$key" -string "$version"
  /usr/bin/defaults write /Library/Preferences/com.apple.SetupAssistant "$key" -string "$version"
done
for key in LastSeenBuddyBuildVersion LastPreLoginTasksPerformedBuild; do
  user_defaults write com.apple.SetupAssistant "$key" -string "$build"
  /usr/bin/defaults write /Library/Preferences/com.apple.SetupAssistant "$key" -string "$build"
done
user_defaults write com.apple.SetupAssistant MiniBuddyShouldLaunchToResumeSetup -bool false
user_defaults write com.apple.assistant.support 'Assistant Enabled' -bool false
user_defaults write com.apple.Siri StatusMenuVisible -bool false
mkdir -p '/Library/Application Support/CrashReporter'
for key in AutoSubmit ThirdPartyDataSubmit; do
  /usr/bin/defaults write '/Library/Application Support/CrashReporter/DiagnosticMessagesHistory' "$key" -bool false
done
# No Apple Account sign-in, update-policy change, license acceptance, or TCC edits.
echo 'Local-account first-login preferences aligned; analytics and Siri disabled.'
echo 'Setup Assistant may still appear. Complete remaining guest screens as described in docs/vm-setup.md; these preferences do not grant desktop permissions.'
