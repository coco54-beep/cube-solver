"""Bounded legal-move beam search for manual 3x3 bandaged states."""
from time import monotonic
from functools import lru_cache
from cube.coordinates import FACE_AXIS_SIGN, layer_values
from cube.notation import parse_move_full
from cube.colors import DEFAULT_COLORS
from cube.bandaged_cube import BandagedCube

_FACES = ('R', 'L', 'U', 'D', 'F', 'B')


def _key(cube):
    return tuple((p, c.home, tuple(sorted(c.stickers.items())))
                 for p, c in sorted(cube.cubies.items()))


def _score(cube):
    at_home = sum(1 for pos, piece in cube.cubies.items() if pos == piece.home)
    coloured = 0
    for piece in cube.cubies.values():
        for normal, color in piece.stickers.items():
            if color in DEFAULT_COLORS.values():
                coloured += 1
    return (26 - at_home, 54 - coloured)


def _moves(cube):
    result = []
    for face in _FACES:
        for suffix in ('', "'", '2'):
            move = face + suffix
            try:
                label, layers, count = parse_move_full(move)
                selected = set(layer_values(cube.n, label, layers=layers))
                axis, _ = FACE_AXIS_SIGN[label]
                if cube.can_turn(axis, selected):
                    result.append(move)
            except (ValueError, KeyError):
                continue
    return result


def solve_bandaged_search(cube, cancelled=None, seconds=8.0, width=180, max_depth=30):
    if cube.is_solved(): return []
    if cube.puzzle_kind=='two_bar_cube':
        from solver.twobar_table import solve as solve_two_bar
        try:
            return solve_two_bar(cube,cancelled,seconds=max(30.,seconds))
        except ValueError as exc:
            if str(exc)!='two_bar.table_missing': raise
    if cube.puzzle_kind=='bandaged_c':
        from solver.bandaged_table import solve as solve_table
        try:
            return solve_table(cube,'solver/data/bandaged_c_table.bin',cancelled,seconds=max(30.,seconds),target_depth=8)
        except ValueError as exc:
            if str(exc)!='bandaged.table_missing': raise
    deadline = monotonic() + seconds
    start = cube.clone(); start.history = []
    beam = [(_score(start), start, [])]
    seen = {_key(start)}
    for _depth in range(max_depth):
        if cancelled and cancelled(): raise InterruptedError()
        following = []
        for _value, state, path in beam:
            if monotonic() > deadline: break
            previous = path[-1][0].upper() if path else None
            for move in _moves(state):
                if move[0].upper() == previous: continue
                if cancelled and cancelled(): raise InterruptedError()
                child = state.clone(); child.history = []
                try: child.apply_move(move)
                except ValueError: continue
                key = _key(child)
                if key in seen: continue
                seen.add(key); word = path + [move]
                if child.is_solved(): return word
                following.append((_score(child), child, word))
        if not following: break
        following.sort(key=lambda item: item[0])
        beam = following[:width]
        if monotonic() > deadline: break
    raise ValueError('rigid.search_limit')


def _inverse(move):
    if move.endswith('2'): return move
    return move[:-1] if move.endswith("'") else move + "'"

def _fast_key(cube):
    import hashlib
    b=bytearray()
    for p in sorted(cube.cubies):
        c=cube.cubies[p]
        b.extend((c.home[0]+1,c.home[1]+1,c.home[2]+1))
        for normal in ((0,0,1),(0,0,-1),(0,1,0),(0,-1,0),(1,0,0),(-1,0,0)):
            color=c.stickers.get(normal)
            b.append(0 if color in (None,"") else ord(str(color)[0])&255)
    return bytes(b)

def _bidirectional(cube, cancelled, seconds, solved_depth, target_depth):
    """Meet in the middle using the exact legal cubie state."""
    from collections import deque
    start=BandagedCube.solved(cube.puzzle_kind);start.history=[]
    front={_fast_key(start):()}; q=deque([(start,())])
    for d in range(solved_depth):
        nxt=deque()
        while q:
            state,word=q.popleft()
            for move in _moves(state):
                if cancelled and cancelled():raise InterruptedError()
                child=state.clone();child.history=[]
                try:child.apply_move(move)
                except ValueError:continue
                key=_fast_key(child)
                if key in front:continue
                front[key]=word+(move,);nxt.append((child,word+(move,)))
        q=nxt
        if not q:break
    other={_fast_key(cube):()};q=deque([(cube,())])
    for d in range(target_depth):
        nxt=deque()
        while q:
            state,word=q.popleft()
            for move in _moves(state):
                if cancelled and cancelled():raise InterruptedError()
                child=state.clone();child.history=[]
                try:child.apply_move(move)
                except ValueError:continue
                key=_fast_key(child)
                if key in other:continue
                other[key]=word+(move,)
                if key in front:
                    return list(word+(move,))+[_inverse(m) for m in reversed(front[key])]
                nxt.append((child,word+(move,)))
        q=nxt
        if not q:break
    return None

