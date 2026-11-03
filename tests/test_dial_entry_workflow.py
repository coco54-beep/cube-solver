"""New models use the existing entry, twist, solve, playback and failure UI."""
from types import SimpleNamespace

import pytest

from tests.test_bandaged_manual_controls import pump,until
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager,Screen,NoTransition
from app.i18n import tr
from app.theme import Theme
from cube.polyhedral import PolyhedralPuzzle,solved_colors,dot
from services.solve_service import SolveService,_make_failure
from solver.result import SolveResult
from ui.screens.polyhedral_screen import PolyhedralScreen,PolyhedralPlaybackScreen,PolyhedralTwistScreen
from ui.screens.solving_screen import SolvingScreen


@pytest.fixture(params=[('time_machine',2),('bean_6',6),('bean_10',10),('skewb',3)])
def workflow(request,monkeypatch):
    kind,n=request.param;cube=PolyhedralPuzzle(kind,n);cube.colors=[-1]*len(cube.colors)
    app=SimpleNamespace(cube=cube,n=n,puzzle_kind=kind,theme=Theme(),simple_input=False,
                        polyhedral_solution=None,solve_result=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    manager=ScreenManager(transition=NoTransition());entry=PolyhedralScreen(name='PolyhedralScreen')
    manager.add_widget(entry)
    for cls,name in ((SolvingScreen,'SolvingScreen'),(PolyhedralPlaybackScreen,'PolyhedralPlaybackScreen'),
                     (PolyhedralTwistScreen,'PolyhedralTwistScreen'),(Screen,'HomeScreen')):
        manager.add_widget(cls(name=name))
    held=[];monkeypatch.setattr(SolveService,'start',lambda service,cube,**kw:held.append((cube,kw)))
    old_size=Window.size;Window.size=(390,844);Window.add_widget(manager)
    for _ in range(3):pump()
    yield app,manager,entry,manager.get_screen('SolvingScreen'),held
    manager.current='HomeScreen'
    for widget in list(Window.children):
        if isinstance(widget,Popup):widget.dismiss(animation=False)
    manager.get_screen('SolvingScreen')._invalidate();entry.reset_interaction()
    Window.remove_widget(manager);Window.size=old_size;pump()


def fill(entry):entry._cube.colors=list(solved_colors(entry._cube));entry._refresh()


def start(workflow):
    _,manager,entry,solving,held=workflow
    entry.entry_action_buttons['solve'].dispatch('on_release');pump()
    assert manager.current=='SolvingScreen' and solving._run is not None and held
    return solving._run


def no_failure_popup():
    assert not any(isinstance(w,Popup) and w._is_open for w in Window.children)


def test_same_actions_and_numbers_are_two_inline_rows(workflow):
    _,manager,entry,_,_=workflow
    assert entry.hint.text and entry.hint.opacity==0 and entry.hint.height==0
    assert set(entry.entry_action_buttons)=={'twist','random','clear','undo','target','solve'}
    assert len(entry.navigation.children)==3
    assert all(row.height==0 for row in (entry.palette2,*entry._extra_palette_rows)
               if not row.opacity)
    if entry._cube.puzzle_kind=='time_machine':
        number_rows=(entry.palette2,entry._extra_palette_rows[0])
        assert len(entry._number_buttons)==12
        for index,row in enumerate(number_rows):
            assert row.opacity and row.height>0 and not row.disabled
            assert list(reversed(row.children))==entry._number_buttons[index*6:(index+1)*6]
            assert all(button.width>=44 and button.height>=44 for button in row.children)
            assert len({round(button.y,1) for button in row.children})==1
        assert number_rows[0].y>number_rows[1].y
        before=list(entry._cube.colors)
        entry._number_buttons[7].dispatch('on_release');pump()
        assert entry._dial_number==7 and entry._number_buttons[7].active
        assert entry._cube.colors==before
        no_failure_popup()
        old=entry._number_buttons[3]
        manager.current='HomeScreen';pump();old.dispatch('on_release')
        assert entry._dial_number==7
    else:
        assert entry._extra_palette_rows[0].height==0


@pytest.mark.parametrize('simple',(False,True))
def test_action_style_and_order_follow_the_shared_input_mode(workflow,simple):
    app,_,entry,_,_=workflow
    app.simple_input=simple
    row=entry.entry_action_buttons['solve'].parent;row.reflow()
    if simple:
        assert list(reversed(row.children))==[entry.entry_action_buttons[k] for k in ('twist','random','clear','undo','solve')]
        assert entry.entry_action_buttons['target'].parent is None
        assert not hasattr(row,'more')
    else:
        assert list(reversed(row.children))==[entry.entry_action_buttons[k] for k in ('twist','random','clear','undo','target','solve')]
    for key,button in entry.entry_action_buttons.items():
        assert button.icon_name==key and not button.text


def test_incomplete_input_stays_inline_and_locates_the_actual_back_face(workflow):
    _,manager,entry,_,held=workflow
    fill(entry);cube=entry._cube
    slot=max(i for i,s in enumerate(cube.geometry.stickers) if s.face==5)
    cube.colors[slot]=-1;entry.solve();pump()
    assert manager.current==entry.name and not held
    assert entry._entry_notice['category']=='incomplete'
    assert entry._entry_notice['locations']==[dict(sticker=slot)]
    assert entry._entry_problem_actions.retry.disabled
    entry._entry_problem_actions.locate.dispatch('on_release');pump();entry.view._draw()
    assert entry._face==5 and entry.view.selected==slot
    normal=entry.view.observation_world().transform(*cube.geometry.spec.normals[5])
    assert dot(normal,entry.view._proj[0])>.98
    no_failure_popup()


def test_invalid_counts_are_localised_and_keep_the_input(workflow):
    _,manager,entry,_,held=workflow
    fill(entry);entry._cube.colors[0]=entry._cube.colors[-1];before=list(entry._cube.colors)
    entry.solve();pump()
    assert manager.current==entry.name and not held and entry._cube.colors==before
    assert entry._entry_notice['category']=='illegal'
    if entry._cube.puzzle_kind in ('time_machine','bean_6','bean_10'):
        assert entry._entry_notice['locations']
        assert 'The color counts' not in entry.status.text
    no_failure_popup()


@pytest.mark.parametrize('failure',('timeout','internal','cancelled'))
def test_common_solver_failure_cancel_retry_and_late_results(workflow,failure):
    _,manager,entry,solving,held=workflow
    fill(entry);before=list(entry._cube.colors);run=start(workflow)
    assert not entry.entry_can_edit() and not solving.cancel.disabled
    if failure=='cancelled':solving.on_cancel()
    else:
        error=TimeoutError('solver.timeout') if failure=='timeout' else RuntimeError('controlled failure')
        solving._finish(_make_failure(error),run)
    until(lambda:getattr(entry,'_entry_notice',{}).get('category')==failure)
    assert manager.current==entry.name and entry._cube.colors==before
    assert entry._entry_notice['category']==failure and entry.entry_can_edit()
    assert not entry.entry_action_buttons['random'].disabled
    no_failure_popup()
    if failure!='cancelled':
        assert not entry._entry_problem_actions.retry.disabled
        entry._entry_problem_actions.retry.dispatch('on_release');pump()
        assert manager.current=='SolvingScreen' and len(held)==2
        solving.on_cancel();pump()
    held[0][1]['on_done'](SolveResult(True,[],'',0,0));pump()
    assert manager.current==entry.name and entry._cube.colors==before


def test_palette_is_preserved_in_shared_solving_playback_and_return(workflow):
    _,manager,entry,solving,_=workflow
    fill(entry);cube=entry._cube;move=cube.moves()[0];cube.apply_move(move);before=list(cube.colors)
    palette=tuple((i/(len(entry.view.palette)+1),.35,.72,1) for i in range(len(entry.view.palette)))
    entry.view.palette=palette;run=start(workflow)
    assert tuple(solving.view.palette)==palette
    inverse=move.inverse(cube.geometry.spec.turn_order)
    solving._finish(SolveResult(True,[inverse],'',0,1),run);pump()
    playback=manager.current_screen
    assert playback.name=='PolyhedralPlaybackScreen' and tuple(playback.view.palette)==palette
    playback.seek(1);until(lambda:playback._seek_job is None and playback._index==1)
    assert playback._work.is_solved() and cube.colors==before
    playback.confirm_back();pump()
    popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open)
    next(b for b in popup.walk() if getattr(b,'icon_name','')=='done').dispatch('on_release');pump()
    assert manager.current==entry.name and entry._cube.colors==before
    assert tuple(entry.view.palette)==palette


def test_failed_scramble_retries_scramble_instead_of_starting_a_solver(workflow,monkeypatch):
    _,manager,entry,_,held=workflow
    before=list(entry._cube.colors)
    def fail(*args):raise RuntimeError('controlled scramble failure')
    monkeypatch.setattr('cube.polyhedral_scramble.scramble',fail)
    entry.entry_action_buttons['random'].dispatch('on_release');pump()
    assert manager.current==entry.name and entry._entry_notice['category']=='internal'
    assert entry._cube.colors==before
    calls=[];monkeypatch.setattr('cube.polyhedral_scramble.scramble',lambda *args:calls.append(1) or ())
    entry._entry_problem_actions.retry.dispatch('on_release');pump()
    assert calls==[1] and not held and manager.current==entry.name
