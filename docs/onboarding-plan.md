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

### 2. Guided host/guest/viewer execution — in progress

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

### 3. Welcome, polish and acceptance — pending

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

Hermes now dispatches explicit setup stages over a separately paired restricted
SSH endpoint and imports authenticated, source-bound progress. Provisioning,
firewall checks, relay/key installation, guest hardening, driver/permission checks,
capture verification and setup-key retirement have deterministic stage handlers.
Administrator bootstrap, first account login, guest consent and viewer ownership
remain explicit handoffs. `setup --next` explains the next action; `--later`
offers opt-in reminders without stopping a running operation.

The current reminder implementation and its exact delivery semantics are in
[onboarding-reminders.md](onboarding-reminders.md). The public scheduler route
has now delivered one user-confirmed Discord test. Full candidate Docker-to-Mac
acceptance remains in progress; see [docker-reminder-acceptance.md](docker-reminder-acceptance.md).
Older phase notes below record earlier review boundaries and are superseded by
these current implementation and acceptance documents where they differ.

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

## Complete reminder design — target design; implementation status below

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

## Reviewed gap ledger — after PR #5

This ledger is the current status; historical phase notes above describe earlier
increments. Phase 1 is implemented. **Phase 2 is in progress**, not complete.
PR #5 supplied Mac-side execution/checkpoint primitives, not the complete Phase 2
or a completed Phase 3. Phase 3 welcome/polish and live end-to-end acceptance
remain pending. No reminders or cron jobs are enabled by installation. The verification increment below adds opt-in next-visit reminders; scheduled delivery remains blocked.

| Requirement | Current increment | Remaining acceptance/work |
| --- | --- | --- |
| Hermes runs each stage over SSH | Pending; commands still plan/connect/diagnose | Dedicated temporary setup authority, reviewed source pin, strict host-key confirmation, bounded stage RPC and revocation; no arbitrary shell on agent/viewer runtime keys |
| Remote Mac preflight before starting | Operator-side actual Mac preflight exists | Run it through authenticated SSH from Hermes; expand admission checks for memory, build tools, existing guests and occupied ports; never infer remote hardware from Hermes |
| Key pairing and host-key confirmation | Operator pairing helper generates a key in each runtime account and pins an independently confirmed Ed25519 host key | Guided transport/distribution of public keys and proof that the two runtime accounts/containers are separate; never auto-trust ssh-keyscan |
| Restricted key installation | Service stage preserves unrelated authorized_keys entries and rejects differently authorized duplicates | Exercise both actual runtime identities after installation; temporary setup access retirement |
| Relay installation | Explicit idempotent install of reviewed relay and selected configuration, refusing different existing files | Upgrade/recovery UI and authenticated remote orchestration |
| Firewall | Explicit root installer remains a human administrator handoff; service stage checks fresh root-owned status and the configured app's ALF block | Integrated administrator handoff, free-port selection and independent external-network/reboot acceptance |
| Guest hardening | Existing explicit operator script only | Integrate bootstrap start without VNC, host-key pinning, password/key rotation, guest SSH alias and exact shutdown permission with independent verification; uncertain hardening must never replay |
| Driver and permissions | Service stage transfers pinned reviewed installers over key-only, host-key-pinned guest SSH; permission stage opens normal guide and verifies grants/capture evidence | Live fresh-guest run, consent/relaunch recovery and authenticated stage receipts; never grant TCC automatically |
| Viewer installation | Explicit macOS GUI LaunchAgent or Linux user systemd stage; private access state outside shared control; authenticated readiness wait | Separate-user live acceptance, browser click/type/handoff and remote viewer dispatch; no model-visible token |
| Final verification | Readiness checks for both restricted SSH identities, wrong-role refusal, guest readiness and viewer/RFB handshake | External firewall, actual browser input, disposable model task and saved-result readback; do not equate readiness with completed onboarding |
| Mac progress linked to Hermes | Pending | Import only authenticated, nonce/plan/source/VM-bound sanitized receipts into profile-local state; reject replay, forged/newer schemas and mismatched identities; never trust copied JSON as completion evidence |
| Progress during execution | Optional NDJSON start/liveness/finish events on both operator runners | Transport events into Hermes nonblocking progress; emit measured milestones where available; heartbeats are not fabricated percentages |
| Custom guest storage | Relay status, MCP, lifecycle and VNC now propagate configured storage_dir; service installation writes matching host.json | Live non-default storage acceptance; keep old default behavior when field omitted |
| Opt-in reminders | Next-visit consent, profile/destination binding, limits and opt-out implemented | Scheduled delivery and automatic session-open nudges need supported Hermes routing; no inferred consent |
| Command manifest inventory | ownmachine listed as advisory commands metadata; current Hermes actually loads public ctx.register_command/register_cli_command registrations | Follow a supported manifest registration field if upstream introduces one; do not claim advisory YAML changes runtime behavior |
| Guide link and wizard quickstart | Current development guide link replaces the fixed v0.6.0 link; wizard-based quickstart documents the actual handoffs | Release docs should link the matching reviewed version; do not execute mutable documentation links as code |
| PR #4 post-review changes | Planning progress and exact setup_allowed_senders authorization are already merged | Retain tests and explicitly show changes in future review descriptions; these are not proof of execution completion |

The next orchestration increment must join these operator stages to the existing
three Hermes command paths. It must not broaden runtime keys or put privileged
scripts, viewer secrets, host passwords or private keys into the installed plugin.
Remote receipt authentication and stage dispatch should land together so a UI
cannot advance based on an unauthenticated status file. Full acceptance must run
from Hermes through the viewer before this ledger can be marked complete.

## Phase 3 orchestration update — SSH transport increment

These entries supersede the earlier gap ledger where implementation has advanced.
They do not close live end-to-end acceptance or the human consent steps.

- [x] Run reviewed stages from the Hermes **operator terminal** over strict,
  host-key-pinned SSH using a separate temporary setup identity and host-side
  allowlist. Runtime keys retain their existing restrictions. Initial source,
  approved plan/config and public-key trust bootstrap remain operator work.
- [x] Check the actual remote Mac from Hermes before build/provision; require a
  fresh successful hardware/Swift/capacity/resource preflight. Port selection and
  full cloud/external-storage admission checks remain future work.
- [x] Import sanitized Mac outcomes through the live authenticated SSH channel,
  bound to nonce, source, plan, VM and stage; display them in Hermes onboarding
  status. Reject mismatches and replay; no copied-file completion import.
- [ ] Wire `secure-guest.py`, initial guest SSH configuration and guest shutdown
  authorization into the resumable protocol. Existing manual hardening remains
  required; partial outcomes must never trigger automatic password rotation.
- [ ] Partial final verify: checks both runtime-key statuses, rejects each key's
  other-role operation and tests viewer VNC authentication. It **does not yet run
  a computer_use screenshot**. Add that and independently verify a desktop task
  before marking this acceptance item complete.
- [ ] Stream progress into nonblocking Hermes chat/UI and complete the fresh
  multi-machine flow. Terminal calls currently wait for the bounded final result;
  local status records pending/uncertain execution. Keep reminders opt-in and
  unimplemented until the previously specified consent/deduplication tests pass.

PR #4 follow-ups: command inventory in plugin.yaml remains documentation-only
for current Hermes; public registration APIs load the command. The wizard
quickstart exists. The setup guide now derives its release tag from plugin version;
an explicit full-commit override supports development without floating release
docs. Never claim that advisory manifest inventory changes Hermes registration.
See [transport and trust setup](setup-transport.md) for configuration and limits.


## Phase 3 hardening and chat increment

- [x] Add explicit `harden` stage to the reviewed SSH allowlist and saved
  checkpoints: matching fresh provisioning receipt/custom storage, VNC-disabled
  boot, isolated host-key pin, credential rotation, guest alias, exact shutdown
  permission and live sshd re-verification. Failed/interrupted mutations require
  inspection. No unattended TCC approval.
- [x] Supervised, sender-authorized chat calls through public Hermes APIs, with
  authenticated bounded SSH heartbeat frames and conversation-bound progress.
  Heartbeats are liveness observations, never completion or percentages.
- [x] Fresh laptop provision, hardening and driver acceptance after explicit
  guest-recreation approval: real Hermes CLI/slash handlers, pinned SSH, authenticated
  heartbeat import and repeat verification without credential rotation.
- [ ] Complete fresh-guest consent and full onboarding acceptance. The permissions
  stage correctly stops at `needs_attention`; no TCC grants or screenshot were
  claimed. See [recorded results](guided-hardening-acceptance.md).
- [ ] Final computer_use screenshot and independently verified desktop task.
  Existing runtime status/role-denial/VNC checks remain only partial verification.
- [ ] Retire temporary setup access after complete acceptance: remove only the
  exact setup public-key entry, preserve unrelated entries, prove setup access
  fails and runtime keys retain their separate roles, record a non-secret receipt,
  and provide interruption recovery. Current retirement is still manual.
- [ ] Phase 2 opt-in reminders, consent, destination binding, deduplication and
  cancellation tests. Live progress does not implement reminders or cron jobs.

This increment supersedes the earlier manual-hardening and terminal-only entries;
initial operator pairing/source transfer and cross-machine viewer installation
remain explicit. See setup-transport.md for commands, limits and recovery.


## Screenshot, retirement and reminder increment

This status supersedes the earlier open items above.

- [x] Fresh laptop guest Accessibility, Screen Recording and capture consent;
  live permissions guide completed, no host desktop grant.
- [x] Final verification captures and validates a PNG through OwnMachine's native
  Hermes computer_use provider after status, role separation and viewer checks.
  Only image digest/dimensions/time enter setup state; pixels never enter chat.
- [x] `setup --run verify --apply` removes the exact temporary setup authorization,
  checks SSH rejects it, and verifies the runtime identity still works. Completion
  is bound to plan/source/transport. Lost acknowledgement requires inspection;
  already-completed verification returns its receipt without replaying retirement.
- [x] Opt-in next-visit reminders: preview/confirmation, exact sender/profile/chat
  binding, persisted consent, maximum three accepted nudges per verified advance,
  daily spacing, opt-out, completion suppression and interrupted-delivery guard.
- [x] Scheduled tomorrow reminders through public gateway attach, `cron.manage`
  inspection and CLI paused creation. Delivery-time checks use this same route.
- [x] Local session-open/resume and authenticated chat-admission next-visit hooks.
  Chat delivery means the next admitted message, not a generic session-open event.
- [ ] Independently verified real-model desktop task remains separate acceptance;
  a valid screenshot does not certify task completion.

See [verification acceptance](verification-retirement-acceptance.md) and
[reminder controls](onboarding-reminders.md). Real external reminder delivery and
full cross-machine unattended orchestration are not claimed by this increment.


### Reminder phase — implemented; acceptance in progress

- [x] Terminal and authorized-chat status/later/off; next-visit remains the default.
- [x] Preview plus 15-minute confirmation; installation and silence grant no consent.
- [x] Configurable daily budget, verified-stage reset, binding and opt-out checks.
- [x] Later/Pause offers reminder choices without stopping active work.
- [x] Paused one-shot creation, exact job verification, delivery-time recheck,
  silent helper errors and delivery receipt reconciliation through public APIs.
- [x] Local session and authenticated chat-message visit hooks; command fallback.
- [x] One real Discord reminder independently confirmed by the recipient; job removed.
- [x] Cron cleaned-environment helper reached the same profile's plugin state.
- [ ] Complete final Docker-to-Mac candidate installation, guest consent, viewer
  input, native capture and retirement acceptance; do not infer this from unit tests.

See [Docker/reminder acceptance](docker-reminder-acceptance.md) for observed results.
