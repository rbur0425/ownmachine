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

## Real-model Safari task — 2026-11-11

**Result: failed safely; Google was not reached.** This is an actual model run,
not a replay of operator-authored desktop actions. The isolated Docker agent used
its public-Git-installed OwnMachine plugin at
`0be4244aa219aa2ac17f4653ed69db3ab4c986e5`, with current Hermes source
`3bcd071226d3d605a2bb3b4f3933e7d583e189d6`. PR documentation head before this
run was `c820d50ef9c402aed09c53a1ce9514673a9ffcda`; this is not a claim that the
installed plugin was upgraded to that later commit.

The normal Hermes one-shot CLI used the configured local OpenAI-compatible
`qwen3.8-flash-next-iq2_xs` model and the `computer_use` toolset. The isolated
profile kept terminal, file and code-execution toolsets disabled. No provider
credentials were copied. The task asked it to open Safari, navigate to
`https://www.google.com`, wait and capture the result, using desktop tools only.
It included explicit guidance to inspect first, use Command+L, type the URL and
press Return. No operator supplied desktop input during the model run.

Observed sequence:

1. Readiness passed. Safari was installed but not running.
2. An initial launch attempt lacked a capture and was rejected with
   `capture_required`. The model captured the desktop and recovered. One malformed
   tool-call wrapper was also rejected before dispatch and subsequently corrected.
3. `focus_app` with `raise_window=true` launched Safari in the background. In the
   current provider, the not-running branch returns after `launch_app`; it does
   not also perform `bring_to_front`. The model captured Safari's Start Page.
4. Command+L was dispatched; the effect required verification. The model captured
   again, then attempted to type the URL. The driver refused with
   `minimized_or_hidden_window` (including inability to prove window state), and
   OwnMachine returned `driver_action_failed_review_required`, blocking writes.
5. The model stopped input, took a final read-only capture and correctly reported
   failure. It did not press Return or claim Google loaded. The transcript contains
   nine `computer_use` results plus status/discovery calls; no shell or external
   browser tool performed the task.

Independent verification: after the run, the operator stopped only the isolated
agent profile's gateway to release its backend session lock, then opened a separate
read-only backend connection. A fresh, unannotated 1456×786 Safari capture showed
**Start Page**, its onboarding card and an empty address field. The Google favorite
tile is not a loaded Google page. The window listing reported Safari on screen,
so the driver's refusal is not proof that Safari was actually minimized; the
launch/focus and driver state checks need investigation. The control gate retained
`pending=true` until operator inspection, then was acknowledged into **paused**.
The guest was left running. Private captures and transcripts remain outside Git.

Follow-up before claiming this task passes: investigate cold-launch foreground
handling and the driver's hidden-window refusal, add appropriate regression
coverage, and repeat this same model task with independent page verification.
This result does not establish model-driven pixel-click reliability. No new host
reboot or Hermes runtime rebuild was performed.

### Fixed cold-launch rerun — passed

The cold-launch branch now honors explicit `raise_window=true`: after one launch,
it observes the same bundle's new process/window, then requests exact-window
`bring_to_front`. Read-only readiness polling uses the configured
`action_timeout_seconds`. Both writes retain lease/generation checks. A failed
launch never raises, a human takeover blocks the second write, and every exit
invalidates the previous capture. Background-only requests remain background-only.
No Safari-specific path, host identity or foreground fallback was added.

Installed fix commit `71049a2c8bcd88c15393a83b64ced99d14fb1fdc` through
`hermes plugins install` from the same public Git URL with `--ref`, `--force`,
`--yes-deps` and `--enable`. Operator preparation closed the empty Safari window
and independently confirmed Safari was not running. A new Hermes session then
received the **same prompt** as the failed run, with the same local Qwen model and
current Hermes source. No operator desktop input occurred during that session.

Hermes captured the desktop, launched/raised Safari, captured its Start Page,
sent Command+L, typed the URL, verified the field contents, pressed Return, waited
and captured the Google page. It dismissed the address suggestions with Escape
and reported success. The initial hidden-window typing refusal did not recur.

Independent verification after the model finished used a separate read-only
backend session, not its success message or saved image: an unannotated 1456×786
capture visibly showed Google's logo, search field and search buttons. A fresh
AX read reported window title `Google` and the smart search field value
`https://www.google.com/?client=safari&channel=mac_bm`. Safari's query parameters
do not change the verified destination. No Google sign-in was performed.
The gate had no pending action; control was returned to **paused**, with the guest
running and Google left open. Private images/transcripts remain outside Git.

The required local gate passed **340 tests, zero skips**, source/packaged Hermes
validation, reproducible bundles/checksums, fresh installation and upgrade checks.
Five new regression cases cover cold launch with/without raise, launch failure,
human takeover before raise and bounded readiness timeout. The CI prerequisite
list was updated for those Hermes-dependent tests; the lightweight CI image does
not include Hermes, while the required local gate executes all five against it.
This task establishes cold-launch and keyboard/AX navigation acceptance; it does
not establish model-driven pixel-click reliability or new firewall reboot coverage.
