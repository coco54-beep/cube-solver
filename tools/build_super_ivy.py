"""Build short, isolated Super Ivy cycles offline, never on the phone."""
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives


def build():
    cube = PolyhedralPuzzle.solved('super_ivy', 3)
    targets = dict(enumerate(piece_orbits('super_ivy', 3)))
    cycles = primitives(cube, targets, use_prepared=False, deep=True)
    orbits = piece_orbits('super_ivy', 3)
    order = sorted(range(len(orbits)), key=lambda i: (
        0 if len(cube.geometry.pieces[orbits[i][0]]) == 2 else
        1 if len(orbits[i]) == 6 else 2, i))
    guards = {}
    fixed = set()
    for i in order:
        guards[i] = set(fixed)
        fixed.update(s for p in orbits[i] for s in cube.geometry.pieces[p])
    staged = primitives(cube, dict(enumerate(orbits)), use_prepared=False,
                        deep=True, protected=guards)
    record = dict(geometry=geometry_key(cube.geometry), cycles={str(i): dict(
        word=[(m.axis, m.layer, m.amount) for m in word], base=base)
        for i, (word, base) in cycles.items()}, order=order,
        staged={str(i): dict(word=[(m.axis, m.layer, m.amount) for m in word], base=base)
                for i, (word, base) in staged.items()})
    path = Path(__file__).resolve().parents[1] / 'solver/data/super_ivy_cycles.bin'
    path.write_bytes(zlib.compress(json.dumps(record, separators=(',', ':')).encode(), 9))
    print({i: len(word) for i, (word, _) in cycles.items()})
    print('staged', {i: len(word) for i, (word, _) in staged.items()})


if __name__ == '__main__':
    build()
