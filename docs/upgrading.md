# Offline plugin upgrades

Use a trusted complete source checkout or verified source bundle containing the
new plugin and LICENSE. This operator command updates **only the plugin package**
in a dedicated Hermes home originally created by `scripts/install-hermes.py`.
It does not upgrade Lume, the guest driver, permissions, relay, viewer or services.
It never edits `config.yaml`, credentials, the shared control directory or VM disks.

Preview first, using your actual home path:

```sh
python3 scripts/upgrade-hermes.py --hermes-home /absolute/path/to/hermes-home
```

Preview reads the installation receipt and compares every installed package file
with its recorded SHA-256. Modified, extra or missing files refuse the operation;
ordinary Python bytecode caches and `.DS_Store` are ignored. Symlinks are refused.
The home must be owned by the current account, outside source, and reached through
its real path without symlinked ancestors. Homes installed by hand or without a
valid fresh-home receipt are not supported. Do not invent a receipt to force an
upgrade; create a separate fresh home and migrate configuration deliberately.

The JSON preview lists added, removed and updated package paths. It writes no
lock, backup, receipt or runtime state. A clean Git checkout records its revision;
source bundles or dirty checkouts may have a null revision, with exact file hashes
still recorded. Verify the source bundle inventory before using it.

## Apply while Hermes is stopped

Stop every Hermes process using this home/plugin, including gateways and other
sessions. An agent may have modules loaded even when it is idle. The tool cannot
detect all such processes or stop them for you. Coordinate other administrators
and keep the source and home unchanged during the operation.

```sh
python3 scripts/upgrade-hermes.py --hermes-home /absolute/path/to/hermes-home \
  --apply --runtime-stopped
```

`--runtime-stopped` is your explicit assertion, not an automatic process check.
An exclusive local lock prevents simultaneous upgrades by this tool. Identical
package contents produce a no-op. A changed package is staged and hash-verified
inside the same home, then the previous plugin is moved to a private backup and
the candidate activated. The installation receipt is replaced only afterward.
Configuration remains untouched; incompatible configuration changes require a
separate migration. Backups are never automatically deleted.

The result's `backup_id` identifies:

```text
HERMES_HOME/.ownmachine-upgrades/BACKUP_ID/previous-plugin/
HERMES_HOME/.ownmachine-upgrades/BACKUP_ID/previous-receipt.json
```

Run Hermes plugin validation for the installed package, restart Hermes explicitly
and run its native doctor in that environment. This command does not validate
Hermes compatibility or claim a successful live agent task by itself. Read the
candidate release notes and keep a backup until validation and use succeed.
CI separately upgrades a synthetic prior-version fixture in a disposable home,
compares the result with the verified plugin artifact and runs Hermes validation.

## Failure and recovery

Ordinary activation or receipt-write exceptions trigger rollback of both plugin
and receipt. If rollback fails, or the process is killed between steps, the
`ownmachine-upgrade-pending.json` marker remains. Subsequent runs refuse to proceed.
The marker contains only a backup identifier and guidance, not credentials.

Keep Hermes stopped. Inspect the marker, installed package, and that backup's
previous package/receipt before changing anything. Preserve all candidates for
inspection. For manual restoration, restore the matching `previous-plugin` as
`plugins/ownmachine` and `previous-receipt.json` as `ownmachine-install.json`, preserving
configuration and all unrelated data. Verify file hashes against the restored
receipt. Only remove the pending marker once the installation is coherent, then
rerun preview and Hermes validation before starting Hermes. If a process stopped
before moving the old package, it may still be intact at the original path; do
not overwrite it blindly. Never delete the shared lease to recover an upgrade.

This is an offline, multi-step filesystem operation, not an atomic transaction
across two directories and a receipt. It is not a power-loss guarantee. Back up
the home independently, do not use it concurrently, and review any interrupted
operation. The local lock coordinates only this command, not arbitrary writers.
The receipt detects accidental edits; it is not a signature authenticating the
publisher, nor protection against another process running as the same account.

## VNC isolation and Omarchy release upgrade

The next release also requires a host Lume rebuild and a true guest cold start;
this plugin-only command cannot perform that security upgrade. Follow the
[release candidate's mandatory upgrade sequence and Linux driver-pin policy](release-1.0.0.md).
Never resume an old saved machine state: it can retain the former credential-share
device configuration. Preserve the disk, shut down normally, verify no saved state,
deploy the reviewed build and cold-start through the viewer-role relay to rotate
the private VNC password before returning control.
