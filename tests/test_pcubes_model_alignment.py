"""Independent dimension checks against the inspected pCubes definitions."""
import math
import pytest
from cube.articulated import ArticulatedCube
from renderer.variant_scene import penrose_radius, _penrose_point


def test_tangram_distances_are_normalized_by_body_size_not_axis_length():
    # Tangram cube.xml: W=.5; D1=sqrt(3)/12; D2=.175.
    cube=ArticulatedCube('tangram')
    axes,cuts=cube._bands()
    assert cuts[3] == pytest.approx((-math.sqrt(3)/6, math.sqrt(3)/6))
    assert all(bounds==pytest.approx((.35,)) for bounds in cuts[:3])
    assert len(cube.geometry.stickers)==48
    for axis in axes:assert sum(x*x for x in axis)==pytest.approx(1)
    for move in cube.moves():
        if cube.can_apply(move):
            work=cube.clone().apply_move(move).apply_move(move.inverse(6))
            assert work.frames==cube.frames


@pytest.mark.parametrize('n,expected',((2,1.),(3,2/3)))
def test_penrose_fillet_uses_the_reference_cylinder_radius(n,expected):
    # W is the body half-width; R=W for 2x2 and R=2W/3 for 3x3.
    radius=penrose_radius(n,1.,2/n)
    assert radius==pytest.approx(expected)
    point=_penrose_point((1.,1.,0.),1.,radius)
    assert math.hypot(point[0]-(1-radius),point[1]-(1-radius))==pytest.approx(radius)


def test_new_tangram_checkpoints_round_trip_but_old_geometry_is_rejected():
    from app.session import encode,decode
    cube=ArticulatedCube('tangram')
    record=encode(cube)
    assert decode(record).frames==cube.frames
    record['v'].pop('layout_version')
    with pytest.raises(ValueError):decode(record)
