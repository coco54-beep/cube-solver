"""Independent shell/cut checks for the second local-reference audit."""
from collections import Counter
from itertools import permutations,product
from pathlib import Path
import math
import random
import re
import threading
import pytest
from cube.polyhedral import (geometry,Spec,CUBE,DODECA,body,_cut_skin,key,
                             dot,cross,rotate,Move,PolyhedralPuzzle)


def polygon(poly):return tuple(sorted(key(v) for v in poly))


def test_masterball_planes_and_all_physical_turns():
    g=geometry('masterball',4)
    levels={round(p[1],8) for s in g.stickers for p in s.polygon
            if abs(abs(p[1])-.55)<1e-7 or abs(p[1])<1e-7}
    assert levels=={-.55,0.,.55}
    for axis,rows in enumerate(g.permutations):
        for perm in rows:
            angle=2*math.pi/g.spec.order(axis)
            for i,j in enumerate(perm):
                if i==j:continue
                a={polygon(tuple(rotate(v,g.spec.axes[axis],angle) for v in p))
                   for p in g.stickers[i].patches}
                assert a=={polygon(p) for p in g.stickers[j].patches}


@pytest.mark.parametrize('kind,cuts',[
    ('pyraminx_crystal',(1/math.sqrt(5),)),('pentultimate',(0.,)),
    ('master_pentultimate',(.06/(.7*math.sqrt((5+2*math.sqrt(5))/15)),)),
    ('master_brilic',(1/math.sqrt(5),(3+4*math.sqrt((5-2*math.sqrt(5))/(5+2*math.sqrt(5))))/5)),
    ('starminx_i',(math.sqrt((5-2*math.sqrt(5))/(5+2*math.sqrt(5))),)),
])
def test_deep_minx_reference_cut_polygons(kind,cuts):
    g=geometry(kind,3)
    reference=_cut_skin(Spec('reference',3,DODECA,DODECA,cuts,5))
    assert Counter((f,polygon(p)) for _,f,p in reference)==Counter((s.face,polygon(s.polygon)) for s in g.stickers)


def test_rediminx_raised_shell_all_twenty_turns_and_outward_shading():
    from cube.rediminx import skin
    g=geometry('rediminx',3)
    assert len(g.pieces)==62 and len(g.stickers)==132
    assert max(dot(v,g.spec.normals[s.face]) for s in g.stickers for p in s.patches for v in p)==pytest.approx(1.15)
    for s,patches in zip(g.stickers,skin()):
        assert all(dot(normal,g.spec.normals[s.face])>0 for _,normal,_ in patches)
    for axis,rows in enumerate(g.permutations):
        for perm in rows:
            for i,j in enumerate(perm):
                if i!=j:
                    assert Counter(polygon(tuple(rotate(v,g.spec.axes[axis],2*math.pi/3) for v in p))
                                   for p in g.stickers[i].patches)==Counter(polygon(p) for p in g.stickers[j].patches)
    from solver.expanded_polyhedra import prepared_chain
    assert prepared_chain(PolyhedralPuzzle('rediminx',3)) is not None


def test_container_shell_matches_independent_plane_arrangement():
    from cube.container import piece_faces
    from cube.fisher_skewb import SHELL_NORMALS
    core=geometry('skewb',3)
    bounds=tuple(math.sqrt(2) if abs(n[1])>.9 else 1. for n in SHELL_NORMALS)
    spec=Spec('reference',3,SHELL_NORMALS,core.spec.axes,(0.,),3,
              axis_steps=(1,)*len(core.spec.axes),bounds=bounds)
    expected=Counter((face,polygon(p)) for _,face,p in _cut_skin(spec))
    actual=Counter((face,polygon(p)) for home in range(len(core.pieces))
                   for p,face in piece_faces(home) if face>=0)
    assert actual==expected


@pytest.mark.parametrize('kind,filename',[
    ('i_cube','I-Cube.xml'),('l_cube','L-Cube.xml'),('t_cube','T-Cube.xml'),
    ('x_cube','X-Cube.xml'),('tri_cube','Trio Cube.xml'),
    ('temple_cube','Temple Cube.xml'),('cross_cube','Cross Cube.xml')])
def test_letter_extension_topology_matches_reference_up_to_rotation(kind,filename):
    from cube.letter_cube import EXTENSIONS,letter_layout
    path=Path(__file__).resolve().parents[1]/'bin/pCubes/Puzzles/Cubic/Cross/3x3x3'/filename
    if not path.exists():pytest.skip('Local reference library is not installed')
    text=path.read_text(encoding='utf-8-sig')
    faces=((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1))
    source={faces[int(i)] for i in re.findall(r'<ExecMacro MacroName = "AddSide" i = "(\d)"',text)}
    if filename=='Cross Cube.xml':
        assert text.count('<LoadFrom File = "Figures\\Cuboid.xml"')==3
        source=set(faces)
    target={CUBE[f] for f in EXTENSIONS[kind]}
    matrices=(tuple(tuple(signs[i]*int(j==order[i]) for j in range(3)) for i in range(3))
              for order in permutations(range(3)) for signs in product((-1,1),repeat=3))
    assert any(dot(m[0],cross(m[1],m[2]))>0 and
               {tuple(dot(row,v) for row in m) for v in source}==target for m in matrices)
    cells,boxes,*_=letter_layout(kind)
    assert len(cells)==27+8*len(source)
    assert len({p for group in cells for p in group})==27+9*len(source)


@pytest.mark.parametrize('kind',('fused_cube','two_bar_cube','bandaged_c','bicube','ai_cube','burr_cube'))
def test_bandaged_all_selection_masks_against_rigid_piece_extent(kind):
    from cube.bandaged_cube import BandagedCube
    c=BandagedCube.random_scramble(kind,100,20261101)
    for axis in range(3):
        values=sorted({p[axis] for p in c.cubies})
        for flags in product((False,True),repeat=len(values)):
            layers={v for v,flag in zip(values,flags) if flag}
            expected=all(not positions.intersection(layers) or positions<=layers
                         for group in c.groups
                         for positions in [{c.cubies_by_home(h).pos[axis] for h in group}])
            assert c.can_turn(axis,layers)==expected


@pytest.mark.parametrize('kind',('i_cube','l_cube','t_cube','x_cube','tri_cube','temple_cube','cross_cube',
                               'cuboid_224','cuboid_335','cuboid_446','cuboid_234',
                               'cuboid_332','cuboid_223','cuboid_334','cuboid_442','cuboid_133','camouflage_3'))
def test_extension_and_cuboid_scrambles_preserve_volume_and_inverse(kind):
    from cube.cuboid import CuboidCube,layout,transform
    c=CuboidCube.solved(kind);cells=layout(kind)[0];rng=random.Random(20261101)
    volume=sum(map(len,cells))
    for _ in range(100):
        moves=c.moves();assert moves
        move=rng.choice(moves);before=c.clone()
        c.apply_move(move)
        placed=[transform(frame,p) for frame,group in zip(c.frames,cells) for p in group]
        if kind=='cuboid_133':
            # Its thick logical columns are identity carriers; only the nine
            # actual thin solids occupy space, unlike a bandaged 3x3 grid.
            centres=c.geometry.centres
            assert len({key(p) for p in centres})==9
        else:assert len(set(placed))==volume
        undo=c.clone();undo.apply_move(move.inverse(4))
        assert undo.frames==before.frames and undo.colors==before.colors


def test_six_view_cancellation_and_preparation_budget_keep_draft():
    from cube.cuboid import CuboidCube
    from cube.cuboid_observation import SixViewDraft
    draft=SixViewDraft.from_cube(CuboidCube.solved('camouflage_3'));before=draft.state()
    token=threading.Event();token.set()
    assert draft.match(cancel=token).status=='cancelled'
    assert draft.match(seconds=0).status=='budget'
    assert draft.state()==before


def test_starminx_session_rejects_the_old_equal_sized_corner_layout():
    from app.session import encode,decode
    cube=PolyhedralPuzzle('starminx_i',3);saved=encode(cube)
    assert decode(saved).geometry.spec.turn_order==5
    saved['v'].pop('layout_version')
    with pytest.raises(ValueError,match='obsolete'):decode(saved)


@pytest.mark.parametrize('kind',('square1','square0','square2','super_square1'))
def test_square_reference_heights_and_every_closed_panel(kind):
    from cube.square1 import Square1Cube
    from cube.square_family import SquareFamilyCube
    from renderer.square1_view import surfaces
    from renderer.square_family_view import family_surfaces
    c=Square1Cube() if kind=='square1' else SquareFamilyCube.solved(kind)
    parts=surfaces(c) if kind=='square1' else family_surfaces(c)
    heights={round(p[1],6) for poly,normal,color,*_ in parts for p in poly
             if kind=='square1' or color==-1}
    expected={-1.,-.5,0.,.5,1.,-1.004,1.004} if kind=='super_square1' else {-1.,-round(1/3,6),round(1/3,6),1.}
    assert heights==expected


@pytest.mark.parametrize('kind',('square1','square0','square2','super_square1'))
def test_empty_square_entry_has_pickable_grey_scaffold_without_recording_blocks(kind):
    from cube.square1_entry import Square1Entry
    from cube.square_family_entry import SquareFamilyEntry
    from cube.square_family import SquareFamilyCube
    from renderer.square1_view import surfaces
    from renderer.square_family_view import family_surfaces
    draft=Square1Entry(empty=True) if kind=='square1' else SquareFamilyEntry(SquareFamilyCube.solved(kind),empty=True)
    parts=surfaces(draft) if kind=='square1' else family_surfaces(draft)
    visible={slot[0] for poly,normal,color,slot,*_ in parts if color==-2}
    assert visible==set(range(len(draft.slots)))
    assert not draft.blocks and draft.complete_count()==0
    draft.show_entry_scaffold=False
    parts=surfaces(draft) if kind=='square1' else family_surfaces(draft)
    assert not any(color==-2 for poly,normal,color,*_ in parts)
