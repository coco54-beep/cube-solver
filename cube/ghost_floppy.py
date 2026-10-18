"""Five-axis Floppy Megaminx mechanism inside the first catalogue Ghost.

Position keys are identifiers, not Cartesian cubie coordinates. Five fixed
edge pieces flip in place, each exchanging its two neighbouring corners.
The central pentagon never turns. Frames belong to the proper D5 group.
"""
import math
from functools import lru_cache

from cube.mastermorphix import IDENTITY, transform
from cube.polyhedral import body, CUBE, rotate, clip, dot, cross, mean

CORE = (0, 0, 0)
EDGES = tuple((i+1, 0, 0) for i in range(5))
CORNERS = tuple((i+1, 1, 0) for i in range(5))
POSITIONS = (CORE,) + EDGES + CORNERS
AXES = tuple((math.cos(math.radians(90+72*i)),
              math.sin(math.radians(90+72*i)), 0.) for i in range(5))


def _frame(axis, angle):
    return tuple(tuple(round(x, 12) for x in rotate(v, axis, math.radians(angle)))
                 for v in IDENTITY)


FLIPS = tuple(_frame(axis, 180) for axis in AXES)
FRAMES = (IDENTITY,) + tuple(_frame((0., 0., 1.), 72*i) for i in range(1, 5)) + FLIPS


def compose(left, right):
    product = tuple(transform(left, row) for row in right)
    return min(FRAMES, key=lambda f: sum((f[j][i]-product[j][i])**2
                                       for i in range(3) for j in range(3)))


def moving_positions(side):
    return (EDGES[side], CORNERS[side], CORNERS[(side-1) % 5])


def _corner_point(index):
    angle = math.radians(126+72*index)
    return (math.cos(angle), math.sin(angle), 0.)


@lru_cache(maxsize=128)
def placements(home, pos):
    if home == CORE:
        return (IDENTITY,) if pos == CORE else ()
    if home in EDGES:
        return (IDENTITY, FLIPS[EDGES.index(home)]) if pos == home else ()
    if home not in CORNERS or pos not in CORNERS:
        return ()
    a, b = _corner_point(CORNERS.index(home)), _corner_point(CORNERS.index(pos))
    return tuple(f for f in FRAMES if sum((x-y)**2 for x, y in zip(transform(f, a), b)) < 1e-16)


def _clip_solid(polygons, normal, bound):
    result, intersections = [], []
    for points, color in polygons:
        kept = clip(points, normal, bound)
        if len(kept) >= 3:
            result.append((tuple(kept), color))
            intersections.extend(p for p in kept if abs(dot(normal, p)-bound) < 1e-8)
    unique = tuple({tuple(round(v, 10) for v in p) for p in intersections})
    if len(unique) >= 3:
        centre = mean(unique)
        u = (0., 0., 1.)
        v = cross(normal, u)
        cap = sorted(unique, key=lambda p: math.atan2(dot(tuple(p[i]-centre[i] for i in range(3)), v),
                                                     dot(tuple(p[i]-centre[i] for i in range(3)), u)))
        result.append((tuple(cap), -1))
    return result


@lru_cache(maxsize=11)
def piece_faces(home):
    # Oblique square slab: the five mechanical cuts become unequal polygons
    # on its broad faces, including the large, fixed central pentagon.
    half = (1.5, 1.5, .30)
    shell_frame = tuple(rotate(rotate(v, (1., 0., 0.), math.radians(18)),
                               (0., 1., 0.), math.radians(12)) for v in IDENTITY)
    polygons = [(tuple(tuple(transform(shell_frame, tuple(p[i]*half[i] for i in range(3)))[j]
                              + (.06, -.04, .02)[j] for j in range(3)) for p in face), 0)
                for face in body(CUBE)]
    outside = ({EDGES.index(home)} if home in EDGES else
               {CORNERS.index(home), (CORNERS.index(home)+1) % 5} if home in CORNERS else set())
    for i, normal in enumerate(AXES):
        sign = -1 if i in outside else 1
        polygons = _clip_solid(polygons, tuple(sign*v for v in normal), sign*.82)
    return tuple(polygons)


def state_key(cube):
    """Compact full shape state; include corner flips, not just permutation."""
    if set(cube.cubies) != set(POSITIONS):
        raise ValueError('ghost.invalid')
    if cube.cubies[CORE].home != CORE or cube.cubies[CORE].frame != IDENTITY:
        raise ValueError('ghost.invalid')
    permutation, corner_bits, edge_bits = [], 0, 0
    for i, pos in enumerate(CORNERS):
        piece = cube.cubies[pos]
        if piece.frame not in placements(piece.home, pos):
            raise ValueError('ghost.invalid')
        permutation.append(CORNERS.index(piece.home))
        corner_bits |= int(piece.frame[2][2] < 0) << i
    if len(set(permutation)) != 5:
        raise ValueError('ghost.invalid')
    for i, pos in enumerate(EDGES):
        piece = cube.cubies[pos]
        if piece.home != pos or piece.frame not in placements(pos, pos):
            raise ValueError('ghost.invalid')
        edge_bits |= int(piece.frame != IDENTITY) << i
    return tuple(permutation) + (corner_bits, edge_bits)


def turn_state(state, side):
    permutation = list(state[:5])
    a, b = side, (side-1) % 5
    permutation[a], permutation[b] = permutation[b], permutation[a]
    bits = state[5]
    first, second = (bits >> a) & 1, (bits >> b) & 1
    bits = (bits & ~((1 << a) | (1 << b))) | ((1-second) << a) | ((1-first) << b)
    return tuple(permutation) + (bits, state[6] ^ (1 << side))
