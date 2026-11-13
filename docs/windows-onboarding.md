# Windows onboarding — development branch

Windows is under qualification in PR #28. This path currently supports saved
plans, Linux preflight, selected existing-runtime checks and progress import.
**It is not yet a clean Windows installer.** Build/provision/hardening/driver and
final viewer verification remain blocked while their integration is finished.
Do not mark those stages complete manually or run a macOS installer for Windows.

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
They adopt a reviewed guest; they do not yet provision a fresh guest automatically.

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

Final fresh-install acceptance and automatic setup-key retirement are still pending.
Do not leave a temporary test key installed after testing. The acceptance report
records manual test-key revocation separately from the unfinished automatic flow.
