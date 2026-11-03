"""Full course coverage, immutable replay, navigation and audio/video ownership."""
import os,wave
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from candidate_puzzles import REQUESTED
from demo.course import load,catalogue
from demo.solutions import state_signature


@pytest.mark.parametrize('entry',REQUESTED,ids=lambda e:e.kind)
def test_all_expanded_courses_replay_every_move_and_cover_every_section(entry):
    case=load(entry.kind,entry.n)[0]['cases'][0]
    initial=case['initial'];signature=state_signature(initial);work=initial.clone()
    parts=case['narration_sections'];last=0
    for part in parts:
        assert part['start']==last and part['end']>last and part['end']-last<=64
        for move in case['moves'][last:part['end']]:work.apply_move(move)
        last=part['end']
        assert part['text'] and part['check']
    assert last==len(case['moves']) and work.is_solved()
    assert state_signature(initial)==signature
    assert case['teaching_kind']=='full_worked_course'
    assert set(catalogue())=={e.kind for e in REQUESTED}


@pytest.fixture
def player(monkeypatch,tmp_path):
    from kivy.app import App
    from app.theme import Theme
    from ui.screens.demo_screen import DemoScreen
    app=SimpleNamespace(theme=Theme(),user_data_dir=str(tmp_path))
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=DemoScreen()
    yield screen
    screen._stop();screen._cancel_export()


def test_long_course_seek_pause_and_return_keep_complete_state(player):
    from demo.media import section_at
    course=load('master_brilic',3);case=course[0]['cases'][0]
    original=state_signature(case['initial']);player.enter_case(('master_brilic',3),0,0,course)
    assert len(player._moves)>2000
    for i in (64,128,64,2368,len(player._moves),0):
        player.seek(i)
        expected=case['initial'].clone()
        for move in case['moves'][:i]:expected.apply_move(move)
        assert state_signature(player._work)==state_signature(expected)
        assert len(player._checkpoints)<=16
    player.seek(len(player._moves));assert player._work.is_solved()
    player.change_section(-1)
    assert player._move_index==player._parts[-2]['start']
    assert state_signature(case['initial'])==original


def test_cancelled_narration_callback_cannot_resume_or_mutate_player(player,monkeypatch):
    from services.speech import Narrator
    callbacks=[]
    monkeypatch.setattr(Narrator,'speak',lambda self,text,done,error:callbacks.append((done,error)))
    course=load('l_cube',3);player.enter_case(('l_cube',3),0,0,course)
    player.toggle_voice();player.play();assert player._narrating and callbacks
    signature=state_signature(player._work);player._stop()
    callbacks[0][0]();callbacks[0][1]('late error')
    assert not player._playing and not player._narrating and player._move_index==0
    assert state_signature(player._work)==signature


def test_narration_finishes_then_starts_exactly_one_actual_move(player,monkeypatch):
    from services.speech import Narrator
    callbacks=[];moves=[]
    monkeypatch.setattr(Narrator,'speak',lambda self,text,done,error:callbacks.append(done))
    monkeypatch.setattr(player,'_start_move',lambda move,index:moves.append((move,index)))
    player.enter_case(('i_cube',3),0,0,load('i_cube',3));player.toggle_voice();player.play()
    assert moves==[]
    callbacks[0]();assert moves==[(player._moves[0],1)]


def test_pcm_pages_keep_voice_across_video_boundaries(tmp_path):
    from services.demo_video import AlignedAudio
    source=tmp_path/'speech.wav'
    pcm=np.concatenate((np.full(11025,1234,dtype='<i2'),np.full(11025,-2345,dtype='<i2')))
    with wave.open(str(source),'wb') as stream:
        stream.setparams((1,2,22050,0,'NONE','not compressed'));stream.writeframes(pcm.tobytes())
    output=tmp_path/'aligned.wav';audio=AlignedAudio(output,12)
    audio.append(6,source,0);audio.append(6,source,.5);audio.append(12);audio.close()
    with wave.open(str(output),'rb') as stream:
        assert stream.getnframes()==44100
        actual=np.frombuffer(stream.readframes(44100),dtype='<i2')
    assert np.all(actual[:11025]==1234) and np.all(actual[11025:22050]==-2345)
    assert np.all(actual[22050:]==0)


def test_video_cancel_does_not_remove_an_existing_export(player,tmp_path):
    from ui.demo_video import VideoExport
    case=load('i_cube',3);player.enter_case(('i_cube',3),0,0,case)
    job=VideoExport(player,None,False);player._export_job=job
    # Simulate an already completed movie from a different job.
    existing=job.output.parent/'existing.mp4';existing.write_bytes(b'keep')
    job.popup=SimpleNamespace(dismiss=lambda:None);job.cancel()
    assert job.cancelled.is_set() and player._export_job is None
    assert existing.read_bytes()==b'keep'
    job._finish(None)
    assert existing.read_bytes()==b'keep'


def test_android_sources_in_snapshot_and_tts_visibility_configuration():
    spec=Path('buildozer.spec').read_text(encoding='utf-8')
    script=Path('scripts/snapshot_apk.py').read_text(encoding='utf-8')
    assert 'android.add_src = android_src' in spec
    assert 'android.extra_manifest_xml = android_src/tts_queries.xml' in spec
    assert "'.java'" in script and "'.xml'" in script and "'android_src'" in script
    assert 'android.intent.action.TTS_SERVICE' in Path('android_src/tts_queries.xml').read_text()


def test_cancelled_voice_generation_does_not_publish_partial_cache(monkeypatch,tmp_path):
    from services.speech import SpeechEngine
    engine=SpeechEngine()
    def interrupted(text,path,cancel):
        Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(b'incomplete')
        raise InterruptedError()
    monkeypatch.setattr(engine,'render',interrupted)
    with pytest.raises(InterruptedError):engine.speak('Original course',tmp_path/'voices')
    assert list((tmp_path/'voices').iterdir())==[]


@pytest.mark.skipif(os.name!='nt',reason='Windows system sound ownership')
def test_old_voice_cleanup_does_not_stop_new_voice(monkeypatch):
    import winsound
    import services.speech as speech
    old=speech.SpeechEngine();new=speech.SpeechEngine();calls=[]
    monkeypatch.setattr(speech,'_sound_owner',new)
    monkeypatch.setattr(winsound,'PlaySound',lambda *args:calls.append(args))
    old.close();assert calls==[] and speech._sound_owner is new
    new.close();assert len(calls)==1 and speech._sound_owner is None


def test_silent_caption_timeline_is_readable_and_section_export_has_no_full_intro(tmp_path):
    from services.demo_video import prepare_narration
    case=dict(moves=('R',)*128,tip='fallback',narration_intro='DO NOT REPEAT INTRO')
    part=dict(start=64,end=128,title='第二段',text='这是本段的实际步骤。'*20,check='本段结束后检查。')
    class NoSpeech:
        def render(self,*args):raise AssertionError('Silent export requested speech')
    timeline=prepare_narration(case,[part],tmp_path,False,12,lambda:False,lambda *_:None,NoSpeech())
    assert 'DO NOT REPEAT INTRO' not in timeline[0]['text']
    assert timeline[0]['frames']/12>=len(timeline[0]['text'])/7
    assert timeline[0]['path'] is None


def test_caption_voice_language_supports_original_chinese_and_japanese():
    from demo.media import speech_language
    assert speech_language('这是原创课程。')=='zh-CN'
    assert speech_language('手順を確認してください。')=='ja-JP'
    assert speech_language('Check the next layer.')=='en-US'


def test_expanded_complete_button_loads_course_without_running_live_solver(player,monkeypatch):
    import time
    from kivy.clock import Clock
    from ui.screens.demo_menu import DemoMenuScreen
    menu=DemoMenuScreen();menu.mode=('master_brilic',3);opened=[]
    expected=load(*menu.mode)[0]['cases'][0]['moves']
    monkeypatch.setattr(menu,'_rebuild',lambda:None)
    monkeypatch.setattr(menu,'open_case',lambda si,ci,steps:opened.append(steps))
    monkeypatch.setattr(menu._service,'start',lambda *_:pytest.fail('Fixed course used a live search'))
    menu.start_complete_demo();deadline=time.monotonic()+5
    while not opened and time.monotonic()<deadline:Clock.tick();time.sleep(.005)
    assert len(opened)==1 and tuple(opened[0][0]['cases'][0]['moves'])==tuple(expected)
    assert expected and opened[0][0]['cases'][0]['narration_sections'][-1]['end']==len(expected)
    assert menu._job is None and menu._solve_popup is None


def test_cancelled_course_load_cannot_reopen_player(player,monkeypatch):
    import threading,time
    from kivy.clock import Clock
    from ui.screens.demo_menu import DemoMenuScreen
    import demo.course
    gate=threading.Event();done=threading.Event();opened=[]
    def delayed(*_):
        gate.wait(2);done.set();return [dict(cases=[])]
    monkeypatch.setattr(demo.course,'load',delayed)
    menu=DemoMenuScreen();menu.mode=('i_cube',3)
    monkeypatch.setattr(menu,'_rebuild',lambda:None)
    monkeypatch.setattr(menu,'open_case',lambda *args:opened.append(args))
    menu.start_complete_demo();menu._cancel_complete();gate.set();assert done.wait(2)
    for _ in range(3):Clock.tick();time.sleep(.01)
    assert opened==[] and menu._job is None and menu._solve_popup is None
