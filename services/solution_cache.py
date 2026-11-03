"""Small verified cache for exact rigid-puzzle states, never scramble histories."""
from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from time import perf_counter

_entries=OrderedDict();_lock=Lock()
MAX_ENTRIES=4;MAX_MOVES=40000;MAX_ENTRY_MOVES=20000


def key(cube):
    if type(cube).__module__ not in ('cube.mixup','cube.articulated'):return None
    return (cube.puzzle_kind,id(cube.solids),id(cube.orientations),tuple(cube.frames))


def clear():
    with _lock:_entries.clear()


def replay(cube,moves,cancel):
    work=cube.clone()
    for move in moves:
        if cancel():raise InterruptedError()
        work.apply_move(move)
    return work.is_solved()


def lookup(cube,cancel):
    stamp=key(cube)
    if stamp is None:return None
    with _lock:
        entry=_entries.get(stamp)
        if entry is None:return None
        _entries.move_to_end(stamp);result=deepcopy(entry[1])
    started=perf_counter()
    if not replay(cube,result.moves,cancel):
        with _lock:_entries.pop(stamp,None)
        return None
    result.elapsed_ms=int((perf_counter()-started)*1000)
    return result


def remember(cube,result,cancel):
    stamp=key(cube)
    if stamp is None or not result.success or not result.moves or len(result.moves)>MAX_ENTRY_MOVES:return
    if not replay(cube,result.moves,cancel):return
    stored=deepcopy(result)
    with _lock:
        # Retain only the immutable model bases, not per-state render geometry.
        # Clones independently rebuild geometry while sharing these bases.
        _entries[stamp]=((cube.solids,cube.orientations),stored);_entries.move_to_end(stamp)
        while len(_entries)>MAX_ENTRIES or sum(len(e[1].moves) for e in _entries.values())>MAX_MOVES:
            _entries.popitem(last=False)
