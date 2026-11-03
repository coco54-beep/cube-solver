"""Speed, chapter ownership, specific actions and honest export estimates."""
import pytest
from tests.test_course_media import player
from demo.course import load
from demo.solutions import state_signature


@pytest.mark.parametrize('mode',(3,('i_cube',3)))
def test_speed_changes_animation_duration_without_changing_action(player,monkeypatch,mode):
    player.enter_case(mode,0,0,load(*mode) if isinstance(mode,tuple) else None);before=state_signature(player._work)
    player.set_speed(2);assert player._playback_speed==2
    captured=[];player._follow=lambda target,begin:begin()
    if isinstance(player._moves[0],str):
        monkeypatch.setattr(player.view,'start_turn',lambda axis,pos,angle,duration,**kw:captured.append(duration))
    else:monkeypatch.setattr(player.view,'animate_move',lambda move,**kw:captured.append(kw['duration']))
    player._start_move(player._moves[0],1)
    assert captured and all(0<d<=.5 for d in captured)
    from app.i18n import tr
    assert player.lbl_progress.text.startswith(tr('demo.progress',i=1,total=len(player._moves),move='').split('·')[0].strip())
    player._stop();assert state_signature(player._work)==before


def test_old_chapter_buttons_cannot_seek_after_case_replaced(player):
    player.enter_case(('master_brilic',3),0,0,load('master_brilic',3))
    popup=player.open_chapters();buttons=popup.content.children[0].children
    selected=buttons[0]
    player.enter_case(('i_cube',3),0,0,load('i_cube',3));selected.dispatch('on_release')
    assert player._move_index==0 and player.mode==('i_cube',3)


def test_action_and_duration_derive_from_the_real_moves(player):
    from demo.media import action_description,action_duration,video_seconds,narration
    from cube.cube3 import Cube3
    cube=Cube3.solved()
    assert '180' in action_description(cube,'R2','R2')
    assert action_duration(cube,'R2',2)==.5
    case=dict(name='example',moves=('R','U2'),tip='Check the actual layer.')
    assert video_seconds(case,cube,2,False)<video_seconds(case,cube,1,False)
    part=dict(start=0,end=2,title='Example',text='Keep the grip.',check='Check the colours.')
    spoken=narration(case,part)
    assert 'R' in spoken and 'U2' in spoken


def test_eta_requires_real_samples_and_finishes_at_zero():
    from services.export_timing import remaining_seconds
    assert remaining_seconds(5,0,100) is None
    assert remaining_seconds(5,1,100) is None
    assert remaining_seconds(10,20,100)==40
    assert remaining_seconds(10,100,100)==0
    assert remaining_seconds(float('nan'),20,100) is None


def test_verified_course_cache_does_not_share_edits_between_players():
    from demo.course import _verified
    _verified.cache_clear()
    first=load('master_brilic',3);case=first[0]['cases'][0];signature=state_signature(case['initial'])
    case['initial'].apply_move(case['moves'][0]);case['narration_sections'][0]['title']='edited'
    again=load('master_brilic',3)[0]['cases'][0]
    assert state_signature(again['initial'])==signature
    assert again['narration_sections'][0]['title']!='edited'
    assert _verified.cache_info().hits>=1 and _verified.cache_info().maxsize==2


def test_export_last_animation_frame_keeps_the_action_that_was_rendered():
    from types import SimpleNamespace
    from threading import Event
    from queue import Queue
    from ui.demo_video import VideoExport
    player=SimpleNamespace(_busy=True,_move_index=0,_moves=['R'],
        lbl_action=SimpleNamespace(text='Current R'),lbl_progress=SimpleNamespace(text='Move 1/1 R'))
    job=VideoExport.__new__(VideoExport)
    job.player=player;job.cancelled=Event();job.frames=Queue(maxsize=3)
    job.ending=False;job.hold=True;job.part_index=0;job.start_index=0;job.frame_count=0
    job.prepared=[dict(part=dict(end=1,title='Chapter',text='Explanation'))]
    job.caption=SimpleNamespace(text='');job.progress=SimpleNamespace(text='')
    def complete():
        player._busy=False;player._move_index=1
        player.lbl_action.text='Next U';player.lbl_progress.text='Completed'
    job._tick_animation=complete
    job._capture=lambda **kw:b'pixels'
    job._pump_frame(0)
    assert job.caption.text=='Chapter\nCurrent R'
    assert job.progress.text=='Move 1/1 R'
