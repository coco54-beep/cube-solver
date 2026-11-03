"""Burr's physical bonds come from the selected pCubes model."""
from itertools import product
from pathlib import Path
import re
import json
import pytest
from cube.bandaged_cube import BandagedCube
from cube.coordinates import FACE_NORMALS


def reference_groups():
    path=Path(__file__).resolve().parents[1]/'bin/pCubes/Puzzles/Cubic/Bandaged/Bandaged-4/Burr.xml'
    if not path.exists():pytest.skip('Local pCubes reference is not installed')
    text=path.read_text(encoding='utf-8-sig');groups=[]
    for dimensions,starts in re.findall(r"ParseTxt\('([0-9]{3})=([^']+)'\)",text):
        for start in starts.replace(' ','').split(','):
            coords=tuple(int(c) for c in start)
            group=[]
            for dx,dy,dz in product(*(range(int(c)) for c in dimensions)):
                x,y,z=(2*(v+d)-3 for v,d in zip(coords,(dx,dy,dz)))
                group.append((-x,z,y))
            groups.append(frozenset(group))
    return tuple(groups)


def test_all_28_reference_bricks_cover_exactly_the_visible_4x4_shell():
    cube=BandagedCube.solved('burr_cube');expected=reference_groups()
    assert set(cube.groups)==set(expected)
    cells=[p for group in expected for p in group]
    assert len(expected)==28 and all(len(g)==2 for g in expected)
    assert len(cells)==len(set(cells))==56 and set(cells)==set(cube.cubies)
    # Proper coordinate rotation: source red -X, green +Y and white +Z.
    def mapped(v):x,y,z=v;return (-x,z,y)
    assert mapped((-1,0,0))==FACE_NORMALS['R']
    assert mapped((0,1,0))==FACE_NORMALS['F']
    assert mapped((0,0,1))==FACE_NORMALS['U']


@pytest.mark.parametrize('seed',range(6))
def test_scrambled_cut_legality_uses_the_reference_bonds_on_every_axis(seed):
    cube=BandagedCube.random_scramble('burr_cube',100,seed)
    for axis in range(3):
        for flags in product((False,True),repeat=4):
            selected={v for v,flag in zip((-3,-1,1,3),flags) if flag}
            expected=True
            for group in reference_groups():
                positions={cube.cubies_by_home(home).pos[axis] for home in group}
                if positions & selected and not positions<=selected:expected=False;break
            assert cube.can_turn(axis,selected)==expected


def test_saved_burr_layout_is_versioned_and_old_layout_is_not_silently_reused():
    from app.session import encode,decode
    cube=BandagedCube.random_scramble('burr_cube',40,701)
    data=json.loads(json.dumps(encode(cube)))
    restored=decode(data)
    assert restored.groups==cube.groups
    assert {c.home:(c.pos,c.stickers) for c in restored.cubies.values()}=={
        c.home:(c.pos,c.stickers) for c in cube.cubies.values()}
    data['v'].pop('layout_version')
    with pytest.raises(ValueError,match='obsolete bond'):decode(data)


def test_complete_solver_assets_are_bound_to_the_new_reference_layout():
    from solver.bandaged_reduction import assets,geometry
    header,blob,group=assets('burr_cube')
    assert header['layout_version']==group['layout_version']==2
    assert header['geometry']==group['geometry']==geometry('burr_cube').grid.fingerprint
    assert header['count']==182070 and header['edges']==1294884
    assert group['verified_transversals']==178
