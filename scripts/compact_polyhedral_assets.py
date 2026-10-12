"""Shorten prepared polyhedral algorithms while preserving required actions.

This rewrites words only: geometry fingerprints, cycle bases, stabilizer
permutations and orientation vectors stay unchanged. FTO replacements must
preserve the full sticker action. Icosamate core replacements preserve every
core sticker; outer sixty-piece orbits are solved afterwards by reduction.
"""
from array import array
from collections import deque
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import Move, PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import apply_word, compose, inverse_word, simplify


def short_words(cube, depth):
    """Offline radius-limited BFS on full sticker actions of the small FTO."""
    g = cube.geometry
    atoms = tuple(Move(m.axis, m.layer, power * g.spec.step(m.axis))
                  for m in cube.moves() for power in range(1, g.spec.order(m.axis)))
    actions = tuple(g.permutation(m) for m in atoms)
    identity = bytes(range(len(g.stickers)))
    paths = {identity: ()}
    queue = deque([identity])
    while queue:
        state = queue.popleft()
        path = paths[state]
        if len(path) == depth:
            continue
        for move, perm in zip(atoms, actions):
            nxt = bytes(map(perm.__getitem__, state))
            if nxt not in paths:
                paths[nxt] = path + (move,)
                queue.append(nxt)
    return paths, atoms, actions


def meet_word(geometry, word, database, depth):
    """Replace a long transversal with an equal full action within 2*depth."""
    paths, atoms, actions = database
    target = bytes(apply_word(geometry, word))
    if target in paths:
        return paths[target]
    frontier = [(target, ())]
    seen = {target}
    for level in range(depth):
        following = []
        for state, path in frontier:
            for move, perm in zip(atoms, actions):
                nxt = bytes(map(perm.__getitem__, state))
                if nxt in seen:
                    continue
                seen.add(nxt)
                tail = path + (move,)
                if nxt in paths:
                    return simplify(paths[nxt] + inverse_word(tail, geometry.spec.turn_order),
                                    geometry.spec.turn_order)
                if level + 1 < depth:
                    following.append((nxt, tail))
        frontier = following
    return word


def compact(geometry, word):
    original = apply_word(geometry, word)
    order = geometry.spec.turn_order
    word = simplify(word, order)
    size = len(geometry.stickers)
    encode = bytes if size <= 256 else lambda p: array('I', p).tobytes()
    while True:
        state = tuple(range(size))
        prefixes = [encode(state)]
        seen = {prefixes[0]: 0}
        result = []
        for move in word:
            state = compose(state, geometry.permutation(move))
            signature = encode(state)
            if signature in seen:
                end = seen[signature]
                for key in prefixes[end + 1:]:
                    del seen[key]
                del prefixes[end + 1:]
                del result[end:]
            else:
                result.append(move)
                prefixes.append(signature)
                seen[signature] = len(result)
        result = simplify(result, order)
        if len(result) == len(word):
            break
        word = result
    if apply_word(geometry, result) != original:
        raise ValueError('Compaction changed a prepared sticker action')
    return result


def words(record, core):
    if core == 'fto':
        for row in record['rows']:
            for permutation, word in row.values():
                yield word
    else:
        for value in record['position_cycles'].values():
            yield value['word']
        for relations in record['relations'].values():
            for value in relations:
                yield value['word']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--families', nargs='+', choices=('fto', 'icosahedron'),
                        default=['fto', 'icosahedron'])
    parser.add_argument('--fto-depth', type=int, choices=range(1, 7), default=5,
                        help='Offline meeting radius for order 2, at most six')
    args = parser.parse_args()
    for kind in args.families:
        path = ROOT / 'solver' / 'data' / (kind + '_core.bin')
        records = json.loads(zlib.decompress(path.read_bytes()))
        changed = False
        for order, record in records.items():
            cube = PolyhedralPuzzle(kind, int(order))
            geometry = cube.geometry
            if record['geometry'] != geometry_key(geometry):
                raise ValueError('Prepared assets do not match the current geometry')
            if kind == 'icosahedron':
                from solver.icosahedron import core_points
                points = core_points(cube)
                indexes = {s: i for i, s in enumerate(points)}

                def core_permutation(move):
                    full = cube.geometry.permutation(move)
                    return tuple(indexes[full[s]] for s in points)

                geometry = SimpleNamespace(spec=cube.geometry.spec, stickers=points,
                                           permutation=core_permutation)
            database = short_words(cube, args.fto_depth) if kind == 'fto' and order == '2' else None
            if database is not None:
                print(f'fto 2: prepared {len(database[0])} short full-sticker actions', flush=True)
            before = []
            after = []
            for encoded in words(record, kind):
                word = tuple(Move(*move) for move in encoded)
                shorter = compact(geometry, word)
                if database is not None and len(shorter) > 2 * args.fto_depth:
                    shorter = meet_word(geometry, shorter, database, args.fto_depth)
                    if apply_word(geometry, shorter) != apply_word(geometry, word):
                        raise ValueError('Short search changed a prepared full-sticker action')
                before.append(len(word))
                after.append(len(shorter))
                if len(shorter) < len(word):
                    encoded[:] = [[m.axis, m.layer, m.amount] for m in shorter]
                    changed = True
            print(f'{kind} {order}: stored total {sum(before)} -> {sum(after)}, '
                  f'longest {max(before)} -> {max(after)}', flush=True)
        if changed:
            payload = zlib.compress(json.dumps(records, separators=(',', ':')).encode(), 9)
            temporary = path.with_suffix('.bin.tmp')
            temporary.write_bytes(payload)
            temporary.replace(path)


if __name__ == '__main__':
    main()
