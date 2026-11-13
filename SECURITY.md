# Security and reporting

OwnMachine is for one trusted operator and one configured VM. It is not a
multi-tenant service, hostile-code sandbox or audited secret vault.

Report suspected vulnerabilities through the repository host's private reporting
channel if available. Otherwise request a private maintainer contact without
posting exploit details, credentials or desktop data in a public issue. No
response-time commitment is currently published.

## Requirements for safe installation

- Use a dedicated non-admin Mac VM account and separate agent/viewer runtime users
  with distinct restricted SSH keys. Verify host keys independently. Keep the
  temporary setup identity separate and retire it after verification.
- Install the reviewed patched Lume build and mandatory PF/application firewall
  rules for its exact app path and configured fixed port. Never expose VNC or the
  viewer publicly. Verify external blocking and private relay access after updates
  and host reboot. A localhost URL does not establish network isolation.
- Keep viewer access state outside shared control, in its private owner-only
  directory. All cooperating writers must use one underlying control directory;
  check access as both actual runtime users before starting either service.
- Disable Hermes host terminal/file/code tools in the dedicated profile; check the
  effective tool list and avoid other tools that restore host execution. Profiles
  alone do not isolate OS files. Do not mount the viewer home or Docker socket into
  the agent container.
- Approve macOS Accessibility, Screen Recording and capture consent inside the
  guest through the normal guide. No host-desktop permission or consent bypass is
  required. Omarchy managed startup requires verified guest hardening.

Follow the [evaluator quickstart](docs/evaluator-quickstart.md) and
[identity, firewall and permissions guide](docs/security-isolation.md) for commands.
Do not weaken permissions or skip failed checks to complete installation.

## Boundaries and limitations

The VNC listener binds all interfaces; PF and application firewall rules restrict
reachability. Readiness evidence is periodically refreshed, not an atomic guarantee
against privileged firewall changes. These rules do not isolate every host service.
The [optional guest-to-host SSH restriction](docs/linux-development.md#maintenance-and-host-service-isolation)
requires selecting the actual bridge/port and testing authorized remote access.

The host account, viewer account and root are trusted. Same-account code can read
private credentials or change configuration. The shared human-control gate
coordinates cooperating clients; it is not protection from arbitrary code with
write access to its database. A handoff cannot recall input already dispatched.
Uncertain writes require inspection; never blindly replay them.

Viewer access links are bearer credentials. Keep them private, use the supported
SSH transport and do not add a public proxy. The viewer does not send host VNC
passwords to browser JavaScript. The managed relay uses private password files;
normal Lume output is redacted, but explicitly requested private output must not
be logged. Manual unmanaged Lume launches are outside the hardened path.

## Upgrades and sensitive data

After upgrading an older Lume build, save guest work, shut down normally, then
cold-start through the relay to rotate credentials. **Never resume an old saved
state** with the former credential-sharing configuration. Old copies are not
erased automatically; do not share host credential directories with the guest.
Follow the [candidate upgrade requirements](docs/release-1.0.0.md).

VM disks and backups can contain logins and documents. Keep credentials, viewer
links, runtime configuration, private installer images, raw logs and private
captures out of issues, Git and CI artifacts. Inspect diagnostics before sharing.
A disclosed secret must be revoked or rotated; removing a file from Git is not
revocation. See [recovery](docs/recovery.md), [dependency provenance](viewer/VENDOR.md)
and the scoped [acceptance overview](docs/acceptance.md).
