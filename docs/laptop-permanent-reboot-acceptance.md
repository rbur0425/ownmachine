# OwnMachine laptop permanent-service reboot acceptance

Baseline observed on 2026-11-10. Source pinned to
`253cac4e660d12c41caa6ab8d12836eebbb46112` (PR 22 merge). This follow-up changes
documentation only. Private deployment identities, addresses, keys, access links,
boot timestamps and guest screenshots are excluded. The separate dedicated Mac
host was not changed. Physical laptop reboot and operator-assisted recovery subsequently passed within the scope below.

## Permanent connection and firewall

The operator ran the reviewed administrator installer for the selected VNC port.
The OwnMachine firewall LaunchDaemon registered, ran once and exited zero. It is
a one-shot rule loader, so an idle/not-running state afterward is expected. Only
after replacement installation did the private deployment script unload the old
test service, retain its plist as a disabled file and flush its obsolete anchor.
The normal macOS Remote Login service was enabled; no FileVault setting changed.

The existing dedicated restricted public key was installed in the selected host
account's normal authorized-keys file. The normal SSH host key was read directly
from the laptop and pinned in the runtime configuration; no trust-on-first-use or
host-key bypass was used. Both Hermes and viewer use this same direct endpoint.
The fixed status command passed; an arbitrary `uname -a` command was rejected as
`unsupported_operation`. The old temporary listener and reverse SSH tunnel were
then stopped. Subsequent readiness checks passed without either process.

From a separate LAN machine, the selected VNC port timed out while restricted
SSH and a shared VNC handshake worked. This establishes the tested IPv4 path;
it does not claim an independent IPv6 firewall test or post-reboot persistence.

## Supervision and shared state

A separate viewer container now runs the viewer as its main process, with an init
process and an explicit `unless-stopped` restart policy. Source is a read-only
versioned export, not the mutable acceptance checkout. The dedicated Hermes
container also has that restart policy. Both retain their existing persistent
mounts and share the same control directory. Runtime user/home and restricted
SSH mount ownership were preserved. No production container was recreated.

A controlled viewer-container restart passed: the token rotated, the old token
returned HTTP 403, the new token authenticated and controller/generation/pending
state were unchanged. The browser access tunnel remains a separate client session;
it is not required for the service to run and must be reconnected after laptop
restart. The updated private link was opened for the operator.

## Guest baseline

Native Hermes doctor reported READY: guest reachability, Accessibility, Screen
Recording, final capture consent, driver and MCP passed. Combined viewer doctor
passed authenticated HTTP, vendored assets, dependencies and shared VNC handshake.
Warnings retained intentional paused control and the external-firewall check.
The existing container also emitted its pnpm artifact synchronization warning.

An initial window capture had no target because no eligible application window
was open. An explicit desktop capture then returned a valid 1456×920 PNG through
the native provider. This was a read-only capture, not a new model-input test.
A unique harmless guest persistence marker was saved and its SHA-256 recorded
privately, along with the host boot timestamp. No private document was copied.

## Reboot checkpoint

The operator confirmed all guest work was saved and authorized guest shutdown.
The lifecycle command returned `stopped`; a separate direct status probe confirmed
that state. The shared control gate is paused with no pending operation. No host reboot is performed by this baseline task.

After the operator restarts and logs in/unlocks FileVault, compare the host boot
timestamp, verify the renamed firewall before VNC startup, check direct restricted
SSH and confirm the guest remains stopped. Start the guest explicitly, compare
the persistence-marker hash, rerun native/viewer doctor and capture, verify the LAN
VNC restriction and browser stream, then test human/agent handoff. Record manual
steps separately from automatic recovery. Until then this is a pre-reboot baseline,
not a reboot pass.

Model pixel-click acceptance is deferred by the operator. The earlier capture
expiry remains a documented limitation; more explicit model instructions are a
possible aid, not a confirmed fix. VM backup/restore remains outside MVP.

Validation: 215 local Python tests (193 passed, 22 expected Hermes-only skips),
Node viewer pointer regression and fresh-profile Hermes plugin validation passed.
The PR's final-head CI is tracked separately in its checks and description.

## Physical-host reboot follow-up — 2026-11-10

The operator restarted the laptop and returned after login. Its boot timestamp
changed from the recorded baseline. The guest remained stopped, the direct
restricted SSH endpoint returned normally, and arbitrary commands were still
refused. Shared control remained paused with no pending action. The OwnMachine
firewall LaunchDaemon ran once after boot and exited zero without reinstalling it.

A privileged PF rule dump was unavailable without renewed administrator
authentication. Instead, before guest startup, an operator-owned temporary TCP
listener bound the configured VNC port on all IPv4 interfaces. A loopback client
received its harmless probe response while a separate LAN client timed out. The
listener was then closed. This checks effective pre-VM IPv4 filtering, not merely
the presence of a registered service; no IPv6 result is claimed.

The first guest start failed because the recently closed probe had left the port
unavailable to Lume. Logs explicitly reported the VNC port in use. The VM remained
stopped and the lifecycle gate marked the failed operation for review. After
inspection, an ordinary bind without address reuse succeeded, confirming the port
was free. The operator acknowledged the gate and repeated startup successfully.
This was a test-induced socket-lifetime conflict, not an uninterrupted first-start
pass. Future probes should ensure the peer closes first and verify the port can
be rebound before starting Lume; do not silently select an unprotected VNC port.

After explicit guest startup:

- The unique guest marker's SHA-256 matched the pre-reboot baseline.
- Native doctor reported READY, including both macOS grants, final capture
  consent, driver and MCP. No permissions were re-granted.
- Native desktop capture returned a valid 1456×920 PNG.
- The browser tunnel was reopened manually. Authenticated live noVNC streaming
  displayed the desktop; viewer doctor confirmed a browser stream and shared
  VNC handshake. Direct LAN IPv4 VNC access still timed out.
- Browser human reservation and return-to-agent both updated control and focused
  the selected button. Control was finally paused with no pending operation.

The VM is running. This closes renamed laptop service reboot acceptance for
operator-assisted login and explicit VM startup. It does not promise unattended
FileVault unlock, automatic guest startup or a reboot of the separate Linux
runtime host. Its viewer container stayed on that host throughout; container
restart persistence was tested separately in the baseline. The dedicated Mac
host was untouched. Private receipts remain outside version control.
