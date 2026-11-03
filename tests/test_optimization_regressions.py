"""Checks for popup navigation, rendering reuse and safe session restoration."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


def test_popup_button_release_reaches_window_without_hanging():
    # Use a child process so a regression reports a timeout instead of freezing
    # the entire test runner, as the original Android order picker did.
    script='''
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from ui.widgets.buttons import UIButton
Button.on_touch_up=lambda self,touch: 'released'
button=UIButton()
popup=Popup(content=button)
popup.open(animation=False)
assert Window.parent is Window
assert button.on_touch_up(object())=='released'
popup.dismiss(animation=False)
print('POPUP_RELEASE_PASS')
'''
    env=dict(os.environ,KIVY_NO_ARGS='1')
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,
                          text=True,encoding='utf8',errors='replace',timeout=20,env=env,
                          cwd=Path(__file__).resolve().parents[1])
    assert result.returncode==0,result.stdout+result.stderr
    assert 'POPUP_RELEASE_PASS' in result.stdout


@pytest.mark.parametrize('bad_screens',[{'HomeScreen':[]},{'HomeScreen':None},
                                       {'HomeScreen':{'_cube':'not a puzzle'}}])
def test_bad_checkpoint_does_not_change_live_puzzle(tmp_path,bad_screens):
    from app.session import SessionStore,encode
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    original=Cube4.solved()
    manager=SimpleNamespace(current='HomeScreen',has_screen=lambda name:name=='HomeScreen')
    app=SimpleNamespace(root=manager,cube=original,n=4,user_data_dir=str(tmp_path))
    store=SessionStore(app)
    state={'version':1,'page':'HomeScreen','app':{'n':3,'cube':Cube3.solved()},
           'screens':bad_screens,'color_info':{}}
    store.path.write_text(json.dumps(encode(state)),encoding='utf8')
    store.restore()
    assert app.cube is original and app.n==4 and not store.restoring


def test_obsolete_page_migrates_to_home_without_discarding_valid_puzzle(monkeypatch,tmp_path):
    from app.session import SessionStore,encode
    from cube.cube3 import Cube3
    from kivy.clock import Clock
    screen=SimpleNamespace()
    manager=SimpleNamespace(current='HomeScreen',has_screen=lambda name:name=='HomeScreen',
                            get_screen=lambda name:screen,transition=SimpleNamespace(duration=0))
    app=SimpleNamespace(root=manager,cube=Cube3.solved(),n=3,user_data_dir=str(tmp_path))
    expected=Cube3.solved();expected.apply_move('R')
    state={'version':1,'page':'RemovedScreen','app':{'n':3,'cube':expected},
           'screens':{'RemovedScreen':{}},'color_info':{}}
    store=SessionStore(app);store.path.write_text(json.dumps(encode(state)),encoding='utf-8')
    monkeypatch.setattr(Clock,'schedule_once',lambda fn,dt:fn(dt))
    store.restore()
    assert manager.current=='HomeScreen' and not store.restoring
    from cube.conversion import cubies_to_facelets
    assert cubies_to_facelets(app.cube.cubies,3)==cubies_to_facelets(expected.cubies,3)


@pytest.mark.parametrize('bad_app,bad_colours',[
    ({'n':4},{}),({'cube':None},{}),({'n':'3'},{}),({},[])])
def test_bad_checkpoint_metadata_is_rejected_before_any_live_mutation(tmp_path,bad_app,bad_colours):
    from app.session import SessionStore,encode
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    original=Cube4.solved()
    manager=SimpleNamespace(current='HomeScreen',has_screen=lambda name:name=='HomeScreen')
    app=SimpleNamespace(root=manager,cube=original,n=4,user_data_dir=str(tmp_path))
    state={'version':1,'page':'HomeScreen','app':{'n':3,'cube':Cube3.solved(),**bad_app},
           'screens':{},'color_info':bad_colours}
    store=SessionStore(app);store.path.write_text(json.dumps(encode(state)),encoding='utf-8')
    store.restore()
    assert app.cube is original and app.n==4 and not store.restoring


@pytest.mark.parametrize('enabled',[True,False])
def test_android_selfcheck_uses_live_java_activity(monkeypatch,enabled):
    from app.ui_self_check import requested
    monkeypatch.delenv('CUBESOLVER_UI_SELFCHECK',raising=False)
    extras=SimpleNamespace(getBoolean=lambda key:enabled if key=='ui_selfcheck' else False)
    activity=SimpleNamespace(getIntent=lambda:SimpleNamespace(getExtras=lambda:extras))
    jnius=SimpleNamespace(autoclass=lambda name:SimpleNamespace(mActivity=activity))
    monkeypatch.setitem(sys.modules,'jnius',jnius)
    assert requested() is enabled


def test_mixup_camera_redraw_reuses_surfaces_and_edits_invalidate():
    from cube.mixup import MixupCube
    from cube.mixup_entry import MixupEntryDraft
    from renderer.mixup_entry_view import MixupEntryView
    draft=MixupEntryDraft.from_cube(MixupCube('mixup_plus_444'))
    view=SimpleNamespace(draft=None,candidate=None,_polygons=[])
    builds=[]
    def build(cube):
        builds.append(True)
        return MixupEntryView._build_surfaces(view,cube)
    view._build_surfaces=build
    MixupEntryView.set_draft(view,draft)
    surfaces=MixupEntryView._surfaces(view,None)
    assert MixupEntryView._surfaces(view,None) is surfaces
    assert len(builds)==1
    index=next(i for i,b in enumerate(draft.blocks) if b['cells'])
    cell=draft.blocks[index]['cells'][0]
    draft.paint(index,0,(cell['color']+1)%6)
    MixupEntryView.set_draft(view,draft,force=True)
    changed=MixupEntryView._surfaces(view,None)
    assert changed!=surfaces and len(builds)==2
    view.candidate=((index,0),cell['world'] or cell['guide'])
    assert MixupEntryView._surfaces(view,None)!=changed
    assert len(builds)==3
    MixupEntryView._surfaces(view,None)
    assert len(builds)==3


@pytest.mark.parametrize('status,errors,expected',[('pass',0,0),('fail',1,1)])
def test_device_check_requires_a_fresh_success_report(monkeypatch,tmp_path,status,errors,expected):
    from tools import device_selfcheck as check
    report={'status':status,'errors':errors,'checked':1,'schema':2,
            'image_validation':'visible_pixels_and_variance','screenshots_requested':True,
            'results':[{'screen':'HomeScreen','current_screen':'HomeScreen','shot':'HomeScreen.png',
                        'status':'ok' if not errors else 'error'}]}
    calls=[]
    def run(adb,*args,**kwargs):
        calls.append(args)
        stdout=('List of devices attached\nemulator-5554\tdevice\n' if args==('devices',)
                else json.dumps(report) if args[:2]==('shell','cat') else '')
        return SimpleNamespace(returncode=0,stdout=stdout,stderr='')
    monkeypatch.setattr(check,'_run',run)
    monkeypatch.setattr(check.time,'sleep',lambda _:None)
    assert check.main(['--adb','test-adb','--out',str(tmp_path)])==expected
    remove=next(i for i,args in enumerate(calls) if args[:3]==('shell','rm','-f'))
    start=next(i for i,args in enumerate(calls) if args[:3]==('shell','am','start'))
    assert remove<start
