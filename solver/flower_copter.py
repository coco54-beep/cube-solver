"""Repair the Flower shape, then solve observed colours with native replay."""
from cube.flower_copter import FlowerCopterCube
from cube.flower_copter_aligned import AlignedFlowerCopter,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver
from functools import lru_cache


class FlowerColourSolver(MaterialSolver):
    @lru_cache(maxsize=1)
    def local_patterns(self):
        from cube.flower_copter import frame_action,transform_mask
        from cube.appearance import ROTATIONS
        c=self.factory();g=self.aligned().geometry
        owners={m:h for h,m in enumerate(c.signatures)}
        result=[set() for _ in c.regions]
        slots={(h,f):i for i,(h,f,p) in enumerate(c.panels)}
        for home,mask in enumerate(c.signatures):
            for frame in ROTATIONS:
                axes,faces=frame_action(frame);destination=owners[transform_mask(mask,axes)]
                paint={slots[destination,faces[c.panels[i][1]]]:c.panels[i][1] for i in g.pieces[home]}
                result[destination].add(tuple(paint[i] for i in g.pieces[destination]))
        return tuple(map(frozenset,result))


_profile=FlowerColourSolver(FlowerCopterCube,AlignedFlowerCopter,generators,source_key,expand,observed_colors,
                        'flower_copter_colour_group.bin',complete_group=False)
ASSET=_profile.asset
validate=_profile.validate
solve_colours=_profile.solve_colours


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
    if not replay.is_solved():raise ValueError('Flower Copter physical replay failed')
    return word
