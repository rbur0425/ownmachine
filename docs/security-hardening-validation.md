# Security hardening validation

This records branch validation, not a claim that older releases or every live
service has been upgraded. The existing guest was subsequently stopped with
operator approval for clean-account acceptance; no host reboot was performed.

## Live Mac checks

On the existing Apple Silicon laptop with Lume 0.7.0, the administrator installed
the updated firewall helper and enabled the application firewall. Its successful
exit and success message were observed. The helper publishes root-owned 0644
status in a root-owned 0755 OwnMachine directory, with a 15-second LaunchDaemon
schedule. The unprivileged source relay accepted the matching fresh status.

With the Lume bundle blocked and the application firewall enabled, a fresh TCP
connection over loopback still received the RFB banner. A separate Linux machine
could not connect directly to the configured VNC port. This confirms that the
application rule does not isolate local loopback clients in this setup; PF and
ALF were both enabled for the external check, so it does not independently prove
ALF-only random-port coverage. No extra public management listener was opened
for testing.

macOS reports the bundle as blocked but reports its `Contents/MacOS/lume` path
as permitted when queried separately. The installer therefore registers and
verifies the app bundle, matching the operating system's application rule. The
first verification attempt failed closed on that redundant executable check;
the corrected installer succeeded. ALTQ warnings were benign.

The standard macOS `/private/var/run` ancestor is root:daemon 0775. The relay
permits daemon-group write only on that exact system ancestor; the OwnMachine
directory and status file must still be root-owned and not group/world-writable.

## Automated coverage

Regression tests cover fixed-port bounds, role-denied dispatch, missing/stale/
wrong-port/unsafe firewall evidence, mismatched VNC URLs/passwords, private
password/log permissions, protected password-file/log launch arguments, fail-closed
start, separate key rendering, nonoverlapping private viewer state and disabled
Hermes host-execution toolsets. The existing real-Hermes fresh-install test also
checks actual toolset selection removes terminal/file/code tools while retaining
computer-use tools.

## Clean-account acceptance — 2026-11-11

Runtime source: `6ea64454e897151e4e21186254f43ea8ead49844`. Subsequent
changes to this record do not imply another hardware run.

A separate non-admin Mac account, outside `staff`, installed the patched app and
created a fresh macOS 26.6.2 guest. No directory-ownership repair was needed.
The original guest was stopped with permission and its disk preserved.

The initial attempt failed before installation with `Failed to get current host
key`; the new host account had never logged into the desktop and had no login
keychain. One operator desktop login initialized it, after which creation
completed. The duplicate stock-app firewall identity also failed closed;
registration of the distinct `org.ownmachine.lume` patched bundle succeeded.

Both unattended verification boots ran without VNC. Sampling began during
installation and covered both boots: 164 listener probes over 167 seconds found
no Lume TCP listeners, with no unexpected probe errors. This is sampled evidence,
not a continuous kernel trace. The Swift patch separately disables VNC at both
call sites and rejects enabled verification. The guest occupied approximately
22 GiB after setup; deleting the completed restore download reclaimed about
18 GiB. These are observations, not universal storage requirements.

### Onboarding and live transport

- Guest key-only SSH, password rotation, aligned autologin/keychain, analytics
  preferences, signed CuaDriver, MCP launcher and lifecycle helper installed
  successfully. No manual ownership correction was used.
- Setup Assistant still required update-policy, Apple Account skip, adult age,
  analytics (both unchecked), guest FileVault deferral and Get Started choices.
  These remain manual; no Apple Account or host permission was granted.
- The permission guide appeared automatically. Both settings pages came to the
  front unobstructed. Accessibility authentication, adding CuaDriver to Screen
  Recording, Quit & Reopen, Check Again and final Allow all worked through noVNC.
  The guide reached `ready`, with signed capture-consent evidence.
- The first VNC-enabled boot became unresponsive: the displayed clock stopped,
  SSH timed out and Lume did not complete graceful shutdown. The disposable guest
  required power-off after the stop timeout. The cause was not established.
  After restart, onboarding and input worked; a later normal restart and a
  separate shutdown/start both passed. This isolated initial hang is a known
  preview limitation, not a proven fix or a claim of unattended reliability.
- The protected stream authenticated using the managed eight-character file.
  Password and detached log were 0600; `.lume` was 0700. Inspection from the
  ordinary host account found no password in process arguments and could not
  read the password or `.lume` directory.

### Agent/viewer isolation and functional checks

Separate non-root Linux agent/viewer identities used two forced-command SSH keys.
Real SSH requests rejected agent VNC/start/stop/restart and viewer MCP. The agent
UID could not read the viewer private key or bearer file. Viewer access directory
and file were 0700/0600, and the token file was absent from shared control storage.
SQLite initially created the shared database as 0640 despite directory default
ACLs; the documented 0660 database setup was applied before agent access.

The installed native Hermes provider captured TextEdit, typed a sentence and
saved it. An independent guest SSH read verified exact file contents. Browser
mouse/keyboard input added and saved a second line, also independently verified.
Human reservation rejected an agent write with `human_takeover`; reserve/return
buttons retained focus. No new model-driven test was performed in this run.

The normal restart and shutdown/start retained both lines, permission grants and
capture consent. A post-start native desktop capture returned a 1456×920 PNG.
Control stayed paused with no pending operation. The unrestricted temporary
operator key was then removed; a reconnect was rejected, its private key deleted,
and only the two restricted authorized keys remained.

### Automated results

- Local Python suite: 229 tests, 207 passed, 22 expected Hermes-only skips.
- Real Hermes Linux gate: 229 tests, 219 passed, 10 expected macOS-only skips;
  native contract, source/extracted/installed plugin validation, repeatable bundles,
  checksums, fresh-home installation and synthetic offline upgrade passed.
- Swift security patch: four tests passed, covering protected-file validation,
  all 66 allowed URL characters, detached path forwarding and no-VNC creation.
- The restricted test container mounts `/tmp` noexec. The first full CI attempt
  failed because executable fixtures were placed there; using a private executable
  test directory resolved those fixture failures without weakening the runtime.

## Limits still unverified for this security change

Independent ALF-only random-port coverage and physical-host reboot persistence
of the new firewall/account arrangement were not tested. Prior reboot evidence
predates this security change. The earlier live external check had PF and ALF
both enabled; it cannot establish which firewall blocked the connection.

Manual `lume run` without the protected-file flag remains outside the hardened
path and can expose an upstream weak password to local loopback clients. The
45-second firewall marker bounds stale evidence; it is not synchronous kernel
attestation. Root, the dedicated Mac account and viewer runtime remain trusted.
Shared lease state is cooperative coordination, not a hostile-code boundary.
