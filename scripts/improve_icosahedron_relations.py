"""Prepare a cheaper orientation basis from exact legal conjugates.

All candidates fix core piece positions. Coverage of the original orientation
space is checked algebraically before replacing a record; outer orbits are
still handled by the following reduction stages.
"""
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import Move, PolyhedralPuzzle
from solver.icosahedron import (PositionModel, core_points, orientation_units,
                               orientation_vector, independent_relation)
from solver.lattice_data import geometry_key
from solver.polyhedral import apply_word, compose, inverse, simplify
from solver.polyhedral_reduction import Transports
from solver.nxn_orbits import three_cycles


def short_position_relations(cube, record, atoms):
    """Close a face turn using existing short position cycles, offline."""
    model = PositionModel(cube)
    targets = model.targets()
    ids = {p: i for i, p in enumerate(model.originals)}
    transports = {}
    primitives = {}
    for index, orbit in targets.items():
        macro = record['position_cycles'][str(index)]
        primitives[index] = tuple(Move(*m) for m in macro['word'])
        base = tuple(ids[p] for p in macro['base'])
        transports[index] = Transports(model, orbit, base, both_directions=True)
    result = []
    identity = tuple(range(len(model.originals)))
    for atom in atoms:
        projected = model.geometry.permutation(atom)
        word = [atom]
        for index, orbit in targets.items():
            indexes = {home: i for i, home in enumerate(orbit)}
            destination = [None] * len(orbit)
            for home in orbit:
                destination[indexes[projected[home]]] = indexes[home]
            for cycle in three_cycles(destination):
                correction = transports[index].conjugate(
                    tuple(orbit[i] for i in cycle), primitives[index])
                projected = compose(projected, apply_word(model.geometry, correction))
                word.extend(correction)
        if projected != identity:
            raise ValueError('Position relation did not close every core piece')
        result.append(simplify(word, cube.geometry.spec.turn_order))
    return result


def improve(cube, record):
    g = cube.geometry
    if record['geometry'] != geometry_key(g):
        raise ValueError('Orientation assets do not match the geometry')
    points = core_points(cube)
    ids = {s: i for i, s in enumerate(points)}
    units = orientation_units(cube, points)
    atoms = tuple(Move(m.axis, m.layer, power * g.spec.step(m.axis))
                  for m in cube.moves() for power in range(1, g.spec.order(m.axis)))
    actions = []
    for atom in atoms:
        full = g.permutation(atom)
        p = tuple(ids[full[s]] for s in points)
        actions.append((atom, p, inverse(p)))
    extra = short_position_relations(cube, record, atoms)
    changed = False
    for prime in (5, 2):
        relations = record['relations'][str(prime)]
        candidates = {}

        def add(permutation, word):
            vectors = orientation_vector(permutation, units)
            if any(vectors[7 - prime]):
                raise ValueError('Orientation formula changed the other component')
            vector = vectors[prime]
            if not any(vector):
                return
            # Weight-1/2 flips span small conjugate orbits, so a basis that
            # uses them leaves the overcomplete conjugate set too sparse for
            # the runtime sparse solver. Keep the mod-2 basis to weight >= 4.
            if prime == 2 and sum(vector) < 4:
                return
            shorter = simplify(word, g.spec.turn_order)
            old = candidates.get(vector)
            if old is None or len(shorter) < len(old):
                candidates[vector] = shorter

        for relation in relations:
            word = tuple(Move(*m) for m in relation['word'])
            full = apply_word(g, word)
            p = tuple(ids[full[s]] for s in points)
            if orientation_vector(p, units)[prime] != tuple(relation['vector']):
                raise ValueError('Recorded orientation vector does not match its word')
            add(p, word)
            for atom, action, inv in actions:
                conjugate = compose(compose(inv, p), action)
                add(conjugate, (atom.inverse(g.spec.turn_order),) + word + (atom,))
        for word in extra:
            full = apply_word(g, word)
            p = tuple(ids[full[s]] for s in points)
            # Split mixed prime components using a power of the closed relation.
            power = 2 if prime == 5 else 5
            q = tuple(range(len(points)))
            for _ in range(power):
                q = compose(q, p)
            add(q, word * power)
        basis = {}
        chosen = []
        for vector, word in sorted(candidates.items(), key=lambda entry: len(entry[1])):
            if independent_relation(vector, basis, prime):
                chosen.append({'vector': list(vector),
                               'word': [[m.axis, m.layer, m.amount] for m in word]})
        original_basis = {}
        for relation in relations:
            independent_relation(relation['vector'], original_basis, prime)
        if len(basis) != len(original_basis):
            raise ValueError('Conjugate basis has an unexpected orientation rank')
        for relation in relations:
            if independent_relation(relation['vector'], dict(basis), prime):
                raise ValueError('Conjugate basis lost an original orientation')
        before = sum(len(r['word']) for r in relations)
        after = sum(len(r['word']) for r in chosen)
        print(f'icosahedron {cube.n}, mod {prime}: basis {before} -> {after}, '
              f'max {max((len(r["word"]) for r in relations), default=0)} -> '
              f'{max((len(r["word"]) for r in chosen), default=0)}', flush=True)
        if after < before:
            record['relations'][str(prime)] = chosen
            changed = True
    return changed


def main():
    path = ROOT / 'solver' / 'data' / 'icosahedron_core.bin'
    records = json.loads(zlib.decompress(path.read_bytes()))
    changed = False
    for order, record in records.items():
        changed = improve(PolyhedralPuzzle('icosahedron', int(order)), record) or changed
    if changed:
        temporary = path.with_suffix('.bin.tmp')
        temporary.write_bytes(zlib.compress(json.dumps(records, separators=(',', ':')).encode(), 9))
        temporary.replace(path)


if __name__ == '__main__':
    main()
