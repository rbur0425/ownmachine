# Omarchy feasibility and provisioning acceptance

Historical PR 15 development experiments, 2026-11-12.

The ARM64 feasibility run verified source/image provenance, boot, networking,
desktop installation and foreground capture/input. Initial XWayland capture and
native-window discovery limitations led to native Wayland discovery and targeted
GTK accessibility support. Chromium input required the explicitly enabled
ABI-matched Hyprland module. Early manual repairs are not clean-install evidence.

Subsequent fresh provisioning runs corrected first-login service/keyring setup;
Docker-to-Mac model navigation and document saving passed independent checks.
The [final fresh-install report](omarchy-final-acceptance.md) is the relevant
security-build baseline, including interruption/resume and remaining limits.

Historic timing, disk and memory samples were small, environment-dependent
observations, not performance or minimum-resource guarantees. Use the pinned input
provenance in the [plan](omarchy-plan.md) and the current [operator guide](linux-development.md),
not early experimental versions or reproduction settings.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
