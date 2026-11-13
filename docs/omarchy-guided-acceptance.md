# Hermes-driven Omarchy installation acceptance

2026-11-12; earlier PR 15 guided-install run.

After explicit source/image/key/firewall preparation, Hermes drove private
installer boot, base/desktop installation, hardening, relay/driver/viewer setup,
screenshot verification and setup-key retirement. An intentional timeout during
base installation followed by a Docker restart demonstrated authenticated progress
import and completed-checkpoint re-observation without reinstalling.

A real-model desktop task passed. Bounded native GTK background keyboard checks
also passed, but Chromium/Electron background and general background pointer/drag
remain unsupported. Foreground is the default; the optional module must match the
compositor ABI. Uncertain operations require inspection, not automatic replay.

The later [fresh security-build run](omarchy-final-acceptance.md) supersedes this
installation baseline. See [setup transport](setup-transport.md) for safe resume
instructions rather than reproducing this historical test harness.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.


## Fresh Hermes installation follow-up

2026-11-12; tested plugin commit `5998565a727cdaeb21beb4f4f4d959fa855ba641`
with Hermes v0.23.1 (upstream `3b421578`). Two disposable Docker instances used
empty Hermes homes; installation used `hermes plugins install` with an immutable
Git ref, dependency installation and enablement. No existing Hermes state, model
credentials, viewer key or Python import-path override was supplied. Operator-owned
agent SSH credentials and shared control state were explicitly reused.

- Empty-state setup/doctor produced actionable configuration guidance. Saved plans
  survived separate CLI invocations; setup stopped at the required pairing handoff.
  Guide links used the tested source pin.
- Next-visit reminders required preview/confirmation, persisted and could be
  disabled. Missing scheduled-delivery configuration created no job. No external
  reminder was sent during this run.
- The first run exposed an absent-guest diagnostic incorrectly reported as a host
  connection failure. The tested commit preserves nonrunning VM states and reports
  an actual running-guest profile mismatch separately.
- Reinstallation into the second empty home passed the installed-plugin validator.
  Doctor passed with the existing guest running. Hermes's native provider discovery
  loaded OwnMachine and captured a valid **1456 × 922 PNG**. Human reservation was
  unchanged; no desktop input was sent.
- The existing guest was started with VNC disabled for this read-only MCP check,
  then gracefully stopped. Doctor correctly reported a reachable host and stopped
  VM afterward. No VM was deleted or recreated.

The full local Hermes-aware suite passed **403 tests, zero skips/failures**;
macOS and Ubuntu CI passed at the tested commit. Validation retained the expected
in-process/CLI notices. The base Docker image also reported its existing pnpm
artifact mismatch; this was not suppressed or repaired by the plugin install.

This verifies a fresh **Hermes plugin installation**, not fresh guest provisioning,
new key pairing, browser streaming, a new model task or host reboot. Earlier guest
installation/model evidence above remains separately scoped.
