# Windows production integration and release qualification

Work continues in PR #28; do not release until the acceptance gates below pass.
The supported target under qualification is Windows 11 x64 on Linux/KVM.
The Enterprise evaluation spike does not certify Pro, Windows ARM, cloud hosts,
GPU passthrough or arbitrary hypervisors.

## Production runtime and persistent security

- [x] Add a KVM adapter behind the production host entrypoint, preserving Lume behavior.
- [x] Pin domain and network identities; refuse TCP consoles and host-device shares.
- [x] Require a standard interactive guest session before MCP dispatch.
- [x] Implement a root-owned persistent firewall service and live read-only security probe.
- [x] Preserve graceful shutdown when readiness fails; disable VM autostart.
- [x] Install the production components on the test host and switch both forced commands after checks.
- [x] Recheck actual agent/viewer boundaries, guest network isolation and private viewer input.
- [x] Test firewall drift refusal and restoration with an additional restrictive rule.
- [x] Test dedicated firewall service restart and restoration.
- [ ] Test physical-host reboot recovery.
- [ ] Review existing policy conflicts, rollback and upgrade behavior; no global firewall flushes.

A runtime key may invoke only its exact root-owned security probe through sudo;
it cannot apply policy, choose another config, run commands or install files.
The probe reads the live nftables table rather than trusting a readiness receipt.
The policy, libvirt ACL configuration and runtime configuration must match the
root-owned manifest. Network identity, bridge/subnet and disabled autostart are
checked again. The systemd service restores only this VM's firewall table.
Administrator changes remain trusted; this is not isolation from root.

## Hermes-driven setup

Fresh provisioning and automatic retirement now have an implementation in PR #28.
Individual live stages are checked below; pristine end-to-end installation remains
a separate qualification gate. Completed checks and remaining limits are recorded in the
[acceptance report](windows-kvm-acceptance.md#fresh-provisioning-implementation-checkpoint).
Follow the [fresh-install guide](windows-onboarding.md#fresh-install-implementation-under-test)
for the administrator and runtime-key handoffs.


- [x] Add the Windows choice and Linux host preflight to the saved plan and wizard.
- [x] Exercise plan save/resume guidance in installed Hermes.
- [x] Exercise authenticated Windows remote preflight/progress, replay refusal and test-key revocation.
- [x] Exercise the remaining mutating stages through Hermes.
- [x] Bind each stage to reviewed source, plan, separate setup identity and pinned host key.
- [x] Check KVM, storage, QEMU, libvirt ACLs, firmware, TPM and verified installation media.
- [x] Render portable domain/network/media configuration without overwriting existing disks.
- [x] Prompt for evaluation/license consent and administrator actions before mutations.
- [x] Install standard guest account, pinned driver and narrowly restricted guest SSH.
- [x] Remove answer-file secrets, one-time login, setup tasks and bootstrap media.
- [x] Install both runtime roles and the separately owned private viewer.
- [ ] Use doctor and saved progress to explain exact manual handoffs and reminder options.
- [x] Verify both runtime roles, private console and computer_use capture, then retire setup keys.
- [ ] Run two clean installations, including non-default paths/names and interruption/resume.
      Operator acceptance at `01f60ae` adds a distinct clean guest, new paths/identities,
      and client disconnect/resume with unchanged state. Broader mid-stage interruption
      cases remain; do not equate a between-stage client restart with crash recovery.

## Runtime acceptance

- [x] Supervised real Hermes browser navigation, Notepad save/reopen and independent file readback.
- [x] Genuine guest cold boot preserves a saved file; driver recovers after operator sign-in.
- [x] Run installed-Hermes doctor and a real-model read/capture task through the production relay.
- [x] Repeat a supervised write/save task from a fresh Hermes installation.
      An isolated Docker install saved and reopened the fresh guest's Notepad
      document; independent UIA and visual checks matched the exact text. Closing
      the last tab needed inspection/acknowledgement of a driver focus warning.
- [x] Qualify save/last-window close/reopen without manual recovery.
      The isolated Hermes rerun verified closure through read-only checks and
      reopened the exact saved content; normal per-action approvals remained.
- [ ] Qualify mixed-profile provider loading.
- [ ] Exercise combined restart, lock/unlock, sign-out, driver restart and gateway restart.
- [ ] Qualify input modes and prerelease-driver update policy; document unsupported actions.
- [ ] Keep initial support claims limited to the tested Enterprise Evaluation matrix.
      Home/Pro installation and qualification are deferred until after PR #28.

## Operator-review regression qualification

- [x] Recreate only the approved qualification guest with the reviewed fixes.
- [x] Verify stopped-driver health reports guest reachability separately.
- [x] Verify a failed driver read reconnects on the next explicit read without
      input replay or a control-state change.
- [x] Verify default AC/DC display and standby settings are disabled, and the
      standard driver returns without a visible console after cold-start/sign-in.
- [x] Repeat real-model read-only capture through installed Hermes with only the
      computer-use toolset, then guided screenshot verification and setup retirement.
- [x] Capture after more than six minutes without input (view-only viewer connected).
- [x] Check configured local time after a genuine guest shutdown/start.
- [x] Ensure correct time in the first installed session before that cold start.
      Operator acceptance at `01f60ae` passed without manual time changes.
- [x] Implement distinct OpenSSH/clock checkpoints and a read-only guest progress window.
- [x] Carry allowlisted recovery reasons into authenticated progress and next-step guidance.
      Operator acceptance confirmed phase messages; automatic window closure now
      has a regression fix and still needs a follow-up desktop check.
- [x] Capture after six minutes with all desktop clients disconnected (operator verified).

These are fresh-guest results on an existing host. They do not complete the broader
session/recovery, upgrade, or physical-host reboot gates above.

## Release qualification — explicitly held

- [ ] Green final-head CI, plugin validation, bundles and checksums.
- [ ] Publishable installation, recovery, upgrade and security documentation.
- [ ] **New release images showcasing Windows, macOS and Omarchy as supported OSes.**
      Produce these only with accurate qualification labels; do not imply Windows
      is released before its acceptance gates pass.
- [ ] Update README, support matrix, catalog pin and release notes through Gitflow.
- [ ] Obtain explicit approval to merge/release; this development request does not authorize either.

See [acceptance evidence](windows-kvm-acceptance.md) for completed tests and their
limits. A checked implementation item is not a claim of live deployment acceptance.

## Deferred follow-up after PR #28: Windows Home and Pro

Explicitly outside this initial PR and not a blocker for its Enterprise Evaluation
scope. Do not advertise Home/Pro support until this follow-up is qualified.

- [ ] Add a portable, configurable bring-your-own-media and license installation
      path for Windows 11 Home and Pro, with explicit edition/image selection.
- [ ] Document edition-matched activation and license requirements for the VM;
      do not present a Home/Pro key as activating the Enterprise evaluation.
      Keep product keys out of chat, logs and repository files.
- [ ] Test each edition independently: fresh setup, account/sign-in requirements,
      hardening, driver/control, viewer, model file tasks and restart persistence.
- [ ] Update the support matrix and onboarding guides only for qualified editions.

## Existing-domain administrator workflow

The scripts below adopt an already reviewed domain and dedicated accounts. For a
fresh guest, use the separate build/registration/provisioning sequence in the
[fresh-install guide](windows-onboarding.md#fresh-install-implementation-under-test).
Keep operator JSON outside the repository.

1. `scripts/install-kvm-security.py --config INSTALL.json` takes a `runtime` object
   and a `bridge`. The runtime fields are validated by `host/kvm_backend.py`:
   domain/network names and UUIDs, separate agent/viewer accounts, QEMU identity,
   private console path/group, guest network, pinned guest SSH key/known-hosts,
   standard guest username, driver executable and health-script paths. The
   installer pins its own security helper. `--prefix` selects the root-owned
   installation directory. Existing different files are refused.
2. `scripts/activate-kvm-runtime.py --config ROOT_CONFIG.json --test-drift` checks
   both roles, refuses a changed live firewall, restores it, and updates only each
   role's single existing forced-command key. Backups remain available to the
   administrator. Ambiguous key files are refused.
3. `scripts/check-kvm-boundaries.py ROOT_CONFIG.json --restart-firewall` checks
   service restoration and role isolation using never-started fixtures. It does
   not reboot the host or guest.
4. Review code updates before running `scripts/update-kvm-runtime.py --config
   ROOT_CONFIG.json --source-dir REVIEWED_HOST_DIRECTORY`. Existing processes
   retain their loaded code; new SSH sessions load the replacement. Hashed backups
   are root-only. Revalidate the installed plugin and live driver afterward.

All four are explicit administrator operations. Hermes runtime cannot invoke them;
its sudo authorization permits only the exact read-only security probe. Do not
replace this boundary with general sudo, a Docker socket mount or broad libvirt
permissions. The operator supplies the host's existing libvirt/QEMU dependencies;
this installer does not restart those services to change their access driver.
