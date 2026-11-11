# Setup service increment acceptance — 2026-11-11

This increment follows merged PR #5. It does not claim a fresh, end-to-end
Hermes-driven Mac installation. The complete gap ledger is in
[the onboarding plan](onboarding-plan.md#reviewed-gap-ledger--after-pr-5).

## Checks performed

- Current Hermes source `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`: 275 tests
  passed, zero skips, using its isolated Python environment.
- Standalone suite: 275 tests, 252 passed and 23 expected Hermes-only skips.
- `hermes plugins validate plugin --install-deps` passed; install security scan
  safe. Command inventory is advisory because this Hermes revision registers
  commands through the public APIs, not a manifest command-loading field.
- Actual OpenSSH pairing in temporary homes: generated a fresh Ed25519 client
  key, confirmed a supplied host fingerprint, installed private pinned host-key
  and client configuration, inspected effective `ssh -G` settings, resumed
  without duplicating Includes and refused a mismatched fingerprint. No network
  host was trusted by scanning, and no existing SSH configuration was modified.
- Real laptop firewall probe: the fresh root-owned PF/ALF status passed, and
  querying the actual protected Lume app confirmed its incoming block. No root
  installer was rerun. This is not an external-network firewall test.
- Real Mac user-service test in an isolated temporary home: installed and started
  the generated viewer LaunchAgent with pinned viewer dependencies, verified the
  authenticated loopback viewer and 0600 access file, then reapplied the same
  stage and observed verification without replaying installation.
- Browser verification of that isolated viewer: authenticated page loaded;
  Reserve for human use changed control to human and retained button focus;
  Return to agent changed control to agent and retained that button's focus.
  The fixture intentionally had no guest backend, so its stream was disconnected.
  This proves service/authentication/control UI behavior, not VM streaming/input.
- Cleanup: unloaded only the temporary test LaunchAgent, closed its browser tab,
  confirmed the service was absent, its listener closed and access file removed.
- Read-only status from the existing laptop acceptance runtime reported the
  existing VM stopped. No existing guest was started, stopped, replaced or
  deleted; no existing runtime key, driver, grant or service was changed.

## Focused regression coverage

Tests cover custom-storage arguments in status/MCP/lifecycle/VNC; configured-app
firewall checks; explicit preview vs apply; installation collision refusal;
private checkpoints and failed-step refusal; preserving unrelated authorized_keys
entries; refusing unrestricted duplicate/public-key reuse; fixed reviewed driver
archive contents and strict guest SSH; consent readiness without granting TCC;
portable LaunchAgent rendering; separate viewer access state; and sanitized
progress-event fields.

## Still required

A complete fresh local and remote installation must run from Hermes, import only
authenticated progress, finish guest hardening and permission consent, and verify
actual guest capture, browser typing/clicking, restricted role denial, external
firewall coverage and a saved desktop task result. Those are not replaced by
unit tests or the isolated viewer exercise above. Linux systemd installation is
rendered and fixture-tested; its live user-service acceptance remains pending.
