# Permanent-service reboot acceptance

2026-11-10; baseline `253cac4e660d12c41caa6ab8d12836eebbb46112`.

Direct restricted SSH, persistent runtime mounts, private viewer token rotation
and shared-control persistence passed before reboot.

## Physical-host reboot follow-up — 2026-11-10

After operator restart/login, the guest remained stopped. Restricted SSH and
effective pre-start IPv4 VNC filtering passed. A test probe briefly occupied the
VNC port; startup refused, then passed after inspection and port release. This was
operator-assisted recovery, not an uninterrupted first-start pass.

Explicit guest startup retained a saved marker, permissions and native capture.
The browser tunnel was reopened manually; streaming and both handoff controls
passed. No unattended FileVault unlock, automatic VM startup, IPv6 filtering or
reboot of the separate Linux runtime host is claimed. Later security changes need
their own validation.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
