# Security model and reporting

OwnMachine is a development preview for one trusted operator and one configured VM.
It is not a public remote-desktop service, multi-tenant sandbox or audited secret
vault. Report vulnerabilities through a private channel offered by the repository
host/maintainer. If none is available, request a private contact without posting
an exploit, credentials or desktop data in a public issue. No dedicated security
contact or response-time commitment is currently published.

## Boundaries

- The Hermes plugin runs with standard permission mode. Host and operator scripts
  stay outside the installable plugin. The model receives bounded status/errors,
  not VNC passwords, viewer links or control-transfer tools.
- A verified SSH alias reaches a forced-command relay for one configured VM.
  The relay rejects arbitrary commands/destinations. The owning Mac account can
  alter its relay, configuration and VM, so it is a trusted operator boundary.
- Guest GUI control uses the signed standard-mode driver and manually granted
  permissions. No script approves TCC or bypasses capture consent.
- Browser access is a bearer capability in a private owner-only access file.
  Possession permits viewing, input while human-reserved, control transfers and
  lifecycle operations. The initial fragment is exchanged for an HttpOnly,
  SameSite=Strict session cookie. Viewer restart rotates the capability.
- HTTP binds numeric loopback. SSH protects remote transport. Do not publish the
  port, add an unauthenticated reverse proxy, or expose the VNC socket. Host and
  origin checks complement authentication; they do not replace it.
- VNC requires a fixed unprivileged port and fresh root-owned evidence of active
  PF and application-firewall blocking. The relay checks matching managed VNC
  credentials and refuses stale/missing evidence. Confirm external blocking and
  local relay access, including after boot; a localhost URL alone is not proof.
- The bridge authenticates upstream VNC inside SSH and never sends the VNC
  password to JavaScript. Server-side RFB parsing and the shared lease gate
  key/pointer events, not merely noVNC's view-only UI. Clipboard synchronization,
  file transfer and privileged client extensions are refused.
- A held key/button keeps its transaction until release. Failed writes retain an
  uncertain-outcome marker, never auto-replay. Human handoff waits for existing
  writes; it cannot recall an already-dispatched event. Separate lease databases
  break coordination. All writers must share one underlying control directory.

## Local data and trusted access

The VM disk may contain browser sessions, documents and passwords. Guest login,
Mac login, filesystem permissions and backups remain operator responsibilities.
Autologin is convenient but increases access for anyone who can reach the guest.
Do not distribute VM images, Lume runtime files, access JSON, private keys, raw
logs or desktop captures as support/CI artifacts. Protect backups like the VM.

Local code running as the viewer or host owner is trusted; it can read the bearer
capability or bypass application-level controls. Raw SSH/VNC credential holders
are also trusted operators. The human gate coordinates cooperating writers; it
is not isolation against a compromised host account or privileged local malware.

The viewer stores no captures itself and suppresses request logging. noVNC source
and licenses are vendored; PyCryptodome is pinned only for legacy VNC challenge
compatibility inside the SSH path. Neither performs runtime self-updates. Review
[dependency provenance](viewer/VENDOR.md) and keep pinned upgrades reviewable.

## Safe diagnostics

Native doctor does not read the viewer token. The separate operator viewer doctor
reads it only to query the local authenticated endpoint and never prints it. Its
optional shared VNC probe sends no desktop input/capture request. Reports are
sanitized, but inspect any additional host logs before sharing them. See the
[recovery guide](docs/recovery.md) for uncertain actions and failed connections.

## Hardened deployment

Follow [identity separation](docs/security-isolation.md): separate agent/viewer
SSH keys and runtime users, private viewer-access state outside shared control,
a dedicated Mac VM account, private VNC credentials/logs and disabled Hermes
host-execution tools. The status attestation has a bounded freshness window;
root or the Mac VM account is still trusted. The application firewall does not
replace local-user isolation. The v0.6.0 preview includes these changes.

VNC passwords must never appear in command-line arguments: ordinary local macOS
accounts can inspect another user's process argv. The locally built Lume patch
accepts only a protected-file path from the relay, including detached children;
the secret remains in a 0600 file under private host state. The 66-character
URL-safe alphabet avoids upstream unescaped VNC URL parsing failures. Stock Lume
without `--vnc-password-file` is not compatible with hardened viewer starts.

### Host VNC credentials stay outside the guest

OwnMachine's common Lume patch removes the automatic `lume-config` VirtioFS
credential share and the fallback SSH copy to the guest home for both macOS and
Linux. Host-local session state remains private to the dedicated host account.
This is independent of the Linux-only clipboard/audio/share isolation patch.

After updating an older build, shut down the guest normally and cold-start it
through the configured relay: the relay generates a new private VNC password on
each start. Do not resume a saved VM state made with the old credential-sharing
device configuration. Old guest or temporary-host copies are not retroactively
erased by the patch; password rotation makes those copies unusable. Do not
manually configure a share of the host credential/state directory.
