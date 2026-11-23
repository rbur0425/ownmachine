# Install an x86-64 Omarchy desktop from Hermes

Choose **omarchy-kvm** for an x86-64 Linux host with hardware KVM, QEMU/libvirt and standard x86-64 UEFI firmware. Choose **omarchy** for the existing ARM64/Lume implementation on Apple Silicon. Hermes itself can run on a different machine. The KVM profile uses foreground control through a version-matched Hyprland input module and a private Unix console.

## Save the plan

Install this revision in an isolated Hermes home. In the wizard choose the guest, the host location, and a new VM name. The equivalent terminal command is below. Replace the uppercase values. The control directory must be the same physical directory for the viewer and Hermes, even when its container mount path differs.

```sh
hermes ownmachine setup --guest-profile omarchy-kvm --target remote \
  --host-alias YOUR_AGENT_ALIAS --vm-name YOUR_VM_NAME \
  --control-dir /YOUR/HERMES/CONTROL --storage-dir /YOUR/HOST/NEW_VM \
  --cpu 4 --memory-gb 8 --disk-gb 64 --min-free-gb 32 --display 1280x800 --save
hermes ownmachine setup --next
```

## Prepare the host

Use a dedicated non-admin setup account. Install libvirt, QEMU, OVMF, libguestfs with **guestfish**, nftables, polkit, POSIX ACL tools, Git, Python with venv, and OpenSSH. Enable libvirt’s per-object polkit checks. The setup account must be able to run its user systemd manager to serve the loopback viewer. Confirm the host’s SSH fingerprint out of band. On distributions that restrict access to the host kernel, an administrator can run `libguestfs-make-fixed-appliance /YOUR/APPLIANCE` and grant the setup account read/traversal access to the resulting appliance. Set `provision.guestfs_appliance` to that directory. Test appliance access as the setup account.

Stage the following files in operator-controlled storage. The build verifies the exact five SHA-256 digests in [omarchy_kvm.py](../scripts/omarchy_kvm.py) before modifying a disk. It makes an independent writable copy of the official preinstalled image. This workflow uses a fresh VM image rather than the interactive ISO installer.

| Services setting | Artifact |
|---|---|
| `image` | [Omarchy 4.5.0 stable x86-64 QCOW2, build 494](https://nightly.omarchy.org/stable/4.5.0/494/omarchy-4.5.0.qcow2) |
| `driver_archive` | Linux **x86_64 binary** tarball and published Sigstore bundle from [CuaDriver 0.47.19](https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.47.19). Verify the GitHub Actions signing identity given in [the guest installer](../scripts/linux-guest.py). |
| `input_archive` | From a checkout of trycua/cua, run `git archive --format=tar -o /YOUR/MEDIA/input.tar ef1e84d6c880ab8aee7587c3d0057a288e764b69 libs/cua-driver/hyprland-plugin`. Preserve the tar bytes. |
| `cmake_wheel`, `ninja_wheel` | Use `python3 -m pip download --only-binary=:all: --no-deps --platform manylinux2014_x86_64 -d /YOUR/MEDIA cmake==4.4.5 ninja==1.13.2`. Keep their original wheel filenames. |

Copy the reviewed checkout to the setup account. Save private plan, services and endpoint JSON files using the [endpoint pairing instructions](windows-onboarding.md#pair-and-run-the-reviewed-setup-endpoint). Use the actual saved Hermes plan for `plan.json`. Start from [the example services file](examples/omarchy-kvm-services.json). Replace **every** placeholder, allocate two fresh UUIDs and an unused private subnet, and use existing firmware-code and matching variables-template paths for your distribution. The runtime JSON filename is the domain UUID without hyphens plus `.json` in the selected root-owned prefix. The upstream image's desktop account is `omarchy`. Runtime host users, groups, SSH aliases, viewer paths, resource sizes, and bridge settings are operator choices.

Create the private control directory for the intended viewer and grant the mapped Hermes OS user access. For example, on Linux, as the directory owner, run the following against that specific directory **before** starting the viewer. Keep the access-link directory separate and mode 0700. Run the viewer as the trusted operator and mount only the agent key and shared control directory into Hermes.

```sh
mkdir -m 700 "$CONTROL_DIR"
setfacl -m "u:$HERMES_UID:rwx,d:u:$HERMES_UID:rwx,d:u:$VIEWER_UID:rwx" "$CONTROL_DIR"
```

Pair a separate temporary setup key. Keep its public-key copy and the authorized-keys file owned by the setup account and mode 0600, and install the exact line printed by `scripts/setup-endpoint.py --render-key`. Set `setup_public_key_file`, `services_file`, `plan_file`, `source_sha256` and the allowed stages in the endpoint config. Allow preflight, build, firewall, relay, keys, viewer, viewer-check, provision, harden, driver, permissions, verify and retire. Configure the verified setup alias and source fingerprint in Hermes. Allow sufficient time for image preparation and the native build via `setup_timeout_seconds`. The client checks the actual endpoint response and can show progress with `setup --run progress`.

## Install and verify

1. From Hermes run `setup --run preflight`, then `setup --run build --apply` (prefix every command here with `hermes ownmachine` in a terminal). Use a new empty storage directory. A failed build with a partial disk requires inspection. Keep the original image.
2. On the Linux host, an administrator runs `sudo python3 scripts/register-windows-host.py --services-file /YOUR/services.json --plan-file /YOUR/plan.json`. This shared KVM registrar reads the saved guest profile. Check that the new domain is **stopped**, that its VNC listener is a private Unix socket, and that persistent security was installed successfully. The private console directory must be new and outside libvirt’s per-process QEMU directories.
3. From Hermes run `setup --run firewall`, `setup --run relay --apply`, `setup --run keys --apply`, and `setup --run viewer --apply`. Configure the runtime SSH alias on the Hermes machine using the **agent** key generated in storage. Save the connection with `setup --connect --save`. Set `computer_use.backend` to `ownmachine`, permission mode to `standard`, and plugin isolation to `in_process` in this Hermes profile. The connection uses `guest_profile: omarchy-kvm` and `console_transport: private-unix`.
4. Refresh preflight, then run `setup --run provision --apply`. It starts the registered VM. On first boot the guest rotates its password, applies key-only SSH and firewall policy, and verifies hardening before graphical login. Allow the graphical session to start. If still booting, check progress, refresh preflight, and repeat provision against the same VM. The operator’s recovery password is stored privately at `guest-password` in the selected storage directory.
5. Run `setup --run harden --apply`, then `setup --run driver --apply`. The latter installs the pinned driver, compiles the input module with the guest’s Hyprland headers and compiler, runs its tests, and enables its user service. Run `setup --run permissions` and `setup --run viewer-check`.
6. Pause control in the viewer. Run `setup --run verify --apply`. This checks role separation, opens the private RFB console, captures and validates a PNG through the native provider, retires temporary guest and host setup access, and verifies the runtime key still works.
7. Save open guest work. Shut down the VM through the viewer, confirm it reached stopped, and start it again. Once the graphical session is ready, run `hermes ownmachine doctor --json`. Look for **foreground_input_ready**, **driver_ready**, and **mcp_ready**. Doctor reads the current guest state on each call. If the compositor module failed, inspect `systemctl --user status ownmachine-input.service` inside the guest; a package update can require rebuilding against the new compositor ABI. Use the browser’s human reservation while troubleshooting.

The host firewall and role restrictions use the existing KVM security machinery. The viewer streams a private Unix socket under its own SSH role. The agent receives the guest’s standard-mode MCP interface. The initial qualification uses software-rendered virtio graphics and native Wayland Chromium. Hardware GPU passthrough and background input are outside this profile’s qualification.
