"""Pentacle: verified history inverse or disc normalization and a state solver."""
from cube.polyhedral import CUBE, Move
from cube.appearance import transform_frame
from solver.articulated import _simplify_rigid


def _score(cube):
    """Lower is better: non-uniform faces plus cut-alignment misses."""
    sets={i:set() for i in range(6)}
    for index,(panel,color) in enumerate(zip(cube.panels,cube._paints)):
        if index in cube.hidden_panels:continue
        if color<0:
            return 1000
        normal=transform_frame(cube.frames[panel.home],CUBE[panel.face])
        face=max(range(6),key=lambda i:sum(normal[k]*CUBE[i][k] for k in range(3)))
        sets[face].add(color)
    return sum(max(0,len(colors)-1) for colors in sets.values())


def _verify(cube,word,cancel):
    replay=cube.clone()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        try:replay.apply_move(move)
        except ValueError:return False
    return replay.is_solved()


def _macros(cube,cancel,cache):
    """Return alignment-prefixed 90-degree core turns."""
    result=[]
    for axis in range(6):
        if cancel and cancel():raise InterruptedError()
        key=(cube.frames,axis)
        alignment=cache.get(key)
        if alignment is None:
            try:alignment=cube.alignment_moves(axis)
            except ValueError:alignment=False
            cache[key]=alignment
        # Empty alignment means the layer is already open. It still has
        # legal core turns; only a failed alignment should remove the axis.
        if alignment is False:
            continue
        for amount in (90,270):
            child=cube.clone()
            try:
                for move in alignment:child.apply_move(move)
                child.apply_move(Move(axis,1,amount))
            except ValueError:continue
            result.append((tuple(alignment)+(Move(axis,1,amount),),child))
    return result


def solve_pentacle(cube,cancel=None,progress=None):
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    period=cube.geometry.spec.turn_order
    if cube.history and cube.frames==cube._history_snapshot:
        word=tuple(m.inverse(period) for m in reversed(cube.history))
        if _verify(cube,word,cancel):
            short=_simplify_rigid(cube,word)
            if len(short)<len(word) and _verify(cube,short,cancel):
                return short
            return word
    from solver.pentacle_state import solve_pentacle_state
    return solve_pentacle_state(cube,cancel,progress)
