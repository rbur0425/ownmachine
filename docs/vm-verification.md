> Historical acceptance record: these tests used the MacDesk name.
> The product is now OwnMachine; recorded VM/file identifiers below are unchanged.

# Guest setup verification — November 10, 2026

Test environment: Apple Silicon host, Lume 0.7.0, fresh macOS 26.6.2 guest.
No private addresses, account identities or recovery credentials are recorded here.

## Passed on hardware

- Created one persistent guest with 4 vCPUs, 12 GiB RAM, 80 GiB sparse disk,
  1440×900 display and NAT networking. Restore download and unattended setup
  completed successfully. Allocated disk was approximately 21.5 GiB afterward.
- Booted the completed guest detached with VNC disabled.
- Installed a dedicated public key and verified strict key-only SSH.
- Rotated the default account password using old-password-authenticated account
  password change, then updated autologin and the login keychain.
- Verified effective sshd configuration disables password and keyboard-interactive
  authentication and configured root SSH login disabled.
- Rebooted the guest; key authentication and GUI autologin recovered.
- A shell-created marker persisted after reboot, and the rotated password still
  unlocked the login keychain. **This is infrastructure persistence evidence, not
  the GUI-only TextEdit save acceptance test.**
- The runtime reports no VNC URL after restart. Lume's unattended creation itself
  temporarily starts its own VNC server; no ongoing viewer was enabled by this setup.
- Restricted host diagnostics report only the configured VM state, including
  provisioning/running/stopped, without returning IPs or VNC credentials.

## Failure recovered during setup

An initial root-only password-reset attempt was rejected before rotation. Key
access remained available and the preset password was confirmed unchanged.
The operator then changed the password using the authenticated old-password
path, completed the remaining settings, and passed the reboot checks. The
portable security script now uses that working path. Partial failures retain
recovery material and refuse automatic retries.

## Not yet verified

Native Hermes computer-use, GUI action semantics, driver permission grants,
AX/screenshot capture, browser interaction, viewer takeover, transport failure
recovery and cold host reboot remain outstanding. Do not describe this as a
completed community plugin or a passed hardware GUI test suite.

## Signed driver and remaining human step

Cua Driver 0.44.0 was installed inside the guest from the pinned official release:
https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.44.0

Archive SHA-256:
`7699d7ebd3d3319cbd066af9fc679dc7439adad6c5c84cc46956aa9880106e37`.
The archive checksum and Cua Apple Developer ID signature verified. Telemetry is
disabled in the wrapper and guest configuration. `cua-driver --version` returned
`0.44.0`; `permissions status --json` returned Accessibility false, Screen Recording
false, daemon not running. These permissions must be granted manually in the guest.

The first driver download encountered a nonresponsive NAT DNS proxy. The guest
could reach HTTPS by literal IP. After configuring a reachable resolver already
present in the Mac host's settings, hostname-based HTTPS and driver download
succeeded. No resolver address is embedded in these scripts or documentation.

Validation for this change: 27 offline tests, Hermes plugin validation, Python
compilation and installer shell syntax checks. VM infrastructure verification
above is real; the GUI automation acceptance gates remain outstanding.

## First-login follow-up

The native viewer's setup screen was clipped at the original resolution. Changing
the guest to 1920×1200 and reopening the viewer resolved it, confirmed by the owner.

Inspection found the unattended preset's system setup markers still targeted an
older build. The post-install script now derives markers from the live guest;
read-back confirmed the current build/version and Siri disabled. Mac and developer
analytics were already false and are explicitly retained as false.

A user-requested easier-to-type password was applied through the new operator
password-change workflow. Account authentication, autologin update, and keychain
unlock verified. The password itself is not present in repository files/history.

Validation now includes 30 offline tests. Fresh guest creation with the expanded
first-login script has not yet been repeated; zero first-boot prompts is not claimed.

### Normal permission window

The onboarding guide now uses a standard AppKit NSWindow through built-in JXA,
with Settings links and an explicit permission recheck. Local macOS verification
passed all 33 tests; the Linux Hermes container passed 30 and skipped the three
macOS-only tests. Hermes plugin validation passed. In the live guest, the guide
LaunchAgent remained running without errors and CoreGraphics reported its window
at layer 0 (normal), sized 620 by 332 including its title bar. The signed driver
was running with `serve --no-permissions-gate`. After the operator enabled both switches, the signed daemon reported
`accessibility: true` and `screen_recording: true`. No screenshot was captured
during the earlier window-layer check.


### Direct screen capture and input

The two TCC switches alone did not satisfy the driver's direct-capture consent.
After the operator approved its additional macOS prompt, a desktop capture
succeeded. CuaDriver launched TextEdit, independently verified focus on its exact
window, and inserted 75 characters with accessibility value readback. The final
screenshot visibly contained the test message. Captures remain outside source.

Onboarding now includes the signed driver's final capture check after Check Again;
ready requires successful capture verification in addition to both switches.
Local macOS tests cover incomplete capture verification as well as successful
completion (35 tests passing).
The deployed JXA Check Again handler was also exercised against the live signed
driver: its final capture check succeeded, it wrote the verification marker, and
the guide helper subsequently reported ready. Linux container verification passed
30 tests with five macOS-only skips; Hermes plugin validation passed.

### Guest readiness from Hermes

The installed status handler was exercised as the Hermes runtime user through
the restricted host relay and operator-configured guest SSH alias. It reported
`vm_state: running`, `guest_reachable: true`, `driver_state: ready`, both
permission booleans true, and `capture_consent_verified: true`. Native provider
readiness remains false. An arbitrary SSH command was refused with
`unsupported_operation`. The source contains no deployment addresses or keys.
All 41 local tests passed; the container passed 36 with five macOS-only skips.
The installed plugin passed Hermes validation. Capture consent is recorded
verification; this status probe does not take a new screenshot.
