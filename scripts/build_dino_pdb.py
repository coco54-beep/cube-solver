"""Build the two six-piece pattern databases for the order-2 Dino Cube."""
import sys
import zlib
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits
from solver.dino import _rank, _size, _SUBSETS, _destinations, _moves


def build():
    cube = PolyhedralPuzzle("dino", 2)
    orbit = piece_orbits("dino", 2)[0]
    moves, order = _moves(cube)
    dests = _destinations(cube, orbit, moves)
    size = _size()
    blobs = []
    for subset in _SUBSETS:
        dist = bytearray([255]) * size
        start = tuple(subset)
        dist[_rank(start)] = 0
        queue = deque([start])
        visited = 1
        while queue:
            state = queue.popleft()
            depth = dist[_rank(state)]
            for dest in dests:
                nxt = tuple(dest[state[j]] for j in range(len(subset)))
                r = _rank(nxt)
                if dist[r] == 255:
                    dist[r] = depth + 1
                    queue.append(nxt)
                    visited += 1
        print("subset", subset, "reached", visited, "of", size, flush=True)
        blobs.append(bytes(dist))
    path = ROOT / "solver" / "data" / "dino_pdb.bin"
    path.write_bytes(zlib.compress(b"".join(blobs), 9))
    print("Saved", path, path.stat().st_size, "bytes", flush=True)


if __name__ == "__main__":
    build()
