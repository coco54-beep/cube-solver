"""Offline legal-state shells for small bandaged 3x3 presets."""
import gzip
import pickle
from collections import deque
from pathlib import Path
from time import monotonic

from cube.bandaged_cube import BandagedCube
from solver.bandaged_search import _moves
from solver.twobar_table import state_key, inverse, word_to

FORMAT = 1


def build(kind, path, depth):
    start = BandagedCube.solved(kind); start.history = []
    root = state_key(start); parents = {root: None}; frontier = [start]
    for _ in range(depth):
        following = []
        for state in frontier:
            key = state_key(state)
            for move in _moves(state):
                child = state.clone(); child.history = []
                try: child.apply_move(move)
                except ValueError: continue
                child_key = state_key(child)
                if child_key in parents: continue
                parents[child_key] = (key, move); following.append(child)
        frontier = following
        if not frontier: break
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    payload = pickle.dumps({'version': FORMAT, 'kind': kind, 'depth': depth,
                            'root': root, 'parents': parents}, protocol=4)
    path.write_bytes(gzip.compress(payload, compresslevel=6))
    return len(parents), path.stat().st_size


def load(path):
    with gzip.open(path, 'rb') as handle: data = pickle.load(handle)
    if data.get('version') != FORMAT: raise ValueError('bandaged.table_version')
    return data


def solve(cube, path, cancelled=None, seconds=30., target_depth=6):
    if cube.is_solved(): return []
    try: data = load(path)
    except (OSError, ValueError, pickle.UnpicklingError): raise ValueError('bandaged.table_missing')
    if data['kind'] != cube.puzzle_kind: raise ValueError('bandaged.table_mismatch')
    parents = data['parents']; deadline = monotonic() + seconds
    def verify(word):
        replay = cube.clone(); replay.history = []
        try: replay.apply_moves(word)
        except ValueError: return False
        return replay.is_solved()
    start = state_key(cube)
    if start in parents:
        word = [inverse(m) for m in reversed(word_to(parents, start))]
        if verify(word): return word
    q = deque([(cube, ())]); seen = {start}
    for _ in range(target_depth):
        if monotonic() > deadline: break
        nxt = deque()
        while q:
            state, path_word = q.popleft()
            for move in _moves(state):
                if cancelled and cancelled(): raise InterruptedError()
                child = state.clone(); child.history = []
                try: child.apply_move(move)
                except ValueError: continue
                key = state_key(child)
                if key in seen: continue
                seen.add(key); word = path_word + (move,)
                if key in parents:
                    tail = word_to(parents, key)
                    result = list(word) + [inverse(m) for m in reversed(tail)]
                    if verify(result): return result
                nxt.append((child, word))
        q = nxt
    raise ValueError('rigid.search_limit')
