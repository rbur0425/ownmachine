# OwnMachine v0.8.0 — catalog security fixes

This minor preview release addresses the Hermes catalog review of v0.7.0.
It supports the existing macOS guest workflow. **Omarchy support is not included**;
that feature remains in a separate development PR. The PolyForm Noncommercial
License 1.0.0 and existing manual setup requirements are unchanged.

## Changes

- Both setup SSH children inherit only PATH, HOME, SSH_AUTH_SOCK and LANG.
  The setup-key retirement probe additionally fixes LANG and LC_ALL to C.
- Reminder scheduling CLI children receive only PATH, HOME, LANG and the owning
  profile's HERMES_HOME. Provider credentials and Python injection variables are
  not forwarded. Hermes must be installed in its running Python environment.
- Screenshot verification declares Pillow>=11.0.0,<14. Missing Pillow produces an
  actionable error and does not permit capture acceptance or setup-key retirement.
- Updated dependency disclosures and regression tests for real child environments
  and missing-dependency failure handling.

## Upgrade and verification

Use the [upgrade guide](upgrading.md) and [evaluator quickstart](evaluator-quickstart.md).
Install the release plugin with its declared dependencies in the intended Hermes
profile, then restart that profile to load the updated code. Existing VMs and host
firewall configuration are not recreated by this update. No host or guest restart
is required solely for these plugin fixes.

If a saved setup plan is bound to a previous source fingerprint, explicitly review
and update the matching operator source/configuration before resuming setup. Do not
bypass source/plan binding or reuse stale completion records.

The five added regressions fail on the catalog-reviewed base and pass with the
fix. The Hermes-aware suite has 345 tests with zero skips. Exact-release validation,
package inventories and checksums accompany the release. Existing in-process/CLI
validator notices remain disclosed. No new hardware acceptance is claimed.

This remains a single-operator preview. Administrator firewall setup, verified SSH
trust, guest permission grants and legal/credential prompts remain human steps.
Catalog acceptance requires a separate maintainer decision; this tag is not proof
of admission. See [SECURITY](../SECURITY.md) for the existing trust boundaries.
