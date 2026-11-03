"""Uniform categories, recovery ownership and exact-state solution reuse."""
from copy import deepcopy
import pytest
from services.failures import classify
from services.solve_service import _make_failure
from app.i18n import CATALOG,tr
from tests.test_input_cache_restore import editor


@pytest.mark.parametrize('lang',('zh','en','ja'))
@pytest.mark.parametrize('key,category',(('poly.error.incomplete','incomplete'),
    ('poly.error.orientation','illegal'),('cuboid.search_budget','timeout')))
def test_classification_does_not_depend_on_screen_language(lang,key,category):
    assert classify(CATALOG[lang][key])==category


def test_internal_faults_and_timeout_never_become_illegal_input():
    assert _make_failure(IndexError('out of range')).failure_category=='internal'
    assert _make_failure(TimeoutError()).failure_category=='timeout'
    assert _make_failure(InterruptedError()).failure_category=='cancelled'
    assert _make_failure(RuntimeError('poly.error.incomplete')).failure_category=='internal'
    assert _make_failure(ValueError('Invalid cuboid search table')).failure_category=='internal'
    assert _make_failure(ValueError('颜色 W 出现 10 次（应为9）')).failure_category=='illegal'
    assert _make_failure(ValueError('Color W appears 10 times (expected 9)')).failure_category=='illegal'


def test_incomplete_input_can_locate_missing_cells_without_changing_colours(editor):
    from ui.entry_problems import focus_problem
    screen,app=editor;screen.on_enter();before=deepcopy(screen.collect_facelets())
    screen.check();notice=screen._entry_notice
    assert notice['category']=='incomplete' and len(notice['locations'])==54
    assert screen._entry_problem_actions.retry.disabled
    focus_problem(screen)
    assert screen.collect_facelets()==before and screen._error_cells
    assert screen.view._entry_pivot is not None
    assert screen._ori.current_face()==screen.view._entry_pivot[0]
    selected=screen.view._entry_pivot
    screen._refresh_view()
    assert screen.view._entry_pivot==selected


def test_timeout_recovery_keeps_input_and_allows_retry(editor,monkeypatch):
    screen,app=editor;screen.on_enter();before=screen.collect_facelets();calls=[]
    monkeypatch.setattr(screen,'start_solve',lambda:calls.append('retry'))
    screen.entry_show_error('cuboid.search_budget',kind='solver',category='timeout')
    row=screen._entry_problem_actions;assert not row.retry.disabled
    row.retry.dispatch('on_release')
    assert calls==['retry'] and screen.collect_facelets()==before


def test_validation_program_fault_keeps_its_exception_category(editor):
    from ui.entry_feedback import validation_action
    screen,app=editor;screen.on_enter();before=screen.collect_facelets()
    @validation_action
    def check(self):raise RuntimeError('poly.error.incomplete')
    check(screen)
    assert screen._entry_notice['category']=='internal'
    assert screen.collect_facelets()==before and not screen._entry_problem_actions.retry.disabled


def test_global_illegality_does_not_invent_a_bad_piece(editor):
    screen,app=editor;screen.on_enter()
    screen.entry_show_error('poly.error.orientation',category='illegal',locations=[])
    assert screen._entry_problem_actions.locate.disabled
    assert tr('entry.location_unknown') in screen.msg.text


def test_solution_cache_replays_and_does_not_alias_a_returned_result():
    from services import solution_cache as cache
    from cube.articulated import ArticulatedCube
    from solver.result import SolveResult
    cube=ArticulatedCube('tangram');move=next(iter(cube.moves()));cube.apply_move(move)
    inverse=move.inverse(cube.geometry.spec.turn_order)
    result=SolveResult(True,[inverse],'',1,1);cache.clear()
    cache.remember(cube,result,lambda:False)
    entered_frames=tuple(cube.frames);reused=cache.lookup(cube,lambda:False)
    assert reused is not None and tuple(cube.frames)==entered_frames
    reused.moves.clear();assert cache.lookup(cube,lambda:False).moves==[inverse]
    with pytest.raises(InterruptedError):cache.lookup(cube,lambda:True)
    assert cache.lookup(ArticulatedCube('tangram'),lambda:False) is None
    cache.clear()


def test_bad_word_is_not_cached():
    from services import solution_cache as cache
    from cube.articulated import ArticulatedCube
    from solver.result import SolveResult
    cube=ArticulatedCube('tangram');move=next(iter(cube.moves()));cube.apply_move(move)
    cache.clear();cache.remember(cube,SolveResult(True,[move,move],'',0,2),lambda:False)
    assert cache.lookup(cube,lambda:False) is None


def test_service_reuses_only_a_verified_exact_state(monkeypatch):
    from services import solution_cache as cache
    from services.solve_service import SolveService,CancelToken
    from cube.articulated import ArticulatedCube
    import solver.articulated
    cube=ArticulatedCube('tangram');cube.apply_move(next(iter(cube.moves())));cube.history=[]
    cache.clear();first=[];SolveService()._run(cube.clone(),first.append,None,CancelToken())
    assert first[0].success
    def unexpected_search(*args,**kwargs):raise AssertionError('Repeated search for identical state')
    monkeypatch.setattr(solver.articulated,'solve_articulated',unexpected_search)
    second=[];progress=[];before=tuple(cube.frames)
    SolveService()._run(cube.clone(),second.append,progress.append,CancelToken())
    assert second[0].success and any(p.get('cache_hit') for p in progress)
    assert tuple(cube.frames)==before and not cube.history
    cache.clear()


def test_solution_cache_has_a_fixed_entry_and_word_bound():
    from services import solution_cache as cache
    from cube.mixup import MixupCube
    from cube.articulated import MIXUP_MODELS
    from solver.result import SolveResult
    cache.clear()
    for kind in tuple(MIXUP_MODELS)[:5]:
        cube=MixupCube(kind);move=next(iter(cube.moves()));cube.apply_move(move)
        result=SolveResult(True,[move.inverse(cube.geometry.spec.turn_order)],'',0,1)
        cache.remember(cube,result,lambda:False)
    assert len(cache._entries)<=cache.MAX_ENTRIES
    assert sum(len(entry[1].moves) for entry in cache._entries.values())<=cache.MAX_MOVES
    cache.clear()
