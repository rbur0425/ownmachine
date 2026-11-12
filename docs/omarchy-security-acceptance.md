# PR 15 security follow-up acceptance

Tested on Apple Silicon macOS and the existing disposable Omarchy guest on
2026-11-12. This supplements, rather than repeats, the earlier fresh guided
installation and real-model acceptance in [the guided report](omarchy-guided-acceptance.md).

## VNC credential isolation

The new **common** Lume patch removes both automatic credential exports:

- The implicit `lume-config` VirtioFS share and its `vnc.env` writer.
- The background SSH fallback that wrote `~/.vnc.env` in the guest.

Both normal `run` (including its saved-state path) and the separate USB/recovery
start path use only the explicitly supplied directories. The Linux isolation
patch separately rejects host directory shares. The relay's private host-local
session discovery and password-file interface are retained.

A clean isolated checkout at upstream
`666c196f42dc9c83dbe075e20318f16c3e3a6d84` accepted the common patches followed by
the Linux isolation patch. The release build compiled and was locally ad-hoc
signed; the build verifier checked the upstream revision, full patch inventory,
signature and password-file CLI. No active host app or firewall registration was
replaced for this test.

`bash scripts/test-lume-vnc-isolation.sh <patched-source>` passed on macOS.
Its Swift test runs **both macOS configuration paths** with the real VM context
builder and an injected virtualization-service boundary. Neither added a share
or created the temporary export directory. The source guard also rejects either
credential writer returning. The test deliberately stops at the service boundary;
it does **not** claim a newly booted macOS guest or a live VNC streaming test.
Upstream Swift concurrency/deprecation warnings remain visible.

Existing guests must cold-start through the relay after deploying the new app;
each relay start generates a new password. Do not resume an older saved state
containing the former device configuration. The patch does not erase copies that
were already exposed; rotation invalidates those copies. See [SECURITY](../SECURITY.md).

## Hardening enforcement

The managed desktop stage now installs the root-owned SDDM drop-in and verifier
**before** upstream desktop installation. SDDM requires the guest firewall service
and an `ExecStartPre` check of the root-owned receipt and live SSH/firewall/sudo
policy. The hardener publishes the receipt only after its checks complete.
The receipt contains the schema, account name and UID, with no credentials.

The host rechecks hardening before driver preflight, mutation and completed-stage
verification. The guest helper checks the trusted receipt before installation,
readiness, daemon startup and MCP startup; unrestricted passwordless sudo also
causes refusal. Root-owned metadata is readable by the guest account while
recovery credentials and firewall files retain private permissions.

Live tests in the existing test guest:

| Check | Result |
| --- | --- |
| Install the exact generated boot-gate prefix | Passed; root-owned files, no installer bypass |
| Start SDDM with no hardening receipt | Refused; graphical login stayed stopped |
| Guest driver guard with no accessible receipt | Refused |
| Publish receipt after live SSH, firewall and sudo checks | Passed |
| Guest driver guard after verified hardening | Passed |
| Start/restart SDDM with the final verifier | Passed |
| Final installed guest helper readiness | Graphical session, AT-SPI, standard driver and native foreground input ready |
| Existing saved acceptance file | Unchanged |

This was an operator-reviewed upgrade of the disposable guest, not another
clean full installation. Its graphical session was restarted; the physical host
and the Mac Studio were not rebooted. An administrator inside the guest can
intentionally change the policy or launch unwrapped programs; these checks prevent
accidental bypass of OwnMachine's managed boot/setup paths, not guest-root access.

## Automated and artifact checks

- **396 Python/Hermes tests passed, zero skips** with
  `python scripts/check-tests.py --require-hermes` and Hermes on `PYTHONPATH`.
- New negative tests cover missing/untrusted receipts, writable/symlink metadata,
  reintroduced passwordless sudo, failed live policy, no receipt publication on
  failure, and fresh/resumed driver-stage refusal before mutation.
- Source plugin validation with `--install-deps` passed. The documented
  in-process callback and CLI-registration notices remain visible.
- Cosign reverified the Linux 0.47.19 archive and bundle: **Verified OK**, using
  the exact issuer/identity recorded in [the plan](omarchy-plan.md).

The current Linux pin is 0.47.19; the separate macOS driver remains 0.44.0.
The upstream release explains its GitHub Pre-release label as a monorepo Latest
label convention, not an unstable SemVer designation. OwnMachine's Linux support
still has the application and background-input limits in the plan. Targeted
Chromium keyboard input requires explicit native-module opt-in and a matching ABI.
