#!/usr/bin/env python3
"""Preview or apply an offline, receipt-verified plugin upgrade in a Hermes home."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def inventory(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('invalid_plugin_directory')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink_refused')
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError('non_regular_file')
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix == '.pyc' or path.name == '.DS_Store':
            continue
        result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not result:
        raise ValueError('empty_plugin')
    return result


def inspect(home):
    home = Path(home).expanduser().absolute()
    # Refuse aliases to directories, including symlinked ancestors.
    if home.resolve() != home or not home.is_dir() or home.stat().st_uid != os.getuid():
        raise ValueError('invalid_home')
    if home == ROOT or ROOT in home.parents:
        raise ValueError('home_inside_source')
    if (home / 'ownmachine-upgrade-pending.json').exists() or (home / 'ownmachine-upgrade-pending.json').is_symlink():
        raise ValueError('incomplete_upgrade_requires_review')
    plugins = home / 'plugins'
    if plugins.is_symlink() or not plugins.is_dir():
        raise ValueError('invalid_plugins_directory')
    receipt = home / 'ownmachine-install.json'
    if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 1024 * 1024:
        raise ValueError('invalid_receipt')
    data = json.loads(receipt.read_text())
    if not isinstance(data, dict) or data.get('installer') != 'ownmachine-fresh-home-v1':
        raise ValueError('unsupported_receipt')
    expected = data.get('plugin_files_sha256')
    if not isinstance(expected, dict) or not expected or any(
            not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v)
            for k, v in expected.items()):
        raise ValueError('invalid_receipt')
    current = inventory(plugins / 'ownmachine')
    if current != expected:
        raise ValueError('installed_files_modified')
    return home, current


def source_inventory():
    files = inventory(ROOT / 'plugin')
    license_path = ROOT / 'LICENSE'
    if license_path.is_symlink() or not license_path.is_file():
        raise ValueError('source_license_missing')
    files['LICENSE'] = hashlib.sha256(license_path.read_bytes()).hexdigest()
    return files


def revision():
    try:
        if not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], stderr=subprocess.DEVNULL).strip():
            return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return None


def write_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def upgrade(home, *, apply=False, runtime_stopped=False):
    home, old = inspect(home)
    new = source_inventory()
    summary = {'ok': True, 'applied': False, 'changed': old != new,
               'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
               'updated': sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
               'source_revision': revision()}
    if not apply:
        return summary
    if not runtime_stopped:
        raise ValueError('runtime_stopped_confirmation_required')
    fd = os.open(home / '.ownmachine-upgrade.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('invalid_lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _, current = inspect(home)
        if current != old or source_inventory() != new:
            raise ValueError('files_changed_during_check')
        if old == new:
            return summary
        backups = home / '.ownmachine-upgrades'
        if backups.is_symlink():
            raise ValueError('unsafe_backup_directory')
        backups.mkdir(mode=0o700, exist_ok=True)
        if backups.stat().st_uid != os.getuid() or stat.S_IMODE(backups.stat().st_mode) & 0o077:
            raise ValueError('unsafe_backup_directory')
        backup = backups / uuid.uuid4().hex
        backup.mkdir(mode=0o700)
        candidate = backup / 'candidate'
        shutil.copytree(ROOT / 'plugin', candidate, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        shutil.copyfile(ROOT / 'LICENSE', candidate / 'LICENSE')
        if inventory(candidate) != new:
            raise ValueError('source_changed_during_copy')
        receipt = home / 'ownmachine-install.json'
        shutil.copyfile(receipt, backup / 'previous-receipt.json')
        os.chmod(backup / 'previous-receipt.json', 0o600)
        write_json(backup / 'candidate-receipt.json', {'installer': 'ownmachine-fresh-home-v1',
                   'source_revision': summary['source_revision'], 'plugin_files_sha256': new})
        if inspect(home)[1] != old:
            raise ValueError('installation_changed_during_staging')
        pending = home / 'ownmachine-upgrade-pending.json'
        write_json(pending, {'format': 1, 'backup_id': backup.name,
                            'instruction': 'Keep Hermes stopped. Inspect previous-plugin and previous-receipt.json before recovery.'})
        target = home / 'plugins/ownmachine'
        moved = installed = False
        try:
            os.replace(target, backup / 'previous-plugin'); moved = True
            os.replace(candidate, target); installed = True
            os.replace(backup / 'candidate-receipt.json', receipt)
            pending.unlink()
        except BaseException:
            # Ordinary failures roll back. If recovery itself fails, retain the
            # pending marker so no future invocation silently proceeds.
            if installed:
                shutil.rmtree(target)
            if moved:
                os.replace(backup / 'previous-plugin', target)
            os.replace(backup / 'previous-receipt.json', receipt)
            pending.unlink()
            raise
        summary.update(applied=True, backup_id=backup.name)
        return summary
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--runtime-stopped', action='store_true', help='Confirm all processes using this plugin are stopped; this command cannot verify that.')
    args = parser.parse_args()
    try:
        result = upgrade(args.hermes_home, apply=args.apply, runtime_stopped=args.runtime_stopped)
    except (ValueError, OSError, TypeError):
        print('Upgrade refused or failed. Keep Hermes stopped after an apply failure. Check the installation receipt, unmodified plugin files, ownership, and any pending-upgrade marker. See docs/upgrading.md; no configuration or control state is intentionally changed.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
