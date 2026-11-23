# OwnMachine v1.2.0

Give Hermes an x86-64 Omarchy desktop on an Intel or AMD Linux host with hardware KVM. Choose `omarchy-kvm` in guided setup. Hermes can run on a separate machine, including in Docker. Linux hosts can also run the existing Windows 11 Enterprise Evaluation profile. Apple Silicon hosts retain the macOS and ARM64 Omarchy options.

The qualified Omarchy configuration uses Omarchy 4.5.0 build 494, CuaDriver 0.47.19, software-rendered virtio graphics and foreground input in a signed-in Hyprland session. A clean 40 GiB install passed first boot, setup-key retirement and a guest cold start. A real Hermes model navigated Chromium to its GPU Internals page, independently confirmed through the VM console. See the [installation guide and qualification evidence](https://github.com/rbur0425/ownmachine/blob/v1.2.0/docs/omarchy-kvm.md).

## Upgrade and setup

Install the plugin and full operator source at the same released revision. Restart affected Hermes processes. KVM permission checks now require an explicit rejection from each restricted role. On existing KVM installations, use the [runtime update and rollback procedure](https://github.com/rbur0425/ownmachine/blob/v1.2.0/docs/windows-maintenance.md) to update the host relay before running setup verification. Existing VM disks can be retained.

New Omarchy guests require administrator registration of the domain, restricted runtime identities and firewall on the Linux host. Reserve the private viewer to sign in. After a Hyprland update, use the [foreground input recovery procedure](https://github.com/rbur0425/ownmachine/blob/v1.2.0/docs/omarchy-kvm.md#recover-foreground-input) if the module no longer matches the compositor. GPU passthrough, background input on KVM and physical Linux-host reboot recovery are outside the tested scope. Catalog installs receive the new profile after the catalog pin is updated.
