# Provision a OwnMachine guest

These are explicit operator setup commands run on the Mac host. They are not
model tools. Install the pinned Lume release first; see `host-setup.md`.

First run the read-only capacity preflight:

```sh
python3 scripts/provision-vm.py --preflight
```

Build the pinned local Lume with `scripts/build-native-lume.sh` first. Patched
unattended creation disables VNC throughout first-boot materialization and SSH
verification, so there is no temporary weak-password listener. Supply its path:

```sh
python3 scripts/provision-vm.py --name ownmachine --cpu 4 --memory-gb 8 --disk-gb 64 \
  --lume /absolute/path/to/patched-lume.app/Contents/MacOS/lume
```

The script sends `--verification-vnc disabled`. Stock Lume rejects that option;
there is no insecure fallback. The legacy `--verification-vnc-port` argument is
accepted but unused. Install the [required firewalls](security-isolation.md)
before enabling VNC through the relay after provisioning.

Defaults target a laptop-sized guest: 4 CPUs, 8 GiB guest memory and a 64 GiB
**sparse virtual capacity**. CPU, memory, disk, display, Lume executable, restore
image and preset remain configurable. The script refuses existing VM names and
uses NAT networking. No VNC port is passed during unattended setup. The script does not install
firewall rules; later browser access must use the guarded relay.

An 80 GiB virtual disk in the existing acceptance deployment occupied 26.2 GiB
on its host. That observation is not a clean-install minimum. The current restore
image inspected during acceptance was approximately 18.4 GiB. Provisioning must
budget download/temporary files, guest allocation, and host working space; it no
longer requires the **entire virtual capacity** to be free. See Lume's
[sparse-disk documentation](https://cua.ai/docs/lume/guides/manage-vms).

The default initial free-space budget is 60 GiB, adjustable with `--min-free-gb`
(32–2000). This is a conservative policy estimate, not an Apple minimum or a
measured guarantee for every OS build. Do not lower it merely to suppress a
failed check. Review the restore image size and expected guest footprint, preserve
host headroom, and monitor space during provisioning. Updates and applications
increase actual usage over time; a sparse disk can eventually reach its virtual
capacity. Preflight reports available space and the deficit without creating
state, downloading, or invoking Lume. Capacity is rechecked before creation.
The check applies to the home volume/default Lume storage; custom storage
locations are not yet supported by this capacity preflight.

Per-VM progress and private logs are under `~/.local/state/ownmachine/<name>/`.
Creation is bounded to 90 minutes. On a timeout or error inspect the existing
VM before retrying; the script never deletes or automatically recreates it.
A per-VM process lock prevents concurrent invocations of this operator script.

## First boot and credentials

### Newly created host accounts

Clean-account acceptance encountered `Failed to get current host key` and
`Unable to access security information` before installation began. The dedicated
host account had never logged into the desktop and had no login keychain.
[Upstream virtualization reports](https://github.com/openai/tart/issues/1146)
describe a first desktop login as a workaround for this error. If affected,
log into the dedicated **host** account once, complete its initial prompts,
then retry after inspecting the failed VM state. Do not disable the firewall,
change VM directory ownership, or disable FileVault to work around this error.
The first desktop login resolved this failure in clean-account acceptance;
creation then completed. Host login/keychain availability after a future reboot
still needs operator attention.

The unattended preset starts with upstream's `lume`/`lume` credentials. Before
using sensitive data, boot the created guest without a VNC listener:

```sh
"$HOME/.local/bin/lume" run ownmachine --detach --display none --vnc disabled
```

Obtain its current IP from Lume's operator-only metadata. Never publish the raw
JSON or `vncUrl` to a model or log because it may contain viewer credentials.
Then, on the Mac host:

```sh
python3 scripts/secure-guest.py --name ownmachine --guest-ip YOUR_CURRENT_GUEST_IP
```

This script is for a **fresh unattended guest**. It pins the new guest key on
first use (`accept-new`) in a dedicated known-hosts file, installs a dedicated
public key, and verifies strict key-only authentication before rotating anything.
All later SSH calls require the recorded host key. Ensure that the IP came from
the VM you just created, on the local NAT network; first use is trust-on-first-use,
not an independent attestation of guest identity.

It generates a unique recovery password with 16 random lowercase letters in
four hyphen-separated groups. There are no uppercase letters, digits, or easily
confused `i`, `l`, and `o` characters, making it easier to type in a native viewer.
It stores this password and SSH identity under the private state
directory, rotates the preset password, updates macOS autologin and the login
keychain, and disables guest password/keyboard-interactive SSH plus root login.
Do not print or commit these files. A partial failure retains recovery material
and refuses an automatic retry; inspect and recover manually before continuing.
The script's credential operations are not exposed to the agent.

Changing the guest password means Lume's default `lume ssh` credentials no longer
work. Use the dedicated key, known-hosts file and `StrictHostKeyChecking=yes` for
subsequent access. The guest IP can change; resolve it from Lume for each connection.

## Remaining setup

Install signed Cua Driver inside the guest and grant GUI permissions manually.
Native `computer_use`, MCP forwarding, and the noVNC viewer remain separate stages.
Keep VNC disabled until its loopback/private transport and takeover gate are ready.

## Signed guest driver

Inside the guest, run the explicit operator installer:

```sh
/bin/bash scripts/install-guest-driver.sh
```

It pins Cua Driver 0.44.0, verifies the official archive SHA-256 and Cua's Apple
Developer ID, and preserves the signed app bundle at `/Applications/CuaDriver.app`.
The wrapper and persistent config disable telemetry. Existing installations are
refused. It does not connect third-party agents or grant macOS permissions.
The archive is checksum-verified and Apple-code-signature-verified; Sigstore
verification is not implemented by this minimal installer.

Grant Accessibility and Screen Recording manually inside the guest's System
Settings before expecting computer-use operations to work. These are separate
from host permissions; never grant control of the personal host desktop.

## Guest DNS troubleshooting

If HTTPS to a literal IP succeeds but hostname lookups fail, test a DNS resolver
from the operator's network before changing anything. Some NAT host configurations
provide a resolver that does not answer guest queries. Inside the guest, explicitly
configure a verified resolver using your own network service name and address:

```sh
sudo networksetup -setdnsservers YOUR_NETWORK_SERVICE YOUR_DNS_RESOLVER
```

Restore DHCP-provided DNS with `sudo networksetup -setdnsservers YOUR_NETWORK_SERVICE Empty`.
Resolver addresses are deployment settings, never plugin defaults. The hardware
setup used a reachable, non-loopback resolver already configured on its Mac host;
its address is stored only in the private operator state directory.

## Open the guest for permission grants

In the dedicated Mac host account's graphical session, attach a native viewer:

```sh
"$HOME/.local/bin/lume" attach ownmachine --display native
```

In the guest, open the OwnMachine permission guide (`~/.local/lib/ownmachine/permission-guide.sh`
from a guest Terminal, or the app UI). The human grants Accessibility and Screen
Recording in guest System Settings, then restarts the app if macOS requests it.
No script should change TCC's database or grant permission to the host desktop.

If guest System Settings asks for authentication, use the **guest account's
current password**, not the host account password. After `secure-guest.py`, it
is stored privately on the VM host at
`~/.local/state/ownmachine/<vm-name>/guest-password`. Do not paste it into chat,
issue reports or logs. Lume's native viewer provides a Paste Mac → VM toolbar
button for transferring clipboard text. Stock Lume 0.7.0 uses factory SSH
credentials for this feature, which do not work after guest hardening. Use the
[optional key-aware native build](native-viewer.md) for clipboard integration,
or type the grouped password directly; clear any copied password afterward.

## Local-account setup defaults and a typeable password

After securing SSH, run `scripts/configure-firstboot.sh` with sudo **inside the
guest**. It reads the actual macOS version/build rather than using fixed version
markers. It marks optional account/privacy/Siri/Screen Time/appearance panels as
seen, disables Siri and both Mac/developer diagnostic sharing, and clears the
resume-setup flag. It does not sign into Apple, change automatic-update policy,
accept licenses, or grant Accessibility/Screen Recording.

These are version-sensitive macOS preferences, not a supported promise that all
Setup Assistant panels will be suppressed on every future OS. Fresh-install testing must verify the remaining screens for each macOS build. Existing visible
Setup Assistant panels may need to be completed or dismissed once. The fresh
macOS 26.6.2 laptop acceptance run still showed automatic updates, Apple Account,
age range, analytics, FileVault and Welcome after these preferences were applied.
The operator completed those screens without an Apple Account and with both
analytics options off. Do not describe this path as fully unattended first login.
These macOS setup pages are separate from the OwnMachine guest-permission guide.

If these pages appear, complete them in the native viewer before the permission
step:

1. Continue through Automatic Updates with your preferred update policy.
2. Apple Account: Other Sign-In Options → Sign in Later → Skip.
3. Choose the age range appropriate to the guest's user.
4. Analytics: leave both sharing options unchecked.
5. Choose guest FileVault encryption deliberately. The acceptance run used Not
   Now; host FileVault was unchanged. Guest encryption can require manual unlock
   after a VM restart, so include that in your recovery plan.
6. Click Get Started on Welcome, then follow OwnMachine's permission guide.

The guide now explains the host-side password-file location and direct typing
when clipboard paste is unavailable. Do not reset permissions or reuse a shared
password to work around viewer input.

To change the password, put your preferred value (at least 10 characters) into a
private file **on the Mac host** and run:

```sh
python3 scripts/change-guest-password.py --name ownmachine --password-file /absolute/path/to/private-password-file
```

No common password is shipped. The tool preserves strict SSH host verification,
changes the account password, updates autologin and login keychain, and verifies
authentication before replacing the saved password. If interrupted, the private
`guest-password` and `guest-password.pending` files retain recovery values; do
not rerun until the outcome has been inspected. Remove your input file afterward.

The provisioning display default is now 1900×1200, adjustable with `--display`,
after a live setup screen was clipped at the earlier resolution. This is a guest
display choice; it does not depend on a specific host address or account.
Keep this default for first boot: the laptop acceptance run reproduced clipping
at 1440×900 on the Update Mac Automatically screen. If an existing guest clips
setup controls, gracefully shut it down from inside the guest, then run
`lume set YOUR_VM_NAME --display 1900x1200` on the host and start it again.
Lume requires the guest to be stopped for this setting; do not force-stop it.

## Guided permissions at first GUI login (default)

Run `install-guest-driver.sh` from the complete source `scripts/` directory; it now
also invokes `install-permission-guide.sh`. For guests with the driver already
installed, run only the latter as the guest desktop user (no sudo):

```sh
/bin/bash scripts/install-permission-guide.sh
```

The installer adds a per-user Aqua LaunchAgent, `org.ownmachine.permission-guide`,
that runs once at graphical login. It starts the signed daemon and checks
CuaDriver's own permission identity after a bounded startup retry. A temporary
CLI failure or a daemon that has not started is not treated as revoked consent.
When both Accessibility and Screen Recording are granted and the final capture
check has succeeded, it exits without a prompt. Otherwise it opens a normal, closable/minimizable OwnMachine window with
buttons for Accessibility and Screen Recording in System Settings. The window
yields focus when opening Settings and never floats above permission prompts.
Enable CuaDriver on both pages; if absent, use + and select
`/Applications/CuaDriver.app`. Approve macOS's requested restart, then use Check
Again. Once both switches are on, this button invokes the signed driver's final
capture check. macOS may ask to allow direct screen capture without a picker;
choose Allow. Only a successful capture check marks onboarding ready. Denial or
failure leaves it pending. Readiness uses the signed driver's recorded capture
verification (bundle, source and timestamp), matching native doctor; a stale local
marker alone is not sufficient. A legacy local marker is cleared only after a
confirmed missing permission. The signed CuaDriver app remains the permission identity.

The driver starts with `serve --no-permissions-gate` to suppress its floating
onboarding panel; this flag does not change its authorization policy or grant
permissions. No TCC database changes, preapproval or simulated permission clicks
occur. The OwnMachine window uses macOS's built-in JXA/AppKit, without extra packages.

Startup defaults to 15 status attempts with one-second pauses between unavailable
results. Configure 1–60 attempts at installation if the host needs a different
startup allowance:

```sh
OWNMACHINE_PERMISSION_STARTUP_ATTEMPTS=30 /bin/bash scripts/install-permission-guide.sh
```

The value is stored in the per-user LaunchAgent environment. If the driver remains
unavailable, state becomes `driver_unavailable`; repair/start the signed driver
and rerun the helper. No misleading grant prompt is shown for unavailable status.
Each status command also has the driver's own execution time.

The LaunchAgent has no KeepAlive or recurring polling interval. Closing the window or
choosing Later leaves setup incomplete and tries again at the next GUI login.
Local status/logs are under `~/.local/state/ownmachine/permissions/`, outside the
plugin and source checkout.

To reopen the guide manually, run `~/.local/lib/ownmachine/permission-guide.sh` in
the guest. To remove automatic onboarding, unload the LaunchAgent with
`launchctl bootout gui/$(id -u)/org.ownmachine.permission-guide` and remove its plist
from `~/Library/LaunchAgents/`; these actions do not revoke existing permissions.
