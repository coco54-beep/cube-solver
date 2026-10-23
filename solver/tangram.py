"""History-independent Tangram algorithms with physical solution replay."""
from solver.articulated import _simplify_rigid


def _verify(cube, word, cancel, progress=None):
    work = cube.clone()
    def guard():
        if cancel and cancel():raise InterruptedError()
    for index,move in enumerate(word):
        guard()
        if progress and index%10==0:progress(index,len(word))
        try: work.apply_move(move,guard=guard)
        except ValueError: return False
    if progress:progress(len(word),len(word))
    return work.is_solved()


def solve_tangram(cube, cancel=None, progress=None):
    if cube.is_solved(): return ()
    period = cube.geometry.spec.turn_order
    if cube.history and cube.frames == cube._history_snapshot:
        word = tuple(m.inverse(period) for m in reversed(cube.history))
        if _verify(cube, word, cancel, progress):
            short = _simplify_rigid(cube, word)
            if len(short) < len(word) and _verify(cube, short, cancel): return short
            return word
    from solver.tangram_geometry import geometry
    from solver.tangram_table import load_table,compact
    model=geometry(cube.puzzle_kind)
    prefix=()
    work=cube.clone()
    if model.shape(work.frames)!=model.shape(model.cube.frames):
        prefix=model.restore_shape(work.frames,cancel,progress)
        frames=tuple(work.frames)
        for move in prefix:
            if cancel and cancel():raise InterruptedError()
            frames=model.apply(frames,move)
            if frames is None:raise ValueError('rigid.invalid')
        work.colors=frames
    table=load_table(cube.puzzle_kind)
    suffix=table.solve(work,cancel)
    word=compact(prefix+suffix)
    if _verify(cube,word,cancel,progress):return word
    raise ValueError('rigid.invalid')
