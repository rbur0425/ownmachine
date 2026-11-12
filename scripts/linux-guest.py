#!/usr/bin/env python3
"""Guest-only Linux driver installation and graphical-session entry points.

No sudo, SSH credentials, host integration or compositor plugin is installed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

VERSION = '0.47.19'
SHA256 = '5a1daed6820e6063f33dddbd3e5403d89dc27b8cf197b45df9af0fddd4fd50bb'
SESSION_KEYS = {'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP',
                'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'HYPRLAND_INSTANCE_SIGNATURE'}


def private_dir(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('symlink_directory')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('unsafe_directory')


def write_new(path, content, mode=0o600):
    private_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def call(argv, timeout=10, env=None):
    return subprocess.run(argv, check=True, capture_output=True, text=True,
                          timeout=timeout, env=env)


def session_environment():
    raw = call(['systemctl', '--user', 'show-environment']).stdout
    session = {}
    for line in raw.splitlines():
        key, sep, value = line.partition('=')
        if sep and key in SESSION_KEYS:
            if not value or any(ord(c) < 32 for c in value) or value.startswith("$'"):
                raise ValueError('invalid_session_environment')
            session[key] = value
    runtime = '/run/user/' + str(os.getuid())
    if (session.get('XDG_RUNTIME_DIR') != runtime or
            session.get('XDG_SESSION_TYPE') != 'wayland' or
            'Hyprland' not in session.get('XDG_CURRENT_DESKTOP', '').split(':') or
            not re.fullmatch(r'wayland-[0-9]+', session.get('WAYLAND_DISPLAY', '')) or
            not session.get('HYPRLAND_INSTANCE_SIGNATURE') or
            session.get('DBUS_SESSION_BUS_ADDRESS') != 'unix:path=' + runtime + '/bus'):
        raise ValueError('graphical_session_required')
    info = Path(runtime).stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('unsafe_runtime_directory')
    return dict(os.environ, **session, CUA_DRIVER_RS_TELEMETRY_ENABLED='0',
                CUA_DRIVER_RS_ENABLE_WAYLAND='1')


def settings():
    path = Path.home()/'.config/ownmachine/linux-driver.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 4096:
            raise ValueError('unsafe_driver_settings')
        data = json.load(stream)
    if set(data) != {'version', 'sha256', 'binary'} or not re.fullmatch(r'\d+\.\d+\.\d+', data['version']) or not re.fullmatch('[a-f0-9]{64}', data['sha256']):
        raise ValueError('invalid_driver_settings')
    binary = Path(data['binary'])
    if not binary.is_absolute() or not binary.is_file():
        raise ValueError('driver_missing')
    if call([str(binary), '--version']).stdout.strip() != 'cua-driver ' + data['version']:
        raise ValueError('driver_version_mismatch')
    return data


def readiness():
    result = dict(schema_version=1, guest_os='linux', guest_profile='omarchy',
                  graphical_session=False, accessibility_bus=False,
                  driver_running=False, standard_mode=False, driver_ready=False)
    try:
        config = settings()
        env = session_environment()
        result['graphical_session'] = True
        call(['gdbus', 'call', '--session', '--dest', 'org.a11y.Bus',
              '--object-path', '/org/a11y/bus', '--method', 'org.a11y.Bus.GetAddress'], env=env)
        result['accessibility_bus'] = True
        state = call([config['binary'], 'status'], env=env).stdout
        result['driver_running'] = 'daemon is not running' not in state and 'permission mode:' in state
        result['standard_mode'] = 'permission mode: standard (' in state
        result['driver_ready'] = all(result[k] for k in ('graphical_session', 'accessibility_bus', 'driver_running', 'standard_mode'))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    return result


def install(version, sha256, artifact=None):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or not re.fullmatch('[a-f0-9]{64}', sha256):
        raise ValueError('explicit_version_and_sha256_required')
    home = Path.home()
    root = home/'.local/opt/ownmachine'/('cua-driver-' + version)
    config = home/'.config/ownmachine/linux-driver.json'
    support = home/'.local/lib/ownmachine'
    destinations = [root, config, support/'linux-guest.py', support/'driver-mcp.sh',
                    home/'.config/systemd/user/ownmachine-driver.service']
    if any(p.exists() or p.is_symlink() for p in destinations):
        raise ValueError('existing_installation_requires_inspection')
    private_dir(root.parent)
    with tempfile.TemporaryDirectory(dir=root.parent) as temporary:
        temp = Path(temporary)
        archive = temp/'driver.tar.gz'
        if artifact:
            shutil.copyfile(artifact, archive)
        else:
            url = f'https://github.com/trycua/cua/releases/download/cua-driver-rs-v{version}/cua-driver-rs-{version}-linux-arm64-binary.tar.gz'
            with urllib.request.urlopen(url, timeout=60) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out)
        with archive.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != sha256:
            raise ValueError('driver_checksum_mismatch')
        unpacked = temp/'unpacked'
        unpacked.mkdir(mode=0o700)
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            if any(not (m.isfile() or m.isdir()) or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):
                raise ValueError('unsafe_driver_archive')
            tar.extractall(unpacked, members=members, filter='data')
        binary = unpacked/'cua-driver'
        if call([str(binary), '--version']).stdout.strip() != 'cua-driver ' + version:
            raise ValueError('driver_version_mismatch')
        unpacked.rename(root)
    write_new(config, json.dumps(dict(version=version, sha256=sha256, binary=str(root/'cua-driver'))).encode())
    write_new(support/'linux-guest.py', Path(__file__).read_bytes(), 0o700)
    write_new(support/'driver-mcp.sh', b'#!/bin/sh\nexec /usr/bin/python3 "$HOME/.local/lib/ownmachine/linux-guest.py" mcp\n', 0o700)
    service = '''[Unit]
Description=OwnMachine Linux desktop driver
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 "%h/.local/lib/ownmachine/linux-guest.py" serve
UMask=0077
Restart=no

[Install]
WantedBy=graphical-session.target
'''
    write_new(home/'.config/systemd/user/ownmachine-driver.service', service.encode())
    call(['systemctl', '--user', 'daemon-reload'])
    call(['systemctl', '--user', 'enable', 'ownmachine-driver.service'])
    # No linger: no desktop control before graphical login.
    session_environment()
    call(['systemctl', '--user', 'start', 'ownmachine-driver.service'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['install', 'status', 'mcp', 'serve'])
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--sha256', default=SHA256)
    parser.add_argument('--artifact', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() not in {'aarch64', 'arm64'} or os.geteuid() == 0:
        raise ValueError('run_inside_arm64_linux_guest_as_desktop_user')
    os.umask(0o077)
    if args.operation == 'install':
        install(args.version, args.sha256, args.artifact)
        print(json.dumps(dict(installed=True, version=args.version)))
    elif args.operation == 'status':
        print(json.dumps(readiness()))
    else:
        config = settings()
        env = session_environment()
        if args.operation == 'mcp' and not readiness()['driver_ready']:
            raise ValueError('standard_graphical_driver_required')
        argv = [config['binary'], args.operation]
        if args.operation == 'serve':
            argv += ['--permission-mode', 'standard']
        os.execve(argv[0], argv, env)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Linux guest setup refused: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
