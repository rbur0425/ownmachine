# OwnMachine v0.7.0 — guided onboarding preview

**Give your AI agent its own desktop.** A persistent private macOS VM for Hermes,
with restricted SSH/MCP, native computer use, a streaming browser viewer and
explicit human/agent control. This source-available preview uses PolyForm
Noncommercial License 1.0.0; commercial licensing is available from the owner.
It is not an approved Hermes catalog listing.

## New since v0.6.0

- Guided terminal/chat setup planning, configurable resources/storage, saved
  resumable state, doctor checks and explicit next-step/handoff instructions.
- Hermes-driven SSH setup stages, authenticated progress, fresh-guest hardening,
  driver/permission guide, native screenshot verification and automatic retirement
  of the exact temporary setup authorization after successful acceptance.
- Opt-in next-visit and scheduled reminders with preview/confirmation, delivery-time
  authorization checks, limits, opt-out and once-only skipped-delivery explanations.
- Correct cold-launch focus: an explicit raise now brings the new exact app window
  forward, retaining control-gate checks and configured readiness timeout.
- An [evaluator quickstart](evaluator-quickstart.md) with administrator handoffs,
  guest consent and a tested two-user shared-control permission recipe.

## Verified behavior

A local Qwen model, through the public-Git-installed plugin and normal Hermes CLI,
cold-launched Safari and navigated to Google with no operator desktop input during
the run. An independent screenshot and accessibility URL read confirmed the page.
The initial failure, fix and passing rerun are retained in
[acceptance evidence](docker-reminder-acceptance.md).

The Docker-to-Mac run covered fresh provisioning, custom storage, hardening,
separate runtime keys, guest consent, human typing with independent file readback,
native captures and setup-key rejection after retirement. One explicitly approved
Discord reminder was received and independently confirmed; its job was removed.
The shared-control recipe passed lock/SQLite/heartbeat checks as two separate
Linux users under a private umask.

The required local gate runs 340 tests without skips, Hermes validation, repeatable
bundles/checksums and fresh-install/offline-upgrade checks. See the attached
`validation-summary.json` for the exact final release commit, tested Hermes
revision and final gate results. Release assets use that same source commit.

## Install and evaluate

Start with the [evaluator quickstart](evaluator-quickstart.md). First-time setup
needs the full-source archive; the plugin-only archive does not contain the
privileged Mac installers or separate viewer. Verify both archive inventories
using `manifest.json` and `SHA256SUMS`; checksums are not publisher signatures.
Use the final commit in `validation-summary.json` for a pinned Git installation.

## Boundaries

- Administrator account/firewall work, initial dedicated-account login, remaining
  Setup Assistant screens and guest macOS consent are explicit human handoffs.
- Host restart acceptance passed previously within its documented scope. At the
  owner's direction it was not repeated for this release; independent ALF-only
  random-port coverage and the later security arrangement's reboot persistence
  remain unverified. This release does not broaden the earlier evidence.
- One historical initial guest boot hung; later lifecycle checks passed. VM
  backup/restore, automatic host recovery and cloud Mac acceptance are deferred.
- The Safari run demonstrates keyboard/accessibility input; model-driven pixel-click
  acceptance remains deferred. Reliability depends on the model and application.
- Automatic nudges on unrelated chat messages are deferred because the tested
  admission hook has no bound reply destination. Explicit commands, local sessions
  and opted-in scheduled delivery have separate supported routes.
- The existing live Hermes image has a build synchronization warning; this is not
  certification of rebuilding Hermes. Final source/package validation is separate.
- No new provider credentials are held by OwnMachine. Screenshots/app text can go
  to the model configured in Hermes; use guest contents appropriate for that route.

The owner is preparing the demo. No catalog PR, X post or hackathon form is
submitted as part of publishing this release.
