"""Translate published algorithm notation into this application's real moves."""
from dataclasses import dataclass
from functools import lru_cache
import math
import re

from cube.polyhedral import (Move, PolyhedralPuzzle, dot, geometry, key, mean,
                             rotate, scale, unit)
from cube.cubie_model import BaseCube, build_solved_cube

SKEWB_CORNERS = {
    'F': (1, 1, 1), 'R': (1, 1, -1), 'B': (-1, 1, -1), 'L': (-1, 1, 1),
    'f': (1, -1, 1), 'r': (1, -1, -1), 'b': (-1, -1, -1), 'l': (-1, -1, 1),
}
SKEWB_MACROS = {'S': "R r' R' r", 'H': "r' R r R'"}


class FormulaCube(BaseCube):
    """Standard speedcubing wide/slice notation, including moving grip centers.

    The solver's physical inner-slice convention and its 2/3-layer shortcut
    are intentionally not used to interpret published speedcubing formulas.
    """
    standard_notation = True

    def __init__(self, order, cubies=None):
        from demo.cases import TEACHING_COLORS
        super().__init__(cubies if cubies is not None else build_solved_cube(order, TEACHING_COLORS))
        self.n = order

    def clone(self):
        return type(self)(self.n, {p: c.clone() for p, c in self.cubies.items()})

    def _rotate_selected(self, axis, positions, rotation):
        updated = {}
        for cubie in self.cubies.values():
            if cubie.pos[axis] in positions:
                cubie = cubie.clone()
                cubie.pos = rotation(*cubie.pos)
                cubie.stickers = {rotation(*normal): color for normal, color in cubie.stickers.items()}
            updated[cubie.pos] = cubie
        self.cubies = updated

    def _apply_single_quarter(self, label, layers):
        from cube.coordinates import FACE_AXIS_SIGN, TURNS, coord_values
        if label in ('x', 'y', 'z'):
            return super()._apply_single_quarter(label, layers)
        axis, sign = FACE_AXIS_SIGN[label]
        positions = {sign * p for p in sorted(coord_values(self.n), reverse=True)[:layers]}
        self._rotate_selected(axis, positions, TURNS[label])

    def apply_move(self, move_str):
        from cube.coordinates import WHOLE_CUBE
        from cube.notation import parse_suffix
        if move_str[:1] in ('M', 'E', 'S'):
            face = move_str[0]
            count = parse_suffix(move_str[1:])
            if face in 'ME':
                count = -count % 4
            axis = {'M': 0, 'E': 1, 'S': 2}[face]
            rotation = WHOLE_CUBE[('x', 'y', 'z')[axis]]
            for _ in range(count):
                self._rotate_selected(axis, {0}, rotation)
            return
        return super().apply_move(move_str)


def animation_steps(move, cube):
    from renderer.turn import decompose_move
    from cube.coordinates import FACE_AXIS_SIGN, coord_values
    from cube.notation import parse_move_full
    steps = decompose_move(move, cube.n)
    step = steps[0]
    if move[:1] in ('M', 'E'):
        step.angle = -step.angle
    elif move[:1] not in ('M', 'E', 'S', 'x', 'y', 'z'):
        label, width, _ = parse_move_full(move)
        _, sign = FACE_AXIS_SIGN[label]
        step.layers = tuple(sign * p for p in sorted(coord_values(cube.n), reverse=True)[:width])
    return steps


class NotationError(ValueError):
    pass


def expand(algorithm):
    """Expand parentheses, repetitions, conjugates and commutators."""
    text = algorithm.replace('’', "'").replace('′', "'").replace('−', '-')
    text = re.sub(r'//[^\n]*', '', text)
    tokens = re.findall(r"\d*[-A-Za-z]+(?:\d+)?'?\d*|\d+'?|'|[()\[\],:]", text)
    # Reject prose or punctuation instead of silently dropping a move.
    residue = re.sub(r"\d*[-A-Za-z]+(?:\d+)?'?\d*|\d+'?|'|[()\[\],:]|\s", '', text)
    if residue:
        raise NotationError('Unsupported notation: ' + residue)
    position = 0

    def inverse(word):
        return [v[:-1] if v.endswith("'") else v + "'" for v in reversed(word)]

    def sequence(stops=()):
        nonlocal position
        result = []
        while position < len(tokens) and tokens[position] not in stops:
            current = tokens[position]
            position += 1
            if current == '(':
                group = sequence((')',))
                if position >= len(tokens):
                    raise NotationError('Unclosed parentheses')
                position += 1
            elif current == '[':
                first = sequence((',', ':', ']'))
                if position >= len(tokens) or tokens[position] == ']':
                    raise NotationError('Missing commutator separator')
                separator = tokens[position]
                position += 1
                second = sequence((']',))
                if position >= len(tokens):
                    raise NotationError('Unclosed commutator')
                position += 1
                group = first + second + inverse(first)
                if separator == ',':
                    group += inverse(second)
            elif current in (')', ']', ',', ':'):
                raise NotationError('Unexpected notation delimiter')
            else:
                result.append(current)
                continue
            if position < len(tokens) and re.fullmatch(r"\d+'?|'", tokens[position]):
                suffix = tokens[position]
                position += 1
                if suffix.endswith("'"):
                    group = inverse(group)
                group *= int(suffix.rstrip("'") or 1)
            result.extend(group)
        return result

    result = sequence()
    if position != len(tokens) or not result:
        raise NotationError('Empty or incomplete algorithm')
    return result


def _parts(token):
    match = re.fullmatch(r"([A-Za-z]+)(\d*)('?)(\d*)", token)
    if not match or (match[2] and match[4]):
        raise NotationError('Unsupported move: ' + token)
    return match[1], int(match[2] or match[4] or 1) * (-1 if match[3] else 1)


def cube_moves(algorithm, order):
    from cube.notation import suffix_for_count
    result = []
    for token in expand(algorithm):
        match = re.fullmatch(r"(\d*)([RLUDFBrludfbMESxyz])(w?)(\d*)('?)(\d*)", token)
        if not match:
            raise NotationError('Unsupported cube move: ' + token)
        prefix, face, wide, power, prime, trailing_power = match.groups()
        count = int(power or trailing_power or 1) * (-1 if prime else 1) % 4
        if not count:
            continue
        suffix = suffix_for_count(count)
        if face in 'MES' and order % 2 == 0:
            raise NotationError('An even cube needs an explicit slice range')
        if wide or face.islower() and face not in 'xyz':
            width = int(prefix or 2)
            if not 1 <= width <= order:
                raise NotationError('Wide turn exceeds cube order')
            base = face.upper() if width == 1 else face.lower() if width == 2 else str(width) + face.upper()
            result.append(base + suffix)
        elif prefix:
            # In SpeedCubeDB, 2R is the second slice, whereas this app's 2R
            # means a two-layer wide turn. Express the slice as two wide turns.
            depth = int(prefix)
            if not 1 <= depth <= order:
                raise NotationError('Slice exceeds cube order')
            base = face if depth == 1 else face.lower() if depth == 2 else str(depth) + face
            result.append(base + suffix)
            if depth > 1:
                inner = face if depth == 2 else face.lower() if depth == 3 else str(depth - 1) + face
                result.append(inner + suffix_for_count((-count) % 4))
        else:
            result.append(face + suffix)
    return tuple(result)


@dataclass(frozen=True)
class FormulaTurn(Move):
    notation: str = ''
    layers: tuple = ()

    def inverse(self, order):
        label = self.notation[:-1] if self.notation.endswith("'") else self.notation + "'"
        return FormulaTurn(self.axis, self.layer, -self.amount % order, label, self.layers)


@dataclass(frozen=True)
class FormulaRotation:
    rotation_axis: tuple
    angle: float
    notation: str

    def inverse(self, order=None):
        label = self.notation[:-1] if self.notation.endswith("'") else self.notation + "'"
        return FormulaRotation(self.rotation_axis, -self.angle, label)


@lru_cache(maxsize=128)
def rotation_permutation(kind, axis, angle):
    g = geometry(kind, 3)
    positions = {key(mean(s.polygon)): i for i, s in enumerate(g.stickers)}
    try:
        permutation = tuple(positions[key(rotate(mean(s.polygon), axis, math.radians(angle)))]
                            for s in g.stickers)
    except KeyError as exc:
        raise NotationError('Whole rotation is not a symmetry of this puzzle') from exc
    if len(set(permutation)) != len(g.stickers):
        raise NotationError('Whole rotation is not bijective')
    return permutation


class FormulaPolyhedralCube(PolyhedralPuzzle):
    """The usual sticker state plus exact whole-puzzle rotations for tutorials."""
    def apply_move(self, move):
        if isinstance(move, FormulaRotation):
            perm = rotation_permutation(self.puzzle_kind, move.rotation_axis, move.angle)
            result = list(self.colors)
            for source, destination in enumerate(perm):
                result[destination] = self.colors[source]
            self.colors = result
        elif getattr(move, 'layers', ()):
            for layer in move.layers:
                super().apply_move(Move(move.axis, layer, move.amount))
        else:
            super().apply_move(move)
        return self


def polyhedral_moves(algorithm, kind):
    g = geometry(kind, 3)
    result = []
    # Rubikskewb notation, as used by SpeedCubeDB's Sarah's Advanced set.
    corners = SKEWB_CORNERS
    minx_names = ('U', 'F', 'L', 'BL', 'BR', 'R', 'FR', 'FL', 'DL', 'B', 'DR', 'D')
    for token in expand(algorithm):
        face, count = _parts(token)
        if face in 'xyz' and len(face) == 1:
            vector = {'x': (1., 0., 0.), 'y': (0., 1., 0.), 'z': (0., 0., 1.)}[face]
            degrees = -90 * count
            if kind == 'megaminx' and face == 'y':
                degrees = -72 * count
            elif kind == 'pyraminx' and face == 'y':
                vector, degrees = g.spec.axes[1], -120 * count
            move = FormulaRotation(vector, degrees, token)
            rotation_permutation(kind, vector, degrees)
            result.append(move)
            continue
        if kind == 'skewb':
            if face in ('S', 'H'):
                # Explicit macros avoid interpreting S as a cube middle slice.
                macro = SKEWB_MACROS[face]
                word = polyhedral_moves(macro, kind)
                if count < 0:
                    word = tuple(m.inverse(3) for m in reversed(word))
                result.extend(word * abs(count))
                continue
            if face not in corners:
                raise NotationError('Unsupported Rubikskewb move: ' + token)
            vector = unit(corners[face])
            axis = max(range(len(g.spec.axes)), key=lambda i: abs(dot(vector, g.spec.axes[i])))
            sign = 1 if dot(vector, g.spec.axes[axis]) > 0 else -1
            layer = 0 if sign == 1 else len(g.layers[axis]) - 1
            result.append(FormulaTurn(axis, layer, -sign * count % 3, token))
        elif kind == 'pyraminx':
            if face.upper() not in ('U', 'L', 'R', 'B'):
                raise NotationError('Unsupported Pyraminx move: ' + token)
            axis = {'U': 1, 'L': 2, 'R': 0, 'B': 3}[face.upper()]
            layers = (0, 1) if face.isupper() else (0,)
            result.append(FormulaTurn(axis, layers[-1], -count % 3, token, layers))
        else:
            face = {'Br': 'BR', 'Bl': 'BL', 'dR': 'FR', 'dL': 'FL', 'dr': 'FR', 'dl': 'FL'}.get(face, face)
            if face not in minx_names:
                raise NotationError('Unsupported Megaminx face: ' + token)
            result.append(FormulaTurn(minx_names.index(face), 0, -count % 5, token))
    return tuple(result)


def square1_moves(algorithm):
    from cube.square1 import Square1Move
    text = re.sub(r'\s+', '', algorithm.replace('−', '-'))
    result = []
    pattern = re.compile(r'/|\((-?\d+),(-?\d+)\)|(-?\d+),(-?\d+)')
    end = 0
    for match in pattern.finditer(text):
        if match.start() != end:
            raise NotationError('Unsupported Square-1 notation')
        end = match.end()
        if match.group() == '/':
            result.append(Square1Move(2))
        else:
            values = match.groups()[:2] if match[1] is not None else match.groups()[2:]
            for axis, value in enumerate(values):
                amount = int(value)
                if amount % 12:
                    result.append(Square1Move(axis, amount))
    if end != len(text) or not result:
        raise NotationError('Empty or incomplete Square-1 algorithm')
    return tuple(result)


def compile_algorithm(puzzle, algorithm):
    if puzzle in ('2x2', '3x3', '4x4', '5x5'):
        return cube_moves(algorithm, int(puzzle[0]))
    if puzzle == 'SQ1':
        return square1_moves(algorithm)
    return polyhedral_moves(algorithm, {'Skewb': 'skewb', 'Pyraminx': 'pyraminx', 'Megaminx': 'megaminx'}[puzzle])
