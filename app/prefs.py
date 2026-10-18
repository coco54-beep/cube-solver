"""Shared preferences with atomic writes and Android-private persistence."""

import json
import logging
import os
import tempfile
import threading

_FILENAME = ".cubesolver_prefs.json"
_LEGACY_FILE = os.path.join(os.path.expanduser("~"), _FILENAME)
# python-for-android sets this to Context.getFilesDir() before importing Python.
# Keep preferences outside the extracted app directory, which upgrades replace.
_PRIVATE_DIR = os.environ.get("ANDROID_PRIVATE")
_PREFS_FILE = os.path.join(_PRIVATE_DIR, _FILENAME) if _PRIVATE_DIR else _LEGACY_FILE
_LOCK = threading.RLock()
_LOG = logging.getLogger(__name__)


def _read(path):
    with open(path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("Preferences must be a JSON object")
    return data


def _write(data):
    directory = os.path.dirname(os.path.abspath(_PREFS_FILE))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".prefs-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _PREFS_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load() -> dict:
    """Load preferences, migrating a readable legacy file on first use."""
    with _LOCK:
        try:
            return _read(_PREFS_FILE)
        except FileNotFoundError:
            if _PREFS_FILE != _LEGACY_FILE:
                try:
                    data = _read(_LEGACY_FILE)
                except FileNotFoundError:
                    return {}
                except (OSError, ValueError):
                    _LOG.warning("Could not read legacy preferences", exc_info=True)
                    return {}
                try:
                    _write(data)
                except OSError:
                    _LOG.warning("Could not migrate preferences", exc_info=True)
                return data
            return {}
        except (OSError, ValueError):
            _LOG.warning("Could not read preferences", exc_info=True)
            return {}


def get(key: str, default=None):
    return load().get(key, default)


def set(key: str, value):  # noqa: A001
    """Merge one preference, keeping other keys and the previous file on failure."""
    with _LOCK:
        data = load()
        data[key] = value
        try:
            _write(data)
        except (OSError, TypeError, ValueError):
            _LOG.warning("Could not save preference %s", key, exc_info=True)
