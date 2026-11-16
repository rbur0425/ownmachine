# Operator-run Windows clean-install acceptance

Use the exact reviewed PR commit for **both** the installed plugin and host source.
This is a development acceptance test, not released Windows support. First-session clock sync and progress messages passed operator acceptance at
`01f60ae`. Operator acceptance at `1f1493d` also passed automatic progress-window
closure and the revised save/close/explicit-file-open task below. Keep this checklist
for regression runs; broader recovery and release gates remain separate.

## 1. Isolate the test

Use a fresh Hermes installation/home (prefer a separate Docker instance), not the
running everyday gateway. Install the reviewed plugin through Hermes:

```sh
hermes plugins install rbur0425/ownmachine/plugin --ref REVIEWED_COMMIT
```

Confirm its installed commit before continuing; do not install the catalog's older
release for this test. Configure `plugins.isolation: in_process`,
`computer_use.backend: ownmachine`, `computer_use.permission_mode: standard`, and
OwnMachine `guest_profile: windows`. Configure model credentials only through
Hermes's supported profile/auth routes. For the later model test expose only
`computer_use`; no terminal, filesystem or skill-editing tools.

## 2. Prepare distinct identities and paths

Follow [Start in Hermes](windows-onboarding.md#start-in-hermes),
[SSH pairing](windows-onboarding.md#pair-and-run-the-reviewed-setup-endpoint) and
[the fresh-install configuration](windows-onboarding.md#fresh-install-implementation-under-test).
Use a new VM name and empty storage directory, new domain/network UUIDs, network
subnet/bridge, runtime accounts, console directory and root runtime prefix. Use a
new control directory and private viewer access directory. The viewer key never
belongs in Hermes's container. Do not reuse completed receipts or retired keys.

Choose a non-UTC `time_zone` to exercise the regression, and reachable `time_servers`
if your network requires an alternative to the default. Keep all deployment
values in private operator configuration, outside Git. Review the media checksum,
driver pin and evaluation-license consent. Keep your desktop password local.

## 3. Build and register

In the test Hermes environment:

```sh
hermes ownmachine setup --run preflight
hermes ownmachine setup --run build --apply
```

Review the generated host files. On the Linux VM host, the administrator runs:

```sh
sudo python3 REVIEWED_SOURCE/scripts/register-windows-host.py \
  --services-file PRIVATE_SERVICES_JSON --plan-file PRIVATE_PLAN_JSON
```

Do not run an old one-time recreation script. If registration fails, preserve the
output and inspect before retrying. Pair the new runtime agent key and configure
`host_alias`, `vm_name`, and the Hermes-side `control_dir`; mount that same control
state for the separately owned viewer at its host-side path.

## 4. Test a safe disconnect/resume

```sh
hermes ownmachine setup --run firewall
hermes ownmachine setup --run relay --apply
hermes ownmachine setup --run keys --apply
hermes ownmachine setup --run viewer --apply
hermes ownmachine setup --run progress
```

Record the VM UUID, progress and disk path. Exit **only the test Hermes client**;
reopen the same environment/profile and run progress and `setup --next` again.
The saved plan, identities and completed stages must remain unchanged. This checks
a client interruption, not a host crash. Do not stop Docker, libvirt or other VMs.

## 5. Install Windows and check first-session time

```sh
hermes ownmachine setup --run preflight
hermes ownmachine setup --run provision --apply
```

Open the private viewer, reserve human control and handle the initial DVD boot
prompt. Let subsequent boots use the installed disk. At the standard desktop,
observe the normal progress window: OpenSSH must not be labelled “awaiting first
sign-in” while it installs. Closing that window must not cancel setup. It should close itself when bootstrap
finishes (within its 1.5-second polling interval), and must not cover the later
desktop task.

**Before restarting Windows**, compare its date/time with a trusted clock; allow
one minute for reading differences. It must become correct during clock
synchronization and bootstrap must not report complete on a sync failure. If
synchronization fails, use the displayed DNS/NTP recovery steps, then repeat only
provision. Do not manually set time or cold-start to make this check pass.

Record the phase/reason, displayed time, configured zone and outcome. Keep private
screenshots outside Git and exclude passwords, viewer links and tokens.

## 6. Harden, verify and retire access

```sh
hermes ownmachine setup --run progress
hermes ownmachine setup --next
hermes ownmachine setup --run provision --apply
hermes ownmachine setup --run harden --apply
hermes ownmachine setup --run driver --apply
hermes ownmachine setup --run permissions
hermes ownmachine doctor
```

Stay signed into the standard user. Return the viewer reservation to agent
control. Close other computer-use sessions, then run these **serially**:

```sh
hermes ownmachine setup --run verify
hermes ownmachine setup --run verify --apply
hermes ownmachine status
```

Expect `complete`, `setup_key_rejected: true` and `runtime_verified: true`.
A refusal is not permission to delete state, restore retired keys or bypass a gate.

## 7. Run the desktop task and report results

Allow enough tool iterations for UI discovery and verification: for a CLI run use
`--max-turns 80` (and an adequate wall-clock budget), with `--toolsets computer_use`.
A larger budget does not authorize retries after an uncertain action or prove
success. Record any continuation prompt as operator intervention.

Ask Hermes:

> Use only computer_use. Open Notepad and type “OwnMachine clean Windows acceptance
> passed.” Save it in Documents as ownmachine-clean-test.txt. For app shortcuts
> such as Ctrl+S and Ctrl+O, explicitly choose delivery_mode=foreground against
> the freshly captured exact window/dialog. Do not use the default/background
> accelerator path for these shortcuts. Verify the save dialog's full filename
> before submitting. Close Notepad using its freshly captured Close/Close Tab
> control with explicit foreground delivery. Relaunch it, then explicitly use
> File → Open (or foreground Ctrl+O) to open the exact saved path, even if a tab
> was restored automatically. Capture and show the reopened contents. A restored
> tab alone does not count as reopening the file. Use no terminal, scripts or
> filesystem tools. Stop on any operator-review gate; do not replay uncertain
> input or switch delivery modes to bypass a refusal.

Approve the normal driver prompts. If a review gate occurs, inspect the guest
and use the viewer’s Return to agent confirmation to acknowledge the uncertain
action. A direct transfer without acknowledgement is intentionally refused with
HTTP 409. Record this as manual recovery, not an uninterrupted pass. Independently view the reopened file and
compare every character. Record whether manual recovery was needed. Then leave
all desktop clients disconnected for at least six minutes and try a fresh capture.

Report the commit, clean-install result, first-session clock, progress-window
behavior, disconnect/resume outcome, retirement flags, model save/reopen result
and any unexpected manual step. Do not count a workaround as a passing test.

## Cleanup

Prefer keeping the passing baseline until the new guest passes. Cleanup is a
separate, explicit operation: check exact domain UUID and disk paths, save wanted
files, stop the selected guest, and remove only its own disk, runtime identities,
viewer unit, security service and dedicated network. Never use a blanket libvirt
or firewall cleanup command. An old name alone is insufficient authorization.
