# Lume installation — November 10, 2026

This installation evidence accompanies the portable OwnMachine foundation.
Deployment-specific identities are intentionally excluded.

## Installation

Installed as a dedicated non-root account on an Apple Silicon test host.
Host addresses, account identities and deployment paths are kept outside the repository.
The source-only operator script is `scripts/install-lume.sh`. It is not a
model-invocable tool or plugin self-updater. Run it explicitly on the Mac:

```sh
/bin/bash scripts/install-lume.sh
```

The script refuses root, unsupported platforms, and existing installations.
It downloads the pinned upstream release, verifies SHA-256 and the Cua Developer
ID code signature, and installs a per-user app plus CLI wrapper. It does not
modify shell profiles, install a background service, or provision a VM.

- Version: `0.7.0`
- Release: https://github.com/trycua/cua/releases/tag/lume-v0.7.0
- Upstream target commit: `666c196f42dc9c83dbe075e20318f16c3e3a6d84`
- Artifact: `lume-0.7.0-darwin-arm64.tar.gz`
- SHA-256: `66ae137164f5428ef73f90994850db49f1270dec298653f9f806debe29d529fc`
- Signer: `Developer ID Application: Cua AI, Inc. (YCK386LBJ7)`
- App: `~/.local/share/lume/lume.app`
- CLI: `~/.local/bin/lume`

Official setup reference: https://cua.ai/docs/lume/quickstart
Installer reviewed: https://cua.ai/lume/install.sh
Telemetry override was verified in the pinned upstream source
`libs/lume/src/Telemetry/TelemetryClient.swift`.

`LUME_TELEMETRY_ENABLED=false` is set before the first binary invocation, then
`lume config telemetry disable` persists the preference. The installed CLI's
telemetry status reports disabled, source persisted, installation ID not created.
No Lume LaunchAgent or HTTP API listener was started.

## Observed verification

- Archive checksum matched GitHub's published asset digest.
- `codesign --verify --deep --strict` succeeded; signer matches Cua's team ID.
- `~/.local/bin/lume --version` returned `0.7.0`.
- `~/.local/bin/lume config telemetry status` confirmed disabled.
- `~/.local/bin/lume ls --format json` returned `[]`.
- The configured dedicated account has no Lume daemon LaunchAgent.
- Container-to-host restricted preflight reports `lume_installed: true`.
- No macOS guest, Cua Driver, or GUI persistence test is claimed.

## Guest provisioning boundary

The host has approximately 146 GiB available. The original 150 GB VM proposal
would leave inadequate headroom if fully allocated. Start with a smaller sparse
guest disk (for example 80 GB), or add storage before provisioning a larger one.
The installed CLI supports explicit CPU, memory, disk, display, IPSW, unattended
preset, and NAT networking arguments. Guest creation is not part of this install.

Before sensitive guest use, rotate preset credentials, verify key authentication,
install the signed guest Cua Driver, and have the owner grant macOS GUI permissions.
Keep installers, VM disks, restore images, private keys and guest profiles out of Git.

## Recovery

Re-running this installer refuses to replace an existing installation. Inspect
`~/.local/share/lume/lume.app` and `~/.local/bin/lume` before an intentional upgrade
or rollback. VM storage is separate; never delete `~/.lume` as an uninstall step.
