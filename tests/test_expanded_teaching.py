"""Teaching uses each physical model and never the live input draft."""
import os
from types import SimpleNamespace
import pytest
os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from candidate_puzzles import REQUESTED
from demo.solutions import solved_demo_cube,build_example,make_scrambled_demo,state_signature
from demo.expanded_tutorials import tutorial,lessons


@pytest.mark.parametrize('entry',REQUESTED,ids=lambda e:e.kind)
def test_expanded_exercises_restore_their_actual_physical_model(entry):
    mode=(entry.kind,entry.n);cube=solved_demo_cube(mode)
    assert cube.puzzle_kind==entry.kind
    signature=state_signature(cube);steps=lessons(*mode)
    assert len(steps[0]['cases'])>=3
    for step in steps:
        for case in step['cases']:
            before=state_signature(case['initial']);work=build_example(mode,case)
            assert work.puzzle_kind==entry.kind and work is not case['initial']
            for move in case['moves']:work.apply_move(move)
            assert work.is_solved(),(entry.kind,case['name'])
            assert state_signature(case['initial'])==before
    assert state_signature(cube)==signature
    random=make_scrambled_demo(mode)
    assert random.puzzle_kind==entry.kind and not random.is_solved()
    assert len(tutorial(entry.kind).goals)==4


@pytest.mark.parametrize('entry',REQUESTED,ids=lambda e:e.kind)
def test_teaching_routes_cover_every_requested_model(entry):
    from ui.screens.demo_menu import source_screen
    from demo.expanded_support import entry_screen,view_class
    assert source_screen((entry.kind,entry.n))==entry_screen(entry.kind)
    assert view_class(entry.kind) is not None
    if entry.kind=='trajber':assert solved_demo_cube((entry.kind,entry.n)).n==4


def test_new_teaching_has_no_external_links():
    from pathlib import Path
    for name in ('demo/expanded_tutorials.py','demo/expanded_curriculum.py'):
        value=Path(name).read_text(encoding='utf-8')
        assert 'https://' not in value and 'http://' not in value
    assert not hasattr(tutorial('blanker'),'sources')


def test_shape_only_routes_do_not_teach_nonexistent_pieces():
    kilominx=''.join(tutorial('mirror_kilominx').goals)
    assert '只有角块' in kilominx
    assert '棱和中心步骤' in kilominx
    assert '二阶' in tutorial('blanker').intro
    assert '四阶' in tutorial('trajber').intro


@pytest.mark.parametrize('entry',REQUESTED,ids=lambda e:e.kind)
def test_original_curriculum_has_actions_checks_and_a_verified_formula(entry):
    from demo.expanded_curriculum import chapters
    units=chapters(entry.kind)
    assert len(units)==4
    assert all(c.title and c.recognize and len(c.actions)>=3 and c.done and c.pitfall for c in units)
    cases=[case for step in lessons(entry.kind,entry.n) for case in step['cases']]
    assert any(case['teaching_kind'] in ('formula','original_formula') for case in cases)
    for case in cases:
        if not case.get('original'):continue
        base=solved_demo_cube((entry.kind,entry.n));work=base.clone()
        original=state_signature(work)
        for _ in range(3):
            for move in case['moves']:work.apply_move(move)
        assert state_signature(work)==original
        assert len(case['cycle_pieces'])==3
        assert set(case['tutorial_targets'])==set(case['cycle_pieces'])


def test_original_chapters_open_local_examples_and_ignore_replaced_buttons(monkeypatch,tmp_path):
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager,Screen,NoTransition
    from app.theme import Theme
    from ui.screens.demo_menu import DemoMenuScreen
    app=SimpleNamespace(theme=Theme(),user_data_dir=str(tmp_path))
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    root=app.root=ScreenManager(transition=NoTransition())
    root.add_widget(Screen(name='BlankerScreen'))
    menu=DemoMenuScreen(name='DemoMenuScreen');root.add_widget(menu)
    root.current=menu.name;menu.mode=('blanker',2)
    popup=menu.open_learning_route();old=menu.chapter_play_button;calls=[]
    monkeypatch.setattr(menu,'open_case',lambda si,ci:calls.append((si,ci)))
    menu.chapter_next.dispatch('on_release');assert menu._route_chapter==1
    old.dispatch('on_release');assert not calls
    menu.chapter_play_button.dispatch('on_release');assert calls==[(0,1)]
    old.dispatch('on_release');assert calls==[(0,1)]
    row=SimpleNamespace(_demo_generation=object(),collide_point=lambda *a:True)
    touch=SimpleNamespace(pos=(0,0),ud={('demo-row',id(menu)):(row,(0,0))})
    assert not menu._row_touch(row,touch,0,0)
    assert calls==[(0,1)]
    popup.dismiss(animation=False)


@pytest.mark.parametrize('kind,n',(('blanker',2),('dodecahedron_2',2),('dodecahedron_3',3),('trajber',4)))
def test_original_core_words_have_the_stated_isolated_effects(kind,n):
    from cube.mastermorphix import IDENTITY
    for step in lessons(kind,n):
        for case in step['cases']:
            name=str(case['name'])
            if '原创核心工具' not in name:continue
            work=solved_demo_cube((kind,n));positions=tuple(work.cubies)
            for move in case['moves']:work.apply_move(move)
            changed=[p for p in positions if work.cubies[p].home!=p or work.cubies[p].frame!=IDENTITY]
            if '角块三循环' in name:
                assert len(changed)==3
                assert all(work.cubies[p].home!=p and len(work.cubies[p].stickers)==3 for p in changed)
            else:
                assert all(work.cubies[p].home==p for p in positions)
                assert len(changed)==2 and all(len(work.cubies[p].stickers)==3 for p in changed)


def test_original_checkpoints_start_from_their_real_full_solution_states():
    from demo.cases import inverse_move_str
    from demo.solutions import verified_solution_lessons
    from solver.result import SolveResult
    initial=solved_demo_cube(('blanker',2))
    forward=('R','U','F','R','U2','F')
    for move in forward:initial.apply_move(move)
    word=[inverse_move_str(m) for m in reversed(forward)]
    steps=verified_solution_lessons(initial,SolveResult(True,word,'',0,len(word),[]))
    assert len(steps)>1
    replay=initial.clone()
    for step in steps[1:]:
        case=step['cases'][0]
        assert state_signature(case['initial'])==state_signature(replay)
        for move in case['moves']:replay.apply_move(move)
    assert replay.is_solved()
