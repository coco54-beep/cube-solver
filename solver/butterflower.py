"""Solve radius-one Butterflower observations without scramble history."""
from cube.butterflower import ButterflowerCube
from cube.butterflower_aligned import AlignedButterflower,generators,source_key,expand,observed_colors
from solver.flower_copter import FlowerColourSolver

_profile=FlowerColourSolver(ButterflowerCube,AlignedButterflower,generators,source_key,expand,observed_colors,
                            'butterflower_colour_group.bin',complete_group=False)
validate=_profile.validate
solve_colours=_profile.solve_colours


class _VisibleObservation(ButterflowerCube):
    """Search visible shape only; certify the hidden completion afterwards."""
    def selection(self,axis,guard=None):
        from cube.butterflower import material_side
        from cube.butterflower_material import cuts
        from cube.curvy_copter import inverse_point
        selected=[];target=cuts()[axis];visible={h for h,f,p in self.panels}
        for home in visible:
            if guard:guard()
            centre=tuple(round(v,10) for v in inverse_point(self.frames[home],target.centre))
            side=material_side(home,centre,target.radius)
            if side==0:raise ValueError('rigid.blocked')
            if side>0:selected.append(home)
        if not selected:raise ValueError('rigid.blocked')
        return tuple(selected)


def prepare_observation(cube,cancel=None,seconds=30.):
    """Infer invisible material from the entered shell, without a move history.

    A visible-only repair is only a candidate. Starting from its closed shell,
    reverse every candidate move with ALL 101 regions present. Only a fully
    guarded replay matching the original visible frames certifies completion.
    The user's entered frames and paints remain untouched.
    """
    from time import monotonic
    from cube.appearance import IDENTITY_FRAME
    from cube.polyhedral import Move
    from solver.rigid_shape import normalize
    started=monotonic()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>=seconds:raise TimeoutError('copter.shape_unresolved')
    guard()
    try:cube.aligned_permutation();return cube.clone()
    except ValueError as exc:
        if str(exc)!='copter.align_first':raise
    visible={h for h,f,p in cube.panels}
    draft=_VisibleObservation(tuple(f if h in visible else IDENTITY_FRAME for h,f in enumerate(cube.frames)),cube.paints)
    aligned,prefix=normalize(draft,cancel,max(.001,seconds-(monotonic()-started)))
    completed=ButterflowerCube(aligned.frames,aligned.paints)
    completed.aligned_permutation()
    for move in reversed(prefix):guard();completed.apply_move(Move(move.axis,0,-move.amount),guard)
    for home in visible:
        if max(abs(a-b) for u,v in zip(completed.frames[home],cube.frames[home]) for a,b in zip(u,v))>1e-7:
            raise ValueError('copter.invalid_shape')
    return completed


def solve(cube,cancel=None,progress=None,seconds=60.):
    from time import monotonic
    started=monotonic()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>=seconds:raise TimeoutError('comet.timeout')
    guard()
    if any(c<0 for c in cube.paints):raise ValueError('Please enter every sticker')
    cube.validate_pose();prefix=()
    try:colours=observed_colors(cube)
    except ValueError as exc:
        if str(exc)!='copter.align_first':raise
        from solver.rigid_shape import normalize
        aligned,prefix=normalize(cube,cancel,max(.001,seconds-(monotonic()-started)))
        guard();colours=observed_colors(aligned)
    word=tuple(prefix)+expand(solve_colours(colours,cancel,progress,max(.001,seconds-(monotonic()-started))))
    replay=cube.clone()
    for move in word:guard();replay.apply_move(move,guard)
    if not replay.is_solved():raise ValueError('Butterflower material replay failed')
    return word
