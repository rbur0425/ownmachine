# Guest restart acceptance

Save guest work before using the operator's graceful Restart control. OwnMachine
pauses input during lifecycle operations and leaves control paused afterward.
It does not force-poweroff the VM or promise that running applications reopen.
Use the same named VM; creating a new VM is not a persistence test.

For a repeatable operator check:

1. Record a harmless document's contents through the guest GUI and save it.
   Record the installed application's version and the presence of its profile
   directory, using paths appropriate to that application and guest account.
2. Confirm no unsaved work/download needs to finish, then use Restart in the
   trusted viewer. Wait for guest login and driver readiness.
3. Verify the live viewer reconnects, then explicitly reserve human control.
   Reopen the application/document and compare contents and app/profile state.
4. Verify native capture still works and direct host VNC access remains blocked
   from another machine while the SSH-backed viewer connects.

Use the existing signed GUI driver for protected folders when macOS refuses SSH
file reads. Do not grant Full Disk Access or modify TCC merely to run this check.
Guest Python/Command Line Tools are not required. Built-in tools can inspect
ordinary app metadata, but do not copy browser credentials or profile contents
into logs, source, CI or support reports. Account sessions can expire remotely
regardless of local disk persistence.

## Recorded verification

After the extended capture run, the operator confirmed guest work was saved.
The browser Restart action completed a graceful stop/start, changed the guest's
boot-session identity, and returned running with control paused and no uncertain
marker. The browser stream reconnected without changing its URL or exposing VNC
credentials. Native driver readiness returned with the existing grants.

Reopening TextEdit through the human-controlled viewer restored a test document.
Its GUI-accessible text hash matched the pre-restart baseline. Chrome launched
successfully; its application metadata hash, installed version and default
profile-directory identity were unchanged. Profile contents and account sessions
were not copied or inspected. Applications needed reopening; disk persistence
does not preserve their running processes.

The restart exposed a permission-guide startup race, addressed in this phase:
temporary daemon/CLI unavailability no longer counts as revocation, and an
existing signed capture-verification record prevents repeat consent onboarding.
A second graceful restart with the corrected guide returned its state to `ready`
and exited successfully without displaying onboarding. The viewer reconnected
and the driver was ready. Direct VNC remained blocked from another machine.
See the configurable startup allowance in [guest setup](vm-setup.md).

A physical Mac-host reboot and its firewall/login-service persistence are still
separate, unverified acceptance checks. This evidence covers guest restart only.
