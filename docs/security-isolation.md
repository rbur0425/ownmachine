# Separate the agent, viewer and Mac VM account

These requirements apply to the hardened setup. Upgrade the host relay, authorized
keys, viewer launch arguments and Hermes profile together; old installations are
not silently rewritten. Save guest work before restarting it with managed VNC
credentials. Do not restart a host or guest just to install these files.

## Three identities, two host keys

Use a dedicated non-administrator **Mac VM account** solely for Lume and the
restricted relay. Do not run Hermes, general browsing or unrelated programs as
that account. Use two different Ed25519 keys from two isolated runtime accounts:

| Runtime | Key's forced role | Permitted host operations |
|---|---|---|
| Hermes user/container | `--role agent` | `status`, `mcp` |
| Separate viewer user/container | `--role viewer` | `status`, `vnc`, `start`, `stop`, `restart` |

Both keys target the dedicated Mac VM account, but neither permits a shell, PTY,
agent forwarding or TCP forwarding. Install the matching relay first. Generate
keys with `ssh-keygen -t ed25519` as their respective runtime users; do not share
the private keys or SSH agents. Render the public entries:

```sh
python3 scripts/render-host-keys.py \
  --python /absolute/path/to/python3 \
  --relay /absolute/path/to/ownmachine_host.py \
  --agent-public-key /path/to/agent.pub \
  --viewer-public-key /path/to/viewer.pub
```

Review and install the two output lines in the Mac account's `authorized_keys`.
Remove the old all-purpose OwnMachine key entry. Do not remove unrelated admin
access. Keep separate SSH aliases (`ownmachine-host` for Hermes and
`ownmachine-viewer-host` for the viewer), verified host keys, `IdentitiesOnly yes`
and `ForwardAgent no`. Do not mount the viewer key/home/private state into Hermes.
A different alias using the same key or OS user is not isolation.

Confirm `status` succeeds through both keys; `vnc/start/stop/restart` through the
agent key and `mcp` through the viewer key must return `unsupported_operation`
without dispatching. The CLI viewer now supports VNC only; legacy frame/MCP
viewer access would defeat this role separation.

## Required Mac firewalls

Choose an unused fixed VNC port between 1024 and 65535 and configure `enable_vnc`
and `vnc_port` in the private host JSON. Port zero/random ports are refused when
VNC is enabled. From an administrator account run:

```sh
sudo bash scripts/install-vnc-firewall.sh YOUR_VNC_PORT /absolute/path/to/lume.app
```

The app path normally belongs to the dedicated VM account:
`/Users/YOUR_VM_ACCOUNT/.local/share/lume/lume.app`. Do not substitute the admin
account's home unless that is actually where Lume is installed.

The installer preserves the global PF ruleset, loads the OwnMachine anchor,
enables PF, enables the macOS application firewall, and blocks the Lume app bundle. macOS registers its signed executable under
that bundle; querying the executable path separately is misleading on the tested
macOS version. The application rule covers inbound Lume connections on other
ports as well; PF independently restricts the configured port to loopback.
`No ALTQ support in kernel` / `ALTQ related functions disabled` do not indicate
failure for this rule. Require a successful exit and the final success message.

The root LaunchDaemon rechecks every 15 seconds. Only after verifying active PF,
the expected loaded rule and application firewall blocking does it publish
`/private/var/run/ownmachine/firewall-status.json`. The relay rejects missing,
non-root-owned, writable, malformed, wrong-port or older-than-45-second evidence.
VNC starts and connections fail closed; open streams recheck at least every five
seconds. A status file is bounded-age evidence, not an atomic guarantee against a
root user changing firewall policy between checks. No unprivileged config path
can override the evidence location.

Verify from a second machine that the configured VNC listener is unreachable,
while the local SSH relay works. To establish all-port coverage independently
of PF, also test a controlled non-PF Lume listener port. Verify again after Lume
updates and host reboot. Application firewall loopback behavior must be measured
on the actual macOS version; it is not a local-user isolation mechanism. Do not
claim this protects against another process under the Mac VM account or root.
A copied/different Lume executable may require another application rule.

## VNC password and private host files

On each relay-managed start, eight independent characters are drawn from the 66
URL-safe characters `A–Z a–z 0–9 - . _ ~` (about 48.4 bits). VNC's legacy authentication uses
only eight bytes; making this string longer would not strengthen that protocol.
The relay stores it in `~/.local/state/ownmachine/vnc-password` with mode 0600,
passes only its path via the patched Lume's `--vnc-password-file`, and sends detached logs to the private
`lume-detached.log` in that 0700 directory. The VNC URL must match the configured
port and this managed password; manually launched/unmanaged listeners are
refused. Credentials never go to the model or browser JavaScript.

Upstream Lume 0.7.0 exposes `--vnc-password` in its process arguments, including
its persistent detached child. **Other ordinary local accounts on macOS can read
those arguments**; this is not limited to privileged users. Loopback is allowed
by the firewalls, so that exposure defeats the password boundary. OwnMachine no
longer passes a password in argv or the environment and never falls back to that
upstream flag.

Build the pinned local Lume with `scripts/build-native-lume.sh` before enabling
browser VNC, set `lume_path` to that app's `Contents/MacOS/lume`, and install the
firewall rule for that app. The build includes both reviewed patches and uses
bundle ID `org.ownmachine.lume`, distinct from the vendor app. It is locally
ad-hoc signed, not vendor-notarized; Xcode/Swift and build space are required.
The file option rejects symlinks, non-regular files, other owners, permissions
other than 0600, hard links, wrong length and non-URL-safe characters. Detached
children receive the path and re-read/validate the protected file. A stock Lume
without that option fails to launch; there is no insecure compatibility fallback.

The literal URL-safe alphabet also avoids upstream Lume's unescaped URL/password
parsing bug. Python round-trip tests cover every character, and the patch includes
Swift URLComponents and detached-argument tests. Root and code running as the
Mac VM account remain trusted and can read its files or process memory.

Run `chmod 700 "$HOME/.lume"` as the dedicated account; the relay also enforces
this before lifecycle/VNC access. Review macOS ACLs (`ls -lde "$HOME/.lume"`) and
remove unexpected ACL grants. Custom Lume storage outside this directory needs
its own private permissions. Use a private primary group for a new dedicated
account where practical. Check `id YOUR_VM_ACCOUNT`; have an administrator change
primary/supplementary groups deliberately. The installer does not remove `staff`
from an existing login account or risk breaking its files. Mode 0700/0600 is the
baseline even when the account belongs to `staff`.

## Viewer secret and shared state

Run the viewer as its separate OS user/container. `--control-dir` still points
to the shared lease/heartbeat directory. Set `--access-dir` to an owner-only
0700 directory outside that tree (default:
`~/.local/state/ownmachine-viewer/VM_NAME`). `viewer-access.json` is 0600 there.
The viewer refuses an access directory equal to, inside, or containing the
shared directory. Remove an old `viewer-access.json` from shared state after
stopping the old viewer; restart rotates the bearer token.

```sh
python3 viewer/server.py --host-alias ownmachine-viewer-host \
  --vm-name ownmachine --control-dir /shared/ownmachine-control \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine"
python3 scripts/ownmachine-viewer-access.py \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" --show-url
```

New control directories default to 0700, independent of the caller's umask.
Existing operator-managed directory modes/ACLs are preserved.
For separate Linux users, an administrator must grant both identities access to
only the control directory, including SQLite journal files. For example, use a
dedicated group, a setgid directory and default ACLs granting that group rwX.
Precreate the shared lease database with group rw before either service starts;
SQLite derives journal permissions from the database. After an administrator
has configured the dedicated shared group and directory, run as one of the
runtime identities (with that group active):

```sh
python3 scripts/ownmachine-control.py --control-dir /shared/ownmachine-control status
touch /shared/ownmachine-control/session.lock
chmod 0660 /shared/ownmachine-control/lease.db /shared/ownmachine-control/session.lock
```

See the [complete Linux/Docker recipe and both-user checks](evaluator-quickstart.md#prepare-shared-control-before-starting-either-runtime).

Default directory ACLs alone do not ensure SQLite creates a group-writable
database. Verify both users can
read/write the lease and that the agent cannot read the viewer key or access
file. Never solve sharing by making private homes/tokens world-readable or by
mounting the entire viewer home. Containers must use restricted separate mounts
and only share the control volume; no Docker socket or host-wide home mount.

The shared lease is a cooperative coordination gate, not authorization against
arbitrary code that can edit that database. Isolating viewer credentials prevents
token/key theft; it does not turn writable shared state into a hostile-code
sandbox.

## Disable Hermes host execution

Fresh `install-hermes.py` profiles now set:

```yaml
agent:
  disabled_toolsets: [terminal, file, code_execution]
```

For existing profiles, add this with the supported Hermes configuration and
restart Hermes. Verify the effective model tool list has no terminal,
process-management, file-editing or code-execution tools; do not rely only on the
YAML. Use a dedicated profile without third-party tools/MCP servers that restore
host shell/file access. This is a model-tool restriction, not an OS sandbox.
A trusted operator can change the profile; arbitrary plugins run with Hermes's
OS permissions. A stronger deployment uses an isolated Hermes container with
only its agent key and required control volume, no viewer private state.

Native GUI tools remain available inside the guest through the agent-only MCP
role and standard permission mode. The guest is the intended work surface.

## Creation and manual launch boundaries

Patched unattended creation has no VNC listener during either first-boot
materialization or final SSH verification. `provision-vm.py` explicitly requests
`--verification-vnc disabled`; an unpatched binary rejects the option rather
than falling back to its weak default. The old `--verification-vnc-port` argument
is accepted for compatibility but is unused. Configure the required firewalls
before the first relay-managed VNC start after provisioning.

Manual `lume run` without `--vnc-password-file` still uses upstream's weak random
passphrase and may choose a random port. The relay refuses that unmanaged VM,
but **other local accounts can still reach its loopback listener**. Application
firewall blocking of external connections does not fix that. Use the relay, or
explicitly use `--vnc disabled` for manual/native sessions. The relay cannot police
commands run directly by the trusted Mac VM account.
