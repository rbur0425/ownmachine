# Guided hardening and chat-progress acceptance

Test date: 2026-11-11. Host-side implementation candidate: `70173d3`; chat delivery handling and final
code validation: `5e1a976`. The host-side scripts did not change between these commits.
Hermes checkout: `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.
Private deployment paths, host identities, credentials and guest captures are
excluded from this report.

## Automated gates

- Current Hermes: 300 tests passed, zero failures and zero skips.
- `scripts/ci-check.py --require-hermes` passed: reproducible source/plugin
  bundles and checksums, isolated fresh-profile installation and upgrade,
  validation of source, packaged and installed plugins. Catalog-style validation
  with `--install-deps` also passed. Reviewed warning: live message handles require
  a dedicated `in_process` profile; host-mode/unavailable delivery refuses remote
  execution and gives a terminal fallback. Advisory manifest command inventory
  remains ignored by Hermes; public command registration is exercised instead.
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
- Fresh macOS 26.6.2 provisioning passed through the real Hermes CLI and pinned
  SSH endpoint, using the selected storage path and a VNC-disabled installer.
- The real Hermes slash handler and supervised task API ran `harden` and `driver`
  over the actual restricted SSH endpoint. Message delivery was recorded locally
  through a test double for the public message API; no external chat was contacted.
  The handler returned immediately, authenticated heartbeats appeared during
  hardening, and both final receipts reported verified outcomes.
- Independent host observations confirmed key authentication, password rotation,
  disabled password SSH, aligned autologin/keychain, a 0600 recovery file, a 0700
  Lume directory, and no recovery password in host process arguments. Bootstrap
  VNC stayed disabled. No directory-ownership repair was needed.
- A second real Hermes `harden --apply` reverified live postconditions without
  changing the recovery file's inode, modification time or size. It did not rotate
  the password or repeat provisioning.
- An explicit operator relay restart succeeded through the existing required
  firewall checks and enabled the protected VNC session. This was an operator
  lifecycle call, not a new runtime-key role-separation acceptance test.
- The real `permissions --apply` stage opened the installed guide and correctly
  imported `needs_attention`: this new guest has not received its manual TCC
  grants. Full onboarding/screenshot acceptance remains open.

## Remaining acceptance

The final `verify` stage still does not perform a computer_use screenshot or a
saved desktop task/readback. Guest consent remains manual. Setup-key retirement
is still an explicit manual operation; automatic retirement has its own unchecked
plan item. Phase 2 reminders remain unimplemented. No catalog submission or
production release is part of this change.
