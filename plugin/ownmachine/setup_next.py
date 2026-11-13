"""Actionable, read-only guidance; never infer success or replay a mutation."""


def next_step(ctx,plan):
    from .setup_acceptance import matches, KEY
    from .setup_transport import summary
    accepted=ctx.state.get(KEY,default=None)
    if matches(ctx,plan,accepted):
        if accepted.get('stage')=='complete':return dict(stage='complete',next='Setup accepted. Use doctor for current health.')
        if accepted.get('stage')=='retiring':return dict(stage='needs_inspection',next='Inspect setup-key retirement on the Mac. Do not reauthorize or replay it.')
    if not ctx.get_config('setup_host_alias','') or not ctx.get_config('setup_source_sha256',''):
        return dict(stage='pairing_required',next='Pair a separate temporary setup key, independently confirm the Mac host key, and install the reviewed endpoint. Follow docs/wizard-quickstart.md; never send private keys in chat.')
    progress=summary(ctx,plan)
    if progress.get('stage') in ('configuration_changed','awaiting_remote_result','needs_inspection'):
        return dict(stage='needs_inspection',next='Inspect the saved configuration and fetch setup --run progress before retrying. Never replay an uncertain mutation.')
    outcomes=progress.get('outcomes',{})
    stages=['preflight','build','provision','firewall','relay','keys','harden','driver','permissions','viewer','verify']
    if plan.get('guest_profile')=='omarchy':
        stages=['preflight','build','firewall','provision','linux-boot-installer','linux-base','linux-boot-system','linux-desktop','relay','keys','harden','linux-start-desktop','driver','permissions','viewer','verify']
    if plan['target']=='existing':stages=['permissions','viewer','verify']
    for step in stages:
        row=outcomes.get(step,{})
        if step=='viewer' and outcomes.get('viewer-check',{}).get('stage')=='checks_passed':continue
        if row.get('stage') in ('verified','checks_passed','observed'):continue
        if row.get('stage') in ('running','needs_inspection'):
            return dict(stage='needs_inspection',next='Inspect the private '+step+' checkpoint; do not replay an uncertain mutation.')
        handoffs={
            'firewall':'The Mac administrator must install the reviewed firewall service. Then run setup --run firewall.',
            'permissions':'Open the guest permission guide with setup --run permissions --apply; approve the guest grants, then repeat the permission check.',
            'viewer':'Start the viewer under its separate owner with private access storage. Run setup --run viewer-check to verify its connection, then check human/agent handoff before final verification.',
            'verify':'Pause agent control in the viewer, then run setup --run verify. Use --apply to repeat checks and retire setup access.'}
        if plan.get('guest_profile')=='omarchy':
            handoffs['linux-boot-installer']='Run setup --run linux-boot-installer --apply to boot the configured private installer with VNC disabled and verify pinned SSH. Pair the bootstrap identity before setup; never send keys in chat.'
            handoffs['linux-base']='Run setup --run linux-base --apply. This requires the fresh guest receipt and refuses a nonempty disk.'
            handoffs['linux-boot-system']='Run setup --run linux-boot-system --apply to shut down the verified installer and boot the installed disk without the ISO.'
            handoffs['linux-desktop']='Run setup --run linux-desktop --apply, then relay, keys and hardening before the first graphical restart.'
            handoffs['linux-start-desktop']='Run setup --run linux-start-desktop --apply. This verifies hardening and the host firewall before restarting into the protected desktop.'
            handoffs['driver']='Run setup --run driver --apply. Targeted Chromium input requires explicit enable_experimental_input in the operator configuration; capture readiness alone does not prove input works.'
            handoffs['permissions']='Log into the Linux graphical session, then run setup --run permissions. This checks the standard-mode driver and accessibility bus; no macOS TCC prompts apply.'
        if step in handoffs:return dict(stage='await_'+step,next=handoffs[step])
        suffix=' --apply' if step in ('build','provision','relay','keys','harden','driver') else ''
        prefix='Refresh setup --run preflight first. ' if step in ('build','provision') else ''
        return dict(stage='await_'+step,next=prefix+'Run setup --run '+step+suffix+'.')
    return dict(stage='await_acceptance',next='Run setup --run verify --apply to capture the desktop and retire temporary setup access.')
