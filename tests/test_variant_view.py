"""Check the actual surface picker and the input/twist/playback state bridge."""
from types import SimpleNamespace

import pytest

pytest.importorskip('kivy')

from cube.appearance import VARIANTS, PENROSE_RGB, kind_for, with_appearance
from cube.bandaged_cube import BandagedCube, KINDS
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.conversion import cubies_to_facelets
from cube.coordinates import rc_from_pos
from renderer.cube_view import CubeView


def make(kind):
    if kind in KINDS:return BandagedCube.solved(kind)
    n=int(kind.rsplit('_',1)[1])
    return with_appearance({2:Cube2,3:Cube3,4:Cube4}[n].solved(),kind)


@pytest.mark.parametrize('kind',sorted(VARIANTS))
def test_pick_uses_rendered_strips_curves_and_arcs(kind):
    cube=make(kind)
    view=CubeView(size=(480,480),size_hint=(None,None))
    view.camera.elevation=0
    view.camera.azimuth=0
    view.set_cube(cube)
    targets={}
    for quad,pos,face in view._last_quads:
        if face!='F':continue
        a,b,c=quad[:3]
        area=abs((b['x']-a['x'])*(c['y']-a['y'])-(b['y']-a['y'])*(c['x']-a['x']))
        if pos not in targets or area>targets[pos][0]:targets[pos]=(area,quad)
    assert len(targets)==cube.n**2
    for pos,(_area,quad) in targets.items():
        # A triangle's centroid lies strictly inside it, even when a fan
        # patch uses a repeated fourth vertex at the circle's centre.
        x=sum(p['x'] for p in quad[:3])/3
        y=sum(p['y'] for p in quad[:3])/3
        assert view.pick_facelet(x,y)==(pos,'F')
        assert view.pick_cell('F',cube.n,x,y)==rc_from_pos(cube.n,'F',pos)


@pytest.mark.parametrize('kind',sorted(VARIANTS))
def test_input_rebuild_preserves_saved_exterior_and_piece_frames(monkeypatch,kind):
    import ui.screens.input_screen as entry
    cube=make(kind)
    move='L' if kind=='camouflage_3' else None
    if move:cube.apply_move(move)
    app=SimpleNamespace(cube=cube,n=cube.n,puzzle_kind=kind)
    monkeypatch.setattr(entry,'_app',lambda:app)
    facelets=cubies_to_facelets(cube.cubies,cube.n)
    rebuilt=entry._build_partial_cube(facelets,cube.n)
    assert kind_for(rebuilt)==kind
    assert rebuilt is not cube
    assert {c.home:c.appearance_frame for c in rebuilt.cubies.values()}=={
        c.home:c.appearance_frame for c in cube.cubies.values()}
    assert kind_for(entry._new_solved_cube(cube.n))==kind


@pytest.mark.parametrize('kind',('penrose_2','penrose_3','circle_2'))
def test_solve_commit_does_not_reset_variant_to_ordinary_cube(monkeypatch,kind):
    import ui.screens.input_screen as entry
    cube=make(kind)
    app=SimpleNamespace(cube=cube,n=cube.n,puzzle_kind=kind)
    def set_cube(cubies,n):
        app.cube={2:Cube2,3:Cube3}[n](cubies)
        app.puzzle_kind='cube'
    app.set_cube=set_cube
    monkeypatch.setattr(entry,'_app',lambda:app)
    facelets=cubies_to_facelets(cube.cubies,cube.n)
    # Use fresh input so the commit must go through the reconstruction path.
    app.cube=None
    entry.InputScreen._commit_cube(SimpleNamespace(_n=lambda:cube.n),facelets)
    assert app.puzzle_kind==kind
    assert kind_for(app.cube)==kind
    assert kind_for(app.cube.clone())==kind


def test_penrose_palette_can_restore_normal_cube_colours():
    from ui.widgets.color_picker import ColorSelector
    from app.constants import COLOR_INFO
    picker=ColorSelector()
    picker.set_palette(PENROSE_RGB,{'W':'U'})
    assert tuple(picker._buttons['W']._fill_ctx.rgba)==pytest.approx(PENROSE_RGB['W'])
    assert picker._buttons['W'].text=='U'
    picker.set_palette()
    assert tuple(picker._buttons['W']._fill_ctx.rgba)==pytest.approx(COLOR_INFO['W'][1])
    assert picker._buttons['W'].text=='W'


@pytest.mark.parametrize('kind',sorted(VARIANTS))
def test_painting_changes_colour_without_rebuilding_the_physical_shell(monkeypatch,kind):
    import ui.screens.input_screen as entry
    from renderer.variant_scene import build_variant_scene
    cube=make(kind)
    app=SimpleNamespace(cube=cube,n=cube.n,puzzle_kind=kind)
    monkeypatch.setattr(entry,'_app',lambda:app)
    facelets=cubies_to_facelets(cube.cubies,cube.n)
    before=build_variant_scene(cube)
    facelets['F'][0][0]='W'
    rebuilt=entry._build_partial_cube(facelets,cube.n)
    after=build_variant_scene(rebuilt)
    assert before[1:]==after[1:]
    assert [tuple(before[0][i:i+3]) for i in range(0,len(before[0]),7)]==[
        tuple(after[0][i:i+3]) for i in range(0,len(after[0]),7)]


def test_a_continuous_fused_plate_is_coloured_and_undone_as_one_action():
    import ui.screens.input_screen as entry
    cube=make('fused_cube')
    facelets=cubies_to_facelets(cube.cubies,3)
    facelets['F']=[['']*3 for _ in range(3)]
    captured=[]
    fake=SimpleNamespace(_data=facelets,_n=lambda:3,
                         view=SimpleNamespace(cube=cube),
                         _error_cells=set(),_valid=True,
                         _commit_action=lambda action:captured.append(action),
                         _refresh_view=lambda:None,_update_progress=lambda:None)
    entry.InputScreen._fill_cell(fake,'F',0,2,'W')
    assert len(captured)==1 and len(captured[0])==4
    assert sum(c=='W' for row in facelets['F'] for c in row)==4
