"""Reference bonds and history-free input of the replacement BiCube."""
from itertools import product
from pathlib import Path
import json
import re
import pytest
from cube.bandaged_cube import BandagedCube
from cube.bandaged_entry import plates, reconstruct
from cube.conversion import cubies_to_facelets
from solver.bandaged_cube import solve_bandaged_cube


def test_bicube_bonds_match_local_xml_including_the_large_brick():
    path=Path(__file__).resolve().parents[1]/'bin/pCubes/Puzzles/Cubic/Bandaged/Bandaged-3/Bicube.xml'
    if not path.exists():pytest.skip('Local pCubes reference is not installed')
    cube=BandagedCube.solved('bicube');expected=[]
    for dims,starts in re.findall(r"ParseTxt\('([0-9]{3})=([^']+)'\)",path.read_text(encoding='utf-8-sig')):
        for start in starts.replace(' ','').split(','):
            points=[]
            for delta in product(*(range(int(v)) for v in dims)):
                x,y,z=(int(v)+d-1 for v,d in zip(start,delta))
                if max(abs(x),abs(y),abs(z))==1:points.append((-x,z,y))
            if len(points)>1:expected.append(frozenset(points))
    assert set(cube.groups)==set(expected)
    assert sorted(map(len,cube.groups))==[2]*9+[7]
    from solver.bandaged_reduction import assets,geometry
    header,_,group=assets('bicube')
    assert header['geometry']==group['geometry']==geometry('bicube').grid.fingerprint
    assert (header['count'],header['edges'])==(121,504)


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('seed',range(4))
def test_bicube_reentered_from_colours_and_seams_solves(length,seed):
    source=BandagedCube.random_scramble('bicube',length,20261102+seed)
    source.apply_moves(('x','y','z')[:seed%4])
    facelets=cubies_to_facelets(source.cubies,3)
    cube=reconstruct('bicube',facelets,{(p.face,p.cells) for p in plates(source)})
    assert not cube.history
    word=solve_bandaged_cube(cube)
    assert cubies_to_facelets(cube.cubies,3)==facelets
    cube.apply_moves(word);assert cube.is_solved()


def test_bicube_rejects_the_previous_layout_checkpoint():
    from app.session import encode,decode
    source=BandagedCube.random_scramble('bicube',30,12)
    data=json.loads(json.dumps(encode(source)))
    cube=decode(data)
    assert cube.groups==source.groups
    data['v']['layout_version']=2
    with pytest.raises(ValueError,match='obsolete bond'):decode(data)
