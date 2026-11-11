# OwnMachine v0.6.0 — security preview

Give your AI agent its own desktop. OwnMachine provides a persistent macOS VM
workspace for Hermes, restricted SSH/MCP transport and private browser streaming
with direct human input and coordinated human/agent handoff.

This is the first release in the recreated public repository. OwnMachine code
uses **PolyForm Noncommercial License 1.0.0**; third-party license notices remain
intact. Commercial licensing is available from the owner. This source-available
preview is not a stable release or an admitted Hermes catalog entry.

## Included

- Native Hermes computer-use provider, MCP forwarding, doctor and recovery tools.
- noVNC streaming, human reservation, pause/return and guest lifecycle controls.
- Mandatory fixed-port PF protection and blocked Lume application-firewall entry,
  checked through fresh root-owned readiness evidence.
- Locally built pinned Lume patch: protected-file VNC credentials with no password
  in detached argv; no VNC listener during unattended guest creation.
- Separate agent/viewer SSH keys and runtime accounts; private viewer tokens,
  no-follow credential file creation and restricted Hermes toolsets.
- Portable operator configuration, guided guest permissions, reproducible source
  and plugin bundles, checksums and per-file inventories.

Use the full-source archive for first-time onboarding. The plugin-only archive
does not install Lume, create a guest, configure SSH/firewalls or start the viewer.
Follow the host, guest and community setup guides included in the source bundle.
The patched Lume executable is built locally and is not included in these archives.

## Validation

The security code passed 229 Python tests across macOS and Hermes Linux runs
(207/219 passes respectively; 22/10 expected platform skips), four targeted Swift
security tests, real-Hermes contract and packaged-plugin validation, repeatable
bundles, fresh-home installation and synthetic offline upgrade.

Fresh dedicated-account guest installation completed without an ownership repair.
Guided permissions and capture consent passed through the browser. Native Hermes
and browser typing saved independently verified text. Human reservation blocked
agent input. Subsequent normal restart and shutdown/start preserved files and
permissions; the temporary unrestricted operator key was removed. See
[full acceptance evidence](security-hardening-validation.md).

Final artifact validation identifies the exact release merge commit separately
in the release assets. Checksums establish integrity against that inventory;
they are not signatures or proof of a trusted publisher.

## Preview limits

- One initial VNC-enabled guest boot hung and required a power-off after the
  shutdown timeout. Cause unknown; subsequent onboarding and two normal lifecycle
  checks passed. Do not assume unattended recovery or hide this initial failure.
- A newly created host account needed one desktop login to initialize its
  virtualization security state. Setup Assistant choices, admin firewall setup,
  guest permissions and host FileVault unlock/login remain operator steps.
- Independent ALF-only random-port coverage and physical reboot persistence of
  the new firewall/account arrangement were not verified in this security run.
- Manual Lume launches without the protected password-file option remain outside
  the hardened path and may expose a weak password to local loopback clients.
- Root, the dedicated Mac account and viewer runtime are trusted. The shared lease
  coordinates cooperating runtimes; it is not a hostile-code security boundary.
- Model-driven pixel-input acceptance remains deferred. The fresh security run
  used deterministic native-provider actions, not a new model-driven benchmark.
- VM backup/restore and fully automatic host/guest recovery remain outside MVP.

No Hermes community-catalog submission is included in this release.
