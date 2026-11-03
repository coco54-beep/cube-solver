"""Bounded shape suffixes on thoroughly mixed, regularly aligned material.

The regular API is retained for colour-table construction; play pages request
shape suffixes explicitly. Every actual turn goes through whole-solid gates.
No undo history or solution is attached to the resulting state.
"""
from time import monotonic
from cube.polyhedral import Move,dot
from cube.curvy_copter import JUMBLE


def deform(cube,rng,cancel,deadline):
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:raise TimeoutError('copter.scramble_timeout')
    # A corner 60-degree step and a partial edge turn both expose real plastic
    # and keep every rigid piece (including its other coloured faces) intact.
    first=Move(rng.randrange(len(cube.turn_axes)),0,60.)
    if first.axis<12:first=Move(first.axis,0,rng.choice((JUMBLE,-JUMBLE,180.-JUMBLE)))
    cube.apply_move(first,guard)
    # Try a second independent cut, with a strict candidate limit on phones.
    axes=list(range(len(cube.turn_axes)));rng.shuffle(axes)
    for axis in axes[:8]:
        if abs(dot(cube.turn_axes[axis],cube.turn_axes[first.axis]))>1-1e-8:continue
        guard();amount=rng.choice((JUMBLE,-JUMBLE)) if axis<12 else rng.choice((60.,-60.))
        move=Move(axis,0,amount)
        try:following=cube.proposed(move,guard)
        except ValueError:continue
        cube.frames=following;break
    # Warm the current state's exact gates in this cancellable background job;
    # returning to the play page must not calculate all 20 cuts on the UI thread.
    for axis in range(len(cube.turn_axes)):
        guard()
        try:cube.selection(axis,guard)
        except ValueError:pass
