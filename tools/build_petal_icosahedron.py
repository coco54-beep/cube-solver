"""Prepare isolated petal and centre cycles for the tangent-circle icosahedron.

Geometry is analytic and has no desktop-only dependency. Run this builder
when the geometry changes; the phone loads the prepared short formula table.
"""
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives


def build(kind='petal_icosahedron'):
    cube = PolyhedralPuzzle(kind, 3)
    targets = {i: orbit for i, orbit in enumerate(piece_orbits(cube.puzzle_kind, 3))
               if len(orbit) > 1}
    prepared = primitives(cube, targets, use_prepared=False,
                          deep=kind in ('petal_icosahedron','petal_tetrahedron'))
    cycles = {str(i): dict(word=[(m.axis, m.layer, m.amount) for m in word], base=base)
              for i, (word, base) in prepared.items()}
    destination = Path(__file__).resolve().parents[1] / 'solver' / 'data' / (kind + '_cycles.bin')
    destination.write_bytes(zlib.compress(json.dumps(dict(
        geometry=geometry_key(cube.geometry), cycles=cycles),
        separators=(',', ':')).encode(), 9))
    print(f'{len(cycles)} isolated petal/centre three-cycles; {destination}')


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv)>1 else 'petal_icosahedron')
