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
