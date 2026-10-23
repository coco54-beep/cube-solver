"""No-history bandage reconstruction, legal search and physical replay."""
import pytest

from cube.bandaged_cube import BandagedCube
from cube.bandaged_entry import reconstruct,plates
from cube.conversion import cubies_to_facelets
from solver.bandaged_state import model,solve_fused,solve_bandaged_state
from solver.bandaged_cube import solve_bandaged_cube


def enter(source):
    result=reconstruct(source.puzzle_kind,cubies_to_facelets(source.cubies,source.n),
                       {(p.face,p.cells) for p in plates(source)})
    assert not result.history
    return result


@pytest.mark.parametrize('seed',range(8))
def test_fused_40_turn_visible_manual_state(seed):
    cube=enter(BandagedCube.random_scramble('fused_cube',40,seed))
    before=cubies_to_facelets(cube.cubies,cube.n)
    word=solve_bandaged_cube(cube)
    assert not cube.history and cubies_to_facelets(cube.cubies,cube.n)==before
    replay=cube.clone();replay.apply_moves(word)
    assert replay.is_solved()


@pytest.mark.parametrize('rotation',('x','y',"z'",'x2'))
def test_fused_manual_global_orientation(rotation):
    source=BandagedCube.random_scramble('fused_cube',50,17)
    source.apply_move(rotation);cube=enter(source)
    cube.apply_moves(solve_fused(cube))
    assert cube.is_solved()


@pytest.mark.parametrize('kind',('ai_cube','burr_cube'))
@pytest.mark.parametrize('seed,length',((20261023,24),(0,40),(1,40)))
def test_four_order_manual_state_solver(kind,seed,length):
    cube=enter(BandagedCube.random_scramble(kind,length,seed))
    word=solve_bandaged_cube(cube)
    assert not cube.history
    cube.apply_moves(word)
    assert cube.is_solved()


@pytest.mark.parametrize('kind',('fused_cube','ai_cube','burr_cube'))
def test_compact_model_agrees_with_each_physical_turn(kind):
    geometry=model(kind)
    for seed in range(3):
        cube=enter(BandagedCube.random_scramble(kind,30,seed))
        state=geometry.encode(cube)
        children={i:child for child,i in geometry.children(state)}
        for i,token in enumerate(geometry.moves):
            replay=cube.clone()
            try:replay.apply_move(token)
            except ValueError:
                assert i not in children
            else:
                encoded=geometry.encode(replay)
                if encoded!=state:assert children[i]==encoded
                else:assert i not in children


@pytest.mark.parametrize('kind',('fused_cube','ai_cube','burr_cube'))
def test_state_solver_cancellation_preserves_input(kind):
    cube=enter(BandagedCube.random_scramble(kind,24,20261023))
    before=cubies_to_facelets(cube.cubies,cube.n)
    with pytest.raises(InterruptedError):solve_bandaged_cube(cube,lambda:True)
    assert not cube.history and cubies_to_facelets(cube.cubies,cube.n)==before
