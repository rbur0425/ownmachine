# Release readiness

The packaged security preview v0.6.0 is published; see [release scope](release-0.6.0.md).
Current catalog preparation and owner-confirmed policy eligibility are tracked in
[catalog readiness](catalog/README.md).
It is not a stable release or an accepted Hermes catalog entry. Feature PRs
merge into `develop`. Release promotion uses a separate `release/<version>` PR
into `main`, followed by a tag and synchronization PR back into `develop`.
Historical acceptance documents retain failures and intermediate test counts;
this page is the current checklist.

## Completed MVP evidence

- Native Hermes provider and private SSH/MCP transport, standard approvals and
  one shared human/agent control gate. Failed/uncertain writes block follow-ups.
- A real configured model created, saved and independently verified a TextEdit
  document. Later direct-provider tests verified corrected pixel mapping and
  stale/paused/human takeover refusal. These are distinct tests, not claims that
  all input routes were exercised by the model. See [hardware acceptance](hardware-acceptance.md).
- Fresh laptop provisioning, local-account onboarding without Apple sign-in,
  analytics opt-out, 1900×1200 display and guided guest permissions passed with
  manual first-login steps. Storage measurements are in [laptop acceptance](laptop-acceptance.md);
  they are observations, not a universal disk-space guarantee.
- A separate Hermes Docker installation passed provider discovery, validation,
  native doctor, MCP, live noVNC click/type and handoff checks against that laptop.
- Optional native-viewer ordinary/masked-field paste and reverse copy passed.
  Privileged macOS password-dialog paste is not certified; direct typing is the
  documented fallback.
- Guest lifecycle and saved-data persistence passed. Current LAN VNC blocking
  and SSH streaming passed. These do not establish physical reboot persistence.
- Read-only stability: 901 captures over 33 minutes 43 seconds, no failures.
  Long-running GUI-write workloads and every application's behavior are unmeasured.
- CI covers repeatable source/plugin bundles, extracted-package validation,
  fresh-home install, synthetic offline upgrade/rollback and the platform test
  matrix. PR #18 ran 211 Python tests: macOS 189 passed / 22 expected Hermes-only
  skips; Hermes 201 passed / 10 expected macOS-only skips. The separate Node
  pointer regression passed. New PRs must report their own counts and exact SHA.

- Direct normal SSH, supervised viewer restart and isolated container recreation
  now pass without a host or guest reboot. Configuration/plugin hashes and paused
  lease state survived; access-token rotation was verified. See
  [persistent installation acceptance](permanent-installation-acceptance.md).

- The fixed renamed candidate `f6ed1c6` passed a fresh laptop guest installation
  without the previous manual ownership repair. A separate fresh Hermes home
  installed the verified bundle; doctor and guest permissions passed. A real model
  completed an AX-driven document task with independent title/content/file checks.
  Earlier failed attempts and the unresolved pixel-binding expiry are retained in
  [clean-candidate acceptance](clean-candidate-acceptance.md).

## Release status and follow-up

The owner selected PolyForm Noncommercial License 1.0.0 and authorized public
source distribution and a clean repository. See [licensing details](licensing.md).
The current security candidate passed dedicated-account clean installation,
guided permissions, native Hermes and browser input, and subsequent guest
restart checks. The initial guest hang and remaining firewall/reboot test limits
are recorded in [security acceptance](security-hardening-validation.md).
Current-upstream validation passed, and the owner confirmed PolyForm and OpenSSH
eligibility for submission. Catalog admission still requires upstream review.

| Gate | Required result |
| --- | --- |
| Physical-host reboot — passed within tested scope | Operator-assisted restart verified a changed boot ID, IPv4 LAN restriction before VNC startup, SSH/MCP, permissions, three document-content hashes, capture and viewer HTTP/VNC handshake; Chrome reopened. Exact browser-profile identity is unverified and was clarified as outside the MVP acceptance requirement. See [hardware acceptance](hardware-acceptance.md#physical-host-reboot-follow-up--2026-11-10). |
| Branding selected; rename validation | **OwnMachine — Give your AI agent its own desktop.** This unreleased preview uses a clean installation; no MacDesk migration or backward compatibility is promised. Clean-install and AX model-task validation passed for `f6ed1c6`; renamed laptop firewall/service reboot and operator-assisted recovery passed. See [laptop reboot acceptance](laptop-permanent-reboot-acceptance.md), including the test-induced port conflict and explicit startup limits. Preliminary name screening is not legal clearance. |
| Final release documentation | The generic install/start/recovery path and historical-evidence cleanup are complete in this phase. v0.6.0 names, GitHub URLs and release notes are defined; keep manual consent and startup limits explicit. |
| Exact release candidate | Released v0.6.0 pins `8431db09c3abd251ba1f2d18a2f09d127816a119`, with verified bundles and final artifact inventories. Earlier model acceptance and the security clean-install run have distinct scopes; see release notes. New changes require their own validation. |
| Model-driven pixel input — deferred | Operator deferred this acceptance gate. A fresh model run hit `capture_expired` before dispatch and stopped safely. Keep the limitation explicit; additional prompting is not a confirmed fix. The AX task pass does not establish pixel-input reliability. |
| Public distribution and catalog | Public source and preview artifacts use github.com/rbur0425/ownmachine. Catalog submission remains separate: the owner confirmed license/SSH eligibility and current-upstream validation passed; the prepared entry pins a reviewed content commit and retains notices. Upstream admission review remains required. No catalog admission is claimed. |
| Gitflow release | The v0.6.0 release PR, tag, verified artifacts and synchronization into `develop` are complete. Future releases follow the same PR workflow. |

## MVP limits, not promises of completed automation

- Setup Assistant choices, macOS permission approvals and administrator firewall
  installation are manual. No Apple account is required by the tested workflow.
- Host FileVault unlock/login and explicit VM startup may be required. Automatic
  host/VM recovery is not an MVP promise; service enablement is not reboot proof.
- A temporary laptop reverse tunnel is acceptance infrastructure, not evidence
  of a permanent production connection. Browser access tunnels are separate
  from the viewer process and the Mac relay connection.
- VM backup/restore is deferred beyond MVP. Plugin upgrade backups only cover
  plugin/configuration state, not guest disks or user data. Real prior-version
  upgrade acceptance is needed before claiming live upgrade support beyond the
  tested synthetic offline workflow.

Never publish private desktop recordings, account sessions, VM images, access
links or deployment identities as evidence. Public demonstrations, naming/legal
review, catalog submission and publication are separate release activities.
