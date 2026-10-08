"""Four-color Mastermorphix: a 3x3 mechanism with oriented, shaped pieces.

The four tetrahedron tips and four small triangles are the eight corners;
the twelve single-color wedges are edges; the six two-color seams are centers.
Virtual six-color stickers are internal solver labels, never user input.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product
import math

from cube.cube3 import Cube3
from cube.cubie_model import Cubie, build_solved_cube
from cube.colors import DEFAULT_COLORS
from cube.coordinates import FACE_AXIS_SIGN, FACE_NORMALS, TURNS, WHOLE_CUBE, layer_values

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


def position_kind(pos):
    return ("", "center", "edge", "corner")[sum(v != 0 for v in pos)]


def position_name(pos):
    return "".join(f for f in AXIS_FACES if pos[FACE_AXIS_SIGN[f][0]] == FACE_AXIS_SIGN[f][1])


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


@lru_cache(maxsize=26)
def piece_geometry(home):
    polygons = []
    for index, normal in enumerate(NORMALS):
        vertices = [v for v in VERTICES if abs(dot(normal, v)-2) < 1e-9]
        a, b, c = vertices
        if dot(cross(tuple(b[i]-a[i] for i in range(3)), tuple(c[i]-a[i] for i in range(3))), normal) < 0:
            vertices.reverse()
        polygons.append((vertices, index))
    for axis, coord in enumerate(home):
        lo, hi = (-2, -.5) if coord == -1 else ((-.5, .5) if coord == 0 else (.5, 2))
        polygons = _clip(polygons, axis, 1, hi)
        polygons = _clip(polygons, axis, -1, -lo)
    return tuple((tuple(vertices), color) for vertices, color in polygons)


def piece_colors(home, palette=DEFAULT_PALETTE):
    return tuple(palette[i] for i in sorted({color for _, color in piece_geometry(home) if color >= 0}))


@dataclass
class MorphixPiece(Cubie):
    frame: tuple = IDENTITY

    def clone(self):
        return MorphixPiece(self.home, self.pos, dict(self.stickers), self.frame)


def make_piece(home, pos, frame):
    virtual = build_solved_cube(3, DEFAULT_COLORS)[home]
    return MorphixPiece(home, pos, {transform(frame, n): col for n, col in virtual.stickers.items()}, frame)


def geometry_signature(piece, palette):
    return tuple(sorted((palette[color] if color >= 0 else "_",
                         tuple(sorted(tuple(round(x, 7) for x in transform(piece.frame, p)) for p in verts)))
                        for verts, color in piece_geometry(piece.home)))


def equivalent_placements(piece, palette):
    signature = geometry_signature(piece, palette)
    candidates = []
    for home in POSITIONS:
        if position_kind(home) != position_kind(piece.pos):
            continue
        if piece_colors(home, palette) != piece_colors(piece.home, palette):
            continue
        for frame in placements(home, piece.pos):
            candidate = make_piece(home, piece.pos, frame)
            if geometry_signature(candidate, palette) == signature:
                candidates.append(candidate)
    return candidates


class MastermorphixCube(Cube3):
    puzzle_kind = "mastermorphix"

    def __init__(self, cubies, palette=DEFAULT_PALETTE):
        super().__init__(cubies)
        if len(palette) != 4 or len(set(palette)) != 4:
            raise ValueError("Mastermorphix requires four different colors")
        self.palette = tuple(palette)

    @classmethod
    def solved(cls, palette=DEFAULT_PALETTE):
        return cls({p: make_piece(p, p, IDENTITY) for p in POSITIONS}, palette)

    def clone(self):
        return type(self)({p: c.clone() for p, c in self.cubies.items()}, self.palette)

    def _apply_single_quarter(self, label, layers):
        if label in WHOLE_CUBE:
            self._rotate_all(WHOLE_CUBE[label])
            return
        axis, _ = FACE_AXIS_SIGN[label]
        selected = set(layer_values(3, label, layers=layers))
        self._rotate_pieces(TURNS[label], lambda pos: pos[axis] in selected)

    def _rotate_all(self, rot):
        self._rotate_pieces(rot, lambda pos: True)

    def apply_inner_slice(self, axis_label, turns=1):
        axis = {"x": 0, "y": 1, "z": 2}[axis_label]
        for _ in range(turns % 4):
            self._rotate_pieces(WHOLE_CUBE[axis_label],
                                lambda pos: pos[axis] == 0 and position_kind(pos) != "center")

    def _rotate_pieces(self, rot, selected):
        result = {}
        for piece in self.cubies.values():
            if selected(piece.pos):
                piece = piece.clone()
                piece.pos = rot(*piece.pos)
                piece.stickers = {rot(*n): col for n, col in piece.stickers.items()}
                piece.frame = tuple(rot(*v) for v in piece.frame)
            result[piece.pos] = piece
        self.cubies = result

    def center_twists(self):
        counts = []
        for face in AXIS_FACES:
            pos = FACE_NORMALS[face]
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
        if set(self.cubies) != set(POSITIONS):
            return False
        target = type(self).solved(self.palette)
        return all(geometry_signature(piece, self.palette) == geometry_signature(target.cubies[pos], self.palette)
                   for pos, piece in self.cubies.items())


class MorphixInputError(ValueError):
    pass


def normalize_input(cube):
    """Resolve invisible labels/twists without altering any physical geometry."""
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import _tface, _tcubie, _build_cubestring

    if set(cube.cubies) != set(POSITIONS):
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
