# Omarchy security regression acceptance

2026-11-12; PR 15 common-patch and managed-hardening changes.

The common Lume patch removed automatic VNC credential exports to both guest
profiles. Clean common/macOS and Linux builds passed patch, signature and CLI
checks. Swift regression exercised normal and recovery configuration builders;
this alone was not a hardware boot. Separate [macOS cold-start evidence](macos-cold-start-acceptance.md)
and [fresh Omarchy evidence](omarchy-final-acceptance.md) cover live operation.

Negative checks confirmed managed graphical startup and driver operations refuse
missing or untrusted hardening state; verified hardening restored readiness.
Regression tests cover unsafe metadata, failed live policy and reintroduced
unrestricted sudo. Guest root remains trusted and can alter its own policy.

The Hermes-aware suite passed 396 tests with zero skips at that revision. Linux
0.47.19 provenance was reverified; pin/identity and upgrade policy remain in the
[plan](omarchy-plan.md) and [release notes](omarchy-release-candidate.md).
Existing users must rebuild, shut down and cold-start through the relay; never
resume a pre-update saved state. See [security requirements](../SECURITY.md).

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
