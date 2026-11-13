# Wizard quickstart

For a first evaluation, start with the [evaluator quickstart](evaluator-quickstart.md),
including administrator handoffs and shared-control permission checks.
This is the guided onboarding path, not a claim of one-click setup.
Use reviewed full source or a checksum-verified release bundle on each operator
machine. The catalog-installed `plugin/` contains no privileged installers.
macOS is the default guest. OwnMachine v1.0.0 also offers ARM64
Omarchy; choose `--guest-profile omarchy` and follow the [Linux operator guide](linux-development.md).
Ubuntu and Windows are not available images.

**Start with the [manual prerequisite checklist](evaluator-quickstart.md#manual-prerequisites-before-hermes-can-provision).**
You can install the plugin and save a plan first, but Hermes cannot provision the
Mac until the operator has prepared trusted SSH setup access and matching source/
configuration. The wizard does not create the host account or grant administrator
privileges. Firewall approval and guest consent remain later human handoffs.
If blocked, use the [status-to-documentation and reminder steps](evaluator-quickstart.md#resume-without-guessing).

## Start in Hermes

Use a dedicated OwnMachine profile; replace `ownmachine` below with your chosen
profile name (create/install it using the evaluator guide first):

```sh
hermes --profile ownmachine config set plugins.isolation in_process
hermes --profile ownmachine ownmachine setup
```

Typical wizard conversation:

```text
Where will the desktop run? local / remote / existing: remote
Verified SSH alias (leave blank until configured): example-agent-mac
Absolute shared control directory: /absolute/shared/control
Absolute VM storage directory on the Mac: /absolute/mac/guest-storage
VM name [ownmachine]: ownmachine
... review resources and proposed steps ...
Save this non-secret plan? yes / no [no]: yes
```

Resource defaults appear in the preview; use setup flags to change them. `local` means the computer running
Hermes, not your browser. Chat has `/ownmachine setup`, `/ownmachine status` and
`/ownmachine doctor`; changes in chat require a locally configured exact sender
allowlist. The terminal wizard remains available without that chat grant.

```sh
hermes --profile ownmachine ownmachine setup --json > plan.json
hermes --profile ownmachine ownmachine status --json
```

Transfer/review the initial non-secret plan through your operator bootstrap channel.
Then configure [Hermes SSH stage dispatch and authenticated progress](setup-transport.md)
to run the stages from the operator terminal. Initial account/source/key trust
establishment is still explicit operator work. Do not
paste passwords, private keys or viewer links into chat.

## Prepare and create the Mac guest

Complete the dedicated non-admin account's first graphical login. Follow
[Mac execution](setup-execution.md) to inspect and explicitly apply `build` and
`provision`. Add `--events` to receive JSON start/liveness/finish events. These
are liveness signals, not download percentages or proof of success.

A successful creation leaves the guest stopped and does not expose verification
VNC. Run the explicit guided `harden --apply` stage through the [setup endpoint](setup-transport.md#guided-fresh-guest-hardening)
before the driver stage. It configures the fresh guest SSH alias and exact
shutdown rule; it refuses to overwrite existing credentials. Bring up the selected guest using the documented protected
runtime or no-VNC bootstrap path; do not launch an unmanaged VNC listener.

## Pair the two runtime identities

On the Mac console obtain `/etc/ssh/ssh_host_ed25519_key.pub` and its fingerprint:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
```

Transfer the **public** host key and independently confirm the displayed
fingerprint. An SSH scan alone is not confirmation. Run the following separately
as the actual Hermes runtime account and as the separate viewer runtime account,
substituting the role, alias and your confirmed fingerprint:

```sh
python3 scripts/pair-ssh.py --role agent --alias example-agent-mac \
  --host mac.example.invalid --user dedicated-account \
  --host-key /absolute/path/to/mac-host.pub --confirm-fingerprint SHA256:CONFIRMED
```

Review, then add `--apply`. Repeat under the viewer runtime account with
`--role viewer --alias example-viewer-mac`. The helper creates a unique private
key locally, pins the supplied host key, and installs a narrow SSH Include. It
refuses changed keys/configuration and never sends a private key to the Mac.
Copy only the two generated `.pub` files to the Mac. Account/container separation
is an operator responsibility; the helper cannot prove another machine's user
isolation. Both keys must belong to different runtime security contexts.

## Configure the service stages

Create an operator-owned JSON file outside the repository. Use only fields needed
by the stages on that machine; paths refer to that machine. This example combines
the Mac and viewer settings for illustration—split it when the viewer is remote:

```json
{
  "vm_name": "ownmachine",
  "storage_dir": "/absolute/mac/guest-storage",
  "lume_app": "/absolute/mac/OwnMachineLume.app",
  "vnc_port": 57279,
  "guest_ssh_alias": "example-guest",
  "python": "/absolute/mac/python3",
  "agent_public_key": "/absolute/mac/agent.pub",
  "viewer_public_key": "/absolute/mac/viewer.pub",
  "agent_host_alias": "example-agent-mac",
  "viewer_host_alias": "example-viewer-mac",
  "control_dir": "/absolute/shared/control",
  "access_dir": "/absolute/private/viewer-access",
  "viewer_python": "/absolute/viewer/venv/bin/python",
  "viewer_port": 0
}
```

Choose an available unprivileged VNC port and protect that exact port; the example
is not a reservation or default. A viewer port of 0 selects a free loopback port.
Keep its access directory outside shared control state. Install the pinned viewer
dependencies in its own Python environment before installing the service.

On the Mac:

```sh
python3 scripts/setup-services.py --config services.json --step preflight
sudo /bin/bash scripts/install-vnc-firewall.sh YOUR_VNC_PORT /absolute/mac/OwnMachineLume.app
python3 scripts/setup-services.py --config services.json --step firewall
python3 scripts/setup-services.py --config services.json --step relay --apply --events
python3 scripts/setup-services.py --config services.json --step keys --apply --events
python3 scripts/setup-services.py --config services.json --step driver --apply --events
python3 scripts/setup-services.py --config services.json --step permissions --apply --events
```

The administrator firewall command is explicit and is never run by the service
runner. The familiar `No ALTQ support in kernel` message is harmless; proceed only
when the installer succeeds and the firewall stage passes. The stage checks the
fresh root-owned PF/ALF status and the configured app's actual ALF block.

Relay installation refuses to replace different existing files. Key installation
preserves unrelated entries and rejects a runtime public key already authorized
with different restrictions. The driver stage only targets the guest selected by
Lume, over pinned key-only SSH; it installs the signed pinned driver, normal
permission guide and MCP launcher. It does not grant macOS permissions.

The permissions `--apply` action opens the guest guide through its GUI LaunchAgent.
Approve Accessibility and Screen Recording inside the guest, perform the guide's
capture check, then repeat the permissions command **without** `--apply` to verify.
Missing grants or capture consent remain a blocked stage. No TCC database is edited.

## Start the viewer and check readiness

First complete [shared-control initialization and both-user checks](evaluator-quickstart.md#prepare-shared-control-before-starting-either-runtime).
Do not start either service against a private 0700 directory owned by the other user.

As the separate viewer runtime owner, using the permanent reviewed source tree:

```sh
python3 scripts/setup-services.py --config viewer-services.json --step viewer --apply --events
```

This installs and starts a per-user systemd unit on Linux or a GUI LaunchAgent on
macOS, and waits for its authenticated loopback readiness check. It refuses an
existing different service. A macOS GUI login and Linux user-service manager must
already be available. No root/system-wide service is installed. The source and
Python paths must remain available after logout/reboot. Use the existing
[private access helper](viewer-access.md) locally to retrieve the browser link.

## Configure the runtime before final verification

Run these commands in the **same Hermes profile that will run the agent**, on
its runtime machine. Setup SSH and runtime SSH are separate connections. Even a
`local` target needs a verified restricted **agent** SSH alias (which may point
to the same Mac); never substitute the setup or viewer alias.

```sh
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.host_alias example-agent-mac
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.vm_name ownmachine
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.control_dir /absolute/shared/control
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.guest_profile macos
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.experimental_linux_background_input false
hermes --profile ownmachine config set computer_use.backend ownmachine
hermes --profile ownmachine config set computer_use.permission_mode standard
hermes --profile ownmachine config set plugins.isolation in_process
```

Use your saved plan's VM name, control directory and guest profile (`omarchy` for
Omarchy). Keep background input `false` unless you explicitly opt into its tested
experimental scope and prerequisites. The control directory must be the same
underlying directory shared with the viewer. These settings do not provision a VM.
**Without `computer_use.backend: ownmachine`, Hermes may select its host-desktop
provider. Do not run a desktop task until this setting is explicit.** Restart the
matching profile's existing Hermes sessions/gateway after changing configuration.

For a newly paired plan with an explicit agent alias, `setup --connect` can save
its runtime connection for local, remote or existing targets. Do not change an
in-progress plan's target to `existing`: that changes its digest and checkpoints.
For an older local plan with an empty alias, configure the runtime settings above
without editing the plan; verification accepts that explicit alias and binds it
into the client acceptance receipt. Nonempty plan aliases must still match.

From an operator verification environment with both restricted aliases and access
to the viewer's private directory (never the Hermes agent container):

```sh
python3 scripts/setup-services.py --config verification-services.json --step verify --events
hermes --profile ownmachine ownmachine doctor
```

Final readiness checks both SSH identities, refusal of arbitrary commands, guest
readiness, a native computer-use screenshot and the authenticated viewer/RFB handshake. It does not prove browser
click/type, external-network firewall isolation, reboot persistence or a desktop
model task. Complete those explicit acceptance checks before declaring onboarding
complete. A green readiness result never transfers control to the agent.

## Resume and remaining automation

Missing prerequisites are checked before the mutation checkpoint, so fixing a
missing firewall or viewer dependency permits a normal retry. Mutating stages use a per-VM lock and private durable checkpoints. A completed
stage rechecks its actual outcome. Changed config/source or uncertain mutations
stop for inspection; no guest deletion or destructive repair is attempted.
Read-only firewall/permission/readiness checks can be repeated after a human fixes
the issue. The runners report sanitized liveness events. The dedicated SSH endpoint now
imports authenticated final outcomes and conversation-bound liveness into Hermes.
See [reminder controls](onboarding-reminders.md) for explicit next-visit consent;
scheduled reminders require a matching running Hermes gateway and an explicitly approved destination. See [reminder controls](onboarding-reminders.md).


### Continue from Hermes chat

After the operator has paired and pinned the separate setup identity, configured
its reviewed source/plan allowlist, and granted the exact chat sender, use
`/ownmachine setup --run preflight`, then the same explicit stages and `--apply`
flags as the terminal. Progress appears in the invoking conversation without
blocking the chat. See [setup transport](setup-transport.md) for the new `harden`
stage, heartbeat limits, VNC-disabled bootstrap and viewer-role restart before
permission setup. No secrets are requested in chat; reminders require explicit opt-in.


### Finish verification and remove setup access

Configure `setup_public_key_file` in the Mac's private endpoint configuration to
point to the dedicated setup public key (mode 0600). Allow `verify` and `retire` in
that endpoint's reviewed stage allowlist. Keep the agent and viewer identities
separate. Pause agent control in the viewer before verification; verification
will refuse a human reservation or uncertain input rather than take it over.

```sh
hermes --profile ownmachine ownmachine setup --run verify --json
hermes --profile ownmachine ownmachine setup --run verify --apply --json
hermes --profile ownmachine ownmachine status --json
```

The first call validates a real screenshot without removing access. The second
repeats the checks, removes only the exact forced-command setup entry, proves that
key is refused and checks runtime readiness. The setup private key can then be
removed by its owner. Do not use that key for any other host or service.

A completed receipt is historical acceptance, not continuous monitoring. Use
`doctor` for current runtime health. If retirement is interrupted, inspect the
Mac's private setup-endpoint retirement receipt and exact authorized key entry;
do not blindly re-authorize a key or replay setup. Remaining runtime identities
and unrelated authorized keys must be preserved.


### Client verification and busy sessions

A Mac-side `verify: checks_passed` receipt is not completed onboarding. The client
must capture the guest and, with `verify --apply`, retire and prove rejection of
the temporary setup key. If capture fails, the CLI reports that distinction;
`ownmachine status --json` retains `screenshot_required`. Correct runtime settings,
check permissions/control status and repeat verification. Do not remove unrelated
keys or treat the remote receipt as proof of retirement.

OwnMachine serializes active desktop operations, not idle cached backends. A busy
operation refuses concurrent access; inspect it and retry a read after it finishes.
Another backend's operation invalidates earlier capture tokens, so recapture before
input. Human reservation and uncertain-write restrictions remain in force. When
upgrading from a version holding a lifetime session lock, stop/restart that old
profile gateway normally after saving work. Do not delete `session.lock` or kill an
unrelated process: removing the inode could allow simultaneous controllers.
