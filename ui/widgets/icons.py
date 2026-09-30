"""Bundled Lucide alpha masks, cached and tinted by each button's theme."""

from functools import lru_cache
from pathlib import Path

from kivy.core.image import Image as CoreImage


_ICON_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons" / "lucide"


@lru_cache(maxsize=64)
def icon_image(name):
    path = _ICON_DIR / f"{name}.png"
    if not path.exists():
        return None
    return CoreImage(str(path))
