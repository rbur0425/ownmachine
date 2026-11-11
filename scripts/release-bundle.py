#!/usr/bin/env python3
"""Build or verify deterministic, unpublished OwnMachine distribution bundles."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 64 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    return bool(name and not path.is_absolute() and '..' not in path.parts
                and str(path) == name and '\\' not in name)


def members(data):
    result = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
        for entry in archive:
            if not safe_name(entry.name.rstrip('/') if entry.isdir() else entry.name):
                raise ValueError('unsafe_archive_path')
            if entry.isdir():
                continue
            if not entry.isfile() or entry.name in result:
                raise ValueError('unsupported_archive_member')
            total += entry.size
            if entry.size < 0 or total > LIMIT:
                raise ValueError('archive_too_large')
            result[entry.name] = (archive.extractfile(entry).read(), entry.mode & 0o111 != 0)
    return result


def packed(files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, (data, executable) in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size = len(data); entry.mode = 0o755 if executable else 0o644
            entry.uid = entry.gid = entry.mtime = 0
            entry.uname = entry.gname = ''
            archive.addfile(entry, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=compressed, mtime=0, compresslevel=9) as stream:
        stream.write(raw.getvalue())
    return compressed.getvalue()


def inventory(files):
    return {name: {'sha256': digest(data), 'size': len(data), 'executable': executable}
            for name, (data, executable) in sorted(files.items())}


def build(root, output):
    root = Path(root).resolve(); output = Path(output).absolute()
    if output.resolve() == root or root in output.resolve().parents:
        raise ValueError('output_must_be_outside_source')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)
    if git('status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('clean_checkout_required')
    revision = git('rev-parse', 'HEAD').decode().strip()
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('full_commit_required')
    tree = git('ls-tree', '-rz', revision)
    if any(row.startswith(b'160000 ') for row in tree.split(b'\0')):
        raise ValueError('submodules_not_supported')
    source = members(git('archive', '--format=tar', revision))
    required = {'LICENSE', 'plugin/plugin.yaml', 'scripts/install-hermes.py',
                'viewer/vendor/novnc/LICENSE.txt', 'viewer/requirements.txt'}
    if not required <= source.keys():
        raise ValueError('incomplete_source')
    plugin = {name[len('plugin/'):]: value for name, value in source.items() if name.startswith('plugin/')}
    plugin['LICENSE'] = source['LICENSE']
    metadata = {'format': 1, 'source_revision': revision, 'artifacts': {}}
    output.mkdir(mode=0o700)  # Refuse existing files, directories and symlinks.
    try:
        for kind, files in (('source', source), ('plugin', plugin)):
            name = f'ownmachine-{kind}-{revision}.tar.gz'
            content = packed(files)
            (output / name).write_bytes(content)
            metadata['artifacts'][name] = {'kind': kind, 'sha256': digest(content),
                                         'size': len(content), 'files': inventory(files)}
        (output / 'manifest.json').write_text(json.dumps(metadata, sort_keys=True, indent=2) + '\n')
        (output / 'SHA256SUMS').write_text(''.join(
            f'{digest(path.read_bytes())}  {path.name}\n'
            for path in sorted(output.iterdir()) if path.is_file()))
        verify(output)
    except BaseException:
        shutil.rmtree(output)
        raise
    return revision


def verify(directory):
    directory = Path(directory)
    path = directory / 'manifest.json'
    if path.is_symlink() or path.stat().st_size > LIMIT:
        raise ValueError('invalid_manifest')
    manifest = json.loads(path.read_text())
    if (manifest.get('format') != 1 or not re.fullmatch(r'[0-9a-f]{40}', manifest.get('source_revision', ''))
            or not isinstance(manifest.get('artifacts'), dict) or len(manifest['artifacts']) != 2):
        raise ValueError('invalid_manifest')
    revision = manifest['source_revision']
    seen = set()
    for name, record in manifest['artifacts'].items():
        kind = record['kind']
        if kind not in {'source', 'plugin'} or kind in seen or name != f'ownmachine-{kind}-{revision}.tar.gz':
            raise ValueError('invalid_artifact_name')
        seen.add(kind)
        path = directory / name
        if path.is_symlink() or path.stat().st_size > LIMIT:
            raise ValueError('invalid_artifact')
        content = path.read_bytes()
        if len(content) != record['size'] or digest(content) != record['sha256']:
            raise ValueError('artifact_checksum_mismatch')
        files = members(content)
        if inventory(files) != record['files']:
            raise ValueError('artifact_inventory_mismatch')
        if kind == 'plugin' and ('plugin.yaml' not in files or 'LICENSE' not in files
                or any(name.startswith(('viewer/', 'host/', 'scripts/', '.git/')) for name in files)):
            raise ValueError('invalid_plugin_boundary')
    sums = directory / 'SHA256SUMS'
    if sums.is_symlink() or sums.stat().st_size > 4096:
        raise ValueError('invalid_checksums')
    expected = ''.join(f'{digest((directory / name).read_bytes())}  {name}\n'
                       for name in sorted([*manifest['artifacts'], 'manifest.json']))
    if sums.read_text() != expected:
        raise ValueError('checksums_mismatch')
    return revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build').add_argument('--output-dir', required=True)
    commands.add_parser('verify').add_argument('--bundle-dir', required=True)
    args = parser.parse_args()
    try:
        revision = build(ROOT, args.output_dir) if args.command == 'build' else verify(args.bundle_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, tarfile.TarError, subprocess.SubprocessError):
        print('Bundle operation failed. Use a clean committed checkout and a new output directory outside source; verify complete, untampered artifacts.')
        return 1
    print(f'Bundle {args.command} passed for source {revision}. Checksums verify integrity, not publisher identity. Nothing was published.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
