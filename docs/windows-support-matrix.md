# Windows support and input matrix

This is the Windows release-candidate scope in PR #28. It is not a promise that
every Windows edition, application or input route works.

## Platform scope

| Area | Qualified scope | Outside this release claim |
| --- | --- | --- |
| Guest | Windows 11 Enterprise Evaluation, x86-64, reviewed Microsoft installation media | Home/Pro, ARM, other releases/editions, arbitrary images, evaluation-to-retail conversion |
| Host | Linux x86-64 with KVM/libvirt, UEFI Secure Boot and virtual TPM; dedicated domain/network and runtime identities | Lume Windows guests, other hypervisors, cloud-host qualification, GPU/host-device passthrough |
| Driver | Pinned CuaDriver 0.49.3 artifact with recorded digest/provenance; Limited interactive standard-user task | Floating driver updates, elevated/SYSTEM or Session 0 desktop control |
| Hermes | Installed native provider over restricted SSH/MCP, including Linux Docker | Cached cross-profile provider reuse; unrelated profiles must not inherit another profile's installation |
| Viewer | Private Unix VNC console relayed over SSH, authenticated loopback web viewer, human reservation | Public VNC/TCP exposure, multi-user remote desktop, clipboard/file-transfer promises |
| Recovery | Guest cold-start file persistence; lock/unlock, sign-out/in, driver/gateway restart and recapture | Automatic sign-in/unlock, automatic replay of uncertain actions |
| Linux host restart | **Not qualified: operator explicitly skipped the physical-host reboot test.** The dedicated firewall service restart was tested. | A claim that service restart proves full host-reboot recovery |

The support claim is **Windows 11 Enterprise Evaluation on Linux x86-64
KVM/libvirt**, subject to the manual handoffs below. It does not certify licensing
or activate Windows. Home/Pro are a separate follow-up.

## Desktop operations

“Qualified” means the recorded tasks exercised this route; it does not mean
unattended operation in every app. The model must stop at a refusal or uncertain
outcome, even if another input mode might work.

| Operation | Release-candidate status | Required behavior / limit |
| --- | --- | --- |
| Desktop/window screenshots and window discovery | Qualified, including fresh-process and same-process recovery | Capture again after dialog/window changes, handoff or another writer. Doctor READY is not screenshot evidence. |
| Discovered application launch/focus | Qualified for tested apps | Use discovered identities and explicit window IDs; do not guess shell coordinates or bypass foreground activation refusal. |
| UI Automation element invocation | Qualified for the tested Notepad/dialog controls | Use only an advertised `invoke` action and a fresh exact-window capture. No generic AXPress substitution. |
| Foreground typing and shortcuts | Qualified for Notepad save/close/reopen and file dialogs | Explicitly request foreground delivery. Ctrl+S/Ctrl+O must not silently fall back from a refused background action. |
| Filename editing | Qualified through focused foreground text/key input | CuaDriver's editable ComboBox child `set_value` route is refused before dispatch. Confirm focus and the complete resulting path before submission. |
| Last-window close | Qualified for the tested advertised foreground close control | The narrow post-click warning reconciliation verifies the exact target disappeared. It does not forgive arbitrary focus errors. |
| Browser viewer mouse and keyboard | Exercised in installation/login, session maintenance and post-upgrade Notepad typing with explicit Shift events | Reserve human control and focus the guest canvas. Browser/host shortcuts can stay local; guest menus are the fallback. |
| Bulk DevTools “type text” into noVNC | **Not qualified** | The observed automation action dropped Shift. Explicit key-down/up sequences worked. This does not establish a physical-keyboard defect. |
| Model-driven pixel clicks, right/double clicks, scrolling, drag/drop and broad UIA coverage | **Not generally qualified by the Windows acceptance task** | Some provider routes exist, but the tested save task does not certify them. Unsupported driver/schema actions must refuse; do not advertise universal GUI coverage. |
| Background text/shortcuts in arbitrary apps | **Not release-qualified** | App behavior varies; modern Notepad shortcuts failed on this route. No automatic background-to-foreground escalation. |
| Clipboard sync, secure-desktop/UAC automation and administrative desktop actions | **Not part of the support claim** | Keep privileged work with the operator. Do not elevate the driver to bypass refusal. |
| Pause/reserve/return and stale/uncertain input | Qualified | Agent writes stop while human/paused. Returning control requires recapture. Unknown write outcomes require inspection and explicit acknowledgement, never replay. |

## Onboarding handoffs

Start with the [Windows guide](windows-onboarding.md), not the macOS/Lume sequence.
Hermes can save the plan and guide the process from the first step; privileged
host setup and consent remain explicit operator actions.

| Checkpoint | Operator action | Resume / verification |
| --- | --- | --- |
| Trust and host preflight | Supply Linux/KVM resources, verified media, license consent, independently confirmed SSH host key and restricted temporary setup access. | Run remote preflight from the intended Hermes profile. |
| Build completed | Review generated configuration; administrator registers the new stopped domain, roles and persistent security. Restrictive `umask 077` is supported. | Run firewall, relay and keys stages. A partial registration requires inspection, not blind rerun. |
| Runtime/viewer pairing | Set the runtime alias, VM name, guest profile and `computer_use.backend: ownmachine`; share the configured control directory with correct user permissions. Keep the viewer key/token outside Hermes. | Start viewer and run doctor. |
| First boot | Open the private viewer and handle the initial DVD boot prompt. Let later boots use the installed disk. | Resume provision; use the displayed OpenSSH/time-sync progress and allowlisted reason. |
| Bootstrap waiting/failure | Follow the matching reason: DNS/NTP, OpenSSH installation, or bootstrap failure. Preserve the disk/checkpoint. | `setup --run progress`, `setup --next`, doctor, then only the indicated stage. |
| Harden and driver | Stay signed into the standard account; finish hardening before driver control. Windows does not need macOS Accessibility/Screen Recording grants. | Bounded driver/permissions polling, doctor, fresh capture. |
| Final verification | Return control to the agent and allow serial capture/verification. | Verify both roles and private console, then automatically retire setup keys and confirm rejection. |
| Pause for later | Ask for an opt-in reminder preview and confirm it only if wanted. | [Reminder instructions](onboarding-reminders.md); same profile/sender and plan, with delivery-time checks. No reminder is scheduled automatically. |

See [maintenance and rollback](windows-maintenance.md) and
[acceptance evidence](windows-kvm-acceptance.md). Host crashes during disk writes,
arbitrary partial-registration repair and cross-version configuration migrations
remain outside the tested automatic-recovery path.
