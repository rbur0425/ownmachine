# Onboarding coordinator acceptance — 2026-11-11

Scope: the first phase in [the onboarding plan](onboarding-plan.md). No live VM,
firewall, permission grant, runtime account or viewer deployment was changed.
This is command/configuration acceptance, not fresh infrastructure acceptance.

## Real Hermes checks

Tested against Hermes source `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`, using
isolated temporary homes and its locked Python environment.

- `/ownmachine setup` resolves through Hermes's real slash-command registry.
  It returns setup questions or the saved plan without reading stdin. The same
  route works under default plugin-host isolation and explains the explicit
  in-process prerequisite. `/ownmachine doctor` reports missing configuration.
- `hermes ownmachine setup --json` returns `needs_input` and exit 2 in an empty
  dedicated profile, without saving settings or contacting a host.
- `setup --target remote --memory-gb 12 --save --json` saves a plan. A separate
  process resumes it with the selected memory value intact.
- `hermes ownmachine doctor --json` returns `invalid_configuration` and exit 1
  for the unconfigured profile. Its configuration file remains byte-identical.
- A real terminal/PTY run exercised the question prompts, preview and decline
  path with example settings. It created no VM or control directory.
- Unit checks cover explicit existing-relay connection writes, replacement refusal,
  recovery from a failed configuration write, missing/noninteractive input,
  invalid values, local incompatibility/low space and no remote-capacity inference.

## Issues discovered during implementation

Hermes infers plugins mentioning the computer-use provider contract as exclusive
provider entries, skipping general command discovery. An explicit supported
`kind: standalone` makes the operator commands discoverable before selecting a
provider. Existing native-provider discovery remains intact and is regression-tested.

Default `plugins.isolation: host` skips CLI registration and refuses the live
native provider. The chat path remains available. The user must explicitly select
`plugins.isolation: in_process` in a dedicated profile; setup does not alter core
isolation or unrelated profile settings. This prerequisite remains an onboarding
friction point to explain, not hide or work around by patching Hermes.

## Limits and next acceptance

Saved state represents a plan, not execution checkpoints or completed setup.
Remote hardware/build-tool checks, privileged bootstrap, guest provisioning,
viewer service setup and verified resume of those actions belong to Phase 2.
The new doctor command reuses the existing bounded read-only diagnostics engine;
this run does not establish new live-VM readiness or new security reboot evidence.

The catalog draft remains pinned to the earlier reviewed preparation commit.
After the onboarding work is merged and accepted, select a new submission pin,
repeat catalog validation and update same-SHA screenshot URLs. Nothing was
submitted upstream by this work.

## Final candidate results

Runtime candidate: `cd95f4721fe45f39e3d5d76c3f2ea449d07d3c62`.

- Current-Hermes macOS suite: **241 passed, zero skips/failures/errors**.
- Standalone macOS suite: **218 passed, 23 expected Hermes-only skips**. The added
  skip is the real-Hermes command/discovery test, explicitly tracked in the test
  coverage policy; it ran and passed in the Hermes-enabled suite.
- Required-Hermes CI gate passed: repeatable bundles, source/extracted/installed
  plugin validation, fresh-home installation and synthetic offline upgrade.
- Security scan: safe. No core runtime overrides detected. The validator's
  host-isolation CLI-skipping note is disclosed above and separately tested.
- Node viewer pointer regression and Git whitespace checks passed.

A separate fresh home then installed the public Git URL with `#plugin` and the
full candidate SHA using `hermes plugins install --yes-deps --enable`. After the
explicit dedicated-profile isolation choice, the actual CLI successfully ran:
empty setup, saved remote plan, resume in a new process, read-only unconfigured
doctor, existing-relay connection configuration and installed-package validation.
Example-only connection settings were used; no real SSH keys were supplied. The
control directory was not created. This test proves command installation and
configuration behavior, not a new live guest deployment.

## Tentative-plan review additions

Added profile-scoped durable progress using public `ctx.state`, separate from
user-editable configuration. Real-Hermes tests verify the state file is 0600,
status preserves its bytes and timestamps across new processes, and setup resumes
the saved plan. Plan/connection changes invalidate old progress. Corrupt or future
state is preserved; failed checkpoint writes can be retried without claiming that
provisioning completed. Existing plan-only settings remain readable.

Added a no-network `status` command in chat and CLI. State distinguishes waiting
for host setup, waiting for verification and blocked preflight. It never marks
onboarding complete. Doctor remains read-only and does not create success records.

Chat mutation tests verify missing identity, wrong platform and wrong chat are
rejected before any config/state write. Only exact operator-configured platform,
user and chat IDs permit save/connect. Local CLI setup remains available without
transport identity. No owner IDs are hardcoded and no new model-facing write tool
is registered. Preview/status/doctor behavior is unchanged by this mutation gate.

No reminder, cron job, remote bootstrap privilege or new guest OS was added. The
plan documents explicit reminder opt-in and the separate setup-authorization path.

Updated runtime candidate `664060cb2b1abe98cdfaa8d6072fc3417d62c31d` passed
**250 current-Hermes tests with zero skips**, the full required-Hermes package/
bundle/fresh-home/synthetic-upgrade gate, and safe plugin validation. Standalone
macOS ran 250 tests: **227 passed, 23 expected Hermes-only skips**. The Node
pointer regression also passed. macOS-only presentation and rejection of OS/image
selector flags are covered. The full opt-in reminder lifecycle and tests are in
the plan; reminder execution remains unimplemented and no messages were scheduled.
