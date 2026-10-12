"""Generate shortest next moves for every reachable Ivy colour state."""
from collections import deque, Counter
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cube.polyhedral import PolyhedralPuzzle
from solver.ivy import IvyStates, STATE_COUNT, UNREACHABLE, SOLVED
from solver.lattice_data import geometry_key


def build():
    model = IvyStates(PolyhedralPuzzle('ivy', 3).geometry)
    table = bytearray([UNREACHABLE]) * STATE_COUNT
    table[model.encode(model.goal)] = SOLVED
    queue = deque([(model.goal, 0)])
    depths = Counter({0: 1})
    while queue:
        state, depth = queue.popleft()
        for action, mapping in enumerate(model.maps):
            following = bytes(state[s] for s in mapping)
            code = model.encode(following)
            if table[code] != UNREACHABLE:
                continue
            table[code] = action ^ 1  # Undo the forward graph edge.
            queue.append((following, depth+1))
            depths[depth+1] += 1
    payload = b'IVY1' + bytes.fromhex(geometry_key(model.g)) + table
    path = ROOT / 'solver' / 'data' / 'ivy_moves.bin'
    temporary = path.with_suffix('.bin.tmp')
    temporary.write_bytes(zlib.compress(payload, 9))
    temporary.replace(path)
    print('Saved', path, 'reachable:', sum(depths.values()),
          'maximum distance:', max(depths), 'depths:', dict(depths), flush=True)


if __name__ == '__main__':
    build()
