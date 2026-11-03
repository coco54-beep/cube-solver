"""Device smoke reports must refer to the page actually displayed by the manager."""
from types import SimpleNamespace
from kivy.uix.screenmanager import Screen,ScreenManager,NoTransition
from kivy.clock import Clock
from app.ui_self_check import UISelfCheck


def checker(monkeypatch,tmp_path,screenshot=False):
    scheduled=[]
    import app.ui_self_check as module
    monkeypatch.setattr(module,'Clock',SimpleNamespace(schedule_once=lambda callback,delay=0:scheduled.append(callback)))
    root=ScreenManager(transition=NoTransition())
    first=Screen(name='HomeScreen');second=Screen(name='InputScreen')
    root.add_widget(first);root.add_widget(second);events=[]
    second.bind(on_pre_enter=lambda *_:events.append('pre'),on_enter=lambda *_:events.append('enter'))
    app=SimpleNamespace(root=root)
    audit=UISelfCheck(app,str(tmp_path),screenshot=screenshot)
    audit._steps=[('InputScreen',lambda:None)]
    return audit,root,events,scheduled


def test_smoke_check_really_navigates_once_before_capture(monkeypatch,tmp_path):
    audit,root,events,scheduled=checker(monkeypatch,tmp_path)
    audit._next(0)
    Clock.tick();Clock.tick()
    assert root.current=='InputScreen' and events==['pre','enter']
    audit._shot(0)
    assert audit.report[0]['status']=='ok' and audit.report[0]['current_screen']=='InputScreen'


def test_wrong_visible_page_cannot_be_reported_as_success(monkeypatch,tmp_path):
    audit,root,events,scheduled=checker(monkeypatch,tmp_path)
    audit._next(0);Clock.tick();Clock.tick();root.current='HomeScreen';Clock.tick();Clock.tick();audit._shot(0)
    assert audit.report[0]['status']=='error'


def test_missing_requested_screenshot_is_a_failure(monkeypatch,tmp_path):
    audit,root,events,scheduled=checker(monkeypatch,tmp_path,screenshot=True)
    monkeypatch.setattr(audit,'_capture',lambda name:None)
    audit._next(0);Clock.tick();Clock.tick();audit._shot(0)
    assert audit.report[0]['status']=='error'


def test_transition_must_finish_before_screenshot(monkeypatch,tmp_path):
    audit,root,events,scheduled=checker(monkeypatch,tmp_path,screenshot=True)
    captured=[];monkeypatch.setattr(audit,'_capture',lambda name:captured.append(name) or 'InputScreen.png')
    audit._next(0);Clock.tick();Clock.tick();root.transition.is_active=True;audit._shot(0)
    assert not captured and not audit.report
    root.transition.is_active=False;audit._shot(0)
    assert captured==['InputScreen'] and audit.report[0]['status']=='ok'


def test_repeated_models_get_separate_screenshot_names(monkeypatch,tmp_path):
    audit,root,events,scheduled=checker(monkeypatch,tmp_path,screenshot=True)
    audit.app.cube=SimpleNamespace(puzzle_kind='mixup_plus_334',n=3)
    audit._steps*=2;captured=[]
    monkeypatch.setattr(audit,'_capture',lambda name:captured.append(name) or name+'.png')
    audit._next(0);Clock.tick();Clock.tick();audit._shot(0)
    assert captured==['InputScreen-mixup_plus_334-3']


def test_device_runner_rejects_old_or_invisible_success_reports():
    from copy import deepcopy
    from tools.device_selfcheck import verified_report
    data=dict(schema=2,image_validation='visible_pixels_and_variance',status='pass',errors=0,checked=1,screenshots_requested=True,
        results=[dict(status='ok',screen='InputScreen',current_screen='InputScreen',shot='InputScreen.png')])
    assert verified_report(data)
    for change in (dict(schema=1),dict(checked=0),dict(screenshots_requested=False)):
        invalid=deepcopy(data);invalid.update(change);assert not verified_report(invalid)
    invalid=deepcopy(data);invalid['results'][0]['current_screen']='HomeScreen';assert not verified_report(invalid)
    invalid=deepcopy(data);invalid['results'][0]['shot']=None;assert not verified_report(invalid)
    invalid=deepcopy(data);invalid.pop('image_validation');assert not verified_report(invalid)


def test_black_capture_cannot_pass_image_validation(monkeypatch,tmp_path):
    import kivy.core.image
    audit,root,events,scheduled=checker(monkeypatch,tmp_path,screenshot=True)
    monkeypatch.setattr(root,'export_to_png',lambda path:__import__('pathlib').Path(path).write_bytes(b'fixture'))
    monkeypatch.setattr(kivy.core.image,'Image',lambda *a,**kw:SimpleNamespace(texture=SimpleNamespace(pixels=b'\0\0\0\xff'*100)))
    audit._next(0);Clock.tick();Clock.tick();audit._shot(0)
    assert audit.report[0]['status']=='error' and 'almost entirely black' in audit.report[0]['shot']


def test_nonblank_root_capture_is_saved_and_accepted(monkeypatch,tmp_path):
    import kivy.core.image
    audit,root,events,scheduled=checker(monkeypatch,tmp_path,screenshot=True)
    calls=[]
    def save(path):calls.append(path);__import__('pathlib').Path(path).write_bytes(b'fixture')
    monkeypatch.setattr(root,'export_to_png',save)
    monkeypatch.setattr(kivy.core.image,'Image',lambda *a,**kw:SimpleNamespace(texture=SimpleNamespace(pixels=(b'\0\0\0\xff'+b'\xff\xff\xff\xff')*100)))
    audit._next(0);Clock.tick();Clock.tick();audit._shot(0)
    assert calls and audit.report[0]['status']=='ok' and audit.report[0]['shot']=='InputScreen.png'
