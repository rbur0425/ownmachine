# Native viewer clipboard

Stock Lume 0.7.0 clipboard transport assumes its factory guest credentials.
OwnMachine rotates those credentials and disables password SSH. Its native toolbar
also sends clipboard shortcuts through VNC, even with VNC disabled. OwnMachine
provides an optional source patch for both issues; this is not a change to the
vendor-signed Lume binary.

## Build and run

On the Apple Silicon VM host, install the Swift 6 toolchain compatible with
Lume 0.7.0, then run these commands from the OwnMachine source checkout:

```sh
python3 scripts/ownmachine-native.py --build
# Shut down the guest normally before changing its owning Lume process.
python3 scripts/ownmachine-native.py --name ownmachine
python3 scripts/ownmachine-native.py --name ownmachine --check
```

The builder fetches the official Cua repository at the pinned Lume 0.7.0 commit,
applies `patches/lume-0.7.0-key-clipboard.patch`, and creates an ad-hoc-signed app
at `~/.local/share/ownmachine/native-lume.app`. It needs network access and build
cache space. This local app is not vendor-notarized. The existing vendor app is
preserved. The builder refuses to overwrite an existing optional app or modify
a dirty build checkout. Choose a fresh `OWNMACHINE_NATIVE_BUILD_ROOT` and
`OWNMACHINE_NATIVE_APP` to build another copy.

The wrapper refuses an already-running or busy guest instead of silently attaching
with ineffective clipboard settings. `--check` verifies the selected running VM
and strict guest-key SSH without reading a clipboard or sending desktop input.
`--build` only builds the app and exits; it never starts or restarts a guest.

The wrapper starts native display with VNC disabled. Merely attaching to an
already-running guest does not change its owner's clipboard configuration.
Focus an editable field in the guest and use **Paste Mac → VM**. **Copy VM →
Mac** copies the guest selection. Transfers are explicit by default;
`--clipboard-sync` opts into continuous bidirectional clipboard sharing.
Avoid copying credentials unnecessarily; clear sensitive clipboard contents
after use. Secure password fields can restrict paste; direct typing remains a
fallback.

## Configuration and authentication

`--name`, `--guest-user`, `--storage`, `--state-root`, and `--lume` select the VM,
guest account, Lume storage, private state directory, and optional app binary.
Defaults match the normal OwnMachine provisioning flow. The helper discovers the
running guest address from Lume; no address is embedded in source. It uses the
selected VM's `guest_ed25519` and `guest_known_hosts` created by
`secure-guest.py`, with strict host-key verification and key-only SSH. Missing
or insecure keys fail closed. No factory password fallback is added.

The patch invokes the local `native-clipboard-helper.py` using argument arrays,
with bounded execution and no local shell. It sends Command-C/V directly to
the native virtual-machine view instead of requiring a VNC listener. The helper
is an operator-side integration, not a remotely exposed plugin tool.

To return to stock Lume, shut down the guest normally and start it with the
original Lume binary. No physical-host reboot is needed.

## Reopen the permission guide

Inside the guest, run:

```sh
~/.local/lib/ownmachine/permission-guide.sh --show
```

This previews the normal window even after setup completed, without resetting
permissions. Check Again performs the existing signed-driver readiness check.
