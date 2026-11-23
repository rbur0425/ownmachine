"""Allowlisted setup reasons; never render arbitrary remote text as instructions."""
WINDOWS_GUIDE = 'docs/windows-onboarding.md#first-install-progress-and-recovery'
WINDOWS_REMEDIES = {
    'windows_installation_in_progress': 'Open the private viewer, handle the initial DVD prompt or sign in to the standard account, and read OwnMachine setup progress. OpenSSH installation can take several minutes before SSH is available. Leave the VM running; do not recreate it.',
    'windows_bootstrap_in_progress': 'Read the OwnMachine setup progress window in the private viewer. Bootstrap is still running; wait before repeating setup --run provision --apply. Do not replay the bootstrap task.',
    'windows_bootstrap_failed': 'Ask the guest administrator to inspect the OwnMachine Bootstrap task history and Windows optional-feature/network errors. Preserve the disk and logs; do not recreate or replay bootstrap.',
    'windows_time_sync_required': 'Check guest DNS and outbound UDP 123 to the configured time servers. Then run setup --run provision --apply to retry only time synchronization. Do not disable certificate checks, rebuild the VM or change the host clock.',
    'windows_hardening_required': 'Finish provision, then run setup --run harden --apply before driver or permissions checks. Do not enable the driver manually.',
    'standard_interactive_guest_login_required': 'Sign into the configured Windows standard-user desktop using the private viewer, then rerun setup --run permissions and doctor. Do not elevate the driver or bypass sign-in.',
    'windows_driver_start_required': 'After hardening, inspect the configured standard-user Driver task in Windows Task Scheduler. Run that Limited interactive task or sign out/in, then rerun permissions and doctor. Do not change SSH/firewall rules for a stopped driver.',
}

OMARCHY_REMEDIES = {
    'omarchy_bootstrap_pending': 'Open the private viewer and let first boot finish. If guest SSH stays unavailable, check the configured address, pinned guest key and guest firewall. Refresh preflight and retry provision on the same disk.',
    'omarchy_hardening_required': 'Check ownmachine-firstboot.service in the guest. Finish provision and confirm hardening before installing the driver.',
    'graphical_session_required': 'Open the private viewer and sign into the configured Omarchy desktop account. Keep its Hyprland session open, then retry the pending stage.',
    'omarchy_guest_unreachable': 'Check the pinned guest SSH connection and firewall, then rerun doctor.',
    'omarchy_guest_health_check_failed': 'Guest SSH responded. Inspect the installed guest health helper, then rerun doctor.',
    'omarchy_driver_required': 'Inspect the guest driver installation and its user service in the signed-in Hyprland session. Run setup --run driver --apply and check doctor.',
    'foreground_input_unavailable': 'Inspect ownmachine-input.service in the guest user session. Rebuild the pinned input module against the installed Hyprland version and check doctor.',
    'omarchy_setup_check_failed': 'Check the private host stage log and saved configuration, then run setup --run progress before retrying.',
}


def remedies(profile):
    return {'windows': WINDOWS_REMEDIES, 'omarchy-kvm': OMARCHY_REMEDIES}.get(profile, {})


def guidance(profile, code):
    guide = WINDOWS_GUIDE if profile == 'windows' else 'docs/omarchy-kvm.md'
    return remedies(profile)[code] + ' See ' + guide + '. For an optional reminder, use remind later --mode next-visit and confirm its preview.'
