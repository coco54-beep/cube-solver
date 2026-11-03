"""A spoken action gates its own motion; overlays follow actual physical bands."""
import math
import pytest
from tests.test_course_media import player


def test_step_voice_speaks_every_move_and_old_callbacks_cannot_start_it(player,monkeypatch):
    from services.speech import Narrator
    calls=[];started=[]
    monkeypatch.setattr(Narrator,'speak',lambda self,text,done,error:calls.append((text,done,error)))
    monkeypatch.setattr(player,'_start_move',lambda move,index:started.append((move,index)))
    player.enter_case(3,0,0)
    si,ci=next((si,ci) for si,s in enumerate(player._steps) for ci,c in enumerate(s['cases']) if len(c['moves'])>1)
    player.enter_case(3,si,ci);player.toggle_voice();player.toggle_voice()
    assert player._voice_enabled and player._voice_mode=='step'
    player.play();assert len(calls)==1 and not started
    assert player.lbl_action.text in calls[0][0]
    calls[0][1]();assert started==[(player._moves[0],1)]
    player._move_index=1;player._update_controls();player._advance()
    assert len(calls)==2 and len(started)==1
    player._stop();calls[1][1]();assert len(started)==1
    player.toggle_voice();assert not player._voice_enabled


def test_standard_guide_uses_the_same_axis_angle_and_layer_positions_as_animation():
    from renderer.move_guide import describe
    from renderer.turn import decompose_move
    from cube.cube4 import Cube4
    cube=Cube4.solved();step=decompose_move('r2',4)[0]
    axis,angle,selected,centre,radius=describe(cube,'r2')
    assert math.isclose(angle,math.radians(step.angle))
    assert selected=={p for p in cube.cubies if p[step.axis] in step.layers}
    assert len(selected)>len(describe(cube,'R')[2])


@pytest.mark.parametrize('kind',('mixup_333','mixup_plus_444','tangram_extreme'))
def test_rigid_guide_highlights_the_actual_band_without_mutating_it(kind):
    from cube.articulated_observation import new_cube
    from renderer.move_guide import describe
    cube=new_cube(kind);move=next(iter(cube.moves()));before=tuple(cube.frames)
    axis,angle,selected,centre,radius=describe(cube,move)
    assert selected==set(cube.geometry.layers[move.axis][move.layer])
    assert tuple(cube.frames)==before


def test_old_guides_are_removed_when_cases_change(player):
    player.enter_case(3,0,0);old=player.move_guide
    player.enter_case(3,0,1)
    assert old.parent is None and old.event is None
    assert player.move_guide is not old


def test_background_resume_restarts_only_the_guide_not_playback(player):
    player.enter_case(3,0,0);player.pause_media()
    assert player.move_guide.event is None and not player._playing
    player.resume_media()
    assert player.move_guide.event is not None and not player._playing and not player._narrating


@pytest.mark.parametrize('kind',('siamese_a','siamese_b'))
def test_siamese_guide_uses_the_selected_cores_real_origin(kind):
    from cube.polyhedral import PolyhedralPuzzle
    from cube.siamese import move_origin
    from renderer.move_guide import describe
    cube=PolyhedralPuzzle(kind,3)
    for move in cube.moves():assert describe(cube,move)[3]==move_origin(kind,move)
