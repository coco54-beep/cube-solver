"""Exact colour-state table for the four-axis Ivy Cube."""
from functools import lru_cache
from pathlib import Path
import zlib

from cube.polyhedral import Move, PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import identify, inverse, simplify

STATE_COUNT = 81 * 720
UNREACHABLE = 255
SOLVED = 254


class IvyStates:
    """Four base-three corner orientations and a six-centre permutation."""
    def __init__(self, geometry):
        self.g = geometry
        self.goal = bytes(s.face for s in geometry.stickers)
        self.moves = tuple(Move(axis, 0, amount) for axis in range(4) for amount in (1, 2))
        self.maps = tuple(inverse(geometry.permutation(move)) for move in self.moves)
        self.corners = []
        for axis, bands in enumerate(geometry.layers):
            piece = next(p for p in bands[0] if len(geometry.pieces[p]) == 3)
            slots = geometry.pieces[piece]
            orientations = {}
            for amount in range(3):
                mapping = inverse(geometry.permutation(Move(axis, 0, amount)))
                colors = tuple(self.goal[mapping[s]] for s in slots)
                orientations[colors] = amount
            self.corners.append((slots, orientations))
        self.centres = tuple(sorted((slots[0] for slots in geometry.pieces if len(slots) == 1),
                                    key=lambda s: geometry.stickers[s].face))

    def encode(self, colors):
        orientation = 0
        for slots, options in self.corners:
            value = options.get(tuple(colors[s] for s in slots))
            if value is None:
                raise ValueError('A piece has a mirrored or impossible orientation')
            orientation = orientation * 3 + value
        permutation = tuple(colors[s] for s in self.centres)
        if set(permutation) != set(range(6)):
            raise ValueError('A piece has an impossible color combination or position')
        rank = 0
        for i, value in enumerate(permutation):
            rank = rank * (6-i) + sum(other < value for other in permutation[i+1:])
        return rank * 81 + orientation


@lru_cache(maxsize=1)
def _prepared():
    model = IvyStates(PolyhedralPuzzle('ivy', 3).geometry)
    path = Path(__file__).parent / 'data' / 'ivy_moves.bin'
    payload = zlib.decompress(path.read_bytes())
    if (len(payload) != 36 + STATE_COUNT or payload[:4] != b'IVY1' or
            payload[4:36] != bytes.fromhex(geometry_key(model.g))):
        raise ValueError('The Ivy solver assets do not match this model')
    return model, payload[36:]


def solve_ivy(cube, cancel=None, progress=None):
    if cancel and cancel():
        raise InterruptedError()
    identify(cube)
    model, table = _prepared()
    work = cube.entered()
    solution = []
    visited = set()
    while True:
        if cancel and cancel():
            raise InterruptedError()
        code = model.encode(work.colors)
        action = table[code]
        if action == UNREACHABLE:
            raise ValueError('The entered puzzle is not a legal state')
        if action == SOLVED:
            break
        if code in visited or action >= len(model.moves):
            raise ValueError('The Ivy solver assets do not match this model')
        visited.add(code)
        move = model.moves[action]
        work.apply_move(move)
        solution.append(move)
        if progress:
            progress(len(solution), len(solution)+1)
    if not work.is_solved():
        raise ValueError('Polyhedral reduction replay failed')
    if progress:
        progress(len(solution), len(solution))
    return simplify(solution, 3)
