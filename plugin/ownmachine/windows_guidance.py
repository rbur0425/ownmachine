"""Allowlisted setup reasons; never render arbitrary remote text as instructions."""
GUIDE = 'docs/windows-onboarding.md#first-install-progress-and-recovery'
REMEDIES = {
    'windows_installation_in_progress': 'Open the private viewer, handle the initial DVD prompt or sign in to the standard account, and read OwnMachine setup progress. OpenSSH installation can take several minutes before SSH is available. Leave the VM running; do not recreate it.',
    'windows_bootstrap_in_progress': 'Read the OwnMachine setup progress window in the private viewer. Bootstrap is still running; wait before repeating setup --run provision --apply. Do not replay the bootstrap task.',
    'windows_bootstrap_failed': 'Ask the guest administrator to inspect the OwnMachine Bootstrap task history and Windows optional-feature/network errors. Preserve the disk and logs; do not recreate or replay bootstrap.',
    'windows_time_sync_required': 'Check guest DNS and outbound UDP 123 to the configured time servers. Then run setup --run provision --apply to retry only time synchronization. Do not disable certificate checks, rebuild the VM or change the host clock.',
    'windows_hardening_required': 'Finish provision, then run setup --run harden --apply before driver or permissions checks. Do not enable the driver manually.',
    'standard_interactive_guest_login_required': 'Sign into the configured Windows standard-user desktop using the private viewer, then rerun setup --run permissions and doctor. Do not elevate the driver or bypass sign-in.',
    'windows_driver_start_required': 'After hardening, inspect the configured standard-user Driver task in Windows Task Scheduler. Run that Limited interactive task or sign out/in, then rerun permissions and doctor. Do not change SSH/firewall rules for a stopped driver.',
}

def guidance(code):
    return REMEDIES[code] + ' See ' + GUIDE + '. For an optional reminder, use remind later --mode next-visit and confirm its preview.'
