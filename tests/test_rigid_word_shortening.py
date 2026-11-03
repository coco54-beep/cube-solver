"""Dynamic shortcuts preserve physical identities as well as painted faces."""
import pytest
from solver.rigid_word import shorten_rigid_word,_key_function


@pytest.mark.parametrize('kind',('fused_cube','two_bar_cube','bandaged_c','bicube','ai_cube','burr_cube',
                               'cuboid_234','cuboid_446','cross_cube','camouflage_3'))
def test_rigid_loops_shorten_only_after_full_legal_replay(kind):
    if kind in ('fused_cube','two_bar_cube','bandaged_c','bicube','ai_cube','burr_cube'):
        from cube.bandaged_cube import BandagedCube
        from cube.ghost import inverse_move
        cube=BandagedCube.random_scramble(kind,30,20261101)
        word=tuple(cube.solution_from_history());cube.history=[]
        move=word[0];loop=(move,inverse_move(move))
    else:
        from cube.cuboid import CuboidCube
        from cube.polyhedral_scramble import scramble
        cube=CuboidCube.solved(kind);scramble(cube,30,20261101)
        from solver.polyhedral import inverse_word
        word=tuple(inverse_word(cube.history,4));cube.history=None
        move=word[0];loop=(move,move.inverse(4))
    key=_key_function(cube);before=key(cube);original=loop*20+word
    reduced=shorten_rigid_word(cube,original,budget=2)
    assert len(reduced)<len(original) and key(cube)==before
    replay=cube.clone()
    for move in reduced:replay.apply_move(move)
    assert replay.is_solved()
    assert shorten_rigid_word(cube,original,budget=0)==original
    with pytest.raises(InterruptedError):shorten_rigid_word(cube,original,lambda:True)
    assert key(cube)==before


@pytest.mark.parametrize('kind',('bicube','cross_cube','camouflage_3'))
def test_identical_paint_never_hides_different_rigid_layouts(kind):
    if kind=='bicube':
        from cube.bandaged_cube import BandagedCube
        from solver.rigid_word import _moves
        cube=BandagedCube.solved(kind)
        for cubie in cube.cubies.values():
            cubie.stickers={normal:'same' for normal in cubie.stickers}
        move=_moves(cube)[0]
    else:
        from cube.cuboid import CuboidCube
        cube=CuboidCube.solved(kind);cube.colors=[0]*len(cube.colors)
        move=cube.moves()[0]
    key=_key_function(cube);before=key(cube)
    changed=cube.clone();changed.apply_move(move)
    assert key(changed)!=before
