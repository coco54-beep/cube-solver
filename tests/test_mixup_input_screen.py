"""Exercise the actual Mixup editor callbacks, undo and background handoff."""
import os
from copy import deepcopy
from time import monotonic,sleep
from types import SimpleNamespace

import pytest

os.environ.setdefault('KIVY_NO_ARGS','1')
os.environ.setdefault('KIVY_METRICS_DENSITY','1')
os.environ.setdefault('KIVY_DPI','96')
from app.desktop_runtime import configure_graphics
configure_graphics()
pytest.importorskip('kivy')
from kivy.config import Config
Config.set('graphics','window_state','hidden')
from kivy.app import App
from kivy.clock import Clock
from app.theme import Theme
from cube.articulated import MIXUP_MODELS
from cube.mixup import MixupCube
from cube.mixup_entry import MixupEntryDraft
from cube.polyhedral import Move
from ui.screens.mixup_input_screen import MixupInputScreen


def wait_until(predicate):
    deadline=monotonic()+4
    while not predicate() and monotonic()<deadline:
        Clock.tick();sleep(.005)
    assert predicate()


@pytest.fixture
def editor(monkeypatch):
    app=SimpleNamespace(theme=Theme(),cube=None,polyhedral_solution=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    screen=MixupInputScreen()
    def load(kind,moves=None):
        cube=MixupCube(kind)
        if moves is not None:cube.apply_moves([Move(*move) for move in moves])
        else:
            for a,bands in enumerate(cube.geometry.layers):
                try:cube.apply_move(Move(a,1,1));break
                except ValueError:continue
        app.cube=cube;screen.on_pre_enter()
        screen.entry_commit_state(MixupEntryDraft.from_cube(cube))
        return screen
    yield load
    screen.reset_interaction()
    # Flush callbacks while the fake app still exists.
    Clock.tick()


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_edit_rotation_and_undo_preserve_other_positions(editor,kind):
    screen=editor(kind);original=deepcopy(screen._mx_state);draft=screen._get_draft()
    index=next(i for i,b in enumerate(draft.blocks)
               if b['role']=='centre' and b['cells'] and draft.can_rotate_assembly(i))
    screen.pick(index*1024);wait_until(lambda:screen._assembly_job is None)
    screen.rotate_assembly(1)
    assert screen._mx_state!=original
    assert all(b==original['blocks'][i] for i,b in enumerate(screen._mx_state['blocks']) if i!=index)
    screen.select_color((screen._color+1)%6)
    screen.pick(index*1024)
    screen.undo();screen.undo()
    assert screen._mx_state==original
    assert screen._applied()
    assert screen._get_draft().state()==original


@pytest.mark.parametrize('kind',MIXUP_MODELS)
@pytest.mark.parametrize('role',('centre','edge','inner_edge'))
def test_full_turn_of_scrambled_block_keeps_verified_state_and_solution_path(editor,monkeypatch,kind,role):
    from tests.test_mixup_entry_edits import mixed_cube
    from ui.screens.articulated_screen import RigidEntryScreen
    cube=mixed_cube(kind)
    screen=editor(kind,[(m.axis,m.layer,m.amount) for m in cube.history])
    draft=screen._get_draft()
    index=next((i for i,b in enumerate(draft.blocks) if b['role']==role and draft.can_rotate_assembly(i)),None)
    if index is None:pytest.skip('This model has no editable '+role)
    original=screen._cube;frames=tuple(original.frames);history=tuple(original.history)
    screen.pick(index*1024);wait_until(lambda:screen._assembly_job is None)
    step=draft.rotation_step(index)
    for _ in range(4//step):screen.rotate_assembly(1)
    assert screen._applied()
    assert screen._cube is original
    assert tuple(screen._cube.frames)==frames
    assert tuple(screen._cube.history)==history
    assert screen._cube._history_snapshot==frames
    seen=[]
    def solve(self):seen.append(self._cube.clone())
    def unexpected(*_):raise AssertionError('A restored state must not be rematched and lose its path')
    monkeypatch.setattr(RigidEntryScreen,'solve',solve)
    monkeypatch.setattr('ui.screens.mixup_input_screen.match_observations',unexpected)
    screen.solve()
    assert screen._job is None and len(seen)==1
    assert tuple(seen[0].history)==history
    assert tuple(seen[0].frames)==frames


def test_restored_saved_input_recovers_known_state_before_matching(editor,monkeypatch):
    from ui.screens.articulated_screen import RigidEntryScreen
    screen=editor('mixup_plus_334');draft=screen._get_draft()
    index=next(i for i,b in enumerate(draft.blocks) if b['role']=='inner_edge' and draft.can_rotate_assembly(i))
    screen.pick(index*1024);wait_until(lambda:screen._assembly_job is None)
    screen.rotate_assembly(1);screen.rotate_assembly(1)
    # Simulate an old saved draft whose physical state was restored but whose
    # applied marker had already been discarded by the previous implementation.
    screen._mx_state=deepcopy(screen._mx_state);screen._draft=None;screen._mx_applied=None
    seen=[]
    monkeypatch.setattr(RigidEntryScreen,'solve',lambda self:seen.append(self._cube))
    screen.solve()
    assert seen==[screen._cube] and screen._applied() and screen._job is None


def test_real_colour_edit_stays_unverified_until_restored(editor):
    screen=editor('mixup_plus_334');draft=screen._get_draft()
    bi=next(i for i,b in enumerate(draft.blocks) if b['cells'])
    original=draft.blocks[bi]['cells'][0]['color']
    screen.select_color((original+1)%6);screen.pick(bi*1024)
    assert not screen._applied()
    screen.select_color(original);screen.pick(bi*1024)
    assert screen._applied()


@pytest.mark.parametrize('kind',('mixup_334','mixup_plus_334'))
def test_generated_scramble_full_turns_and_production_solution_replay(editor,kind):
    from cube.mixup import scramble_mixup
    from solver.mixup import solve_mixup
    cube=scramble_mixup(kind,seconds=2.)
    screen=editor(kind,[(m.axis,m.layer,m.amount) for m in cube.history])
    for role in ('centre','inner_edge'):
        draft=screen._get_draft()
        index=next((i for i,b in enumerate(draft.blocks) if b['role']==role and draft.can_rotate_assembly(i)),None)
        if index is None:continue
        screen.pick(index*1024);wait_until(lambda:screen._assembly_job is None)
        for _ in range(4//draft.rotation_step(index)):screen.rotate_assembly(1)
    assert screen._applied() and screen._cube.frames==cube.frames
    result=solve_mixup(screen._cube.clone())
    assert result.success
    replay=screen._cube.clone();replay.apply_moves(result.moves)
    assert replay.is_solved()


def test_fast_selection_does_not_keep_previous_positions_cards(editor):
    screen=editor('mixup_333')
    choices=[i for i,b in enumerate(screen._get_draft().blocks) if b['role']=='edge' and b['cells']]
    screen.pick(choices[0]*1024);wait_until(lambda:screen._assembly_job is None)
    stale=screen._assemblies[0]
    screen.pick(choices[1]*1024)
    before=deepcopy(screen._mx_state)
    screen.select_assembly(stale)
    assert screen._mx_state==before
    wait_until(lambda:screen._assembly_job is None)
    assert all(a.positions==screen._get_draft().linked_positions(choices[1]) for a in screen._assemblies)


def test_new_scramble_replaces_dirty_input_and_can_undo(editor,monkeypatch):
    screen=editor('mixup_333');screen.pick(4*1024)
    screen.select_color((screen._color+1)%6)
    screen.pick(4*1024)
    before=deepcopy(screen._mx_state)
    monkeypatch.setattr('cube.mixup.scramble_mixup',lambda kind,cancel:MixupCube(kind))
    screen.randomize();wait_until(lambda:screen._job is None)
    assert screen._applied() and screen._cube.is_solved()
    assert screen._mx_state!=before
    screen.undo()
    assert screen._mx_state==before
    assert screen._get_draft().state()==before


def test_failed_scramble_keeps_current_edit_and_undo(editor,monkeypatch):
    screen=editor('mixup_333');screen.pick(4*1024);screen.rotate_assembly(1)
    before=deepcopy(screen._mx_state);undo=len(screen._mx_undo)
    def fail(kind,cancel):raise ValueError('rigid.no_scramble')
    monkeypatch.setattr('cube.mixup.scramble_mixup',fail)
    screen.randomize();wait_until(lambda:screen._job is None)
    assert screen._mx_state==before
    assert len(screen._mx_undo)==undo
    assert screen._get_draft().state()==before


def test_changed_composition_invalidates_old_picking_polygons(editor):
    screen=editor('mixup_444');screen.pick(3*1024)
    wait_until(lambda:screen._assembly_job is None)
    screen.view._polygons=[('old hit targets',123)]
    screen.clear_position()
    assert screen.view._polygons==[]
    screen.undo()
    assert screen.view._polygons==[]


def test_original_choice_stays_after_switch_and_restores_full_local_input(editor):
    moves=[(1,1,1),(1,0,2),(2,0,2),(2,2,2),(2,2,2),(2,0,2),(0,0,2),(1,2,2),(0,1,1)]
    screen=editor('mixup_333',moves);screen.pick(3*1024)
    wait_until(lambda:screen._assembly_job is None)
    before=deepcopy(screen._mx_state)
    keys=tuple(c.assembly_key for c in screen.gallery.children)
    assert len(keys)==3  # original sloping edge, centre, regular edge
    source=screen._original_assembly()['assembly'].key
    assert source in keys
    option=next(a for a in screen._assemblies if a.counts=={'centre':1})
    screen.select_assembly(option)
    assert screen._mx_state!=before
    assert tuple(c.assembly_key for c in screen.gallery.children)==keys
    original_card=next(c for c in screen.gallery.children if c.assembly_key==source)
    original_card.dispatch('on_release')
    assert screen._mx_state==before
    assert tuple(c.assembly_key for c in screen.gallery.children)==keys
    screen.undo()
    assert screen._mx_state!=before


def test_original_choice_survives_rotation_and_reselecting_other_piece(editor):
    screen=editor('mixup_333');screen.pick(22*1024)
    wait_until(lambda:screen._assembly_job is None)
    before=deepcopy(screen._mx_state)
    keys=tuple(c.assembly_key for c in screen.gallery.children)
    screen.rotate_assembly(1)
    assert tuple(c.assembly_key for c in screen.gallery.children)==keys
    screen.pick(13*1024);wait_until(lambda:screen._assembly_job is None)
    screen.pick(22*1024);wait_until(lambda:screen._assembly_job is None)
    assert tuple(c.assembly_key for c in screen.gallery.children)==keys
    screen.restore_original((22,))
    assert screen._mx_state==before


def test_clicking_active_original_does_not_reset_later_colours(editor):
    screen=editor('mixup_333');screen.pick(22*1024)
    wait_until(lambda:screen._assembly_job is None)
    screen.select_color((screen._color+1)%6)
    screen.pick(22*1024)
    before=deepcopy(screen._mx_state);count=len(screen._mx_undo)
    screen.restore_original((22,))
    assert screen._mx_state==before
    assert len(screen._mx_undo)==count


def test_assembly_caption_remains_attached_after_redrawing_and_resizing(editor):
    screen=editor('mixup_333');screen.pick(22*1024)
    wait_until(lambda:screen._assembly_job is None)
    for card in screen.gallery.children:
        assert card.caption.text
        for size in ((100,76),(180,90),(130,76)):
            card.size=size;card.redraw()
            assert card.caption.canvas in card.canvas.children


def test_only_one_local_clear_button_opens_explicit_scopes(editor):
    screen=editor('mixup_333');screen.pick(22*1024)
    assert not hasattr(screen,'clear_position_button')
    before=deepcopy(screen._mx_state)
    screen.clear_choices()
    popup=screen._clear_popup
    assert popup is not None
    buttons=list(reversed(popup.content.children))
    assert len(buttons)==3
    assert screen._mx_state==before  # opening does not clear anything
    buttons[0].dispatch('on_release')
    assert screen._get_draft().blocks[22]['cells'][0]['color']==-1
    assert all(b==before['blocks'][i] for i,b in enumerate(screen._mx_state['blocks']) if i!=22)
    screen.undo();screen.clear_choices()
    buttons=list(reversed(screen._clear_popup.content.children))
    buttons[1].dispatch('on_release')
    assert not screen._get_draft().blocks[22]['configured']
    assert all(b==before['blocks'][i] for i,b in enumerate(screen._mx_state['blocks']) if i!=22)


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_colour_brush_paints_successive_panels_and_undoes_each_stroke(editor,kind):
    screen=editor(kind);before=deepcopy(screen._mx_state)
    targets=[]
    for bi,block in enumerate(screen._get_draft().blocks):
        for ci,cell in enumerate(block['cells']):
            if cell['color']!=2:targets.append((bi,ci))
        if len(targets)>=3:break
    targets=targets[:3]
    screen.select_color(2)
    assert screen._mx_state==before  # choosing a brush never changes a panel
    for bi,ci in targets:
        screen.pick(bi*1024+ci)
        assert screen._get_draft().blocks[bi]['cells'][ci]['color']==2
        assert screen._color==2
        assert screen._swatches[2].active
    assert len(screen._mx_undo)==3
    for _ in targets:screen.undo()
    assert screen._mx_state==before


def test_changing_brush_does_not_repaint_previous_panel(editor):
    screen=editor('mixup_333')
    screen.select_color(2);screen.pick(0)
    before=deepcopy(screen._mx_state)
    screen.select_color(4)
    assert screen._mx_state==before
    screen.pick(2*1024)
    assert screen._get_draft().blocks[0]['cells'][0]['color']==2
    assert screen._get_draft().blocks[2]['cells'][0]['color']==4


def test_active_colour_toggles_to_selection_without_recolouring(editor):
    screen=editor('mixup_333');screen.select_color(2);screen.pick(0)
    screen.select_color(2)
    before=deepcopy(screen._mx_state);count=len(screen._mx_undo)
    screen.pick(2*1024)
    assert screen._mx_state==before
    assert len(screen._mx_undo)==count
    assert not any(s.active for s in screen._swatches)


def test_brush_does_not_invent_an_unconfigured_assembly(editor):
    screen=editor('mixup_333');screen.clear()
    screen.select_color(2)
    before=deepcopy(screen._mx_state)
    screen.pick(3*1024)
    assert screen._mx_state==before
    assert screen._paint_enabled and screen._color==2
    screen.pick(0)
    assert screen._get_draft().blocks[0]['cells'][0]['color']==2


def test_repainting_same_colour_does_not_create_undo_steps(editor):
    screen=editor('mixup_333');screen.select_color(2);screen.pick(0)
    count=len(screen._mx_undo);before=deepcopy(screen._mx_state)
    screen.pick(0)
    assert screen._mx_state==before
    assert len(screen._mx_undo)==count


@pytest.mark.parametrize('kind',('mixup_plus_333','mixup_plus_334','mixup_plus_344','mixup_plus_444'))
def test_inner_composition_cards_rotation_and_colours(editor,kind):
    from cube.mixup_assembly import inner_pattern
    screen=editor(kind);screen.clear();screen.pick(2*1024)
    wait_until(lambda:screen._assembly_job is None)
    choices={inner_pattern(a.pieces):a for a in screen._assemblies}
    assert len(screen.gallery.children)==len({a.group_key for a in screen._assemblies})
    screen.select_assembly(choices.get('same',choices.get('whole')))
    draft=screen._get_draft()
    screen.select_color(2);screen.pick(2*1024);screen.select_color(2)
    if len(draft.blocks[2]['cells'])==2:
        screen.select_color(4);screen.pick(2*1024+1);screen.select_color(4)
    before=deepcopy(screen._mx_state)
    screen.rotate_assembly(1)
    assert screen._get_draft().blocks[2]['rotation']==2
    assert '180' in screen.rotation_label.text
    assert {c['color'] for c in screen._get_draft().blocks[2]['cells']}=={c['color'] for c in before['blocks'][2]['cells']}
    screen.rotate_assembly(1)
    assert screen._get_draft().blocks[2]['rotation']==0
    if 'opposite' in choices:
        screen.select_assembly(choices['opposite'])
        assert inner_pattern(screen._get_draft().assembly_at(2).pieces)=='opposite'
        assert all(c['color']>=0 for c in screen._get_draft().blocks[2]['cells'])


@pytest.mark.parametrize('kind,count',(('mixup_plus_333',2),('mixup_plus_334',5),
                                     ('mixup_plus_344',7),('mixup_plus_444',3)))
def test_plus_centre_edge_menu_is_shared_and_does_not_label_physical_identity(editor,kind,count):
    from app.i18n import tr
    screen=editor(kind);screen.clear();draft=screen._get_draft()
    indices=[next(i for i,b in enumerate(draft.blocks) if b['role']==role) for role in ('centre','edge')]
    expected=None
    for index in indices:
        screen.pick(index*1024);wait_until(lambda:screen._assembly_job is None)
        keys=tuple(c.assembly_key for c in screen.gallery.children)
        assert len(keys)==count
        if expected is None:expected=keys
        assert keys==expected
        assert screen.selection.text.startswith(tr('mixup.entry_observation_position'))
        # A same-colour template made of centres must also be selectable at
        # the two-sided observation position formerly called an edge slot.
        if draft.blocks[index]['role']=='edge':
            choice=next(a for a in screen._assemblies if set(a.counts)=={'centre'})
            screen.select_assembly(choice)
            assert screen._get_draft().assembly_at(index).counts==choice.counts
            assert len(screen.gallery.children)==count
