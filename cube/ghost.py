"""Ghost cuboids and the five-axis first-order Floppy Ghost.

Integer cubies describe the aligned mechanism; phases record the real extra
horizontal-layer angles. Cross-axis moves require those phases to be zero.
"""
from functools import lru_cache
import math

from cube.mastermorphix import (MastermorphixCube, MorphixPiece, IDENTITY,
                                make_piece, positions_for_order, placements, transform, _clip)
from cube.coordinates import coord_values
from cube.colors import DEFAULT_COLORS
from cube.polyhedral import body, CUBE, rotate

def phase_token(index, angle):
    return f'@G{index}:{angle:g}'


def band_token(axis, layers, angle):
    return '@B'+','.join(str(v) for v in (axis, *layers))+f':{angle:g}'


def custom_move(token):
    if token.startswith('@B'):
        head, angle = token[2:].split(':')
        values = tuple(int(v) for v in head.split(','))
        if len(values) < 2 or values[0] not in (0,1,2) or float(angle) not in (-90.,90.,180.,-180.):
            raise ValueError('Invalid Ghost band turn')
        return ('band', (values[0], values[1:]), float(angle))
    if token.startswith('@G'):
        index, angle = token[2:].split(':')
        return ('phase', int(index), float(angle))
    if token.startswith('@F:') and token[3:] in ('1', '2', '3', '4', '5'):
        return ('floppy', int(token[3:])-1, 180.)
    raise ValueError('Invalid Ghost alignment move')


def inverse_move(token):
    if token.startswith('@'):
        kind, index, angle = custom_move(token)
        if kind == 'floppy':
            return token
        return phase_token(index, -angle) if kind == 'phase' else band_token(index[0],index[1],-angle)
    return token[:-1] if token.endswith("'") else token if token.endswith('2') else token + "'"


def goal_phases(n):
    return {1: (), 2: (-15., 20.), 3: (-15., 0., 20.),
            4: (-15., -5., 10., 20.)}[n]


def _floppy_piece(home, frame=IDENTITY, pos=None):
    stickers = {(0, 0, 1): DEFAULT_COLORS['F'], (0, 0, -1): DEFAULT_COLORS['B']}
    return MorphixPiece(home, home if pos is None else pos,
                        {transform(frame, normal): color for normal, color in stickers.items()}, frame)


def ghost_placements(n, home, pos):
    if n != 1:
        return placements(home, pos)
    from cube.ghost_floppy import placements as floppy_placements
    return floppy_placements(home, pos)


def ghost_piece(n, home, pos, frame):
    return _floppy_piece(home, frame, pos) if n == 1 else make_piece(home, pos, frame, n)


def _rotate_y(point, angle):
    return rotate(point, (0., 1., 0.), math.radians(angle))


@lru_cache(maxsize=256)
def piece_faces(n, home):
    if n == 1:
        from cube.ghost_floppy import piece_faces as floppy_faces
        return floppy_faces(home)
    # The slab is oblique to the mechanism and has no equal-looking colour
    # grid. Remove the layer's solved phase before clipping its X/Z cubies.
    frame = IDENTITY
    rotations = (((1/math.sqrt(3),)*3, 47.), ((1.,0.,0.), 7.), ((0.,0.,1.), 11.))
    for axis, angle in rotations:
        frame = tuple(rotate(v, axis, math.radians(angle)) for v in frame)
    half = (1.55, 1.55, 1.55)
    polygons = [(tuple(tuple(transform(frame, tuple(p[i]*half[i] for i in range(3)))[j]
                              + (.09, -.06, .04)[j] for j in range(3)) for p in face), 0)
                for face in body(CUBE)]
    if n > 1:
        values = coord_values(n)
        y_index = values.index(home[1])
        if y_index:
            polygons = _clip(polygons, 1, -1, -(-1.5 + 3*y_index/n))
        if y_index < n-1:
            polygons = _clip(polygons, 1, 1, -1.5 + 3*(y_index+1)/n)
        polygons = [(tuple(_rotate_y(p, -goal_phases(n)[y_index]) for p in points), color)
                    for points, color in polygons]
        for axis in (0, 2):
            index = values.index(home[axis])
            if index:
                polygons = _clip(polygons, axis, -1, -(-1.5 + 3*index/n))
            if index < n-1:
                polygons = _clip(polygons, axis, 1, -1.5 + 3*(index+1)/n)
    return tuple((tuple(points), color) for points, color in polygons)


class GhostCube(MastermorphixCube):
    puzzle_kind = 'ghost'
    distinct_piece_shapes = True

    def __init__(self, cubies=None, palette=('MIRROR',), n=3, phases=None):
        if n not in (1, 2, 3, 4):
            raise ValueError('Ghost supports catalogue models 1 to 4')
        self.n = self.size = n
        self.palette = ('MIRROR',)
        from cube.ghost_floppy import POSITIONS as floppy_positions
        self.positions = floppy_positions if n == 1 else positions_for_order(n)
        if n == 1 and cubies is not None and not set(cubies) <= set(self.positions):
            raise ValueError('ghost.invalid')  # Reject checkpoints from the obsolete nine-piece model.
        self.cubies = (dict(cubies) if cubies is not None else
                       {p: ghost_piece(n, p, p, IDENTITY) for p in self.positions})
        self.phases = tuple(goal_phases(n) if phases is None else phases)
        if len(self.phases) != (0 if n == 1 else n) or any(not math.isfinite(a) for a in self.phases):
            raise ValueError('Invalid Ghost layer angles')
        self._solving = False

    @classmethod
    def solved(cls, palette=('MIRROR',), n=3):
        return cls(n=n)

    def clone(self):
        result = type(self)({p: piece.clone() for p, piece in self.cubies.items()}, n=self.n, phases=self.phases)
        result._solving = self._solving
        return result

    def alignment_moves(self, restore=False):
        target = goal_phases(self.n) if restore else (0.,)*len(self.phases)
        return [phase_token(i, desired-current) for i, (current, desired) in enumerate(zip(self.phases, target))
                if abs(current-desired) > 1e-8]

    def can_turn_axis(self, axis):
        return self.n == 1 or axis == 1 or all(abs(angle) < 1e-8 for angle in self.phases)

    def apply_move(self, token):
        if token.startswith('@'):
            kind, index, angle = custom_move(token)
            if kind == 'phase':
                if self.n == 1 or not 0 <= index < self.n or not math.isfinite(angle):
                    raise ValueError('Invalid Ghost alignment layer')
                phases = list(self.phases)
                phases[index] = round(phases[index] + angle, 7)
                self.phases = tuple(phases)
            elif kind == 'band':
                self.turn_layer(index[0], index[1], int(angle/90))
            else:
                if self.n != 1:
                    raise ValueError('Floppy turns only apply to the first-order Ghost')
                from cube.ghost_floppy import FLIPS, CORNERS, moving_positions, compose
                moving = moving_positions(index)
                frame = FLIPS[index]
                result = dict(self.cubies)
                for pos, piece in self.cubies.items():
                    if pos in moving:
                        target = (moving[2] if pos == moving[1] else moving[1]) if pos in CORNERS else pos
                        orientation = compose(frame, piece.frame)
                        result[target] = _floppy_piece(piece.home, orientation, target)
                self.cubies = result
            return
        if self.n == 1:
            raise ValueError('The first-order Ghost uses 180-degree floppy turns')
        from renderer.turn import decompose_move
        if any(not self.can_turn_axis(step.axis) for step in decompose_move(token, self.n)):
            raise ValueError('ghost.align_required')
        super().apply_move(token)

    def turn_layer(self, axis, layers, sign):
        if self.n == 1 or not self.can_turn_axis(axis):
            raise ValueError('ghost.align_required')
        super().turn_layer(axis, layers, sign)

    def is_solved(self):
        if set(self.cubies) != set(self.positions):
            return False
        restored = all(piece.home == pos and piece.frame == IDENTITY for pos, piece in self.cubies.items())
        return restored and (self._solving or all(abs(a-b) < 1e-7
                                                for a, b in zip(self.phases, goal_phases(self.n))))
