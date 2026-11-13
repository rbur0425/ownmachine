# OwnMachine v1.0.1

Fixes local onboarding verification and idle gateway contention after v1.0.0.

- Local plans with an empty planning alias can verify using an explicitly configured
  runtime agent SSH alias. Other runtime/plan fields still match; acceptance binds
  the runtime configuration. Client capture failure explains that host checks passed
  but setup access has not been retired.
- Local and remote plans support explicit runtime connection configuration without
  changing their target to existing. The guides include the runtime settings and
  explicit `computer_use.backend: ownmachine` selection in the same Hermes profile.
- Cached backends connect lazily and lock only during an active operation. Another
  backend's operation invalidates previous capture targets before input. Human
  reservation and uncertain-write gates remain enforced.

## Upgrade and resume

Save active work and normally stop the affected Hermes gateway/sessions before
updating the plugin. Restart that gateway after installation: old loaded code can
retain its lifetime lock until it exits. **Do not delete `session.lock`.** A guest
recreation or host reboot is not needed for this patch.

Keep the existing setup plan, operator source pin, runtime settings and checkpoints.
For a local plan with an empty alias, configure the explicit runtime agent alias
without editing the plan. Follow the [runtime configuration checklist](wizard-quickstart.md#configure-the-runtime-before-final-verification).
The guest profile, VM name and shared control directory must match the saved plan.
Restart the matching profile after selecting the OwnMachine backend; never allow a
host-desktop provider to stand in for the guest.

Run `ownmachine doctor` and `ownmachine setup --next` in that profile. With agent
control paused (not reserved for human input), repeat `ownmachine setup --run verify`.
Once that succeeds, `ownmachine setup --run verify --apply` repeats verification and
retires only the configured temporary setup key. Host-side `checks_passed` alone is
not completion. Existing acceptance receipts predating runtime binding are not
reused as proof; if setup access was already retired, inspect status with the
operator rather than automatically restoring a key.

## Validation scope

The fixes reproduce the v1.0.0 alias mismatch and macOS lock failure in regression
tests. A separate-process test retains an idle backend while another captures and
refuses stale input. The fix gate passed 408 Hermes-aware tests with no skips,
source/packaged/installed validation, reproducible bundles, fresh-home installation
and offline upgrade. Release PR checks validate the final versioned tree. These
are isolated/package tests, not a new guest installation or model-task acceptance.
The macOS/Omarchy hardware scope and upgrade requirements in [v1.0.0 notes](release-1.0.0.md)
still apply, including the mandatory patched Lume/firewall protections.
