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
