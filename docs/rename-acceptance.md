# OwnMachine rename acceptance

Observed on 2026-11-10. The operator selected **OwnMachine — Give your AI agent
its own desktop.** and explicitly replaced the migration requirement with a
fresh installation. Only the selected VM on the dedicated Mac host was authorized
for deletion/recreation. The separate laptop VM and its active agent were excluded.

## Source and repository

The private repository was renamed to `ownmachine`; Gitflow protections and PR
history remain in place. Source identifiers, plugin/provider/tool names, CLI
scripts, restricted SSH protocol, viewer branding, new service labels, default VM
name, bundles and example catalog paths use `ownmachine`. Historical acceptance
records retain the actual names used for their tests. No compatibility layer or
VM migration is included. Host/user identities and credentials remain external.

Initial installation revision: `621cc486974ba49c2dd0db1dd48a54863545c165`.
The viewer now runs `e59ea32eb389bdce96902df7038e173c4d85250d`, which fixes
RFB framing and guest support-directory ownership. The dedicated container retains
the initial package revision; plugin contents are unchanged by those fixes.

## Offline and installation checks

- macOS: 215 tests, 193 passed and 22 expected Hermes-only skips. Node pointer
  regression passed.
- Gitea Hermes CI passed at the implementation revision, including the platform
  test policy, repeatable bundles, extracted validation, fresh install and offline
  upgrade fixtures. These fixtures exercise OwnMachine-to-OwnMachine upgrades,
  not a MacDesk migration.
- A separate Docker container installed the renamed package into a new dedicated
  Hermes home and passed Hermes plugin validation. It uses an idle entrypoint for
  explicit CLI acceptance, not an unattended model/gateway service.
- The pinned viewer source runs under a new enabled user service. Browser inspection
  confirmed the OwnMachine title and tagline on its unauthenticated unlock screen.
  Authenticated live streaming and guest mouse/keyboard input were subsequently
  exercised through the permission setup, including password authentication.

## Fresh VM setup

The previous selected guest was confirmed stopped, and its shared control gate
was paused with no pending write before deletion. Its old viewer service was
stopped and disabled. The authorized guest was deleted by its exact name. New
provisioning uses four CPUs, 8 GB RAM, a 64 GB sparse virtual disk and 1900×1200
resolution. No bulk Lume cleanup or laptop lifecycle command was run.

An administrator installed the renamed firewall service on the same configured
port before retiring the old service/rule. The new LaunchDaemon was registered
and reported last exit code zero; the old daemon was absent. A new restricted
relay identity and renamed relay configuration were installed separately from the
legacy configuration. No host-key checking was disabled.

Fresh macOS 26.6.2 provisioning completed. Bootstrap rotated the guest password,
pinned its SSH host key, disabled password SSH/root login, and configured autologin.
No Apple account was required; analytics and Siri were disabled by the setup defaults.
The signed Cua Driver 0.44.0 was verified and installed.

## Failures found and corrected

- The root lifecycle installer created guest support directories with root ownership,
  preventing the driver wrapper from being installed. The installer now creates them
  as the configured guest account. This acceptance run repaired only the newly created
  directories and resumed installation after verifying the signed app. It was an
  operator-assisted recovery, not an uninterrupted clean-install pass.
- Renaming the RFB desktop name left its encoded length at seven bytes, corrupting
  subsequent stream messages. The header now derives its length from the name bytes;
  a regression test covers the following framebuffer message. The corrected viewer
  was deployed and live browser streaming then worked.

## Permission and runtime acceptance

With explicit operator approval, Accessibility and Screen Recording were enabled
inside the new guest through its browser viewer. Screen Recording initially had no
entry: adding CuaDriver from Applications, authenticating with the guest password,
and choosing Quit & Reopen worked. Check Again in the guide triggered the final
capture prompt, which was approved. The normal guide window did not block Settings.
Synthetic browser path typing did not populate Go to Folder reliably; selecting
Applications and CuaDriver visually completed the same documented add-app flow.
This does not establish native Lume clipboard behavior for the new guest.

The restricted host status reported Accessibility, Screen Recording,
capture_consent_verified and driver_ready all true. Native Hermes computer-use
doctor reported READY, including MCP. Its container also emitted a pre-existing
pnpm artifact synchronization warning; this was not a plugin-readiness failure.
An actual native provider desktop capture returned valid pixels at 1456×920.
Browser mouse input and guest password entry were exercised during onboarding.
The shared control gate was left paused with no pending write after verification.

With the new firewall active, direct LAN access to the VNC port timed out while
SSH-backed live viewing succeeded. Guest lifecycle restart was exercised during
setup; no physical-host reboot or new model-driven task is claimed for this guest.
The laptop VM, its services, and its other agent were left untouched.
