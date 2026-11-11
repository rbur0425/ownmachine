> Historical acceptance record: these tests used the MacDesk name.
> The product is now OwnMachine; recorded VM/file identifiers below are unchanged.

# Model-driven and physical-host acceptance

Observed on 2026-11-10. This record distinguishes operator-assisted recovery
from an uninterrupted model success. Private deployment identities, credentials,
transcripts and desktop captures are excluded.

## Real model path

The configured model ran through Hermes `AIAgent`, native `computer_use`, the
MacDesk provider and SSH/MCP transport into the macOS guest. GUI actions were
chosen by the model; the operator approved individual writes. No scripted GUI
sequence or filesystem tool was provided to the model. This is a dedicated
Hermes-home API run: the separate interactive CLI attempt hit a profile mismatch
and is not counted as a CLI end-to-end pass. The configured model alias differed
from the inference server's reported loaded weights; results apply to the actual
configured endpoint, not an independently verified model brand/version.

- Browser task: the model opened Chrome and navigated to the requested public
  example site. It observed malformed initial address entry, recaptured and
  corrected it. Subsequent window/tab/AX observations confirmed the page; a
  separate viewer inspection agreed. The fixture's expected heading was absent,
  so the heading-specific criterion did not pass.
- TextEdit task: the model created a new document and set the exact acceptance
  text. Fresh AX and screenshot observations agreed. An attempted AXPress on
  an AXWindow failed; the provider preserved the pending write marker and
  required operator review. The document remained unsaved.
- After independent inspection and explicit human-to-agent transfer, another
  model run opened a Save sheet on the intended document. Setting the location
  popup with `set_value` failed. A subsequent model write was blocked without
  dispatch. This demonstrates gate enforcement, but also shows that the model
  did not immediately stop at the first error as instructed.
- Failure replies retained the upstream escalation recommendation alongside the
  instruction to stop. MacDesk now removes that driver recommendation. Hermes's
  own generic response classifier also added an `escalate` verdict for failed
  actions. MacDesk now uses supported `tool_execution` middleware to replace
  that verdict only on MacDesk-tagged review-required results. It calls the tool
  once, preserves evidence, and leaves other results/providers untouched. The
  actual Hermes formatter plus middleware is covered by regression testing; no
  core function is replaced. The durable write gate remains authoritative.
- The provider now preserves supported AX actions and refuses an explicitly
  unsupported AXPress before dispatch. It never silently substitutes a pixel
  click. Driver failure replies retain bounded diagnostic text for inspection.

A further continuation tried AXPress on the Save As text field and failed. Its
coordinate retry was blocked without dispatch. After independent inspection,
a separate diagnostic run was restricted to screenshot-grounded foreground
pointer/keyboard input chosen by the model. This isolates the AX interaction
limitations and will be reported as assisted continuation, not a clean run.

The pixel/keyboard continuation opened and expanded the location picker, then
opened Go to Folder. Foreground `type` into that dialog failed and the model
stopped immediately. **File-save acceptance failed.** No saved-file completion
was claimed. An independent operator preserved open TextEdit contents in a
private recovery record before reboot preparation; that is recovery evidence,
not a GUI save or a model-task pass. The viewer was reserved for inspection and
then explicitly paused. Its ordinary page control worked, but attempts to dismiss
the guest folder dialog through viewer input did not visibly succeed; the cause
has not been established.

These runs demonstrate real model execution and durable failure gating, but
not an uninterrupted end-to-end pass. The later corrective runs below supersede the action-metadata gap; earlier
failed runs remain failures.

## Physical-host reboot

Preflight recorded the host boot-session identifier. FileVault is enabled and
the dedicated service account lacks passwordless administrator privileges.
The host reboot is explicitly deferred until the operator confirms their file
transfer is finished. No MacDesk host LaunchAgent is installed. Login/unlock and operator VM startup
may therefore be required after reboot; automatic VM recovery is not claimed.

Pre-reboot: two saved acceptance documents were read through signed-driver AX
and hashed privately; Chrome's installed version and default-profile directory
identity were recorded without copying profile contents. The existing firewall
LaunchDaemon was registered and its last exit code was zero. Control was paused.

The guest was gracefully stopped during preflight, then started again for the
authorized model-control fixes while the physical reboot remained deferred.
Before the eventual host reboot, stop it again and refresh the baseline.

Pending: reboot the physical host, confirm a new boot identifier, check the existing PF
restriction before enabling the VNC listener, start the VM through the configured
lifecycle path, then verify SSH/MCP, guest permissions, saved content, Chrome
profile identity and restricted viewer connectivity.

## Follow-up onboarding work

The guide now explains guest password retrieval and direct typing. Remaining
macOS first-login screens are documented step by step, without promising
unattended suppression. Exact 1900×1200 was visually verified after a guest-only
restart. Those initially pending native paste and guide-layout checks were completed
in later follow-ups, including ordinary-field paste, masked Safari-field paste
and reverse copy. Privileged macOS password-dialog paste remains unverified. See
[laptop onboarding observations](laptop-acceptance.md). VM backup/restore remains
deferred beyond MVP.

## Validation

At the first PR revision, macOS ran 197 tests: 180 passed and 17 expected
Hermes-only skips. Hermes ran 197: 187 passed and 10 expected macOS-only skips.
Plugin validation and the complete Gitea bundle/install/upgrade CI gate passed.
The subsequent contradictory-escalation fix passed all 13 native-provider tests;
CI for the updated revision is tracked separately. These are offline checks,
not hardware acceptance passes.

## Corrected test procedure

The driver invalidates previous tokens when any client snapshots the same
window. Operator AX inspections during approval pauses can therefore invalidate
the model's pending action. Earlier popup/field failures cannot be attributed
solely to unsupported controls. In particular, the pinned driver's `set_value`
contract supports popup selection. Future acceptance runs must have one capture
owner: no concurrent operator/diagnostic AX captures while the model is active.
Private failure-reply recording does not request a second snapshot.

The provider now includes supported AX actions in capture guidance and preserves
actions/value/enabled/focused metadata. A click on an element explicitly lacking
AXPress is refused before dispatch (including before bring-to-front), leaving
the lease usable. It never silently substitutes a pixel click. Unknown action
metadata retains existing driver behavior, and dispatched failures still require
operator review. Fourteen native-provider tests pass.

## Isolated corrective run

A fresh model run with a single capture owner created and verified the exact
new TextEdit content, opened Save, and set the filename successfully. It stopped
on a failed `set_value("Desktop")` for the Where popup. An operator diagnostic
reproduced the failure after inspection/acknowledgement: the popup offered the
current directory and its ancestors, not Desktop. This was a missing option,
not evidence that popup `set_value` is unsupported. The diagnostic did not save
the document and is not counted as model completion.

Capture guidance now requires observed popup choices and explains that location
popups can list ancestors; other destinations need dialog navigation or keyboard
shortcuts. Bounded driver failure details are retained in result metadata.
The model must still stop on any review-required failure. No operator snapshot
is taken while the subsequent model run owns capture tokens.

Current offline checks: macOS 183 passed with 18 expected Hermes-only skips;
Hermes 191 passed with 10 expected macOS-only skips (201 tests each). Hermes
plugin validation passed, including declared middleware and no core override.

## Successful fresh model task

A subsequent fresh `AIAgent` run with the corrected provider guidance created a
new TextEdit document, entered the exact fixture text, navigated to Desktop,
saved it, and recaptured the saved title and content. Only individual write
approvals were supplied; the model chose the GUI sequence. No operator AX
capture, filesystem tool or scripted GUI sequence intervened during this run.
It dismissed the previous run's Save sheet without altering its document.

The model inspected the ancestor-only location popup, selected the home folder,
then navigated to the observed Desktop entry. Filename assignment used
`set_value`; Save used AXPress. Post-run independent checks confirmed the
expected Desktop `.rtf` exists (427 bytes), and a new signed-driver AX capture
confirmed both the saved title and exact fixture text. The gate had no pending
write. Direct SSH content extraction was denied by guest privacy controls; no
additional access was granted, and no filesystem-content claim relies on it.
This passes the create/type/navigate/save/verify task through the real configured
model, native Hermes provider and MCP transport.

This is not a claim that every input route is reliable: the model recovered from
ineffective pixel clicks and pre-dispatch stale-element/pixel-capture refusals.
It also corrected `app=desktop` to the supported `app=screen` alias. Pixel
mapping/focus behavior deserves a separate focused acceptance case. The model
run used the capability/navigation changes at `58ec457`; the subsequent
operator-review middleware was verified through Hermes's actual response
formatter and the full suite, rather than by inducing another live failed write.
The full bundle/install/upgrade CI gate passed at `6412261`.

## Pixel input follow-up

A focused live regression exercised the actual native provider, SSH/MCP
transport and human-control gate against a harmless browser counter fixture.
Three fresh captures followed by screenshot-local pixel clicks changed the
observed AX label from Clicks: 0 to 1, 2 and 3. The foreground global-input
route and background accessibility hit-test route both succeeded on a 2x
scaled display. Control was returned to paused with no pending write.

The provider now sends the driver's opaque capture ID with each pixel click,
consumes that binding once, and uses current `screenshot_frame` geometry in
preference to older window-list bounds. It rejects nonfinite/out-of-image
coordinates or missing driver capture support before focusing or dispatching.
Right and double clicks use the same bound driver click endpoint; offline
contract tests cover both. `desktop` is accepted as a screen alias.

This is a direct provider regression, not another model-driven run. The earlier
model create/save pass remains the model evidence. Scroll and application-
specific behavior are not established by the counter fixture. No automatic
replay or weakening of the human-control gate was introduced. Physical-host
reboot remains deferred by the operator; backup/restore remains outside MVP.

Final offline checks for this follow-up: macOS 186 passed / 21 expected
Hermes-only skips; Hermes 197 passed / 10 expected macOS-only skips (207 tests
each). Hermes plugin validation passed. The optional Swift viewer patch also
compiled in release mode and passed the live ordinary-field paste test in
[laptop acceptance](laptop-acceptance.md). Host reboot acceptance is still pending.

## Physical-host reboot follow-up — 2026-11-10

The operator authorized and performed the physical VM-host restart. The guest
was gracefully stopped through the configured lifecycle path with control paused.
Three acceptance-document content hashes were refreshed through signed-driver AX
before shutdown; the host boot-session identifier was recorded privately.

SSH became unavailable during the restart. After the operator unlocked FileVault
and logged in, the boot-session identifier differed from the baseline. FileVault
remained enabled. The guest was still stopped and no VNC listener was active.
The existing firewall LaunchDaemon was registered with last exit code zero.
Before starting the guest, a temporary harmless IPv4 listener on the configured
VNC port accepted loopback access while a connection from a separate LAN machine
timed out. The probe was closed before VM startup. No firewall rules or system
security settings were changed. This verifies the tested IPv4 path, not every
network interface or IPv6 route.

The operator lifecycle command started the guest and retained paused control.
An immediate readiness probe reported guest-not-ready; after guest startup
finished, the combined check passed with 18 passes, four informational/manual
warnings and no failures. SSH/MCP, Accessibility, Screen Recording and capture
consent survived. A native provider capture returned a nonempty PNG and AX tree.
All three restored acceptance documents matched the refreshed content hashes;
Chrome's window returned. Authenticated loopback viewer HTTP and the SSH-backed
shared VNC handshake passed. No fresh browser click/type or model task is claimed
by this reboot test. Control remained paused with no pending write.

Chrome was installed and its profile directory existed after reboot. The attempted
pre-reboot Chrome metadata refresh failed, so exact Chrome version/profile
identity persistence across this reboot is **not verified**. Earlier records
claiming a recorded profile baseline do not replace that missing comparison.
The operator clarified that no deliberately configured Chrome profile was part
of this acceptance task. Exact browser-data-directory identity is therefore not
an MVP release gate. Chrome reopening and saved-document persistence passed;
Google-account sign-in, browser sessions and profile-content persistence are not
claimed. The physical-host recovery acceptance passes within this scope.

This is operator-assisted recovery: host FileVault unlock/login and explicit VM
startup were required. Automatic recovery is not claimed. The separate laptop
VM, its agent, and its services were not modified. Private identities, document
contents, hashes, boot IDs and captures are excluded from this record.
