"""Full God's-algorithm table for the two- and three-order pentahedrons."""
from pathlib import Path
import sys
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from solver.pentahedron_optimal import _DATA_DIR, structure, _weights


def build(n):
    gens, orbits = structure(n)
    weights = _weights(orbits)
    size = 1
    for _points, order, _trans, _coord in orbits:
        size *= order
    print('n=%d size=%d' % (n, size), flush=True)

    trans = [np.asarray(o[2], dtype=np.int64) for o in orbits]
    dist = np.full(size, 255, dtype=np.uint8)
    dist[0] = 0
    frontier = np.zeros(1, dtype=np.int64)
    depth = 0
    while frontier.size:
        depth += 1
        parts = [(frontier // weights[j]) % orbits[j][1] for j in range(len(orbits))]
        chunks = []
        for mi in range(len(gens)):
            nf = np.zeros(frontier.size, dtype=np.int64)
            for j in range(len(orbits)):
                nf += trans[j][mi][parts[j]] * weights[j]
            chunks.append(nf)
        nxt = np.unique(np.concatenate(chunks))
        nxt = nxt[dist[nxt] == 255]
        dist[nxt] = depth
        frontier = nxt
        print('  depth', depth, 'reached', int((dist != 255).sum()), flush=True)
    return dist.tobytes(), depth


def main():
    for n in (2, 3):
        data, depth = build(n)
        path = _DATA_DIR / f'pentahedron_{n}.bin'
        path.write_bytes(zlib.compress(data, 9))
        print('saved', path, path.stat().st_size, 'diameter', depth, flush=True)


if __name__ == '__main__':
    main()
