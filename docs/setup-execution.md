# Resumable Mac setup execution

The Hermes commands save and explain the plan. The full-source operator runner
now implements two explicit Mac-side steps: build the pinned, patched Lume app,
and create a macOS guest without a verification VNC listener. It does **not** yet
orchestrate firewall installation, guest hardening, permission grants, keys or the
viewer. A verified provision step does not mean the desktop is ready.

Use a reviewed checkout or checksum-verified release source bundle, under the
intended dedicated non-admin Mac account after its first GUI login. Keep that
source unchanged during execution. The runner fingerprints its scripts, patches,
plan and installation paths to detect changes on resume; this is change detection,
not proof that an arbitrary downloaded source tree is trustworthy.

Export the plan from the intended Hermes profile:

```sh
hermes ownmachine setup --target remote --storage-dir /absolute/mac/storage --save --json > plan.json
```

Use `local` when Hermes itself runs on that Mac. For remote Hermes, transfer this
non-secret plan and the reviewed source through your operator channel and run the
following **on the Mac**, not in the Hermes container. Agent and viewer forced
SSH commands do not gain arbitrary command or provisioning access.

```sh
python3 scripts/setup-mac.py --plan-file plan.json --step build
python3 scripts/setup-mac.py --plan-file plan.json --step build --apply
python3 scripts/setup-mac.py --plan-file plan.json --step provision
python3 scripts/setup-mac.py --plan-file plan.json --step provision --apply
```

Without `--apply`, the runner only inspects the plan and saved checkpoint; it does
not probe readiness or create directories. Build requires Apple's Swift build
tools, network access and substantial working space. Provisioning downloads a
macOS restore image and can take a long time. Capacity is an estimate, not a
promise: sparse guest capacity is distinct from actual allocation, and restore
caches can use the home volume even with a custom guest storage directory.

`--app` and `--build-dir` configure absolute installation/cache paths.
`--ipsw` selects the restore image and `--preset` selects the supported macOS
unattended preset (`tahoe` or `sequoia`); neither permits another guest OS. The plan's
absolute `storage_dir` is passed explicitly to Lume for both listing and creation.
New execution directories are private; existing selected directories must already
be owned by the operator and mode 0700. Symlink execution directories are refused.
For the existing relay/viewer workflow, use the account's standard `~/.lume`
location (expanded to an absolute path). Custom-storage guest creation is supported
here, but propagating that location into every runtime relay operation remains a
separate follow-up; do not connect a custom-storage guest to the default relay.

Checkpoints and logs live beneath
`~/.local/state/ownmachine/<vm-name>/setup/` (directory 0700, files 0600).
The per-VM execution lock prevents concurrent runner operations. A successful
step is reverified when explicitly applied again, without repeating its mutation.
Build verification checks the pinned revision, patch hashes, code signature and
required protected-VNC options. Guest verification checks its unique name, macOS,
CPU, memory, disk capacity, display and stopped state after a successful provisioning command.

A failed, interrupted or uncertain operation stops at `needs_inspection`; it never
automatically deletes or recreates the guest, overwrites an existing app, or
retries creation. Inspect private logs and resources before operator-led recovery.
Changing the plan, source or paths also stops resume. Do not delete checkpoints
as a routine retry: an earlier process may still be running and a guest may exist.
A subprocess timeout is not proof that all descendant processes have stopped.

Continue with [community setup](community-setup.md) for the remaining manual
steps. No root command, account change, firewall exception, credential transfer,
permission approval, reminder or VM start is performed by this runner. Hermes's
profile checkpoint and this Mac execution checkpoint remain separate until a
future authenticated receipt-import flow is implemented.
