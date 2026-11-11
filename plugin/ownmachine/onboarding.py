"""Operator-only setup planning and read-only diagnosis through public Hermes APIs."""
import argparse
import json
from pathlib import Path
import platform
import shlex
import shutil
import sys
from . import onboarding_state
from .config import Config
from .diagnostics import diagnose, render as render_doctor

PREREQUISITE = ('CLI commands and the native provider require a dedicated Hermes profile with in-process loading. '
                'In that profile, explicitly run: hermes config set plugins.isolation in_process. '
                'This changes profile isolation; setup never changes it automatically.')
def guide(ctx):
    import re
    manifest = (Path(__file__).resolve().parents[1] / 'plugin.yaml').read_text()
    match = re.search(r'^version: ([0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9.-]+)?)$', manifest, re.M)
    if not match: raise ValueError('invalid_plugin_version')
    ref = ctx.get_config('setup_guide_ref', '') or 'v' + match.group(1)
    if not isinstance(ref, str) or not re.fullmatch(r'(?:[a-f0-9]{40}|v[0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9.-]+)?)', ref):
        raise ValueError('guide_requires_version_or_commit')
    return 'https://github.com/rbur0425/ownmachine/blob/' + ref + '/docs/community-setup.md'

FIELDS = ('target', 'host_alias', 'vm_name', 'control_dir', 'storage_dir',
          'cpu', 'memory_gb', 'disk_gb', 'min_free_gb', 'display')
DEFAULTS = dict(target='', host_alias='', vm_name='ownmachine', control_dir='',
                storage_dir='', cpu=4, memory_gb=8, disk_gb=64,
                min_free_gb=60, display='1900x1200')


class InputError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError('Invalid setup options. Use /ownmachine help or hermes ownmachine --help.')


def add_arguments(parser):
    subs = parser.add_subparsers(dest='ownmachine_command')
    setup = subs.add_parser('setup', help='Plan or resume setup; explicitly save non-secret settings')
    setup.add_argument('--target', choices=['local', 'remote', 'existing'])
    for name in ('host-alias', 'vm-name', 'control-dir', 'storage-dir', 'display'):
        setup.add_argument('--' + name)
    for name in ('cpu', 'memory-gb', 'disk-gb', 'min-free-gb'):
        setup.add_argument('--' + name, type=int)
    from .setup_transport import STEPS
    setup.add_argument('--run', choices=(*STEPS, 'progress'), help='Run a reviewed stage over the dedicated setup SSH identity (terminal only)')
    setup.add_argument('--apply', action='store_true', help='Explicitly authorize a remote mutating step or opening the guest guide')
    setup.add_argument('--save', action='store_true', help='Save the plan in the active Hermes profile')
    setup.add_argument('--connect', action='store_true', help='Save existing relay connection settings; does not start the VM')
    setup.add_argument('--replace', action='store_true', help='Allow replacement of different existing connection settings')
    setup.add_argument('--json', action='store_true', dest='as_json')
    status = subs.add_parser('status', help='Show saved onboarding progress without contacting the Mac')
    status.add_argument('--json', action='store_true', dest='as_json')
    doctor = subs.add_parser('doctor', help='Read-only configured host, permissions and MCP checks')
    doctor.add_argument('--json', action='store_true', dest='as_json')
    subs.add_parser('help', help='Show setup entry points')


def configuration(ctx):
    return Config(**{k: ctx.get_config(k, v) for k, v in vars(Config()).items()})


def validate_plan(plan):
    if plan['target'] not in ('local', 'remote', 'existing'):
        raise InputError('Choose a target: local (Hermes runs on this Mac), remote, or existing.')
    for key in ('host_alias', 'vm_name', 'control_dir', 'storage_dir', 'display'):
        if not isinstance(plan[key], str) or any(ord(c) < 32 for c in plan[key]):
            raise InputError('Setup fields must be plain text without control characters.')
    Config(host_alias=plan['host_alias'] or 'not-configured', vm_name=plan['vm_name'],
           control_dir=plan['control_dir']).validate()
    if plan['storage_dir'] and not Path(plan['storage_dir']).is_absolute():
        raise InputError('Storage directory must be an absolute path on the Mac host.')
    for key, low, high in (('cpu', 2, 32), ('memory_gb', 8, 128), ('disk_gb', 50, 1000), ('min_free_gb', 32, 2000)):
        if type(plan[key]) is not int or not low <= plan[key] <= high:
            raise InputError(f'{key} must be an integer between {low} and {high}.')
    import re
    match = re.fullmatch(r'(\d{3,4})x(\d{3,4})', plan['display'])
    if not match or not all(640 <= int(v) <= 4096 for v in match.groups()):
        raise InputError('Display must use WIDTHxHEIGHT, for example 1900x1200.')


def preflight(plan):
    checks = [{'check': 'ssh_client', 'status': 'pass' if shutil.which('ssh') else 'fail',
               'detail': 'OpenSSH is required in the Hermes environment.'}]
    if plan['target'] == 'local':
        compatible = platform.system() == 'Darwin' and platform.machine() == 'arm64'
        checks.append({'check': 'local_mac', 'status': 'pass' if compatible else 'fail',
                       'detail': 'Local means the machine running Hermes, not your browser. Apple Silicon macOS is required.'})
        if plan['storage_dir']:
            path = Path(plan['storage_dir'])
            while not path.exists() and path != path.parent:
                path = path.parent
            try:
                free = shutil.disk_usage(path).free // (1024 ** 3)
                checks.append({'check': 'storage', 'status': 'pass' if free >= plan['min_free_gb'] else 'fail',
                               'detail': f'{free} GiB free; selected working budget {plan["min_free_gb"]} GiB. Sparse virtual disk capacity is separate.'})
            except OSError:
                checks.append({'check': 'storage', 'status': 'fail', 'detail': 'Cannot inspect selected storage location.'})
        else:
            checks.append({'check': 'storage', 'status': 'pending', 'detail': 'Select an absolute storage directory on the Mac.'})
    else:
        checks.append({'check': 'mac_host', 'status': 'pending',
                       'detail': 'Remote hardware/storage are not inferred from this Hermes machine; verify on the Mac.'})
    return checks


def setup(ctx, args):
    if getattr(args, 'run', None):
        from .setup_transport import dispatch
        saved = ctx.get_config('setup_plan', {})
        if not isinstance(saved, dict) or not saved or args.save or args.connect or any(getattr(args, k, None) is not None for k in FIELDS):
            raise InputError('Save/review the plan separately before running a remote stage; do not combine plan edits with execution.')
        plan = {k: saved.get(k, DEFAULTS[k]) for k in FIELDS}
        validate_plan(plan)
        return dispatch(ctx, plan, args.run, args.apply)
    if getattr(args, 'apply', False):
        raise InputError('--apply requires --run.')
    saved = ctx.get_config('setup_plan', {})
    if not isinstance(saved, dict) or saved.get('schema_version', 1) != 1:
        raise InputError('Saved setup plan is invalid or from a newer version; review it in plugin settings.')
    plan = {**DEFAULTS, **{k: saved[k] for k in FIELDS if k in saved}}
    current = configuration(ctx)
    for key in ('host_alias', 'vm_name', 'control_dir'):
        if key not in saved:
            plan[key] = getattr(current, key)
    for key in FIELDS:
        value = getattr(args, key, None)
        if value is not None:
            plan[key] = value
    if not plan['target']:
        return {'ok': False, 'stage': 'needs_input', 'questions': [
            'Where should the desktop run: local, remote, or existing?',
            'For a configured host, what is its verified SSH alias?',
            'Which absolute control directory is shared by agent and viewer?'],
            'prerequisite': PREREQUISITE, 'next': 'Run setup --target local|remote|existing; use --help in the terminal for options. No passwords or private keys in chat.'}
    validate_plan(plan)
    checks = preflight(plan)
    previous = onboarding_state.load(ctx) if args.save or args.connect else None
    if args.connect:
        if plan['target'] != 'existing' or not plan['host_alias'] or not plan['control_dir']:
            raise InputError('--connect requires target existing, a verified SSH alias and an absolute shared control directory.')
        desired = {k: plan[k] for k in ('host_alias', 'vm_name', 'control_dir')}
        old = {k: getattr(current, k) for k in desired}
        if (current.host_alias or current.control_dir) and desired != old and not args.replace:
            raise InputError('Existing connection differs. Review it before explicitly using --replace.')
        # Each public API write is atomic. Restore earlier values if a later write fails.
        written = []
        try:
            for key, value in desired.items():
                ctx.set_config(key, value)
                written.append(key)
        except Exception:
            for key in reversed(written):
                ctx.set_config(key, old[key])
            raise
    if args.save or args.connect:
        ctx.set_config('setup_plan', {**plan, 'schema_version': 1})
        onboarding_state.checkpoint(ctx, plan, checks, connected=args.connect, previous=previous)
    return {'ok': not any(c['status'] == 'fail' for c in checks), 'stage': 'planned',
            'saved': bool(args.save or args.connect), 'connection_saved': bool(args.connect),
            'guest_os': 'macos',
            'plan': plan, 'checks': checks,
            'progress': onboarding_state.summary(ctx, {k: ctx.get_config('setup_plan', {}).get(k, DEFAULTS[k]) for k in FIELDS}) if ctx.get_config('setup_plan', {}) else {'stage': 'not_started'},
            'steps': ['Check Mac capacity and build tools', 'Prepare dedicated account and restricted SSH keys',
                      'Install and verify firewall', 'Provision guest without Apple sign-in',
                      'Approve guest Accessibility, Screen Recording and capture consent',
                      'Start private viewer and verify human/agent handoff'],
            'next': ('Run hermes ownmachine doctor. Select the ownmachine native provider and in-process plugin loading in a dedicated profile using the guide; open a new session afterward.' if args.connect else
                     'Plan saved; resume with the same setup command.' if args.save else 'Review this plan, then add --save to keep it.'),
            'guide': guide(ctx), 'prerequisite': PREREQUISITE,
            'scope': 'Planning/configuration only. No VM, account, firewall, key, service or permission was created or changed. Use --run with the approved setup endpoint for explicit remote execution.'}


def render_setup(report):
    lines = ['OwnMachine setup: ' + report['stage'].replace('_', ' ').upper()]
    for question in report.get('questions', []):
        lines.append(question)
    if 'guest_os' in report:
        lines.append('Guest image: macOS (the only supported image; no OS selection required)')
    if 'plan' in report:
        lines.extend(f'{key}: {value or "not selected"}' for key, value in report['plan'].items())
    lines.extend(f'[{c["status"].upper()}] {c["check"]}: {c["detail"]}' for c in report.get('checks', []))
    lines.extend(f'{i}. {step}' for i, step in enumerate(report.get('steps', []), 1))
    if 'progress' in report:
        lines.append('Saved progress: ' + report['progress']['stage'])
    lines.append(report['prerequisite'])
    lines.append(report['next'])
    if 'guide' in report:
        lines.extend([report['guide'], report['scope']])
    return '\n'.join(lines)


def execute(ctx, args):
    if args.ownmachine_command == 'setup':
        report = setup(ctx, args)
        if getattr(args, 'run', None):
            return json.dumps(report), (0 if report['ok'] else 2)
        return (json.dumps(report) if args.as_json else render_setup(report)), (0 if report['ok'] else 2)
    if args.ownmachine_command == 'status':
        saved = ctx.get_config('setup_plan', {})
        if not isinstance(saved, dict):
            raise InputError('Saved plan is invalid; review plugin settings before continuing.')
        plan = {k: saved.get(k, DEFAULTS[k]) for k in FIELDS} if saved else {}
        report = onboarding_state.summary(ctx, plan)
        from . import setup_transport
        if ctx.state.get(setup_transport.KEY, default=None) is not None:
            report['execution'] = setup_transport.summary(ctx, plan)
        text = 'OwnMachine onboarding: ' + report['stage'].replace('_', ' ').upper() + '\n' + report['next']
        if 'execution' in report:
            text += '\nRemote execution: ' + report['execution']['stage']
        if report.get('blocked_checks'):
            text += '\nBlocked checks: ' + ', '.join(report['blocked_checks'])
        return (json.dumps(report) if args.as_json else text), 0
    if args.ownmachine_command == 'doctor':
        report = diagnose(configuration(ctx))
        return (json.dumps(report) if args.as_json else render_doctor(report)), (0 if report['ok'] else 1)
    return ('OwnMachine: /ownmachine setup | hermes ownmachine setup | hermes ownmachine doctor\n'
            'Setup resumes the saved plan. Use --save to persist it, or --target existing --connect to configure a prepared relay.\n'
            'Use setup --run STAGE for the approved SSH endpoint; mutating stages require --apply and chat requires an allowed sender. Never paste passwords or private keys into chat.\n' + PREREQUISITE), 0


def interactive(ctx, args):
    """Only the explicit terminal setup command prompts; chat/cron never read stdin."""
    if args.ownmachine_command != 'setup' or args.target is not None or args.as_json or args.save or args.connect or getattr(args, 'run', None):
        return
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    saved = ctx.get_config('setup_plan', {})
    saved = saved if isinstance(saved, dict) else {}
    print('Give your AI agent its own desktop. No passwords or private keys are requested.')
    def ask(label, default=''):
        value = input(f'{label}' + (f' [{default}]' if default else '') + ': ').strip()
        return value or default
    args.target = ask('Where will the desktop run? local / remote / existing', saved.get('target', 'local'))
    args.host_alias = ask('Verified SSH alias (leave blank until configured)', saved.get('host_alias', ctx.get_config('host_alias', '')))
    args.control_dir = ask('Absolute shared control directory', saved.get('control_dir', ctx.get_config('control_dir', '')))
    if args.target != 'existing':
        args.storage_dir = ask('Absolute VM storage directory on the Mac', saved.get('storage_dir', ''))
    args.vm_name = ask('VM name', saved.get('vm_name', 'ownmachine'))
    preview, _ = execute(ctx, args)
    print(preview)
    args.save = ask('Save this non-secret plan? yes / no', 'no') == 'yes'
    if args.target == 'existing' and args.save:
        args.connect = ask('Also configure this existing relay connection? yes / no', 'no') == 'yes'
    return True


def authorized_sender(ctx, context):
    """Transport identity is not authorization; command text never supplies identity."""
    source = context.get('source')
    platform_name = context.get('platform')
    user = getattr(source, 'user_id', None)
    chat = getattr(source, 'chat_id', None)
    if not all(isinstance(v, str) and v for v in (platform_name, user, chat)):
        return False
    allowed = ctx.get_config('setup_allowed_senders', [])
    return isinstance(allowed, list) and any(
        isinstance(entry, dict) and entry.get('platform') == platform_name
        and entry.get('user_id') == user and entry.get('chat_id') == chat
        for entry in allowed)


def register_commands(ctx):
    from .chat_setup import ChatSetup
    chat_setup = ChatSetup(ctx)
    def cli(args):
        try:
            previewed = interactive(ctx, args)
            text, code = execute(ctx, args)
            if previewed:
                print('Plan saved. No provisioning performed.' if args.save else 'Plan not saved. Run setup again when ready.')
                if args.connect:
                    print('Existing connection saved. Run hermes ownmachine doctor; start a new session after configuring the provider.')
            else:
                print(text)
            return code
        except InputError as error:
            print('OwnMachine: ' + str(error), file=sys.stderr)
            return 2
        except (ValueError, TypeError, OSError, RuntimeError, EOFError):
            if getattr(args, 'run', None):
                print('OwnMachine: remote success was not confirmed. Check the setup alias, source pin and stage allowlist; use setup --run progress before retrying. Do not replay an uncertain mutation.', file=sys.stderr)
            else:
                print('OwnMachine: setup could not complete. Check non-secret settings, saved state and directory permissions; existing state is preserved and no provisioning was performed.', file=sys.stderr)
            return 2
    def slash(raw_args='', **kwargs):
        parser = Parser(prog='/ownmachine', add_help=False)
        add_arguments(parser)
        try:
            tokens = shlex.split(raw_args)
            if '--help' in tokens or '-h' in tokens:
                return 'Use /ownmachine help, or hermes ownmachine setup --help in a terminal.'
            args = parser.parse_args(tokens)
            if args.ownmachine_command == 'setup' and getattr(args, 'run', None):
                if not authorized_sender(ctx, kwargs):
                    return 'OwnMachine: remote setup requires an explicitly allowed sender; use the operator terminal or configure setup_allowed_senders.'
                return chat_setup.start(args, kwargs)
            if args.ownmachine_command == 'setup' and (args.save or args.connect):
                if not authorized_sender(ctx, kwargs):
                    return 'OwnMachine: configuration changes in chat require an explicitly allowed sender. Use the local terminal setup command, or configure setup_allowed_senders with verified platform, user_id and chat_id values. No settings were changed.'
            return execute(ctx, args)[0]
        except InputError as error:
            return 'OwnMachine: ' + str(error)
        except (ValueError, TypeError, OSError, RuntimeError):
            return 'OwnMachine: invalid or unavailable setup settings/state. Existing state is preserved. Use /ownmachine help. No provisioning was performed.'
        except SystemExit:
            return 'Use /ownmachine help, or hermes ownmachine setup --help in a terminal.'
    if hasattr(ctx, 'register_cli_command'):
        ctx.register_cli_command(name='ownmachine', help='Set up or diagnose a private desktop',
                                 setup_fn=add_arguments, handler_fn=cli)
    if hasattr(ctx, 'register_command'):
        ctx.register_command('ownmachine', handler=slash,
                             description='Plan desktop setup or run read-only diagnostics', args_hint='setup | status | doctor | help')
