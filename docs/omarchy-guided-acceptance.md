# Hermes-driven Omarchy installation acceptance

This follow-up tests the installed plugin, rather than calling provisioning
scripts directly. It supplements the [earlier acceptance record](omarchy-phase1-acceptance.md).
No release or expanded background-control claim follows from a successful install.

## Setup and trust boundary

An isolated Linux Docker agent installed `plugin/` through Hermes from GitHub at
`a0ddcee1bd7ca8664b209df36f9901dc2e564a3f`. A second Docker UID owns the viewer
key and private access state. Both users passed the documented shared lock and
SQLite transaction checks before runtime startup. No production Hermes instance
or Mac Studio was changed. The preceding laptop guest was stopped and preserved;
a separate empty guest disk was created for this test.

Operator prerequisites were the verified Linux-capable Lume build, administrator
firewall registration, a private seeded installer derived from the verified
Archboot ISO, independently pinned guest/host SSH identities, and separate
restricted setup/runtime keys. The helper generated new per-guest bootstrap keys;
the private ISO and keys are not repository artifacts. Installer boot disables
VNC; the graphical boot requires verified firewall readiness and a password file.

The test harness initially used a GitHub tree URL containing a slash in the branch
name, which Hermes parsed as part of the subdirectory. A standard `tree/main/plugin`
URL with an explicit immutable `--ref` installed the intended commit. A concurrent
harness config write caused dependency-publication conflict; Hermes refused and
left the plugin disabled. Reinstalling sequentially through the supported command
completed dependency consent and enablement. Neither issue was repaired inside
the guest or bypassed in Hermes.

## Verified sequence

- Hermes invoked remote `preflight`, verified the existing reviewed `build`, checked
  `firewall`, created the fresh guest with `provision` and ran `linux-boot-installer`.
- The new boot stage launched the private installer with VNC disabled and waited
  for the independently pinned root bootstrap SSH identity and Archboot root mount.
- Hermes started `linux-base` with an intentionally reduced eight-second client
  timeout. It reported uncertainty and instructed the operator to import progress
  instead of replaying the mutation. The endpoint retained its execution lock and
  continued on the Mac after SSH disconnect; the isolated Docker agent was restarted.
- Base installation finished successfully. The restarted installed Hermes plugin
  imported the authenticated `progress` result. Reissuing `linux-base --apply`
  returned its completed checkpoint rather than repartitioning the nonempty disk.
- Hermes invoked `linux-boot-system`: graceful shutdown of the installer, disk boot
  without the ISO and verification of the pinned non-root installed guest identity.
- Hermes completed `linux-desktop`, `relay`, `keys`, `harden`,
  `linux-start-desktop`, `driver`, `permissions` and `viewer-check`. No operator
  boot transition or guest repair was needed after initial trust preparation.
- Final `verify --apply` completed a 1456x922 computer_use screenshot,
  SHA-256 `f34fb8dc56c1a3bda1ccbd5948bcafe3e0ae6c5fbb0dc3b588580efc580658a3`,
  retired the actual setup key, proved it rejected and reverified runtime access.
  Reminder cleanup was not pending. Both actual Docker runtime roles rejected
  the opposite role's operation; the agent's permitted status call succeeded.
- A later installed plugin revision adds a disabled-by-default background-input
  experiment. Its desktop task results are recorded below separately from this
  completed installation acceptance.

## Interruption semantics

A lost client connection is not a cancellation command. The Mac endpoint ignores
hangup during an authorized operation, keeps its lock and records completion.
Reconnect with `setup --run progress`; do not automatically retry a timed-out
mutation. The endpoint still refuses concurrent mutation and uncertain checkpoints.
A host crash, power loss or failed disk write is **not** the successful client-loss
case: incomplete/uncertain checkpoints require inspection, not automatic reformat.

Boot stages likewise do not adopt arbitrary running guests or silently repeat a
transition. They require a matching receipt, verified predecessor, pinned identity
and a successful checkpoint. Repeating a verified transition only re-observes its
postcondition. Starting an old installer after the guest has advanced is refused.

## Background-input boundary

The pinned native module's source documentation admits separate-seat background
input only for targets that bind its agent seats. GTK 3/4 qualify for a bounded
experiment; Qt 6 keyboard input refuses, and Chromium/Electron refuse with
`client_not_bound`. XWayland is also outside that route. Semantic AT-SPI actions
are separate from isolated synthesized mouse/keyboard input.

OwnMachine retains Linux background-input refusal by default. An explicit
`experimental_linux_background_input: true` setting permits a requested background
action to reach the driver for per-target admission; it never requests a foreground
fallback, and `bring_to_front` conflicts are refused before dispatch. This
installation test alone does not establish background isolation. The bounded test below observes another foreground window and cursor position
and exercises human takeover. Event-level isolation, background pointer/drag
actions, cancellation under sustained input and broader app qualification remain
separate work. Broad macOS-like background browser control cannot be promised for
this compositor/application combination.

Source: [pinned input module documentation](https://github.com/trycua/cua/blob/ef1e84d6c880ab8aee7587c3d0057a288e764b69/libs/cua-driver/hyprland-plugin/README.md).


## Real-model task and bounded GTK background result

The isolated Docker agent upgraded through Hermes to
`27e44137d75cc4baaffdb2184f6fc6763e7e86ca` and explicitly enabled the background
experiment for this test. Qwen3.8-flash-next used desktop tools only; terminal,
file and code toolsets stayed disabled. The single-query approval override was
limited to this disposable profile and restored to `deny` afterward.

The first task attempt stopped on `foreground_unavailable (primary_target_busy):
foreground_grab` after opening Mousepad's File menu. The input gate required
inspection. The operator viewed the desktop, acknowledged the uncertainty and
dismissed that menu through the protected browser viewer; no text was edited or
saved by the operator. This is a failed desktop-task attempt, not an installer
repair. The second run used the already verified Ctrl+S shortcut rather than a
menu. Guidance now calls out this limitation; refusals do not authorize retries
or escalation around the control gate.

The successful model run saved the initial line through Mousepad's Save As UI,
raised Foot as a different foreground app without typing a command in it, and
captured Mousepad without raising it. It then issued raw `type` without an element
and a Ctrl+S action, both with `delivery_mode=background` and
`bring_to_front=false`. Both driver responses reported exact-target synthetic
input dispatched, effect unverifiable; subsequent captures and independent
checks established the result rather than trusting those dispatch responses.

Independent SSH verification found exactly these 92 bytes (each line ends in a
newline) in the saved file, with a native Wayland Mousepad title and no unsaved
asterisk:

```text
OwnMachine Hermes-guided installation passed.
Background input kept the other app in front.
```

SHA-256: `2a0cb95b78564511ed965eb0a72e80c557cdb310ce8cfca9bf09e41b1a318c8e`.
A separate observer sampled Hyprland's active window and cursor every 200 ms.
All 52 samples over the approximately 12-second interval surrounding background
typing and saving reported Foot foreground and the same cursor position.
The final independent probe agreed. This is sampled, bounded evidence, not
proof that no transient event occurred between samples or general isolation.

A third real-model run, with the viewer owner reserving the VM for human use,
attempted exactly one raw background `DO_NOT_DELIVER` input. It returned
`human_takeover`; the model made no retry or foreground fallback. Independent
verification found the unchanged file hash, saved editor title and foreground
terminal. Hermes's generic refusal hint still mentioned escalation, so the
provider now explicitly recommends operator intervention and explains that no
input was dispatched and control must be returned before a fresh capture. This
provider guidance uses public result fields; Hermes core is not patched.

The final workspace is paused with no pending action. The test profile's
background option was restored to false. This establishes experimental Mousepad
GTK keyboard/background-save support for the pinned configuration, not background
browser support, background pointer actions, every GTK application or background
operation concurrent with a human reservation.

## Local validation

The strict suite passed **388 tests with zero skips** with the Hermes contract
available. Plugin validation passed, including security and registration checks.
The documented in-process-only requirement remains visible. Final CI and bundle
results are recorded on PR #15; no release or catalog update is performed here.
