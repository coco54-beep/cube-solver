"""Short prism solutions preserve complete actions and entered-state goals."""
import pytest

from cube.polyhedral import Move,PolyhedralPuzzle
from solver.polyhedral import apply_word,scramble
from solver.drum_prism import _colored_core,_record
from solver.pentahedron_high import _rules,shorten_pentahedron


@pytest.mark.parametrize('n',(4,5))
def test_every_short_rule_has_the_claimed_full_sticker_action(n):
    cube=PolyhedralPuzzle('pentahedron',n)
    rules,atoms=_rules(n)
    for permutation,word in rules.items():
        assert bytes(apply_word(cube.geometry,word))==permutation
        assert len(word)<=3
    for move in atoms.values():
        assert move.amount%cube.geometry.spec.step(move.axis)==0


@pytest.mark.parametrize('n',(4,5))
@pytest.mark.parametrize('seed',(0,7,13,29,54))
def test_shortening_replays_without_scramble_history_and_preserves_input(n,seed):
    cube=PolyhedralPuzzle('pentahedron',n)
    scramble(cube,60,seed)
    cube=cube.entered()
    before=tuple(cube.colors)
    original=_colored_core(cube,_record(cube),None,None)
    shorter=shorten_pentahedron(cube,original)
    assert len(shorter)<=len(original)
    assert tuple(cube.colors)==before
    replay=cube.entered()
    for move in shorter:replay.apply_move(move)
    assert replay.is_solved()


@pytest.mark.parametrize('n',(4,5))
def test_shortener_removes_a_redundant_inverse_excursion(n):
    cube=PolyhedralPuzzle('pentahedron',n)
    move=cube.moves()[0]
    word=[move,move.inverse(cube.geometry.spec.turn_order)]
    assert shorten_pentahedron(cube,word)==()


def test_shortener_propagates_cancellation():
    cube=PolyhedralPuzzle('pentahedron',4)
    with pytest.raises(InterruptedError):
        shorten_pentahedron(cube,[Move(0,0,3)],cancel=lambda:True)


def test_shortener_rejects_a_candidate_that_does_not_solve_the_entered_state():
    cube=PolyhedralPuzzle('pentahedron',4)
    move=cube.moves()[0]
    cube.apply_move(move)
    invalid=[Move(1,0,3),Move(1,0,3)]
    assert shorten_pentahedron(cube,invalid)==tuple(invalid)
