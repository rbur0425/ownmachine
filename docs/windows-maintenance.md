# Windows maintenance and recovery

Applies to the tested Windows 11 Enterprise Evaluation guest on Linux x86-64
KVM/libvirt. Home/Pro and other hypervisors remain outside this qualification.
Use your saved plan, services file and root runtime config; paths, users, aliases,
VM identities and timeouts below are operator configuration, not fixed defaults.

## Recover an existing desktop

Reserve human control before session maintenance. Save open work before signing
out. Unlock or sign into the configured **standard** Windows account in the
private viewer. Its Limited interactive Driver task starts at sign-in. If the
driver alone stopped, use Task Scheduler to run the existing
`OwnMachine-<vm_name>-Driver` task as that account; do not elevate it, restore
setup access, or change SSH/firewall permissions.

Run `hermes ownmachine doctor`, return control explicitly, and request a fresh
`computer_use` capture. A failed read is not retried automatically; the next read
can reconnect. A capture from before a handoff or another process's operation
cannot authorize later input. An uncertain write still needs operator inspection
and explicit acknowledgement; never delete the control database or repeat input
merely because a connection returned.

For gateway maintenance, stop and start only the affected Hermes profile's
runtime using its normal deployment supervisor. With an unmanaged Docker
runtime, `hermes gateway stop` followed by `hermes gateway ensure` is the tested
path. Existing chats may reconnect separately. Do not restart an unrelated
container or clear control state. After a plugin update, restart affected Hermes
processes so cached provider code is unloaded. Different profiles need their own
installed plugin and process; a cached provider from another profile is refused.
Profiles targeting the same VM must share its configured control directory.

## Setup interruption

Reconnect and inspect `hermes ownmachine setup --status`, doctor, the private
viewer and authenticated setup progress before continuing. If the endpoint
completed while the client was disconnected, import that completion. Never mark
a step complete based only on a local timeout.

If a mutating stage remains `running` or `needs_inspection` after its endpoint
process died, automatic replay is intentionally refused. The operator must inspect
whether the child is still running and what resources it created. Preserve the
checkpoint and disk. A partially completed administrator registration is not an
idempotent retry: inspect its exact domain/network UUIDs, accounts, console,
security service and SSH entries before any repair or scoped rollback. Do not
rerun registration with a different umask or delete unrelated resources.

The driver/permissions checks allow a bounded startup grace period. Set
`driver_ready_timeout_seconds` in the operator's services JSON to an integer
from 0 to 120 (default 30). This controls additional read-only polling, not the
baseline SSH probe deadline or an automatic driver restart. A stopped guest,
unhardened guest or failed health helper does not become ready by waiting.

## Upgrade the plugin and host relay

1. Save guest work, reserve human control and record the current plugin/source
   pin. Keep a private backup of operator configuration and runtime policy. A
   configuration backup is **not** a backup of the Windows disk, UEFI state or TPM.
2. Review the new release and validate its packaged plugin. Install that exact
   reviewed version through Hermes's supported plugin route. Do not independently
   upgrade the guest driver, mutate root config, or change VM identity.
3. For a compatible **relay-code-only** update, an administrator runs
   `sudo python3 scripts/update-kvm-runtime.py --config ROOT_CONFIG.json --source-dir REVIEWED_HOST_DIRECTORY`.
   The updater validates all three Python modules first, creates root-only hashed
   backups, and replaces each file with explicit read permissions. It changes no
   keys, firewall policy, domain definition or VM state. Stop client activity
   during this operation: replacement is atomic per file, not a transaction
   across all files. Old processes retain loaded code.
4. Restart affected Hermes/viewer processes. Run doctor, fresh capture, human/agent
   handoff and a small save/reopen task. Have an administrator rerun
   `scripts/check-kvm-boundaries.py ROOT_CONFIG.json` before accepting the update.
   Firewall/domain/schema changes require their release-specific reviewed procedure;
   the code updater is not a configuration migration tool.

### Rollback or interrupted code update

Keep control reserved. Compare installed files with the reviewed old/new source.
A `.update-new` file means an interrupted replacement needs inspection, not blind
retry. Preserve it for diagnosis and remove it only after the administrator has
verified its identity and that no updater is active. Restore the **complete,
compatible three-module set** from the previous reviewed source using the updater,
then restore the matching plugin pin and restart its processes. The
`*.before-<sha256-prefix>` files are additional evidence; verify their hashes
before using them. Do not roll back security fixes without reviewing the resulting
exposure. Recheck boundaries, doctor, capture and save/reopen before returning
control. This procedure does not roll back a changed guest disk or configuration.

## Driver updates

The driver version and artifact digest are part of the qualified guest image.
Do not use a floating `latest` download or an automatic vendor updater. A new pin
requires verified artifact provenance, signature/digest checks, and the Windows
capture/input, save/reopen, idle and session-recovery matrix before adoption.
Preview pins receive the same checks; a stable label alone does not qualify them.

There is currently **no supported in-place guest-driver updater after setup-key
retirement**. The supported path is a separate fresh guest built from the new
reviewed pin, qualification, and an explicit operator-managed transfer of saved
files. Preserve the old VM until the replacement is accepted. Its unchanged
configuration/runtime pair is the rollback path. Never restore broad setup access
or grant agent administration just to replace the driver.

See [acceptance evidence](windows-kvm-acceptance.md) for what was actually tested.
Physical Linux-host reboot acceptance was explicitly skipped by the operator;
service-restart evidence must not be presented as a host-reboot pass. After any
real host reboot, verify security readiness, role boundaries, private viewer and a
fresh Hermes capture before resuming desktop tasks.
