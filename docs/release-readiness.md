# Release readiness

PR 15 adds the tested Omarchy foreground configuration; macOS remains the default.
The candidate release is **on hold** pending explicit approval. A pushed review
branch or passing CI is not a published release or catalog admission.

## Before promotion

- Validate the exact candidate commit with the [CI/package procedure](ci.md),
  including Hermes plugin validation, bundles and checksums. Later changes require
  fresh validation; do not reuse an older head's green checks.
- Review the [acceptance overview](acceptance.md) and its limitations. Fresh
  installation and model task results have different scopes from historical host
  reboot tests. No new reboot is implied by documentation changes.
- Follow [release upgrade notes](release-0.8.0.md): rebuild patched Lume, save work,
  shut down, never resume old saved state, cold-start through the relay and verify.
- Keep source, dependency provenance, license, screenshots and catalog pins
  consistent. [Catalog preparation](catalog/README.md) remains separate from
  upstream approval. Do not claim an accepted listing without that approval.
- Use Gitflow: feature PR into `develop`, release PR into `main`, validate/tag and
  attach artifacts, then synchronize back to `develop`. Do not publish early.

## User-facing limits to retain

Administrator firewall setup, verified SSH pairing and guest permissions remain
explicit handoffs. First-run browser terms/keyring prompts may need the operator.
Host unlock/login and explicit VM startup may be necessary. Native protected-
password paste, general model pixel reliability and cloud hosts are not certified.
Background Omarchy input is experimental and application-limited; rolling upgrades
may require a reviewed module rebuild. VM backup/restore is outside the MVP.

See the [evaluator guide](evaluator-quickstart.md), [security requirements](../SECURITY.md)
and [submission handoff](submission-handoff.md) for the relevant procedures.
