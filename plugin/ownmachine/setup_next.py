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
        stages[3:3]=['linux-base','linux-desktop']
    if plan['target']=='existing':stages=['permissions','viewer','verify']
    for step in stages:
        row=outcomes.get(step,{})
        if row.get('stage') in ('verified','checks_passed','observed'):continue
        if row.get('stage') in ('running','needs_inspection'):
            return dict(stage='needs_inspection',next='Inspect the private '+step+' checkpoint; do not replay an uncertain mutation.')
        handoffs={
            'firewall':'The Mac administrator must install the reviewed firewall service. Then run setup --run firewall.',
            'permissions':'Open the guest permission guide with setup --run permissions --apply; approve the guest grants, then repeat the permission check.',
            'viewer':'Start the viewer under its separate owner with private access storage. Verify its connection and human/agent handoff before final verification.',
            'verify':'Pause agent control in the viewer, then run setup --run verify. Use --apply to repeat checks and retire setup access.'}
        if plan.get('guest_profile')=='omarchy':
            handoffs['linux-base']='Boot the verified installer with VNC disabled, confirm its SSH host key in the native console, and pair the temporary guest setup key. Then run setup --run linux-base --apply; it refuses a nonempty disk.'
            handoffs['linux-desktop']='Boot the installed disk without the ISO using the same confirmed host key and desktop-user SSH alias. Then run setup --run linux-desktop --apply and restart the guest.'
            handoffs['permissions']='Log into the Linux graphical session, then run setup --run permissions. This checks the standard-mode driver and accessibility bus; no macOS TCC prompts apply.'
        if step in handoffs:return dict(stage='await_'+step,next=handoffs[step])
        suffix=' --apply' if step in ('build','provision','relay','keys','harden','driver') else ''
        prefix='Refresh setup --run preflight first. ' if step in ('build','provision') else ''
        return dict(stage='await_'+step,next=prefix+'Run setup --run '+step+suffix+'.')
    return dict(stage='await_acceptance',next='Run setup --run verify --apply to capture the desktop and retire temporary setup access.')
