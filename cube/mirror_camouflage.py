"""Offset silver Camouflage, following pCubes' three selectively split bricks.

The material panels stay attached to their solids. Four invisible inner cells
are absent; a 4x4 backing with all 64 cells would introduce false collisions.
All lengths use D=.2 as one unit, in app coordinates (x,z,-y).
"""
from functools import lru_cache
from itertools import product

from cube.cuboid import CuboidCube, IDENTITY, transform, multiply, turn_frame
from cube.polyhedral import CUBE, Spec, Geometry, Sticker

KIND = 'mirror_camouflage_3'
SHELL = ((-3., 2.), (-2.25, 2.75), (-2.75, 2.25))


def _point(p):
    return (p[0], p[2], -p[1])


@lru_cache(maxsize=1)
def mirror_layout():
    cuts = ((-3., 0., 1., 2.), (-2.25, -1., 0., 2.75),
            (-2.25, -1., 0., 2.75))
    bins = (((0, 1), (2,), (3,)), ((0,), (1,), (2, 3)),
            ((0,), (1,), (2, 3)))
    cells, boxes = [], []
    # Only these three parts are visible after InvertVisibility/SplitByAxes.
    trims = {(1, 1, 2): (2, 1., 2.75, (3,)),
             (1, 2, 1): (1, 1., 2.75, (3,)),
             (0, 1, 1): (0, -3., -1., (0,))}
    for index in product(range(3), repeat=3):
        if index == (1, 1, 1):
            continue
        box = [(cuts[a][i], cuts[a][i+1]) for a, i in enumerate(index)]
        logical = [bins[a][i] for a, i in enumerate(index)]
        if index in trims:
            a, lo, hi, group = trims[index]
            box[a], logical[a] = (lo, hi), group
        cells.append(tuple(_point(tuple(2*v-3 for v in p)) for p in product(*logical)))
        boxes.append((box[0], box[2], (-box[1][1], -box[1][0])))
    stickers, entries, lookup = [], [], {}
    for piece, box in enumerate(boxes):
        for face, normal in enumerate(CUBE):
            a, sign = next((a, v) for a, v in enumerate(normal) if v)
            if box[a][int(sign > 0)] != SHELL[a][int(sign > 0)]:
                continue
            lookup[piece, face] = len(entries)
            entries.append((piece, normal))
            stickers.append(Sticker(piece, face, ()))
    identity = tuple(range(len(entries)))
    bounds = tuple(sign*SHELL[a][int(sign > 0)] for normal in CUBE
                   for a, sign in enumerate(normal) if sign)
    spec = Spec(KIND, 3, CUBE, CUBE, (), 4, bounds=bounds)
    base = Geometry(spec, tuple(stickers), tuple(() for _ in cells), (),
                    tuple((identity,)*3 for _ in CUBE), ())
    return tuple(cells), tuple(boxes), tuple(entries), lookup, base


@lru_cache(maxsize=26*24)
def shell_pose(piece, frame):
    """Whether a solid and each of its metal faces fit the restored shell."""
    cells, boxes, entries, lookup, base = mirror_layout()
    body = tuple(transform(frame, p) for p in product(*boxes[piece]))
    if any(not SHELL[a][0]-1e-8 <= p[a] <= SHELL[a][1]+1e-8
           for p in body for a in range(3)):
        return False
    for home in (s.face for s in base.stickers if s.piece == piece):
        normal = CUBE[home]
        a, sign = next((a, v) for a, v in enumerate(normal) if v)
        point = tuple(boxes[piece][j][int(sign > 0)] if j == a else 0.
                      for j in range(3))
        world, outward = transform(frame, point), transform(frame, normal)
        b, side = next((b, v) for b, v in enumerate(outward) if v)
        if abs(world[b]-SHELL[b][int(side > 0)]) > 1e-8:
            return False
    return True


class MirrorCamouflageCube(CuboidCube):
    panel_anchored = True
    material_only = True
    shell_bounds = SHELL
    shell_span = 5.
    pose_is_solved = staticmethod(shell_pose)

    def __init__(self, kind=KIND, colors=None, frames=None, history=None):
        fresh = colors is None
        super().__init__(kind, [0]*len(mirror_layout()[2]) if fresh else colors, frames, history)
        if fresh and frames is None and history is None:
            self.history = []

    @property
    def color_count(self):
        return 1

    def observation_color(self, piece, home_face):
        return 0

    @property
    def geometry(self):
        if self._geometry_cache is not None:
            return self._geometry_cache
        cells, boxes, entries, lookup, base = mirror_layout()
        current = [tuple(transform(frame, p) for p in group)
                   for frame, group in zip(self.frames, cells)]
        occupied = [p for group in current for p in group]
        if len(set(occupied)) != len(occupied):
            raise ValueError('Cuboid bricks overlap')
        stickers = tuple(Sticker(s.piece, CUBE.index(transform(self.frames[s.piece], CUBE[s.face])), ())
                         for s in base.stickers)
        pieces = tuple(tuple(i for i, s in enumerate(stickers) if s.piece == p)
                       for p in range(len(cells)))
        layers = []
        for normal in CUBE:
            a, sign = next((a, v) for a, v in enumerate(normal) if v)
            bands = []
            for depth in range(3):
                selected = []
                for p, group in enumerate(current):
                    flags = {sign*cell[a] >= 3-2*depth for cell in group}
                    if len(flags) != 1:
                        selected = []
                        break
                    if True in flags:
                        selected.append(p)
                bands.append(tuple(selected) if 0 < len(selected) < len(cells) else ())
            layers.append(tuple(bands))
        centres = tuple(transform(f, tuple((lo+hi)/2 for lo, hi in box))
                        for f, box in zip(self.frames, boxes))
        self._geometry_cache = Geometry(base.spec, stickers, pieces, centres,
                                        base.permutations, tuple(layers))
        return self._geometry_cache

    def apply_move(self, move):
        if move.amount % 4 == 0:
            return self
        if not self.can_apply(move):
            raise ValueError('This turn crosses a rigid cuboid brick')
        if (tuple(self.colors), self.frames) != self._snapshot:
            self.history = None
        moving = set(self.geometry.layers[move.axis][move.layer])
        rotation = turn_frame(move.axis, move.amount % 4)
        self.frames = tuple(multiply(rotation, f) if p in moving else f
                            for p, f in enumerate(self.frames))
        self._geometry_cache = None
        if self.history is not None:
            self.history.append(move)
            if len(self.history) > 4096:
                self.history = None
        self._snapshot = (tuple(self.colors), self.frames)
        return self

    def paint(self, index, color):
        if color not in (-1, 0):
            raise ValueError('Mirror Camouflage has one metal colour')
        super().paint(index, color)

    def is_solved(self):
        if any(c != 0 for c in self.colors):
            return False
        # An overall change of holding does not change the restored shape.
        from cube.appearance import ROTATIONS
        return any(all(shell_pose(p, multiply(holding, f)) for p, f in enumerate(self.frames))
                   for holding in ROTATIONS)
