# Setup service acceptance

2026-11-11; Hermes `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.

The Hermes-aware suite passed 276 tests with zero skips at that revision.
Real OpenSSH pairing, fixed command restrictions, current firewall readiness,
isolated viewer service startup and authenticated browser checks passed.
Temporary services were cleaned up without changing the existing guest.

These were component/integration checks, not a complete fresh guest installation.
Later [hardening](guided-hardening-acceptance.md) and [verification](verification-retirement-acceptance.md)
runs cover the remaining stages. Use the [wizard](wizard-quickstart.md) for current
configuration rather than historical fixture paths.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
