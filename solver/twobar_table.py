"""Offline Two-Bar distance shell and shallow meet-in-the-middle solve."""
import gzip
import hashlib
import pickle
from collections import deque
from pathlib import Path
from time import monotonic

from cube.bandaged_cube import BandagedCube
from solver.bandaged_search import _moves

ROOT = Path(__file__).resolve().parent
TABLE = ROOT / 'data' / 'twobar_table.bin'
DEPTH = 8
FORMAT = 1


def state_key(cube):
    raw = bytearray()
    for pos in sorted(cube.cubies):
        piece = cube.cubies[pos]
        raw.extend((piece.home[0] + 1, piece.home[1] + 1, piece.home[2] + 1))
        for normal in ((0,0,1),(0,0,-1),(0,1,0),(0,-1,0),(1,0,0),(-1,0,0)):
            color = piece.stickers.get(normal)
            raw.append(0 if color in (None, '') else ord(str(color)[0]) & 255)
    return hashlib.blake2b(bytes(raw), digest_size=16).digest()


def inverse(move):
    if move.endswith('2'): return move
    return move[:-1] if move.endswith("'") else move + "'"


def build(path=TABLE, depth=DEPTH):
    start = BandagedCube.solved('two_bar_cube'); start.history = []
    root = state_key(start)
    parents = {root: None}
    frontier = [start]
    for level in range(depth):
        following = []
        for state in frontier:
            key = state_key(state)
            for move in _moves(state):
                child = state.clone(); child.history = []
                try: child.apply_move(move)
                except ValueError: continue
                child_key = state_key(child)
                if child_key in parents: continue
                parents[child_key] = (key, move)
                following.append(child)
        frontier = following
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = pickle.dumps({'version': FORMAT, 'kind': 'two_bar_cube', 'depth': depth,
                            'root': root, 'parents': parents}, protocol=4)
    path.write_bytes(gzip.compress(payload, compresslevel=6))
    return len(parents), path.stat().st_size


def load(path=TABLE):
    with gzip.open(path, 'rb') as handle:
        data = pickle.load(handle)
    if data.get('version') != FORMAT or data.get('kind') != 'two_bar_cube':
        raise ValueError('two_bar.table_version')
    return data


def word_to(parents, key):
    result = []
    while parents.get(key) is not None:
        parent, move = parents[key]
        result.append(move); key = parent
    return list(reversed(result))


def solve(cube, cancelled=None, seconds=20.0):
    if cube.is_solved(): return []
    try: data = load()
    except (OSError, ValueError, pickle.UnpicklingError):
        raise ValueError('two_bar.table_missing')
    parents = data['parents']
    deadline = monotonic() + seconds
    def verify(word):
        replay = cube.clone(); replay.history = []
        try: replay.apply_moves(word)
        except ValueError: return False
        return replay.is_solved()
    start = state_key(cube)
    if start in parents:
        word = word_to(parents, start)
        word = [inverse(m) for m in reversed(word)]
        if verify(word): return word
    frontier = deque([(cube, ())]); seen = {start}
    for _level in range(7):
        if monotonic() > deadline: break
        following = deque()
        while frontier:
            state, path = frontier.popleft()
            for move in _moves(state):
                if cancelled and cancelled(): raise InterruptedError()
                child = state.clone(); child.history = []
                try: child.apply_move(move)
                except ValueError: continue
                key = state_key(child)
                if key in seen: continue
                seen.add(key); word = path + (move,)
                if key in parents:
                    tail = word_to(parents, key)
                    result = list(word) + [inverse(m) for m in reversed(tail)]
                    if verify(result): return result
                following.append((child, word))
        frontier = following
    raise ValueError('rigid.search_limit')
