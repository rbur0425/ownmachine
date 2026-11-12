# Omarchy Phase 1 acceptance

Date: 2026-11-12. Status: experimental foreground-only acceptance passed. The final clean-run section records no-repair provisioning, real Hermes browser/editor/reopen tasks, authenticated screenshot and setup-key retirement. Earlier sections preserve failures and interim findings; they are not the current completion status. This is not broad Linux or background-control certification.

## Environment and scope

Apple Silicon laptop; patched Lume 0.7.0, upstream `666c196f42dc9c83dbe075e20318f16c3e3a6d84`. Existing disposable demo VM gracefully stopped and deleted with explicit owner authorization; allocated size approximately 27 GiB. Free space increased from approximately 37 to 64 GiB. Dedicated test-account storage was already empty. No other VM or host was deleted/restarted.

## Verified inputs

- Cua installer scripts pinned at `36c576698e7265a84fb3469c8b9d2c9824df6931` under `docs/public/scripts/omarchy-arm64-lume/`.
- Omarchy source target: `13f18b2cb7286fb54f87daf571a031aa6af3d8f0` (4.0.1).
- The guide's Archboot 2026.08.25 / kernel 7.2.0 image returned HTTP 404. The same monthly archive offers `archboot-2026.08.31-02.07-7.2.2-2-aarch64-ARCH-aarch64.iso`; this is a documented substitution, not the exact guide-tested kernel.
- ISO size: 484345856 bytes. SHA-256: `e96e17a04aec8ffef407d1a1d1718cf4eea48fa51aaac0f901856399cfa57f2e`.
- BLAKE2b matched the signed monthly manifest: `b22e2c54211c7415120fc363fe9baddeba5b6bfefb2d28ff5388c5874cf15912c940397db94e64c72fe6515307b5f07d4994310754a1d0f22211bb4ac95d5676`.
- GPG emitted GOODSIG and VALIDSIG for fingerprint `5B7E3FB71B7F10329A1C03AB771DF6627EDF681F`, independently confirmed in [Arch Linux's developer directory](https://archlinux.org/people/developers/#tpowa). The isolated keyring has no web-of-trust certification; fingerprint verification was explicit. Keyserver access through GPG failed, so the identical fingerprint key was retrieved over HTTPS and imported.
- Driver: `cua-driver-rs-0.44.0-linux-arm64-binary.tar.gz`, SHA-256 `ff2c83ea6dfff11130bb0928aa06c41c45316f6eb201a414f0595e4d05616ce0`.
- Driver legacy Sigstore bundle verified with Cosign 3.1.4: `Verified OK`, issuer `https://token.actions.githubusercontent.com`, identity `https://github.com/trycua/cua/.github/workflows/cd-rust-cua-driver.yml@refs/tags/cua-driver-rs-v0.44.0`. Python sigstore rejected the legacy bundle schema; verification was not bypassed.
- Installer SHA-256: `install-arch.sh` = `f62d7d5e5c93201b010a60d71fe6f8d9a7a0adb472fc0e86dcc4d5064def61d4`; `install-omarchy.sh` = `6208dfdad21c42f353661fdd7bcc67adec2250415f8db056abc75a41068e9fbe`.

## Source-audit findings before boot

Linux Lume configuration automatically attaches Rosetta when available, enables host clipboard sharing, and configures host microphone/audio. Merely omitting `--shared-dir` does not disable these. The isolated experimental build removes those devices and rejects directory shares. This is an experiment prerequisite, not a change to the released Lume build. The exact replacement section is included below for reproducibility. Default patched VNC-password and native-clipboard patches remain applied.

Cua's base installer creates a passwordless-sudo desktop user and enables SSH; the Omarchy installer enables additional services including Docker. These are upstream experimental defaults, not accepted production guest hardening. Phase 2 must explicitly minimize services and harden access. Package resolution remains rolling despite pinned installer/source commits.

## Test ledger

| Check | Result |
|---|---|
| Host storage and approved cleanup | Passed |
| Signed Archboot manifest and image checksum | Passed |
| Driver checksum and Sigstore identity | Passed |
| Linux host-integration source audit | Found automatic shares; isolated build required |
| Native Archboot boot and networking | Passed: ARM64 shell, DHCP and package mirror configuration |
| Installer download/checksum inside guest | Passed; matches host-reviewed script |
| Installed desktop and reboot | Passed: disk boot, then stop/start at second display size; saved file hash unchanged |
| MCP status/screenshot | MCP initializes; default XWayland capture fails; opt-in native Wayland desktop capture passes |
| GTK accessibility bus/tree | Bus reachable; targeted tree fails because driver discovers zero native windows |
| Foreground click/type and Chromium | GTK menu clicks, typing and file save passed; Chromium foreground navigation and page typing passed |
| Native Wayland / optional seat plugin | Native Wayland tested explicitly after default backend failure; optional ABI-bound plugin not attempted |
| Capture timings, installed disk use | Measured below; installation peak not sampled |
| Full OwnMachine/Hermes model acceptance | Later phase |

## Initial live results

The isolated build compiled successfully (79.66 seconds) and passed `codesign --verify --deep --strict`. Created a separate Linux guest with 8 vCPUs, 8 GiB RAM, a 64 GiB sparse disk, and 1920x1200 display. This experiment uses the interactive host account for the native console, not the dedicated production host account; dedicated-account/relay acceptance remains untested for Linux.

Booted the verified ISO using `--vnc disabled --display native`: Lume reports `vncUrl: null`, and `lsof` found no TCP listener for the VM process. No Rosetta, host filesystem, clipboard or audio device is configured by the experimental Linux build. Native viewer toolbar controls still appear; they were not used. Removing misleading controls and checking runtime share APIs remain production integration work.

Observed Archboot 7.2.2-2-aarch64-ARCH, configured English locale, DHCP/NAT and Arch Linux ARM package mirror, declined the offered live kernel upgrade, and reached the root console. `uname -m` returned `aarch64`. Downloaded the pinned base installer and verified SHA-256 inside the guest against the independently reviewed host copy.

Native text injection converted the colon in `https://` to a shell separator on the first command. Explicit Shift and Ctrl combinations also lost their modifiers; enabling native key capture did not fix this. Retried successfully with `curl --proto-default https` and a scheme-less hostname. This is native console bootstrap input, not evidence of CuaDriver or MCP input reliability. Record this in onboarding polish; do not recommend raw pasted commands without observing their result.

The owner approved temporary key-only SSH administration and CuaDriver desktop control inside this guest. The following checks were performed after approval; approval itself is not test evidence.

## Installed guest and control evidence

The base installer initially failed because Archboot lacked `sgdisk`; installing `gptfdisk` in the live guest resolved it. The installed guest boots without the ISO. Resolved packages: kernel `7.3.4-1-aarch64-ARCH`, Hyprland `0.57.2-1`, Mesa `1:26.2.6-1`, Chromium `156.0.8078.79-1`, AT-SPI `2.62.1-1`. These rolling versions differ from the guide; the Omarchy source commit remains pinned.

Temporary SSH uses a locally generated key, pinned guest host key, no password/root login, and no forwarding. The live image's default web console and SSH service were stopped. The installed guest's nftables rules allow SSH only from the observed host-side address, plus established traffic, DHCP and ICMP; other inbound traffic and forwarding default to drop. The nftables unit is a successful oneshot (inactive after exit); inspecting the actual rules confirms enforcement and persistence. Docker, CUPS and Bluetooth services were disabled. Upstream passwordless sudo and production service minimization remain Phase 2 work. No credentials or deployment addresses are included in this report.

The signed ARM64 driver runs as the graphical guest user with the session's display, D-Bus and Hyprland environment. Telemetry is disabled. Direct `cua-driver mcp` initializes successfully. This is a protocol compatibility test, not a Hermes model-driven run and not OwnMachine's released relay/provider integration.

Default backend desktop capture returned an X11 GetImage Match error. After explicitly enabling `CUA_DRIVER_RS_ENABLE_WAYLAND=1`, desktop capture succeeded. AT-SPI's bus and registry are running, but `list_windows` returns no windows and `get_window_state` refuses the Mousepad PID. Hyprland independently reports the mapped native Wayland editor. A process-only accessibility inventory is not a GTK accessibility-tree pass.

Through MCP desktop foreground actions, the driver typed `OwnMachine foreground test: ABC 123`, opened Mousepad's File menu by coordinates, chose Save, typed a filename and clicked Save. Reading the resulting file separately over SSH confirmed the exact 35-byte text; SHA-256 `33c59515068fdd9f10cf217f25c653acc787dc4e88c0d474a3540fe759b5b55f`. Action responses only reported `effect: unverifiable`; screenshots and file readback establish the outcome. `Ctrl+S` created a Save dialog, but automatic 2x scaling placed part of it offscreen. Enter alone did not complete the save; the explicit Save click did. Immediate captures can precede visible changes, so observe again before retrying a mutation.

The default 1920x1200 output used scale 2, yielding a 960x600 logical capture and clipped dialogs. Setting the guest's `omarchy_gdk_scale` and `omarchy_monitor_scale` to 1 made a freshly opened Save dialog usable. The apparently washed-out editor was underneath a modal, not proof of a capture codec failure. This scale configuration must become part of the Linux bootstrap rather than an undocumented repair.

Chromium launch via MCP reached its first-run “Additional Terms of Service” window. After explicit owner approval, the driver clicked Accept. A new-keyring password prompt was canceled without creating a credential. Google loaded; the driver clicked its search field and typed `OwnMachine foreground browser test`, verified in a subsequent capture. It then used Ctrl+L, typed `https://www.google.com/` and pressed Return. Independent read-only browser-history inspection found the HTTPS URL and title `Google`; Hyprland also reported the native Wayland Chromium window titled `Google - Chromium`. A normal SQLite read hit Chromium’s database lock; an immutable read of the existing database supplied corroborating history, not a live-tab guarantee. No remote-debugging port or browser automation extension was enabled.

A graceful guest shutdown followed by a new disk boot at 1456x920 restored the desktop and firewall rules. The editor file's SHA-256 was unchanged. Rebooted MCP capture succeeded at the new native dimensions. The driver reopened the saved file, appended ` | reboot verified` and saved with Ctrl+S; independent SSH readback confirmed the resulting text and SHA-256 `79773d9e1568e4461e417765c531f77f560b7a0274c4dd0af0b6b2312dbbd98d`. Host reboot was not performed.

### Measurements

| Measurement | Observation |
|---|---|
| 1920x1200, scale 1, three MCP capture round trips | 112, 129, 152 ms (median 129 ms) |
| 1456x920, scale 1, three MCP capture round trips after reboot | 108, 70, 68 ms (median 70 ms) |
| Guest root filesystem use | Approximately 8.9 GiB, including source history and package cache |
| Host allocated VM storage | Approximately 9.4 GiB; virtual capacity 64 GiB |
| Guest memory snapshot with test apps | 1,457 MiB used of 7,920 MiB; not an idle benchmark |
| Host free space after installation | Approximately 53 GiB |
| Installation peak / idle CPU | Not sampled; no minimum-resource claim |

Capture timings include local SSH/MCP round trips, use three samples only, and differ in scene content. They are not streaming FPS or a controlled performance comparison. Animations were disabled. Software graphics remains in use.

### Decision and remaining gates

**Continue an experimental foreground-only Linux path; do not offer it as supported automation yet.** ARM64 boot, capture and an independently verified GUI file save justify further work. Targeted native window discovery/GTK accessibility still needs closure. Chromium foreground navigation and post-reboot input now pass the bounded smoke checks; full Hermes/OwnMachine integration remains later work. The optional Hyprland plugin has not been built or loaded; its exact-ABI compatibility and separate input opt-in must be evaluated before relying on it. Keep these limitations visible rather than treating the desktop-wide fallback as background control acceptance.

## Continued development: discovery and targeted accessibility

The initial 0.44.0 failure was traced to Hyprland 0.57 omitting `id` on an unused `specialWorkspace`. Upstream driver 0.47.19 handles that omission. Its ARM64 binary archive SHA-256 is `5a1daed6820e6063f33dddbd3e5403d89dc27b8cf197b45df9af0fddd4fd50bb`; both the release checksum and Sigstore workflow identity verified. This is a Linux-only version change; the released macOS driver stays pinned to 0.44.0.

With the optional plugin unloaded, 0.47.19 discovered Mousepad's exact native window, returned its GTK AT-SPI tree and a valid window screenshot, and performed `set_value` on a snapshot-bound text element. The action returned `effect: confirmed`, `route: accessibility` and an exact value readback. A subsequent tree and window capture showed `OwnMachine targeted accessibility verified.`. Discovery no longer needs a compositor plugin workaround.

Built the optional plugin from driver tag source commit `ef1e84d6c880ab8aee7587c3d0057a288e764b69` against installed Hyprland 0.57.2, using GNU C++ 16.1.1 (matching the compositor's compiler family/version). Both default discovery and `CUA_HYPRLAND_INPUT=ON` builds passed **21/21 CTest tests**. Live load reported matching compiled/runtime ABI `11cbc6c577b84ffb1edf4df3fc5b6128c3ae6947_aq_0.16_hu_0.14_hg_0.6_hc_0.1_hlg_0.6`.

The default build advertised discovery-only status, not application targeting. After explicitly enabling the input build in this disposable guest, targeted foreground click/type inserted `PLUGIN` at the editor caret; AT-SPI readback confirmed the insertion. Turning the plugin transport off and reloading caused the next targeted type to return `foreground_unavailable`, `effect: refused`; the sentinel text did not appear. This is a bounded foreground/refusal smoke, not independent-seat or background isolation certification. Desktop restart remains the safe module-replacement lifecycle.

A new portable guest-only installer, `scripts/linux-guest.py`, installed a pinned driver and a user systemd service tied to `graphical-session.target`. Its live readiness probe confirmed the graphical session, accessibility bus, running daemon and standard permission mode. No linger or macOS-style TCC grants are fabricated. The host relay/doctor now have a separate Linux readiness path. Reproducible Linux isolation is an explicit native-build option, `OWNMACHINE_LINUX_GUESTS=1`; existing macOS-only builds remain accepted for macOS. The Linux-capable build completed and passed provenance/signature verification. Full provision/viewer/onboarding integration is still in progress in PR #15.

## Shared Linux layer follow-up

The portable hardener passed inside the disposable guest. Key-only SSH remained
usable; the dedicated nftables service and user driver were active; unrestricted
`sudo -n /usr/bin/true` was refused; and the guest-side recovery-password transfer
file was removed. The systemd MCP launcher returned a GTK tree and screenshot
in 0.135 seconds before restart. These are direct MCP tests, not a Hermes model run.

The first VNC-enabled boot correctly failed isolation because upstream Lume adds
an automatic configuration folder. The Linux patch now also omits that folder and
its VNC credential file. The rebuilt app booted through the relay with a protected
password file, a fixed port, current root firewall attestation and an independently
confirmed application block. A distinct Linux bundle identifier resolved the
observed firewall registration collision. After guest shutdown/start, all Linux
readiness checks passed again. The viewer-role pipe produced the expected RFB
3.8 greeting; the agent role refused VNC and the viewer role refused MCP. These
local forced-command tests do not yet prove separate-user SSH/noVNC handoff.

The new provisioner's live creation test made a separate empty Linux VM and a
verified checkpoint. Repeating the same command returned the checkpoint without
recreating its disk. Base/desktop installer integration remains open.

A post-hardening sample with Mousepad open showed 1.11 GB guest used memory and
10.15 GB filesystem use (decimal), with 8.31 GB visible guest memory. This is a
single sample, not an installation-peak measurement or a supported minimum.
The driver/plugin builds and retained package caches affect disk consumption.

## Repository validation

- Full suite with the established Hermes validation environment: **354 tests passed, zero skips**; the subsequent host OS-mismatch guard also passed all 29 host tests.
- An initial system-Python run lacked `websockets`/Hermes: 7 errors and 28 skips; rerunning in the correct dependency environment passed. No code was changed to suppress tests.
- Hermes plugin validation with `--install-deps`: **passed**, safe security scan; existing in-process-only isolation warning remains disclosed. Hermes checkout: `b5f15a6d3188e94f815d504d5ebbeb926e1bd08a`.

## Reproduction configuration

This is an operator experiment, not the supported installer. Set `LUME_BIN` to the independently built/signed isolated app, `VM_NAME` to a new disposable name, `VM_STORAGE` to a private absolute storage directory, and `ARCHBOOT_ISO` to the verified ISO. These values are operator-owned; no laptop identity or credentials are required in source.

```sh
"$LUME_BIN" create "$VM_NAME" --os linux --cpu "${VM_CPU:-8}" \
  --memory "${VM_MEMORY:-8GB}" --disk-size "${VM_DISK_SIZE:-64GB}" \
  --display "${VM_DISPLAY:-1920x1200}" --verification-vnc disabled \
  --storage "$VM_STORAGE"
"$LUME_BIN" run "$VM_NAME" --storage "$VM_STORAGE" \
  --mount "$ARCHBOOT_ISO" --vnc disabled --display native
```

Virtual disk capacity is not a measured physical free-space requirement. The footprint and timings below are samples, not a certified minimum. Before recommending this path, close the remaining Phase 1 gates in [the plan](omarchy-plan.md).

## Experimental isolation change

In `libs/lume/src/Virtualization/VMVirtualizationService.swift` at the pinned Lume commit, replace the **Linux** configuration section from `// Audio configuration` through the directory-sharing assignment immediately before `// USB Controller configuration` with the following. Leave the corresponding macOS configuration alone. Apply the repository's two existing Lume patches as well. This experiment is not installed by released scripts.

```swift
// OwnMachine isolated Linux spike: no microphone/audio, host clipboard,
// Rosetta virtiofs, or arbitrary directory shares are attached.
guard config.sharedDirectories?.isEmpty != false else {
    throw NSError(domain: "OwnMachine", code: 1,
                  userInfo: [NSLocalizedDescriptionKey:
                    "Host shares are disabled for the isolated Linux spike"])
}
vzConfig.audioDevices = []
vzConfig.directorySharingDevices = []
```

The removed section creates audio devices, the Spice clipboard console port, configured directory shares and the automatic Rosetta share. Build the modified Lume target, sign the isolated app using the upstream local entitlements, and verify its signature before using the configurable commands above. This source-level isolation is separate from production runtime API hardening, which remains open.


## Fresh provisioning orchestration (2026-11-12)

A separate empty Linux guest ran the pinned base and desktop installers over
independently pinned, temporary key-only SSH. VNC remained disabled. Resource
configuration was 4 CPUs, 8 GiB RAM, 64 GiB sparse disk and 1900x1200 display;
no host directories, Rosetta, audio or clipboard devices were attached.

The first base installation inherited umask 077, creating `/etc` as 0700 and
preventing D-Bus/network startup. After adding an explicit base-install umask 022
and an `/etc` mode assertion, the disposable disk was emptied and base installation
repeated. The second boot passed D-Bus, NetworkManager and SSH checks without
repair; the independently confirmed host key survived the live-to-disk handoff.

Desktop installation completed and the native viewer visibly showed Omarchy.
Hardening then exposed two separate problems: the same private umask changed a
requested sudoers 0440 mode to 0400, and recursive root directory creation left a
0700 parent of the desktop helper owned by root. Both are fixed in code, with
regression tests for exact descriptor modes and each created parent's ownership.
The live test required an inspected mode/ownership repair and completion of the
remaining hardening steps. Its original failed checkpoints and partial driver
installation were preserved for diagnosis. **This is not a clean hardening pass.**

After recovery, the guest firewall was active, unrestricted passwordless sudo
was absent, and driver installation/readiness passed in the graphical Wayland
session. The native first-login view still showed large default-scale onboarding
notifications. The new desktop stage sets configurable scale 1 by default (2 is
available); complete first-login/browser acceptance is still pending.

Resolved packages: linux-aarch64 7.3.4-1, Hyprland 0.57.2-1, Mesa 26.2.6-1,
Chromium 156.0.8078.79-1 and at-spi2-core 2.62.1-1. A post-boot sample reported
8.9 GiB used inside the guest filesystem and 1,129 MiB used RAM. These are single
samples, not measured installation peaks or minimum host-space requirements.
No Docker-driven model or browser-handoff success is claimed for this run yet.


## Docker/browser follow-up (2026-11-12)

Two new isolated Docker containers use distinct agent/viewer UIDs and keys,
exclusive home mounts and a shared control volume. Confirmed Mac host keys were
paired with the public pairing script. Both restricted keys read status; agent
VNC and viewer MCP requests return `unsupported_operation`. The viewer key
restarted the guest through the protected relay, and Linux driver readiness
returned. A direct VNC connection from the Docker host was blocked, while the
SSH-relayed shared VNC authentication handshake passed.

The browser displayed the live desktop. Human reservation and pause/return
buttons updated control and focused the selected button. A terminal shortcut and
text reached the guest; CUA's automated mixed-case typing lost capitalization,
so this is not case-sensitive keyboard certification. While human control was
reserved, a provider keyboard attempt returned `human_takeover` without dispatch.
The test harness initially omitted the documented shared-volume ACL/database
initialization. Applying those evaluator-guide steps made both runtime accounts'
lock/transaction probes pass; private viewer access state was not mounted in the
agent container. This was a harness omission, not an undocumented product repair.

First-login inspection found missing generated theme data and an unavailable
`xdg-terminal-exec` shortcut. Fresh setup now generates a configurable bundled
theme headlessly, disables animations and uses installed `foot` for the terminal
shortcut. Live foot launch passed; the launcher/notification polish still needs
verification. Chromium's first-run terms were accepted with explicit user approval,
and its optional new-keyring dialog was canceled without creating credentials.

The installed candidate passed Hermes validation in the Docker profile. A real
model run first stopped at Hermes's one-shot approval gate. After authorizing the
requested desktop-only actions in that isolated profile, a second session found
the previous session's exclusive backend lock; restarting only the test container
released it. The subsequent real model run discovered and captured Chromium's
exact native window, then its first Ctrl+L foreground action was refused with
`foreground_unavailable`: the optional Hyprland input module was not installed.
The durable control gate stopped further writes, and the model honestly reported
that Google had not loaded. **This is a model-driven refusal pass, not desktop-task
acceptance.** The ABI-matched module test and successful browser/document tasks
remain open. No credential-store reads, production runtime changes or host reboot
were involved.

Local validation after the status/provisioning follow-ups: 361 tests passed, zero
skips, strict Hermes coverage gate passed. The earlier commit `36659d1` also passed
both Linux and macOS CI. Later commits require their own CI result.


### Module-enabled model navigation

The optional input module was rebuilt inside the fresh guest from Cua source
`ef1e84d6c880ab8aee7587c3d0057a288e764b69`, with expected Hyprland 0.57.2 and
matching GCC 16.1.1. All 21 CTest cases passed. Live status confirmed an exact
compiled/runtime ABI match; after explicit opt-in, protocol-3 transport was ready
with same-UID 0600 sockets. No automatic loading or background-control claim is made.

After visually inspecting the refused action and acknowledging it through the
viewer, a fresh real Hermes run used the installed OwnMachine provider to capture
Chromium, send foreground Ctrl+L, type `https://www.google.com`, press Return and
verify fresh page state. Independent SSH read-only checks confirmed the live
Hyprland window title `Google - Chromium` and Chromium history URL
`https://www.google.com/`, title `Google`. **The module-enabled model browser task
passed.** This does not erase the earlier refusal or certify module-free input.

The subsequent GTK task discovered Mousepad but its cold launch failed because
the provider sent the macOS `bundle_id` argument instead of Linux's discovered
`launch_path`. The model stopped on the durable review gate without creating a
file. Linux launch now uses that discovered identity, rejects a missing identity
before dispatch, and has regression coverage. The corrected model save task still
requires a live retest.


The corrected cold launch succeeded through Hermes and was independently observed
by its fresh window list/capture. The model then chose element activation on the
GTK text area, producing an unknown AT-SPI activation result; the review gate
correctly stopped it. The provider now refuses Linux text/entry activation before
dispatch and explains `set_value` or an explicitly grounded foreground pixel click.
A regression test verifies this refusal leaves the gate usable for a value edit.
The strict local suite passes 364 tests with zero skips; a completed save remains
pending at this checkpoint.


### Independently verified model document task

At candidate `166331f`, the installed plugin passed Hermes validation and the
real Docker-hosted model completed the GTK task using only `computer_use`.
Targeted `set_value` wrote and read back the requested text. Ctrl+S opened a
separate Save As window; the model rediscovered it, set its filename, and used a
freshly grounded foreground pixel click when the Save button lacked AXPress.
A fresh capture showed the saved filename with no unsaved marker.

Independent read-only SSH verification confirmed the exact line
`OwnMachine Linux acceptance: Hermes controls this desktop.` plus the editor's
trailing newline (58 bytes), and the live saved-file Mousepad title. SHA-256:
`288029d8c329dbae59db27127ceef23a91405d7083f407c23461d8b8fc8f7fc2`.
The file did not exist before this run. No operator input or direct filesystem
write completed the task for the model. This certifies this bounded GTK workflow,
not arbitrary desktop reliability or module-free foreground input.

Both CI jobs passed on `166331f` (Linux 26 seconds, macOS 1 minute 20 seconds).
The follow-up guest status probe distinguishes `foreground_input_ready` from
`driver_ready`; the new probe passed against the running module-enabled guest.
The full no-workaround provisioning repeat, headless bootstrap, optional module
installation and first-login polish remain open.

## Clean provisioning and first-login polish follow-up

The private bootstrap utility was exercised against the previously verified
Archboot source hash. It generated a private derived ISO and pinned host/client
keys, booted with VNC disabled, and reached key-only SSH without console repair.
The default live SSH and anonymous web terminal were masked. Base and desktop
installation completed on an empty disk; preserved machine identity and DHCP
configuration kept the authenticated installed guest reachable.

The first clean guest needed **no directory ownership repair**. All first-login
steps completed, including the six user services missing from the ARM installer.
Hardening applied successfully; its initial verifier falsely rejected the mixed
case emitted by current `sshd -T`. A case-insensitive verifier passed without
changing the guest's security policy. The failed checkpoint was retained.

Explicit experimental-input installation built the pinned Cua module, passed all
21 tests, and enabled production protocol-3 same-user input. After a protected
relay restart, its graphical-session unit exited successfully and input readiness
returned. Guest memory reported 897 MiB used of 7,921 MiB, with no swap. Ten-second
host samples reached 9.48 GiB allocated for the 64 GiB sparse disk; this is a
sampled maximum, not an exact installation peak or total host storage requirement.
It excludes ISO/build inputs and the Mac-side application build.

Qt 6.12's `Color` singleton collided with Omarchy's palette, leaving notifications
blank. A 54-file, hash-checked namespace qualification restored readable colors;
this was visually verified in Lume and survived guest restart. The fix is now
part of desktop provisioning. Pending upstream migrations remain visible; they
were not marked complete or silently run against the pinned installation.

A subsequent empty-disk run exposed a timing issue: SSH became ready before
Archboot's `Type=simple` signing-key initialization finished. Concurrent package
work failed with unknown-trust errors before disk partitioning. Failed checkpoints
were preserved. The base stage now waits for successful keyring completion before
any package/disk mutation, retaining signature enforcement. A new empty-disk run
with that guard passed base installation; full desktop/hardening/driver and Docker
acceptance are still in progress. Do not count the repaired palette run as the
complete no-workaround pass.

Local strict coverage: **377 tests passed, zero skips** with Hermes available.
Hermes package validation also passed before the final operator-only additions.
Remote viewer readiness now has a separate check-only forced-command endpoint;
its live cross-host acceptance is pending.

### Successful no-repair run and new Docker installation

A new empty-disk guest completed base installation, desktop installation,
hardening, first graphical boot, explicit production input-module build/load,
and permission/readiness checks without manual guest repairs. The installer
included keyring waiting, user-unit dependencies, scale 1 and the palette patch
from the start. All 21 module tests passed. Ten-second samples recorded a maximum
9.55 GiB allocated disk (64 GiB sparse capacity). This is sampled disk allocation,
not an exact peak or a total Mac storage minimum.

A fresh Docker agent installed `plugin/` from GitHub at immutable commit
`9db05e514ea7de7d9e40cd137815b724231a8209` through `hermes plugins install`, with
explicit dependency consent and enablement. A distinct viewer UID/private home
and runtime key were used. The initial Docker harness omitted the documented
0660 database initialization; the first model run refused before any app action.
Both runtimes were stopped, that documented step was completed, and the lock plus
SQLite transaction probe passed as both users without truncating state. This was
a harness omission, not an undocumented guest repair. The isolated test profile
also explicitly enabled single-query approvals for the authorized desktop tasks.

Real Hermes then launched Chromium and stopped at its first-run terms prompt.
After the user approved those terms, the operator accepted them through the
protected viewer and canceled optional keyring creation without setting an empty
password. Hermes subsequently navigated to Google using foreground input. An
independent guest probe confirmed native Wayland Chromium, live title
`Google - Chromium`, and the persisted `https://www.google.com/` history row titled
`Google`. The live history database used an exclusive lock, so verification read
an in-memory copy and required SQLite integrity checking before querying.

Authenticated Hermes setup calls passed remote preflight, firewall and Linux
permission checks. A separate check-only viewer SSH key passed remote VNC probing
and rejected an arbitrary shell command. The first preflight correctly refused
insufficient free space; removal of stopped disposable test VMs restored headroom
and the same read-only check passed. No failed checkpoint was erased to retry a
destructive stage. Final authenticated screenshot/retirement and editor acceptance
are still being completed.

The fresh Docker model's GTK task also passed. It launched Mousepad, used targeted
accessibility text, opened Save As, and used a fresh foreground pixel capture when
the Save button lacked an AXPress action. Independent guest checks found exactly
59 bytes (`OwnMachine clean acceptance: Hermes controls this desktop.` plus one
newline), SHA-256 `2e2dbc196577ae2349ba26fc6ccce40e838ad44d93e763567dc787561357a12b`,
and a native Wayland Mousepad title naming the saved file without an asterisk.
No operator wrote the document. Scale-1 first-run/browser/editor dialogs were
fully visible. The model runs used only desktop tooling, with terminal/file/code
execution toolsets disabled in the isolated test profile.

## Final clean-run verification

The installed Docker plugin was upgraded through Hermes to
`0a4c2f9c240fb21064d9b266cefc13b63015adc6`. Authenticated setup completed
preflight, firewall, permissions, read-only viewer-check, progress import and final
verification. Final verification captured a 1456x922 PNG through computer_use;
SHA-256 `512d4577439b10851420a3686a092561147cdbc243dd0920c3faf10b147e66db`.
Automatic retirement removed the actual temporary setup authorization, confirmed
that key was rejected and reverified runtime access. Reminder cleanup was not
pending. Private desktop captures and runtime credentials are not repository artifacts.

Browser Restart VM reconnected successfully and retained paused control. After
additional resolution/restart measurements, Hermes reopened the saved document
through Mousepad's UI without editing it. Independent SSH inspection confirmed
the native Wayland title, 59 bytes and the same SHA-256 recorded above. The VM
was returned to its configurable 1900x1200 default (Hyprland reports 1896x1200),
agent control was paused and the isolated model-test approval override was reset
to deny. This tests guest restart, not a new physical-host reboot.

| Final clean guest measurement | Result |
|---|---|
| Sampled installation disk maximum, 41 ten-second samples | 9.55 GiB allocated; 64 GiB sparse capacity |
| Post-test quiescent desktop with saved editor open | 1,100 MiB used / 7,921 MiB; no swap |
| Five-second guest CPU busy sample | 0.90% |
| 1920x1200 capture, five Docker→SSH→MCP calls | 109, 95, 105, 94, 99 ms; median 99 ms |
| 1456x920 capture, five calls | 71, 68, 64, 63, 60 ms; median 64 ms |

These are small observational samples, not an exact transient peak, model latency
or streaming FPS benchmark. Total host space includes installer/build inputs and
headroom beyond the guest disk. Experimental onboarding defaults to a 32 GiB
free-space floor; explicit lower overrides do not certify a 16 GiB installation.
Four vCPUs and 8 GiB guest RAM were used. Resolved rolling packages were Hyprland
0.57.2-1, Chromium 156.0.8078.79-1, Mousepad 0.7.0-1, Qt 6.12.0-4 and Quickshell
0.3.2-1. Future repository updates can change these independently of pinned source.

Reissuing the original creation parameters returned the verified checkpoint without
recreating the disk; a changed CPU request refused with
`configuration_changed_inspect_checkpoint`. The terminal wizard now explicitly
offers macOS and experimental Omarchy and explains the foreground input opt-in.
The evaluator quickstart documents boot, keys, firewall, viewer-owner and shared
control-directory setup in order. Future catalog disclosures are prepared separately
without altering the already released catalog pin.

**Scope:** provisioning itself ran through operator scripts; the new Docker Hermes
installation drove the authenticated final setup stages and three real-model tasks.
No manual guest repair was required in this final run. Operator ISO/boot handoffs,
Chromium consent, the exact-ABI module and documented shared-file permissions
remain requirements, not hidden automation. Earlier failures above are retained
as historical evidence and are superseded only by the specific successful repeat.

Final local strict suite: **381 passed, zero skips** with Hermes available.

Distribution validation at `0e97e15f0b30cff258bbde62a585300ee6e76637` passed: clean-commit source/plugin bundles, SHA-256 inventories, plugin-only package boundaries and Hermes validation of the extracted plugin. Source validation passed too. Hermes reports the documented in-process-only requirement for callback/CLI integration; it is not suppressed. Bundles remain local and unpublished. Subsequent evidence-only commits are checked again by CI.
