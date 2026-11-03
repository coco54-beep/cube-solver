"""Repair Drawing3 Twins shape, then solve colours with whole-solid replay."""
from cube.twins_state import TwinsState
from cube.twins_aligned import expand,observed_colors
from cube.twins_cad_reduced import ReducedTwins,AlignedReducedTwins,generators,source_key,compress,reduction
from solver.rigid_colours import MaterialSolver
from functools import lru_cache


class TwinsColourSolver(MaterialSolver):
    @lru_cache(maxsize=1)
    def local_patterns(self):
        from cube.twins_cad_material import frame_action,transform_group
        from cube.appearance import ROTATIONS
        c=ReducedTwins();g=self.aligned().geometry
        owners={m:h for h,m in enumerate(c.signatures)}
        result=[set() for _ in c.regions]
        slots={(h,f):i for i,(h,f,p) in enumerate(c.panels)}
        for home,mask in enumerate(c.signatures):
            for frame in ROTATIONS:
                action=frame_action(frame);faces=action[3];destination=owners[transform_group(mask,action)]
                paint={slots[destination,faces[c.panels[i][1]]]:c.panels[i][1] for i in g.pieces[home]}
                result[destination].add(tuple(paint[i] for i in g.pieces[destination]))
        return tuple(map(frozenset,result))


_profile=TwinsColourSolver(ReducedTwins,AlignedReducedTwins,generators,source_key,expand,observed_colors,
                        'twins_cad_colour_group.bin',complete_group=False)
ASSET=_profile.asset
prepared=_profile.prepared
local_patterns=_profile.local_patterns


def _reduced_call(colors,operation):
    from collections import Counter
    if len(colors)!=192:raise ValueError('rigid.invalid')
    if any(type(c) is not int or c not in range(6) for c in colors):raise ValueError('Please enter every sticker')
    if Counter(colors)!=Counter(f for h,f,p in TwinsState().panels):raise ValueError('The color counts do not match this puzzle')
    reduced=compress(colors)
    try:return operation(reduced)
    except ValueError as error:
        if hasattr(error,'locations'):
            slots=reduction()[0];error.locations=[dict(sticker=slots[p['sticker']]) for p in error.locations]
        raise


def validate(colors):return _reduced_call(tuple(colors),_profile.validate)


def solve_colours(colors,cancel=None,progress=None,seconds=30.):
    return _reduced_call(tuple(colors),lambda reduced:_profile.solve_colours(reduced,cancel,progress,seconds))


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
        colours=observed_colors(aligned)
    word=prefix+expand(solve_colours(colours,cancel,progress,max(.001,seconds-(monotonic()-started))))
    replay=cube.clone()
    for move in word:guard();replay.apply_move(move,guard)
    if not replay.is_solved():raise ValueError('Drawing3 Twins physical replay failed')
    return word
