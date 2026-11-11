# OwnMachine clean installation

**OwnMachine — Give your AI agent its own desktop.**

OwnMachine was developed under the name MacDesk. It has not been publicly
released. This rename intentionally uses a clean installation, without a legacy
migration or backward-compatibility layer. Historical acceptance records keep
the actual names used in those tests.

Fresh installations use `ownmachine` for the Hermes plugin/provider and default
VM name, `ownmachine_status` for readiness, `ownmachine-host` for the restricted
relay protocol, and `scripts/ownmachine-*.py` for operator commands. New user
services use `ownmachine-viewer.service` and `org.ownmachine.*` labels. The signed
upstream Cua Driver identity remains unchanged. All hosts, account names, paths,
ports, VM names and keys remain operator-configured.

## Replacing a private development installation

Deleting a VM destroys its guest applications, files, accounts and permission
grants. Do not do this on an installation another person or agent is using.
The source rename does not delete, stop or recreate any VM automatically.

1. Save or export anything you want to retain. Pause control and verify no write
   is pending. Stop the old viewer and Hermes processes targeting this VM.
2. Gracefully stop only the selected guest. Confirm its name and stopped state
   using Lume. Delete that exact VM only with the owner's explicit authorization.
   Do not delete all Lume storage or reset unrelated VM configuration.
3. Keep the old firewall restriction active until the replacement protection is
   installed and verified on the configured VNC port. The old rule's label does
   not weaken its protection. Installing new system firewall services requires
   an administrator. Never start an unprotected VNC listener to test the rename.
4. Follow [VM setup](vm-setup.md) to provision a new VM, harden the initial account,
   install the signed driver and complete guest Setup Assistant/permission consent.
   Old guest host keys, passwords and permission grants do not apply to this guest.
5. Install the renamed host relay and pin the new guest identity. Keep host SSH
   verification enabled. Update only the dedicated forced-command key entry and
   the selected guest SSH alias; preserve unrelated keys and aliases.
6. Install into a new dedicated Hermes home using `scripts/install-hermes.py`.
   Configure its model credentials separately and use an explicit shared control
   directory. Never run old and new providers or viewers against the same VM with
   different control directories.
7. Render the new viewer service using `scripts/render-viewer-service.py` with
   your selected source, Python, SSH alias, VM and control paths. Stop/disable the
   old viewer unit before enabling the new one. Retrieve a new private access link;
   old viewer credentials are not carried forward.
8. Validate the plugin, run doctor, complete capture consent and test the private
   viewer and human/agent handoff. Keep old host-only configuration backups private
   until the replacement is verified; remove obsolete service files individually.

The rename does not require disabling FileVault or changing the host's desktop
permissions. A fresh guest still requires manual first-login choices and approval
of Accessibility and Screen Recording inside that guest.
