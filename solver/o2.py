"""Exact observable-state O2 solving, independent of move history."""
from collections import deque
from cube.polyhedral import Move


def solve_o2(cube,cancel=None,progress=None):
    colors=tuple(cube.colors)
    if len(colors)!=12 or set(colors[:6])!=set(range(6)) or set(colors[6:])!=set(range(6)):
        raise ValueError('o2.invalid')
    goal=colors[:6]+colors[:6]
    queue=deque([(colors,())]);seen={colors}
    atoms=tuple(Move(axis,0,amount) for axis in range(3) for amount in (1,2,3))
    maps=tuple(cube.geometry.inverse_permutation(m) for m in atoms)
    while queue:
        if cancel and cancel():raise InterruptedError()
        state,word=queue.popleft()
        if state==goal:return word
        for move,mapping in zip(atoms,maps):
            target=tuple(map(state.__getitem__,mapping))
            if target not in seen:seen.add(target);queue.append((target,word+(move,)))
    raise ValueError('o2.orientation')
