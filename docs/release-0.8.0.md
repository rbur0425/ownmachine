# OwnMachine v0.8.0 — release candidate notes

This candidate adds ARM64 Omarchy foreground desktop support on Apple Silicon,
Hermes-driven resumable installation, and VNC credential isolation fixes for
**both macOS and Linux guests**. macOS remains the default. Background Omarchy
control remains experimental. Publication is held until the release checklist
below is complete; this document is not an announcement of availability.

## Required upgrade for existing installations

Updating the Hermes plugin alone does **not** apply the host security fix.
Previously patched Lume builds could export VNC credentials through an implicit
`lume-config` guest share or a guest-home `.vnc.env` copy. The new common patch
removes both exports, including macOS normal and recovery startup paths.

1. Pause the agent, save all guest work and arrange a maintenance window. Stop
   active Hermes desktop sessions. Preserve the guest disk and configuration;
   plugin upgrade backups do not back up VM disks.
2. Build Lume from the reviewed candidate's full-source bundle or checkout using
   `scripts/build-native-lume.sh`. Choose a **new**, operator-owned build directory
   and app destination with `OWNMACHINE_NATIVE_BUILD_ROOT` and
   `OWNMACHINE_NATIVE_APP`; the builder refuses to overwrite an existing app.
   Keep `OWNMACHINE_LINUX_GUESTS=0` for the macOS build, or explicitly use `1` for
   the Linux-capable build. Do not substitute an unpatched stock Lume download.
3. Gracefully shut down the guest through the existing viewer/relay. Confirm it
   has stopped. **Shutdown is required; suspend, save-state and snapshot resume
   are not equivalent. Never resume a saved machine state from the old build.**
4. Confirm the selected VM's Lume JSON listing reports `savedState: false` and
   inspect the selected storage directory for `state.vzvmsave`/`state.vsock`.
   If saved-state artifacts exist, stop and obtain operator recovery assistance:
   preserve the disk and state for review, and explicitly decide how to discard
   volatile saved state before proceeding. Do not launch it just to clear the
   flag, silently delete it, or treat relay `start` as a cold-start guarantee.
5. Deploy the verified new app and the matching relay/setup source while the VM
   is stopped. Point the operator configuration at that app and the **same**
   configured VM/storage. Verify its signature, upstream revision and complete
   patch inventory. Recheck required PF/application-firewall readiness; if the
   app identity/path changed, an administrator must register that exact app again.
   Keep old binaries only for investigation, not as a security-fix rollback path.
6. Cold-start through the **viewer-role relay**, not manual `lume run`, native
   saved-state resume, or the agent key. A relay start generates a new private
   VNC password and uses the protected password-file interface. Keep agent
   control paused while checking readiness.
7. Verify the guest booted, the private viewer and read-only computer_use capture
   work, and the agent/viewer role restrictions remain in force. Verify no
   `lume-config` share is attached and no new guest `.vnc.env` is written. A
   pre-existing copy is not automatically erased; the new password invalidates
   it. Do not print the password, publish it, or copy it into the guest.
8. Validate the updated plugin and doctor, then explicitly return control after
   a fresh capture. If the first read sees the pre-shutdown closed transport,
   inspect the guest and request a new read-only capture. Never replay uncertain
   input. Keep backups until the installation passes its own acceptance checks.

The patch prevents new exports; it cannot retract old copies. Cold-start password
rotation is essential. Neither a plugin-only upgrade nor restoring an older VM
saved state completes this security upgrade. Retain the required firewall and
private account/storage permissions throughout.

## Linux driver pin and upgrade policy

The reviewed Linux CuaDriver pin is **0.47.19**. Treat the integration as
preview-grade even though upstream describes plain SemVer versions as stable and
uses GitHub's Pre-release label to avoid monorepo Latest-tag collisions. The label
alone is neither a reason to silently upgrade nor evidence of compatibility.
The separate macOS driver remains at its independently reviewed pin.

- Install only an explicitly reviewed version, archive SHA-256, Sigstore issuer
  and exact workflow/tag identity. The current values are recorded in the
  [plan](omarchy-plan.md#security-review-follow-up). Never resolve `latest`,
  follow a moving branch, or disable signature checks to get a build working.
- No automatic driver promotion. A newer stable/reviewed upstream release must
  arrive through a versioned OwnMachine PR with updated hashes/identity and
  dependency/security review. Review its changes and compatible Hermes/tool
  schema, not just the release label.
- Before promotion, require source and packaged-plugin validation, supported
  platform CI, a fresh guided install and interruption/resume, hardening and
  human-control refusals, independent Chromium/editor model-task verification,
  viewer input and guest restart/read-only capture recovery. Record exact driver,
  compositor, compiler and app versions and retained failure cases.
- Rolling Arch/Hyprland/compiler updates are operator decisions. They can break
  the native input module ABI. Recheck readiness after updates; rebuild only
  against the reviewed exact ABI and retest input. Never bypass the mismatch
  guard or infer input readiness from a successful screenshot.
- If a regression or security advisory invalidates the pin, pause the affected
  automation and document the affected configuration. Upgrade only through a
  reviewed fix. A rollback must retain the VNC export-removal patch and pass the
  same security/readiness checks; do not restore exposed saved-state devices or
  weaken isolation to regain functionality.

Foreground Chromium requires explicit native-module opt-in. Background keyboard
control has bounded GTK evidence only; broad background, Qt, XWayland, cloud Mac
and every-application reliability are not claimed.

## Release gates

- [x] Implementation and Studio acceptance head
  `42609662a0fb3a4db4c7009bba3ac1c96fe0f56f`: macOS and Ubuntu
  [CI passed](https://github.com/rbur0425/ownmachine/actions/runs/43320207309).
  This is the feature baseline, not a substitute for final release-head validation.
- [x] Fresh final-security Omarchy install, real-model tasks, human gate and restart:
  [independent evidence](omarchy-final-acceptance.md).
- [x] Live macOS guest cold start through the relay on the new macOS-only build,
  with no saved state, independent boot/credential-share checks and live noVNC:
  [hardware evidence and retained diagnostic failure](macos-cold-start-acceptance.md).
  Follow-up onboarding and CuaDriver consent passed; a real Hermes Safari task
  reached Google after one operator-reviewed recovery. This is not a background-only
  or uninterrupted autonomous pass; see the same evidence document.
- [ ] Revalidate the exact release head, packages/checksums and current-head CI
  after final edits.
- [ ] On the release branch, remove development banners/wording and update release
  links/version/pin coherently. Do not imply v0.7.0 contains Omarchy.
- [ ] Obtain authorization before Gitflow merge, tag, artifact publication and
  catalog-pin changes.
