"""Penrose 2/3/4 enter whole real pieces, with no colour brush fallback."""
import os
import random
from types import SimpleNamespace
import pytest

os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
pytest.importorskip('kivy')
from kivy.app import App
from app.theme import Theme
from cube.coordinates import FACE_NORMALS,pos_from_rc,rc_from_pos
from cube.penrose_entry import (solved,piece_groups,VISIBLE,
                               visible_facelets,shell_signature,Choice,reconstruct)
from cube.conversion import cubies_to_facelets
from ui.screens.input_screen import InputScreen


@pytest.fixture
def editor(monkeypatch):
    screens=[]
    app=SimpleNamespace(theme=Theme(),n=3,puzzle_kind='cube',cube=None,simple_input=False,
                        facelets_input=None,facelets_cache={},bandage_entry_cache={},
                        polyhedral_solution=None,solve_result=None,selection_series=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    def make(n):
        app.n=n;app.cube=solved(n);app.puzzle_kind=f'penrose_{n}'
        screen=InputScreen(name='InputScreen');screen.on_enter();screen.clear_all()
        screen._history=[];screens.append(screen)
        return screen,app
    yield make
    for screen in screens:screen.reset_interaction()


@pytest.mark.parametrize('n',(2,3,4))
def test_all_piece_roles_select_cards_without_painting(editor,n):
    screen,_=editor(n);before=screen.collect_facelets();seen=set()
    for row in range(n):
        for col in range(n):
            pos=pos_from_rc(n,'F',row,col)
            screen.on_cell(row,col,'F');panel=screen.penrose_edges
            role=len(panel.choices[0].stickers);seen.add(role)
            assert panel.position==pos and panel.gallery.children
            assert len(panel.gallery.children)<=8
            assert screen.collect_facelets()==before
    assert seen==({3} if n==2 else {1,2,3})
    assert screen.picker.disabled and screen.picker.height==0
    assert screen.btn_fill.parent is None and screen.btn_pick.parent is None
    screen.fill_face();screen._fill_cell('F',0,0,'G')
    assert screen.collect_facelets()==before


@pytest.mark.parametrize('n',(2,3,4))
def test_card_places_complete_piece_rotation_cycle_and_undo(editor,n):
    screen,_=editor(n)
    for row,col in ((0,0),)+(() if n==2 else ((0,1),(1,1))):
        screen.on_cell(row,col,'F');panel=screen.penrose_edges;pos=panel.position
        before=screen.collect_facelets();card=panel.gallery.children[-1]
        choice=card.penrose_choice;card.dispatch('on_release')
        data=screen.collect_facelets()
        changed=[(f,r,c) for f in before for r in range(n) for c in range(n) if before[f][r][c]!=data[f][r][c]]
        assert len(changed)==len(choice.stickers)
        assert {pos_from_rc(n,f,r,c) for f,r,c in changed}=={pos}
        screen.undo();assert screen.collect_facelets()==before
        screen.redo();assert screen.collect_facelets()==data
        rotations={1:0,2:2,3:3}[len(choice.stickers)]
        for _ in range(rotations):panel.rotate.dispatch('on_release')
        assert screen.collect_facelets()==data
        history=len(screen._history)
        next(b for b in panel.gallery.children if b.active).dispatch('on_release')
        assert len(screen._history)==history


@pytest.mark.parametrize('n',(2,3,4))
def test_stale_cards_and_busy_model_cannot_change_another_position(editor,n):
    screen,_=editor(n);screen.on_cell(0,0,'F');old=screen.penrose_edges.gallery.children[-1]
    screen.on_cell(n-1,n-1,'F');before=screen.collect_facelets();old.dispatch('on_release')
    assert screen.collect_facelets()==before
    screen.view.camera_busy=True
    try:screen.penrose_edges.gallery.children[-1].dispatch('on_release')
    finally:screen.view.camera_busy=False
    assert screen.collect_facelets()==before


@pytest.mark.parametrize('n',(2,3,4))
@pytest.mark.parametrize('seed',(37,20261025))
def test_all_scrambled_pieces_can_be_entered_from_blank_cards(editor,n,seed):
    from cube.appearance import frame_for
    rng=random.Random(seed);pool=('R','U','F','L','B','D')+(('2R','2U','2F') if n==4 else ())
    source=solved(n);source.apply_moves([rng.choice(pool)+rng.choice(('',"'",'2')) for _ in range(24)])
    if n==3:source.apply_moves(['x'])
    target=visible_facelets(cubies_to_facelets(source.cubies,n))
    screen,_=editor(n)
    for _ in range(6):
        face=screen._ori.current_face()
        for row in range(n):
            for col in range(n):
                pos=pos_from_rc(n,face,row,col)
                screen.on_cell(row,col,face);panel=screen.penrose_edges
                desired=next(c for c in panel.choices if all(
                    target[f][r][cc]==dict((a,VISIBLE[b]) for a,b in c.stickers)[normal]
                    for f,normal in FACE_NORMALS.items() if normal in dict(c.stickers)
                    for r,cc in (rc_from_pos(n,f,pos),)))
                group=next(g for g in piece_groups(n,pos) if desired in g)
                card=next(b for b in panel.gallery.children if b.penrose_choice in group)
                card.dispatch('on_release')
                for _ in range(3):
                    if panel.pattern()==tuple((a,VISIBLE[b]) for a,b in desired.stickers):break
                    panel.rotate.dispatch('on_release')
                assert panel.pattern()==tuple((a,VISIBLE[b]) for a,b in desired.stickers)
        screen._ori.turn_next();screen._refresh_view()
    assert screen.collect_facelets()==target
    rebuilt=reconstruct(screen.collect_facelets(),n)
    assert visible_facelets(cubies_to_facelets(rebuilt.cubies,n))==target
    for pos,p in source.cubies.items():
        q=rebuilt.cubies[pos]
        assert shell_signature(n,pos,Choice(p.home,frame_for(p),tuple(sorted(p.stickers.items()))))==shell_signature(n,pos,Choice(q.home,frame_for(q),tuple(sorted(q.stickers.items()))))


def test_ordinary_input_restores_palette_and_face_fill(editor):
    from cube.cube3 import Cube3
    screen,app=editor(2)
    app.cube=Cube3.solved();app.n=3;app.puzzle_kind='cube';screen.on_enter()
    assert not screen.picker.disabled and screen.picker.height>0
    assert screen.btn_fill.parent is screen.controls_grid and screen.controls_grid.cols==6
    screen.on_cell(0,0,'F');assert screen.collect_facelets()['F'][0][0]


@pytest.mark.parametrize('n',(2,3,4))
def test_real_face_animation_preserves_pieces_and_blocks_queued_cards(editor,n):
    screen,_=editor(n);screen.on_cell(0,0,'F')
    screen.penrose_edges.gallery.children[-1].dispatch('on_release')
    stale=screen.penrose_edges.gallery.children[-1];before=screen.collect_facelets()
    for _ in range(6):
        screen.btn_next.dispatch('on_release')
        assert screen._busy_turn and screen.view._whole_anim is not None
        stale.dispatch('on_release');assert screen.collect_facelets()==before
        screen.view._whole_anim_tick(.6)
        assert not screen._busy_turn
    assert screen._ori.current_face()=='F' and screen.collect_facelets()==before


def test_simple_input_also_uses_whole_piece_cards(editor):
    screen,app=editor(2);app.simple_input=True;screen.apply_input_mode(True)
    screen.on_cell(0,0,'F');panel=screen.penrose_edges
    assert screen.picker.disabled and screen.picker.height==0
    panel.gallery.children[-1].dispatch('on_release')
    assert sum(bool(c) for g in screen.collect_facelets().values() for row in g for c in row)==3
