"""Shape restoration and state solve after fresh six-view matching."""
import pytest
from cube.cuboid import CuboidCube
from cube.cuboid_observation import SixViewDraft,project
from cube.polyhedral_scramble import scramble
from cube.polyhedral import Move
from solver.cuboid import solve_cuboid
from solver.cuboid442 import orientations,transition,MOVES,solver_data


@pytest.mark.parametrize('seed',range(8))
@pytest.mark.parametrize('length',(24,100))
def test_six_view_reentry_deep_states_solve(seed,length):
    source=CuboidCube.solved('cuboid_442');scramble(source,length,seed)
    if seed%2:source.apply_moves((Move(1,1,1),Move(4,1,3)))
    draft=SixViewDraft.from_cube(source);match=SixViewDraft('cuboid_442',draft.state()).match(seconds=10)
    assert match.status=='ok'
    cube=match.cube;assert cube.history is None
    visible=lambda c:tuple(tuple((color,depth) for color,owner,depth in view) for view in project(c,draft.model))
    before=visible(cube);assert before==visible(source)
    word=solve_cuboid(cube)
    assert cube.history is None and visible(cube)==before
    replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()


@pytest.mark.parametrize('seed',range(8))
def test_coupled_orientation_graph_matches_every_physical_move(seed):
    cube=CuboidCube.solved('cuboid_442');scramble(cube,40,seed)
    outer,inner=orientations(cube)
    for move in MOVES:
        predicted=transition(outer,inner,move)
        assert (predicted is not None)==cube.can_apply(move)
        if predicted is not None:
            work=cube.clone();work.apply_move(move);assert orientations(work)==predicted


def test_complete_orientation_component_and_root_fibre_bounds():
    header,parents,group,indices=solver_data()
    assert len(parents)==2187**2
    assert header['reachable']==len(parents)-parents.count(255)==2421009
    assert header['diameter']==11 and parents.count(254)==1
    assert group['order']==group['parity_bound']=='1321454146682880000'
    assert sorted(map(len,group['root_orbits']))==[8,8,8,8]


def test_cancel_does_not_apply_part_of_a_solution():
    source=CuboidCube.solved('cuboid_442');scramble(source,40,7);source.history=None
    before=source.frames,tuple(source.colors);calls=0
    def cancel():
        nonlocal calls
        calls+=1;return calls>20
    with pytest.raises(InterruptedError):solve_cuboid(source,cancel)
    assert (source.frames,tuple(source.colors))==before and source.history is None
