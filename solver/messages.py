"""Localised solver messages with a headless fallback.

Solvers are used by tests and command-line tools without Kivy installed.  The
UI translation module imports Kivy, so keep a safe fallback here and use the
real translator whenever the app runtime provides it.
"""

try:
    from app.i18n import tr
except ImportError:
    def tr(key, **kwargs):
        return key.format(**kwargs) if kwargs else key
