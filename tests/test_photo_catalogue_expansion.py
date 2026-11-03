"""Current catalogue, physical face groups and observation-based photo entry."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from vision.scan_profiles import ScanProfile,SUPPORTED


def test_photo_categories_are_a_filtered_copy_of_the_current_catalogue():
    from ui.screens.irregular_directory_screen import PUZZLES,ORDERS
    from ui.widgets.photo_entry import photo_groups
    original=deepcopy(ORDERS);groups=photo_groups()
    assert [f for f,_ in groups]==[f for f in ('cube',)+PUZZLES if f in dict(groups)]
    assert ORDERS==original
    flat=[k for _,kinds in groups for k in kinds]
    assert len(flat)==len(set(flat)) and set(flat)=={'cube',*SUPPORTED}
    assert 'professor_pentagonal' in dict(groups)['pentagonal_family']
    assert 'pyraminx_crystal' in dict(groups)['megaminx']
    assert 'tangram' in dict(groups)['tangram_family']
    assert 'dogic_i' in dict(groups)['icosahedron']


def test_piece_direction_and_size_inputs_are_not_enabled_as_colour_only_photos():
    from ui.widgets.photo_entry import supported
    for kind,n in (('mixup_333',3),('mixup_plus_444',4),('tangram_extreme',3),
                   ('penrose_3',3),('mirror',3),('blanker',2),('camouflage_3',3),('masterball',4)):
        assert not supported(kind,n)


@pytest.mark.parametrize('kind',('cuboid_332','cuboid_223','cuboid_334'))
def test_fixed_cuboid_physical_panels_fill_all_virtual_slots(kind):
    from cube.cuboid import CuboidCube
    from cube.polyhedral_scramble import scramble
    cube=CuboidCube.solved(kind);scramble(cube,12,20261030)
    profile=ScanProfile(kind,cube.n);data=profile.from_cube(cube)
    entered=profile.apply(data,CuboidCube.solved(kind))
    aliases=[index for s in profile.surfaces for index in s.cell]
    assert sorted(aliases)==list(range(len(cube.colors)))
    assert len(profile.surfaces)<len(aliases)
    assert entered.colors==cube.colors and not entered.history
    partial=profile.blank();s=profile.surfaces[0];partial[profile.face_keys[s.face]][s.index]=2
    draft=profile.apply(partial,CuboidCube.solved(kind))
    assert all(draft.colors[i]==2 for i in s.cell)
    assert sum(c>=0 for c in draft.colors)==len(s.cell)


def test_tangram_photo_samples_are_observations_not_rigid_pose_numbers():
    from cube.articulated import ArticulatedCube
    from cube.articulated_observation import match_observations,ObservationDraft,polygon_key
    from cube.polyhedral import Move
    cube=ArticulatedCube('tangram');cube.apply_move(next(iter(cube.moves())))
    profile=ScanProfile('tangram',3)
    data=profile.from_cube(cube);draft=profile.observations(data)
    expected=ObservationDraft.from_cube(cube)
    def signature(d):return sorted((f,polygon_key(p['outline']),p['color']) for f,v in enumerate(d.views) for p in v)
    assert signature(draft)==signature(expected)
    assert profile.from_observations(draft.state())==data
    result=match_observations(draft,seconds=20.)
    assert result.status=='matched' and not result.cube.history
    assert profile.from_cube(result.cube)==data
    assert profile.from_cube(cube,set())==profile.blank()


def test_dogic_colour_count_and_pentagonal_palette_match_the_entry_models():
    assert len(ScanProfile('dogic_i',3).palette)==12
    assert len(ScanProfile('dogic_20',3).palette)==20
    assert len(ScanProfile('professor_pentagonal',5).palette)==7


def test_wrong_photo_model_or_malformed_face_is_rejected_before_modification():
    from cube.polyhedral import PolyhedralPuzzle
    profile=ScanProfile('pentagonal_prism',3);cube=PolyhedralPuzzle('pentagonal_domino',2)
    before=list(cube.colors)
    with pytest.raises(ValueError,match='camera.invalid_input'):profile.apply(profile.blank(),cube)
    assert cube.colors==before
    cube=PolyhedralPuzzle('pentagonal_prism',3);data=profile.blank();data[profile.face_keys[0]]=[]
    with pytest.raises(ValueError,match='camera.invalid_input'):profile.apply(data,cube)


@pytest.mark.parametrize('kind,n',(('tangram',3),('professor_pentagonal',5),('dogic_i',3),
                                 ('starminx_i',3),('cuboid_332',3),('super_ivy',3)))
def test_perspective_photo_with_soft_edges_and_calibrated_light(kind,n):
    import numpy as np
    from PIL import Image,ImageFilter
    from tools.audit_photo_entry import photo
    from vision.scan_profiles import detect_surface
    profile=ScanProfile(kind,n);face=profile.face_keys[0];world=profile.face_world(face)
    image,corners,expected=photo(profile,face,world)
    image=Image.fromarray(np.round(image.astype(float)*.84).astype('uint8')).filter(ImageFilter.GaussianBlur(.6))
    profile.palette=tuple(tuple(c*.84 for c in rgba[:3])+(1.,) for rgba in profile.palette)
    result=detect_surface(np.asarray(image),profile,face,world,controls=corners)
    assert result.values==expected


@pytest.mark.parametrize('kind,n',(('pentagonal_prism',3),('dogic_i',3),('cuboid_332',3),('tangram',3)))
def test_all_photographed_faces_reenter_a_scramble_then_production_solver_replays(kind,n):
    from tools.audit_photo_entry import photo
    from vision.scan_profiles import detect_surface
    from cube.polyhedral import PolyhedralPuzzle
    from cube.articulated import ArticulatedCube
    from cube.cuboid import CuboidCube
    from demo.expanded_support import scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    def model():
        if kind=='tangram':return ArticulatedCube(kind)
        if kind.startswith('cuboid_'):return CuboidCube.solved(kind)
        return PolyhedralPuzzle(kind,n)
    source=scramble(model(),20261101,3);profile=ScanProfile(kind,n)
    expected=profile.from_cube(source);data=profile.blank()
    for face in profile.face_keys:
        world=profile.face_world(face);image,corners,_=photo(profile,face,world,expected[face])
        result=detect_surface(image,profile,face,world,controls=corners)
        assert result.values==expected[face]
        data[face]=result.values
    if kind=='tangram':
        from cube.articulated_observation import match_observations
        matched=match_observations(profile.observations(data),seconds=20.)
        assert matched.status=='matched';entered=matched.cube
    else:entered=profile.apply(data,model())
    assert profile.from_cube(entered)==expected and not getattr(entered,'history',None)
    assert not getattr(entered,'scramble_history',None)
    clear();answers=[]
    SolveService()._run(entered.clone(),answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message
    replay=entered.clone()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved() and not getattr(entered,'history',None)
    clear()


def test_photo_menu_constructs_tangram_through_its_existing_family(monkeypatch):
    from kivy.app import App
    from ui.widgets import photo_entry as module
    from cube.articulated import ArticulatedCube
    calls=[];menus=[]
    app=SimpleNamespace(cube=None,n=3)
    def make(kind):calls.append(kind);app.cube=ArticulatedCube(kind)
    app.new_articulated=make
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    monkeypatch.setattr(module,'_choose',lambda title,entries,callback,**kw:menus.append((entries,callback)))
    monkeypatch.setattr(module,'open_existing',lambda screen,cube:calls.append(cube.puzzle_kind))
    module.choose_photo_puzzle(SimpleNamespace())
    assert 'tangram_family' in [v for label,v in menus[0][0]]
    menus[0][1]('tangram_family')
    assert calls==['tangram','tangram']


def test_photo_menu_ignores_duplicate_or_closed_option_releases(monkeypatch):
    from kivy.app import App
    from app.theme import Theme
    from ui.widgets.photo_entry import _choose
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:SimpleNamespace(theme=Theme())))
    calls=[];popup=_choose('Models',[('A','a'),('B','b')],calls.append)
    popup.photo_buttons['a'].dispatch('on_release')
    popup.photo_buttons['b'].dispatch('on_release')
    popup.dismiss(animation=False)
    assert calls==['a']


def test_tangram_photo_to_real_entry_and_back_keeps_partial_corrections(monkeypatch,tmp_path):
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager,Screen,NoTransition
    from app.theme import Theme
    from cube.articulated import ArticulatedCube
    from ui.screens.camera_screen import CameraScreen
    from ui.screens.articulated_screen import ArticulatedEntryScreen
    from kivy.clock import Clock
    app=SimpleNamespace(n=3,puzzle_kind='tangram',cube=ArticulatedCube('tangram'),theme=Theme(),
        user_data_dir=str(tmp_path),camera_recorded=set(),camera_observations=None,input_from_camera=False,
        polyhedral_solution=None,solve_result=None)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    camera=CameraScreen(name='CameraScreen');monkeypatch.setattr(camera,'_ensure_source',lambda:None)
    entry=ArticulatedEntryScreen(name='ArticulatedEntryScreen');manager=ScreenManager(transition=NoTransition())
    manager.add_widget(Screen(name='HomeScreen'));manager.add_widget(camera);manager.add_widget(entry)
    manager.current=camera.name
    for _ in range(3):Clock.tick()
    profile=camera._profile
    s,t=profile.surfaces[:2];camera._data[profile.face_keys[s.face]][s.index]=2
    camera.apply_to_input()
    assert manager.current==entry.name and entry._ao_dirty and entry._ao_applied is None
    assert sum(map(len,entry._ao_state['views']))==1
    assert app.cube.is_solved()  # Placeholder is never treated as the entered state.
    draft=entry._get_draft();draft.paint_samples(t.cell[0],(t.cell[1],),4);entry._ao_state=draft.state()
    entry.back()
    for _ in range(3):Clock.tick()
    assert manager.current==camera.name
    assert camera._data[profile.face_keys[t.face]][t.index]==4
    assert sum(c>=0 for face in camera._data.values() for c in face.values())==2
    pending=profile.surfaces[2]
    camera._data[profile.face_keys[pending.face]][pending.index]=5
    camera.on_enter()
    assert camera._data[profile.face_keys[pending.face]][pending.index]==5
    camera.on_leave();entry.reset_interaction()
