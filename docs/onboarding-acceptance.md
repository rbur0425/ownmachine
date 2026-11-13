# Onboarding command acceptance

2026-11-11; initial command and saved-plan implementation.

Real Hermes terminal and slash-command paths passed wizard preview/save/decline,
missing-input handling, persistent plan state and doctor refusal for incomplete
configuration. Tests covered approved configuration writes, replacement refusal,
sender limits and stale progress. No privileged action was implied by saving a plan.

The Hermes-aware gate passed 241 tests with zero skips at that revision. Initial
manual execution and reminder gaps were addressed by later increments; use the
[current wizard](wizard-quickstart.md), [transport guide](setup-transport.md) and
[reminder guide](onboarding-reminders.md) for current behavior.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
