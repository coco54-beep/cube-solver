"""Input real scrambled bandage panels through the Camouflage-style workflow."""
from copy import deepcopy
from types import SimpleNamespace
from threading import Event
import pytest
from cube.bandaged_cube import BandagedCube,KINDS
from cube.bandaged_entry import plates
from cube.bandaged_observation import BandagedSixViewDraft,COLOR_CODES,state_key
from cube.cuboid import FACES
from cube.cuboid_observation import UNKNOWN,EMPTY,PLASTIC
from cube.conversion import cubies_to_facelets


def enter(source):
    draft=BandagedSixViewDraft(source.puzzle_kind)
    data=cubies_to_facelets(source.cubies,source.n)
    for p in plates(source):
        f=FACES.index(p.face);r,c=p.cells[0]
        cells=tuple(rr*source.n+cc for rr,cc in p.cells)
        # The rectangle operation must cover exactly the physical plate.
        assert draft.rectangle(f,cells[0],cells[-1])==cells
        draft.paint(f,cells,COLOR_CODES.index(data[p.face][r][c]))
    return draft


@pytest.mark.parametrize('kind',KINDS)
@pytest.mark.parametrize('length,seed',[(30,7),(100,23),(100,79)])
def test_scramble_manually_enter_rectangles_and_match_without_history(kind,length,seed):
    source=BandagedCube.random_scramble(kind,length,seed)
    source.history=[]
    before=state_key(source)
    draft=enter(source)
    restored=BandagedSixViewDraft(kind,deepcopy(draft.state()))
    result=restored.match()
    assert result.status=='ok'
    assert result.cube.history==[]
    assert cubies_to_facelets(result.cube.cubies,source.n)==cubies_to_facelets(source.cubies,source.n)
    assert {(p.face,p.cells) for p in plates(result.cube)}=={(p.face,p.cells) for p in plates(source)}
    assert state_key(source)==before
    # Matching must preserve the preset's actual move restrictions.
    for axis in range(3):
        extent=max(p[axis] for p in source.cubies)
        for layers in ({-extent}, {extent}):
            assert result.cube.can_turn(axis,layers)==source.can_turn(axis,layers)


def test_repaint_existing_panel_keeps_its_seams_and_does_not_recolour_neighbour():
    draft=BandagedSixViewDraft('fused_cube')
    draft.paint(2,(0,1),0);draft.paint(2,(2,),0)
    neighbour=draft.views[2][2];group=draft.views[2][0][1]
    draft.paint(2,(1,),4)
    assert [v[0] for v in draft.views[2][:2]]==[4,4]
    assert draft.views[2][2]==neighbour and draft.views[2][0][1]==group
    assert draft.connections()>={('F',((0,0),(0,1))),('F',((0,2),))}


def test_incomplete_illegal_empty_and_cancel_keep_source_draft():
    draft=BandagedSixViewDraft('bicube')
    assert draft.match().status=='incomplete'
    cancel=Event();cancel.set()
    assert draft.match(cancel=cancel).status=='cancelled'
    draft=enter(BandagedCube.solved('bicube'));before=draft.state()
    assert draft.match(seconds=0).status=='budget' and draft.state()==before
    draft.paint(2,(0,),EMPTY)
    assert draft.match().status=='conflict'


@pytest.fixture
def editor(monkeypatch):
    from app.desktop_runtime import configure_graphics
    configure_graphics()
    from kivy.app import App
    from app.theme import Theme
    from ui.screens.bandaged_six_view_screen import BandagedSixViewScreen
    from kivy.clock import Clock
    monkeypatch.setattr(Clock,'schedule_once',lambda *_:None)
    cube=BandagedCube.solved('bicube')
    app=SimpleNamespace(cube=cube,puzzle_kind='bicube',n=3,theme=Theme(),simple_input=False,
        facelets_input=None,facelets_cache={},bandage_entry_cache={},bandage_six_cache={},
        solve_result=None,polyhedral_solution=None,input_from_camera=False)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=BandagedSixViewScreen(name='BandagedSixViewScreen');screen.on_pre_enter()
    yield screen,app
    screen.reset_interaction()


def test_simplified_controls_continuous_colour_and_undo(editor):
    screen,app=editor
    assert all(button.parent.parent is None for button in screen.tools.values())
    assert screen.depth_label.parent.parent is None
    screen.select_color(3)
    screen.select_region((0,1));screen.select_region((2,))
    assert screen._draft.views[2][0][0]==screen._draft.views[2][2][0]==3
    screen.undo()
    assert screen._draft.views[2][2][0]==UNKNOWN and screen._draft.views[2][0][0]==3


def test_scrambled_state_remains_editable_and_reset_undo_preserves_exact_state(editor):
    screen,app=editor
    source=BandagedCube.random_scramble('bicube',30,7)
    screen._load_cube(source)
    before=state_key(screen._cube);state=deepcopy(screen._six_state)
    assert screen._ready()
    screen.entry_reset_solved();screen.undo()
    assert state_key(screen._cube)==before and screen._six_state==state
    screen.select_color(0);screen.select_region((0,))
    assert not screen._ready()
    screen.undo();assert screen._ready() and screen._six_state==state


def test_per_model_draft_survives_leaving_and_reselecting_preset(editor):
    screen,app=editor
    source=BandagedCube.random_scramble('bicube',30,7);screen._load_cube(source)
    expected=deepcopy(screen._six_state)
    screen.on_pre_leave()
    app.cube=BandagedCube.solved('bicube');screen._fresh_request=True
    screen.on_pre_enter()
    assert screen._six_state==expected and not screen._ready()


def test_solve_button_passes_matched_bandaged_state_to_shared_solver(editor):
    screen,app=editor;source=BandagedCube.random_scramble('bicube',30,7)
    screen._load_cube(source);calls=[]
    target=SimpleNamespace(configure=lambda cube,name:calls.append((cube.clone(),name)) or False)
    screen.manager=SimpleNamespace(current=screen.name,get_screen=lambda _:target)
    screen.solve()
    assert len(calls)==1 and state_key(calls[0][0])==state_key(source)
    assert calls[0][1]==screen.name and screen.manager.current==screen.name
    assert app.facelets_input==screen.collect_facelets()


def test_twist_uses_restored_six_views_instead_of_an_older_live_draft(editor):
    from ui.screens.twist_screen import TwistScreen
    screen,app=editor;source=BandagedCube.random_scramble('bicube',30,7)
    app.cube=screen._cube=source
    screen._six_state=BandagedSixViewDraft.from_cube(source).state()
    screen._six_applied=deepcopy(screen._six_state);screen._six_cube_key=state_key(source)
    fake=SimpleNamespace(manager=SimpleNamespace(has_screen=lambda _:True,get_screen=lambda _:screen))
    assert TwistScreen._input_screen(fake) is screen
    assert screen.collect_facelets()==cubies_to_facelets(source.cubies,3)


def test_current_partial_six_view_draft_survives_session_restore(editor,monkeypatch,tmp_path):
    from app.session import SessionStore
    from kivy.clock import Clock
    screen,app=editor;app.user_data_dir=str(tmp_path)
    class Manager:
        current=screen.name;transition=SimpleNamespace(duration=0)
        current_screen=screen
        def has_screen(self,name):return name==screen.name
        def get_screen(self,name):assert name==screen.name;return screen
    app.root=Manager();screen.manager=app.root
    screen.select_color(2);screen.select_region((0,1));expected=deepcopy(screen._six_state)
    store=SessionStore(app);store.save(synchronous=True)
    screen._six_state=None;screen._draft=BandagedSixViewDraft('bicube')
    monkeypatch.setattr(Clock,'schedule_once',lambda fn,dt=0:fn(dt))
    try:
        store.restore()
        assert not store.restoring and store.recovery_reason is None
        assert screen._six_state==expected and screen._draft.state()==expected
    finally:store.close()


def test_legacy_size_card_draft_migrates_colours_and_seams(editor,monkeypatch,tmp_path):
    import json
    from app.session import SessionStore,encode
    from kivy.clock import Clock
    screen,app=editor;app.user_data_dir=str(tmp_path)
    source=BandagedCube.random_scramble('bicube',30,7)
    values=cubies_to_facelets(source.cubies,source.n)
    seams={(p.face,p.cells) for p in plates(source)}
    old=SimpleNamespace()
    class Manager:
        current='HomeScreen';transition=SimpleNamespace(duration=0)
        def has_screen(self,name):return name in ('InputScreen',screen.name,'HomeScreen')
        def get_screen(self,name):return screen if name==screen.name else old
    app.root=Manager();screen.manager=app.root
    state=dict(version=1,page='InputScreen',app=dict(n=3,cube=source,puzzle_kind='bicube'),
               screens={'InputScreen':dict(_data=values,_bandage_connections=seams)},color_info={})
    store=SessionStore(app);store.path.write_text(json.dumps(encode(state)),encoding='utf-8')
    monkeypatch.setattr(Clock,'schedule_once',lambda fn,dt=0:fn(dt))
    try:
        store.restore()
        assert store.recovery_reason is None and app.root.current==screen.name
        assert screen.collect_facelets()==values and screen._draft.connections()==seams
        assert screen._draft.match().status=='ok'
    finally:store.close()
