"""Prepare exact, independent petal cycles for the Flower Dodecahedron."""
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.polyhedral_reduction import primitives
from solver.lattice_data import geometry_key


def build():
    cube = PolyhedralPuzzle('blossom', 3)
    orbits = piece_orbits('blossom', 3)
    targets = {i: orbit for i, orbit in enumerate(orbits) if len(orbit) > 1}
    cycles = primitives(cube, targets, use_prepared=False)
    record = {'geometry': geometry_key(cube.geometry),
              'cycles': {str(i): {'word': [[m.axis, m.layer, m.amount] for m in word],
                                 'base': list(base)}
                         for i, (word, base) in cycles.items()}}
    path = ROOT / 'solver' / 'data' / 'blossom_cycles.bin'
    temporary = path.with_suffix('.bin.tmp')
    temporary.write_bytes(zlib.compress(json.dumps(record, separators=(',', ':')).encode(), 9))
    temporary.replace(path)
    print('Saved', path, 'cycles:', {i: len(word) for i, (word, _) in cycles.items()}, flush=True)


if __name__ == '__main__':
    build()
