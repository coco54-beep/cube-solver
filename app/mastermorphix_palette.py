"""Four selectable standard or custom colors, persisted as RGBA values."""

from app.constants import COLOR_INFO
from app.prefs import get, set
from cube.mastermorphix import DEFAULT_PALETTE


def load_palette(entries=None):
    if entries is None:
        entries = get("mastermorphix_palette", list(DEFAULT_PALETTE))
    if not isinstance(entries, (list, tuple)) or len(entries) != 4:
        entries = DEFAULT_PALETTE
    palette = []
    for index, value in enumerate(entries):
        if isinstance(value, str) and value in COLOR_INFO:
            palette.append(value)
        elif isinstance(value, (list, tuple)) and len(value) in (3, 4):
            try:
                rgba = tuple(max(0., min(1., float(v))) for v in value[:3]) + (1.,)
            except (ValueError, TypeError):
                return load_palette(DEFAULT_PALETTE)
            key = f"M{index}"
            COLOR_INFO[key] = (str(index+1), rgba)
            palette.append(key)
        else:
            return load_palette(DEFAULT_PALETTE)
    if len({COLOR_INFO[c][1][:3] for c in palette}) != 4:
        return load_palette(DEFAULT_PALETTE)
    return tuple(palette)


def palette_entries(palette):
    return [list(COLOR_INFO[c][1]) if c.startswith("M") else c for c in palette]


def save_palette(entries):
    palette = load_palette(entries)
    set("mastermorphix_palette", palette_entries(palette))
    return palette
