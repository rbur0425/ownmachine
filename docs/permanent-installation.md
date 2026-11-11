# Persistent installation and daily startup

This is an operator-managed, single-user installation. Choose your own Mac host,
Mac account, VM name, SSH aliases, Hermes runtime account, paths and ports. No
machine identity or fixed account named `hermes` is required. Native Hermes on
macOS/Linux and Docker use the same relay protocol. Only the optional viewer
service section below requires Linux with a systemd user manager.

## 1. Verify the actual runtime account

Run these checks in the environment that will run Hermes, as **that account**:

```sh
id
python3 -c 'import os,pwd; p=pwd.getpwuid(os.getuid()); print("SSH account:",p.pw_name,"passwd home:",p.pw_dir)'
```

For Docker, inspect the deployment's configured user and startup command. The
container's default exec user may differ from the account running Hermes; do not
assume root or a username from an example is correct. Execute checks explicitly:

```sh
docker exec --user YOUR_RUNTIME_USER YOUR_CONTAINER id
docker exec --user YOUR_RUNTIME_USER YOUR_CONTAINER \
  python3 -c 'import os,pwd; p=pwd.getpwuid(os.getuid()); print(p.pw_name,p.pw_dir)'
```

Use the actual Python executable if your image uses a virtual environment.
OpenSSH uses the account's passwd home for its default `.ssh/config`; changing
`HOME` or `HERMES_HOME` alone does not relocate that configuration. A numeric UID
without a passwd entry can also fail. Use a supported account in your image.
Mount the configuration, restricted key and verified known-hosts file where that
account can read them, with paths valid **inside** the container. Keep private
keys owner-readable only. Align writable mount ownership with that runtime UID/GID. If the image has a
fixed UID that differs from the existing shared data owner, use its supported
UID configuration or a reviewed derived image with a matching passwd/group
entry. Changing only `docker --user` to an unknown UID is insufficient. Do not
make keys or control files world-writable, and do not change production data
ownership merely to accommodate a test container.
Do not mount unrelated SSH identities or copy a production Hermes home into a
clean-install test. Persist the dedicated Hermes home and shared control data
outside the container's writable layer.

## 2. Establish the normal Mac connection

On the chosen Mac, enable Remote Login for the selected non-root account through
your administrator-managed macOS setup. Install the forced-command public key and
relay as described in [host setup](host-setup.md). Verify the host key through an
independent trusted channel. A stable private DNS name is convenient; an
operator-configured address also works. Never disable host-key checking to make
an example connect. Keep SSH private to your LAN or trusted private network.

From the Hermes runtime account, substitute your configured alias and VM name:

```sh
ssh -T YOUR_MAC_ALIAS ownmachine-host status --vm YOUR_VM_NAME
ssh -T YOUR_MAC_ALIAS uname -a
```

The first must return the configured VM's readiness. The second must fail with
`unsupported_operation`. Repeat from inside Docker if that is the deployment
being validated; a successful host-shell check does not prove container access.
The alias must target your Mac's normal SSH endpoint, not an acceptance-only
listener or a temporary reverse tunnel. Temporary tunnels remain useful for
experiments but are not the persistent deployment demonstrated here.

SSH starts the forced-command relay on demand. The relay needs no background
process or Mac LaunchAgent. It does not start the VM merely because SSH connects.
FileVault unlock, a host login or guest startup may still require the operator.
**Do not disable FileVault.** At the physical Mac's startup login screen, select
an account authorized to unlock the disk and enter that account's login password.
Wait for macOS to finish loading. Reaching the desktop means the startup volume
is already unlocked for this boot; encryption remains enabled. FileVault protects
the startup volume, not only the dedicated service account.

Leave the VM stopped until the firewall has been checked after a host reboot.
Then start it explicitly through the configured lifecycle command and allow guest
startup to finish before running doctor. An early guest-not-ready result is not
a reason to restart it again. The [observed reboot test](hardware-acceptance.md#physical-host-reboot-follow-up--2026-11-10)
passed operator-assisted recovery within its documented scope. Browser-profile
identity and Google-account/session persistence were not certified. No automatic VM recovery is claimed.

## 3. Keep installations separate from development checkouts

Use a verified source bundle or a clean checkout pinned to a reviewed commit in
a versioned installation directory. Keep it available for the viewer and operator
scripts. Do not point a long-running service at a feature checkout that changes
underneath it. Keep keys, host JSON, Hermes configuration and the control directory
outside that source directory. Record the branch/commit or bundle manifest with
your deployment receipt. All providers and viewers for one VM must share the
same underlying control directory, including across container mounts.

Install the plugin using [community setup](community-setup.md), then run native
and [combined onboarding checks](onboarding-check.md) in its actual environment.
A viewer process restart does not start the VM, reset permission grants or clear
an uncertain write. Existing control state persists; it is not automatically
changed to agent control.

## 4. Optional supervised viewer on Linux

Install the pinned [viewer dependencies](streaming.md) in a dedicated Python
environment. Configure the service account's own restricted SSH alias first.
The account must have access to the same control directory as Hermes. A separate
host-side viewer can use a different path from Docker, provided both paths refer
to the same files. No system-wide root service is needed.

Render a unit from your versioned source installation, replacing the placeholders:

```sh
mkdir -p "$HOME/.config/systemd/user"
python3 scripts/render-viewer-service.py \
  --source /absolute/path/to/versioned-source \
  --python /absolute/path/to/viewer-venv/bin/python \
  --host-alias YOUR_VIEWER_MAC_ALIAS --vm-name YOUR_VM_NAME \
  --control-dir /absolute/path/to/shared-control \
  > /private/path/to/viewer-candidate.service

systemd-analyze --user verify /private/path/to/viewer-candidate.service
```

The renderer only prints configuration; it does not install or start anything.
Review it, then copy it to a service filename you choose, such as
`~/.config/systemd/user/ownmachine-viewer.service`. If a viewer already owns the
control directory, stop that **viewer process** normally before starting the
service. This disconnects browser sessions but does not shut down the VM. Do
not interrupt active input or acknowledge an uncertain operation just to switch
supervisors. Save any unit being replaced so it can be restored.

```sh
systemctl --user daemon-reload
systemctl --user enable --now ownmachine-viewer.service
systemctl --user status ownmachine-viewer.service
journalctl --user -u ownmachine-viewer.service -n 30 --no-pager
```

Default port `0` selects an available loopback port. `--port NUMBER` requests a
preferred port but still falls back if occupied. Optional `--swap-red-blue`,
`--read-only` and connection/action timeout flags remain configurable. The unit
uses an owner-only umask, no shell command, and bounded restart-on-failure; it
never issues guest lifecycle or control-transfer commands.

A user service normally starts with its user manager at login. Staying active
after logout or starting before login depends on the host's user-manager policy
(for example administrator-enabled lingering); `enable` alone does not prove
that behavior. Check your platform's policy. Do not assume service enablement
proves boot recovery, Mac login readiness or firewall persistence.

After every viewer restart, retrieve the new private link with
[the access helper](viewer-access.md). Its token rotates and its port may change.
Reconnect a browser tunnel to the actual reported port. The viewer itself does
not depend on that browser tunnel; closing the tunnel only removes local access.

On a host without systemd, run the same foreground viewer command under your
chosen process supervisor, with the same account, private configuration and
shared control directory. This guide does not install a macOS host LaunchAgent.

## Optional Docker-supervised viewer on a Linux runtime host

A separate viewer container is another supported deployment arrangement. Use a
pinned image with the viewer dependencies and run `viewer/server.py` as its main
process, with an init process and an explicit restart policy such as
`unless-stopped`. Do not rely on a detached `docker exec` process inside an idle
Hermes container: it is not that container's supervised main process.

Mount the reviewed, versioned source read-only; mount the restricted SSH identity,
configuration and verified known-hosts file read-only in the runtime account's
actual passwd home. Mount the same persistent control directory read-write in
both viewer and Hermes containers. Keep the configured UID/GID and ownership
consistent. Supply host alias, VM name, control path, port and optional color
correction as ordinary viewer arguments. A Linux host-network container can bind
the viewer to the runtime host's loopback address; this is not a portable Docker
Desktop networking assumption and does not authorize a public listener.

The Mac still uses its normal Remote Login endpoint and administrator-installed
OwnMachine firewall. There is no permanent reverse tunnel or custom Mac SSH
listener in this arrangement. The forced-command relay starts on demand. The
viewer runs on the runtime host, so rebooting the Mac does not restart the viewer
container. After the Mac returns, verify the firewall before explicitly starting
the guest. Browser SSH forwarding is a separate client connection and must be
reopened after the client laptop restarts. A DHCP address may change: configure a
stable private DNS name or reservation, or update the private SSH configuration;
never weaken host-key verification to recover connectivity.

Test a viewer-container restart before the host reboot. Verify credential rotation,
rejection of the old access link and unchanged shared control state. Retrieve the
new link privately. Container restart policies and Mac service registration are
baseline checks, not proof of recovery after physical reboot.

## 5. Verify persistence without rebooting a physical host

1. Confirm the direct restricted SSH status command and arbitrary-command refusal.
2. Run native doctor, combined readiness and the optional VNC handshake probe.
3. With control idle/paused, restart only the viewer service. Confirm it returns
   active, the old link is rejected, the new link works and lease state is unchanged.
4. Recreate an isolated test container with the same image/account and persistent
   mounts. Confirm installed file hashes, configuration and lease state survive;
   rerun doctor from its configured runtime account. Do not recreate production
   containers just to perform this acceptance check.
5. Close the provisioning SSH session and browser tunnel. Reconnect in a new
   session and verify the service still runs. Guest permissions and VM contents
   must remain unchanged; no guest or physical-host reboot is needed here.

These checks establish process/container and session independence. Physical-host
reboot and pre-VNC firewall verification are separate checks; see the qualified
[physical-host result](hardware-acceptance.md#physical-host-reboot-follow-up--2026-11-10).

To remove the optional viewer service, stop and disable the chosen unit, remove
only that unit file, and reload the user manager. Preserve VM disks, keys, Hermes
home and control state. To roll back code, stop the service, restore the reviewed
unit pointing to the previous versioned source, reload and start it, then rerun
doctor and retrieve a fresh access link.

## Hardened service identities

Follow [security isolation](security-isolation.md) before enabling services. Run
Hermes and the viewer as different users/isolated containers with different SSH
keys. Pass `--access-dir` to the viewer service renderer for its private state;
only the control directory is shared. Existing services need an explicit update.
