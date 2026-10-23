from collections import Counter
from types import SimpleNamespace
import pytest
from cube.bandaged_cube import BandagedCube,KINDS,_FACE_PLATES
from cube.bandaged_entry import plates,steps,plate_shape,completed
from cube.coordinates import FACE_NORMALS


@pytest.mark.parametrize('kind',sorted(KINDS))
@pytest.mark.parametrize('scrambled',(False,True))
def test_inventory_partitions_each_physical_layout(kind,scrambled):
    cube=(BandagedCube.random_scramble(kind,18,73) if scrambled else BandagedCube.solved(kind))
    inventory=plates(cube)
    for face in FACE_NORMALS:
        cells=[cell for p in inventory if p.face==face for cell in p.cells]
        assert Counter(cells)==Counter((r,c) for r in range(cube.n) for c in range(cube.n))
    assert steps(cube)[:3]==('1×1','2×1','2×2')
    assert all(p.shape in steps(cube) for p in inventory)


@pytest.mark.parametrize('kind',tuple(_FACE_PLATES))
def test_bicube_and_cube_c_match_each_reference_face(kind):
    cube=BandagedCube.solved(kind)
    for face,rows in _FACE_PLATES[kind].items():
        expected={frozenset((r,c) for r in range(3) for c in range(3) if rows[r][c]==label)
                  for row in rows for label in row}
        actual={frozenset(p.cells) for p in plates(cube) if p.face==face}
        assert actual==expected,(kind,face,actual,expected)


def test_rotated_bars_and_extra_shapes_have_their_own_step():
    assert plate_shape(((0,0),(1,0)))==plate_shape(((0,0),(0,1)))=='2×1'
    assert plate_shape(((0,0),(0,1),(0,2)))=='3×1'
    assert plate_shape(((0,0),(0,1),(1,0)))=='other'
    assert '3×1' in steps(BandagedCube.solved('two_bar_cube'))


def test_colours_never_change_fixed_piece_boundaries():
    cube=BandagedCube.solved('bandaged_c');before=plates(cube)
    for cubie in cube.cubies.values():
        for normal in cubie.stickers:cubie.stickers[normal]='W'
    assert plates(cube)==before


def test_step_paint_fills_one_plate_and_rejects_wrong_shape(monkeypatch):
    import ui.screens.input_screen as entry
    cube=BandagedCube.solved('fused_cube')
    data={f:[['']*3 for _ in range(3)] for f in FACE_NORMALS}
    captured=[]
    fake=SimpleNamespace(_data=data,_n=lambda:3,view=SimpleNamespace(cube=cube),
        _bandage_step='2×2',msg=SimpleNamespace(text=''),_error_cells=set(),_valid=None,
        _commit_action=lambda a:captured.append(a),_refresh_view=lambda:None,
        _update_progress=lambda:None,_update_bandage_step=lambda **kw:None)
    plate=next(p for p in plates(cube) if p.face=='F' and p.shape=='2×2')
    entry.InputScreen._fill_cell(fake,'F',*plate.cells[0],'R')
    assert len(captured)==1 and len(captured[0])==4 and completed(plate,data)
    assert all(data['F'][r][c]=='R' for r,c in plate.cells)
    single=next(p for p in plates(cube) if p.face=='F' and p.shape=='1×1')
    entry.InputScreen._fill_cell(fake,'F',*single.cells[0],'G')
    assert len(captured)==1 and not completed(single,data)


def test_completed_singles_skip_absent_bar_step():
    import ui.screens.input_screen as entry
    from kivy.uix.boxlayout import BoxLayout
    cube=BandagedCube.solved('fused_cube')
    data={f:[['']*3 for _ in range(3)] for f in FACE_NORMALS}
    for p in plates(cube):
        if p.shape=='1×1':
            for r,c in p.cells:data[p.face][r][c]='W'
    fake=SimpleNamespace(view=SimpleNamespace(cube=cube),_data=data,
        _bandage_kind='fused_cube',_bandage_step='1×1',bandage_row=BoxLayout(),
        _select_bandage_step=lambda key:None)
    entry.InputScreen._update_bandage_step(fake,advance=True)
    assert fake._bandage_step=='2×2'
    assert len(fake.bandage_row.children)==3


def test_fill_button_only_paints_current_size():
    import ui.screens.input_screen as entry
    cube=BandagedCube.solved('fused_cube')
    data={f:[['']*3 for _ in range(3)] for f in FACE_NORMALS};actions=[]
    fake=SimpleNamespace(_busy_turn=False,_ori=SimpleNamespace(current_face=lambda:'F'),
        picker=SimpleNamespace(current_color='G'),_n=lambda:3,_data=data,
        view=SimpleNamespace(cube=cube),_bandage_step='1×1',_error_cells=set(),
        _commit_action=lambda a:actions.append(a),_refresh_view=lambda:None,
        _update_bandage_step=lambda **kw:None,_update_progress=lambda:None,
        msg=SimpleNamespace(text=''))
    entry.InputScreen.fill_face(fake)
    assert len(actions)==1 and len(actions[0])==5
    for p in plates(cube):
        if p.face=='F':assert completed(p,data)==(p.shape=='1×1')



def make_placement_entry(monkeypatch):
    import ui.screens.input_screen as entry
    from kivy.uix.boxlayout import BoxLayout
    cube=BandagedCube.solved('bandaged_c')
    data={f:[['']*3 for _ in range(3)] for f in FACE_NORMALS}
    fake=SimpleNamespace(_entry_layout_cube=cube,view=SimpleNamespace(cube=cube),
        _bandage_mode='place',_bandage_step='1×1',_bandage_kind='bandaged_c',
        _bandage_connections=set(),_data=data,_history=[],_redo=[],_error_cells=set(),
        _bandage_rotation=0,_bandage_pending=None,_n=lambda:3,
        picker=SimpleNamespace(current_color='G'),bandage_row=BoxLayout(),
        _refresh_view=lambda:None,_update_progress=lambda:None,
        _update_edit_buttons=lambda:None,_select_bandage_step=lambda key:None,
        msg=SimpleNamespace(text=''),entry_can_edit=lambda:True)
    fake._update_bandage_step=lambda **kw:entry.InputScreen._update_bandage_step(fake,**kw)
    fake._bandage_candidate=lambda:entry.InputScreen._bandage_candidate(fake)
    monkeypatch.setattr(entry,'_app',lambda:SimpleNamespace(polyhedral_solution=None))
    return fake


def test_placement_fills_and_connects_atomically_and_undoes(monkeypatch):
    import ui.screens.input_screen as entry
    fake=make_placement_entry(monkeypatch);cube=fake._entry_layout_cube;original=cube.groups
    for shape in steps(cube):
        for p in plates(cube):
            if p.shape!=shape:continue
            fake._bandage_step=shape;fake._bandage_pending=(p.face,*p.cells[0])
            fake._bandage_rotation=1 if len({r for r,c in p.cells})>len({c for r,c in p.cells}) else 0
            entry.InputScreen._place_bandage_plate(fake,*fake._bandage_pending)
    assert len(fake._bandage_connections)==len(plates(cube))
    assert all(completed(p,fake._data) for p in plates(cube))
    assert cube.groups==original
    entry.InputScreen.undo(fake)
    assert len(fake._bandage_connections)==len(plates(cube))-1
    assert not all(completed(p,fake._data) for p in plates(cube))
    entry.InputScreen.redo(fake)
    assert all(completed(p,fake._data) for p in plates(cube))
    assert cube.groups==original


@pytest.mark.parametrize('rotation,expected',[(0,((1,1),(1,2))),(1,((1,1),(2,1))),
 (2,((1,0),(1,1))),(3,((0,1),(1,1)))])
def test_block_rotates_about_clicked_cell_centre(rotation,expected):
    from cube.bandaged_entry import rotated_cells
    assert rotated_cells(1,1,'2×1',rotation)==expected


def test_new_plate_never_overwrites_colours(monkeypatch):
    import ui.screens.input_screen as entry
    fake=make_placement_entry(monkeypatch)
    p=next(p for p in plates(fake._entry_layout_cube) if p.face=='F' and p.shape=='2×2')
    fake._bandage_step='2×2';fake._bandage_pending=('F',*p.cells[0])
    r,c=p.cells[-1];fake._data['F'][r][c]='R'
    entry.InputScreen._place_bandage_plate(fake,*fake._bandage_pending)
    assert fake._data['F'][r][c]=='R'
    assert len(fake._history)==0 and not fake._bandage_connections
    assert sum(bool(c) for row in fake._data['F'] for c in row)==1


def test_tapping_only_previews_until_confirmed(monkeypatch):
    import ui.screens.input_screen as entry
    fake=make_placement_entry(monkeypatch)
    p=next(p for p in plates(fake._entry_layout_cube) if p.face=='F' and p.shape=='2×2')
    fake._bandage_step='2×2'
    entry.InputScreen._fill_cell(fake,'F',*p.cells[0],'G')
    assert fake._bandage_pending==('F',*p.cells[0])
    assert not fake._history and not fake._bandage_connections
    assert not any(c for grid in fake._data.values() for row in grid for c in row)


def test_square_also_rotates_around_pivot_instead_of_its_own_centre():
    from cube.bandaged_entry import rotated_cells
    assert rotated_cells(1,1,'2×2',1)==((1,0),(1,1),(2,0),(2,1))
    assert rotated_cells(1,1,'2×2',2)==((0,0),(0,1),(1,0),(1,1))


def test_outside_is_rejected_but_scrambled_plate_positions_are_editable(monkeypatch):
    import ui.screens.input_screen as entry
    fake=make_placement_entry(monkeypatch)
    fake._bandage_step='2×2';fake._bandage_pending=('F',2,2)
    entry.InputScreen._place_bandage_plate(fake,*fake._bandage_pending)
    assert not fake._history and not fake._bandage_connections
    fake._bandage_pending=('F',1,1)
    entry.InputScreen._place_bandage_plate(fake,*fake._bandage_pending)
    assert len(fake._history)==1 and ('F',((1,1),(1,2),(2,1),(2,2))) in fake._bandage_connections


@pytest.mark.parametrize('kind',sorted(KINDS))
@pytest.mark.parametrize('seed',(12,73,125))
def test_manual_colours_and_seams_reconstruct_scrambled_rigid_groups(kind,seed):
    from cube.bandaged_entry import reconstruct
    from cube.conversion import cubies_to_facelets
    from cube.appearance import frame_for,transform_frame
    source=BandagedCube.random_scramble(kind,30,seed)
    data=cubies_to_facelets(source.cubies,source.n)
    seams={(p.face,p.cells) for p in plates(source)}
    work=reconstruct(kind,data,seams)
    assert not work.history
    assert cubies_to_facelets(work.cubies,work.n)==data
    assert {(p.face,p.cells) for p in plates(work)}==seams
    assert len({p.home for p in work.cubies.values()})==len(work.cubies)
    for pos,piece in work.cubies.items():assert transform_frame(frame_for(piece),piece.home)==pos
    for move in ('R','L','U','D','F','B','r','u','f'):
        if work.n==3 and move.islower():continue
        def allowed(cube):
            try:cube.clone().apply_move(move);return True
            except ValueError:return False
        assert allowed(work)==allowed(source),(kind,seed,move)


def test_complete_colours_without_seams_are_not_committed():
    from cube.bandaged_entry import reconstruct
    from cube.conversion import cubies_to_facelets
    cube=BandagedCube.solved('bicube')
    with pytest.raises(ValueError,match='entry_incomplete'):
        reconstruct('bicube',cubies_to_facelets(cube.cubies,3),set())


def test_scene_cache_includes_confirmed_bonds():
    from renderer.variant_scene import build_variant_scene
    cube=BandagedCube.solved('bandaged_c')
    bonded=build_variant_scene(cube)[2]
    cube.groups=()
    grid=build_variant_scene(cube)[2]
    assert grid!=bonded
    assert all(edges==(0,1,2,3) for pos,face,edges in grid)


@pytest.mark.parametrize('kind',('bandaged_c',None))
def test_check_distinguishes_rigid_matching_from_standard_reachability(monkeypatch,kind):
    import ui.screens.input_screen as entry
    from cube.cube3 import Cube3
    from cube.conversion import cubies_to_facelets
    cube=BandagedCube.solved(kind) if kind else Cube3.solved()
    data=cubies_to_facelets(cube.cubies,3)
    app=SimpleNamespace(puzzle_kind=kind,theme=SimpleNamespace(accent=(0,1,0,1),danger=(1,0,0,1)))
    monkeypatch.setattr(entry,'_app',lambda:app)
    fake=SimpleNamespace(collect_facelets=lambda:data,_n=lambda:3,_penrose=lambda:False,
        _error_cells=set(),entry_can_edit=lambda:True,_refresh_view=lambda:None,
        _bandage_connections={(p.face,p.cells) for p in plates(cube)} if kind else set(),
        msg=SimpleNamespace(text='',color=None))
    entry.InputScreen.check(fake)
    assert fake._valid
    assert fake.msg.text==entry.tr('bandage.entry_checked' if kind else 'input.valid')
