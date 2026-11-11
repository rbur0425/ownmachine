# Guided hardening and chat-progress acceptance

Test date: 2026-11-11. Implementation candidate: `70173d3`.
Hermes checkout: `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.
Private deployment paths, host identities, credentials and guest captures are
excluded from this report.

## Automated gates

- Current Hermes: 299 tests passed, zero failures and zero skips.
- `scripts/ci-check.py --require-hermes` passed: reproducible source/plugin
  bundles and checksums, isolated fresh-profile installation and upgrade,
  validation of source, packaged and installed plugins.
- Added tests cover nonblocking chat, duplicate calls, sender revocation,
  messaging failure before execution, cancellation and uncertain outcome state.
- Real subprocess pipes exercise authenticated heartbeat binding, sequence and
  elapsed bounds, final receipts, malformed events and SSH-process cancellation.
- Hardening fixtures check matching fresh-provision/custom-storage identity,
  VNC-disabled startup, preservation of unrelated SSH aliases, private logs,
  live effective sshd/shutdown verification, and absence of the recovery password
  from host process arguments. Guest utilities still receive their required
  secret arguments inside the guest; no stronger isolation claim is made.

## Live laptop checks

- Isolated loopback sshd rejected an arbitrary command. Actual Mac preflight
  reported insufficient space when free storage fell below the configured
  32 GiB minimum; that failure was imported through authenticated progress.
- With explicit approval, gracefully stopped and deleted only the laptop test
  guest. Retained its previous private recovery state in a separate archive.
- Free space increased from about 31 to 56 GiB. A fresh isolated Hermes profile,
  reviewed source/plan and separate restricted setup key successfully ran the
  actual Mac preflight. Runtime keys and their role restrictions were retained.
- Fresh macOS provisioning is being exercised through the real Hermes CLI and
  pinned SSH endpoint. Final guest results will be recorded before review.

## Remaining acceptance

The final `verify` stage still does not perform a computer_use screenshot or a
saved desktop task/readback. Guest consent remains manual. Setup-key retirement
is still an explicit manual operation; automatic retirement has its own unchecked
plan item. Phase 2 reminders remain unimplemented. No catalog submission or
production release is part of this change.
