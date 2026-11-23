"""Import one standalone build disk into administrator-controlled libvirt storage."""
import hashlib
import json
import os
import stat
import struct
import subprocess
import tempfile


def require_trusted_parent(parent):
    if not parent.is_absolute() or '..' in parent.parts:
        raise ValueError('absolute_disk_parent_required')
    for directory in (*reversed(parent.parents), parent):
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('trusted_disk_parent_required')


def import_disk(source, parent, identity, owner, qemu, size, digest):
    require_trusted_parent(parent)
    destination = parent / (identity + '.qcow2')
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as src:
        info = os.fstat(src.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_nlink != 1:
            raise ValueError('regular_setup_owned_disk_required')
        if info.st_size > size + size // 16 + 64 * 1024**2:
            raise ValueError('oversized_build_disk')
        # The build directory remains writable. Only operate on a private copy;
        # an already-open writer to the source cannot change the validated image.
        with tempfile.NamedTemporaryFile(dir=parent) as copy:
            checksum = hashlib.sha256()
            remaining = info.st_size
            while remaining:
                chunk = src.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError('incomplete_disk')
                copy.write(chunk)
                checksum.update(chunk)
                remaining -= len(chunk)
            if checksum.hexdigest() != digest:
                raise ValueError('built_artifact_changed')
            copy.flush()
            copy.seek(0)
            header = copy.read(104)
            if len(header) != 104 or header[:4] != b'QFI\xfb' or struct.unpack_from('>I', header, 4)[0] != 3:
                raise ValueError('qcow2_v3_required')
            # Require the standalone v3 layout produced by the guided build.
            # Reject backing paths, encryption, snapshots and incompatible
            # features (including external data) before invoking any parser.
            if (any(header[8:20]) or any(header[32:36]) or any(header[60:80])
                    or int.from_bytes(header[24:32], 'big') != size):
                raise ValueError('standalone_qcow2_required')
            result = subprocess.run(['qemu-img', 'info', '-f', 'qcow2', '--output=json', copy.name],
                                    check=True, capture_output=True, timeout=60)
            img = json.loads(result.stdout)
            details = img.get('format-specific', {}).get('data', {})
            if (img.get('format') != 'qcow2' or img.get('virtual-size') != size
                    or 'backing-filename' in img or 'data-file' in details or img.get('snapshots')):
                raise ValueError('standalone_qcow2_required')
            os.fchmod(copy.fileno(), 0o600)
            os.fchown(copy.fileno(), qemu.pw_uid, qemu.pw_gid)
            os.fsync(copy.fileno())
            os.link(copy.name, destination)  # atomic publication, never overwrite
    return destination
