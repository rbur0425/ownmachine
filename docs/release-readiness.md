# Release readiness

The v1.1.0 release adds Windows 11 Enterprise Evaluation on Linux KVM alongside
macOS and ARM64 Omarchy on Apple Silicon. Release publication requires explicit
approval and final-commit validation. A prepared branch is not a published release.

## Before promotion

- Validate the exact candidate commit with the [CI/package procedure](ci.md),
  including Hermes plugin validation, bundles and checksums. Later changes require
  fresh validation; do not reuse an older head's green checks.
- Review the [acceptance overview](acceptance.md) and its limitations. Fresh
  installation and model task results have different scopes from historical host
  reboot tests. No new reboot is implied by documentation changes.
- Follow [v1.1.0 release notes](release-1.1.0.md) and platform-specific maintenance
  instructions. Existing Lume security requirements remain in force; Windows
  relay updates do not migrate configuration or update the guest driver.
- Keep source, dependency provenance, license, screenshots and catalog pins
  consistent. [Catalog preparation](catalog/README.md) remains separate from
  upstream approval. The plugin is already listed, but a new release pin still needs review.
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

Windows support is bounded by the [platform/input matrix](windows-support-matrix.md).
Physical Linux-host reboot qualification was explicitly skipped. Home/Pro and
arbitrary configuration migrations remain outside this release.
