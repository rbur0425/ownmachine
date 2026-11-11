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
   Detect Docker/remote execution. Cloud Macs remain unverified.
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

The first implementation saves planning choices, not execution checkpoints.
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
