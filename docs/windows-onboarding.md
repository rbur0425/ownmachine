# Windows onboarding — development branch

Windows is under qualification in PR #28. Saved plans, authenticated execution
and progress import now include a fresh provisioning implementation, described
below. One repair-free guest installation has passed; broader release qualification
is still pending. Do not mark stages complete
manually or run a macOS installer for Windows.

## Start in Hermes

Use a dedicated Hermes profile. Install the reviewed OwnMachine development commit
and explicitly configure `plugins.isolation in_process`. For development docs, set
OwnMachine's `setup_guide_ref` to that reviewed immutable commit; released versions
use versioned documentation. No model credentials or unrelated authentication files
need to be copied into the plugin.

For qualification, use an isolated Hermes installation/home containing only the
reviewed plugin. On the tested Hermes build, a live process could reuse an older
OwnMachine provider loaded from another profile even after the target profile's
plugin was updated. A named profile alone did not isolate that module cache.
OwnMachine input results now include `meta.input_route` to identify the selected
driver operation; explicit Windows foreground shortcuts should use `press_key`.
If an updated installation behaves like an old one, stop and check installation
isolation before retrying input. Do not patch Hermes core or clear a pending gate
to work around this.

For last-window closure, use a freshly captured `Close` or `Close Tab` button
with an advertised invoke action and explicit foreground delivery. OwnMachine
reconciles the tested driver's exact post-click focus warning only when unfiltered
window enumeration and an exact-HWND lookup both confirm the last target window
is gone. It returns `window_closed_verified` and invalidates the old capture.
Rediscover windows before further input. Other labels, shortcuts, pixel clicks,
ambiguous results or failed verification retain the operator-review gate; inspect
the viewer before acknowledging those results, and never repeat an uncertain close.
See the [supervised save/reopen evidence](windows-kvm-acceptance.md#foreground-save-and-reopen-supervised-acceptance-passed).

Run `hermes ownmachine setup` and choose `windows`, or save an explicit plan:

```sh
hermes ownmachine setup --guest-profile windows --target remote \
  --host-alias YOUR_AGENT_SSH_ALIAS --vm-name YOUR_VM_NAME \
  --storage-dir /YOUR/HOST/STORAGE --control-dir /YOUR/HERMES/CONTROL \
  --cpu 4 --memory-gb 8 --disk-gb 96 --save
hermes ownmachine setup --next
```

Names and paths are examples to replace. Storage is on the Linux VM host; the
control directory is shared only by the intended Hermes/viewer identities. Local
means the machine running Hermes, not the browser. Windows requires an x86-64
Linux/KVM host; macOS and Omarchy retain their Apple Silicon/Lume paths.

## Host preparation and the administrator handoff

The host needs hardware virtualization, adequate storage, QEMU/libvirt, UEFI Secure
Boot firmware, software TPM and nftables. Supply verified Windows installation
media with an appropriate license. The current acceptance uses Enterprise
evaluation; it does not certify Pro or Windows ARM. Neither a password nor a
product key belongs in chat.

An administrator must establish dedicated runtime accounts, a private per-VM
network and console, object-scoped libvirt policy and the persistent firewall.
Runtime credentials must not provide broad libvirt or sudo access. The production
adoption scripts and their limits are documented in the
[production plan](windows-production-plan.md#existing-domain-administrator-workflow).
Those adoption scripts remain available for reviewed guests. The separate fresh
registration handoff below creates a new, stopped domain after artifact preparation.

## Pair and run the reviewed setup endpoint

Use a separate temporary setup SSH key and independently verify the host key.
Keep the setup account non-root. Install the reviewed source and private,
operator-owned plan/services/endpoint files on that host. The endpoint binds the
source fingerprint, plan digest, VM and allowed stages; Hermes imports only its
SSH-authenticated responses. Do not expose a general shell through the setup key.

For the current preflight path, the services file selects `vm_name`, `storage_dir`,
`runtime_config`, `agent_alias`, `viewer_alias` and `ssh_config`. The plan and
services VM/storage must agree. Preflight can run before runtime installation;
later checks require the root-pinned runtime configuration. Allow only reviewed
implemented stages in `allowed_steps`. Use `setup-endpoint.py --fingerprint` and
`--render-key` to produce the source pin and exact forced-command entry.

In the active Hermes profile, configure OwnMachine's `setup_host_alias`,
`setup_ssh_config` and `setup_source_sha256`, then run:

```sh
hermes ownmachine setup --run preflight
hermes ownmachine setup --run progress
hermes ownmachine setup --next
```

Progress survives reconnects. If an operation is uncertain, inspect its checkpoint
and fetch progress rather than replaying it. `setup --later` offers reminder
choices; reminders require explicit consent and are not silently scheduled.

## Existing runtime and manual desktop sign-in

Configure the plugin's `host_alias`, `vm_name`, `control_dir` and
`guest_profile: windows`. Explicitly select `computer_use.backend: ownmachine` and
`computer_use.permission_mode: standard` in the same Hermes profile. The separate
viewer uses its own key plus `--guest-profile windows --console-transport
private-unix`; its access token stays outside shared control state.

Run `hermes ownmachine doctor`. Sign into the Windows standard desktop account
when requested. The driver must run in that user's interactive session with a
Limited task, never as administrator or in Session 0. Windows has no macOS
Accessibility/Screen Recording prompts. Permanent automatic sign-in is off in the
tested baseline.

Use the viewer to reserve human control and return it to the agent. Agent input
stays blocked while paused or reserved; returning control requires a fresh capture.
After a guest restart, sign in again before expecting driver readiness.

Automatic guest and host setup-key retirement passed live verification after a
host-side media-check correction. A pristine run with all fixes from the beginning
is still being qualified; see the acceptance report. Do not leave temporary access
installed after testing or mark uncertain retirement complete manually.

## Fresh-install implementation under test

PR #28 now contains a fresh provisioning path. **Its clean-install acceptance is
still in progress; this is not a released Windows support claim.** The earlier
adoption evidence does not qualify this path.

The operator services JSON has a `provision` object in addition to the six
connection fields above. Keep this file private on the host. Configure:

- New `vm_uuid`, `network_uuid`, `bridge`, private IPv4 `subnet`, `guest_ip` and
  `dns_server`; the dedicated network must not overlap existing libvirt networks.
- `windows_iso`, its independently verified `windows_iso_sha256`, and `driver_zip`
  matching the pinned driver digest. Set `accept_evaluation_terms: true` only
  after the operator accepts the evaluation terms. This template selects the
  first image in the reviewed Enterprise evaluation media, not arbitrary ISOs.
- Separate `operator_user`, `agent_user`, `viewer_user`, `qemu_user` and
  `console_group`; new runtime identities must not already exist. Configure a
  new private `console_socket` directory and root-owned `runtime_prefix`.
  Keep the console outside libvirt's managed QEMU state directory (commonly
  `/var/lib/libvirt/qemu`); libvirt can treat sockets there as generated paths
  and rewrite them. Registration verifies the normalized socket definition.
- `host_address`, optional `host_ssh_port` (22), pinned `host_known_hosts`, and
  optional `ssh_service` (`ssh`). No host key is accepted automatically.
- Separate `guest_user` and `guest_setup_user`, plus `guest_install_root`.
- `viewer_python` ending in `bin/python`, `viewer_control_dir`, `access_dir` and
  `viewer_port` (0 selects an available port). Build creates a missing viewer
  virtual environment and installs its pinned dependency. The viewer owner needs
  a working systemd user manager; enable lingering explicitly if it must outlive
  that user's login.

`viewer_control_dir` is the **host-side** shared control path; the saved plan's
`control_dir` is the **Hermes-side** path to that same directory. They can differ
when Hermes runs in Docker. The viewer's `access_dir` and SSH keys must remain
outside that shared directory and outside the container's mounts. Arrange the
intended identities' ownership before setup; never use world-writable state.

All paths must be absolute. The fresh storage directory must be empty. The
configured `runtime_config` is `runtime_prefix/VM_UUID_WITHOUT_HYPHENS.json`.
Configure aliases in the services file separately for agent and viewer. Source,
plan, services and public setup-key files remain outside shared control state.

Run the stages from the configured Hermes profile:

```sh
hermes ownmachine setup --run preflight
hermes ownmachine setup --run build --apply
```

Build prepares private keys, unattended media, domain templates and a receipt; it
neither defines nor starts a VM. The administrator then reviews the exact files
and runs on the Linux host:

```sh
sudo python3 REVIEWED_SOURCE/scripts/register-windows-host.py \
  --services-file PRIVATE_SERVICES_JSON --plan-file PRIVATE_PLAN_JSON
```

This first-install handoff refuses existing identities, networks, domains and
storage disks. It registers a stopped guest, installs the persistent per-VM
security policy and restricted runtime SSH keys, and reloads SSH. It does not
restart libvirt, Docker, the host or existing guests. Libvirt's polkit access
control must already be configured. An interrupted administrator installation
requires inspection, not blind replay.

Pair the generated **agent** key with Hermes using normal OpenSSH administration;
keep the viewer key with the viewer owner. Do not paste private keys into chat.
Set runtime `host_alias`, `vm_name`, `control_dir`, `guest_profile: windows`,
`computer_use.backend: ownmachine` and `computer_use.permission_mode: standard`.
Then continue:

```sh
hermes ownmachine setup --run firewall
hermes ownmachine setup --run relay --apply
hermes ownmachine setup --run keys --apply
hermes ownmachine setup --run viewer --apply
hermes ownmachine setup --run preflight
hermes ownmachine setup --run provision --apply
```

Provision starts only the configured guest. Open the private viewer, reserve human
control, click inside the desktop, and press a key when Windows asks to boot from
CD/DVD. If the prompt expires, enter the firmware boot menu and select the
Windows installation ISO (not the smaller bootstrap ISO), then respond to its
keypress prompt. Do not press a key at later restarts: let the installed disk boot.
This console step is currently manual; creation is not fully unattended.

A still-installing response is not success:
fetch progress, refresh preflight and repeat provision to check bootstrap; it
will not recreate a running guest or its disk. Build refuses an uncertain partial
artifact directory rather than erasing it. If the desktop appears but provisioning
never completes, inspect `bootstrap-status.json` under the configured guest
installation root through the viewer. A `failed` result requires diagnosis; do not
mark the stage complete or start the driver manually. Keep bootstrap media mounted
until provisioning confirms success; the hardening stage ejects it.

```sh
hermes ownmachine setup --run harden --apply
hermes ownmachine setup --run driver --apply
hermes ownmachine setup --run permissions
hermes ownmachine setup --run verify
hermes ownmachine setup --run verify --apply
```

Hardening requires completed bootstrap, ejects installation media, removes cached
answer files and one-time sign-in, and enables only the limited interactive driver
task. MCP refuses access before hardening. Final verification requires the private
console and a native computer-use screenshot. The final `--apply` disables the
guest setup account, proves its key is rejected, removes temporary seed artifacts,
then removes the exact host setup authorization. Hermes independently verifies
host-key rejection and continuing runtime health. Any uncertain retirement stops
for inspection. Permanent guest automatic sign-in remains disabled; after future
cold starts, sign in through the private viewer when doctor requests it.


The Windows viewer preserves the server's normal RGB colors by default. Set the
optional boolean `provision.viewer_swap_red_blue` only for a console server that
actually needs that compatibility workaround; do not enable it for every Windows
VM. Its default is `false`. The private-console transport and human-input gate
are unchanged by this display-only setting.

## Idle display, driver recovery and clock policy

Fresh Windows provisioning accepts `display_idle_minutes` and
`sleep_idle_minutes` in the provision configuration (integers 0–1440; default 0,
meaning never). This keeps the VM available while idle; it does not disable
Windows locking or sign-in. `time_zone` is a Windows time-zone ID (default `UTC`,
for example `Eastern Standard Time`). Windows validates that ID during setup.
The virtual hardware clock uses UTC, paired with Windows `RealTimeIsUniversal`.
Setup now starts Windows Time automatically and performs a blocking resync before
it reports bootstrap complete. `time_servers` is an optional list of 1–5 DNS names
or IPv4 addresses (default `['time.windows.com']`); use reachable, trusted time
servers appropriate to your network. The guest needs DNS and outbound UDP 123.
No administrator password, provider credential or host clock is used to set time.
The UTC RTC policy still applies on subsequent boots. New first-session behavior
needs the clean-install acceptance below; earlier evidence only qualified time
after a cold start. Never bypass certificate checks for an incorrect clock.

These defaults apply to newly provisioned guests. Existing guests are not silently
modified. A host administrator must coordinate a stopped-domain clock change with
the guest administrator's registry/time-zone update; changing only one side can
shift the clock. Do not rerun bootstrap or restore retired setup keys to perform
an upgrade. The hidden driver launcher also requires updating the guest's
standard-user interactive scheduled task; it remains Limited, never SYSTEM.

Doctor checks connectivity and driver readiness, not whether the screen is awake
and unlocked. Check a fresh `computer_use` capture after login. A failed driver
read now closes its MCP stream; the next explicitly requested capture reconnects.
No input is replayed, and an uncertain prior input still requires operator review.
If guest SSH answers but the health helper fails, inspect that helper. If the
driver task stopped, restart the standard-user task; changing firewall rules or
SSH keys is not a remedy for a stopped desktop driver.

## Browser automation and acceptance tool access

Whole-string Chrome DevTools typing into the live canvas has been observed to
lose capitals. Explicit Shift/key-down/key-up sequences worked in the same
session. This is an automation-path limitation, not evidence that physical typing
is broken. For automated viewer tests, emit actual modifier/key events; for agent
text entry, use the permission-gated `computer_use` text action. Do not bypass the
human-control gate with injected guest commands.

A prompt saying “use only computer_use” is not a tool-access restriction. Run
acceptance in a dedicated Hermes profile/container with only the intended desktop
tools exposed. Exclude terminal, file-writing and skill-management tools and
inspect the recorded tool calls. One-shot prompting alone does not prevent skill
writes if `skill_manage` is available. Keep the normal Hermes profile untouched.


## First-install progress and recovery

The standard-user desktop opens a normal **OwnMachine setup progress** window.
It is read-only, is not always on top, and can be closed without stopping setup.
It distinguishes power setup, OpenSSH installation, SSH configuration, driver
configuration and time synchronization. Before OpenSSH is available, Hermes cannot
read the exact guest checkpoint; use this window in the private viewer instead.
To reopen it, run the installed `show-setup-progress.ps1` with Windows PowerShell
under the configured guest installation root. Do not run bootstrap again.

| What you see | What to do |
| --- | --- |
| Installing OpenSSH / SSH not yet reachable | Leave the guest running; Windows optional-feature installation can take several minutes. Handle any DVD/login prompt in the viewer. Do not rebuild the disk. |
| Synchronizing clock | Wait for the bounded operation; bootstrap is not complete yet. |
| Time synchronization needs attention | Check guest DNS, the configured time servers and outbound UDP 123. Run `hermes ownmachine setup --run provision --apply` again: this retries only synchronization. It does not reinstall Windows. |
| Bootstrap failed | Have the guest administrator inspect the configured Bootstrap task history and optional-feature installation errors. Preserve the VM/logs; do not blindly replay the task. |
| Bootstrap complete, driver unavailable | Run provision to import completion, then harden and driver stages. Sign into the standard guest account; inspect its Limited interactive Driver task if it stopped. |
| Verify cannot capture | Finish permissions/readiness checks, unlock the guest, return human reservation to agent control, and wait for other computer-use sessions to exit before repeating verify. |

After a handoff, run `hermes ownmachine setup --run progress`,
`hermes ownmachine setup --next` and `hermes ownmachine doctor`. Saved progress
contains only allowlisted reason codes; the plugin supplies the guidance locally.
It does not import guest error messages or secrets into chat. Doctor does not
create a VM, start bootstrap, change firewall rules, or grant desktop control.

For a reminder, run `hermes ownmachine remind later --mode next-visit`, review its
preview and confirm the displayed token. Nothing is scheduled without consent.
`next-visit` appears on a later OwnMachine command; use the separate tomorrow mode
only when its gateway/chat delivery prerequisites pass.

See [the clean-install checklist](windows-clean-install-checklist.md) for the
operator-run acceptance of these changes.

Windows Time behavior follows Microsoft's [workgroup service guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-client/active-directory/w32time-not-start-on-workgroup)
and [time service commands](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/Windows-Time-Service-Tools-and-Settings).
