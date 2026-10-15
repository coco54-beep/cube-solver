"""Verified, optional formula finishes; the state solver remains the fallback.

The packaged index contains only ordinary native moves. No tutorial model,
scramble history, notation dialect or whole-puzzle rotation reaches playback.
"""
from base64 import b64decode
from functools import lru_cache
import json
from pathlib import Path
from time import monotonic
import zlib

FACES = ('U', 'R', 'F', 'D', 'L', 'B')


@lru_cache(maxsize=1)
def _tables():
    try:
        data = json.loads(zlib.decompress(
            (Path(__file__).parent / 'data' / 'formula_finishes.bin').read_bytes()))
        if data['version'] != 1:
            return {}, {}
        tables = {puzzle: {b64decode(k): v for k, v in entries.items()}
                  for puzzle, entries in data['tables'].items()}
        symmetries = {}
        for puzzle, entries in data['symmetries'].items():
            symmetries[puzzle] = []
            for perm, face_map in entries:
                undo = tuple(face_map.index(i) for i in range(len(face_map)))
                symmetries[puzzle].append((perm, bytes(face_map), undo))
        return tables, symmetries
    except (OSError, ValueError, KeyError, TypeError, zlib.error):
        return {}, {}


def cube3_key(facelets):
    centers = {facelets[face][1][1]: i for i, face in enumerate(FACES)}
    if len(centers) != 6:
        raise ValueError('Six distinct centers are required')
    return bytes(centers[c] for face in FACES for row in facelets[face] for c in row)


def _key(puzzle, cube):
    if puzzle == '3x3':
        return cube3_key(cube.facelets)
    if puzzle == 'SQ1':
        return bytes(cube.slots) + bytes((cube.middle,))
    return bytes(cube.colors)


def _decode(puzzle, encoded):
    if puzzle == '3x3':
        return tuple(encoded.split())
    if puzzle == 'SQ1':
        from cube.square1 import Square1Move
        return tuple(Square1Move(*m) for m in encoded)
    from cube.polyhedral import Move
    return tuple(Move(*m) for m in encoded)


@lru_cache(maxsize=3)
def _alignments(puzzle):
    """Pullback permutations for top alignment in the canonical formula grip."""
    if puzzle == 'SQ1':
        from cube.square1 import Square1Move
        result = []
        for a in range(12):
            for b in range(12):
                perm = tuple(range(a, 12)) + tuple(range(a)) + tuple(range(12 + b, 24)) + tuple(range(12, 12 + b)) + (24,)
                word = tuple(Square1Move(axis, amount) for axis, amount in ((0, a), (1, b)) if amount)
                result.append((perm, word))
        return tuple(result)
    elif puzzle == '3x3':
        from cube.facelet_model import FaceletCube
        labels = {f: [[i * 9 + r * 3 + c for c in range(3)] for r in range(3)] for i, f in enumerate(FACES)}
        result = [(tuple(range(54)), ())]
        for suffix in ('', '2', "'"):
            cube = FaceletCube(labels, 3)
            cube.apply_move('U' + suffix)
            result.append((tuple(v for f in FACES for row in cube.facelets[f] for v in row), ('U' + suffix,)))
        return tuple(result)
    else:
        from cube.polyhedral import Move, geometry
        g = geometry('megaminx', 3)
        result = [(tuple(range(len(g.stickers))), ())]
        for amount in range(1, 5):
            move = Move(0, 0, amount)
            pullback = [0] * len(g.stickers)
            for i, dest in enumerate(g.permutation(move)):
                pullback[dest] = i
            result.append((tuple(pullback), (move,)))
        return tuple(result)


def shorten(puzzle, cube, solution, cancel=None, budget=.3):
    """Replace an exactly matched suffix only when full replay solves the input.

    Length uses the same native move count as the existing solver. A failed
    lookup, exhausted budget or rejected candidate leaves its result intact.
    """
    original = tuple(solution)
    if len(original) < 2:
        return original
    tables, symmetries = _tables()
    table = tables.get(puzzle)
    if not table:
        return original
    deadline = monotonic() + max(0., budget)
    best = original
    work = cube.clone()
    prefix = []
    for at in range(len(original)):
        if cancel and cancel():
            raise InterruptedError()
        if monotonic() >= deadline or len(prefix) >= len(best) - 1:
            break
        state = _key(puzzle, work)
        frames = symmetries.get(puzzle, [(range(len(state)), bytes(range(16)), tuple(range(16)))])
        for perm, face_map, undo in frames:
            if monotonic() >= deadline:
                break
            rotated = bytes(face_map[state[i]] for i in perm)
            for alignment, setup in _alignments(puzzle):
                if len(prefix) + len(setup) >= len(best):
                    continue
                aligned = bytes(rotated[i] for i in alignment)
                encoded = table.get(aligned)
                if encoded is None:
                    continue
                tail = setup + _decode(puzzle, encoded)
                if puzzle == '3x3':
                    tail = tuple(FACES[undo[FACES.index(m[0])]] + m[1:] for m in tail)
                elif puzzle == 'Megaminx':
                    from cube.polyhedral import Move
                    tail = tuple(Move(undo[m.axis], m.layer, m.amount) for m in tail)
                candidate = tuple(prefix) + tail
                if len(candidate) >= len(best):
                    continue
                replay = cube.clone()
                try:
                    for move in candidate:
                        replay.apply_move(move)
                except ValueError:
                    continue
                if replay.is_solved():
                    best = candidate
        work.apply_move(original[at])
        prefix.append(original[at])
    return best


def shorten_3x3(facelets, solution):
    from cube.facelet_model import FaceletCube
    return list(shorten('3x3', FaceletCube(facelets, 3), solution, budget=.15))
