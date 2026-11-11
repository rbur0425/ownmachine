# Catalog preparation — not a submission

The local `ownmachine.yaml` is a reviewed-source preparation draft, not an
accepted entry. No upstream PR, issue, fork or maintainer message is authorized
by this work. The owner confirmed the two policy questions below on 2026-11-11.

## Policy confirmation

The owner reported on 2026-11-11 that **PolyForm Noncommercial 1.0.0 and the
operator-managed OpenSSH authentication design are acceptable**. These are no
longer unresolved preparation blockers. This records the owner's confirmation;
it is not an independently verified maintainer statement or catalog admission.
The eventual upstream PR still needs CI and maintainer review.

Keep the authentication disclosure: OpenSSH uses operator-managed configuration,
a restricted private key or SSH agent; OwnMachine does not parse private keys.
No credential API workaround or policy bypass is included. Future functionality
requiring secrets must use the applicable Hermes-supported credential route.

Rule 18 concerns password-manager login backends. OwnMachine registers neither
`browser_vault` nor `ctx.register_login_backend`, so it does not request a
vendor-only login-backend listing or the `verified`/`official` tier. Operator
setup passwords do not turn it into a password-manager integration. This does
not remove the obligation to disclose OpenSSH authentication under rule 11.

## Prepared evidence

- [Current-upstream validation](validation-2026-11-11.md), including the exact
  Hermes source revision, test results, scanner result and limitations.
- [Real viewer screenshots](../media/catalog/README.md), visually reviewed for
  private data and captured with actual human/agent handoff controls.
- `plugin/README.md` describes installation boundaries, public APIs, subprocesses,
  credential handling, capture/model-provider data flow, persistent processes,
  setup downloads, privileged setup, manual consent and preview limits.
- The root and installable-package licenses match. The package contains source,
  not the locally built Lume executable or a self-updater.

## Before an authorized upstream PR

1. Include the owner-confirmed license and OpenSSH design in the submission
   disclosures. If upstream review requires changes, repeat affected validation.
2. Merge the OwnMachine preparation PR. The local draft pins the content commit
   containing the screenshots and updated plugin README, not a moving branch.
   If a different commit is selected, rerun validation and update **both** `sha`
   and all screenshot URLs to that same full 40-character commit.
3. Recheck the current upstream rules and run
   `hermes plugins validate /path/to/pinned/plugin --install-deps` and the
   upstream `scripts/validate_plugin_catalog.py` against the draft YAML.
4. With explicit submission authorization, add only
   `plugin-catalog/ownmachine.yaml` to a PR in `NousResearch/hermes-agent`.
   Explain the disclosures below and wait for catalog CI and human review.

The catalog renders `plugin/README.md`, not the repository-root README. The
native computer-use provider should be described in the PR even though the
capability arrays cover tools/hooks/middleware/env. Do not invent a schema field
for it. The separately hosted browser viewer is not a Desktop SDK extension.

## Prepared submission description

OwnMachine connects Hermes to one operator-configured macOS VM over a restricted
SSH relay and guest MCP. It registers `ownmachine_status`, the native `ownmachine`
computer-use provider, the `on_session_open` hook, and `tool_execution` middleware through public APIs.
Cooperating agent/viewer writers share one control database. Standard approvals
remain enabled; uncertain writes stop for operator review. That shared state is
coordination, not a boundary against hostile code.

Disclose OpenSSH subprocess authentication and the owner's policy confirmation, local control state/heartbeat, captures and app text sent through Hermes
to the configured model provider, guest-app networking, the separately installed
long-running viewer and bearer file, administrator firewall/hardening steps,
manual guest permissions, official pinned setup downloads and locally built Lume
patch. No native binary or updater is included in `plugin/`. Full-source offline
upgrade scripts are a separate operator workflow. State the PolyForm terms and
preview limits, including deferred pixel-model acceptance, unverified cloud Mac
hosting, initial guest hang and outstanding new-security reboot/ALF-only tests.

## Rules checked

- [Canonical rules at the tested Hermes revision](https://github.com/NousResearch/hermes-agent/blob/3bcd071226d3d605a2bb3b4f3933e7d583e189d6/plugin-catalog/README.md)
- [Live submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)

Recheck before submission. Automated validation is not catalog admission.

## Reminder dependency and merge review

The candidate declares `websockets==15.0.1` in `plugin.yaml` for the public local
gateway client. It is also disclosed in the entry’s `known_issues` because the
current catalog schema has no dedicated dependency field. Hermes resolves it
against core constraints and asks for installation consent. No tokens are read
from files. The v0.7.0 release asset `ownmachine-catalog.yaml` pins the final release merge
commit and matching screenshots. The source draft pins reviewed content; use
the release asset for submission. Do not submit without owner authorization.

Local session-open delivery passed a real gateway session test. The admitted-chat
pipeline returned `no_conversation`, so that hook was withdrawn. A successful
scheduled Discord reminder alone did not establish either result. See the
explicit checks in `docs/onboarding-plan.md`.

Scheduled reminders use the public same-user gateway attach contract, WebSocket
transport (`websockets==15.0.1`) and public cron CLI. Jobs are created paused,
verified, then resumed after explicit user confirmation; delivery rechecks consent.
No gateway/provider credentials are read from credential stores. Disclose the
profile-local helper script, scheduled job and persisted reminder state as well.
See [submission handoff](../submission-handoff.md) for the checked entry process.
