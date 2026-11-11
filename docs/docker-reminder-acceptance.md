# Docker onboarding and reminder acceptance

Candidate branch: `feature/onboarding-docker-reminders`.
Hermes reference: `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.
These results describe observed tests, not a claim that every onboarding path has
completed. Private destinations, account names, paths and keys are omitted.

## Public scheduler route

- Created a no-model job paused through the public CLI. The authenticated gateway
  listing confirmed its exact unique name, script, destination, disabled state
  and absent next run before it was resumed.
- An isolated resumed silent script completed successfully without output.
- An isolated resumed failing script reported an error; failure delivery was
  configured local, and no external destination was used for this test.
- Sent exactly one fixed reminder through an existing Docker Hermes default
  profile to an explicitly approved Discord channel. Public job status was `ok`,
  with neither a delivery error nor unverified delivery. The user independently
  confirmed receipt, including Hermes's standard cron wrapper. Removed the job
  and helper afterward; no repeat remains scheduled.
- This Hermes version refuses manual execution of paused jobs. Acceptance resumed
  the inspected job before triggering it once. The plugin's delivery-time checks
  still protect early, repeated or altered executions.
- Unit coverage includes due-time checks, edited destinations, opt-out, uncertain
  creation, silent helper failure, unconfirmed delivery and unavailable gateways.

- A cron script running in Hermes’s cleaned environment invoked the public plugin
  CLI and read the exact profile’s reminder preview state successfully.

- Stopping only the isolated profile gateway caused tomorrow scheduling to refuse;
  no job or automatic gateway start occurred.

## Docker-to-Mac setup

Separate operator, agent and viewer OS users and private SSH keys were prepared.
Only public keys and independently trusted host-key material crossed machines.
The operator ran remote preflight and build verification through Hermes and the
restricted setup endpoint. The signed patched Lume app was explicitly adopted,
not rebuilt or overwritten. A fresh guest was provisioned in non-default
storage whose path includes a space. The old test guest was deleted only after
explicit approval. Host firewall protection remains active. Remote firewall, relay, keys, hardening
and driver stages all passed. The older relay file differed, so setup refused to
overwrite it; inspection confirmed no relay mutation, and the old file and failed
checkpoint were preserved before the explicit fresh-install retry.

The initial fixture copied the candidate plugin for testing. A second fresh Docker
profile then installed it through `hermes plugins install` from the public Git
URL at immutable commit `0be4244aa219aa2ac17f4653ed69db3ab4c986e5`, resolved the
declared Python dependency and enabled the plugin successfully.

The initial required local package gate passed all 333 tests with no skips, reproducible
bundle/checksum checks, fresh installation, upgrade and source/packaged Hermes
validation. The GitHub offline job exposed a missing test-environment dependency;
the workflow now installs the same pinned WebSocket dependency as the manifest.

The protected Docker viewer connected after the managed guest restart. First boot
still required Update Mac Automatically, optional accessibility preferences,
Apple Account skip, adult age range, analytics (unchecked), Screen Time and guest
FileVault choices. The permission guide appeared afterward. Guest consent and the guide's capture verification passed. A disposable TextEdit
file was typed and saved through the browser, then independently read over guest
SSH from the guest home directory. The guest Documents folder denied SSH access;
no Full Disk Access was granted to bypass that protection.

Native capture passed through the Docker operator and separately through the
public-Git-installed plugin under the dedicated agent user. Both returned valid
1456×920 PNG captures. Final verify/apply completed, rejected the retired setup
key, retained runtime access and reported no pending reminder cleanup. Control
was left paused. This is deterministic desktop acceptance, not a model-driven task.

The fixture initially omitted the documented shared-control bootstrap: its lease
and session lock were private to their creating users. Group modes and default
ACLs were configured only on the shared control volume; private key/token homes
remained inaccessible to the agent. Include this bootstrap before starting either
service. Mac-side verification used its existing local verification aliases and
viewer; the separate Docker key-denial, streaming, input/readback and installed
plugin capture tests above establish the new cross-machine path independently.

## Review follow-ups

- A real local gateway session received the fixed `on_session_open` reminder as
  a session event; state counted exactly one accepted delivery.
- The actual Hermes admission pipeline was exercised with its isolated test
  adapter and real plugin dispatch. `ctx.post_message` returned `no_conversation`;
  the original message reached the agent once, and the reminder count stayed zero.
  The ineffective `post_gateway_admission` registration was removed. Automatic
  next-message chat nudges remain deferred; explicit OwnMachine chat commands and
  consent-bound scheduled delivery remain supported.
- Skipped/failed one-shot results now retain a one-time explanation for the next
  authorized matching visit, respecting opt-out and configuration changes.
- The catalog draft discloses the pinned WebSocket dependency and actual hook list.

The review follow-up suite passes 335 tests. A separate capture explicitly loaded
the pinned current Hermes source in Docker and passed after setup-key retirement.
The original Docker image remains an existing managed runtime (it reports a
dependency/build synchronization warning); this acceptance does not certify a
from-scratch rebuild of Hermes itself. OwnMachine’s immutable-pin installation,
plugin validation and runtime capture were tested separately.

A live early-run test produced no scheduled reminder output. The next real local
session received exactly one skipped-delivery explanation; a second session
received none. The delivery count stayed unchanged. The test job/consent were
cleared and the isolated gateway stopped afterward.
