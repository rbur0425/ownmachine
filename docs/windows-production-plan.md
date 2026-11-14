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
      Earlier fixtures exposed and qualified fixes. One final fixture now passed
      repair-free installation, screenshot and automatic retirement from one fixed
      source commit; a second clean run and broader interruption cases remain.

## Runtime acceptance

- [x] Supervised real Hermes browser navigation, Notepad save/reopen and independent file readback.
- [x] Genuine guest cold boot preserves a saved file; driver recovers after operator sign-in.
- [x] Run installed-Hermes doctor and a real-model read/capture task through the production relay.
- [x] Repeat a supervised write/save task from a fresh Hermes installation.
      An isolated Docker install saved and reopened the fresh guest's Notepad
      document; independent UIA and visual checks matched the exact text. Closing
      the last tab needed inspection/acknowledgement of a driver focus warning.
- [ ] Qualify uninterrupted save/close/reopen and mixed-profile provider loading.
- [ ] Exercise combined restart, lock/unlock, sign-out, driver restart and gateway restart.
- [ ] Qualify input modes and prerelease-driver update policy; document unsupported actions.
- [ ] Test Windows editions separately; keep claims within the tested matrix.

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
