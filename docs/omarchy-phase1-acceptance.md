# Omarchy Phase 1 acceptance

Date: 2026-11-12. Status: Phase 1 started; guest installation/control acceptance pending. Not a Linux support claim.

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

Linux Lume configuration automatically attaches Rosetta when available, enables host clipboard sharing, and configures host microphone/audio. Merely omitting `--shared-dir` does not disable these. The isolated experimental build removes those devices and rejects directory shares. This is an experiment prerequisite, not a change to the released Lume build. The patch is included below for reproducibility. Default patched VNC-password and native-clipboard patches remain applied.

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
| Installed desktop and reboot | Pending |
| MCP status/screenshot | Pending |
| GTK accessibility bus/tree | Pending |
| Foreground click/type and Chromium | Pending |
| Native Wayland / optional seat plugin | Not attempted; baseline must pass first |
| Capture timings, installed disk use | Pending |
| Full OwnMachine/Hermes model acceptance | Later phase |

## Initial live results

The isolated build compiled successfully (79.66 seconds) and passed `codesign --verify --deep --strict`. Created a separate Linux guest with 8 vCPUs, 8 GiB RAM, a 64 GiB sparse disk, and 1920x1200 display. This experiment uses the interactive host account for the native console, not the dedicated production host account; dedicated-account/relay acceptance remains untested for Linux.

Booted the verified ISO using `--vnc disabled --display native`: Lume reports `vncUrl: null`, and `lsof` found no TCP listener for the VM process. No Rosetta, host filesystem, clipboard or audio device is configured by the experimental Linux build. Native viewer toolbar controls still appear; they were not used. Removing misleading controls and checking runtime share APIs remain production integration work.

Observed Archboot 7.2.2-2-aarch64-ARCH, configured English locale, DHCP/NAT and Arch Linux ARM package mirror, declined the offered live kernel upgrade, and reached the root console. `uname -m` returned `aarch64`. Downloaded the pinned base installer and verified SHA-256 inside the guest against the independently reviewed host copy.

Native text injection converted the colon in `https://` to a shell separator on the first command. Retried successfully with `curl --proto-default https` and a scheme-less hostname. This is native console bootstrap input, not evidence of CuaDriver or MCP input reliability. Record this in onboarding polish; do not recommend raw pasted commands without observing their result.

The owner approved temporary key-only SSH administration and CuaDriver desktop control inside this guest. Base installation and driver execution are still in progress; approval is not test evidence.

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

Virtual disk capacity is not a measured physical free-space requirement. The installed disk footprint and timing gates remain pending. Before recommending this path, complete every Phase 1 control/reboot check in [the plan](omarchy-plan.md).

## Experimental isolation patch

Apply after the repository's two existing Lume patches to the pinned upstream source. It deliberately changes only Linux VM configuration, does not grant host permissions, and is not installed by released scripts.

```diff
```
