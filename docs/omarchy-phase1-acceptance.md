# Omarchy Phase 1 acceptance

Date: 2026-11-12. Status: Phase 1 compatibility spike in progress; installed ARM64 desktop, native Wayland capture and foreground GTK file creation verified. Targeted accessibility remains open; Chromium foreground navigation and typing pass. Not a Linux support claim.

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

## Repository validation

- Full suite with the established Hermes validation environment: **340 tests passed, zero skips**.
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
