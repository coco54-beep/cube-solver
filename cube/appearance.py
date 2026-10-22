"""Exterior identities for cube variants which share the ordinary grid engine.

Keep this metadata on the state, rather than looking at the current app page:
thumbnails, input, twisting, playback and restored sessions must agree.
"""
from functools import lru_cache
from itertools import permutations, product

from cube.colors import DEFAULT_COLORS
from cube.coordinates import FACE_NORMALS

IDENTITY_FRAME = ((1,0,0),(0,1,0),(0,0,1))


def transform_frame(frame, point):
    return tuple(sum(frame[j][i]*point[j] for j in range(3)) for i in range(3))


def _rotations():
    frames=[]
    for perm in permutations(range(3)):
        for signs in product((-1,1), repeat=3):
            frame=tuple(tuple(signs[j] if i==perm[j] else 0 for i in range(3)) for j in range(3))
            a,b,c=frame
            cross=(a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
            if sum(x*y for x,y in zip(cross,c))==1: frames.append(frame)
    return (IDENTITY_FRAME,)+tuple(f for f in frames if f!=IDENTITY_FRAME)


ROTATIONS = _rotations()
_HOME_NORMAL = {color: FACE_NORMALS[face] for face,color in DEFAULT_COLORS.items()}


@lru_cache(maxsize=8192)
def infer_frame(home, pos, stickers):
    constraints=[(_HOME_NORMAL[c],n) for n,c in stickers if c in _HOME_NORMAL]
    candidates=[f for f in ROTATIONS if all(transform_frame(f,a)==b for a,b in constraints)]
    if not candidates: candidates=list(ROTATIONS)
    return next((f for f in candidates if transform_frame(f,home)==pos), candidates[0])


def frame_for(cubie):
    return getattr(cubie, 'appearance_frame', None) or infer_frame(
        tuple(cubie.home), tuple(cubie.pos), tuple(sorted(cubie.stickers.items())))

VARIANTS = frozenset((
    'fused_cube', 'two_bar_cube', 'bandaged_c', 'bicube', 'ai_cube',
    'burr_cube', 'penrose_2', 'penrose_3', 'penrose_4',
))
PENROSE = frozenset(('penrose_2', 'penrose_3', 'penrose_4'))

# Paired adjacent mechanical faces form the three continuous Penrose surfaces:
# U/R (red), F/L (blue), D/B (yellow). Logical colour identities stay distinct.
PENROSE_RGB = {
    'W': (.91, .075, .095, 1.), 'R': (.91, .075, .095, 1.),
    'G': (.035, .46, .88, 1.), 'O': (.035, .46, .88, 1.),
    'Y': (1., .88, .025, 1.), 'B': (1., .88, .025, 1.),
}


def kind_for(cube):
    kind = getattr(cube, 'appearance_kind', getattr(cube, 'puzzle_kind', None))
    return kind if kind in VARIANTS else None


def with_appearance(cube, kind):
    if kind in VARIANTS:
        cube.appearance_kind = kind
        for cubie in cube.cubies.values():
            if getattr(cubie, 'appearance_frame', None) is None:
                cubie.appearance_frame = frame_for(cubie)
    return cube
