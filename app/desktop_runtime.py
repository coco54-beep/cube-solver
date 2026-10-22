"""Choose desktop graphics before any module imports Kivy's window."""
from importlib.util import find_spec
import os
import site
import sys

# PyInstaller never runs ``site.main()``, so ``site.USER_BASE`` stays None in
# the frozen build. The ``kivy_deps`` packages (angle/glew/sdl2) call
# ``os.path.join(site.USER_BASE, ...)`` while Kivy imports, which raises
# ``TypeError: expected str, bytes or os.PathLike object, not NoneType``.
# Give them a real path before Kivy is imported.
if getattr(site, 'USER_BASE', None) is None:
    site.USER_BASE = os.path.expanduser('~')
if getattr(site, 'USER_SITE', None) is None:
    site.USER_SITE = os.path.join(site.USER_BASE, 'Python', 'site-packages')


def configure_graphics():
    """Prefer installed ANGLE on Windows; retain explicit backend choices."""
    if sys.platform != 'win32' or os.environ.get('KIVY_GL_BACKEND'):
        return
    # Checking dependency metadata must not initialise Kivy/OpenGL. SDL2
    # loads ANGLE's EGL/GLES libraries after the backend has been selected.
    try:
        available = (find_spec('kivy_deps.angle') is not None
                     and find_spec('kivy_deps.sdl2') is not None)
    except (ImportError, ModuleNotFoundError, ValueError):
        available = False
    if available:
        os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'
        os.environ.setdefault('KIVY_WINDOW', 'sdl2')
        print('cubesolver: Windows graphics backend = angle_sdl2', flush=True)
