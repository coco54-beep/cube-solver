"""The physical fallback obeys full wide-layer legality and can be cancelled."""
import pytest
from time import monotonic
from cube.articulated import MIXUP_MODELS
from cube.mixup import MixupCube,MixupSliceMove
from cube.polyhedral import Move
from solver.mixup_complete import solve_complete,orientation_patterns
from solver.mixup_reduction import geometry


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_complete_fallback_solves_a_no_history_entry(kind):
    cube=MixupCube(kind);cube.apply_move(Move(0,0,2));cube.history=[]
    before=cube.frames;word=solve_complete(cube,cache_limit=1)
    assert cube.frames==before and not cube.history
    replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()


def test_public_solver_uses_physical_recovery_after_a_fast_search_limit(monkeypatch):
    import solver.mixup as module
    cube=MixupCube('mixup_333');cube.apply_move(Move(1,1,1));cube.history=[]
    def limited(*args,**kwargs):raise ValueError('mixup.shape_limit')
    monkeypatch.setattr(module,'_restore_shape',limited)
    result=module.solve_mixup(cube)
    assert result.success and not cube.history
    replay=cube.clone();replay.apply_moves(result.moves);assert replay.is_solved()


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_three_turn_mixed_state_reenters_from_visible_panels(kind):
    from cube.mixup_entry import MixupEntryDraft
    from cube.articulated_observation import ObservationDraft,match_observations
    source=MixupCube(kind);source.apply_move(Move(0,0,2));source.apply_move(Move(1,0,2))
    model=geometry(kind)
    child,move=next((ch,mv) for ch,mv in model.children(source.frames,model.describe(source.frames)[0],complete=True) if mv.amount==1)
    source.apply_move(move)
    state=MixupEntryDraft.from_cube(source).observations().state()
    assert 'frames' not in state and 'history' not in state
    matched=match_observations(ObservationDraft(kind,state),seconds=20.)
    assert matched.status=='matched'
    cube=matched.cube;before=cube.frames;assert not cube.history
    begun=monotonic();word=solve_complete(cube,cancel=lambda:monotonic()-begun>10.)
    assert cube.frames==before and not cube.history
    replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()


@pytest.mark.parametrize('message',('rigid.invalid','mixup.replay_failed'))
def test_invalid_or_failed_replay_does_not_enter_an_unbounded_search(monkeypatch,message):
    import solver.mixup as module
    def invalid(*args,**kwargs):raise ValueError(message)
    monkeypatch.setattr(module,'_restore_shape',invalid)
    with pytest.raises(ValueError,match=message):module.solve_mixup(MixupCube('mixup_333'))


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_complete_children_include_every_legal_wide_move(kind):
    model=geometry(kind);cube=MixupCube(kind);features=model.describe(cube.frames)[0]
    choices={move:frames for frames,move in model.children(cube.frames,features,complete=True)}
    for axis,layers in model.ranges:
        for amount in range(1,8):
            move=Move(axis,layers[0],amount) if len(layers)==1 else MixupSliceMove(axis,layers[0],amount,layers)
            try:actual=cube.proposed(move)
            except ValueError:assert move not in choices
            else:assert choices[move]==actual


def test_relaxed_orientation_estimates_change_by_at_most_one_for_any_single_piece_turn():
    model=geometry('mixup_333')
    for (mask,corner),distances in orientation_patterns().items():
        for pose,distance in enumerate(distances):
            if distance==255:continue
            for axis in range(3):
                for amount in range(1,8):
                    target=model.next_pose(axis,amount,pose)
                    if target is None or distances[target]==255:continue
                    assert abs(distance-distances[target])<=1


def test_cancel_preserves_original_input():
    cube=MixupCube('mixup_plus_444');cube.apply_move(Move(0,0,2));cube.history=[];before=cube.frames
    with pytest.raises(InterruptedError):solve_complete(cube,lambda:True)
    assert cube.frames==before and not cube.history
