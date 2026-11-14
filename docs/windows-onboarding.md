# Windows onboarding — development branch

Windows is under qualification in PR #28. Saved plans, authenticated execution
and progress import now include a fresh provisioning implementation, described
below. Clean-install acceptance is still pending. Do not mark stages complete
manually or run a macOS installer for Windows.

## Start in Hermes

Use a dedicated Hermes profile. Install the reviewed OwnMachine development commit
and explicitly configure `plugins.isolation in_process`. For development docs, set
OwnMachine's `setup_guide_ref` to that reviewed immutable commit; released versions
use versioned documentation. No model credentials or unrelated authentication files
need to be copied into the plugin.

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
[production plan](windows-production-plan.md#current-administrator-workflow).
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

Live qualification of the new automatic setup-key retirement remains pending.
Do not leave temporary access installed after testing; an implementation is not
acceptance evidence. Earlier manual test-key revocation is recorded separately.

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

Provision starts only the configured guest. Windows may require a boot-media
keypress in the private viewer. A still-installing response is not success:
fetch progress, refresh preflight and repeat provision to check bootstrap; it
will not recreate a running guest or its disk. Build refuses an uncertain partial
artifact directory rather than erasing it.

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
