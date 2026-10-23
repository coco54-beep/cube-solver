"""Reject impossible visible inputs while preserving legal parity cases."""
import random

import pytest

from cube.conversion import cubies_to_facelets
from cube.coordinates import get_d_maxc,rc_from_pos,coord_values
from cube.cube2 import Cube2
from cube.cube3 import Cube3
from cube.cube_n import CubeN
from cube.validation import validate_2x2,validate_3x3,validate_4x4,validate_5x5
from cube.validation_n import validate_nxn


def solved(n):
    return Cube2.solved() if n==2 else Cube3.solved() if n==3 else CubeN.solved(n)


def validate(data,n):
    return ({2:validate_2x2,3:validate_3x3,4:validate_4x4,5:validate_5x5}[n](data)
            if n<=5 else validate_nxn(data,n))


def cells(n,position,faces):
    return [(face,*rc_from_pos(n,face,position)) for face in faces]


def cycle(data,locations):
    colours=[data[f][r][c] for f,r,c in locations]
    for (f,r,c),colour in zip(locations,colours[1:]+colours[:1]):data[f][r][c]=colour


@pytest.mark.parametrize('n',range(2,10))
def test_single_corner_twist_is_rejected(n):
    data=cubies_to_facelets(solved(n).cubies,n)
    _,m=get_d_maxc(n)
    cycle(data,cells(n,(m,m,m),('R','U','F')))
    assert any('扭转' in e for e in validate(data,n))


@pytest.mark.parametrize('n',range(2,10))
def test_mirrored_corner_is_rejected_even_when_ud_colour_stays_on_top(n):
    data=cubies_to_facelets(solved(n).cubies,n)
    _,m=get_d_maxc(n)
    cycle(data,cells(n,(m,m,m),('R','F')))
    assert any('镜像' in e for e in validate(data,n))


@pytest.mark.parametrize('n',range(4,10))
def test_single_wing_flip_is_rejected(n):
    data=cubies_to_facelets(solved(n).cubies,n)
    _,m=get_d_maxc(n)
    inner=next(v for v in coord_values(n) if 0<v<m)
    cycle(data,cells(n,(m,m,inner),('R','U')))
    assert any('棱翼' in e for e in validate(data,n))


@pytest.mark.parametrize('n',[5,7,9])
def test_odd_middle_edge_flip_is_rejected(n):
    data=cubies_to_facelets(solved(n).cubies,n)
    _,m=get_d_maxc(n)
    cycle(data,cells(n,(0,m,m),('U','F')))
    assert any('翻转' in e for e in validate(data,n))


@pytest.mark.parametrize('n',[4,5,6,7])
def test_duplicate_corner_inventory_is_rejected(n):
    data=cubies_to_facelets(solved(n).cubies,n)
    _,m=get_d_maxc(n)
    cycle(data,cells(n,(m,m,m),('R',))+cells(n,(-m,-m,-m),('L',)))
    assert validate(data,n)


@pytest.mark.parametrize('n',[5,6,7])
def test_centres_cannot_move_between_distinct_orbits(n):
    from solver.nxn_orbits import orbits
    cube=solved(n)
    groups=[g for g in orbits(n,1) if len(g)==24]
    p=groups[0][0]
    q=next(q for q in groups[1] if cube.cubies[q].stickers!=cube.cubies[p].stickers)
    from cube.coordinates import FACE_NORMALS
    def face_at(position):
        normal=next(iter(cube.cubies[position].stickers))
        return next(face for face,norm in FACE_NORMALS.items() if norm==normal)
    data=cubies_to_facelets(cube.cubies,n)
    cycle(data,cells(n,p,(face_at(p),))+cells(n,q,(face_at(q),)))
    assert any('轨道' in e for e in validate(data,n))


@pytest.mark.parametrize('n',range(2,10))
@pytest.mark.parametrize('seed',[0,1,37,91])
def test_random_legal_face_slice_and_whole_turns_still_pass(n,seed):
    cube=solved(n)
    rng=random.Random(seed)
    for _ in range(50):
        if rng.randrange(8)==0:move=rng.choice(('x','y','z'))
        else:
            width=rng.randint(1,n)
            move=(str(width) if width>1 else '')+rng.choice(('U','R','F','D','L','B'))
        cube.apply_move(move+rng.choice(('','2',"'")))
    data=cubies_to_facelets(cube.cubies,n)
    before={f:[row[:] for row in rows] for f,rows in data.items()}
    assert validate(data,n)==[]
    assert data==before


@pytest.mark.parametrize('n',[4,6,8])
def test_legal_odd_wing_parity_is_accepted(n):
    from solver.nxn_orbits import orbits,wing_permutation,parity
    cube=solved(n)
    cube.apply_moves(['2R',"R'"])
    assert any(parity(wing_permutation(cube,g)) for g in orbits(n,2) if len(g)==24)
    assert validate(cubies_to_facelets(cube.cubies,n),n)==[]
