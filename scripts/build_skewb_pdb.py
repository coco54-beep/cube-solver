"""Build the two coupled pattern databases for the order-3 Skewb."""
import sys
import zlib
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import PolyhedralPuzzle, Move
from solver.polyhedral import piece_orbits
from solver.skewb import _reachable_rank


def build():
    cube = PolyhedralPuzzle.solved("skewb", 3)
    g = cube.geometry
    order = g.spec.turn_order
    orbits = piece_orbits("skewb", 3)
    corner = tuple(s for o in orbits if len(g.pieces[o[0]]) == 3
                   for p in o for s in g.pieces[p])
    centre = tuple(s for o in orbits if len(g.pieces[o[0]]) == 1
                   for p in o for s in g.pieces[p])
    full = corner + centre
    loc = {s: i for i, s in enumerate(full)}
    moves = [Move(a, l, amt)
             for a in range(len(g.layers))
             for l in range(len(g.layers[a]))
             for amt in range(1, order)]
    dest = [tuple(loc[g.permutation(m)[s]] for s in full) for m in moves]
    n = len(full)
    a_idx = list(range(0, 12))
    b_idx = list(range(12, 24))
    c_idx = list(range(len(corner), n))
    rank_a = _reachable_rank(a_idx, dest)
    rank_b = _reachable_rank(b_idx, dest)
    rank_c = _reachable_rank(c_idx, dest)
    nc = len(rank_c)

    def joint(orbit_idx, rank_o):
        indices = orbit_idx + c_idx
        proj = {fp: j for j, fp in enumerate(indices)}
        k = len(indices)
        sub = [tuple(proj[dest[m][indices[p]]] for p in range(k)) for m in range(len(dest))]
        table = bytearray([255]) * (len(rank_o) * nc)
        start = tuple(range(k))
        table[rank_o[start[:12]] * nc + rank_c[tuple(v - 12 for v in start[12:])]] = 0
        queue = deque([start])
        count = 1
        while queue:
            state = queue.popleft()
            depth = table[rank_o[state[:12]] * nc + rank_c[tuple(v - 12 for v in state[12:])]]
            for d in sub:
                nxt = tuple(d[v] for v in state)
                idx = rank_o[nxt[:12]] * nc + rank_c[tuple(v - 12 for v in nxt[12:])]
                if table[idx] == 255:
                    table[idx] = depth + 1
                    queue.append(nxt)
                    count += 1
        print("joint", len(rank_o), "x", nc, "reached", count, "of", len(table), flush=True)
        return bytes(table)

    table_a = joint(a_idx, rank_a)
    table_b = joint(b_idx, rank_b)
    path = ROOT / "solver" / "data" / "skewb_pdb.bin"
    path.write_bytes(zlib.compress(table_a + table_b, 9))
    print("Saved", path, path.stat().st_size, "bytes", flush=True)


if __name__ == "__main__":
    build()
