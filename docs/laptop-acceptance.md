> Historical acceptance record: these tests used the MacDesk name.
> The product is now OwnMachine; recorded VM/file identifiers below are unchanged.

# Fresh laptop onboarding acceptance

Observed on 2026-11-10 with Apple Silicon, 64 GiB host RAM, Lume 0.7.0 and
a fresh macOS 26.6.2 guest. This is an in-progress acceptance record, not a
release certification. Deployment identities and private captures are omitted.

## Provisioning and storage

- Installed the pinned, signature-verified Lume release on the laptop.
- An administrator installed the fixed-port PF rule. The installer printed
  ALTQ warnings followed by its loopback-restriction success message. External
  blocking and physical-host reboot persistence still require separate checks.
- Created a guest with 4 CPUs, 8 GiB RAM and 64 GiB sparse virtual capacity.
- Creation completed successfully. Immediately afterward, the guest disk
  occupied approximately 21.4 GiB on the host.
- A monitor sampled host-volume free space every two seconds: 90.04 GiB at
  start, 49.17 GiB minimum, approximately 40.87 GiB net peak consumption.
  The restore download was approximately 18.4 GiB. These volume measurements
  include concurrent host activity and are not a universal installation minimum.
- Strict guest-key authentication, password rotation, password-SSH disabling,
  autologin credential update and login-keychain update all reported success.
- Installed the pinned, signed Cua Driver and the default permission guide.

## First login through the native Lume viewer

The 1440×900 test setting clipped the Update Mac Automatically page, hiding
the controls. A graceful guest shutdown, change to 1920×1200 and restart made
both buttons visible. The requested provisioning default is now 1900×1200;
a later guest-only restart verified that exact size with the complete menu bar and dock visible. No host reboot occurred.

The first-login preference script ran successfully, but did not suppress all
Setup Assistant pages on this build. The operator completed:

1. Automatic updates: Continue.
2. Apple Account: Other Sign-In Options → Sign in Later → Skip.
3. Age range: Adult for this operator-owned test workspace.
4. Analytics: both sharing boxes remained unchecked.
5. Guest FileVault: Not Now, then Continue; no existing encryption was disabled.
6. Welcome: Get Started.

The guest desktop and MacDesk permission guide then appeared. This verifies
local-account onboarding without Apple sign-in; fully unattended first login
has **not** passed.

## Permission guide observations

- The normal MacDesk guide window fits within the visible desktop.
- Open Accessibility launches the guest's System Settings permission page.
- System Settings appears in front of the guide; the earlier always-on-top
  obstruction was not reproduced.
- The page initially took time to populate. Once loaded, CuaDriver was already
  listed, so manually locating its application bundle was unnecessary.
- The Accessibility switch was observed off in this fresh guest. Permissions
  from another VM do not establish readiness here.
- Enabling Accessibility opened a Privacy & Security authentication dialog for
  the guest account. The dialog was fully visible above System Settings; the
  guide did not obscure it. The operator authenticated successfully by typing
  the shorter password; the Accessibility switch was then visibly on.
- Usability gap: the hardened guest has a generated recovery password, but the
  original guide did not explain where to retrieve it. The updated guide now displays the portable host-side path and direct-typing fallback. The operator must use the private
  host-side `~/.local/state/macdesk/<vm-name>/guest-password` file, not the host
  account password or the original unattended preset password.
- Automated text entry and ordinary paste through the native viewer did not
  complete the password prompt. The stored credential was independently
  verified using guest account authentication without printing it. The exact
  input-path cause is unresolved; operator entry was requested rather than
  resetting credentials or bypassing the permission dialog. Keyboard capture
  was returned to the host after the attempt.
- The operator also reported that clipboard paste failed. At their request,
  the guest password was changed to the new typeable format: four groups of
  four cryptographically random lowercase letters, with ambiguous letters
  excluded. Password rotation, autologin update and keychain verification
  succeeded. New guests use this format; there is no shared default password.
  Direct manual entry into the GUI succeeded. For the later Screen Recording
  authentication, individual key presses through the native viewer also
  succeeded; this does not establish that clipboard paste works.

- Open Screen Recording reached the correct guest settings page, initially with
  no applications listed. Used +, authenticated, selected Applications →
  CuaDriver, and clicked Open. macOS offered Quit & Reopen; accepting it left
  the CuaDriver switch visibly on.
- Returned to the guide and clicked Check Again. The final direct screen-capture
  consent appeared unobstructed; Allow dismissed it and the guide closed.
- Independent signed-driver status then reported daemon running, Accessibility
  true, Screen Recording true, and a direct capture verification receipt from
  `permissions_grant`. No whole-VM restart was needed for this permission flow.

The guided permission flow passed on this guest. This does not establish
Hermes transport, model-driven task completion or host reboot acceptance.

## Initially outstanding acceptance (historical)

Transport, viewer, input and LAN firewall checks below were completed in the
isolated-container follow-up. Physical-host reboot remains deferred. See
[release readiness](release-readiness.md) for the current checklist; VM
backup/restore is outside MVP.

## Follow-up verification

The revised normal permission window was reopened using `--show` without
resetting TCC. At the 1900x1200 guest display, all instructions, the password
path, direct-typing fallback and all four buttons were fully visible. Open
Accessibility opened the correct System Settings page in front of the guide;
CuaDriver was already enabled. Check Again closed the completed guide. This
supersedes the earlier pending visual-preview result.

Native paste failures were traced to two Lume 0.7.0 behaviors: factory-password
SSH and VNC-only clipboard shortcuts. The optional pinned source patch uses
the existing guest key and delivers shortcuts directly to the native VM view.
A first shortcut attempt typed a literal v; the final fix includes the native
left-Command device flag. The release build compiled and its local ad-hoc app
signature verified. After a guest-only restart with VNC disabled, the toolbar
inserted the exact harmless host clipboard fixture into guest TextEdit, visibly
verified in the native viewer. Continuous clipboard sync was disabled.

This proves toolbar paste into an ordinary editable field. At that stage, secure password
fields and reverse copy had not been retested (see the later follow-up below); direct typing remains the fallback
for fields that refuse paste. See [native viewer setup](native-viewer.md) for
the optional build, configuration and rollback instructions. The stock
vendor-signed Lume application was preserved. No physical host was rebooted.

## Isolated Hermes installation and completed follow-up

The follow-up used a new non-root Docker container and a new Hermes home, with
no credentials or configuration copied from the main Hermes installation.
A clean install exposed a real category-loader incompatibility: Hermes's
computer-use collector does not implement middleware registration. The plugin
now registers middleware only on contexts that support it, while still
registering its native provider in both contexts. A regression test installs
into a new home and calls the real Hermes category loader. New profiles inherit
the installed Hermes config schema version instead of appearing to be legacy
profiles. No Hermes core files were changed.

The laptop had no system SSH listener. Acceptance used a temporary loopback-only
SSH endpoint, a restricted forced-command key and a reverse SSH tunnel. Host keys
were pinned. This proves the plugin/relay path through that topology, not system
Remote Login provisioning or automatic startup after a physical reboot.

Observed results:

- Native doctor passed configuration, SSH, host/guest readiness, Accessibility,
  Screen Recording, direct-capture consent, signed driver and MCP transport.
- Combined native/viewer readiness and the shared upstream VNC handshake passed.
- Loopback VNC connected; a separate LAN machine's direct IPv4 connection timed
  out. The firewall launch daemon was registered with a successful last exit.
  This supersedes the earlier pending LAN check, not the physical reboot gate.
- The optional native viewer copied the exact harmless text fixture from guest
  TextEdit back to host TextEdit. Toolbar paste into a Safari password field
  produced the expected 22 masked characters. This does not certify paste into
  privileged macOS authentication dialogs; direct typing remains the fallback.
- The native launcher now separates `--build` from launching and provides a
  read-only `--check`. It refuses an already-running VM with an actionable
  shutdown instruction rather than pretending the patched view was attached.
- Guest restart through the web lifecycle control returned to running/paused.
  The persistent HTML fixture's SHA-256 matched before and after restart. Guest
  SSH and driver access recovered without new permission grants. An immediate
  doctor check during login correctly reported guest-not-ready; retry after
  login is required. This was a guest restart, not a physical-host reboot.
- Safari displayed the authenticated live desktop. Acceptance uncovered a
  zero-button-mask mouse-down on the macOS browser input path. A documented
  noVNC patch uses the explicit changed button in that case; normal masks and
  releases remain unchanged. The button advanced from 0 to 1 and the text field
  displayed `browser input`. Pausing left both unchanged after attempted input.
  Both native-display and headless modes showed the original input problem;
  the fix was verified in headless mode. It was not a frozen framebuffer.

- The actual Hermes category-loaded provider captured the Safari fixture,
  refused writes while paused and after an obsolete capture, then incremented
  the counter from 1 to 2 using a fresh screenshot-grounded pixel click. Native
  typing appended ` native provider`; the resulting image showed the complete
  text. A browser human takeover then rejected the next native write with
  `human_takeover`. These are direct provider tests, not an additional model run.

The disposable `tests/fixtures/desktop-acceptance.html` has no external requests
or form submission. Use harmless text, never actual credentials. Keep desktop
captures and runtime configuration outside the source tree.

Physical-host reboot, firewall persistence across that reboot, and fully
unattended macOS Setup Assistant remain unverified. The operator has deferred
the physical reboot. VM backup/restore remains outside MVP scope.
