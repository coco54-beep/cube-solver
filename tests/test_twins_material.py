"""Retained planar base regression; public Twins uses the Drawing3 model."""
from collections import Counter
import pytest
from cube.planar_twins_state import PlanarTwinsState as TwinsState,JUMBLE,SECOND
from cube.polyhedral import Move,key
from cube.crazy_comet import volume


def test_every_material_piece_is_closed_and_has_positive_volume():
    c=TwinsState()
    assert len(c.solids)==166 and len(c.panels)==198
    assert Counter(f for h,f,p in c.panels)=={i:33 for i in range(6)}
    for faces in c.solids:
        assert volume(faces)>1e-11
        edges=Counter(tuple(sorted((key(a),key(b)))) for p,f in faces for a,b in zip(p,p[1:]+p[:1]))
        assert set(edges.values())=={2}


@pytest.mark.parametrize('axis',range(20))
def test_all_twenty_axes_move_complete_material_and_reverse_without_paint_loss(axis):
    c=TwinsState();before=c.signature();angle=180 if axis<12 else 60
    assert c.can_apply(Move(axis,0,angle))
    selected=set(c.selection(axis));c.apply_move(Move(axis,0,angle))
    assert c.paints==TwinsState().paints
    assert all(c.frames[h]==TwinsState().frames[h] for h in range(len(c.solids)) if h not in selected)
    c.apply_move(Move(axis,0,-angle));assert c.signature()==before


@pytest.mark.parametrize('axis',range(20))
def test_regular_closed_moves_recover_exact_slot_permutations(axis):
    c=TwinsState();amount=180 if axis<12 else 120
    c.apply_move(Move(axis,0,amount));p=c.aligned_permutation()
    assert sorted(p)==list(range(198))
    for _ in range((2 if axis<12 else 3)-1):c.apply_move(Move(axis,0,amount))
    assert c.is_solved()


def test_blocked_axes_are_atomic_after_half_skewb_and_partial_edge_turns():
    for first in (Move(0,0,JUMBLE),Move(0,0,SECOND),Move(12,0,60)):
        c=TwinsState().apply_move(first)
        blocked=[m for m in c.moves() if not c.can_apply(m)]
        assert blocked
        before=c.signature()
        with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(blocked[0])
        assert c.signature()==before


def test_observation_reentry_has_own_identity_and_keeps_both_pose_and_paint():
    import json
    c=TwinsState().apply_move(Move(12,0,60));c.paint(0,-1)
    data=json.loads(json.dumps(c.observation_data()))
    assert TwinsState.from_observation(data).signature()==c.signature()
    data['model']='crazy-comet-planar'
    with pytest.raises(ValueError):TwinsState.from_observation(data)
