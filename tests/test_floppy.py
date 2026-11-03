"""All 192 ordinary Floppy states, shortest answers and real input."""
from collections import deque
import pytest
from cube.cuboid import CuboidCube,layout
from cube.polyhedral import Move
from cube.polyhedral_scramble import scramble
from solver.cuboid import solve_cuboid


def test_all_192_states_have_shortest_half_turn_answers_and_fixed_exterior():
    root=CuboidCube.solved('floppy_133');queue=deque(((root,0),))
    seen={bytes(root.colors)};maximum=0
    while queue:
        cube,distance=queue.popleft();cube.history=None
        word=solve_cuboid(cube);assert len(word)==distance
        assert all(m.amount==2 and m.layer==0 for m in word)
        replay=cube.clone().apply_moves(word);assert replay.is_solved()
        assert not cube.can_change_shape
        for move in cube.moves():
            child=cube.clone().apply_move(move);key=bytes(child.colors)
            # All thin solids retain the same exterior throughout the graph.
            from cube.cuboid import transform
            from itertools import product
            assert all(abs(transform(f,p)[1])<=.5 for f,box in zip(child.frames,layout('floppy_133')[1])
                       for p in product(*box))
            if key not in seen:seen.add(key);queue.append((child,distance+1))
        maximum=max(maximum,distance)
    assert len(seen)==192 and maximum==8
    assert len(root.panels())==30


def test_ordinary_floppy_blocks_quarter_turns_while_super_floppy_keeps_them():
    cube=CuboidCube.solved('floppy_133')
    for axis in range(6):
        assert not cube.can_apply(Move(axis,0,1))
        assert not cube.can_apply(Move(axis,1,2))
    super_cube=CuboidCube.solved('cuboid_133')
    assert super_cube.can_apply(Move(1,0,1))
    assert super_cube.can_change_shape


@pytest.mark.parametrize('seed',range(8))
def test_manual_colour_only_input_has_no_scramble_history(seed):
    source=CuboidCube.solved('floppy_133');scramble(source,100,seed)
    cube=CuboidCube('floppy_133',list(source.colors))
    assert cube.history is None
    before=list(cube.colors);word=solve_cuboid(cube)
    assert cube.colors==before and cube.history is None
    cube.apply_moves(word);assert cube.is_solved()


def test_unreachable_colours_and_cancel_do_not_mutate_input():
    cube=CuboidCube.solved('floppy_133');a,b=cube.panels()[:2]
    # A single painted corner twist preserves counts but is not a Floppy state.
    slots=next(v for v in cube.geometry.pieces if len(v)>=3)
    values=[cube.colors[i] for i in slots]
    for i,c in zip(slots,values[1:]+values[:1]):cube.colors[i]=c
    before=list(cube.colors)
    with pytest.raises(ValueError):solve_cuboid(cube)
    assert cube.colors==before
    with pytest.raises(InterruptedError):solve_cuboid(cube,cancel=lambda:True)
