# Final Omarchy fresh-install acceptance

2026-11-12; installed OwnMachine `e69e554d6d48e6f47738ee7165cdbfd2d19913f0`, Hermes `b5f15a6d3188e94f815d504d5ebbeb926e1bd08a`.

A fresh Apple Silicon guest and separate Docker agent/viewer installation passed
the complete Hermes-driven post-pairing flow without manual guest repairs.
Operator source/image trust, key pairing and administrator firewall preparation
remained prerequisites. Installer boots had VNC disabled.

An intentional client timeout during base installation and Docker agent restart
passed interruption/resume checks: authenticated progress observed the completed
checkpoint without repartitioning. Before hardening, managed graphical startup
and driver installation refused; normal hardening then enabled both.

Final verification captured a real screenshot, checked runtime-role separation and
viewer connectivity, retired the setup key and proved its rejection.

## Real-model tasks and independent checks

- Chromium reached Google after human terms/keyring handoffs. Independent viewer,
  native-window and browser-history checks confirmed navigation. The operator
  dismissed prompts but did not navigate; this was not fully unattended.
- Mousepad saved the requested document. Independent file contents and saved-window
  state confirmed completion; the operator did not write or save it.
- Human reservation refused an agent write without dispatch or fallback.

![Independently verified Chromium result](media/omarchy/final-google.png)

Guest restart preserved saved data and recovered driver readiness. The first
capture used a closed transport and stopped; an explicitly requested read-only
reconnect succeeded after inspection. No input was replayed. Firewall checks,
private credentials/logs, credential rotation and absence of guest exports passed.

## Scope and limitations

Tested foreground input used an explicitly enabled ABI-matched Hyprland module.
Background input remains experimental; Chromium/Electron background, general Qt,
XWayland, background pointer/drag and cloud hosts are not certified. One active
Hermes conversation owns the workspace. Source pins do not freeze rolling packages.
Measured VM allocation excludes build/download caches and is not a minimum-space
promise. See [operator guidance](linux-development.md), [later maintenance retest](security-maintenance-acceptance.md)
and [macOS evidence](macos-cold-start-acceptance.md). Publication remains on hold.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
