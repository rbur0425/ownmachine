# Windows KVM development experiment

Not a supported installer or an advertised Windows release. These are the reviewed components used for an isolated Linux x86-64/KVM experiment. Do not run the host scripts on an existing virtualization server without reviewing their account, libvirt authorization, SSH and firewall changes. The account installer restarts libvirtd; the acceptance host had no existing VMs when it ran. Host firewall persistence is unfinished.

## Configuration and boundaries

Keep configuration, media, keys and generated seed files outside this repository. Scripts take an explicit JSON path or named arguments. Host configuration includes `vm_name`, `vm_uuid`, `network_uuid`, `bridge`, `subnet`, `guest_ip`, `dns_server`, `storage_dir`, `source_dir`, `operator_user`, `agent_user`, `viewer_user`, `console_group`, and each role's `*_public_key`. Choose unused identities/networks; generate UUIDs. `source_dir` is the protected runtime directory containing `relay.py` and `host.json`, not the repository root. Runtime configuration also accepts `guest_user`, `driver_executable`, and `guest_health_script`. Paths sent to Windows must satisfy the relay's strict path validation. No deployment address or private key is bundled.

The separate operator runs setup. Two forced-command runtime keys split agent status/MCP from viewer console/lifecycle. The agent cannot use libvirt's console or monitor; the viewer cannot read the guest runtime key. VNC has no TCP listener: no-auth RFB is admitted only over the verified private Unix socket and the viewer's SSH route. Keep viewer keys and bearer access files outside Hermes's mounted configuration.

Hermes uses an isolated profile with `computer_use.backend: ownmachine` and plugin settings `host_alias`, `vm_name`, `control_dir`, `guest_profile: windows`, and `console_transport: private-unix`. The viewer receives the corresponding `--guest-profile windows --console-transport private-unix` and its separate viewer alias. Do not copy personal model credentials; configure the test profile through Hermes's public profile/config commands. Shared control files must be accessible to the intended Hermes/viewer identities without world-write permissions.

## Component sequence

1. Review/install host dependencies, render an operator-owned host configuration and generate separate keys.
2. Review `prepare-host-security.py` and `enable-runtime-ssh.py` with administrator access. They are spike tools, not idempotent production migration tools. Apply the reviewed `update-network-acl.py` for the viewer’s dedicated-network lifecycle dependencies; never reuse that network for other VMs. Verify the resulting domain ACL and private console using `check-host-boundaries.py` (actual open/connect probes).
3. Obtain Windows media from Microsoft under an appropriate license. The experiment used Enterprise evaluation; it does not qualify Pro. Verify the pinned driver artifact and Sigstore identity recorded in the acceptance report.
4. `render-inputs.py --help` describes private unattended seed generation; evaluation terms require explicit acceptance. It wipes guest disk zero, creates a standard desktop account and temporary setup administrator, and performs one initial automatic sign-in. Use only a newly created disposable domain. Never attach this seed to an existing VM.
5. `render-host.py` renders domain/network XML without defining them. Review XML, allocate the configured sparse disk, build the seed ISO with label `OWNBOOT`, and define only the chosen network/domain. ISO boot may require a console keypress.
6. `prepare-guest.ps1` defers Windows servicing to `finish-guest.ps1` after first sign-in. Track the bootstrap checkpoint; Windows Update can delay servicing. The driver task uses the standard account and Limited run level. Never elevate it to work around a targeting failure.
7. Install `guest-health.ps1` as `health.ps1`, `guest-agent-entry.ps1` as `agent-entry.ps1`, and `health-config.json` (`user`, `driver`) in an administrator-owned guest directory. Restrict the standard user's SSH key to the exact forced command entrypoint; preserve ACLs. This final integration is still a separate setup step, not yet wired into generated bootstrap.
8. After successful setup, `cleanup-bootstrap.ps1` disables autologin and removes guest bootstrap secrets/task/cached answer files. Eject seed and installation media. Retire temporary administration after acceptance. Securely handle remaining host seed files outside Git.

## Desktop task workflow

Discover the application with `list_apps`, then `focus_app` using its exact name/identity. Capture its actual `pid` and `window_id` from `list_windows`. On Windows, a display name can differ from an executable name; OwnMachine resolves unique discovered process identities without guessing. After opening Save or another dialog, rediscover and capture that dialog's exact window. Do not assume taskbar position, reuse the old editor target, or bypass an exact-window activation refusal. Start/shell activation remains a driver limitation under investigation.

Bootstrap disables hibernation/Fast Startup so ACPI shutdown is a genuine cold stop; acceptance checks a changed boot timestamp, not only a running state. A normal guest shutdown/start preserves the disk but ends the interactive session. Permanent autologin is off: the operator must sign in before the Limited driver task can resume. Host reboot acceptance and persistent network policy are separate from guest restart acceptance.

See [acceptance results](../../docs/windows-kvm-acceptance.md). Remaining work stays in the draft development PR; this experiment is not added to the guided production setup choices.
