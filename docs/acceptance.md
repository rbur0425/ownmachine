# Acceptance overview

These are scoped observations, not a security certification or a promise that every
application, host or later commit works. Installation starts with the
[evaluator quickstart](evaluator-quickstart.md); security requirements are in
[SECURITY](../SECURITY.md). Historical reports below retain results and material
limits without publishing deployment inventories or raw operator logs.

## PR 15 evidence

| Area | Observed result and limit | Evidence |
| --- | --- | --- |
| Fresh Omarchy installation | Hermes-driven post-pairing setup, interruption/resume, hardening, screenshot and setup-key retirement passed without manual guest repairs. Trust/bootstrap and administrator steps remained explicit. | [Fresh install](omarchy-final-acceptance.md) |
| Omarchy model control | Chromium navigation and Mousepad save independently verified. First-run terms/keyring prompts required human handoff. Foreground native module required; background is experimental. | [Model tasks](omarchy-final-acceptance.md) |
| macOS common Lume patch | Fresh guest relay cold start and normal viewer passed; no credential export. Recovery configuration had regression coverage, not a hardware recovery boot. | [macOS run](macos-cold-start-acceptance.md) |
| macOS model control | Safari reached Google after operator-reviewed recovery; not an uninterrupted or background-only pass. | [macOS run](macos-cold-start-acceptance.md) |
| Security maintenance | Listing/log redaction, Linux cold start, combined firewall checks and optional guest-to-host SSH restriction passed. Later redaction build was not redeployed on the macOS test host. | [Maintenance](security-maintenance-acceptance.md) |
| Rolling update | Zero pending migrations after update/restart; signed repository/prerequisite repair was needed. Future rolling updates remain unqualified. | [Maintenance](security-maintenance-acceptance.md) |
| Automated checks | CI and package validation apply only to their exact commit. Use current PR checks, not an older report's test count. | [CI procedure](ci.md) |

## Earlier evidence and limits

- [Physical-host reboot](laptop-permanent-reboot-acceptance.md): operator login,
  explicit guest startup and manual browser-tunnel reconnection; not automatic
  FileVault unlock or universal reboot coverage for later changes.
- [Docker and reminders](docker-reminder-acceptance.md): actual scheduler delivery,
  session/chat nudges and independently verified Safari navigation.
- [Clean macOS setup](clean-candidate-acceptance.md) and
  [dedicated-account security setup](security-hardening-validation.md): historical
  clean-install evidence; retain the initial guest hang and manual consent limits.
- Model-driven pixel acceptance previously hit capture expiry and remains distinct
  from successful Accessibility tasks. Native password-dialog paste is not certified.
- Cloud hosts, broad application coverage, VM backup/restore and unattended host
  recovery are outside the certified scope. Plugin backups are not guest backups.

## Reproducing safely

Use a new disposable guest and private state, the reviewed source pin and the
current setup guides. Do not reuse another deployment's keys, runtime paths,
completed checkpoints or test approval settings. Verify model results independently
after the task; do not compete for capture ownership while it runs. Keep legal and
credential decisions human-controlled. Record failures and manual intervention,
restore normal approvals, and never publish private guest content as evidence.
