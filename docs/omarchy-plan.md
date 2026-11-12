# Omarchy guest plan

Status: experimental; Phase 1 started 2026-11-12. ARM64 boot, native Wayland foreground control, Chromium and guest reboot smoke checks pass; native window discovery and GTK accessibility now pass with the Linux-only driver 0.47.19 pin. No Linux profile is offered by the released installer. See [Phase 1 evidence](omarchy-phase1-acceptance.md).

## Scope and decisions

Use Apple Silicon and the existing patched Lume first. The baseline is foreground agent control, not isolated background control. CuaDriver 0.47.19 is the verified Linux ARM64 pin (macOS remains 0.44.0); Hyprland compatibility and artifact verification are the questions to test. Native Wayland and the optional seat plugin are separate experiments. Chromium/Electron must use foreground actions; never imply that their input is isolated or that focus/pointer state is restored.

Use Cua's Archboot ARM64 installation followed by Omarchy source commit `13f18b2cb7286fb54f87daf571a031aa6af3d8f0` (4.0.1). Do not conflate this with upstream edge/nightly Omarchy ISOs. Pin every downloaded input and verify it before use. Arch repositories remain rolling: record resolved package versions; a pinned source commit alone does not make package installation reproducible.

Install with VNC disabled, or through OwnMachine's relay-fronted viewer using the password-file patch, protected fixed port, and verified firewall readiness. Never expose stock weak-password VNC, including during creation. Do not attach Rosetta or host directory shares. Keep credentials and machine-specific configuration outside the repository.

## PR scope and progress

All Omarchy implementation and acceptance work stays in PR #15 until reviewed. The existing macOS release remains the production baseline. Checkboxes require recorded evidence; a successful build alone is not a runtime pass. Release preparation belongs here; merging, tagging and publishing still follow the repository Gitflow approval rules.

- [x] Verify installation inputs and boot the isolated ARM64 guest.
- [x] Verify native Wayland foreground capture, editor save, Chromium and guest reboot.
- [x] Resolve native window discovery and targeted GTK accessibility (0.47.19, without plugin).
- [x] Build/test the optional Hyprland plugin against the exact compositor ABI; record limitations (21 tests per build; bounded foreground smoke and disabled-transport refusal).
- [ ] Measure installation peak and idle resources.
- [x] Implement shared Linux provisioning, hardening, graphical-session driver and lifecycle. A fresh empty-disk repeat passed without guest repairs; see the acceptance record.
- [x] Verify private viewer, SSH roles and human/agent handoff for Linux. Separate-account Docker streaming, role refusals, reservation refusal and browser pause/resume passed.
- [ ] Add configurable experimental Omarchy onboarding, resume and doctor checks. Profile routing, Linux stages, no-destructive-replay checks and viewer/doctor flags are implemented; complete authenticated Docker acceptance remains open.
- [ ] Complete fresh Docker-to-Mac and real Hermes model acceptance.
- [ ] Finish resource guidance, catalog disclosures, evaluator docs and release validation.

## Phases

### 1. Compatibility spike

- Independently confirm Archboot's GPG fingerprint using Arch Linux's developer directory; verify signed checksum manifest and ISO.
- Pin Cua installer scripts and audit them before running only inside the disposable guest.
- Verify CuaDriver 0.44.0 Linux ARM64 SHA-256 and Sigstore identity/bundle before installation.
- Test in order: driver status; screenshot via `cua-driver mcp`; GTK AT-SPI tree and accessibility bus; foreground click/type; Chromium foreground navigation/type.
- Only after baseline tests, try `CUA_DRIVER_RS_ENABLE_WAYLAND=1`, then the optional Hyprland seat plugin. Require explicit experimental-input opt-in for mutations.
- Disable Hyprland animations. Measure capture latency at 1920x1200 and 1456x920, allocated disk usage, installation peak and idle resources. These test sizes do not change existing defaults.
- Reboot and repeat capture/input checks. Record exact versions, commands, failures, workarounds and independent observations.
- Gate: written go/no-go. Foreground-only may justify experimental viewer plus best-effort agent support; it is not full background-control acceptance. If ARM64 control fails outright, evaluate x86_64 on a separate backend.

Phase 1 follow-ups from the laptop run: native discovery/GTK targeting and bounded optional-plugin tests now pass; sample installation peak and idle resources. The optional plugin does not have broad background-control certification. Preserve foreground-only scope until those results justify more. Default 2x scaling clipped GTK dialogs, so Linux setup needs an explicit configurable scale. Native console modifier injection, missing live `gptfdisk`, Chromium first-run terms/keyring prompts and persistent first-login notifications must become documented/bootstrap-handled steps. Do not count direct MCP smoke tests as full Hermes acceptance.

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

Implementation commands and safety boundaries: [Linux development guide](linux-development.md).

## Fresh provisioning follow-up (2026-11-12)

- [x] Run pinned base and desktop stages against a newly created guest with VNC disabled.
- [x] Reinstall the base from an empty disk after fixing inherited-umask permissions;
  verify D-Bus, networking and key-only SSH after boot without a directory repair.
- [x] Reach the graphical desktop and verify CuaDriver's standard-mode readiness.
- [x] Add regression checks for sudo rule modes under umask 077 and ownership of
  every newly created desktop support parent.
- [x] Repeat complete provisioning with both hardening fixes included. The later keyring-guarded clean run passed without guest repairs; earlier recovery evidence is retained.
- [x] Verify default scale 1 across first-login dialogs, browser and editor. Chromium consent and GTK save dialogs were fully visible.
- [x] Finish the separate-account browser handoff and real Docker/Hermes browser/document tasks.

See the appended fresh-install evidence in the acceptance record. Original failed
checkpoints remain preserved locally; corrected code does not rewrite that history.


Docker/browser acceptance found that exact-window foreground input requires the
opt-in Hyprland module. Keep that requirement visible in onboarding and doctor
output; do not equate driver capture readiness with input support. The first real
model run reached Chromium discovery/capture and safely stopped on this refusal.
Private streaming, role checks and a human-reservation input refusal now have
cross-account Docker evidence. Module-enabled browser and document tasks now
pass through real Hermes, with independent guest checks. Complete fresh guided
setup remains open because hardening required recovery.


- [x] Rebuild the optional input module in the fresh guest, pass 21 tests and
  verify exact ABI plus explicitly enabled transport.
- [x] Complete the module-enabled real Hermes Chromium-to-Google task and
  independently verify the live title and history URL.
- [x] Retest GTK create/save after correcting Linux launch identity and text activation; independently verify exact saved bytes and live editor title.
- [x] Integrate an explicit optional-module installation/readiness path; do not
  advertise module-free targeted Chromium input or silently broaden its target.

Foreground input readiness is now reported separately from driver/capture readiness.
The live module-enabled probe passes; absent, mismatched, test-only or non-private
transports report false. The explicitly opted-in installer built the module, passed all 21 tests, enabled protocol-3 private input, and restored readiness after a guest restart. This is foreground-only evidence.


### Clean-repeat progress and newly found compatibility issues

- [x] Private seeded installer boots with pinned key-only SSH and no native-console
  key entry. Stock SSH and the anonymous web terminal are masked.
- [x] Fresh base/desktop installation completes without directory ownership repairs.
- [x] First-login user-service setup completes after including missing units and
  ARM command paths; no failed user units were observed.
- [x] Hardening enforces key-only/non-root SSH, guest firewall and exact shutdown
  sudo. Its read-only verifier now accepts OpenSSH's mixed-case setting output.
- [x] Explicit optional input installation and guest-restart persistence pass.
- [x] Diagnose and visually verify the Qt 6.12 palette collision fix; integrate it
  into provisioning with a pinned input-hash manifest.
- [x] Repeat from an empty disk with palette, verifier and package-keyring fixes included. Base/desktop/hardening/driver readiness all passed without guest repairs.
- [ ] Complete authenticated guided setup/import/retirement against that guest,
  then repeat browser/editor/model acceptance and resource measurements.
