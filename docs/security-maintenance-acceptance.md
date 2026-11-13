# Security and rolling-update follow-up

Verified on the laptop Omarchy test guest on November 12, 2026 (local time).
This follow-up changes the release candidate; earlier release-head validation
must not be reused for the new commit. Publication remains on hold.

## VNC output and network boundary

- Added a common Lume patch that redacts VNC userinfo in normal terminal,
  redirected-text and JSON VM listings, including `get`, and removes credentials
  from both normal and recovery VNC startup log messages.
- The viewer-role relay alone requests explicit `ls --include-vnc-password`
  output, captures it privately and still checks the URL port and managed password.
  Same-account processes can request this mode/read private files: this is an
  accidental-log-leak fix, not an OS-account security boundary. Stock Lume remains
  unsupported for hardened deployment. This does not change Lume's optional HTTP
  API; OwnMachine does not expose or run that API.
- Actual running-VM checks: default JSON and text listings contained no password;
  explicit private listing retained it. After a relay shutdown/cold start on the
  new signed Linux build, the new password was absent from the detached log and
  process arguments; its file remained mode 0600. The normal browser viewer
  authenticated and streamed successfully with the updated relay.
- Apple's private VNC server API still binds all interfaces. PF and application
  firewall restrictions remain mandatory; no unsupported bind-address selector
  was guessed. Direct LAN VNC timed out while the SSH-backed viewer worked.
- A duplicate app identity initially prevented firewall readiness. Start refused
  with the guest stopped. A distinct bundle identity restored verified blocking;
  `OWNMACHINE_LUME_BUNDLE_ID` makes that build choice configurable. No firewall
  check was bypassed. The Studio deployment was not changed in this follow-up.

Swift printer regression tests cover default terminal/redirected/JSON redaction,
explicit private output and malformed URL handling. Both common/macOS and Linux
patch application/build paths were checked. The added Python relay assertion
requires the explicit private-output flag.

## Guest-to-host SSH and cleanup

Added the operator-only `install-guest-ssh-firewall.sh GUEST_BRIDGE [HOST_SSH_PORT]`.
The administrator installed its independent persistent PF anchor on the actual
laptop VM bridge. New guest-to-host SSH connections timed out both before and
after guest restart; the authorized homelab client still reached host SSH over the
LAN. Global PF rules/states and unrelated LAN access were not flushed or replaced.
This affects all guests on the selected bridge, not arbitrary guest networks or
other host services. Interface/port remain operator configuration.

Exactly two legacy `lume-config-*` directories were inspected and removed with
`rmdir` (which refuses nonempty directories). No recursive deletion or broad temp
cleanup was used. They were older-build artifacts, not active guest shares.

## Omarchy maintenance: failures and actual completion

The owner explicitly requested updating the test guest and retesting it. The
normal upstream updater initially could not run migrations: its required Tensaku
package was absent from the guest's configured base Arch Linux ARM repositories.
The official ARM64 repository was configured with signature verification required
and the upstream pinned key fingerprint
`40DFB630FF42BCFFB047046CF0134EE680CAC571`, obtained through Omarchy's own WKD.
The previous pacman configuration was preserved. No unsigned-package bypass or
public keyserver substitution was used.

Missing Snapper/pacman-contrib prerequisites were installed through the signed
package route; the guest root filesystem was confirmed Btrfs. Migrations resumed
rather than being marked complete. The reboot-prompt dependency Gum was also
installed after its absence was reported. The updater completed and the actual
pending-migration count reached **zero**, remaining zero after a graceful guest
shutdown and relay cold start. Temporary private sudo credential helpers were
removed. The guest's no-PTY SSH restriction stayed in place; an initial terminal
attempt blocked at sudo before package installation and was stopped before retry.

The root hardening gate passed after the update. Runtime readiness reported the
graphical session, accessibility bus, standard mode and foreground input ready.
Hyprland remained 0.57.2-1, Chromium 156.0.8078.79-1, Mousepad 0.7.0-1 and Qt
6.12.0-4; the native input module remained compatible without rebuilding. This is
one tested update, not a guarantee for future rolling upgrades. The existing
49-byte acceptance document still matched its expected contents after restart.

### Real model retest

The installed Hermes profile and local Qwen model launched Chromium using only
computer_use. A new-keyring creation prompt caused the model to stop. After an
explicit cancellation-only instruction, the model still declined an ungrounded
pixel click. The operator reserved the desktop and clicked **Cancel**; no password
was entered, no keyring created, and no password-store/security setting changed.
Control was returned to the same Hermes conversation. The model then focused the
address field, typed `https://www.google.com/`, pressed Enter with foreground
input and captured the resulting page.

Independent viewer inspection, guest window discovery and a new Chromium history
visit confirmed Google. This is an **operator-assisted prompt dismissal followed
by successful model navigation**, not a fully unattended pass. Agent control was
left paused; test approvals returned to deny and background input stayed disabled.
The remaining “Update System” desktop card is an upstream first-run shortcut,
not evidence of pending migrations. The pending-migrations card disappeared;
welcome cards were not hidden to manufacture a clean result.

![Post-update Hermes navigation independently verified](media/omarchy-maintenance-google.png)

Sources for the signed ARM repository and update prerequisites:
[official package repository](https://github.com/omacom/omarchy-pkgs),
[upstream keyring update procedure](https://github.com/omacom/omarchy/blob/quattro/bin/omarchy-update-keyring).
Runtime addresses, account names, credentials and operator logs remain private.
