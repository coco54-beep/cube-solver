"""Crash-loop protection for the one automatic startup checkpoint.

The marker deliberately outlives the process: a native crash or a force-close
during restoration must not cause the same checkpoint to load on every launch.
"""
import hashlib
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
import weakref

_LOG = logging.getLogger(__name__)


class RestoreProtection:
    def __init__(self, path):
        self.path = Path(path)
        self.marker = self.path.with_name('last-session.restore-pending.json')
        self.backup = None
        self.block_save = False
        self._handler = None

    def begin(self):
        if self.path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('Checkpoint too large')
        raw = self.path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if self.marker.exists():
            try:
                pending = json.loads(self.marker.read_text(encoding='utf-8'))
                interrupted = pending.get('digest') == digest
            except (ValueError, OSError, AttributeError):
                interrupted = True
            if interrupted:
                raise ValueError('Previous checkpoint restoration did not finish')
        # Atomic, durable marker before decoding models or entering any screen.
        # If storage is unwritable, skip restoration instead of trying without
        # crash-loop protection.
        fd, name = tempfile.mkstemp(prefix='.restore-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'digest': digest}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.marker)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return raw

    def quarantine(self):
        """Move the untouched source aside; never overwrite a previous backup."""
        if self.path.exists():
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup = self.path.with_name(
                f'last-session.failed-{stamp}-{uuid.uuid4().hex[:8]}.json')
            try:
                os.replace(self.path, backup)
                self.backup = backup
                _LOG.warning('Checkpoint isolated at %s', backup)
            except OSError:
                # Preserve the original even when it cannot be moved. Do not
                # let autosave overwrite the only copy with the recovery page.
                self.block_save = True
                _LOG.exception('Could not isolate checkpoint; autosave suspended')
                return
        self.clear_marker()

    def clear_marker(self):
        try:
            self.marker.unlink(missing_ok=True)
        except OSError:
            _LOG.exception('Could not clear checkpoint restoration marker')

    def guard(self, store):
        """Catch delayed Kivy entry/draw failures only during startup restore."""
        from kivy.base import ExceptionHandler, ExceptionManager
        owner = weakref.ref(store)

        class Handler(ExceptionHandler):
            def handle_exception(self, error):
                current = owner()
                if (current is None or not current.restoring or
                        current._restore_failed_once or not isinstance(error, Exception)):
                    return ExceptionManager.RAISE
                current._restore_failed(error, deferred=True)
                return ExceptionManager.PASS

        self._handler = Handler()
        ExceptionManager.add_handler(self._handler)
        # A test or aborted app build may discard the store without a clock tick.
        weakref.finalize(store, ExceptionManager.remove_handler, self._handler)

    def unguard(self):
        if self._handler is not None:
            from kivy.base import ExceptionManager
            ExceptionManager.remove_handler(self._handler)
            self._handler = None
