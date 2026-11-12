# Experimental Linux development

Omarchy is an experimental ARM64 guest on an Apple Silicon Mac. macOS remains
the released installation path. All Linux work is tracked in PR #15 and the
[Omarchy plan](omarchy-plan.md); the experimental setup planner accepts `--guest-profile omarchy`; macOS is the default.

## Isolated host build

Set operator-owned absolute app/build paths and build with
`OWNMACHINE_LINUX_GUESTS=1 bash scripts/build-native-lume.sh`. The optional
`OWNMACHINE_NATIVE_APP` and `OWNMACHINE_NATIVE_BUILD_ROOT` variables select those
paths. Existing apps/build trees are preserved for inspection. This build has a
distinct `org.ownmachine.lume.linux` identity, preventing collision with the
production app's application-firewall registration.

The Linux patch removes host audio, microphone, clipboard, automatic Rosetta and
folder devices. It also omits Lume's automatic VNC configuration folder and its
credential file. Explicit shared directories are refused. No Linux clipboard
bridge is promised. The original macOS build remains the default.

Before enabling VNC, run the documented administrator firewall installer with the
chosen fixed port and this exact app path. Require the root-owned readiness file
and application block; a successful shell invocation alone is not evidence.
The ALTQ warning is harmless, but `Firewall verification failed` is not.

## Provisioning building blocks

`scripts/provision-linux-vm.py --help` exposes an explicit `--profile omarchy`
creation/boot path. Supply a signed-manifest-verified ARM64 Archboot ISO and its
SHA-256, private storage/checkpoint directories, and the verified Linux app.
CPU, RAM, sparse disk size, free-space floor, display and VM name are configurable.
Without `--apply` the command only previews. Creation records a checkpoint;
repeating the same verified creation validates the existing guest without
recreating it. Changed inputs, existing unowned guests and interrupted creation
require inspection. The boot stage opens a native console with VNC disabled.

The authenticated setup endpoint routes `build` and `provision` through
`scripts/setup-linux.py`, then `linux-base` and `linux-desktop` through
`scripts/install-linux-desktop.py`. Supply the verified ISO and SHA-256 in the
operator-owned endpoint configuration. The service configuration must match the
plan's profile, VM and storage directory. It also supplies `guest_ssh_alias` and
`guest_user`; `display_scale` accepts 1 (default) or 2. The endpoint never accepts
arbitrary installer URLs or unverified script inputs.

There are still explicit handoffs: boot the live ISO with VNC disabled, pair a
key-only guest SSH identity and independently confirm its host-key fingerprint
from the native console, then shut down and boot the installed disk without the
ISO after the base stage. Preserve that host key across the handoff. The base
stage requires an Apple-virtualized Archboot live root and an empty `/dev/vda`;
it refuses partitions, existing filesystem signatures or a mounted `/mnt`.
A verified checkpoint resumes without reinstalling. A running, failed or changed
checkpoint requires inspection; never delete it just to force a retry.

The live Archboot SSH service may use a different port. Explicit bootstrap must
stop that listener and use a reviewed key-only configuration; do not expose a
password-based live console. Native modifier injection remains unreliable in
this experimental viewer, so inspect entered commands before execution. This
handoff is not yet a certified unattended installation.

After the installed desktop boots, the shared setup-service stages route
hardening, driver and readiness checks to Linux implementations. Guest scripts
must never be run directly on the Mac host. A Linux readiness result means a
Wayland session, accessibility bus and standard-mode driver are ready; it does
not represent macOS TCC consent. The viewer and diagnostic CLIs accept
`--guest-profile omarchy` and keep their existing configurable SSH/control paths.

Inside the graphical Linux guest, as its desktop user,
`scripts/linux-guest.py install` verifies the pinned ARM64 CuaDriver archive and
installs a graphical-session user service. An operator can provide an explicit
version/checksum and local artifact. The installer preserves existing files for
inspection. It never enables linger. `status` checks the graphical session,
AT-SPI bus, daemon and standard authorization mode; it does not invent macOS
permission grants. Restarting the guest must restore readiness after graphical
login before using MCP.

After pairing and independently confirming a key-only guest SSH connection,
run `scripts/secure-linux-guest.py` **inside the guest** as root. Preview first.
Choose the desktop user and the host source address observed on that connection.
For `--apply`, provide a private guest-side password transfer file and retain its
recovery copy securely on the host. The script consumes the transfer file,
disables password/root SSH and forwarding, installs a dedicated inbound firewall,
removes the known unattended passwordless-sudo rule, disables Docker/CUPS/Bluetooth,
and grants only exact passwordless shutdown. Unknown sudo policy is refused.
The recovery password is still needed for later guest administration.

## Runtime and control

The host relay accepts `guest_os: linux`, `guest_profile: omarchy`, the custom
`storage_dir` and existing configurable VM/SSH/VNC fields. For side-by-side testing,
pin an absolute `--config` in each restricted SSH forced command using
`scripts/render-host-keys.py --config ...`. Explicit configs have separate private
VNC passwords, logs and lifecycle locks. Do not point two independently controlled
relays at the same VM. Agent and viewer keys remain separate roles.

Set the Hermes plugin's `guest_profile` to `omarchy` for foreground-default input.
Background input is refused in this experimental profile. The human-control
lease still gates all writes. Targeted GTK accessibility works without the
optional Hyprland plugin; compositor-mediated targeted pointer input may require
that plugin and must report refusal when unavailable. The plugin's 21 unit tests
and bounded foreground smoke do not certify independent background seats.

Keep the optional module disabled unless explicitly testing it. Build only
against matching Hyprland headers/compiler ABI, record its source revision and
ABI string, and repeat acceptance after compositor upgrades. Do not hot-replace a
loaded module. See the evidence record for exact tested revisions and limits.
