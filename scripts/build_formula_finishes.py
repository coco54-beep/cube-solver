"""Compile the curated formula catalog into a small native solver lookup."""
from base64 import b64encode
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.coordinates import FACE_NORMALS, WHOLE_CUBE
from cube.notation import parse_suffix, suffix_for_count
from cube.facelet_model import FaceletCube
from cube.polyhedral import PolyhedralPuzzle, Move, key, mean
from demo.formula_notation import compile_algorithm, FormulaRotation
from demo.algorithm_library import catalog, initial_hold
from solver.formula_finishes import FACES


def merge(word):
    result = []
    for token in word:
        count = parse_suffix(token[1:])
        if result and result[-1][0] == token[0]:
            count = (parse_suffix(result.pop()[1:]) + count) % 4
        if count:
            result.append(token[0] + suffix_for_count(count))
    return tuple(result)


def face_turns(algorithm):
    """Express standard wide/slice notation as fixed-grip outer turns."""
    expansions = {'M': "L' R x'", 'E': "D' U y'", 'S': "F' B z",
                  'r': 'x L', 'l': "x' R", 'u': 'y D', 'd': "y' U",
                  'f': 'z B', 'b': "z' F"}
    frame = dict(FACE_NORMALS)
    result = []
    for token in compile_algorithm('3x3', algorithm):
        face, count = token[0], parse_suffix(token[1:])
        atoms = expansions.get(face, face).split()
        for _ in range(count):
            for atom in atoms:
                label, power = atom[0], parse_suffix(atom[1:])
                if label in WHOLE_CUBE:
                    for _ in range(power):
                        frame = {f: WHOLE_CUBE[label](*n) for f, n in frame.items()}
                else:
                    original = next(f for f, normal in frame.items() if normal == FACE_NORMALS[label])
                    result.append(original + suffix_for_count(power))
    return merge(result)


def cube_symmetries():
    identity = tuple(FACE_NORMALS[f] for f in FACES)
    frames = [('', identity)]
    seen = {identity}
    for word, frame in frames:
        for axis, turn in WHOLE_CUBE.items():
            rotated = tuple(turn(*n) for n in frame)
            if rotated not in seen:
                seen.add(rotated)
                frames.append((word + axis, rotated))
    labels = {f: [[i * 9 + r * 3 + c for c in range(3)] for r in range(3)] for i, f in enumerate(FACES)}
    for word, frame in frames:
        cube = FaceletCube(labels, 3)
        for turn in word:
            cube.apply_move(turn)
        perm = tuple(v for f in FACES for row in cube.facelets[f] for v in row)
        face_map = tuple(next(i for i, f in enumerate(FACES) if FACE_NORMALS[f] == n) for n in frame)
        yield perm, face_map


def minx_symmetries(cube):
    from solver.polyhedral import _body_frames, _transform
    g = cube.geometry
    positions = {key(mean(s.polygon)): i for i, s in enumerate(g.stickers)}
    faces = {key(n): i for i, n in enumerate(g.spec.normals)}
    for frame in _body_frames('megaminx', 3):
        destinations = [positions[key(_transform(frame, mean(s.polygon)))] for s in g.stickers]
        pullback = [0] * len(destinations)
        for i, dest in enumerate(destinations):
            pullback[dest] = i
        yield tuple(pullback), tuple(faces[key(_transform(frame, n))] for n in g.spec.normals)


def build():
    tables = {p: {} for p in ('3x3', 'Megaminx', 'SQ1')}
    costs = {p: {} for p in tables}
    def store(puzzle, state, word):
        if not word:
            return
        if len(word) < costs[puzzle].get(state, 100000):
            costs[puzzle][state] = len(word)
            tables[puzzle][state] = ' '.join(word) if puzzle == '3x3' else word

    labels = {f: [[i * 9 + r * 3 + c for c in range(3)] for r in range(3)] for i, f in enumerate(FACES)}
    permutations = {}
    for f in FACES:
        for suffix in ('', '2', "'"):
            cube = FaceletCube(labels, 3)
            cube.apply_move(f + suffix)
            permutations[f + suffix] = tuple(v for face in FACES for row in cube.facelets[face] for v in row)
    csyms = tuple(cube_symmetries())
    minx = PolyhedralPuzzle('megaminx', 3)
    msyms = tuple(minx_symmetries(minx))
    solved3 = bytes(i // 9 for i in range(54))
    seen = {p: set() for p in tables}
    for group in catalog()['sets']:
        p = group['puzzle']
        if p not in tables:
            continue
        for case in group['cases']:
            if 'error' in case:
                continue
            for algorithm in case['algorithms']:
                if algorithm in seen[p]:
                    continue
                seen[p].add(algorithm)
                try:
                    if p == '3x3':
                        word = face_turns(algorithm)
                        if len(word) > 20:
                            continue
                        for amount in range(4):
                            extended = merge(word + (('U' + suffix_for_count(amount),) if amount else ()))
                            if len(extended) > 20:
                                continue
                            state = solved3
                            for token in reversed(extended):
                                inverse = token[0] + suffix_for_count(4 - parse_suffix(token[1:]))
                                state = bytes(state[i] for i in permutations[inverse])
                            store(p, state, extended)
                    elif p == 'Megaminx':
                        moves = compile_algorithm(p, initial_hold(p, algorithm)[1])
                        if any(isinstance(m, FormulaRotation) or getattr(m, 'layers', ()) for m in moves):
                            continue
                        for amount in range(5):
                            word = tuple(Move(m.axis, m.layer, m.amount) for m in moves)
                            if amount:
                                word += (Move(0, 0, amount),)
                            work = minx.clone()
                            for m in reversed(word):
                                work.apply_move(m.inverse(5))
                            store(p, bytes(work.colors), tuple((m.axis, m.layer, m.amount) for m in word))
                    else:
                        from cube.square1 import Square1Cube
                        moves = compile_algorithm(p, algorithm)
                        work = Square1Cube()
                        for m in reversed(moves):
                            work.apply_move(m.inverse())
                        store(p, bytes(work.slots) + bytes((work.middle,)), tuple((m.axis, m.amount) for m in moves))
                except ValueError:
                    # Unusable alternatives are excluded, even when another
                    # alternative made the source case usable for tutorials.
                    continue
    payload = {'version': 1, 'tables': {p: {b64encode(k).decode(): v for k, v in rows.items()} for p, rows in tables.items()},
               'symmetries': {'3x3': csyms, 'Megaminx': msyms}}
    destination = Path('solver/data/formula_finishes.bin')
    destination.write_bytes(zlib.compress(json.dumps(payload, separators=(',', ':')).encode(), 9))
    print({p: len(rows) for p, rows in tables.items()}, destination.stat().st_size, 'bytes')


if __name__ == '__main__':
    build()
