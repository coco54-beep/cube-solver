"""Cuboids with an NxN core and independently movable outer extensions.

Panels stay attached to physical pieces. The extra outer layer is not a
bandaged layer of a larger cube. It turns only when a whole plane is present.
Mechanisms: Jaap's cube446.htm and cube234.htm; the cubic-core tower family
uses the same extension construction with cores of order two, three and four.
"""
from functools import lru_cache
from itertools import product

from cube.cuboid import CuboidCube, MODELS, IDENTITY, transform, multiply, turn_frame
from cube.polyhedral import CUBE, Geometry, Spec, Sticker, Move

CORE_DIMENSIONS = {
    'cuboid_224': (2, 2, 2), 'cuboid_335': (3, 3, 3),
    'cuboid_446': (4, 4, 4), 'cuboid_234': (2, 2, 3),
}


@lru_cache(maxsize=4)
def extended_layout(kind):
    dims = CORE_DIMENSIONS[kind]
    display, n = MODELS[kind]
    values = tuple(tuple(range(1-d, d, 2)) for d in dims)
    core = tuple(product(*values))
    cells = [[p] for p in core]
    free = []
    for piece, p in enumerate(core):
        if abs(p[1]) != dims[1]-1:
            continue
        outer = (p[0], (dims[1]+1)*(1 if p[1] > 0 else -1), p[2])
        if abs(p[0]) < dims[0]-1 and abs(p[2]) < dims[2]-1:
            cells[piece].append(outer)
        else:
            free.append([outer])
    cells.extend(free)
    cells = tuple(tuple(g) for g in cells)
    boxes = tuple(tuple((min(p[a] for p in g)/2-.5, max(p[a] for p in g)/2+.5)
                        for a in range(3)) for g in cells)
    entries = []; lookup = {}; stickers = []
    for piece, group in enumerate(cells):
        for face, normal in enumerate(CUBE):
            axis, sign = next((a, v) for a, v in enumerate(normal) if v)
            boundary = dims[axis]+1 if axis == 1 else dims[axis]-1
            home = next((p for p in group if p[axis] == sign*boundary), None)
            if home is None:
                continue
            lookup[piece, face] = len(entries)
            entries.append((home, normal)); stickers.append(Sticker(piece, face, ()))
    steps = []
    for normal in CUBE:
        a = next(a for a, v in enumerate(normal) if v)
        others = [dims[j] for j in range(3) if j != a]
        steps.append(1 if others[0] % 2 == others[1] % 2 else 2)
    spec = Spec(kind, max(display), CUBE, CUBE, (), 4, axis_steps=tuple(steps),
                bounds=tuple(display[next(a for a, v in enumerate(norm) if v)]/2 for norm in CUBE))
    identity = tuple(range(len(stickers)))
    permutations = tuple((identity,)*(n-1) for _ in CUBE)
    base = Geometry(spec, tuple(stickers), tuple(() for _ in cells), (), permutations, ())
    return cells, boxes, tuple(entries), lookup, base


class ExtendedCuboid(CuboidCube):
    panel_anchored = True

    @property
    def core_dimensions(self):
        return CORE_DIMENSIONS[self.puzzle_kind]

    @property
    def core_count(self):
        x, y, z = self.core_dimensions
        return x*y*z

    @property
    def geometry(self):
        if self._geometry_cache is not None:
            return self._geometry_cache
        dims = self.core_dimensions
        cells, boxes, entries, lookup, base = extended_layout(self.puzzle_kind)
        current = tuple(tuple(transform(f, p) for p in g) for f, g in zip(self.frames, cells))
        flat = [p for g in current for p in g]
        if len(set(flat)) != len(flat):
            raise ValueError('Cuboid pieces overlap')
        expected = set(product(*(range(1-d, d, 2) for d in dims)))
        core_positions = tuple(g[0] for g in current[:self.core_count])
        if set(core_positions) != expected:
            raise ValueError('Invalid cuboid core')
        outer = set(flat)-expected
        demanded = set()
        for i, g in enumerate(cells[:self.core_count]):
            p = g[0]
            if abs(p[1]) == dims[1]-1:
                demanded.add(transform(self.frames[i], (p[0], (dims[1]+1)*(1 if p[1] > 0 else -1), p[2])))
        if outer != demanded:
            raise ValueError('Outer extensions do not match the core')
        def anchor(p):
            return tuple(max(1-dims[a], min(dims[a]-1, p[a])) for a in range(3))
        anchors = tuple(core_positions[i] if i < self.core_count else anchor(g[0]) for i, g in enumerate(current))
        def outer_plane(axis, sign):
            wanted = set(product(*(range(1-d, d, 2) if a != axis else (sign*(d+1),)
                                   for a, d in enumerate(dims))))
            if not wanted <= outer:
                return ()
            return tuple(i for i, g in enumerate(current) if any(p in wanted for p in g))
        layers = []
        for normal in CUBE:
            a, sign = next((a, v) for a, v in enumerate(normal) if v)
            bands = [outer_plane(a, sign)]
            for width in range(1, self.core_n-1):
                if width < dims[a]:
                    threshold = dims[a]-1-2*(width-1)
                    bands.append(tuple(i for i, p in enumerate(anchors) if sign*p[a] >= threshold))
                elif width == dims[a]:
                    opposite = outer_plane(a, -sign)
                    bands.append(tuple(i for i in range(len(cells)) if i not in opposite) if opposite else ())
                else:
                    bands.append(())
            layers.append(tuple(bands))
        stickers = tuple(Sticker(s.piece, CUBE.index(transform(self.frames[s.piece], CUBE[s.face])), ())
                         for s in base.stickers)
        pieces = tuple(tuple(i for i, s in enumerate(stickers) if s.piece == p) for p in range(len(cells)))
        centres = tuple(transform(f, tuple((lo+hi)/2 for lo, hi in box)) for f, box in zip(self.frames, boxes))
        self._geometry_cache = Geometry(base.spec, stickers, pieces, centres, base.permutations, tuple(layers))
        return self._geometry_cache

    def apply_move(self, move):
        if move.amount % 4 == 0:
            return self
        if not self.can_apply(move):
            raise ValueError('This outer cuboid layer is incomplete')
        if (tuple(self.colors), self.frames) != self._snapshot:
            self.history = None
        moving = set(self.geometry.layers[move.axis][move.layer])
        rotation = turn_frame(move.axis, move.amount % 4)
        self.frames = tuple(multiply(rotation, f) if i in moving else f for i, f in enumerate(self.frames))
        self._geometry_cache = None
        if self.history is not None:
            self.history.append(move)
            if len(self.history) > 4096:
                self.history = None
        self._snapshot = (tuple(self.colors), self.frames)
        return self

    def is_solved(self):
        if any(c != s.face for c, s in zip(self.colors, self.geometry.stickers)):
            return False
        _, boxes, *_ = extended_layout(self.puzzle_kind)
        bounds = tuple(d/2 for d in self.dimensions)
        return all(all(abs(p[a]) <= bounds[a]+1e-8 for a in range(3))
                   for f, box in zip(self.frames, boxes) for p in (transform(f, c) for c in product(*box)))

    def layer_labels(self, axis):
        from app.i18n import tr
        a = next(a for a, v in enumerate(CUBE[axis]) if v)
        return tuple(tr('cuboid.extension_layer') if i == 0 and band else
                     tr('cuboid.core_layers', i=i) if band and i < self.core_dimensions[a] else
                     tr('cuboid.outer_layers', i=i+1) if band else tr('cuboid.layer_blocked', i=i+1)
                     for i, band in enumerate(self.geometry.layers[axis]))
