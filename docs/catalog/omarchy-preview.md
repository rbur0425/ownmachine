# Omarchy disclosure for the next catalog revision

This is preparation for a future release, not a change to the currently pinned
v0.7.0 catalog entry. After Gitflow release validation, update the entry's version,
immutable commit and screenshots together. Do not point the existing released pin
at development-only documentation or imply maintainer approval.

Suggested description once the experimental path is released:

> A persistent private desktop for Hermes: macOS or experimental ARM64 Omarchy on
> an Apple Silicon Mac, with restricted SSH/MCP and human-controlled browser access.

Include these known-issue disclosures alongside existing dependency/license notes:

- Omarchy is experimental and foreground-only. Chromium exact-window input requires
  explicitly opting into a native Hyprland module built for the installed compositor
  and compiler. Updates can require a reviewed rebuild; mismatches refuse loading.
- The host still requires Apple Silicon macOS, a reviewed Linux-capable Lume build,
  administrator firewall setup and pinned SSH identities. This does not add native
  Linux/Windows VM hosting or certify cloud Mac providers.
- Linux does not use macOS Accessibility/Screen Recording consent. Chromium first-run
  terms remain a user decision; a keyring is not weakened or created with an empty
  password to suppress prompts.
- Pinned installer/source hashes do not freeze Arch's rolling package repositories.
  Upstream migrations/updates remain operator decisions. Software graphics and
  application/package gaps can affect performance; no broad background-seat or
  every-application reliability claim is made.
- Creation, installed-disk boot and separate viewer-owner setup have documented
  operator handoffs. Private bootstrap images contain a generated SSH host key and
  must not be redistributed. Shared-control permissions must be initialized before
  either runtime starts.

The clean guest and two real model tasks are recorded in
[acceptance evidence](../omarchy-phase1-acceptance.md). These results supplement,
rather than replace, the released macOS evidence and remaining platform limits.
