"""Serialize operations, not idle Hermes backend lifetimes."""
from contextlib import contextmanager
from functools import wraps
import fcntl


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with operation(self):
            return method(self, *args, **kwargs)
    return call


@contextmanager
def operation(backend):
    with backend._operation_lock:
        if backend.owner is not None:
            yield
            return
        # Keep the inode: unlinking a locked file would allow parallel owners.
        path = backend.lease.path.parent / 'session.lock'
        with open(path, 'a+') as owner:
            try:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('ownmachine_operation_busy_retry_read_after_active_call') from None
            backend.owner = owner
            try:
                owner.seek(0)
                if owner.read() != backend.session:
                    backend._clear()
                    backend.transport.stop()
                    backend._connected = False
                # Publish ownership before dispatch, so a crashed operation also
                # invalidates another backend's previously captured target.
                owner.seek(0)
                owner.truncate()
                owner.write(backend.session)
                owner.flush()
                yield
            finally:
                backend.owner = None
                fcntl.flock(owner, fcntl.LOCK_UN)
