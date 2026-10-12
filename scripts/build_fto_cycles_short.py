"""Generate short FTO orbit 3-cycle macros with broad commutators.

Only rewrites fto_cycles.bin; the shared primitives() search is untouched.
"""
import json
import math
import sys
import zlib
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import Move, PolyhedralPuzzle
from solver.polyhedral import (piece_orbits, apply_word, inverse, inverse_word,
                               simplify, compose)
from solver.polyhedral_reduction import _outside_order, primitives
from solver.lattice_data import geometry_key


def piece_perm(g, p):
    return tuple(g.stickers[p[g.pieces[i][0]]].piece for i in range(len(g.pieces)))


def power(p, k):
    result = tuple(range(len(p)))
    for _ in range(k):
        result = compose(result, p)
    return result


def isolating_k(p, pp, orbit, target_stickers):
    seen = set()
    threes = 0
    kill = 1
    for start in orbit:
        if start in seen:
            continue
        length = 0
        j = start
        while j not in seen:
            seen.add(j)
            length += 1
            j = pp[j]
        if length == 3:
            threes += 1
        elif length > 1:
            kill = kill * length // math.gcd(kill, length)
    if threes != 1:
        return None
    seen = set(target_stickers)
    k = kill
    for i in range(len(p)):
        if i in seen:
            continue
        length = 0
        j = i
        while j not in seen:
            seen.add(j)
            length += 1
            j = p[j]
        if length > 1:
            k = k * length // math.gcd(k, length)
    if k % 3 == 0 or k > 120:
        return None
    return k


def find_macros(cube, targets, target_stickers, existing):
    g = cube.geometry
    order = g.spec.turn_order
    atoms = tuple(Move(m.axis, m.layer, power * g.spec.step(m.axis))
                  for m in cube.moves() for power in range(1, g.spec.order(m.axis)))
    perms = {m: g.permutation(m) for m in atoms}
    best = {i: (len(existing[str(i)]['word']),
                tuple(Move(*m) for m in existing[str(i)]['word']),
                tuple(existing[str(i)]['base'])) for i in targets}
    conjugators = []
    for length in (1, 2, 3):
        for word in product(atoms, repeat=length):
            if len(simplify(word, order)) != length:
                continue
            permutation = apply_word(g, word)
            conjugators.append((word, permutation, inverse(permutation)))
    for A in atoms:
        pA = perms[A]
        invA = inverse(pA)
        for B, pB, invB in conjugators:
            p = compose(compose(compose(pA, pB), invA), invB)
            pp = piece_perm(g, p)
            for index, orbit in targets.items():
                ts = target_stickers[index]
                moved = [i for i in orbit if pp[i] != i]
                k = None
                if len(moved) == 3 and all(pp[i] in moved for i in moved):
                    o = _outside_order(p, ts, 3)
                    if o:
                        k = o
                if k is None:
                    k = isolating_k(p, pp, orbit, ts)
                if k is None:
                    continue
                word = simplify(((A,) + B + (A.inverse(order),) + inverse_word(B, order)) * k, order)
                if len(word) >= best[index][0]:
                    continue
                powered = power(p, k)
                pk = piece_perm(g, powered)
                trip = [i for i in orbit if pk[i] != i]
                if len(trip) != 3:
                    continue
                a, b = trip[0], pk[trip[0]]
                c = pk[b]
                if pk[c] != a:
                    continue
                if any(powered[i] != i for i in range(len(powered)) if i not in ts):
                    raise ValueError('Cycle did not isolate its sticker orbit')
                if power(powered, 3) != tuple(range(len(powered))):
                    continue
                if len(word) < best[index][0]:
                    best[index] = (len(word), word, (a, b, c))
                    print('  improved orbit', index, 'to', len(word), flush=True)
    # A nested commutator can cancel side effects without repeating the
    # original commutator five times. Enumerate short, deduplicated actions.
    commutators = {}
    for a in atoms:
        for b in atoms:
            word = simplify((a, b, a.inverse(order), b.inverse(order)), order)
            if not word:
                continue
            permutation = apply_word(g, word)
            old = commutators.get(permutation)
            if old is None or len(word) < len(old):
                commutators[permutation] = word
    entries = [(p, inverse(p), w) for p, w in commutators.items()]
    for p, ip, pw in entries:
        for q, iq, qw in entries:
            action = compose(compose(compose(p, q), ip), iq)
            pp = piece_perm(g, action)
            base_word = pw + qw + inverse_word(pw, order) + inverse_word(qw, order)
            for index, orbit in targets.items():
                ts = target_stickers[index]
                k = isolating_k(action, pp, orbit, ts)
                if k is None:
                    continue
                word = simplify(base_word * k, order)
                if len(word) >= best[index][0]:
                    continue
                powered = power(action, k)
                pk = piece_perm(g, powered)
                moved = [i for i in orbit if pk[i] != i]
                if len(moved) != 3:
                    continue
                a = moved[0]
                b = pk[a]
                c = pk[b]
                if b not in moved or c not in moved or pk[c] != a:
                    continue
                if any(powered[i] != i for i in range(len(powered)) if i not in ts):
                    raise ValueError('Nested cycle did not isolate its orbit')
                if power(powered, 3) != tuple(range(len(powered))):
                    continue
                best[index] = (len(word), word, (a, b, c))
                print('  nested improved orbit', index, 'to', len(word), flush=True)
    return best


def build():
    path = ROOT / 'solver' / 'data' / 'fto_cycles.bin'
    records = json.loads(zlib.decompress(path.read_bytes()))
    order = 3
    cube = PolyhedralPuzzle('fto', order)
    g = cube.geometry
    orbits = piece_orbits('fto', order)
    targets = {i: o for i, o in enumerate(orbits)
               if len(o) > 6 and len(g.pieces[o[0]]) < 3}
    target_stickers = {i: {s for p in o for s in g.pieces[p]} for i, o in targets.items()}
    print('Searching FTO cycles', order, 'orbits', list(targets), flush=True)
    record = records[str(order)]
    if record['geometry'] != geometry_key(g):
        raise ValueError('Stored cycles do not match the model')
    best = find_macros(cube, targets, target_stickers, record['cycles'])
    # The shared deep commutator search (length-one and length-two inner words,
    # two-move outer words) reaches some centre orbits that the broad and
    # nested scans above do not; keep whichever macro is shorter per orbit.
    deep = primitives(cube, targets, use_prepared=False, deep=True)
    for i in targets:
        length, word, base = best[i]
        candidate = tuple(deep[i][0])
        if len(candidate) < length:
            best[i] = (len(candidate), candidate, tuple(deep[i][1]))
            print('  deep improved orbit', i, 'to', len(candidate), flush=True)
    cycles = {}
    for i, entry in best.items():
        if entry is None:
            raise SystemExit('No macro found for orbit %s order %s' % (i, order))
        length, word, base = entry
        cycles[str(i)] = {'word': [[m.axis, m.layer, m.amount] for m in word],
                          'base': list(base)}
        print('  orbit', i, 'len', length, flush=True)
    records[str(order)] = {'geometry': geometry_key(g), 'cycles': cycles}
    path.write_bytes(zlib.compress(json.dumps(records, separators=(',', ':')).encode('utf-8'), 9))
    print('Saved', path, path.stat().st_size, flush=True)


if __name__ == '__main__':
    build()
