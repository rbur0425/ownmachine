# Evaluator quickstart

OwnMachine gives Hermes a persistent macOS VM and a private browser viewer with
human/agent handoff. This guide is the entry point for evaluating the released
plugin. Installing the plugin does **not** silently create accounts, authorize
SSH keys, install a firewall or grant macOS permissions.

## Manual prerequisites before Hermes can provision

**You can start in Hermes by installing the plugin and saving a wizard plan. That
alone does not grant setup access or create a VM.** Before `setup --run preflight`
can reach the Mac, the operator must complete the trust/bootstrap items below.
Keep the chosen profile, VM name, storage and source pin consistent throughout.

| When / where | Human responsibility | Instructions |
| --- | --- | --- |
| Before remote execution — Mac host | Provide an Apple Silicon Mac, a dedicated non-admin VM account, its first graphical login, and administrator help for Remote Login. Keep FileVault enabled. | [Machines and identities](#choose-the-machines-and-identities) |
| Before remote execution — setup operator and Mac | Review matching full source, prepare/transfer the saved plan and service configuration, independently verify the Mac host key, and install the restricted temporary setup endpoint/key. Pair separate agent and viewer keys; keep private keys out of chat. | [Bootstrap trust](setup-transport.md#bootstrap-trust-once), [service configuration](wizard-quickstart.md#configure-the-service-stages) |
| Before either runtime starts — runtime host/containers | Create separate agent/viewer users and private homes, persistent storage and one shared control directory. Verify permissions as both actual users, including SQLite/lock files. Install the viewer's own dependencies and service under its owner. | [Shared control](#prepare-shared-control-before-starting-either-runtime), [viewer setup](wizard-quickstart.md#start-the-viewer-and-check-readiness) |
| After building Lume, before VNC — Mac administrator | Run the firewall installer for the exact app path and fixed port; require its success and the firewall stage check. A successful plugin install does not authorize sudo. | [Administrator handoff](#execute-setup-and-complete-the-administrator-handoff) |
| During first boot — guest desktop | Complete first-run choices. For macOS, approve Accessibility, Screen Recording and final capture consent in the guest. For Omarchy, review browser terms/keyring prompts yourself; no macOS permission grants apply. | [macOS permissions](#approve-guest-permissions-and-open-the-viewer), [Omarchy handoffs](#omarchy-foreground-evaluation-unreleased-pr-15) |

For Omarchy, verified image/private-bootstrap preparation is also required before
provisioning; follow the [Linux bootstrap instructions](linux-development.md#private-installer-bootstrap).
Chromium foreground input needs explicit native-module opt-in before desktop setup.
Do not follow the macOS provisioning sequence for an Omarchy plan.

**After bootstrap, Hermes can run the approved stages over SSH and import saved
progress.** It cannot supply administrator authentication, accept terms or approve
guest permissions for you. Complete each handoff, then rerun the corresponding
read-only check before continuing. [Pause and reminder instructions](#resume-without-guessing)
are available whenever you need to return later; reminders are not automatic.

## Choose the machines and identities

- **Mac host:** Apple Silicon macOS, a dedicated non-admin account for Lume, and
  an administrator available for account creation, Remote Login and firewall setup.
  Log into the dedicated account graphically once before creating the VM. Keep
  that account's home and VM storage private; do not run unrelated workloads there.
- **Hermes agent:** a separate runtime account/container with Hermes, Python and
  OpenSSH. It may run on the Mac or another machine. Model/vision configuration
  stays in Hermes; a suitable local model also works.
- **Viewer:** a different runtime account/container with its own SSH key and
  private access directory. The agent must not have its key, token, home, Docker
  socket or other host-execution tools. Profiles alone do not isolate OS files.
- **Setup operator:** temporary restricted setup access, separate from both runtime
  keys. It coordinates setup and is retired after successful verification.

The agent and viewer share **one underlying control directory**, not their homes.
Use persistent mounts and stable paths; a path inside a container may differ from
its host path. On the Mac, use the same canonical VM storage path in the plan and
relay configuration. `local` means the machine running Hermes, not your browser.
The v0.8.0 release supports macOS; this unreleased v1.0.0 candidate also supports the tested
Omarchy foreground configuration described below. Defaults are 4 CPUs, 8 GiB RAM, 64 GiB sparse disk,
1900×1200 display and a configurable 60 GiB provisioning free-space budget.

## Install the reviewed release

Obtain the full-source bundle and checksums from the release linked in the README;
[verify before extraction](distribution.md). Keep the full source at a permanent
operator-owned location: the viewer service references it. The plugin-only package
contains no privileged installers. For a Git checkout, select the release tag.

In a new dedicated Hermes profile (use your own profile name):

```sh
hermes profile create ownmachine --isolated-auth --no-credentials --no-skills --no-alias
hermes --profile ownmachine plugins install https://github.com/rbur0425/ownmachine.git#plugin --ref RELEASE_COMMIT --yes-deps --enable
hermes --profile ownmachine config set plugins.isolation in_process
hermes --profile ownmachine config set computer_use.backend ownmachine
hermes --profile ownmachine config set computer_use.permission_mode standard
hermes --profile ownmachine config set agent.disabled_toolsets '["terminal","file","code_execution"]'
hermes --profile ownmachine setup
```

Replace `RELEASE_COMMIT` with the full 40-character commit from the release, not a
branch name. For this unreleased v1.0.0 candidate, use the reviewed PR commit for
both plugin and full source, and set `setup_guide_ref` to that same full commit;
there is no v1.0.0 release tag yet. Do not use v0.8.0 bundles for Omarchy.
The last command configures your model through Hermes. Never copy
another profile's credential files. Verify that no extra tools/MCP servers restore
host terminal/file access. `in_process` is explicit because the native provider
and plugin terminal commands need this mode in the tested Hermes version.

For an unreleased candidate only, bind documentation links to the same reviewed
40-character source commit before starting the wizard:

```sh
hermes --profile ownmachine config set plugins.entries.ownmachine.settings.setup_guide_ref REVIEWED_COMMIT
```

Start the OwnMachine wizard with:

```sh
hermes --profile ownmachine ownmachine setup
hermes --profile ownmachine ownmachine setup --json > plan.json
```

The wizard previews settings and saves only with consent. Review the plan and
transfer it through your operator bootstrap channel. Follow the
[wizard configuration](wizard-quickstart.md) and [SSH setup endpoint](setup-transport.md)
for exact service JSON and pinned setup/agent/viewer key pairing. Confirm the Mac
host-key fingerprint independently at its console; an unverified SSH scan is not
trust establishment. SSH must run as the configured runtime user, including in
Docker; a working SSH connection as container root does not prove agent access.

## Prepare shared control before starting either runtime

On a **Linux runtime host**, ask its administrator to create a dedicated group
containing only the agent and viewer runtime identities. Substitute their existing
account names, a new control-directory path and your chosen group below. Install
the OS `acl` tools if `setfacl` is missing. Stop both runtimes before changing an
existing installation; never truncate existing state to fix permissions.

```sh
CONTROL_DIR=/absolute/persistent/ownmachine-control
CONTROL_GROUP=ownmachine-control
AGENT_USER=your-agent-user
VIEWER_USER=your-viewer-user
sudo groupadd "$CONTROL_GROUP"                     # once, if it does not exist
sudo usermod -a -G "$CONTROL_GROUP" "$AGENT_USER"
sudo usermod -a -G "$CONTROL_GROUP" "$VIEWER_USER"
sudo install -d -o "$VIEWER_USER" -g "$CONTROL_GROUP" -m 2770 "$CONTROL_DIR"
sudo setfacl -m u::rwx,g::rwx,m::rwx,o::--- "$CONTROL_DIR"
sudo setfacl -d -m u::rwx,g::rwx,m::rwx,o::--- "$CONTROL_DIR"
```

Start fresh login/service sessions so group membership takes effect. For Docker,
configure a common numeric supplementary GID with `--group-add`/`group_add`, matching
the control volume's group; changing the host's account memberships alone does not
change a container's groups. Mount only that directory into both containers, and
keep each private home exclusive to its owner. Grant traversal to parent directories
as needed without exposing either private home. Do not use `chmod 777`.

As the viewer owner, with the shared group active and reviewed full source:

```sh
python3 scripts/ownmachine-control.py --control-dir "$CONTROL_DIR" status
touch "$CONTROL_DIR/session.lock"
chmod 0660 "$CONTROL_DIR/lease.db" "$CONTROL_DIR/session.lock"
```

This initializes a **paused** lease if none exists; it does not reset existing state.
The explicit database mode is required because SQLite derives journal permissions
from it. The lock must also be group-writable. Default ACLs cover new heartbeat,
replacement and journal files even with a private umask. On an existing stopped
installation inspect group/mode/ACLs of all control files, including
`viewer-status.json`; repair only that shared directory, not private keys/tokens.

From **each actual runtime account/container**, check its groups and run:

```sh
id
python3 scripts/ownmachine-control.py --control-dir "$CONTROL_DIR" status
python3 - "$CONTROL_DIR" <<'CHECK'
import fcntl, pathlib, sqlite3, sys
p = pathlib.Path(sys.argv[1])
with (p / 'session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with sqlite3.connect(p / 'lease.db') as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE lease SET generation=generation WHERE id=1')
        db.rollback()
print('Shared lock and database access passed; state preserved.')
CHECK
```

Also prove that the agent cannot read the viewer's SSH key or access file. On a
native macOS runtime, have its administrator configure an equivalent dedicated
shared group and inheritable ACL on the control directory, then run the **same
access checks as both users**. Linux `setfacl` commands are not macOS commands.
The tested cross-user recipe here is Linux/Docker; do not assume native macOS
sharing is configured merely because the directory exists.

## Execute setup and complete the administrator handoff

Use the approved setup identity and source/plan digest from the endpoint guide.
Run `preflight`, `build`, fresh `preflight`, then `provision` with the documented
`--apply` flags. Build/provision run on the Mac and honor the selected storage.
Fresh provisioning leaves the guest stopped. Keep source and configuration fixed
while stages run; uncertain or interrupted mutations require inspection.

An administrator on the **Mac host** must explicitly run:

```sh
sudo /bin/bash scripts/install-vnc-firewall.sh YOUR_VNC_PORT /absolute/mac/OwnMachineLume.app
```

Use the configured unprivileged VNC port and actual signed app path. This installs
PF protection and application-firewall blocking/readiness. `No ALTQ support in
kernel` / `ALTQ related functions disabled` are harmless warnings, but **a nonzero
exit or “no readiness status published” is not success**. The following firewall
stage must pass. The non-admin Lume account is not expected to have sudo rights.

Continue `firewall`, `relay`, `keys`, `harden`, `driver`, `permissions` as described
in [setup transport](setup-transport.md). Guided hardening configures a new guest's
key-only SSH, rotates its factory password and installs its exact shutdown rule;
it does not grant TCC permissions. After hardening, use the **viewer identity** to
restart from VNC-disabled bootstrap into the protected runtime. Choose an available
port; the relay and firewall must agree. Start the viewer under its separate owner
only after the shared-control checks above pass.

## Approve guest permissions and open the viewer

Use the native Lume display or private viewer. Complete any remaining macOS first
login choices: skip Apple Account, choose no analytics and handle the other visible
Setup Assistant screens. These choices are not all automated. Approve **CuaDriver
Accessibility and Screen Recording inside the guest**, not for your personal host
desktop. Use the guide's normal window so system dialogs stay accessible. If asked,
enter the generated guest password locally; do not paste it into Hermes chat.

Follow macOS's Quit & Reopen/restart instruction, reopen the guide, select its
capture check and approve the separate screen-capture dialog. Both switches alone
are not proof of capture consent. Re-run the read-only permissions stage until it
passes. Do not edit TCC databases or grant host Full Disk Access as a workaround.

As the viewer owner, use [the private access helper](viewer-access.md) to obtain
the link locally. A remotely hosted loopback viewer needs an operator SSH port
forward; the browser cannot reach that machine's `127.0.0.1` directly. Keep tokens,
passwords and private links out of model context and screenshots.

## Verify, retire setup access, and try the desktop task

Run `hermes --profile ownmachine ownmachine doctor`. With control paused, run
`ownmachine setup --run verify --json`, then `--run verify --apply --json` through
the configured operator profile. Final verification includes a real screenshot,
role refusals and viewer handshake; apply also removes the exact setup authorized
key and proves it is refused. It does not grant the model control automatically.

In the viewer choose **Return to agent**. In a new Hermes session ask:

> Open Safari in the OwnMachine VM and go to https://www.google.com. Inspect the
> desktop first, use computer_use to launch/focus Safari, press Command+L, type
> the URL and press Return. Wait and capture the page to verify completion.
> Use only computer_use desktop actions and stop if operator review is required.

Independently check the visible Google page and Safari address field, not just the
model's answer. Then choose **Reserve for human use**, click/type in the guest,
and **Return to agent** or **Pause agent**. The accepted Qwen run and independent
verification are recorded in [acceptance evidence](docker-reminder-acceptance.md).
This verifies one keyboard/AX task, not every app or pixel-input workflow.

## Resume without guessing

Run these in the **same configured operator profile** (replace `ownmachine` if
using a different profile):

```sh
hermes --profile ownmachine ownmachine status
hermes --profile ownmachine ownmachine setup --next
hermes --profile ownmachine ownmachine doctor
```

Doctor checks runtime health; setup status/`--next` track the installation handoff.
A runtime-not-ready result is expected before provisioning and permissions finish.
Use the reported blocker to choose the relevant instructions below; this table is
an operator guide, not a claim that every diagnostic automatically deep-links here.

| Blocker / observed stage | Next action |
| --- | --- |
| No saved plan or incomplete configuration | [Run the wizard](wizard-quickstart.md#start-in-hermes); review and save the plan. |
| SSH/setup endpoint unavailable or source/plan mismatch | [Verify bootstrap trust](setup-transport.md#bootstrap-trust-once) and [profile settings](setup-transport.md#configure-the-active-hermes-profile); do not bypass host-key or source checks. |
| Firewall readiness missing or app/port mismatch | Ask the Mac administrator to complete the [firewall handoff](#execute-setup-and-complete-the-administrator-handoff), then rerun the firewall check. |
| Lease/database access denied or viewer unavailable | Check [both-user control permissions](#prepare-shared-control-before-starting-either-runtime) and the [separate viewer service](wizard-quickstart.md#start-the-viewer-and-check-readiness). |
| Guest driver, consent or capture not ready | Follow [macOS guest permissions](#approve-guest-permissions-and-open-the-viewer) or [Omarchy readiness](linux-development.md#runtime-and-control), then repeat the readiness check. |
| Interrupted setup or uncertain outcome | Use [authenticated progress/resume](setup-transport.md#execute-and-resume); inspect before retrying. Never delete checkpoints or replay a destructive stage blindly. |
| All runtime checks ready | Complete [screenshot verification and setup-key retirement](#verify-retire-setup-access-and-try-the-desktop-task), then independently verify a model task. |

To pause after saving your plan, request an **opt-in reminder preview**:

```sh
hermes --profile ownmachine ownmachine remind later --mode next-visit
# Review the preview, then use its actual token:
hermes --profile ownmachine ownmachine remind later --mode next-visit --confirm PREVIEW_TOKEN
hermes --profile ownmachine ownmachine remind status
# Cancel when no longer wanted:
hermes --profile ownmachine ownmachine remind off
```

`next-visit` does not promise a next-day message. For scheduled delivery, configure
the intended destination and matching running Hermes gateway, then preview and
confirm `--mode tomorrow` as described in the [reminder guide](onboarding-reminders.md).
No reminder is scheduled merely by reading these commands or saving a plan.
Chat setup/reminders also require an explicitly allowed sender. A reminder does
not complete a manual step; recheck status and readiness when returning.

## Omarchy foreground evaluation (unreleased PR #15)

Use the [Linux operator guide](linux-development.md) and [checked acceptance
plan](omarchy-plan.md) for the tested ARM64 foreground path. Keep the released
macOS setup as the default. Choose `--guest-profile omarchy` explicitly when
saving the Hermes setup plan; all VM names, storage, resources and aliases are
operator configuration. The new-plan free-space floor is 32 GiB, independently
configurable; it is not a promise that every install fits that amount.

The ordered handoffs are:

1. Verify the Linux Lume build and original signed Archboot ISO. The Mac
   administrator registers that exact app with the required firewall before VNC
   can be enabled. Native-console or private bootstrap installation uses VNC off.
2. Prepare a private seeded installer if avoiding console key entry. Pin both SSH
   aliases from its receipt: live root via `guest_bootstrap_ssh_alias`, installed
   desktop user via `guest_ssh_alias`. Never publish the seeded ISO or paste keys
   into Hermes chat. The live web terminal and stock SSH listener stay disabled.
3. Through Hermes run `setup --run provision --apply`, then
   `setup --run linux-boot-installer --apply`, `setup --run linux-base --apply`,
   `setup --run linux-boot-system --apply` and `setup --run linux-desktop --apply`.
   The boot stages verify the pinned guest and keep installer VNC disabled. Run
   relay/key setup and `harden`, then `linux-start-desktop`, before driver setup. The keyring wait, directory modes, user services,
   scale and palette fixes are installer work, not evaluator repair commands.
4. Restart into the graphical session and run `driver`. For exact-window Chromium
   input, set `enable_experimental_input: true` in operator configuration before
   desktop installation; otherwise leave the native module off. Run `permissions`
   to check Linux session/AT-SPI readiness; no macOS TCC grants are requested.
5. Prepare shared control as described above **before starting either runtime**.
   Start the viewer under its separate owner. If it is remote, install the
   check-only endpoint and configure the Mac's `viewer_probe_ssh_alias` and pinned
   `viewer_probe_ssh_config`. Run `setup --run viewer-check`; this is distinct from
   mutating viewer installation.
6. Test human reservation and return, pause the agent, then run
   `setup --run verify --apply`. This validates runtime roles and viewer access,
   captures the guest, retires temporary setup access, and proves the setup key
   is rejected while the runtime connection remains available.
7. Return control and run a small browser/editor task through Hermes. Chromium may
   show first-run terms and a keyring dialog: review terms yourself; create a
   protected keyring if you need it, or cancel for a test storing no credentials.
   Do not hide these decisions by weakening protection. Independently verify the
   visible result and saved file before marking acceptance complete.

Continue follow-up desktop tasks in the same Hermes conversation. The provider
holds an exclusive workspace session; a second conversation may be refused while
the first still owns it. For CLI follow-ups use Hermes `--resume SESSION_ID`, or
end the owning session through Hermes before starting another. After a VM restart,
the first capture can report `transport_outcome_unknown` for the closed stream.
Inspect the VM, then explicitly request a new read-only capture to reconnect;
never replay an uncertain input. Control remains paused until you return it.

A package update can invalidate the native input module. Doctor's capture
readiness is separate from `foreground_input_ready`; recheck after updates and
login. See [catalog disclosures](catalog/omarchy-preview.md) before promoting a
release or changing the public catalog pin.
