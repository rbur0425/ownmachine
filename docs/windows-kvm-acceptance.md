# Windows KVM development acceptance

Windows is an experiment in this branch, not a released support claim. The Windows development setup choice saves a plan and runs authenticated provisioning, hardening, verification and setup-key retirement. Final pristine-install qualification remains in progress; implementation alone is not a passing acceptance result. Existing macOS and Omarchy behavior is preserved. Operator components are under [experiments/windows-kvm](../experiments/windows-kvm/README.md); no deployment addresses, keys, seed media or raw desktop captures belong in Git.

## Tested baseline — 13 November 2026

Linux x86-64 with hardware KVM, QEMU 10.2.1, libvirt 12.0.0, OVMF Secure Boot and software TPM 2.0. The disposable guest uses Windows 11 Enterprise 90-day evaluation, four vCPUs, 8 GiB RAM and a 96 GiB sparse SATA disk with inbox e1000e networking. This does not qualify Windows Pro, virtio, GPU passthrough, Windows on Apple Silicon or cloud providers.

CuaDriver 0.49.3 Windows x86-64 is a **prerelease**. Archive SHA-256: `1f8caf9b0a5577c559d95f12cfc55584bad32edffe5b49f5e700ed3ddc573566`. Sigstore verification passed with identity `https://github.com/trycua/cua/.github/workflows/cd-rust-cua-driver.yml@refs/tags/cua-driver-rs-v0.49.3` and issuer `https://token.actions.githubusercontent.com`. The installed PE signature was Valid. The driver runs under a standard guest account in its interactive session with a Limited scheduled task; Secure Boot and TPM readiness were independently confirmed.

## Security and transport

- Dedicated agent/viewer identities see only the assigned VM. Other-domain reads/mutations and QEMU monitor access are denied. Actual open/connect checks confirmed that only the viewer reaches the private console socket and only the agent reads the guest runtime key.
- Forced SSH commands separate agent status/MCP from viewer console/lifecycle. Shell requests and cross-role operations were refused.
- Browser streaming works through the private Unix console and restricted SSH relay. There is no TCP VNC listener. The new no-auth RFB path requires explicit Windows/private-Unix configuration and exact relay metadata; released Lume/password-VNC configurations cannot silently downgrade.
- Guest probes could not reach host SSH or the tested LAN SSH endpoint, while public HTTPS worked. These sample the policy, not every address/port. The spike firewall was session-only; the production persistence follow-up below supersedes that limitation.
- Permanent autologin is disabled; bootstrap task, guest seed secrets and cached answer files were removed, and installation media ejected. Temporary setup administration remains solely for acceptance and must be retired afterward.

## Real Hermes results and targeting corrections

An isolated Docker Hermes profile with the configured Qwen3.8 model opened Edge and reached Google using only computer_use. Both the HTTPS address and page were independently observed in the private viewer. Inputs used per-action operator approvals: this is supervised model acceptance, not autonomous approval-mode certification.

The initial Notepad attempt guessed a taskbar coordinate and hit a driver exact-HWND activation refusal. OwnMachine stopped writes for operator review. A later identity-based launch succeeded; exact UIA value assignment produced the requested document text. Batched foreground typing had delivered incomplete text, which the model detected rather than treating as success.

The adapter now resolves Windows display names through unique discovered process identities, recognizes advertised UIA `invoke` actions, and maps explicitly foreground modifier shortcuts to the driver's modifier-capable `press_key` API. The driver's XAML `hotkey` path otherwise searches visible menu accelerators even for foreground requests. Exact window admission, capture invalidation, per-action approvals and the human-control gate remain enforced; no automatic fallback or elevation was added.

Hermes's category-provider loader retained the old module across normal plugin reloads and profile changes in the tested gateway. The live acceptance uses a test-only provider directory alias in a separate profile to load the new module without restarting production. This is test deployment plumbing, not a production plugin rename. A normal fresh process loads the standard `ownmachine` package. Source is not patched into Hermes core.

The corrected provider completed the Notepad save through real Hermes: foreground Ctrl+S opened a separately discovered Save As window, Hermes entered the full destination and pressed Return, and the final capture showed a saved title without an unsaved marker. Independent administrative readback confirmed the exact requested 54 bytes, SHA-256 `e739a1fa0f7e83389905acea18361db016a4494d452f9749796be9a3adc6ad91`. No file-writing shell or API completed the model task.

The viewer's graceful shutdown succeeded. Its subsequent start was refused by libvirt because the original per-domain policy omitted network dependencies. `update-network-acl.py` is a reviewable administrator step scoped to the viewer and the configured dedicated network/ports; it does not restart services. Do not share that network with unrelated VMs. After applying it, viewer start succeeded. The operator reran all 18 boundary checks, including configured versus unrelated network reads/mutations, and reported all true. The combined restart initially failed at start; the subsequent separate viewer stop/start cycle passed.

The portable read-only `probe-saved-file.py` compares exact content and SHA-256 and records the guest boot timestamp, independently of model claims. The first shutdown/start exposed Windows Fast Startup: the file survived but the boot timestamp did not change. Provisioning now disables hibernation and rejects failure to do so. After applying that setting to the test guest, viewer stop/start changed the boot timestamp and preserved all 54 bytes and the identical SHA-256. After operator sign-in, the standard-user interactive driver returned to ready without repair. Permanent autologin remains off.

Post-boot real Hermes acceptance also reopened the saved file and read its exact text. This run needed operator intervention: UIA `set_value` on the Open dialog's filename Edit was resolved by the driver to its enclosing ComboBox and refused with `option_not_found`. OwnMachine blocked writes for review. After independent visual inspection and explicit acknowledgement, the model took a fresh capture, used explicitly foreground typing into the focused filename field and Return, then captured the reopened document. Independent readback again matched the original hash. This is a supervised passing recovery path, not proof that filename ComboBox value assignment or unattended recovery works. App launch reported a window-discovery timeout before a subsequent window listing found Notepad; delayed launch discovery also needs further qualification.

## Filename-control compatibility fix

CuaDriver 0.49.3 routes native ComboBox child Edit values through option selection, so a free-form filename can fail even though the snapshot advertises `set_value`. OwnMachine now follows snapshot parent indices to identify Windows Edit descendants of ComboBoxes, removes that unsupported action from the model-facing capture, and preflights an attempted value write without dispatching it. Plain Edit fields and ComboBox option selection are unchanged. The capture explains how to use explicitly requested foreground keyboard input after confirming focus, followed by value verification. There is no automatic input-mode fallback, filename-specific label matching, or review-gate reset. Existing human/paused/pending gates still take precedence. This is an adapter compatibility fix; it does not patch the upstream driver's native ComboBox implementation.

Tests cover capability filtering, no dispatch/no pending marker for the unsupported operation, preserved plain-edit and combo-selection routes, explicit typing, capture invalidation, platform scoping, human takeover and pre-existing uncertain outcomes.

### Live rerun

The updated installed plugin completed a real Docker Hermes save-and-reopen test with the same Qwen3.8 model. The filtered capability note appeared in live dialog captures. The model saved the 48-byte text `OwnMachine filename control acceptance verified.`, opened its path through Notepad's Open dialog, and captured the matching document. Independent administrative readback before and after reopen matched SHA-256 `d2b923a103a18f5195db54e7b19a097b66ba20cf829c97711bed5d2b9f8ef71c`; the viewer independently showed the same text. No filename-control failure, manual desktop input, or pending-action acknowledgement was needed during the passing sequence.

This was guided, supervised acceptance: per-action Allow once approvals remained enabled; explicit foreground keyboard delivery, English-guest filename focus guidance and sequential exact-dialog captures were supplied. An earlier general attempt was stopped before a background shortcut; another timed out on dialog navigation. The passing save run also reached its configured wall-clock budget before reopening, so a continuation completed Open without changing VM state or resetting a gate. This demonstrates the corrected filename path, not unattended general Windows reliability. The existing saved file from cold-start acceptance was preserved. Guest restart persistence was established earlier and was not repeated for this adapter-only change.

## Remaining graduation work

- Complete broader lifecycle qualification; the supervised saved-file, genuine guest cold-boot persistence and post-login driver checks passed. Host reboot is a separate, untested Windows surface.
- Qualify Windows foreground typing, shell/Start targets, background input, lock/sign-out and broader UIA behavior. Do not elevate the daemon to work around refusals.
- Integrate health/forced guest-key setup into fully clean provisioning and retire temporary setup keys automatically.
- Finish guided provisioning and rollback qualification; persistent policy and Windows doctor integration are implemented in the production follow-up below.
- Replace or explicitly qualify the prerelease driver pin; test additional Windows editions/hypervisor configurations separately.

The updated provider regression run passed 423 tests. Installed-plugin validation passed with the expected in-process callback and CLI-registration warnings. No production support claim follows from these checks.

Network ACL design follows [libvirt object-scoped Polkit policy](https://www.libvirt.org/aclpolkit.html) and [network-port API permissions](https://libvirt.org/html/libvirt-libvirt-network.html). Offline CI initially rejected the newly added Hermes-dependent tests as undeclared skips; their explicit platform declarations now accompany the tests. They passed in the local Hermes-backed 420-test run.

## Production adapter and persistence follow-up

The KVM adapter now runs behind the production host entrypoint. Runtime code,
configuration and guest key are root-owned; only the agent's dedicated group can
read that key. Domain/network identity, private console configuration and guest
standard-session readiness are checked before control. A narrow, read-only sudo
probe compares the live nftables rules with the installed policy and checks the
root-owned policy/configuration, network bridge/subnet and disabled VM autostart.
The installed systemd service restores only its dedicated table. An unsafe state
refuses access; graceful shutdown remains available.

Live administrator installation passed on the test host. The prerequisite check
initially misread a blank line before an enabled libvirt ACL directive; that parser
was corrected without restarting libvirt. Both production role probes passed,
cross-role operations were refused, and an extra restrictive DROP rule caused
readiness refusal. Restoring the intended table restored readiness. Both runtime
keys were then switched to the root-owned relay. The service reports enabled and
active; **physical-host reboot recovery is not yet tested for this backend**.

The browser connected to the production private console. Human reservation,
display wake input and return to paused mode worked; the previously saved Notepad
text remained visible. No VM or daemon restart was needed. The installed-plugin
doctor check exposed a Lume-only assumption; Windows-specific doctor checks now
have regression coverage and passed in an isolated installed Hermes profile.

See [the production checklist](windows-production-plan.md) for remaining setup,
release-image and qualification gates. These implementation/live checks do not
turn the earlier spike into a released Windows support claim.

Two end-to-end failures were fixed before accepting production MCP. The new
firewall initially dropped replies to host-initiated guest SSH; it now admits
established reply-direction traffic while retaining the guest-initiated host
block. After a dedicated firewall-service restart, guest probes still could not
reach host/LAN SSH and public HTTPS succeeded. All 18 production boundary checks
passed. The service's boot apply path installs/checks nftables without querying
libvirt, avoiding a boot-order dependency cycle; runtime checks still inspect
libvirt state. Physical host reboot remains a release qualification gate.

The MCP readiness subprocess originally inherited protocol stdin and could consume
the client's initialization message. It now receives DEVNULL; tests cover that
stream boundary and refusal of an unhealthy session. Installed Hermes doctor then
passed all readiness checks, with only the intentional paused-control warning.
A real Qwen3.8 Hermes run discovered/captured the existing Notepad window and read
its exact 48-byte sentence through the production relay. The private viewer and
independent file readback agreed. This was a read-only production transport test;
the earlier save/reopen test remains the write-task evidence.

Installed Hermes also saved a Windows plan with non-default storage/disk settings
and returned the expected temporary-key pairing handoff on `setup --next`.
Windows fresh provisioning and final verification/retirement are explicitly
blocked until their stage integration is finished; no macOS installer fallback
or fabricated completion is used. The Windows setup endpoint reuses source/plan
binding, authenticated progress import and interruption handling.

Final local regression validation: the complete 448-test suite passed. Installed-plugin validation passed with the expected in-process hook
and CLI-registration warnings. The live deployment preceded the last restart
revalidation safeguard; that safeguard is unit-tested, while another physical
host/guest restart is not claimed here.

### Authenticated onboarding preflight

Installed Hermes executed Windows preflight on the Linux host through a separate,
temporarily paired forced-command key. The endpoint allowed only preflight and
progress, and bound requests to the reviewed source and saved plan. The remote
preflight returned `observed`; a subsequent command imported that authenticated
checkpoint, and `setup --next` advanced to `await_build`. Reusing the request nonce
was refused. No VM was provisioned or changed by this test. The exact temporary
key was removed afterward while preserving unrelated authorizations, and a new
SSH attempt with it was rejected. This test cleanup was manual, not evidence that
the unfinished automatic retirement flow has passed.

### Fresh provisioning implementation checkpoint

PR #28 adds artifact preparation, a separate administrator registration handoff,
fixed guest bootstrap/hardening operations, a private viewer service, final
console/screenshot verification, and guest-then-host setup-key retirement. These
are implementation changes, **not yet clean-guest acceptance results**.

At checkpoint `4713252`, a separate Hermes profile installed the exact development
commit using the public plugin installer with explicit dependency consent.
Installed-plugin validation passed, with the expected in-process hooks and local
CLI registration notices. Hermes saved a non-default Windows plan, ran real SSH
preflight against its separate restricted setup endpoint, imported progress on a
later command, and advanced to the build handoff. No new VM was created by these
checks. Existing Windows guests were preserved.

The complete local suite passed **456 tests**, including refusal of MCP before
hardening. The revised hardening/retirement PowerShell script also passed the
native Windows parser without executing its mutations. Ubuntu and macOS CI
passed on implementation checkpoint `4713252`. The clean media build is waiting for an administrator
to grant the non-admin setup account read access to the existing verified ISO,
which is QEMU-owned. No installation, automatic retirement or fresh model-task
success is claimed at this checkpoint. The container also reports its preexisting
pnpm artifact warning; plugin installation and validation nevertheless passed.

At source checkpoint `9d7c4cd`, the administrator granted the setup account
read-only access to the QEMU-owned ISO. Hermes then installed that exact commit,
refreshed authenticated preflight and completed `build --apply`. The build
verified both media hashes, generated private bootstrap inputs and role keys,
created the pinned viewer environment, and recorded its artifact receipt. A
separate Hermes command imported the completed build checkpoint successfully.
No VM disk existed afterward: domain registration and boot remain separate stages.
Both macOS and Ubuntu CI passed on this source checkpoint. The next live handoff
is administrator registration of the separate stopped guest; clean guest boot,
hardening, final capture and automatic retirement are still pending.

### Registration refusal found during clean-host integration

Administrator registration created the separate stopped domain and persistent
security service. The first authenticated runtime check refused it: libvirt had
normalized the private VNC socket under its managed QEMU directory into an
automatic TCP listener. The guest never started or exposed a listener. Defining
the same stopped domain with its socket outside that managed directory preserved
the private Unix-socket definition. The renderer now also states the socket on
the graphics element, and registration verifies libvirt's normalized definition
before installing runtime authorizations or reporting success. The guide explains
the storage-location constraint.

The viewer user service installed through Hermes and is active; its shared
control directory has the intended owner and mode 0700. This is service-start
evidence, not stream or guest-input acceptance. A narrowly scoped administrator
correction to the stopped fixture's root-owned console path/integrity record
passed; the authenticated relay then started the guest. This first fixture therefore requires a repair and cannot qualify the
repair-free clean-install requirement; a subsequent clean run must exercise the
corrected registration path.


### Fresh desktop and bootstrap failure (continued qualification)

At `e5eab64`, both CI platforms and 457 local tests passed. Hermes accepted
relay/key receipts after their result stage was aligned with the authenticated
transport contract. The fresh guest installed and reached its standard-user
Windows desktop; the private web console delivered mouse and keyboard input.
Disconnecting the setup SSH client during the guest-readiness wait left the VM
running. A subsequent authenticated progress import recovered the endpoint's
`needs_attention` result without replaying provisioning. This does not test
interruption during disk creation or administrator registration.

The guest's bootstrap report then exposed a real PowerShell argument-binding
failure: the generated firewall name's suffix became a separate positional
argument. SSH never started, and hardening/verification/key retirement correctly
remained incomplete. Dynamic firewall/task names now use parenthesized string
concatenation. A native Windows PowerShell probe reproduced the original failure;
`tests/windows/bootstrap-bindings.ps1` executed all five corrected command
expressions against strict, non-mutating stubs successfully. Parser-only checks
had missed this failure. A new clean installation must qualify the fix; this
fixture is not a passing clean-install result.


### Second fresh fixture: bootstrap passed; media-normalization fix

A separate fixture using `66644dd` passed Hermes preflight, artifact build,
administrator registration, firewall, both runtime-role checks and viewer setup.
Its private console definition survived libvirt normalization without repair.
After the documented DVD-boot keypress, Windows installed and signed into its
standard user without guest-file/permission repairs. The Windows SSH-component
installation took several minutes after the desktop appeared; the initial
bootstrap checkpoint did not show intermediate progress. Authenticated provision
then reported configured, Secure Boot/TPM ready, and driver signature/hash valid.
MCP was refused before hardening.

Hermes ejected both CDs but rejected the resulting live XML: libvirt retained
`<source index="…"/>` for empty drives. A diagnostic invocation of the same fixed
guest hardening command succeeded, while Hermes's media check continued to fail.
This was not an uninterrupted end-to-end pass. The check now accepts only empty
or index-only sources and checks both live and persistent definitions; sources
with file/device/network attributes or children remain refused. Regression tests
cover retained live indexes and media still attached in the persistent definition.
No guest scripts, privileges or file ownership were manually repaired. Remaining
verification/retirement must exercise the updated host-side check; a pristine run
from one final source commit is still a separate qualification requirement.


### Verified setup and automatic retirement after host-side correction

With the reviewed `65f7a99` host source re-pinned, the previous endpoint receipts
were archived and checks rerun rather than carried forward. Hermes passed
preflight, firewall, separate runtime roles, provision, harden, driver and
permissions. Native `computer_use` screenshot verification decoded and checked a
1280×800 PNG. `verify --apply` repeated verification, disabled guest setup access,
proved its key rejected, removed temporary installation artifacts, retired the
host setup key and proved runtime readiness afterward. The receipt reported
`complete`, `setup_key_rejected=true`, `runtime_verified=true` and no pending
reminder cleanup. Doctor passed all readiness checks.

Independent follow-up SSH attempts isolated each retired identity (no fallback
keys) and both were refused. Filesystem inspection confirmed the temporary guest
setup key, seeded host key, bootstrap ISO and seed directory were absent; the disk
and viewer key remained. These are live retirement results, not mocks. The
retirement checkpoint is in the endpoint's private state directory, not VM storage.

A real-model read/capture attempt through the installed plugin succeeded. Its
one-shot input was correctly refused by Hermes's approval policy. An interactive
repeat retained per-action Allow once approvals but stopped on modern Notepad's
unsupported background new-tab shortcut and entered operator review. It did not
complete the requested write/save task. No approval policy, driver privilege or
pending-input gate was relaxed to obtain a passing result. The viewer then showed
a blank stream with the pending-review notice; review-state viewing and the
explicit foreground task path need follow-up qualification. This does not undo
setup/retirement acceptance or establish unattended desktop reliability.

A final pristine run must include the bootstrap argument and media-normalization
fixes from the beginning. The Windows viewer's unconditional red/blue swap was
also removed: normal colors are now the default, with a boolean compatibility
override. All 460 local tests pass for that change; visual confirmation belongs to
the next clean fixture. Release remains held.


### Final pristine fixture: host registration and runtime handoff

A separate fixture built from `0b4395f` passed administrator registration without
a console-path repair. The installed Hermes profile then passed authenticated
firewall, relay, separate-key and viewer-service stages. Its isolated agent key
was paired into the container; a direct runtime status check confirmed the
configured Windows domain was stopped. The viewer credential remains outside the
container's shared control directory.

Provisioning has not yet begun: browser automation was interrupted by an extension
popup before the private viewer could be unlocked. The initial DVD-boot prompt
requires an available viewer. The preceding test guest's graceful relay stop
also timed out; its inspected Windows desktop offered an update/shutdown action,
which began a restart/update sequence. No forced power-off or memory
overcommit was used. These are pending operational checks, not a clean-install
completion claim. The prior pending-review viewer displayed its desktop again;
after inspection, human reservation was explicitly acknowledged for shutdown.


### Pristine installation and automatic retirement passed

The final fixture completed from implementation commit `0b4395f` without changes
to its deployed source, guest files, privileges or ownership during acceptance.
The private viewer's initial connection missed the short DVD prompt; selecting
the Windows DVD from the firmware menu recovered boot without changing media or
disk configuration. Windows then installed and signed into its standard account.
Normal RGB rendering was visually confirmed. The post-desktop OpenSSH component
installation took roughly eleven minutes; a read-only report still showed
`awaiting_first_signin` and Task Manager showed DISM servicing. This coarse progress
message remains an onboarding polish gap, not a recorded bootstrap failure.

A separate Hermes command recovered authenticated progress while the guest was
installing. Refreshing preflight and resuming provision then passed; harden, driver
and permissions passed sequentially. No installer or guest repair was applied.
`verify --apply` checked a 1280×800 native screenshot and completed guest-then-host
setup-key retirement. The completion receipt reports runtime verified, setup key
rejected and no pending reminder cleanup. The guest retirement receipt records
positive key rejection before private setup artifacts were removed. An independent
SSH attempt with only the retired host identity was rejected. Independent host
inspection confirmed both CDs empty, the Windows disk and viewer key preserved,
and temporary seed media/keys absent. Installed Hermes doctor passed all 14 checks.

Hermes plugin validation also passed with no warnings in the acceptance profile;
it identifies the plugin as the explicitly installed catalog development ref
`9d7c4cdd`. Only this plugin is enabled among the profile's user plugins. The host
source and runtime configuration are separate from that install record. This
qualifies one repair-free fresh guest, not two fresh installations, an empty
Hermes home, physical-host reboot, or a completed model write/save task.


### Final fixture model task: text entered, save refused

Real Docker Hermes/Qwen3.8 ran a new task with explicit foreground instructions
and per-action Allow once approvals. It discovered Notepad, encountered delayed
launch discovery, captured the newly created empty document, entered the requested
line and captured the result. The subsequent request explicitly contained
`delivery_mode=foreground` and `keys=ctrl+s`, but its result reported the Windows
XAML hotkey accelerator refusal. The model stopped, reported the file unsaved and
left OwnMachine's pending-review gate intact. No manual save completed the task.
The viewer independently confirmed review-required control afterward.

The installed provider contains the Windows foreground modifier routing, and an
isolated no-dispatch probe maps that request to `press_key` with modifiers; a
no-input Hermes dispatcher probe also preserves foreground kwargs. The difference
was subsequently traced to provider loading, as described below. This attempt
itself did not pass; the clean setup, screenshot and retirement results above
remain valid independently of it.

### Foreground save and reopen: supervised acceptance passed

The live Hermes session had loaded an older OwnMachine provider from another
profile under the shared `_hermes_user_computer_use.ownmachine` module namespace.
A temporary read-only diagnostic reported that module's source path and confirmed
the new routing metadata was absent. Installing the current plugin in the target
profile alone did not replace the cached provider. No Hermes core code was patched.

An isolated Docker instance with a new Hermes home installed OwnMachine at
`178aa3a8fa6e94d7dd97df92d1994a6de5ad72b6` through the public plugin installer.
It reused only the configured agent SSH identity and existing shared control
directory, not the old profile's plugins, history or credential stores. The local
model endpoint needed no provider secret. The container's dedicated numeric user
needed a passwd entry before OpenSSH could operate; this was test-container setup,
not a guest repair. Plugin validation passed with no warnings, and 460 local tests
passed for this implementation. Hermes was v0.23.1, upstream `3b421578`.

Real Qwen3.8/Hermes then:

1. Captured the existing unsaved Notepad document and checked its exact text.
2. Sent explicit foreground Ctrl+S. Routing metadata confirmed `press_key` with
   modifiers, and a new capture confirmed Save As opened.
3. Typed the full destination into the observed filename field, saved with Enter,
   and captured the unmodified saved document.
4. Closed its last tab. The window really closed, but the driver's post-action
   foreground check reported uncertainty because the target HWND no longer existed.
   The model stopped. Independent window enumeration and the live viewer confirmed
   closure before an operator acknowledged the gate. No save or reopen was done
   manually, and the action was not retried.
5. Relaunched Notepad to an empty Untitled document, used foreground Ctrl+O to open
   the exact saved path, and captured the reopened text.

After the model exited, a separate read-only UI Automation capture and visual
inspection confirmed `ownmachine-fresh-acceptance.txt` contained exactly
`OwnMachine fresh Windows acceptance passed.` (43 characters). The SHA-256 of that
captured text's UTF-8 encoding was
`8ac49cff418c86cd1801cef837fb1e5ed8104ffad13d2aae10395b2b336773a2`.
This is independent reopened-content verification, not a raw disk-byte hash.
Private session logs and screenshots remain outside Git.

All desktop writes retained individual Allow once approvals, standard driver
privilege and the shared human-control gate. The temporary diagnostic plugin was
disabled after use. This establishes supervised save/reopen on the fresh guest
from a fresh Hermes installation, not an uninterrupted autonomous pass. Mixed
profile provider loading and last-window foreground closure remain explicit
compatibility limitations; release remains held.

### Last-window fix: save/close/reopen without manual recovery

Implementation `59b06a0e01e607f3a79c5210dd4260d808a1a2ce` adds narrow read-only
closure reconciliation within the existing write transaction. Eligibility requires
a fresh Windows Button token labelled `Close` or `Close Tab`, its advertised invoke
action, and explicit foreground single-click delivery. Only the driver's exact
post-click foreground error for that captured HWND is eligible. An unfiltered
window list must contain neither that HWND nor another window of the target PID;
the driver's separate exact-HWND lookup must then explicitly report that window
missing. Successful verification invalidates all old targets/tokens and returns
`window_closed_verified`. The original warning remains visible in metadata.
These checks verify closure from the driver's desktop-window view, not native
handle destruction or process termination; an application may close to its tray.
There is no input replay, background fallback, control transfer or acknowledgement
of an already-pending action. Unknown failures and failed verification retain the
durable review marker. This reconciles a completed close; it does not suppress
general foreground admission checks.

The isolated Docker/Hermes installation installed that immutable commit through
the public installer. Real Qwen3.8 completed one prompted task with normal Allow
once approvals: preserved the previous file, typed a new 47-character line into
an empty tab, saved `ownmachine-close-acceptance.txt`, closed the last Notepad
window, relaunched Notepad to an empty document, and reopened the exact saved path.
The close returned `verified: true` with
`closure_verification: window_list_and_exact_hwnd_missing`. No manual desktop
input, operator-review acknowledgement, prompt intervention or input retry was
needed. The model corrected a read-only ambiguous-window capture and malformed
tool-call JSON itself; these were not dispatched-input failures. The final shared
control state remained agent-controlled with no pending operation.

After the model exited, a separate fresh UIA read confirmed the reopened document
was exactly `OwnMachine save close reopen acceptance passed.` (47 characters).
Its UTF-8 text SHA-256 was
`67d555bf300fddaa99f7333c2308a486e257e807da970b22f5ae68c4982bb624`;
this hashes captured text, not raw disk bytes. All 463 local tests passed, including
negative cases for minimized/still-present windows, reused HWNDs, another window
in the process, malformed/error listings, failed exact lookups, transport loss,
non-close controls, other platforms and background delivery. Installed Hermes
plugin validation passed with no warnings. Private task evidence stays outside Git.

This supersedes the preceding last-window manual-recovery limitation for the
tested close-button path. Mixed-profile provider loading and the other release
qualification gates remain open. No release is authorized.

## Operator-review follow-up — 14 November 2026

The operator's profile-origin guard is retained. Follow-up changes discard a
failed read stream without replaying input, add bounded configurable idle and
UTC-clock policies for fresh provisioning, launch the standard interactive driver
without a closable console, distinguish health-helper failure from unreachable
SSH, preserve allowlisted firewall-drift reasons, and link onboarding to the
installed public commit. The in-process prerequisite is omitted when already set.

The reported capital loss was Chrome DevTools whole-string automation. Explicit
Shift key sequences worked; physical keyboard input was not shown to fail. No
noVNC keyboard patch is warranted from that evidence alone. Prompt disobedience
and self-editing require restricting the acceptance profile's exposed tools,
not relying on model instructions as an access boundary.

At that checkpoint, the guest changes had not been deployed. The fresh-install
results below supersede that pending status only for the checks explicitly listed.
Existing-guest upgrade qualification and the remaining release gates stay open.


### Fresh operator-review qualification — 15 November 2026

Tested implementation: `e3ef27c2953d887bbd87de4eaa158972167a92ce`.
With explicit operator approval, only the old qualification VM and its disk were
replaced. Other domain identities and states were preserved. This was a clean
Windows guest on an existing KVM host, not a pristine-host installation. Completed
receipts and the stopped viewer unit belonging to the retired installation were
archived before reusing its VM name; they were not overwritten or marked complete.

The installed Hermes plugin drove preflight, build, firewall, relay, keys, viewer,
provision, harden, driver, permissions and verification. The administrator performed
the documented host registration, and the initial DVD boot needed console input.
Windows bootstrap completed without guest repairs. OpenSSH capability installation
kept the first-sign-in checkpoint visible for several minutes; progress reporting
for that interval still needs improvement.

Live results:

- Before driver startup, guest health returned valid diagnostics: SSH/guest reachable,
  driver not ready. A stopped driver was not misreported as an SSH/firewall failure.
- The fresh guest's AC/DC display and standby timeouts were independently inspected
  and all were zero. After hardening and again after cold-start/operator sign-in,
  the standard interactive driver became ready without a visible console window.
- In one installed-provider process, an actual invalid-window driver read failed,
  disconnected its stream, and a subsequent explicit desktop capture opened a new
  stream and succeeded. Shared control remained unchanged. This tests recovery
  from a real driver error, not the precise display-sleep failure sequence.
- After more than six minutes without desktop input, capture and the same-process
  recovery probe still passed. The view-only live viewer remained connected; this
  does not certify unattended behavior with every client disconnected.
- Normal viewer shutdown reached `shut off`; viewer start cold-booted the guest.
  Runtime readiness and capture returned after operator sign-in. Other VMs stayed
  unchanged. This check did not repeat file-persistence or physical-host reboot
  acceptance.
- Real Qwen3.8 through installed Hermes, restricted to the `computer_use` toolset,
  made two desktop captures (SOM and vision), sent no input, and correctly reported
  Recycle Bin, Microsoft Edge and the taskbar clock. Independent viewer inspection
  matched the desktop. This is a read-only model test; the earlier save/close/reopen
  result remains separate evidence.
- Guided verification accepted a real 1280×800 screenshot. Automatic retirement
  completed with `setup_key_rejected=true`, `runtime_verified=true` and no pending
  reminder cleanup. An overlapping model session made an earlier client capture
  fail safely without retiring access; rerunning after that session exited passed.

Clock limitation: the configured non-UTC display zone was correct, but the first
installed session was five hours behind the host. After a complete shutdown/start,
the guest displayed the correct local time. The cold-start UTC/registry pairing
passed; correct time before that first cold start is **not qualified**. Do not use
this evidence to claim seamless initial time synchronization or arbitrary Windows
upgrade support. Private credentials, screenshots and deployment details remain
outside Git. Release remains held.

### First-session clock and onboarding follow-up — pending operator clean install

The next implementation adds a blocking Windows Time resync before bootstrap can
become `configured`, configurable NTP servers, and a narrow time-only retry through
the temporary setup key. Failed synchronization prevents hardening. The standard
user sees a normal read-only progress window while OpenSSH is being installed;
closing it does not cancel bootstrap. After SSH is ready, allowlisted reason codes
survive authenticated progress import and select local guidance/documentation and
opt-in reminder instructions. No arbitrary remote error text becomes chat guidance.

Regression checks exercise sync failure/successful retry, refusal to replay completed
bootstrap, malformed NTP configuration, atomic progress checkpoints, PowerShell
parsing/argument binding, and authenticated reason-code filtering. PowerShell OS
operations are stubbed: these checks are **not** proof of actual first-install NTP
synchronization, GUI appearance, or a second clean Windows install. The operator
will run the [clean-install checklist](windows-clean-install-checklist.md). Existing
guests were not upgraded and no VM was deleted for this change. Release remains held.


### Operator-reported second clean install — `01f60ae`

The operator reports a separate fresh Hermes container with only computer_use
available and a byte-identical plugin, new VM/network/runtime identities and no
changes to existing guests or services. Build/administrator registration and all
runtime pairing stages passed on the first attempt. Killing/reopening the test
Hermes chat preserved the plan, completed stages, domain identity and disk, with
the same next-step guidance. This verifies client disconnect/resume, not an
interrupted host mutation or physical-host reboot.

Windows reached the desktop in about nine minutes. The progress window correctly
showed OpenSSH installation. The first desktop clock was five hours behind while
bootstrap was incomplete; it became correct when bootstrap completed, before any
restart or manual adjustment. The operator's samples were 60 seconds apart, so
the brief synchronization phase itself was not visually captured. This is a live
first-session clock pass, supplied by the operator rather than independently
rerun by this agent. Hardening, driver, permissions and doctor passed; final
verification retired setup access, confirmed key rejection and preserved runtime
access. With the viewer, tunnel and chat disconnected for 6m44s, a fresh Hermes
process captured the desktop on its first attempt.

The model saved the correct 43-byte document, independently checked by the operator
character for character. This was **not an uninterrupted save/close/reopen pass**:
the default Ctrl+S route required review/acknowledgement; closing Notepad completed
but produced another foreground review while the still-open setup progress window
became foreground. The model also exhausted a 30-step budget and required a
continuation prompt. Relaunch restored Notepad's session rather than explicitly
opening the saved disk file, so reopen remains unproven for this run.

Follow-up changes close the progress window automatically at configured/hardened
checkpoints, add foreground-shortcut advice to Windows capture notes, document
review acknowledgement, and require an explicit File → Open path in the task with
an adequate iteration budget. Review gates and input routing defaults are unchanged.
Regression tests execute the actual progress callback with a stub window, including
waiting, failure, configured and hardened states. Live GUI closure and an
uninterrupted rerun of the revised model task remain pending. Private paths,
credentials and screenshots are omitted. No merge or release is authorized.


### Operator-reported follow-up pass — `1f1493d`, November 15, 2026

The operator reports that installation, the DVD prompt, first-session clock sync,
progress messages, disconnect/resume and final verification all passed again.
Verification returned `setup_key_rejected: true` and `runtime_verified: true`.
The progress window closed automatically in the same 15-second frame interval as
the clock correction. The prior false foreground warning on closing Notepad did
not recur.

The real-model task used explicit foreground Ctrl+S and Ctrl+O, reopened the saved
file through File → Open, and finished within its turn limit. No manual recovery
or continuation was reported in this run. Independent operator inspection found
the local Documents file was 43 bytes and matched the expected text exactly.
This supersedes the preceding run's manual-recovery and session-restore-only
reopen limitations for the revised task; it does not certify every app/input mode.

All clients were disconnected from 21:00:18 to 21:07:04 EST (6m46s). Doctor then
reported READY, and a fresh Hermes process captured the desktop on the first try.
The screenshot clock read 9:07 PM on November 15, matching the expected local time.

These are operator-supplied live results, not a separate rerun by this agent.
The automatic-close and revised desktop-task follow-up checks are now passed.
Mid-stage interruption, broader session recovery, Linux host reboot, maintenance
policy and final release qualification remain separate gates. No merge or release
is authorized by this report.
