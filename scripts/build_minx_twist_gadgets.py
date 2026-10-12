"""Precompute the pure corner-twist gadgets for the megaminx orders."""
from pathlib import Path
import json
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.high_minx_reduction import build_twist_gadget


def main():
    data = {}
    for n in range(2, 14):
        cube = PolyhedralPuzzle('megaminx', n)
        orbits = piece_orbits('megaminx', n)
        corners = next((o for o in orbits if len(cube.geometry.pieces[o[0]]) == 3), None)
        if corners is None:
            continue
        gadget = build_twist_gadget(cube, corners)
        if gadget is None:
            print('n=%d no gadget' % n, flush=True)
            continue
        word, base, _vec = gadget
        data[str(n)] = {'word': [[m.axis, m.layer, m.amount] for m in word],
                        'base': list(base)}
        print('n=%d gadget len %d base %s' % (n, len(word), base), flush=True)
    path = ROOT / 'solver' / 'data' / 'minx_twist_gadgets.bin'
    path.write_bytes(zlib.compress(json.dumps(data, separators=(',', ':')).encode(), 9))
    print('saved', path, path.stat().st_size)


if __name__ == '__main__':
    main()
