# Guided hardening and chat-progress acceptance

2026-11-11; Hermes `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.

Fresh macOS provisioning through Hermes and pinned SSH passed. Supervised chat
ran hardening and driver stages with authenticated progress. Independent checks
confirmed key authentication, password rotation and disabled password SSH; a
second hardening invocation rechecked postconditions. The permission guide opened
and correctly waited for manual consent.

The Hermes-aware gate passed 300 tests with zero skips. Coverage included sender
revocation, duplicate calls, bounded heartbeats and uncertain outcomes. These
counts describe that historical revision, not the current head. Screenshot and
key retirement were completed in the [subsequent run](verification-retirement-acceptance.md).

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
