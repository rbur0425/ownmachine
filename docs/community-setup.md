# Community setup and doctor

OwnMachine uses one persistent VM and a shared control directory. Addresses, SSH
keys, host/guest accounts and model credentials belong to the operator. The
source contains none of them. Complete [host setup](host-setup.md),
[guest setup](vm-setup.md), and [MCP setup](native-provider.md) first.

For a verified source bundle instead of a Git checkout, follow the
[distribution verification steps](distribution.md) first. The plugin-only archive
does not include the host/guest/viewer onboarding tools.

For persistent SSH, runtime-account checks, supervised viewer startup and
container recreation, follow [persistent installation](permanent-installation.md).

## Install a dedicated Hermes home

Use Python from your Hermes installation. Choose a **new, nonexistent** home
with an existing writable parent. The installer refuses existing homes, including
empty directories and symlinks; it never edits another profile or copies keys.

```sh
python scripts/install-hermes.py \
  --hermes-home "$HOME/hermes-ownmachine" \
  --host-alias ownmachine-host \
  --vm-name ownmachine \
  --control-dir "$HOME/.local/state/ownmachine/control"

export HERMES_HOME="$HOME/hermes-ownmachine"
hermes plugins validate "$HERMES_HOME/plugins/ownmachine"
hermes computer-use doctor
```

Substitute your SSH alias and VM name. The control directory must be the **same
underlying directory** for every viewer and agent targeting that VM. When using
Docker, use its container path inside Hermes and the corresponding bind-mounted
host path for host-side operators. Do not create separate leases for different
profiles. The installer does not initialize, reset or transfer existing control.

The installer copies only `plugin/` plus the project license, enables OwnMachine, selects the native backend
with standard permissions, and sets `plugins.isolation: in_process` in this new
home. This isolation setting is required by the tested Hermes category-provider
loader. Configuration uses JSON syntax, which is valid YAML and accepted by
Hermes. Both timeouts are configurable with `--connect-timeout-seconds` and
`--action-timeout-seconds` (1–120). Home permissions are 0700; config and receipt
are 0600. A receipt records the installed file hashes and the source commit when
available from a clean Git checkout. Dirty/exported sources have a null commit
and still record exact file hashes.

The installer records the installed Hermes config schema when available, so a
new profile is not mistaken for a legacy configuration. Provider discovery and
full plugin loading are tested separately: the category collector does not offer
all middleware registration methods.

A fresh home has no model credentials. Configure your model/vision provider
using Hermes's own setup before asking an agent to perform work. Doctor does not
need an LLM or send screenshots to one. SSH authentication must already work
from the user/container environment running Hermes.

For an existing Hermes home, follow [manual configuration](native-provider.md).
This installer intentionally does not merge YAML or upgrade an existing install.
For an upgrade, stop the native agent session, validate the new package, replace
only the installed plugin, and retain configuration, SSH identity and shared
control state. Keep the previous package and receipt for rollback. A running
Hermes process must reload the plugin before using updated code.

## Set up the noVNC browser desktop

Complete [identity separation and hardening](security-isolation.md) first.
The agent and viewer need different keys and isolated runtime users.
Complete this step before the first browser-control session. noVNC is bundled
with the source checkout; the standalone viewer and its dependencies are not
installed by the Hermes plugin installer. Native agent input still uses MCP.

1. On the Mac host, update the restricted relay and choose an unused, fixed VNC
   port. Follow [streaming host setup](streaming.md#host-prerequisites-and-firewall)
   to add `enable_vnc: true` and `vnc_port` to the existing private host JSON.
   Preserve the VM name, guest SSH alias and other settings.
2. **Use an administrator account on the Mac host** to run
   `sudo bash scripts/install-vnc-firewall.sh YOUR_VNC_PORT /absolute/path/to/lume.app` from the checkout.
   The dedicated non-root VM account may not be in sudoers; switch to an
   existing administrator account for this step. Lume listens on all interfaces,
   so a localhost VNC URL alone does not protect the port. Install the rule
   before enabling the listener. If this cannot be completed, keep `enable_vnc`
   false; browser streaming is unavailable until firewall setup succeeds.
   You may see `No ALTQ support in kernel` and `ALTQ related functions disabled`;
   these are harmless for OwnMachine's firewall rule. Proceed when the installer
   finishes successfully and prints `OwnMachine VNC port YOUR_VNC_PORT is restricted
   to loopback.` with your chosen port. See the
   [firewall output explanation](streaming.md#host-prerequisites-and-firewall).
3. Save guest work and gracefully restart the VM using the lifecycle controls
   to apply the host settings. The guest shutdown helper and lifecycle opt-in
   must already be installed as described in [lifecycle setup](viewer-lifecycle.md).
   Verify from a different machine that direct access to the chosen VNC port
   is blocked. The SSH relay must still be able to connect locally.
4. As a separate viewer OS user/container, create an environment and launch
   the viewer with the same shared control directory as Hermes:

   ```sh
   python3 -m venv "$HOME/.local/share/ownmachine-viewer-venv"
   "$HOME/.local/share/ownmachine-viewer-venv/bin/pip" install -r viewer/requirements.txt
   "$HOME/.local/share/ownmachine-viewer-venv/bin/python" viewer/server.py \
     --host-alias ownmachine-viewer-host --vm-name ownmachine \
     --control-dir "$HOME/.local/state/ownmachine/control"
   ```

   Replace the alias, VM and directory with your configuration. With Docker,
   use the host path of the same bind-mounted control directory. The viewer
   chooses a free HTTP port; this is separate from the fixed host VNC port.
   If the desktop's red and blue channels are reversed, add `--swap-red-blue`
   (required by the tested Lume release). See [all viewer options](streaming.md#viewer-installation).
5. Retrieve the current private link on the viewer machine:

   ```sh
   python3 scripts/ownmachine-viewer-access.py \
     --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" --show-url
   ```

   Use your private viewer access directory. For remote access, follow the
   [private link and SSH tunnel guide](viewer-access.md); it also covers a
   different local port and token-only output for the unlock form. Keep the
   returned link private. Restarting the viewer rotates its token.
6. Select **Reserve for human use**, click inside the desktop, then type in a
   disposable document and drag its window to check direct keyboard and mouse
   input. Select **Pause agent** and verify input stops. Select **Return to
   agent** when finished; the browser becomes view-only and the agent must take
   a fresh capture. Start, Restart and Shut down leave agent control paused.

The existing guest Accessibility, Screen Recording and capture-consent guide
is still required for Hermes/MCP. noVNC does not approve those permissions.
Native doctor checks MCP readiness and viewer heartbeat. Use the separate
[viewer doctor](recovery.md) for authenticated HTTP, streaming prerequisites and
an optional shared VNC handshake. Neither certifies firewall coverage or browser
input. Perform the checks above; the recovery guide explains common failures.

## Diagnose without Hermes

The same checks are available from a source checkout:

```sh
python scripts/ownmachine-doctor.py \
  --host-alias ownmachine-host \
  --vm-name ownmachine \
  --control-dir "$HOME/.local/state/ownmachine/control"
```

Use `--json` for structured output. The standalone command accepts the same two
timeout flags as the installer. Both doctor entry points exit 1 if a required
check fails, or 0 when transport readiness checks pass. Warnings distinguish
intentional paused/human control and the optional offline viewer from broken
connectivity. READY does **not** mean agent input is enabled or a GUI task has
succeeded; inspect the control check.

Doctor checks configuration, standard permission mode, the SSH executable, shared control state, viewer
heartbeat, host relay, Lume/VM state, guest readiness, each required permission,
recorded capture consent, and an MCP handshake with required-tool discovery.
It reports stable codes with a suggested repair. Dependent checks stop when an
upstream prerequisite fails, so a stopped VM does not produce a pile of false
permission errors. Fix the first failure and rerun.

Doctor never starts/stops a VM, changes control, clears uncertain actions,
approves permissions, captures the desktop, or sends input. It reads lease state
with SQLite read-only mode. Permission/consent checks are the readiness helper's
reported/recorded evidence, not a new capture. MCP diagnostics open and close an
independent stream without acquiring a native writer session. Host status and
MCP have bounded calls; doctor can take longer than one timeout because it runs
multiple checks. Raw SSH stderr, private endpoints and viewer tokens are not
included in reports. It cannot distinguish every SSH authentication, network,
or host-key failure; those share a safe connection-failure code.

## Check native stability

After doctor passes, optionally run the [read-only stability check](stability.md)
with Hermes Python while the agent is idle. The browser can stay under human
control. Captures are opt-in and never saved; reports contain only timing/status.

After saving work, follow the [guest restart acceptance checklist](persistence.md)
to verify your own files and application/profile persistence.

## Recovery guide

| Doctor code | Operator action |
|---|---|
| `invalid_configuration` | Set the SSH alias, configured VM, absolute shared control directory and valid timeouts in the active home. |
| `ssh_missing` | Install OpenSSH in the actual Hermes environment/container. |
| `host_unreachable` / `ssh_connection_failed` | Check network, alias, key authentication and independently verified host key. Inspect SSH locally; never disable verification. |
| `invalid_host_response` | Install the matching restricted relay; remove shell banners from its stdout. |
| `lume_missing` | Install the pinned Lume release and correct the relay's configured path. |
| `vm_stopped` / `vm_absent` | Explicitly start the existing VM, or provision the named VM if absent. Doctor never creates one. |
| `guest_not_ready` | Check guest GUI login, SSH alias/key, readiness helper and relay guest configuration. |
| `accessibility_required` / `screen_recording_required` | Use the guest permission guide, approve manually, and follow any restart prompt. |
| `capture_consent_required` | Complete the guided capture test and manually approve any macOS capture dialog. |
| `driver_not_ready` | Start the signed standard-mode driver in the desktop login; verify the pinned version and login launcher. |
| `mcp_unavailable` / `incompatible_driver_tools` | Check relay `enable_mcp`, the guest MCP launcher and the supported pinned driver. |
| `control_not_initialized` / `control_paused` / `control_human` | Intentional input block. Use the trusted operator controls when ready; the agent must recapture. |
| `uncertain_outcome` | Inspect the guest first. Explicitly acknowledge through operator controls; never blindly repeat the failed action. |
| `control_unreadable` | Check ownership/database integrity. Do not delete the lease to evade an uncertain action. |
| `viewer_offline` | Optional: start the viewer and use its private access link. It automatically chooses a free port. |

The standalone doctor cannot diagnose Hermes's plugin loader or model settings.
If Hermes cannot discover OwnMachine, check the active `HERMES_HOME`, installed
`plugins/ownmachine`, enabled entry, `in_process` isolation and selected backend.
Run plugin validation before investigating the remote VM. Keep raw diagnostic
logs private; share the sanitized doctor report when requesting help.

## Validation for this phase

A fresh dedicated home was created with the installer in the actual Hermes
container. Its generated configuration loaded without manual edits; plugin
validation passed and `hermes computer-use doctor` completed host, guest and
MCP checks against the existing VM. Human control was reported as an intentional
warning and remained unchanged. No GUI writes or lifecycle operations were
performed by these checks. This tests installation into a fresh Hermes home,
not provisioning a new physical Mac or a new VM from scratch.

Automated tests cover missing SSH, stopped VM, missing Lume, unreachable guest,
missing individual permissions, absent MCP tools, MCP failure, unsupported
permission modes, corrupt/pending control state, secret-free reports, and fresh
home installation/refusal/rollback. Platform-specific provider and onboarding
checks run in the complementary Linux/Hermes and macOS test environments.

Final suite: 93 tests discovered; macOS passed 84 with nine Hermes-only skips,
and Hermes passed 88 with five macOS-only skips. Together the runs exercised
every test. Installed plugin validation and both live doctor entry points passed.

## Check the completed setup

Use the [unified onboarding check](onboarding-check.md) on the viewer machine for
one native/viewer report with a first-failure remedy. Run the native doctor inside
the actual Hermes environment too; host readiness does not prove container setup.
Automatic checks leave browser interaction, external firewall and persistence
acceptance explicitly unverified.

For an existing installer-created home, follow [offline plugin upgrades](upgrading.md).
Do not rerun the fresh-home installer over an existing profile.

## Test a separate Docker installation

Use a disposable container built from your supported Hermes image. Give it a
new writable data directory and install into a new Hermes home using the command
above **inside that container**. Mount the source read-only, mount only the
restricted relay SSH identity and verified known-hosts file, and set
`HERMES_HOME` explicitly for installation, validation, doctor and later agent
commands. Model credentials are configured separately; do not copy a production
Hermes home as a clean-install test.

OpenSSH reads its default configuration from the account's passwd home; changing
`HOME` alone may not change that location. Mount `.ssh` at the container user's
actual home and use container-visible paths in its SSH configuration. Verify the
relay alias from the container before running doctor. Use the same bind-mounted
control directory for the test viewer and provider. Leave control paused until
readiness passes and you are ready for a disposable GUI input test.

Prefer the ordinary private-network relay setup in [host setup](host-setup.md).
If the Mac cannot accept inbound SSH, an operator-managed restricted reverse
tunnel can support testing; its ports, account and key paths are deployment
configuration, not plugin defaults. A temporary tunnel does not establish
persistence after host login or reboot. Do not expose VNC or the viewer publicly.
