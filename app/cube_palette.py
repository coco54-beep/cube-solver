"""Ordinary cube display colours, separate from logical IDs and scan calibration."""
from app.constants import COLOR_INFO

# Same face order as the palette reference net: U, R, F, D, L, B.
FACE_CODES=('W','R','G','Y','O','B')
_defaults={code:tuple(COLOR_INFO[code][1]) for code in FACE_CODES}
_cached=None


def default_palette():return dict(_defaults)


def _valid(colors):
    return (isinstance(colors,(list,tuple)) and len(colors)==6 and
            all(isinstance(c,(list,tuple)) and len(c)==4 and
                all(isinstance(v,(int,float)) and 0<=v<=1 for v in c) for c in colors) and
            len({tuple(c[:3]) for c in colors})==6)


def get_palette():
    global _cached
    if _cached is None:
        from app.prefs import get
        colors=get('cube_display_palette',None)
        _cached=(dict(zip(FACE_CODES,(tuple(c[:3])+(1.,) for c in colors)))
                 if _valid(colors) else default_palette())
    return dict(_cached)


def save_palette(colors):
    global _cached
    if not _valid(colors):raise ValueError('Invalid cube display palette')
    from app.prefs import set
    palette={code:tuple(c[:3])+(1.,) for code,c in zip(FACE_CODES,colors)}
    set('cube_display_palette',[list(palette[c]) for c in FACE_CODES])
    _cached=palette
