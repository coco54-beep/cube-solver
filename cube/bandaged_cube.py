"""Cube-family bandage constraints.

The presets here describe rigidly glued cubie groups on ordinary 3x3/4x4
coordinate grids.  Turns that split one of those groups are rejected.  A
scramble history is retained so the app can return a legal inverse solution
for states it generated itself.
"""
from __future__ import annotations

import random

from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.notation import parse_move_full
from cube.coordinates import FACE_AXIS_SIGN, layer_values


KINDS = {
    'fused_cube': 3,
    'two_bar_cube': 3,
    'bandaged_c': 3,
    'bicube': 3,
    'ai_cube': 4,
    'burr_cube': 4,
}


def _group(cubies, ranges):
    return frozenset(home for home in cubies
                     if all(lo <= home[axis] <= hi for axis, lo, hi in ranges))


def _corner_block(cubies, signs, n):
    bounds = []
    for axis, sign in enumerate(signs):
        coords = sorted({p[axis] for p in cubies})
        edge = coords[-1] if sign > 0 else coords[0]
        next_in = coords[-2] if sign > 0 else coords[1]
        bounds.append((axis, min(edge, next_in), max(edge, next_in)))
    return _group(cubies, bounds)


# Face partitions transcribed from both complementary views of each puzzle.
# Letters are local to a face; repeated letters identify one continuous plate.
# Rows and columns use coordinates.pos_from_rc, so colour orientation is stable.
_FACE_PLATES = {
    'bicube': {
        'U': ('abb', 'cde', 'fde'),
        'R': ('aab', 'ccd', 'eef'),
        'F': ('abc', 'abd', 'efg'),
        'B': ('aab', 'ccb', 'dde'),
        'D': ('abc', 'abc', 'dee'),
        'L': ('abc', 'abc', 'dee'),
    },
    'bandaged_c': {
        'U': ('abc', 'dec', 'ffg'),
        'L': ('abc', 'dec', 'ffg'),
        'F': ('aab', 'aac', 'def'),
        'B': ('abc', 'ade', 'fgg'),
        'R': ('abb', 'cbb', 'def'),
        'D': ('abc', 'dde', 'ddf'),
    },
}


def _photographed_groups(cubies, kind):
    """Join plate cells across all six faces into physical rigid pieces."""
    from cube.coordinates import pos_from_rc
    parent = {home: home for home in cubies}

    def root(home):
        while parent[home] != home:
            parent[home] = parent[parent[home]]
            home = parent[home]
        return home

    for face, rows in _FACE_PLATES[kind].items():
        first = {}
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                home = pos_from_rc(3, face, r, c)
                other = first.setdefault(label, home)
                parent[root(home)] = root(other)
    groups = {}
    for home in sorted(parent):
        groups.setdefault(root(home), set()).add(home)
    return tuple(frozenset(group) for group in groups.values() if len(group) > 1)


def _profile(cubies, n, kind):
    vals = sorted({p[0] for p in cubies})
    if kind == 'fused_cube':
        return (_corner_block(cubies, (1, 1, 1), n),)
    if kind == 'two_bar_cube':
        # The two opposite 1x1x3 bars are the canonical Two-Bar layout.
        bars = []
        for sign in (-1, 1):
            x = vals[-1] if sign > 0 else vals[0]
            bars.append(frozenset(p for p in cubies if p[0] == x and p[1] == 0))
        return tuple(bars)
    if kind in _FACE_PLATES:
        return _photographed_groups(cubies, kind)
    if kind == 'ai_cube':
        # Four alternating 2x2x2 corner blocks on the 4x4 mechanism.
        signs = ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))
        return tuple(_corner_block(cubies, s, n) for s in signs)
    if kind == 'burr_cube':
        # Brick-wall dominoes on the 4x4 shell. The middle four bars on the
        # top/bottom are perpendicular to the outer rows (Burr arrangement).
        groups = []
        lo, hi = vals[0], vals[-1]
        for y in (lo, hi):
            plates = []
            for z in (lo, hi):
                for start in (0, 2):
                    plates.append(((vals[start], y, z), (vals[start+1], y, z)))
            for x in vals:
                plates.append(((x, y, vals[1]), (x, y, vals[2])))
            if y == lo:
                plates = [tuple((p[2], p[1], -p[0]) for p in pair) for pair in plates]
            groups.extend(frozenset(pair) for pair in plates)
        ring = [(x, lo) for x in vals]
        ring += [(hi, z) for z in vals[1:]]
        ring += [(x, hi) for x in reversed(vals[:-1])]
        ring += [(lo, z) for z in reversed(vals[1:-1])]
        for row, y in enumerate(vals[1:-1]):
            for i in range(0, len(ring), 2):
                a, b = ring[(i+row) % len(ring)], ring[(i+row+1) % len(ring)]
                groups.append(frozenset(((a[0], y, a[1]), (b[0], y, b[1]))))
        return tuple(groups)
    raise ValueError(f'Unknown bandaged cube preset: {kind}')


class BandagedCube(Cube3):
    """A 3x3 or 4x4 cube whose glued cubie groups constrain legal turns."""

    def __init__(self, cubies, kind, history=None):
        n = KINDS[kind]
        (Cube4 if n == 4 else Cube3).__init__(self, cubies)
        self.n = n
        self.puzzle_kind = kind
        from cube.appearance import with_appearance
        with_appearance(self, kind)
        self.groups = _profile({c.home for c in cubies.values()}, n, kind)
        self._by_home = {c.home: c for c in cubies.values()}
        self.history = list(history or ())

    @classmethod
    def solved(cls, kind):
        n = KINDS[kind]
        from cube.cube3 import Cube3
        from cube.cube4 import Cube4
        base = (Cube4 if n == 4 else Cube3).solved()
        return cls(base.cubies, kind)

    def clone(self):
        return type(self)({p: c.clone() for p, c in self.cubies.items()},
                          self.puzzle_kind, self.history)

    def can_turn(self, axis, layers):
        selected = set(layers)
        for group in self.groups:
            flags = {self._by_home[home].pos[axis] in selected
                     for home in group if home in self._by_home}
            if len(flags) > 1:
                return False
        return True

    def cubies_by_home(self, home):
        return self._by_home.get(home)

    def surface_group(self, pos, normal):
        """Coplanar facelets on the selected continuous bonded plate."""
        homes = {self.cubies[pos].home}
        changed = True
        while changed:
            changed = False
            for group in self.groups:
                if homes.intersection(group) and not group.issubset(homes):
                    homes.update(group)
                    changed = True
        return tuple(c.pos for c in self.cubies.values()
                     if c.home in homes and normal in c.stickers)

    def can_apply_layer_turn(self, axis, layers):
        return self.can_turn(axis, layers)

    def note_layer_turn(self, axis, layers, sign):
        from cube.ghost import band_token
        self.history.append(band_token(axis, tuple(sorted(layers)), 90. if sign > 0 else -90.))

    def apply_move(self, move_str):
        if move_str.startswith('@B'):
            from cube.ghost import custom_move
            kind, index, angle = custom_move(move_str)
            if kind != 'band':
                raise ValueError('Invalid bandaged cube move')
            for _ in range(max(1, int(abs(angle) // 90))):
                self.apply_layer_turn(index[0], index[1], 1 if angle > 0 else -1)
            return
        if move_str and move_str[0] in ('M', 'E', 'S'):
            raise ValueError('Bandaged cube does not allow free middle-slice turns')
        label, layers, count = parse_move_full(move_str)
        if label in ('x', 'y', 'z'):
            from cube.coordinates import WHOLE_CUBE
            for _ in range(count):
                self._rotate_all(WHOLE_CUBE[label])
            self._by_home = {c.home: c for c in self.cubies.values()}
            self.history.append(move_str)
            return
        selected = set(layer_values(self.n, label, layers=layers))
        axis, _ = FACE_AXIS_SIGN[label]
        for _ in range(count):
            if not self.can_turn(axis, selected):
                raise ValueError(f'Illegal bandage turn: {move_str}')
            self._apply_single_quarter(label, layers)
        self._by_home = {c.home: c for c in self.cubies.values()}
        self.history.append(move_str)

    def apply_layer_turn(self, axis, layers, sign):
        if not self.can_turn(axis, layers):
            raise ValueError('This turn would split a fused block')
        from renderer.twist import apply_layer_turn
        apply_layer_turn(self.cubies, axis, list(layers), sign)
        self._by_home = {c.home: c for c in self.cubies.values()}
        self.note_layer_turn(axis, layers, sign)

    @classmethod
    def random_scramble(cls, kind, length=24, seed=None):
        rng = random.Random(seed)
        cube = cls.solved(kind)
        faces = ('R', 'L', 'U', 'D', 'F', 'B')
        # AI's 2x2x2 blocks need two-layer turns from the solved position;
        # Burr also needs wide layers to change the wall alignment.
        if cube.n == 4:
            faces += tuple(face.lower() for face in faces)
        previous = None
        for _ in range(max(0, length)):
            choices = []
            for face in faces:
                if face.upper() == previous:
                    continue
                for suffix in ('', "'", '2'):
                    move = face + suffix
                    try:
                        # Test legality on the current state without mutating it.
                        label, layers, _count = parse_move_full(move)
                        selected = set(layer_values(cube.n, label, layers=layers))
                        axis, _ = FACE_AXIS_SIGN[label]
                        if cube.can_turn(axis, selected):
                            choices.append(move)
                    except ValueError:
                        continue
            if not choices:
                # At a constrained dead end, permit the previous face; a
                # legal inverse move always exists for a reachable state.
                for face in faces:
                    for suffix in ('', "'", '2'):
                        move = face + suffix
                        try:
                            label, layers, _count = parse_move_full(move)
                            selected = set(layer_values(cube.n, label, layers=layers))
                            axis, _ = FACE_AXIS_SIGN[label]
                            if cube.can_turn(axis, selected):
                                choices.append(move)
                        except ValueError:
                            continue
            if not choices:
                raise RuntimeError(f'No legal turn found for {kind}')
            move = rng.choice(choices)
            cube.apply_move(move)
            previous = move[0].upper()
        return cube

    def solution_from_history(self):
        from cube.ghost import inverse_move
        return [inverse_move(m) for m in reversed(self.history)]


def make_bandaged_cube(cubies, kind):
    if kind not in KINDS:
        raise ValueError(kind)
    return BandagedCube(cubies, kind)
