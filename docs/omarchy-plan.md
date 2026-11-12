# Omarchy guest plan

Status: experimental; Phase 1 started 2026-11-12. No Linux profile is offered by the released installer. See [Phase 1 evidence](omarchy-phase1-acceptance.md).

## Scope and decisions

Use Apple Silicon and the existing patched Lume first. The baseline is foreground agent control, not isolated background control. CuaDriver 0.44.0 has Linux ARM64 release artifacts; Hyprland compatibility and artifact verification are the questions to test. Native Wayland and the optional seat plugin are separate experiments. Chromium/Electron must use foreground actions; never imply that their input is isolated or that focus/pointer state is restored.

Use Cua's Archboot ARM64 installation followed by Omarchy source commit `13f18b2cb7286fb54f87daf571a031aa6af3d8f0` (4.0.1). Do not conflate this with upstream edge/nightly Omarchy ISOs. Pin every downloaded input and verify it before use. Arch repositories remain rolling: record resolved package versions; a pinned source commit alone does not make package installation reproducible.

Install with VNC disabled, or through OwnMachine's relay-fronted viewer using the password-file patch, protected fixed port, and verified firewall readiness. Never expose stock weak-password VNC, including during creation. Do not attach Rosetta or host directory shares. Keep credentials and machine-specific configuration outside the repository.

## Phases

### 1. Compatibility spike (first evidence/documentation PR)

- Independently confirm Archboot's GPG fingerprint using Arch Linux's developer directory; verify signed checksum manifest and ISO.
- Pin Cua installer scripts and audit them before running only inside the disposable guest.
- Verify CuaDriver 0.44.0 Linux ARM64 SHA-256 and Sigstore identity/bundle before installation.
- Test in order: driver status; screenshot via `cua-driver mcp`; GTK AT-SPI tree and accessibility bus; foreground click/type; Chromium foreground navigation/type.
- Only after baseline tests, try `CUA_DRIVER_RS_ENABLE_WAYLAND=1`, then the optional Hyprland seat plugin. Require explicit experimental-input opt-in for mutations.
- Disable Hyprland animations. Measure capture latency at 1920x1200 and 1456x920, allocated disk usage, installation peak and idle resources. These test sizes do not change existing defaults.
- Reboot and repeat capture/input checks. Record exact versions, commands, failures, workarounds and independent observations.
- Gate: written go/no-go. Foreground-only may justify experimental viewer plus best-effort agent support; it is not full background-control acceptance. If ARM64 control fails outright, evaluate x86_64 on a separate backend.

### 2. Shared Linux guest layer

Introduce `guest_os: linux` and `guest_profile: omarchy`, Linux probes/shutdown and a configurable `provision-linux-vm.py --profile omarchy`. Separate macOS guest TCC/codesign/LaunchAgent steps from shared lifecycle. Patched Lume and host firewall remain Mac-host requirements for both guests. Add key-only SSH, guest firewall, telemetry settings and driver user systemd service bound to the graphical session. Handle disabled verification VNC throughout Linux creation. Gate: clean repeatable provision with no manual ownership repair or weak listener. Ubuntu can reuse this layer.

### 3. Viewing and control

Reuse SSH roles, private noVNC viewer and human-control lease. Foreground is the default. Validate capture and input against the actual app backend; refuse unsupported operations and unapproved experimental mutations. Gate: human reservation blocks agent writes and return restores control.

### 4. Onboarding

Offer macOS and experimental Omarchy only on compatible Apple Silicon hosts with patched Lume. Add Linux checkpoints, authenticated progress, safe resume/recovery, doctor checks and existing reminder paths. Gate: interruptions resume without repeating destructive actions and errors identify corrective steps.

### 5. Full acceptance

Fresh Docker-to-Mac installation; Hermes opens Chromium, visits Google, and saves a document in a GTK editor. Verify browser state and file independently over SSH. Record foreground/XWayland/native Wayland mode for every step. Test viewer, control handoff, lifecycle, reboot persistence and security. No claim of supported Linux automation before these pass.

### 6. Documentation and release

Publish measured resource requirements, supported applications and verified limitations: software graphics/audio/package gaps, Chromium foreground-only behavior and exact-Hyprland-ABI seat-plugin update risk. Do not copy historical package/audio counts as current results. Update catalog `known_issues`, evaluator quickstart and tutorial. Use feature -> develop -> release/* -> main PRs with release evidence.

## Configuration and support policy

CPU, RAM, disk location/capacity, display dimensions, VM name, versions, ports and SSH identities remain operator-configurable. Measure physical storage use before declaring a minimum. Do not freeze package updates silently: record update policy and retest any optional plugin against its exact compositor ABI. Omarchy remains experimental; Ubuntu/Xorg may become the first fully supported Linux profile if Omarchy only passes foreground tests.

## References

- [Lume Linux guest guide](https://cua.ai/docs/lume/guides/linux-guests)
- [CuaDriver platform support](https://cua.ai/docs/cua-driver/concepts/platform-support)
- [CuaDriver 0.44.0 assets](https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.44.0)
- [Arch Linux developer fingerprint](https://archlinux.org/people/developers/#tpowa)
- [Omarchy ARM status](https://github.com/omacom/omarchy/discussions/15702)
