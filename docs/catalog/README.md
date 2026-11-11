# Catalog preparation — not a submission

`ownmachine.yaml.example` is a local preparation template, not a catalog entry.
No upstream PR, issue, fork or maintainer message is created by this update.
The owner selected PolyForm Noncommercial 1.0.0. Catalog license eligibility
remains unconfirmed; do not represent the license as accepted by Hermes.

## Before a submission is authorized

1. Confirm license eligibility with the maintainers. The published admission rules
   do not explicitly require an OSI-approved license; that does not establish
   acceptance of PolyForm Noncommercial 1.0.0.
2. Ask reviewers to assess operator-managed SSH keys/agents under the catalog's
   credential rule. The plugin delegates authentication to OpenSSH; this is a
   disclosure, not a claim that the credential policy does not apply.
3. Merge the readiness changes, choose a complete 40-character commit, and verify
   its `plugin/LICENSE` exactly matches the root license. Catalog installs use
   `subdir: plugin`, so they need a license there independently of release bundles.
4. Run `hermes plugins validate /path/to/plugin --install-deps` against the chosen
   commit in the Hermes environment used for current catalog admission. Prior
   validation on Hermes 0.23.1 alone is not current-upstream compatibility proof.
5. Capture sanitized screenshots of the actual viewer and its handoff controls.
   Commit only reviewed screenshots with no credentials, personal data or private
   deployment identities. The stylized teaser is not an actual UI screenshot.
6. Replace the template SHA, confirm the version/capabilities against the pinned
   manifest, and use same-SHA GitHub image URLs. Add only the resulting
   `plugin-catalog/ownmachine.yaml` to an authorized upstream submission branch.
   Run the upstream schema validator and follow its current submission guide.

The catalog renders `plugin/README.md`, not the repository-root README. It now
contains setup links, runtime/privileged-setup disclosures, provider capabilities,
limits and licensing. The native computer-use provider should be explained in the
PR even though the catalog capability arrays cover tools/hooks/middleware/env.
Do not invent a schema field for it. The separately hosted browser viewer is not
a Hermes Desktop SDK extension.

## Suggested submission description

OwnMachine connects Hermes to one operator-configured macOS VM over a restricted
SSH relay and guest MCP. It registers `ownmachine_status`, the native `ownmachine`
computer-use provider and `tool_execution` middleware through public APIs. All
writers share the same control database. Standard approvals remain enabled;
uncertain writes stop for operator review.

Disclose the README's OpenSSH subprocess and credential handling, local control
state/heartbeat, capture data sent through Hermes, external guest-app networking,
long-running separately installed viewer, bearer access file, administrator
firewall/hardening steps, manual guest permissions, and official checksum/signature-
pinned setup-time binary downloads. No updater or native binary is included in
the catalog-installed package. Full-source offline upgrade scripts are a separate
operator workflow. State licensing restrictions and unresolved preview limits.

## References checked

- [Canonical admission rules and schema](https://github.com/NousResearch/hermes-agent/blob/2b7a6ceca58d82f998fc9d2e5bcbaa7c7f5d60af/plugin-catalog/README.md)
- [Current submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)

Recheck these before submission; review rules can change. This preparation does
not assert approval or submit OwnMachine to any catalog.
