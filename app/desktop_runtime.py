"""Choose desktop graphics before any module imports Kivy's window."""
from importlib.util import find_spec
import os
import sys


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
