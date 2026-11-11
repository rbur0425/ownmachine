"""Operator-side setup helpers; deliberately outside the installed plugin."""
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import stat
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


mac = module('setup_mac_runner', 'scripts/setup-mac.py')


def private_read(path, limit=1024*1024):
    if any(p.is_symlink() for p in path.parents):
        raise ValueError('symlink_directory')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_nlink != 1 or st.st_mode & 0o077 or st.st_size > limit:
            raise ValueError('unsafe_private_file')
        return stream.read(limit + 1)


def install_exact(path, content):
    """Create, or verify identical bytes. Never overwrite another installation."""
    if any(p.is_symlink() for p in (path.parent, *path.parent.parents)):
        raise ValueError('symlink_directory')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
        raise ValueError('unsafe_install_directory')
    if path.exists() or path.is_symlink():
        if private_read(path) != content:
            raise ValueError('existing_file_differs')
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def events(enabled, step):
    """Sanitized liveness, never raw logs, secrets or fabricated percentages."""
    stopped = threading.Event()
    start = time.monotonic()
    def emit(state):
        print(json.dumps({'format': 1, 'event': state, 'step': step,
                          'elapsed_seconds': int(time.monotonic() - start)}), flush=True)
    def heartbeat():
        while not stopped.wait(5):
            emit('running')
    worker = None
    if enabled:
        emit('started')
        worker = threading.Thread(target=heartbeat, daemon=True)
        worker.start()
    try:
        yield
    finally:
        stopped.set()
        if worker:
            worker.join()
            emit('finished')
