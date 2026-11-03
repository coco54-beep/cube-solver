"""Raised surfaces retain the exact logical turn and paint identities."""
import math
import pytest
from cube.polyhedral import PolyhedralPuzzle, rotate, key, dot, cross, add, scale
from renderer.time_machine_skin import skin, HEIGHT, RADIUS


def test_reference_radius_height_and_all_96_sticker_ids_are_preserved():
    cube=PolyhedralPuzzle('time_machine',2)
    tiles=skin()
    assert len(tiles)==len(cube.colors)==96
    for i,patches in enumerate(tiles[24:],24):
        n=cube.geometry.spec.normals[cube.geometry.stickers[i].face]
        cap=patches[0][0]
        assert all(dot(p,n)==pytest.approx(HEIGHT) for p in cap)
        assert max(math.sqrt(dot(p,p)-HEIGHT**2) for p in cap)==pytest.approx(RADIUS)
        assert len(patches)>1


def test_every_raised_surface_follows_the_native_turn_permutation():
    cube=PolyhedralPuzzle('time_machine',2);g=cube.geometry;tiles=skin()
    def signatures(patches,axis=None,angle=0):
        return {tuple(sorted(key(rotate(p,axis,angle) if axis else p) for p in patch))
                for patch,normal,_ in patches}
    for move in cube.moves():
        action=g.permutation(move);moving=set(g.layers[move.axis][move.layer])
        for i,s in enumerate(g.stickers):
            axis=g.spec.axes[move.axis] if s.piece in moving else None
            actual=signatures(tiles[i],axis,math.tau*move.amount/g.spec.turn_order)
            assert actual==signatures(tiles[action[i]]),(move,i)


def test_raised_surfaces_have_outward_normals():
    for patches in skin()[24:]:
        for patch,normal,_ in patches:
            area=(0.,0.,0.)
            for a,b in zip(patch,patch[1:]+patch[:1]):area=add(area,cross(a,b))
            assert dot(area,normal)>1e-8
