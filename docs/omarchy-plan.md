# Omarchy guest plan

Status: Omarchy foreground support acceptance passed on the final security build, verified 2026-11-12; unreleased PR #15. See [final fresh-install evidence](omarchy-final-acceptance.md). Foreground is the default; an optional bounded GTK background keyboard experiment also passed. Clean provisioning, Docker/Hermes browser/editor tasks, authenticated final screenshot, setup-key retirement and guest-restart persistence pass. The released macOS baseline is unchanged; this work is awaiting PR review and release. See [acceptance evidence](omarchy-phase1-acceptance.md).

## Scope and decisions

Use Apple Silicon and the existing patched Lume first. The baseline is foreground agent control, not isolated background control. CuaDriver 0.47.19 is the verified Linux ARM64 pin (macOS remains 0.44.0); Hyprland compatibility and artifact verification are the questions to test. Native Wayland and the optional seat plugin are separate experiments. Targeted Chromium/Electron keyboard input requires explicit opt-in to the ABI-matched native Hyprland input module; the stock driver alone refused the acceptance task. Chromium/Electron must use foreground actions; never imply that their input is isolated or that focus/pointer state is restored.

Use Cua's Archboot ARM64 installation followed by Omarchy source commit `13f18b2cb7286fb54f87daf571a031aa6af3d8f0` (4.0.1). Do not conflate this with upstream edge/nightly Omarchy ISOs. Pin every downloaded input and verify it before use. Arch repositories remain rolling: record resolved package versions; a pinned source commit alone does not make package installation reproducible.

Install with VNC disabled, or through OwnMachine's relay-fronted viewer using the password-file patch, protected fixed port, and verified firewall readiness. Never expose stock weak-password VNC, including during creation. Do not attach Rosetta or host directory shares. Keep credentials and machine-specific configuration outside the repository.

## PR scope and progress

All Omarchy implementation and acceptance work stays in PR #15 until reviewed. The existing macOS release remains the production baseline. Checkboxes require recorded evidence; a successful build alone is not a runtime pass. Release preparation belongs here; merging, tagging and publishing still follow the repository Gitflow approval rules.

- [x] Verify installation inputs and boot the isolated ARM64 guest.
- [x] Verify native Wayland foreground capture, editor save, Chromium and guest reboot.
- [x] Resolve native window discovery and targeted GTK accessibility (0.47.19, without plugin).
- [x] Build/test the optional Hyprland plugin against the exact compositor ABI; record limitations (21 tests per build; bounded foreground smoke and disabled-transport refusal).
- [x] Measure sampled installation disk maximum and idle resources; exact transient peak is not certified.
- [x] Implement shared Linux provisioning, hardening, graphical-session driver and lifecycle. A fresh empty-disk repeat passed without guest repairs; see the acceptance record.
- [x] Verify private viewer, SSH roles and human/agent handoff for Linux. Separate-account Docker streaming, role refusals, reservation refusal and browser pause/resume passed.
- [x] Add configurable experimental Omarchy onboarding, resume and doctor checks. Creation resume and changed-configuration refusal passed; authenticated remote checks, progress import and retirement passed.
- [x] Complete fresh Docker-to-Mac and real Hermes model acceptance; the follow-up below also verifies Hermes-driven installation and boot transitions after operator trust preparation.
- [x] Finish resource guidance, future catalog disclosures and evaluator docs.
- [x] Build and verify committed source/plugin bundles and validate the extracted plugin. Final CI status is recorded on PR #15; release/tag/catalog updates require a separate approved release.

## Phases

### 1. Compatibility spike

- Independently confirm Archboot's GPG fingerprint using Arch Linux's developer directory; verify signed checksum manifest and ISO.
- Pin Cua installer scripts and audit them before running only inside the disposable guest.
- Verify CuaDriver 0.47.19 Linux ARM64 SHA-256 and Sigstore identity/bundle before installation.
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

CPU, RAM, disk location/capacity, display dimensions, VM name, versions, ports and SSH identities remain operator-configurable. Measure physical storage use before declaring a minimum. Do not freeze package updates silently: record update policy and retest any optional plugin against its exact compositor ABI. Support covers the tested foreground ARM64 configuration on Apple Silicon. Background input remains experimental; foreground acceptance does not establish universal app, background-seat or cloud support.

## References

- [Lume Linux guest guide](https://cua.ai/docs/lume/guides/linux-guests)
- [CuaDriver platform support](https://cua.ai/docs/cua-driver/concepts/platform-support)
- [CuaDriver 0.47.19 Linux assets](https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.47.19)
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
pass through real Hermes, with independent guest checks. The subsequent clean run below passed without that recovery; its operator boot handoffs remain explicit.


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
- [x] Complete authenticated guided checks/import/screenshot/retirement against that guest, then browser/editor/model acceptance and resource measurements.

## Earlier run scope (superseded by the guided follow-up below)

The clean run used operator scripts for bootstrap ISO preparation, base/desktop
provisioning and boot handoffs. The freshly installed Hermes plugin then invoked
authenticated preflight, firewall, permissions, viewer-check, final screenshot
verification and setup-key retirement. This is not evidence that Hermes invoked
every destructive installation stage end to end. Those operator handoffs are
part of the experimental quickstart.

Foreground-only experimental release preparation is a **go** for the measured
configuration. Background seats, broad app compatibility, rolling package updates,
cloud hosts and a new Linux-profile physical-host reboot test are not certified.
The existing macOS host-reboot evidence does not become a Linux acceptance claim.

## Hermes-driven installation follow-up

PR #15 now includes explicit authenticated `linux-boot-installer`,
`linux-boot-system` and `linux-start-desktop` transitions. Each checks the selected
VM, prior stage, pinned guest identity and its own checkpoint; uncertain transitions
require inspection. Installer/base boots keep VNC disabled. The graphical restart
requires verified hardening, relay configuration and host firewall readiness.

- [x] Complete a fresh guest from the installed Hermes CLI, including boot transitions.
- [x] Interrupt the client during base installation, restart the isolated Hermes
  container, import authenticated progress and continue without destructive replay.
- [x] Verify final driver/capture, viewer and retirement through that same flow.
- [x] Record the background-input compatibility boundary separately from the
  foreground installation acceptance.

Initial trust remains an operator responsibility: verify the source ISO and patched
Lume build, prepare the private guest bootstrap identity, pin host keys, pair the
restricted setup/runtime keys and obtain administrator firewall approval. These
are security prerequisites, not consent that a chat model can silently grant itself.


The [Hermes-driven follow-up](omarchy-guided-acceptance.md) now passes the entire
post-pairing installation sequence and client interruption/resume. A separately
opted-in Mousepad background typing/save test also passed while Foot stayed
foreground in 52 samples; human reservation refused a subsequent background
write. This is a bounded keyboard experiment, not full background desktop support.

## Security review follow-up

- [x] Remove automatic host VNC credential export for **all** guests, including
  the `lume-config` VirtioFS share and guest-home SSH fallback, from both normal
  and USB/recovery VM start paths. The common patch also covers saved-state resume
  through normal `run`; do not resume an old saved state that contains the former
  device configuration. Use a cold start after deploying the new build.
- [x] Install a root-owned SDDM gate **before** the desktop installer can enable
  graphical boot. Require a root-owned completion receipt plus live SSH,
  firewall and sudo checks. Missing/failed hardening blocks managed graphical login.
- [x] Recheck hardening before driver mutation, completed-stage verification,
  driver installation, daemon startup and MCP startup. These controls prevent
  accidental stage bypass, not deliberate changes by an administrator inside the guest.
- [x] Correct the current Linux driver references and scope paragraph; retain the
  historical 0.44.0 failure evidence and the separate macOS 0.44.0 pin.

Linux 0.47.19 archive SHA-256:
`5a1daed6820e6063f33dddbd3e5403d89dc27b8cf197b45df9af0fddd4fd50bb`.
Sigstore issuer: `https://token.actions.githubusercontent.com`.
Certificate identity:
`https://github.com/trycua/cua/.github/workflows/cd-rust-cua-driver.yml@refs/tags/cua-driver-rs-v0.47.19`.
Cosign verified the downloaded archive and its bundle again during this review.
The upstream release explains that its GitHub “Pre-release” flag prevents
monorepo Latest-tag collisions; plain SemVer driver versions are stable releases.
The final fresh-install acceptance below establishes the bounded foreground support claim; the driver version alone does not certify applications.
See [security regression evidence](omarchy-security-acceptance.md).

## Final security-build acceptance and support decision

- [x] Deploy and verify the final Lume patch at the configured app path.
- [x] Repeat the complete Hermes-driven fresh installation with the hardening gates, without manual guest repairs.
- [x] Repeat client interruption, Docker restart, authenticated progress import and safe resume.
- [x] Prove missing hardening blocks graphical startup and driver installation before sealing.
- [x] Rerun real-model foreground Chromium → Google and Mousepad save; independently verify results.
- [x] Verify human reservation refuses model input with no dispatch.
- [x] Restart the guest; verify saved data, VNC rotation/isolation and explicit read-only capture recovery.
- [x] Finalize the foreground support claim and retain experimental background boundaries.
- [ ] Merge/release through Gitflow only after separate authorization.

**Decision:** ready for review as Omarchy foreground desktop support on Apple
Silicon for the tested pinned configuration. Do not market this as universal or
full background control. First-run terms/keyring decisions remain operator
handoffs. See [final report](omarchy-final-acceptance.md) for versions, failures,
recoveries and independent checks. This supersedes earlier experimental-only
release decisions above; their evidence remains historical.
