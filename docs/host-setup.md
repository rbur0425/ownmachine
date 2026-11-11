# Operator host setup

This guide installs the readiness relay. Optional native desktop
control is configured separately in [native provider setup](native-provider.md). All example identities must be replaced with your own.

## Install Lume on the Mac

Copy the source to your dedicated, non-root Mac account and run:

```sh
/bin/bash scripts/install-lume.sh
"$HOME/.local/bin/lume" --version
"$HOME/.local/bin/lume" config telemetry status
```

The installer pins 0.7.0, verifies its published SHA-256 and Cua signing identity,
and installs only into your account. It refuses existing installations. Telemetry
is disabled before first invocation and persistently afterward. It does not create
VMs, start an HTTP server, or change your login services or shell profile.

## Hardened browser runtime

The vendor install above supports provisioning and native use. Hardened browser
VNC additionally requires the protected-password-file build from
`scripts/build-native-lume.sh`; set `lume_path` to its executable and register
that app with the firewall. See [security isolation](security-isolation.md).
A stock binary is refused rather than exposing the VNC password in argv.

## Install the relay

```sh
mkdir -p "$HOME/.local/lib/ownmachine" "$HOME/.config/ownmachine"
cp host/ownmachine_host.py "$HOME/.local/lib/ownmachine/ownmachine_host.py"
```

Optional `~/.config/ownmachine/host.json` selects one permitted VM and custom binary:

```json
{"vm_name": "ownmachine", "lume_path": "/absolute/path/to/lume"}
```

Omit `lume_path` to discover the per-user install or standard Homebrew locations.
Omit the config file for default VM name `ownmachine`. Keep this file private to the
operator account. No shell command or destination is accepted from model input.

Generate a dedicated SSH key on the machine running Hermes using your normal
SSH tooling. Install only its public key on the Mac. Restrict that public key's
`authorized_keys` entry to the relay, using your actual Python and relay paths:

```text
restrict,command="/absolute/path/to/python3 /absolute/path/to/ownmachine_host.py --role agent" ssh-ed25519 PUBLIC_KEY YOUR_COMMENT
```

By default this accepts only `ownmachine-host status --vm YOUR_CONFIGURED_VM`.
Explicit `enable_mcp: true` also enables the fixed MCP relay for the same VM. Arbitrary commands,
PTYs and forwarding are not enabled. The account owns the relay; this does not
isolate it from other code already running as the same Mac user.

Use a second key owned by a separate viewer runtime user with `--role viewer`.
It permits status/VNC/lifecycle and refuses MCP; the agent key refuses VNC and
lifecycle. See [mandatory separation setup](security-isolation.md).

For the browser desktop, continue with the [noVNC onboarding steps](community-setup.md#set-up-the-novnc-browser-desktop).
Explicit `enable_vnc: true` permits the fixed VNC relay for this VM. Complete the
administrator firewall setup before enabling its listener; SSH forwarding is
still disabled on the restricted key.

## Configure the Hermes-side SSH client

Verify the Mac host key through a trusted channel before recording it. In the
SSH config of the account actually running Hermes:

```sshconfig
Host ownmachine-host
  HostName YOUR_MAC_HOSTNAME
  User YOUR_DEDICATED_MAC_ACCOUNT
  IdentityFile ~/.ssh/YOUR_OWNMACHINE_KEY
  IdentitiesOnly yes
  StrictHostKeyChecking yes
  BatchMode yes
  ForwardAgent no
```

First identify the actual Hermes runtime account and its passwd home using
[persistent installation](permanent-installation.md#1-verify-the-actual-runtime-account).
For Docker, make this configuration and key available through operator-managed
persistent mounts accessible to that account. Do not assume the default exec
user or an example username matches your deployment. Do not copy private keys into the plugin or commit them.
Test from that same runtime account:

```sh
ssh -T ownmachine-host ownmachine-host status --vm ownmachine
```

Expected after installation: `lume_installed: true`; `vm_state` is `absent` until
the configured guest exists, then `provisioning`, `stopped`, or `running`.
Unexpected listings or failed probes return `unknown`. Other VM metadata is omitted.
A separate test such as `ssh -T ownmachine-host uname -a` must be refused.

## Optional guest readiness probe

After the guest is secured and its host key is verified, add a dedicated alias in
this Mac account's `~/.ssh/config` (replace every placeholder):

```sshconfig
Host ownmachine-guest-probe
  User YOUR_GUEST_ACCOUNT
  IdentityFile /absolute/path/to/guest-key
  UserKnownHostsFile /absolute/path/to/verified-guest-known-hosts
  HostKeyAlias YOUR_STABLE_GUEST_KEY_NAME
  IdentitiesOnly yes
  StrictHostKeyChecking yes
  BatchMode yes
  ForwardAgent no
```

Set `"guest_ssh_alias": "ownmachine-guest-probe"` in the existing host JSON object.
Keep keys and SSH configuration outside the source repository. The relay gets
only the selected VM's current address from Lume and overrides HostName for that
one connection; it never accepts a destination from the model. A stable verified
HostKeyAlias is required to preserve guest identity across DHCP changes. The
fixed guest command reads `cua-driver permissions status --json` from the desktop
user's per-user install. It never clicks, captures, starts the persistent daemon,
or opens consent prompts (Cua may briefly launch its non-prompting status probe).

`driver_state` distinguishes `not_configured`, `vm_not_running`,
`guest_unreachable`, `invalid_response`, `permissions_required`,
`capture_consent_required`, `not_running`, and `ready`. `driver_ready` requires
an active daemon, both TCC switches, and recorded direct-capture consent under the
signed driver identity. `capture_consent_verified` is historical verification,
not proof that a new screenshot or future action will succeed. Re-run the guided
capture check if capture fails. Driver errors, guest addresses, paths, and VNC
credentials are excluded from the result. SSH is noninteractive with host-key
verification; guest probing times out after eight seconds and never retries.
Without an alias, the original host-only status behavior remains available.

## Next stage

Follow [VM setup](vm-setup.md) to provision one guest with a disk budget appropriate to your host. Rotate preset
credentials, establish key authentication, install signed Cua Driver inside the
guest, and grant its GUI permissions manually. The restricted relay in this
version provides no VM creation. See native-provider setup for opt-in MCP forwarding.
