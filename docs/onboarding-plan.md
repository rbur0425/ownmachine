# Guided onboarding implementation plan

Goal: install the plugin, answer a few questions, approve the Mac changes, and
open a working private desktop without editing YAML or assembling several guides.
Preserve portable configuration, restricted runtime identities and Gitflow PRs.
This plan was approved for implementation on 2026-11-11. It is not a claim that
all stages are shipped.

## Entry points

- `/ownmachine setup`: nonblocking chat path; offer local, remote or existing
  setup and collect non-secret settings through explicit command arguments.
- `hermes ownmachine setup`: interactive terminal wizard, with equivalent flags
  and JSON output for automation. Resume saved choices rather than starting over.
- `hermes ownmachine doctor`: bounded read-only readiness and recovery advice.
  `/ownmachine doctor` is also available in chat.

Hermes default plugin-host mode skips CLI registration and refuses the native
provider. The first chat setup path explains the explicit dedicated-profile step:
`hermes config set plugins.isolation in_process`. Do not change another profile's
isolation automatically. Declare `kind: standalone` so Hermes discovers the
operator commands before a provider is selected; native-provider discovery still
uses the existing public provider registration.

Use Hermes's public command/configuration APIs. Registration must never prompt,
provision, contact hosts or create runtime state. A later welcome notice should
be one-time, dismissible and restricted to interactive sessions. Do not assume a
post-install wizard API; the catalog onboarding card is not available to a
community-tier entry. Never block cron or messaging on stdin.

## User journey

1. Offer Set up a desktop, Connect existing installation, or Later.
2. Ask where the Mac runs. Local means the Hermes machine, not the browser device.
   Detect Docker/remote execution. Cloud Macs remain unverified. macOS is the only
   guest image; do not show an OS picker, Linux choice, or unsupported image option.
3. Ask only for missing non-secret information: verified SSH alias, shared control
   location, VM storage location and desired resources. Show editable defaults:
   4 CPUs, 8 GiB RAM, 64 GiB sparse disk, 1900×1200 display. The configurable
   60 GiB working-space preflight budget is distinct from virtual disk capacity.
4. Preflight the actual Mac: hardware, OS, storage, memory, build tools, SSH,
   existing VMs and ports. Show proposed changes before execution. Never infer
   remote disk capacity from the Hermes host or browser.
5. Run deterministic setup steps with progress, bounded timeouts and checkpoints.
   Verify actual outcomes before marking steps complete. Resume after disconnects
   without recreating VMs or replaying uncertain operations.
6. Consolidate administrator work on the Mac into a reviewed account/firewall/
   service step. Keep that bootstrap privilege separate from agent/viewer runtime
   keys, and retire temporary setup access after successful verification.
7. Open the guest permission guide. Bring system prompts to the front and verify
   Accessibility, Screen Recording, restart/relaunch and capture consent. These
   are guest permissions, not host-desktop grants. Never request passwords in chat.
8. Verify firewall readiness, restricted identities, guest capture, viewer input,
   human/agent handoff and a disposable saved-document/readback check. Only then
   present Open desktop, Try a task and Run diagnostics. Keep viewer credentials
   in the operator flow and leave control paused until explicitly returned.

## Phases

### 1. Coordinator and command paths — first implementation

Ship all three entry points, optional terminal questions, saved profile-local
non-secret plans, configurable resource choices, local preflight, existing-relay
connection configuration and the existing doctor engine. Refuse unintended
replacement of configured connections. Registration and preview are read-only.

The first implementation saves planning choices and a separate durable planning/connection checkpoint, not provisioning execution checkpoints.
Fresh-install execution is explicitly pending. Selecting a native provider,
in-process loading and the hardened dedicated runtime profile remain in the
operator guide. Do not silently change unrelated Hermes settings.

### 2. Guided host/guest/viewer execution

Orchestrate the existing full-source scripts behind explicit operator actions.
Keep privileged scripts and host relay outside the catalog-installed plugin;
resolve a separately verified full-source installation at the reviewed revision,
not an executable downloaded from a moving branch. Build a versioned plan/apply
protocol with dry run, step locks, verification, cancellation and safe resume.

Implement local Mac and remote Mac bootstrap paths, dedicated-account first login,
pinned Lume build checks, strong protected VNC credentials, required PF/ALF
verification, guest provisioning, driver installation, separate keys and viewer
service setup. Select a free port before installing matching firewall rules;
never switch VNC ports without re-establishing protection. Prefer direct SSH;
configure reverse transport only when needed and supported, never promise it is
mandatory. Never delete an existing guest as a repair action.

Evaluate current Lume offline unattended setup separately against our pinned
security patch. Do not upgrade dependencies or claim Setup Assistant screens are
removed until clean acceptance proves it. Retain no Apple-account requirement,
analytics opt-out and manual permission consent.

### 3. Welcome, polish and acceptance

Add a supported interactive-session welcome and a progress surface with a clear
next action, actual progress, retry/resume and sanitized diagnostics export.
Show download/build expectations before starting. A browser setup surface, if
added, must be authenticated, private and separate from agent credentials.

Test fresh local and remote-Hermes installations ourselves: occupied ports, low
storage, missing build tools, failed SSH, interrupted downloads, first account
login, denied/revoked permissions, process restart and safe resume. Check private
links and secrets never reach model context or committed evidence. Repeat catalog
validation after registration/capability changes. Final acceptance requires a
working viewer and independently verified desktop task, not only a green doctor.

## Current implementation boundary

The first PR implements Phase 1. `--save` stores a plan under the active profile's
OwnMachine settings; `--connect` explicitly saves an existing relay's connection.
Neither creates an account, VM, firewall rule, SSH key, viewer service or permission
grant. Remote preflight remains pending until checked on the host. Plans never
claim provisioning has completed. See the companion acceptance document for the
exact checks run.

## Sources informing the design

- [Hermes public plugin commands and settings](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
- [Hermes event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)
- [Catalog admission and onboarding tier restrictions](https://github.com/NousResearch/hermes-agent/blob/3bcd071226d3d605a2bb3b4f3933e7d583e189d6/plugin-catalog/README.md)
- [Lume unattended setup](https://github.com/trycua/cua/blob/main/libs/lume/README.md)
- [Apple guest permission flow reference](https://support.apple.com/guide/mac-help/control-access-screen-system-audio-recording-mchld6aa7d23/mac)

## Review of the tentative plan — additions to Phase 1

Adopted now:

- Keep operator choices in `setup_plan` and runtime progress in Hermes `ctx.state`,
  not a second ad-hoc file writer. Hermes provides profile scoping, locking,
  atomic replacement and a 0600 state file. Store schema version, timestamps,
  plan digest, last completed planning action and bounded blocked-check codes.
- Add `/ownmachine status` and `hermes ownmachine status [--json]` for saved
  progress without SSH/VM probes. Saving a connection is `await_verification`,
  not `complete`; readiness remains evidence-based through doctor.
- Invalidate progress when chosen settings or the configured connection change.
  Preserve malformed/future state and report an error; do not erase it to resume.
- Require explicit stable platform/user/chat identity grants before chat setup
  can change configuration. Missing source identity fails closed. The local CLI
  is the operator fallback; model tools remain read-only status only.

Adopt in later phases:

- Probe → act → verify for each provisioning stage; typed JSON progress from
  host scripts, no parsing prose. Add execution locks and durable verified
  checkpoints only when those stages exist. Never replay an uncertain write.
- A single quickstart transcript, prefilled non-secret choices and concise remedies.
- Optional reminders only after an explicit request, with a clear delivery target,
  bounded count, quiet/off controls and cancellation after completion. Silence or
  an unanswered prompt is not consent to create a cron job. No reminder jobs or
  hooks are included in this PR.

Corrections to assumptions in the tentative plan:

- The restricted agent SSH key only supports status/MCP; viewer keys support a
  different fixed allowlist. Neither is a general SCP/shell provisioning key.
  Bootstrap must use a distinct, explicitly authorized operator path that is
  retired afterward. Do not broaden runtime keys to make setup convenient.
- Verify host fingerprints using the Mac's host public key through an independent
  trusted channel; `ssh-keyscan` alone does not establish identity. Never switch
  to `accept-new` merely to bypass a mismatch.
- Hermes's native doctor already dispatches to OwnMachine's provider; it is not
  exclusively a CuaDriver-only command. Our doctor entry point reuses our existing
  diagnostics without requiring the provider to be selected first.
- Hermes has public message APIs, but hook/session routing and recipient authority
  still need verification. Do not assume a hook return automatically posts a nudge.
- Public APIs alone do not make every registration surface work in host isolation:
  the tested CLI/native-provider limitation remains documented.
- macOS is the sole supported guest image, not just a default. Do not collect an
  OS choice or expose Linux/cloud-init. Cloud Mac hosting remains unverified.
- Existing resources should be verified and reused when compatible, not overwritten
  or unconditionally rejected. Repair actions such as key rotation need separate
  explicit approval; running setup again must never silently perform them.
- Only declare actual supported manifest fields/capabilities. New setup/bootstrap
  authority needs its own review; prior acceptance of runtime OpenSSH is not a
  blanket approval of arbitrary remote execution.

Planning state is not a cross-file transaction with Hermes configuration. If a
checkpoint write fails after saving choices, the choices remain available; status
reports absent/stale progress, and an explicit save retries the checkpoint. No
provisioning or readiness success is inferred from that partial save.

## Complete reminder design — planned, not implemented

Reminders are part of the onboarding roadmap. They must help an operator resume
without creating messages or background work merely because a question went
unanswered. They use the same saved stage and never run provisioning themselves.

### Consent and controls

After an explicit Later/Pause action, ask once: **Remind you tomorrow?** Offer
Tomorrow, Next time I open Hermes, and No reminders. Do not infer an answer from
silence. A successful opt-in records the chosen channel and consent timestamp;
no cron job, injection hook or recurring reminder is enabled by installation.

Proposed chat commands and equivalent `hermes ownmachine` subcommands:

- `remind status`: show consent, destination, pending time, remaining budget and
  delivery limitations, without exposing a private access link.
- `remind later`: after confirmation of the displayed time/destination, postpone
  or create one reminder; postponing an existing job does not consume another
  delivered-reminder count.
- `remind off`: disable both channels and cancel any pending job. Persist the
  disabled preference before attempting cancellation, so a late job stays silent.
- `setup` / `status`: resume or inspect the unchanged saved stage. An explicit
  pause never resets progress and must not schedule anything without opt-in.

Chat mutations require the exact configured sender identity gate. Local CLI
commands require explicit operator action. Shared/group chats need an explicit
approved destination; never infer permission from a display name, an untrusted
command argument, or an arbitrary model-selected recipient.

### State and limits

Extend the versioned `ctx.state` record with a separate reminder subrecord:
`enabled`, `mode` (session-only or scheduled), `consented_at`, `stage_revision`,
`last_nudge_at`, `delivered_count`, `job_id`, `next_due_at`, an idempotency key,
and the approved platform/chat/thread destination. Do not store credentials,
viewer tokens, prompt transcripts or raw error output there. Keep timestamps in
UTC internally; display the selected schedule in the user's timezone.

Both channels share a maximum of three delivered reminders per verified stage
revision. At most one nudge is delivered in 24 hours, and at most one scheduled
job is pending. A verified advance to a new provisioning stage resets the budget;
saving the same plan, retrying, or repeatedly saying Later does not. After the
budget is exhausted, remain quiet until the user explicitly resumes or opts in
again. Changing hosts invalidates prior destination/job state and requires review.

### In-session behavior

Use supported session hooks only in interactive sessions. A session-start
observer reads consent/progress and determines eligibility; a supported prompt
context/message mechanism supplies a fixed, minimal offer to resume. Verify the
actual Hermes routing contract before implementation; hook return values are not
assumed to send messages. Never append state paths, private hostnames, credentials
or desktop contents to model context. No nudges in cron, background workers,
subagents, unapproved chats, or profiles other than the one owning the setup.

Mark a nudge delivered only after the supported delivery path accepts it. If
scheduled delivery already consumed the daily allowance, do not add a session
nudge. Multiple sessions must not race to deliver duplicate offers.

### Scheduled behavior

Only after explicit consent, use Hermes's supported scheduling API/tool to create
one one-shot job for the approved time and destination. Verify the current API,
permissions, scheduler availability and delivery semantics during implementation;
do not bake a guessed `cronjob_manage` schema into the plugin.

The job carries a fixed resume-check instruction and an opaque onboarding
identifier, never private keys, passwords, viewer links, raw settings or desktop
text. At execution, recheck consent, profile, stage revision, completion, daily
limit and destination authority. Deliver only a short offer to resume; never
create the VM, change configuration, request credentials or automatically chain
another reminder. Use the scheduler's documented suppression mechanism when
there is nothing to send; verify it rather than assuming `[SILENT]` always works.

If gateway/scheduling/delivery is unavailable, show that clearly and offer an
explicit session-only fallback. A CLI-local job log is not a delivered message.
Do not invent an external delivery channel for Docker or headless installations.

### Cancellation and recovery

On verified completion, opt-out or destination changes, cancel pending jobs and
persist the new reminder state. A late delivery must recheck state and remain
silent. Cancellation failures keep a bounded error code and retryable cleanup
status; never silently re-enable reminders. Persist scheduling intent before job
creation and reconcile by idempotency key after crashes, preventing duplicate
jobs if the scheduler accepted a request but its response was lost. Unknown
outcomes require reconciliation, not blind creation retries.

### Reminder acceptance tests

Test explicit opt-in and no-response behavior; all three initial choices; exact
sender/destination authorization; once-per-day and three-total limits; progress
versus retry budget resets; repeat Later calls; timezone display; missing gateway;
failed scheduling/delivery/cancellation; concurrent sessions; restart around job
creation; stale stage revisions; completed setup; opt-out before job execution;
and zero secrets/private links in prompts or logs. Use fake clocks/schedulers for
regressions, then a separately approved real one-shot delivery to the operator.
Do not send real reminders as part of ordinary CI.

## Remaining implementation coverage

Phase 2 also needs a configurable mounted SSH directory for Docker, a reviewed
Mac-side runner/package decision, independently verified host-key pairing,
structured JSON progress/error codes from host scripts, and a distinct temporary
bootstrap authority. The installed runtime agent/viewer keys retain their fixed
allowlists. Use live probes to recognize compatible existing installations and
require explicit repair consent for incompatible resources.

Phase 3 includes the single quickstart transcript, authenticated progress surface,
resume/repair UI, permission-dialog guidance, and the reminder implementation
above. Validate the full path on both a local Mac and remote/Docker Hermes;
measure user interactions and actual download/build time rather than promising
an untested fixed installation duration. Completion requires verified desktop
capture/input, saved-result readback and handoff, not merely a stored stage value.

### Phase 2 increment: Mac-side execution runner

Implemented in the setup-execution branch: reviewed full-source operator runner
with explicit build/provision apply steps, private durable checkpoints, per-VM
execution lock, plan/source identity checks, and postcondition verification.
Successful steps reverify without repeating mutations; interrupted/failed work
requires inspection. Provisioning passes the selected storage path explicitly and
keeps VNC disabled. Wizard resource/display bounds now match the provisioner.
See [execution instructions and boundaries](setup-execution.md).

Still pending: authenticated receipt import into Hermes progress, remote bootstrap
transport, integrated firewall/guest hardening/driver/keys/viewer execution,
custom-storage propagation through the runtime relay, cancellation with descendant
process tracking, actionable repair flow, live fresh-install acceptance, and the
complete opt-in reminder design above. The existing three command entry points
remain available; they do not claim these pending steps are automated.
