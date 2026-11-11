# Evaluator quickstart

OwnMachine gives Hermes a persistent macOS VM and a private browser viewer with
human/agent handoff. This guide is the entry point for evaluating the released
plugin. Installing the plugin does **not** silently create accounts, authorize
SSH keys, install a firewall or grant macOS permissions.

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
Only macOS guests are supported. Defaults are 4 CPUs, 8 GiB RAM, 64 GiB sparse disk,
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
branch name. The last command configures your model through Hermes. Never copy
another profile's credential files. Verify that no extra tools/MCP servers restore
host terminal/file access. `in_process` is explicit because the native provider
and plugin terminal commands need this mode in the tested Hermes version.

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

`ownmachine setup --next`, `--run progress`, `status` and `doctor` show the next
handoff and observed state. Fix prerequisites and repeat read-only checks. A
changed plan/source or uncertain mutation stops for inspection; do not delete
checkpoints or rerun a destructive stage blindly. Reminders are opt-in via preview
and confirmation; scheduled delivery needs a matching running Hermes gateway.
The [reminder guide](onboarding-reminders.md) explains limits and opt-out.
