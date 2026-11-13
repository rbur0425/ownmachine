# Hermes-driven setup over SSH

The operator terminal can now dispatch a reviewed setup stage from Hermes and
import its authenticated result into profile-local onboarding status. An explicitly
allowed chat sender can use the same `setup --run STAGE [--apply]` commands. Hermes
supervises the background task and posts progress only to the invoking conversation.
No privileged installer or viewer secret is included in the installed plugin.

## Bootstrap trust once

Use a **third, temporary setup key**, separate from both runtime keys. Generate
it as the operator with `scripts/pair-ssh.py --role setup`, independently confirming
the Mac host-key fingerprint as in the wizard quickstart. Keep it unavailable to
agent terminal tools; perform setup in an operator-only profile/session. Installing
the plugin alone does not grant setup authority. Remove the setup authorized_keys
entry and retire its key when setup is complete.

On the intended non-root Mac account, place reviewed full source at a permanent
path and prepare the approved plan and service configuration from the wizard
quickstart. These bootstrap files still require explicit operator transfer/review;
this increment does not automate first-account creation or trust establishment.
Use canonical absolute paths and mode 0600 for the endpoint config and plan.

```sh
python3 scripts/setup-endpoint.py --fingerprint
```

This fingerprints scripts, host code, plugin code, viewer code/assets and patches.
Review that source before trusting the result. A digest is a change detector,
not an independent signature or proof of a trustworthy download.

Create an operator-owned endpoint config outside the source tree:

```json
{
  "plan_file": "/absolute/private/plan.json",
  "services_file": "/absolute/private/services.json",
  "app": "/absolute/mac/OwnMachineLume.app",
  "build_dir": "/absolute/mac/build-cache",
  "allowed_steps": ["preflight", "build", "provision", "firewall", "relay", "keys", "harden", "driver", "permissions"],
  "source_sha256": "REVIEWED_SOURCE_SHA256"
}
```

Grant only the stages needed on that account. `viewer` and `verify` are also
supported where the operator-owned viewer configuration, dependencies and
verification aliases are available; they do not turn an agent account into a
viewer account. Cross-machine viewer orchestration remains an explicit deployment
choice, not automatic credential sharing. Optional `ipsw` and `preset` select the
existing macOS provisioner options. The configured plan's VM/storage must match
the service configuration.

Render a narrow authorization entry:

```sh
python3 scripts/setup-endpoint.py --config /absolute/private/endpoint.json \
  --render-key /absolute/path/to/setup.pub
```

Inspect and install that public entry using your existing operator access. Do not
replace unrelated authorized_keys entries or reuse an agent/viewer public key.
The entry uses `restrict` and a fixed forced command. It accepts only the literal
`ownmachine-setup-v1` request with a bounded JSON protocol, not shell commands,
request-supplied paths, forwarding, a PTY or arbitrary scripts. The existing agent
and viewer forced-command operation lists are unchanged. Root execution is refused.

## Configure the active Hermes profile

Set these non-secret settings through Hermes's normal plugin configuration:

```yaml
computer_use:
  backend: ownmachine
  permission_mode: standard
plugins:
  isolation: in_process
  enabled: [ownmachine]
  entries:
    ownmachine:
      settings:
        host_alias: example-agent-mac
        vm_name: ownmachine
        control_dir: /absolute/shared/control
        guest_profile: macos # use omarchy for the Omarchy plan
        experimental_linux_background_input: false
        setup_host_alias: example-setup-mac
        setup_source_sha256: REVIEWED_SOURCE_SHA256
        setup_timeout_seconds: 7500
        setup_ssh_config: /absolute/operator/ssh-config
```

The runtime fields must match the saved plan; local targets also need a restricted
agent SSH alias. Follow [runtime configuration](wizard-quickstart.md#configure-the-runtime-before-final-verification)
before final verification or any desktop task. Setup configuration alone does not
select the computer-use provider.

`setup_ssh_config` is optional; an empty value uses normal OpenSSH configuration.
The plugin passes it as `ssh -F`; it never reads SSH private keys itself. Use a
strictly pinned host key and a distinct alias from the agent runtime. Settings
and the saved plan belong to the active profile. Do not put passwords, private
keys or viewer tokens in setup settings or chat. Keep the dedicated runtime
profile's terminal restrictions in place after retiring setup access.

## Execute and resume

Save/review the wizard plan first. Its digest must match the approved Mac-side
plan. Execution cannot be combined with plan edits or `--connect`/`--save`.

```sh
hermes ownmachine setup --run preflight --json
hermes ownmachine setup --run build --apply --json
hermes ownmachine setup --run preflight --json
hermes ownmachine setup --run provision --apply --json
hermes ownmachine setup --run firewall --json
hermes ownmachine setup --run relay --apply --json
hermes ownmachine setup --run keys --apply --json
hermes ownmachine setup --run harden --apply --json
hermes ownmachine setup --run driver --apply --json
hermes ownmachine setup --run permissions --apply --json
hermes ownmachine setup --run permissions --json
hermes ownmachine setup --run progress --json
hermes ownmachine status --json
```

Build/provision require a successful actual-Mac preflight within five minutes.
The remote check observes hardware, Swift availability, selected-volume free
space, CPU count and memory against the saved resource plan. This does not yet
cover automatic port selection, every external-storage cache requirement or a
cloud-host qualification. After a long build, refresh preflight before creation.

The root firewall installer remains a human administrator handoff. The explicit
`harden --apply` stage now runs fresh-guest hardening, prepares key-only SSH and
installs the exact shutdown permission; see the prerequisites below. Driver setup
requires that prepared guest SSH path and a running selected VM. Permissions
`--apply` opens the guest guide; the human still approves macOS consent. Final
verify includes a native screenshot; apply also retires the temporary setup key.

`--apply` is required for mutating stages. Set a suitable bounded timeout (5–7500
seconds); the default is 120 seconds. A lost/timed-out connection is uncertain,
not a reason to replay. The endpoint records running/outcome state and locks
execution. Run `--run progress` after the previous process has finished; the
endpoint refuses concurrent work rather than queueing duplicate mutations.
Interrupted/uncertain mutations may require operator inspection.

## What authenticates progress

Every request carries a fresh nonce, source fingerprint, approved-plan digest,
VM and stage. The endpoint checks that identity before running a fixed reviewed
script and refuses reused request nonces. The response must match all those
fields and arrive on that same strict-host-key-checked SSH channel. Only bounded,
sanitized stage outcomes and timestamps are imported through Hermes's state API;
raw logs, credentials, paths and desktop contents are not imported. Copied JSON
files and unsolicited callbacks have no import path.

The endpoint retains up to 4096 request nonces, then requires operator retirement
of that setup session; it never silently evicts nonce replay protection. Progress
queries return prior observations, not fresh postcondition verification. Imported
state becomes stale when plan/source/SSH transport configuration changes. No
result marks the entire desktop accepted. Final verify includes a real
`computer_use` screenshot. Browser input and independently verified model-task
completion are separate acceptance checks.

The operator runners retain their liveness events. Terminal calls wait for a
bounded final response; supervised chat calls receive sanitized authenticated
endpoint heartbeats as described below. While a call is running, profile status records
`awaiting_remote_result`; on uncertainty it records `needs_inspection`.

## Stable documentation links

The setup guide URL derives `v<version>` from the installed plugin manifest. It
points to that release's community setup document, which links the matching
wizard quickstart once included in that release. For an unreleased reviewed
checkout, set `setup_guide_ref` to its full 40-character commit. Floating branches
such as `develop` are rejected. Repository README links are relative to the tree
being viewed, so release-tag pages stay tied to their release.

## Guided fresh-guest hardening

Add `harden` to the reviewed endpoint allowlist and set `guest_user` in the
service configuration if the unattended image uses a name other than `lume`.
The stage requires this version's successful provisioning receipt matching the
VM name and canonical custom storage path. It refuses existing credentials or
an already configured guest alias; do not adapt an existing personal desktop.
The guest must be stopped. An explicit `--run harden --apply` boots it with VNC
**disabled**, pins its first SSH host key in isolated guest known-hosts, installs
a unique key, rotates the factory password, disables SSH password/root login,
aligns autologin/keychain, configures the selected guest alias, and installs only
the exact guest shutdown sudo rule. The selected Mac account owns the private
recovery file; the Hermes plugin neither reads it nor requests it in chat.

Password-bearing operations travel over SSH stdin, not host command arguments.
Guest password utilities still receive their required arguments inside the guest;
this is not a claim to protect guest credentials from a compromised guest account.
Resume checks live effective sshd settings, pinned key access and shutdown
permission. An interrupted rotation requires inspection, never automatic replay.
This does not grant Accessibility or Screen Recording; those remain guest consent.
After hardening, restart the guest through the **viewer runtime identity** to
switch from VNC-disabled bootstrap to the firewall-checked, password-file VNC
session before viewing the permission guide. The agent key cannot perform this.

## Live chat progress and interruption

Configure exact `setup_allowed_senders` entries before invoking remote setup in
chat, including read-only steps. Missing identity fails closed. Chat execution
requires the explicitly selected dedicated `in_process` profile: Hermes message
handles cannot cross plugin-host IPC. Planning remains available in host mode.
This uses Hermes public `spawn_task` and `apost_message` APIs; older versions receive a
terminal fallback. A second active call in that plugin instance is refused.
Profile state and host execution locks remain authoritative across processes.

The SSH endpoint emits nonce/source/plan/VM/stage-bound heartbeats every five
seconds. They prove only that the endpoint is waiting for its child, not that the
child is healthy or any postcondition passed. The plugin validates sequence and
size bounds; a terminal authenticated receipt alone imports completion. Chat
updates use `setup_progress_interval_seconds` (default 30, range 5–300) and stop
after 20 interim updates, then send the final result. Raw logs and credentials
never appear. Messaging failure, unload or sender revocation cancels the local
SSH wait; the remote child may continue. Query `setup --run progress` once the
remote lock is free and inspect uncertain state; do not replay mutations.

These are updates for an explicit active call. Separately opted-in
[reminders](onboarding-reminders.md) can use the public Hermes scheduler. Final
`verify --apply` checks the screenshot, removes only the exact temporary setup
authorized key, proves rejection and retains runtime access. Configure `verify`
and `retire` in the reviewed allowlist and the private `setup_public_key_file`
as described in the [wizard quickstart](wizard-quickstart.md#finish-verification-and-remove-setup-access).
The operator may then remove its private setup key; never remove unrelated keys.
