"""Physical reduction, not scramble-history reversal."""
import json
from pathlib import Path
import random

import pytest

from cube.articulated import MIXUP_MODELS
from cube.mixup import MixupCube,MixupSliceMove
from cube.polyhedral import Move
from solver.mixup import align_centres,project_cube,translate_token
from solver.mixup_reduction import geometry


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_fast_engine_matches_real_legality_and_frames(kind):
    rng=random.Random(2201);cube=MixupCube(kind);model=geometry(kind)
    for sample in range(12):
        frames=tuple(cube.frames);features=model.describe(frames)[0];legal=[]
        for axis,layers in model.ranges:
            for amount in (1,2,4,6):
                move=MixupSliceMove(axis,layers[0],amount,layers) if len(layers)>1 else Move(axis,layers[0],amount)
                if (layers[0]==0 or layers[-1]==len(model.cuts[axis])) and amount%2:continue
                fast=model.apply(frames,features,move)
                try:real=cube.proposed(move)
                except ValueError:real=None
                assert (fast is None)==(real is None),(kind,sample,move)
                if real is not None:
                    assert fast[0]==real
                    legal.append(move)
        cube.apply_move(rng.choice(legal))


def test_adjacent_span_is_one_move_and_checkpoint_roundtrips():
    from app.session import encode,decode
    cube=MixupCube('mixup_334');move=MixupSliceMove(1,1,1,(1,2))
    cube.apply_move(move)
    restored=decode(encode(cube))
    assert restored.frames==cube.frames and restored.history==cube.history
    restored.apply_move(move.inverse(8))
    assert restored.is_solved()
    with pytest.raises(ValueError,match='rigid.blocked'):
        cube.proposed(MixupSliceMove(1,0,2,(0,2)))


def test_wide_and_whole_tokens_use_simultaneous_layers():
    cube=MixupCube('mixup_344')
    for token in ('r','u',"x'",'y2'):
        moves=translate_token(cube,token,3)
        assert len(moves)==1 and isinstance(moves[0],MixupSliceMove)
        cube.apply_move(moves[0]);cube.apply_move(moves[0].inverse(8))
        assert cube.is_solved()


def test_true_core_identity_can_fix_a_rectangular_centre_grid():
    cube=MixupCube('mixup_334')
    table=json.loads((Path(__file__).resolve().parents[1]/'assets/mixup_center_finish.json').read_text())
    mask,word=next((m,w) for m,w in table['words'].items() if int(m)&6)
    for token in word:cube.apply_moves(translate_token(cube,token,3))
    assert project_cube(cube).is_solved() and not cube.is_solved()
    assert align_centres(cube) and cube.is_solved()


@pytest.mark.parametrize('stage',('shape','layout'))
def test_reduction_cancels_without_mutating_source(stage):
    from solver.mixup_reduction import greedy_geometry,restore_layout
    cube=MixupCube('mixup_plus_334');cube.apply_move(Move(0,1,1));before=cube.frames
    function=greedy_geometry if stage=='shape' else restore_layout
    with pytest.raises(InterruptedError):function(cube,cancel=lambda:True)
    assert cube.frames==before


def test_centre_swap_is_not_a_spatially_rotated_3x3_handoff():
    from cube.colors import DEFAULT_COLORS
    from solver.mixup import FACES,valid_center_frame
    facelets={f:[[DEFAULT_COLORS[f]]*3 for _ in range(3)] for f in FACES}
    assert valid_center_frame(facelets)
    facelets['U'][1][1],facelets['D'][1][1]=facelets['D'][1][1],facelets['U'][1][1]
    assert not valid_center_frame(facelets)


@pytest.mark.parametrize('seed',('211021','211022'))
def test_history_free_334_observations_solve_even_when_centres_exchange(seed):
    from cube.articulated_observation import match_observations
    from cube.mixup_entry import MixupEntryDraft
    from solver.mixup import solve_mixup
    path=Path(__file__).resolve().parents[1]/'reports/input-audit/2026-10-21/mixup-manual-inputs'/('mixup_334-'+seed+'.json')
    cube=match_observations(MixupEntryDraft('mixup_334',json.loads(path.read_text())).observations()).cube
    assert not cube.history
    original=cube.frames;result=solve_mixup(cube)
    assert cube.frames==original
    cube.apply_moves(result.moves)
    assert result.success and cube.is_solved()


@pytest.mark.parametrize('kind,seed,directory',(
    ('mixup_plus_334','211022','2026-10-21/mixup-manual-inputs'),
    ('mixup_plus_344','211022','2026-10-21/mixup-manual-inputs'),
    ('mixup_plus_444','211021','2026-10-21/mixup-manual-inputs'),
    ('mixup_plus_444','221023','2026-10-22/fresh-manual-inputs'),
))
def test_plus_manual_regressions_need_no_scramble_path(kind,seed,directory):
    from cube.articulated_observation import match_observations
    from cube.mixup_entry import MixupEntryDraft
    from solver.mixup import solve_mixup
    path=Path(__file__).resolve().parents[1]/'reports/input-audit'/directory/(kind+'-'+seed+'.json')
    cube=match_observations(MixupEntryDraft(kind,json.loads(path.read_text())).observations()).cube
    assert not cube.history
    before=cube.frames;result=solve_mixup(cube)
    assert cube.frames==before
    cube.apply_moves(result.moves)
    assert result.success and cube.is_solved()
