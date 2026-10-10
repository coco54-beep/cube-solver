"""Four-color Mastermorphix with oriented, shaped pieces on a 2-9 mechanism.

The four tetrahedron tips and four small triangles are the eight corners.
On order three, twelve single-color wedges are edges and six seams are centers;
higher orders subdivide those edge and center regions into independent orbits.
Virtual six-color stickers are internal solver labels, never user input.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product
import math

from cube.cube3 import Cube3
from cube.cubie_model import Cubie, build_solved_cube
from cube.colors import DEFAULT_COLORS
from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS, TURNS, WHOLE_CUBE, get_d_maxc, layer_values

IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
DEFAULT_PALETTE = ("R", "Y", "B", "G")
NORMALS = ((-1, -1, -1), (-1, 1, 1), (1, -1, 1), (1, 1, -1))
VERTICES = ((2, 2, 2), (2, -2, -2), (-2, 2, -2), (-2, -2, 2))
AXIS_FACES = ("U", "R", "F", "D", "L", "B")


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def transform(frame, point):
    return tuple(sum(frame[j][i] * point[j] for j in range(3)) for i in range(3))


def _rotations():
    result = []
    for perm in permutations(IDENTITY):
        for signs in product((-1, 1), repeat=3):
            frame = tuple(tuple(s*x for x in v) for s, v in zip(signs, perm))
            if dot(frame[0], cross(frame[1], frame[2])) == 1:
                result.append(frame)
    return tuple(sorted(result, key=lambda frame: frame != IDENTITY))


ROTATIONS = _rotations()
POSITIONS = tuple(p for p in product((-1, 0, 1), repeat=3) if any(p))


@lru_cache(maxsize=8)
def positions_for_order(n):
    """Surface-piece coordinates for an order-N Mastermorphix mechanism."""
    if not 2 <= n <= 9:
        raise ValueError("Mastermorphix orders must be between 2 and 9")
    return tuple(build_solved_cube(n, DEFAULT_COLORS))


def position_kind(pos):
    # Coordinates away from the center are nonzero on even and higher-order
    # cubes too. A sticker exists only on an outermost coordinate.
    maximum = max(abs(v) for v in pos)
    return ("", "center", "edge", "corner")[sum(abs(v) == maximum for v in pos)]


def position_name(pos):
    maximum = max(abs(v) for v in pos)
    return "".join(f for f in AXIS_FACES
                   if pos[FACE_AXIS_SIGN[f][0]] == FACE_AXIS_SIGN[f][1] * maximum)


def placements(home, pos):
    frames = tuple(frame for frame in ROTATIONS if transform(frame, home) == pos)
    if frames and position_kind(pos) == "center":
        # Enumerate continuous clockwise quarter turns, not rotation-table
        # order. Both the input cards and their rotate button use this order.
        turn = TURNS[position_name(pos)]
        frame = frames[0]
        ordered = []
        for _ in frames:
            ordered.append(frame)
            frame = tuple(turn(*axis) for axis in frame)
        return tuple(ordered)
    return frames


def _clip(polygons, axis, sign, bound):
    output, cuts = [], []
    for vertices, color in polygons:
        clipped = []
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            da, db = sign*a[axis]-bound, sign*b[axis]-bound
            if da <= 1e-9:
                clipped.append(a)
            if (da < -1e-9 and db > 1e-9) or (db < -1e-9 and da > 1e-9):
                t = da / (da-db)
                point = tuple(a[i]+t*(b[i]-a[i]) for i in range(3))
                clipped.append(point)
                cuts.append(point)
        # Coalesce shared clipping vertices, including on-plane endpoints.
        unique = []
        for p in clipped:
            if not any(sum((p[i]-q[i])**2 for i in range(3)) < 1e-16 for q in unique):
                unique.append(p)
        if len(unique) >= 3:
            output.append((unique, color))
            cuts.extend(p for p in unique if abs(sign*p[axis]-bound) < 1e-8)
    unique = {tuple(round(x, 9) for x in p) for p in cuts}
    if len(unique) >= 3:
        center = tuple(sum(p[i] for p in unique)/len(unique) for i in range(3))
        normal = tuple(sign if i == axis else 0 for i in range(3))
        u = IDENTITY[(axis+1) % 3]
        v = cross(normal, u)
        cap = sorted(unique, key=lambda p: math.atan2(dot(tuple(p[i]-center[i] for i in range(3)), v),
                                                    dot(tuple(p[i]-center[i] for i in range(3)), u)))
        output.append((cap, -1))
    return output


@lru_cache(maxsize=2048)
def piece_geometry(home, n=3):
    if n not in (2, 3):
        return cut_curved_pieces(n, 12)[home]
    polygons = []
    for index, normal in enumerate(NORMALS):
        vertices = [v for v in VERTICES if abs(dot(normal, v)-2) < 1e-9]
        a, b, c = vertices
        if dot(cross(tuple(b[i]-a[i] for i in range(3)), tuple(c[i]-a[i] for i in range(3))), normal) < 0:
            vertices.reverse()
        polygons.append((vertices, index))
    vals = sorted({p[0] for p in positions_for_order(n)})
    # A 2x2 Pyramorphix is cut by the three central planes. Each outer
    # tetrahedral face has one middle triangle and three corner triangles.
    boundaries = [-2., 0., 2.] if n == 2 else [-2., -.5, .5, 2.]
    for axis, coord in enumerate(home):
        index = vals.index(coord)
        lo, hi = boundaries[index], boundaries[index+1]
        polygons = _clip(polygons, axis, 1, hi)
        polygons = _clip(polygons, axis, -1, -lo)
    return tuple((tuple(vertices), color) for vertices, color in polygons)


def cut_boundaries(n):
    """Symmetric mechanism planes, with room for every high-order piece.

    The curved high-order body contains the mechanism's inner cube. Equal
    inner layer widths shrink both kinds of corners as the order increases;
    its extended tips are part of the outer layers rather than warped cuts.
    """
    if n == 2:
        return (-2., 0., 2.)
    if n == 3:
        return (-2., -.5, .5, 2.)
    if not 4 <= n <= 9:
        raise ValueError("Mastermorphix orders must be between 2 and 9")
    return (-3.,) + tuple(-1.5 + 3.*i/n for i in range(1, n)) + (3.,)


@lru_cache(maxsize=10000)
def _high_order_point(point):
    """Four spherical face patches forming a convex curved tetrahedral body.

    This is an intersection of equal balls about the opposite tetrahedron
    vertices. Its broad curved faces expose the small mono-color corners
    even at order nine. Radial projection applies only to the uncut exterior;
    all mechanism cuts are made afterwards and stay planar.
    """
    length2 = dot(point, point)
    scale = min((dot(point, vertex) +
                 math.sqrt(dot(point, vertex)**2 + 20.*length2)) / length2
                for vertex in VERTICES)
    return tuple(scale * value for value in point)


@lru_cache(maxsize=4)
def high_order_body(subdivisions=12):
    output = []
    for color, normal in enumerate(NORMALS):
        a, b, c = [v for v in VERTICES if abs(dot(normal, v)-2.) < 1e-9]
        if dot(cross(tuple(b[i]-a[i] for i in range(3)),
                     tuple(c[i]-a[i] for i in range(3))), normal) < 0:
            b, c = c, b

        def point(i, j):
            return _high_order_point(tuple(((subdivisions-i-j)*a[k]+i*b[k]+j*c[k]) /
                                          subdivisions for k in range(3)))

        for i in range(subdivisions):
            for j in range(subdivisions-i):
                output.append(((point(i, j), point(i+1, j), point(i, j+1)), color))
                if i+j < subdivisions-1:
                    output.append(((point(i+1, j), point(i+1, j+1), point(i, j+1)), color))
    return tuple(output)


@lru_cache(maxsize=12)
def cut_curved_pieces(n, subdivisions=12):
    """Partition once per order; shared cuts have identical vertices.

    Reusing clipped strips avoids clipping the complete body separately for
    every one of the 386 nine-order pieces, including in gallery thumbnails.
    """
    vals = sorted({pos[0] for pos in positions_for_order(n)})
    boundaries = cut_boundaries(n)

    def strip(polygons, axis, index):
        lo, hi = boundaries[index:index+2]
        return _clip(_clip(polygons, axis, 1, hi), axis, -1, -lo)

    body = high_order_body(subdivisions)
    output = {}
    for ix, x in enumerate(vals):
        x_strip = strip(body, 0, ix)
        for iy, y in enumerate(vals):
            xy_strip = strip(x_strip, 1, iy)
            for iz, z in enumerate(vals):
                if not any(index in (0, n-1) for index in (ix, iy, iz)):
                    continue
                output[x, y, z] = tuple((tuple(points), color)
                                        for points, color in strip(xy_strip, 2, iz))
    return output


def piece_colors(home, palette=DEFAULT_PALETTE, n=3):
    return tuple(palette[i] for i in sorted({color for _, color in piece_geometry(home, n) if color >= 0}))


@dataclass
class MorphixPiece(Cubie):
    frame: tuple = IDENTITY

    def clone(self):
        return MorphixPiece(self.home, self.pos, dict(self.stickers), self.frame)


@lru_cache(maxsize=8)
def _virtual_cubies(n):
    return build_solved_cube(n, DEFAULT_COLORS)


def make_piece(home, pos, frame, n=3):
    virtual = _virtual_cubies(n)[home]
    return MorphixPiece(home, pos, {transform(frame, n): col for n, col in virtual.stickers.items()}, frame)


def geometry_signature(piece, palette, n=3):
    return tuple(sorted((palette[color] if color >= 0 else "_",
                         tuple(sorted(tuple(round(x, 7) for x in transform(piece.frame, p)) for p in verts)))
                        for verts, color in piece_geometry(piece.home, n)))


def equivalent_placements(piece, palette, n=3):
    signature = geometry_signature(piece, palette, n)
    candidates = []
    for home in positions_for_order(n):
        if position_kind(home) != position_kind(piece.pos):
            continue
        if piece_colors(home, palette, n) != piece_colors(piece.home, palette, n):
            continue
        for frame in placements(home, piece.pos):
            candidate = make_piece(home, piece.pos, frame, n)
            if geometry_signature(candidate, palette, n) == signature:
                candidates.append(candidate)
    return candidates


class _RotMap(dict):
    """Memoises a rotation formula over the small set of coordinates it sees."""

    __slots__ = ("rot",)

    def __init__(self, rot):
        self.rot = rot

    def __missing__(self, value):
        result = self.rot(*value)
        self[value] = result
        return result


_ROT_MAPS = {}


def _rot_map(rot):
    table = _ROT_MAPS.get(rot)
    if table is None:
        table = _RotMap(rot)
        _ROT_MAPS[rot] = table
    return table


class _FrameMap(dict):
    """Memoises rotation of a whole piece frame (a handful of orientations)."""

    __slots__ = ("scalar",)

    def __init__(self, rot):
        self.scalar = _rot_map(rot)

    def __missing__(self, frame):
        result = tuple(map(self.scalar.__getitem__, frame))
        self[frame] = result
        return result


_FRAME_MAPS = {}


def _frame_map(rot):
    table = _FRAME_MAPS.get(rot)
    if table is None:
        table = _FrameMap(rot)
        _FRAME_MAPS[rot] = table
    return table


@lru_cache(maxsize=128)
def _layer_positions(n, label, layers):
    axis = FACE_AXIS_SIGN[label][0]
    values = set(layer_values(n, label, layers=layers))
    return frozenset(p for p in positions_for_order(n) if p[axis] in values)


@lru_cache(maxsize=16)
def _all_positions(n):
    return frozenset(positions_for_order(n))


@lru_cache(maxsize=16)
def _inner_positions(n, axis):
    return frozenset(p for p in positions_for_order(n)
                     if p[axis] == 0 and position_kind(p) != "center")


class MastermorphixCube(Cube3):
    puzzle_kind = "mastermorphix"

    def __init__(self, cubies, palette=DEFAULT_PALETTE, n=3):
        super().__init__(cubies)
        if len(palette) != 4 or len(set(palette)) != 4:
            raise ValueError("Mastermorphix requires four different colors")
        self.palette = tuple(palette)
        if not 2 <= n <= 9:
            raise ValueError("Mastermorphix orders must be between 2 and 9")
        self.n = n
        self.size = n
        self.positions = positions_for_order(n)

    @classmethod
    def solved(cls, palette=DEFAULT_PALETTE, n=3):
        return cls({p: make_piece(p, p, IDENTITY, n) for p in positions_for_order(n)}, palette, n)

    def clone(self):
        return type(self)({p: c.clone() for p, c in self.cubies.items()}, self.palette, self.n)

    def _apply_single_quarter(self, label, layers):
        if label in WHOLE_CUBE:
            self._rotate_all(WHOLE_CUBE[label])
            return
        self._rotate_pieces(TURNS[label], _layer_positions(self.n, label, layers))

    def _rotate_all(self, rot):
        self._rotate_pieces(rot, _all_positions(self.n))

    def apply_inner_slice(self, axis_label, turns=1):
        axis = {"x": 0, "y": 1, "z": 2}[axis_label]
        for _ in range(turns % 4):
            self._rotate_pieces(WHOLE_CUBE[axis_label], _inner_positions(self.n, axis))

    def turn_layer(self, axis, layers, sign):
        """Apply a dragged mechanical slice, including high-order inner layers."""
        from cube.coordinates import coord_values
        if axis not in (0, 1, 2) or not set(layers).issubset(coord_values(self.n)):
            raise ValueError('Invalid mechanical layer')
        moving=frozenset(p for p in self.positions if p[axis] in layers
                         and not (self.n%2 and p[axis]==0 and sum(v!=0 for v in p)==1))
        for _ in range(sign%4):
            self._rotate_pieces(TURNS[('L', 'D', 'B')[axis]], moving)

    def _rotate_pieces(self, rot, moving):
        rotate = _rot_map(rot)
        frames = _frame_map(rot)
        cubies = self.cubies
        result = dict(cubies)
        for pos in moving:
            piece = cubies[pos]
            new_pos = rotate[pos]
            result[new_pos] = MorphixPiece(
                piece.home, new_pos,
                {rotate[n]: col for n, col in piece.stickers.items()},
                frames[piece.frame])
        self.cubies = result

    def center_twists(self):
        _, maxc = get_d_maxc(self.n)
        counts = []
        for face in AXIS_FACES:
            pos = tuple(value * maxc for value in FACE_NORMALS[face])
            piece = self.cubies[pos]
            if piece.home != pos:
                raise ValueError("Two-color centers must stay on their reference axes")
            frame = IDENTITY
            for count in range(4):
                if piece.frame == frame:
                    counts.append(count)
                    break
                frame = tuple(TURNS[face](*v) for v in frame)
            else:
                raise ValueError("Invalid center orientation")
        return tuple(counts)

    def is_solved(self):
        if set(self.cubies) != set(self.positions):
            return False
        target = type(self).solved(self.palette, self.n)
        return all(geometry_signature(piece, self.palette, self.n) == geometry_signature(target.cubies[pos], self.palette, self.n)
                   for pos, piece in self.cubies.items())


class MorphixInputError(ValueError):
    pass


def normalize_input(cube):
    """Resolve invisible labels/twists without altering any physical geometry."""
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import _tface, _tcubie, _build_cubestring

    if cube.n != 3:
        raise MorphixInputError("invalid")
    if set(cube.cubies) != set(cube.positions):
        raise MorphixInputError("incomplete")
    work = cube.clone()
    corner_homes = [c.home for c in work.cubies.values() if position_kind(c.pos) == "corner"]
    if len(set(corner_homes)) != 8:
        raise MorphixInputError("duplicate")
    try:
        center_twists = work.center_twists()
    except ValueError as exc:
        raise MorphixInputError("centers") from exc

    def cubie_state():
        fc = _tface.FaceCube()
        fc.from_string(_build_cubestring(cubies_to_facelets(work.cubies, 3)))
        return fc.to_cubie_cube()

    state = cubie_state()
    if state.corner_parity() != sum(center_twists) % 2:
        raise MorphixInputError("center_parity")
    # Generated scrambles already have legal virtual identities. Relabeling
    # them needlessly changes the two-phase search, even for solved geometry.
    if state.verify() == _tcubie.CUBE_OK:
        return work
    neutral = next((c for c in work.cubies.values() if position_kind(c.pos) == "corner"
                    and len(piece_colors(c.home, work.palette)) == 1), None)
    if neutral is not None:
        for candidate in equivalent_placements(neutral, work.palette):
            work.cubies[neutral.pos] = candidate
            if sum(cubie_state().co) % 3 == 0:
                break
    if sum(cubie_state().co) % 3:
        raise MorphixInputError("corner_twist")

    edges = [c for c in work.cubies.values() if position_kind(c.pos) == "edge"]
    options = [equivalent_placements(c, work.palette) for c in edges]
    # Three same-color wedges can have indistinguishable physical shapes.
    # Assign their virtual identities as an exact matching problem, then use
    # the 3x3 orientation/permutation constraints to choose a legal labeling.
    def assign(index, used):
        if index == len(edges):
            return cubie_state().verify() == _tcubie.CUBE_OK
        for candidate in options[index]:
            if candidate.home in used:
                continue
            work.cubies[edges[index].pos] = candidate
            if assign(index+1, used | {candidate.home}):
                return True
        return False

    if not assign(0, set()):
        raise MorphixInputError("invalid")
    return work
