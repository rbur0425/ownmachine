"""Refuse to act through an OwnMachine copy that the active Hermes profile did not install.

Hermes imports user computer-use providers under a fixed module name and reuses a
cached module without checking where it was loaded from. One long-lived process
that serves several profiles, or survives an in-place upgrade, can therefore run an
older OwnMachine copy for a profile that has a different one installed. That copy
would carry another profile's code and assumptions, so it must fail closed.
"""
import hashlib
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FILES = ('plugin.yaml', '.hermes-catalog.json')


def identity(root):
    """Digest of the small files an install or upgrade rewrites; never the code being run."""
    digest = hashlib.sha256()
    for name in IDENTITY_FILES:
        try:
            digest.update(name.encode() + b'\0' + (root / name).read_bytes() + b'\0')
        except OSError:
            digest.update(name.encode() + b'\0missing\0')
    return digest.hexdigest()


LOADED_IDENTITY = identity(PACKAGE_ROOT)


def expected_root():
    """The active profile's installed OwnMachine directory, or None when Hermes cannot say."""
    try:
        from hermes_constants import get_hermes_home
        candidate = Path(get_hermes_home()) / 'plugins' / 'ownmachine'
    except Exception:
        return None
    try:
        return candidate.resolve() if (candidate / '__init__.py').is_file() else None
    except OSError:
        return None


def mismatch():
    """None when this module is the active profile's install; otherwise a short reason code."""
    expected = expected_root()
    if expected is None:
        return None
    if expected != PACKAGE_ROOT:
        return 'ownmachine_provider_loaded_from_other_profile'
    if identity(expected) != LOADED_IDENTITY:
        return 'ownmachine_plugin_changed_since_load'
    return None


def require_active_install():
    reason = mismatch()
    if reason:
        raise RuntimeError(reason + ': restart this Hermes process so it loads the active profile install')
