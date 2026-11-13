# Omarchy setup and Linux development

OwnMachine v1.0.0 supports the tested ARM64 Omarchy foreground desktop on an Apple Silicon Mac. See [final acceptance and boundaries](omarchy-final-acceptance.md). Background control remains experimental. macOS remains
the default installation path. Linux implementation is recorded in PR #15 and the
[Omarchy plan](omarchy-plan.md); the setup planner accepts `--guest-profile omarchy`; macOS is the default.

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
`scripts/setup-linux.py`, the three boot transitions through
`scripts/setup-linux-boot.py`, and `linux-base` and `linux-desktop` through
`scripts/install-linux-desktop.py`. Supply the verified ISO and SHA-256 in the
operator-owned endpoint configuration. The service configuration must match the
plan's profile, VM and storage directory. It also supplies `guest_ssh_alias` and
`guest_user`; `display_scale` accepts 1 (default) or 2. `desktop_theme` selects
a bundled pinned theme (default `catppuccin`). Fresh setup generates that theme
before login, disables animations and binds the terminal shortcut to installed
`foot`, avoiding the unavailable ARM64 `xdg-terminal-exec` dependency. The endpoint never accepts
arbitrary installer URLs or unverified script inputs.

After initial operator trust/key/firewall preparation, use the installed Hermes
command for each stage, with `--apply` for mutations:

```text
preflight → build → firewall → fresh preflight → provision
→ linux-boot-installer → linux-base → linux-boot-system → linux-desktop
→ relay → keys → harden → linux-start-desktop → driver → permissions
→ viewer-check → verify
```

The three boot stages use the configured VM/storage and preserve the pinned guest
host identity across live-to-disk boot. Installer and base boots have VNC disabled;
the hardened graphical boot uses the protected relay. The base stage requires an
Apple-virtualized Archboot live root and an empty `/dev/vda`; it refuses partitions,
filesystem signatures or a mounted `/mnt`. Completed checkpoints re-observe without
reinstalling. Failed, running or changed checkpoints require inspection.

For a disconnected client, reconnect and import `setup --run progress`. An already
authorized stage may still be running on the Mac; losing SSH is not cancellation.
Do not delete checkpoints or replay an uncertain operation. Once the remote stage
has completed, authenticated progress lets Hermes continue with the next stage.

Manual native-console boot remains an operator alternative. If using it instead
of the private seeded image, independently confirm the live SSH host key and stop
stock password listeners. Do not expose a password-based installer console or
rely on native-viewer modifier injection. The guided path still requires operator
trust preparation and administrator firewall approval; it does not grant those
permissions silently from chat.

### Private installer bootstrap

To avoid typing a key into the native console, the Mac operator can prepare a
private image with `scripts/prepare-linux-bootstrap.py`. Install `xorriso`,
`mtools` and `zstd` first (for example, `brew install xorriso mtools zstd`). Supply
the original ISO path, its independently verified signed-manifest SHA-256 with
`--iso-sha256`, and a new absolute `--state-dir`. Existing output directories are
refused, including interrupted builds; preserve them for inspection.

The script verifies the source hash before creating files, generates separate
guest-client and guest-host Ed25519 identities, and writes a private derived ISO
plus `bootstrap.json`. Use the derived image/hash for VM creation. The receipt
provides the identity file, known-hosts file and host-key alias for a pinned SSH
alias; use `IdentitiesOnly yes` and `StrictHostKeyChecking yes`. The live user is
`root`; after base installation, use the configured non-root desktop user with
the same pinned host identity. Resolve the current address from Lume each time.

The seed enables key-only SSH and DHCP, masks Archboot's stock SSH and web-terminal
services, and needs no host directory share or VNC listener. Base installation
preserves its host identity. The derived ISO contains a **private host key**:
keep it in its 0700 directory, never publish it, and remove it after the installed
disk has booted successfully and the installer is detached. Keep the client key
private for the configured guest SSH connection. Hardening subsequently removes
root/password SSH and unrestricted setup sudo. This guest identity is separate
from the temporary Mac setup-endpoint key retired by final setup acceptance.

The bootstrap utility does not itself create a VM, install the desktop or mark
authenticated onboarding complete. The subsequent [Hermes-driven installation
acceptance](omarchy-guided-acceptance.md) tests those stages separately; do not
count an image build alone as an installation pass.

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
Background input is refused by default; the separately opted-in bounded GTK
keyboard experiment is described below. The human-control
lease still gates all writes. Targeted GTK accessibility works without the
optional Hyprland plugin; compositor-mediated targeted pointer input may require
that plugin and must report refusal when unavailable. The plugin's 21 unit tests
and bounded foreground smoke do not certify independent background seats.

Keep the optional module disabled unless explicitly testing it. Build only
against matching Hyprland headers/compiler ABI, record its source revision and
ABI string, and repeat acceptance after compositor upgrades. Do not hot-replace a
loaded module. See the evidence record for exact tested revisions and limits.


### Targeted input acceptance requirement

The fresh Docker/Hermes run verified native Chromium discovery and capture, then
refused its first foreground action because the Hyprland input module was absent.
The refusal correctly left a durable review gate and no URL was typed. Therefore
`driver_ready` is capture/session readiness, not proof of targeted browser input.
Targeted compositor input requires the explicitly enabled, ABI-matched optional
module. GTK semantic accessibility is a separate path. Never silently downgrade
an exact-window action to untargeted desktop input to avoid this refusal.

First-run Chromium terms remain an explicit user decision. A new-keyring prompt
may be canceled for a test that stores no logins; setup does not create an empty
keyring or disable credential protection to suppress that dialog.


Linux status reports `foreground_input_ready` separately from `driver_ready`.
Capture and GTK accessibility readiness do not prove exact-window keyboard/mouse
support. Foreground input requires the explicit production Hyprland input module,
an exact compiled/runtime ABI match, enabled protocol-3 transport, and private
same-user sockets. Missing or unsafe transport reports false; the probe never
loads a module or changes compositor configuration. Recheck after every desktop
restart or compositor update. The explicit experimental module installation path is described below; it is not enabled by a status probe.

### First-login compatibility and explicit input installation

The desktop stage installs the pinned user services and their `fcitx5`/`bluez-tools`
dependencies before first login, adapting only Omarchy command paths to the ARM
installer's `/usr/local/bin`. It also validates all affected QML files against a
pinned hash manifest before qualifying the palette namespace. This fixes the
[Qt 6.12 Color collision](https://github.com/omacom/omarchy/issues/15069) without
hiding notifications, downgrading Qt, or marking setup steps complete artificially.
Changed upstream files stop the patch for review.

Set `guest_bootstrap_ssh_alias` to the pinned live root alias and
`guest_ssh_alias` to the installed desktop-user alias in the same operator service
configuration. Installer boot, base installation and the live shutdown use the
bootstrap alias; installed-system stages use the desktop alias. Both aliases must
pin the generated host identity; neither uses trust-on-first-use. Complete
hardening before the first graphical restart, then run the driver stage.

For experimental exact-window Chromium input, explicitly set
`"enable_experimental_input": true` **before** desktop installation. The desktop
stage installs build prerequisites; the driver stage fetches the pinned Cua
module source, builds with production input enabled and test-input/trace disabled,
and requires all 21 module tests to pass. It verifies compositor/header/compiler
compatibility, enables the module through a real configuration reload, and installs
a graphical-session user unit. Every subsequent login rechecks the compositor
binary, compiler, module hash and pinned revision before loading. An update that
changes this identity requires a reviewed rebuild; the helper does not silently
rebuild or hot-replace native code. The opt-in is omitted/disabled by default.

`linux-input-module.py build|enable --enable-experimental-input --apply` is the
underlying guest-only helper. Preview without `--apply` is read-only. A partial
build or conflicting configuration stops for inspection. Capture readiness and
foreground-input readiness remain separate. The default remains foreground;
the separately opted-in background keyboard experiment is described below.

### Viewer on a separate Docker host

When the viewer lives on another machine/account, set `viewer_probe_ssh_alias` in
the Mac's operator service configuration. Install `viewer-check-endpoint.py`
under the viewer owner and pin it as a forced command for a dedicated check-only
SSH key, with `restrict` and independently verified host keys. Its private JSON
configuration contains exactly `host_alias`, `vm_name`, `guest_profile`,
`control_dir`, and `access_dir`, all for that viewer. The command accepts only
`ownmachine-viewer-check status|probe --vm <configured-name>` and returns bounded
readiness metadata. It cannot start/stop a VM, inject input or return a token.
The setup account needs the check key, not the viewer's private runtime key or
access file. Keep the check key separate from agent, viewer and temporary setup
keys. Do not give a general remote shell to the setup endpoint.

Install the remote viewer under its actual owner first. `setup --run viewer-check`
checks it; `--apply` is refused for this remote path. Final verification probes its
protected VNC connection through the same fixed endpoint. The subsequent native
computer-use screenshot and setup-key retirement remain separate acceptance steps.

Archboot's `pacman-init.service` is `Type=simple`: SSH availability does not imply
its package-signing keyring is ready. The base stage waits for successful `exited`
state before package installation or recording a disk mutation. Failure refuses
provisioning; it never relaxes package-signature verification. Installer failures
retain mode-0600 output under the operator's VM setup directory for inspection.

For isolated side-by-side installations, `relay_path` and `relay_config` select
private operator-owned installation files. The default paths remain unchanged.
Use `runtime_ssh_config` for the setup verifier's two runtime-role aliases and
`viewer_probe_ssh_config` for its remote check-only alias when the operator's
normal SSH configuration offers other identities. These explicit `-F` files must
pin the intended identity/host key and disable agent forwarding; a successful
connection through a different unrestricted key does not prove role separation.

New Omarchy plans default to a 32 GiB free-space floor; an explicit expert override
may select 16–2000 GiB, matching the provisioner. The tested clean guest used a
24 GiB floor, a 64 GiB sparse disk and about 9.55 GiB peak allocated disk sampled
every ten seconds. Allow extra room for the original/private ISO, Lume build,
package cache and later applications. This is not a certified 16 GiB minimum.
macOS resource defaults and minimums are unchanged.


## Optional background keyboard experiment

Foreground remains the default. After the explicit native-module installation,
a dedicated Hermes profile may opt into per-target background admission:

```sh
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.experimental_linux_background_input true
```

Start a new Hermes session after changing this setting. Request `delivery_mode:
background` explicitly and leave `bring_to_front` false; omitted modes remain
foreground. The provider never changes a rejected background request into
foreground input. Disable the option with the same command ending in `false`.

Mousepad native Wayland typing and Ctrl+S passed a bounded real-model test with a
separate foreground terminal and sampled cursor/focus observation. Human
reservation still blocks agent writes, including background writes. This option
does not enable simultaneous human/agent ownership. Chromium/Electron do not bind
the module's agent seats; Qt keyboard and XWayland routes are not qualified.
Do not treat module readiness as universal background support. Read the
[full evidence and limitations](omarchy-guided-acceptance.md).

### Enforced hardening order

The desktop installer installs the root-owned SDDM startup gate before invoking
upstream installation. Complete the `harden` stage before `linux-start-desktop`
and `driver`. Restarting early leaves SDDM stopped; use the already paired SSH
setup connection to finish hardening, then retry the guided desktop start.
Do not delete the drop-in to work around a failed check.

The hardener publishes `/etc/ownmachine/hardened.json` only after verifying SSH,
firewall and sudo policy. This is public policy metadata, not a password.
Every managed SDDM start rechecks live policy; the guest driver requires the
trusted receipt for installation, readiness, daemon and MCP startup, and refuses
unrestricted passwordless sudo even if a receipt remains. The host also verifies
hardening before new or resumed driver stages. An administrator can deliberately
change these controls; they are not a sandbox against guest root or arbitrary
manual compositor/driver launches outside OwnMachine.

Existing experimental guests without the gate need reviewed operator repair or
a fresh guided installation. A completed old checkpoint is not permission to skip
the new checks. Source-bound onboarding checkpoints prevent replaying installation
with changed scripts. See [regression evidence](omarchy-security-acceptance.md).

## Maintenance and host-service isolation

Keep the tested package versions in the acceptance record. Before an intentional
update, pause agent control, save guest work and check the configured package
repositories and signing keys. Omarchy migrations may require packages outside the
base Arch Linux ARM repositories; an absent official Omarchy repository can stop a
migration with `target not found`. Use the upstream official ARM64 repository and
its pinned signing-key procedure, with signature checking required; do not substitute
unsigned packages, mark failed migrations complete, or suppress update notifications.
Record each failure, repair its actual prerequisite, and resume the upstream update.
Afterward verify no migrations remain, restart the guest, check hardening and driver
readiness, verify the Hyprland module ABI, and rerun the model/browser acceptance.
An update completing is not itself proof that desktop automation still works.

When multiple signed Lume copies collide in macOS application-firewall registration,
set `OWNMACHINE_LUME_BUNDLE_ID` to a distinct reverse-DNS identity when building into
a new app directory. Register that exact app with the administrator firewall
installer before selecting it in relay configuration. Never bypass the readiness
check; a failed registration must leave VM start/viewing refused.

See [host-service isolation and output redaction](../SECURITY.md#boundaries-and-limitations)
for optional configurable guest-to-host SSH blocking. This protects host SSH on the
selected guest bridge; it is separate from the mandatory VNC firewall.
