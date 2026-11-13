# Setup transport acceptance

2026-11-11; Hermes `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.

Actual SSH and Hermes CLI calls passed Mac preflight, authenticated progress
import and persisted status. Wrong host keys, arbitrary commands, replayed nonces,
wrong source/plan identities and unapproved stages were refused.

This was a read-only loopback SSH integration test on a real Mac, not a complete
remote installation. Later [Docker acceptance](docker-reminder-acceptance.md) and
[Omarchy guided acceptance](omarchy-guided-acceptance.md) cover cross-machine setup.
See [setup transport](setup-transport.md) for configuration and resume requirements.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
