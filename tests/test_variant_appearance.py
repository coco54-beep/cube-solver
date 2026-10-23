"""Exterior regression checks independent of a window or graphics driver."""
import math

import pytest

from cube.appearance import VARIANTS, kind_for, with_appearance
from cube.bandaged_cube import BandagedCube, KINDS
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube4 import Cube4
from cube.coordinates import FACE_NORMALS, TURNS, get_d_maxc
from renderer.mat4 import Mat4
from renderer.variant_scene import build_variant_scene


def make(kind):
    if kind in KINDS:
        return BandagedCube.solved(kind)
    n=int(kind.rsplit('_',1)[1])
    return with_appearance({2:Cube2,3:Cube3,4:Cube4}[n].solved(),kind)


@pytest.mark.parametrize('kind',sorted(VARIANTS))
def test_all_exteriors_are_finite_pickable_quads(kind):
    cube=make(kind)
    vertices,indices,infos=build_variant_scene(cube)
    assert vertices and len(vertices)==len(infos)*28
    assert len(indices)==len(infos)*6
    assert all(math.isfinite(v) for v in vertices)
    assert max(indices)<len(vertices)//7
    assert {face for _pos,face,_edges in infos if face is not None}==set(FACE_NORMALS)
    for pos,face,edges in infos:
        assert pos in cube.cubies
        assert face is None or FACE_NORMALS[face] in cube.cubies[pos].stickers
        assert all(0<=edge<4 for edge in edges)


def test_fused_corner_has_continuous_plates_instead_of_internal_grid():
    cube=make('fused_cube')
    _vertices,_indices,infos=build_variant_scene(cube)
    assert len(infos)==54  # Picking still distinguishes every logical facelet.
    assert sum(4-len(edges) for _pos,_face,edges in infos)==24


def test_burr_bricks_partition_the_shell_and_differ_from_ai_octants():
    burr=make('burr_cube')
    members=[home for group in burr.groups for home in group]
    assert len(members)==len(set(members))==56
    assert set(members)==set(burr.cubies)
    assert len(burr.groups)==28
    assert all(len(group)==2 for group in burr.groups)
    assert len(make('ai_cube').groups)==4


@pytest.mark.parametrize('kind', sorted(KINDS))
def test_exterior_presets_can_scramble_and_rewind_without_splitting_a_piece(kind):
    from solver.bandaged_cube import solve_bandaged_cube
    cube=BandagedCube.random_scramble(kind,length=18,seed=73)
    assert len(cube.history)==18
    if cube.n==4:
        assert any(move[0].islower() for move in cube.history)
    moves=solve_bandaged_cube(cube)
    cube.apply_moves(moves)
    assert cube.is_solved()


@pytest.mark.parametrize('kind', sorted(KINDS))
def test_whole_rotation_suffixes_preserve_shell_orientation(kind):
    cube=make(kind)
    before=build_variant_scene(cube)
    cube.apply_moves(['x', "x'", 'y2', 'y2', 'z', "z'"])
    assert build_variant_scene(cube)==before


def _piece_surfaces(cube,scene):
    vertices,_indices,infos=scene
    surfaces={}
    for i,(pos,face,_edges) in enumerate(infos):
        if face is None:continue
        cubie=cube.cubies[pos]
        label=cubie.stickers[FACE_NORMALS[face]]
        key=(cubie.home,label)
        points=surfaces.setdefault(key,set())
        for j in range(4):
            start=i*28+j*7
            points.add(tuple(round(v,7) for v in vertices[start:start+3]))
    return surfaces


@pytest.mark.parametrize('kind',('penrose_2','penrose_3','penrose_4','camouflage_3'))
def test_curved_and_unequal_pieces_move_rigidly_with_their_facelets(kind):
    cube=make(kind)
    before=_piece_surfaces(cube,build_variant_scene(cube))
    _d,maxc=get_d_maxc(cube.n)
    # Camouflage's provisional constraints block R; use a legal free face.
    move='L' if kind=='camouflage_3' else 'R'
    turn_axis=0
    layer=-maxc if move=='L' else maxc
    cube.apply_move(move)
    after=_piece_surfaces(cube,build_variant_scene(cube))
    assert before.keys()==after.keys()
    for key,points in before.items():
        if key[0][turn_axis]==layer:
            points={tuple(round(v,7) for v in TURNS[move](*p)) for p in points}
        assert points==after[key]


def test_animation_transform_does_not_change_geometry_or_reintroduce_seams():
    cube=make('fused_cube')
    base,base_indices,base_info=build_variant_scene(cube)
    rotation=Mat4.rotation_axis(37,(1,0,0))
    moving={pos for pos in cube.cubies if pos[0]<0}
    animated,indices,infos=build_variant_scene(cube,moving,rotation)
    assert base_info==infos and base_indices==indices
    for i,(pos,_face,_edges) in enumerate(infos):
        for j in range(4):
            start=i*28+j*7
            expected=tuple(base[start:start+3])
            if pos in moving: expected=rotation.transform(*expected)
            assert tuple(animated[start:start+3])==pytest.approx(expected)


def test_cached_curves_are_reused_without_allowing_caller_mutation():
    cube=make('penrose_3')
    first=build_variant_scene(cube)
    cache=cube._appearance_scene_cache
    original=first[0][0]
    first[0][0]=999
    second=build_variant_scene(cube)
    assert cube._appearance_scene_cache is cache
    assert second[0][0]==original
    cube.apply_move('R')
    build_variant_scene(cube)
    assert cube._appearance_scene_cache is not cache


@pytest.mark.parametrize('kind',('penrose_2','penrose_3','penrose_4'))
def test_ordinary_engine_variants_keep_exterior_after_clone_and_session_restore(kind):
    from app.session import encode,decode
    cube=make(kind)
    cube.apply_move('R')
    clone=cube.clone()
    restored=decode(encode(clone))
    assert kind_for(clone)==kind_for(restored)==kind
    assert build_variant_scene(restored)==build_variant_scene(cube)


def test_circle2_geometry_clone_and_session_roundtrip():
    from app.session import encode, decode
    from cube.circle_cube import Circle2Cube
    cube = Circle2Cube()
    assert len(cube.geometry.stickers) == 48
    assert all(sticker.patches for sticker in cube.geometry.stickers if sticker.face >= 0)
    from cube.polyhedral import Move
    cube.apply_move(Move(0, 0, 1))
    clone = cube.clone()
    restored = decode(encode(clone))
    assert type(restored) is Circle2Cube
    assert restored.colors == clone.colors
    assert restored.anchor == clone.anchor


@pytest.mark.parametrize('kind', sorted(VARIANTS))
def test_all_visible_patches_have_outward_winding(kind):
    vertices,_indices,infos=build_variant_scene(make(kind))
    for i,(_pos,face,_edges) in enumerate(infos):
        if face is None:continue
        pts=[vertices[i*28+j*7:i*28+j*7+3] for j in range(3)]
        a=[pts[1][j]-pts[0][j] for j in range(3)]
        b=[pts[2][j]-pts[0][j] for j in range(3)]
        cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        assert sum(x*y for x,y in zip(cross,FACE_NORMALS[face]))>0
