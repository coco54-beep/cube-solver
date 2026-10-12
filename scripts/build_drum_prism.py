"""Produce complete stabilizers and independent orbit cycles, not scrambles."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.drum_prism import core_points
from solver.lattice_data import geometry_key
from solver.polyhedral import StabilizerChain, piece_orbits, simplify, apply_word
from solver.polyhedral_reduction import primitives, _macro_cost
from scripts.compact_polyhedral_assets import compact


def build_cycles(cube, points, targets):
    """Prepared orbit macros, solved hardest first with the rest protected.

    A long isolating commutator becomes short once the solved core is protected
    and the still-unsolved orbits may be disturbed. The cycles are stored in the
    order the solver applies them, so each later macro was built to leave the
    already-solved orbits fixed.
    """
    g = cube.geometry
    orbits = piece_orbits(cube.puzzle_kind, cube.n)
    baseline = primitives(cube, targets, use_prepared=False, deep=True)
    if not any(len(baseline[i][0]) > 8 for i in baseline):
        return baseline
    order = sorted(targets, key=lambda i: (-len(baseline[i][0]), i))
    guarded = set(points)
    protected = {}
    for index in order:
        protected[index] = set(guarded)
        guarded.update(s for p in orbits[index] for s in g.pieces[p])
    ordered = {i: targets[i] for i in order}
    try:
        staged = primitives(cube, ordered, use_prepared=False, deep=True,
                            protected=protected)
    except ValueError:
        return baseline
    if _macro_cost(staged) < _macro_cost(baseline):
        return {i: staged[i] for i in order}
    return baseline


def build():
    records = {}
    for kind in ('war_drum', 'pentahedron'):
        for n in (2, 3, 4, 5):
            cube = PolyhedralPuzzle(kind, n)
            g = cube.geometry
            points = core_points(cube)
            point_index = {s: i for i, s in enumerate(points)}
            def core_permutation(move):
                full = g.permutation(move)
                return tuple(point_index[full[s]] for s in points)
            core = SimpleNamespace(spec=g.spec, stickers=points, permutation=core_permutation)
            chain = StabilizerChain(cube, points=points)
            rows = []
            for row in chain.trans:
                entries = {}
                for destination, (permutation, word) in row.items():
                    moves = simplify(word.flatten(g.spec.turn_order), g.spec.turn_order)
                    moves = compact(core, moves)
                    # A producer integrity guard prevents corrupt words shipping.
                    full = apply_word(g, moves)
                    if tuple(point_index[full[s]] for s in points) != permutation:
                        raise ValueError('Stabilizer asset word mismatch')
                    entries[str(destination)] = [list(permutation),
                        [[m.axis, m.layer, m.amount] for m in moves]]
                rows.append(entries)
            targets = {i: orbit for i, orbit in enumerate(piece_orbits(kind, n))
                       if kind == 'war_drum' and len(orbit) > 6
                       and len(g.pieces[orbit[0]]) < 3}
            if not targets:
                cycles = {}
            else:
                cycles = build_cycles(cube, points, targets)
            records[f'{kind}:{n}'] = {'geometry': geometry_key(g),
                'points': list(points), 'rows': rows,
                'cycles': {str(i): {'word': [[m.axis, m.layer, m.amount] for m in word],
                                    'base': list(base)}
                           for i, (word, base) in cycles.items()}}
            print('Prepared', kind, n, 'stickers', len(g.stickers), flush=True)
    path = ROOT / 'solver' / 'data' / 'drum_prism.bin'
    path.write_bytes(zlib.compress(json.dumps(records, separators=(',', ':')).encode(), 9))
    print('Saved', path, path.stat().st_size, flush=True)


if __name__ == '__main__':
    build()
