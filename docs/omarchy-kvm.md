# Install an x86-64 Omarchy desktop from Hermes

Choose **omarchy-kvm** for an x86-64 Linux host with hardware KVM, QEMU/libvirt and standard x86-64 UEFI firmware. Choose **omarchy** for the existing ARM64/Lume implementation on Apple Silicon. Hermes itself can run on a different machine. The KVM profile uses foreground control through a version-matched Hyprland input module and a private Unix console.

## Save the plan

Follow the [Hermes profile and plugin installation steps](evaluator-quickstart.md#install-the-reviewed-release) using a revision that contains `omarchy-kvm`. For a development checkout, set the plugin setting `setup_guide_ref` to its full Git commit so the wizard opens the matching guide. In the wizard choose the guest, the host location, and a new VM name. The equivalent terminal command is below. Replace the uppercase values. The control directory must be the same physical directory for the viewer and Hermes, even when its container mount path differs.

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

Pair a separate temporary setup key. Keep its public-key copy and the authorized-keys file owned by the setup account and mode 0600, and install the exact line printed by `scripts/setup-endpoint.py --render-key`. Set `setup_public_key_file`, `services_file`, `plan_file`, `source_sha256` and the allowed stages in the endpoint config. Allow preflight, build, firewall, relay, keys, viewer, viewer-check, provision, harden, driver, permissions, verify and retire. Configure the verified setup alias and source fingerprint in Hermes. Allow sufficient time for image preparation via `setup_timeout_seconds`. For the first native driver build, Hermes waits at least 7,400 seconds. The host allows 6,900 seconds for guest installation, including configuration, compilation and tests. After installation, the host polls readiness without reinstalling the driver. The client checks the actual endpoint response and can show progress with `setup --run progress`.

## Install and verify

1. From Hermes run `setup --run preflight`, then `setup --run build --apply` (prefix every command here with `hermes ownmachine` in a terminal). Use a new empty storage directory and allocate at least the upstream disk’s 40 GiB virtual capacity. Larger values expand the virtual disk. The qualification did not measure guest filesystem growth. A failed build with a partial disk requires inspection. Keep the original image.
2. On the Linux host, an administrator runs the registrar from an administrator-controlled checkout using reviewed, administrator-controlled copies of the services file and saved plan. Run `sudo python3 scripts/register-windows-host.py --services-file /YOUR/services.json --plan-file /YOUR/plan.json`. For Omarchy, registration imports a standalone copy of the staged disk under `/var/lib/libvirt/images`. To select another filesystem, pass `--disk-parent /YOUR/TRUSTED/IMAGES`. Create that directory first. It and its ancestors must be root-owned and closed to group and other writers, and QEMU must be able to traverse the path. Allow temporary space for private copies of the pinned downloads during the build and an independent runtime disk during registration. If registration stopped immediately after disk import, the same command verifies and reuses an unchanged disk. Inspect any conflicting disk or partially created host resources before continuing. Check that the new domain is **stopped**, that its VNC listener is a private Unix socket, and that persistent security was installed successfully. The private console directory must be new and outside libvirt’s per-process QEMU directories.
3. From Hermes run `setup --run firewall`, `setup --run relay --apply`, `setup --run keys --apply`, and `setup --run viewer --apply`. Configure the runtime SSH alias on the Hermes machine using the **agent** key generated in storage. Save the connection with `setup --connect --save`. Set `computer_use.backend` to `ownmachine`, permission mode to `standard`, and plugin isolation to `in_process` in this Hermes profile. The connection uses `guest_profile: omarchy-kvm` and `console_transport: private-unix`.
4. Refresh preflight, then run `setup --run provision --apply`. It starts the registered VM. On first boot the guest rotates its password, applies key-only SSH and firewall policy, and verifies hardening before graphical login. After an interrupted first boot, restart the same guest. Setup reuses matching private keys and working offline tools, then retries hardening. If a key differs or its owner or mode changed, inspect the guest instead of deleting the key or disabling the login gate. Allow the graphical session to start. If still booting, check progress, refresh preflight, and repeat provision against the same VM. The operator’s recovery password is stored privately at `guest-password` in the selected storage directory.
5. Run `setup --run harden --apply`. Open the private viewer and sign into the configured desktop account if needed. Keep its Hyprland session open and run `setup --run driver --apply`. The latter installs the pinned driver, compiles the input module with the guest’s Hyprland headers and compiler, runs its tests, and enables its user service. Run `setup --run permissions` and `setup --run viewer-check`. After login or reboot, permissions and verify poll while the foreground module starts. The host services setting `driver_ready_timeout_seconds` defaults to 30 seconds and accepts 0–120. Both roles must explicitly reject the other role’s operation. If using a KVM relay installed from an earlier PR revision, update the host runtime before rechecking role separation.
6. Pause control in the viewer. Run `setup --run verify --apply`. This checks role separation, opens the private RFB console, captures and validates a PNG through the native provider, retires temporary guest and host setup access, and verifies the runtime key still works.
7. Save open guest work. Shut down the VM through the viewer, confirm it reached stopped, and start it again. Once the graphical session is ready, run `hermes ownmachine doctor --json`. Look for **foreground_input_ready**, **driver_ready**, and **mcp_ready**. Doctor reads the current guest state on each call. If doctor reports `guest_unreachable`, check guest SSH connectivity and key pairing first. A `guest_health_check_failed` result means SSH answered but the guest helper failed. A `foreground_input_unavailable` refusal on an otherwise ready session keeps new MCP connections, including screenshot requests, closed. The private viewer remains available. To restore MCP, inspect `systemctl --user status ownmachine-input.service` inside the guest; a package update can require rebuilding against the new compositor ABI. Use the browser’s human reservation while troubleshooting.

The host firewall and role restrictions use the existing KVM security machinery. The viewer streams a private Unix socket under its own SSH role. The agent receives the guest’s standard-mode MCP interface. The initial qualification uses software-rendered virtio graphics and native Wayland Chromium. Hardware GPU passthrough and background input are outside this profile’s qualification.

## Recover foreground input

If doctor reports `graphical_session_required`, sign into Hyprland through the private viewer and run doctor again. For `foreground_input_unavailable` after a compositor upgrade, or an interrupted module build, reserve the viewer and save your work. Sign out and back in to start a fresh compositor. Open a terminal **inside the VM as the desktop user**. Check `systemctl --user status ownmachine-input.service` and the previous `~/.local/share/ownmachine/input-module/build.log` if present.

Once the previous build process has exited, run these commands together. They move its entire working directory to a private backup and build from the pinned source shipped in the guest. This path also works after setup-key retirement.

```sh
(
  set -eu
  umask 077
  cd "$HOME/.local/share/ownmachine"
  if [ -d input-module ]; then
    backup=$(mktemp -d ./input-module-backup.XXXXXXXX)
    mv input-module "$backup/"
    printf 'Previous build saved in %s\n' "$backup"
  fi
  export PATH="/opt/ownmachine-kvm/tools/bin:$PATH"
  module="$HOME/.local/lib/ownmachine/linux-input-module.py"
  python3 "$module" build --source-archive /opt/ownmachine-kvm/input.tar --enable-experimental-input --apply
  python3 "$module" enable --enable-experimental-input --apply
)
```

Run `hermes ownmachine doctor --json` from Hermes and verify foreground input and MCP readiness. If the compiler or compositor ABI is incompatible with the pinned source, keep the build log and use the private viewer until you restore a compatible package set or install a qualified driver update.

## Qualification evidence

A fresh Hermes Docker profile guided installation on an x86-64 Linux/KVM host using Omarchy 4.5.0 build 494, CuaDriver 0.47.19, and a 1280 × 800 virtio display. The installation used a new disk converted from the verified upstream image, a new VM identity, fresh roles, and separate private viewer and shared control directories.

| Check | Observed result |
|---|---|
| Build and host registration | Hermes verified the media and built the disk. The administrator registered a stopped domain. Hermes verified the persistent firewall, restricted runtime roles and private viewer. |
| First boot and resume | Provision initially reported that the guest needed time. Repeating the stage on the running VM completed it. Hardening, driver installation and guest permission checks passed. |
| Final setup verification | The private RFB handshake passed. The native provider returned a valid 1280 × 800 PNG. The client recorded setup complete, verified that the temporary setup key was rejected, and confirmed that runtime access still worked. |
| Guest cold start | The viewer role requested a graceful shutdown. Libvirt reported the domain shut off. Starting it assigned a new running domain ID. The first doctor check reported foreground input unavailable during startup. A later check passed foreground input, driver and MCP without manual module activation. |
| Human-to-agent handoff after cold start | In Chrome, the operator reserved the private viewer and typed `Browser`. The guarded Hermes input returned `human_takeover`. After control returned to the agent, its foreground input appended `Hermes`. An independent libvirt console capture showed `BrowserHermes` in Chromium. |
| Model-driven desktop task | A local Qwen model using the installed Hermes computer-use tool navigated from Chromium’s About Version page to `chrome://gpu`. An independent console capture showed the new URL, the GPU Internals tab, and the software-rendering report. |

The first end-to-end run exposed a receipt mismatch in the separate read-only viewer check. The host returned the mutating stage label. The corrected host runner returned `checks_passed` against the installed viewer, and a regression test checks the receipt expected by Hermes. The final setup verification independently exercised the private console before retiring the keys.

### Interrupted first-boot recovery

A separate disposable KVM guest booted from an imported copy of the freshly seeded image. A qualification fixture stopped the first hardening attempt immediately after key and tool installation. Offline inspection confirmed the recovery password remained private in the guest and neither completion marker existed. On the second cold boot, hardening sealed successfully, first boot completed and the guest password-transfer file was gone. Both SSH key files and the CMake executable retained their contents, ownership, inode and modification time. The fixture powered the guest down after each observation.

### Release-candidate clean install and login timing

A fresh Hermes Docker profile and a new 40 GiB VM ran the complete guided setup on x86-64 Linux KVM at runtime commit `103bb946acfd1e160cdc99e9be418fba7292c86d`. The administrator registered the stopped domain. Hermes verified the firewall, restricted agent and viewer keys, private viewer, hardening and native driver. Provision initially returned `omarchy_bootstrap_pending` during first boot. Refreshing preflight and repeating provision on the same running guest succeeded. The driver installed in one attempt. Read-only verify captured a 1280 × 800 desktop before the cold start.

The viewer role gracefully stopped the guest. Libvirt confirmed it was shut off and assigned a new domain ID when it started again. The first observed Hyprland session reported both driver and foreground input unready. The first Hermes permissions command then passed without an operator retry. Verify with `--apply` captured another 1280 × 800 screenshot, confirmed setup-key rejection and verified continued runtime access.

After control returned to the agent in the private browser viewer, a local Qwen model used Hermes computer use to navigate an open Chromium New Tab to `chrome://gpu`. A separate libvirt console capture showed the GPU Internals tab, the destination URL and the Graphics Feature Status section reporting software rendering. This run exercised a guest cold start on the existing Linux host.
