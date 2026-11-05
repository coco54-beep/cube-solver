"""Recorded play recovery and observed-state repair for edge-turning models."""
from time import monotonic
from cube.polyhedral import Move
from solver.rigid_shape import normalize, solve_recorded_turns


def solve(cube,cancel=None,progress=None,seconds=60):
    if cube.puzzle_kind=='helicopter_14':
        from solver.helicopter_14 import solve as solve_fourteen
        return solve_fourteen(cube,cancel,progress,seconds)
    start=monotonic()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-start>=seconds:raise TimeoutError('copter.shape_unresolved')
    guard();prefix=()
    recorded = solve_recorded_turns(cube, guard)
    if recorded is not None:
        return recorded
    def checked_cancel():guard();return False
    try:fixed=cube.regular_colours()
    except ValueError as e:
        if str(e)!='copter.align_first':raise
        aligned,prefix=normalize(cube,checked_cancel,max(.001,seconds-(monotonic()-start)))
        fixed=aligned.regular_colours()
    if fixed.puzzle_kind=='helicopter':
        from solver.helicopter import solve_helicopter
        result=solve_helicopter(fixed,checked_cancel,progress)
    elif fixed.puzzle_kind=='clover':
        from solver.polyhedral import solve_polyhedral
        result=solve_polyhedral(fixed,checked_cancel,progress)
    elif fixed.puzzle_kind=='mf8_bauhinia_minx':
        from solver.rex_dodecahedron import solve as solve_rex
        result=solve_rex(fixed,checked_cancel,progress)
    else:
        from solver.expanded_polyhedra import solve_expanded
        result=solve_expanded(fixed,checked_cancel,progress)
    step=120 if fixed.puzzle_kind=='mf8_bauhinia_minx' else 180
    word=prefix+tuple(Move(m.axis,m.layer,m.amount*step) for m in result)
    work=cube.clone()
    for m in word:guard();work.apply_move(m,guard)
    if not work.is_solved():raise ValueError('rigid.invalid')
    return word
