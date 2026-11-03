"""Analytic extrema that vertex/centroid-only cut tests cannot establish."""
import math
import pytest
from cube.polyhedral import CUBE
from cube.curved_partition import SphereCut
from cube.spherical_cells import Plane,Arrangement


def arrangement(cuts=()):return Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts)


def test_box_distances_include_face_interior_not_only_vertices():
    box=arrangement().region(0)
    assert box.squared_distances((0.,0.,0.))==pytest.approx((0.,3.))
    assert box.squared_distances((2.,0.,0.))==pytest.approx((1.,11.))
    # Every corner misses this sphere, but the middle of x=1 enters it.
    assert all(sum((a-b)**2 for a,b in zip(p,(1.15,0.,0.)))>.25**2 for p in box.vertices)
    assert box.side(SphereCut((1.15,0.,0.),.25))==0


def test_variable_plane_and_sphere_have_four_positive_whole_regions():
    a=arrangement((SphereCut((0.,0.,0.),.4),Plane((1.,0.,0.),0.)))
    assert a.positive_masks()==(0,1,2,3)
    half_ball=a.region(3)
    assert half_ball.interior_closure((0.,0.,0.))
    assert not half_ball.interior_closure((.1,0.,0.))
    assert half_ball.squared_distances((2.,0.,0.))==pytest.approx((4.,2.4**2))


def test_an_enclosed_ball_with_no_vertices_has_complete_radial_bounds():
    a=arrangement((SphereCut((0.,0.,0.),.4),));ball=a.region(1)
    assert not ball.vertices
    assert ball.squared_distances((0.,0.,0.))==pytest.approx((0.,.16))
    assert ball.squared_distances((2.,0.,0.))==pytest.approx((1.6**2,2.4**2))
    assert ball.side(SphereCut((0.,0.,0.),.5))==1
    assert ball.side(SphereCut((2.,0.,0.),1.))==-1
    assert ball.side(SphereCut((1.1,0.,0.),1.))==0


def test_plane_clearance_uses_face_and_circle_extrema_even_without_vertices():
    ball=arrangement((SphereCut((0.,0.,0.),.4),)).region(1)
    assert not ball.vertices
    assert ball.side(Plane((1.,0.,0.),.41))==1
    assert ball.side(Plane((1.,0.,0.),-.41))==-1
    assert ball.side(Plane((1.,0.,0.),.3))==0
    lens=arrangement((SphereCut((-.4,0.,0.),.8),SphereCut((.4,0.,0.),.8))).region(3)
    assert not lens.vertices
    assert lens.side(Plane((0.,1.,0.),math.sqrt(.48)))==1
    assert lens.side(Plane((0.,1.,0.),.69))==0
    half=arrangement((SphereCut((0.,0.,0.),.4),Plane((1.,0.,0.),0.))).region(3)
    assert half.side(Plane((1.,0.,0.),0.))==1
    assert half.side(Plane((-1.,0.,0.),0.))==-1


def test_nonconvex_annulus_retains_inside_and_outside_sphere_constraints():
    a=arrangement((SphereCut((0.,0.,0.),.4),SphereCut((0.,0.,0.),.8)))
    annulus=a.region(2)
    assert annulus.squared_distances((0.,0.,0.))==pytest.approx((.16,.64))
    assert annulus.squared_distances((2.,0.,0.))==pytest.approx((1.2**2,2.8**2))
    assert annulus.side(SphereCut((0.,0.,0.),.6))==0


def test_two_sphere_lens_extremum_occurs_on_a_circle_without_vertices():
    lens=arrangement((SphereCut((-.4,0.,0.),.8),SphereCut((.4,0.,0.),.8))).region(3)
    assert not lens.vertices
    assert lens.squared_distances((0.,0.,0.))==pytest.approx((0.,.48))
    assert lens.side(SphereCut((0.,0.,0.),math.sqrt(.48)+.01))==1
    assert lens.side(SphereCut((0.,0.,0.),.6))==0


def test_invalid_membership_is_rejected_instead_of_hiding_a_region():
    a=arrangement((SphereCut((0.,0.,0.),.4),))
    for mask in (-1,2,True):
        with pytest.raises(ValueError):a.region(mask)


def test_isolated_tangent_contacts_are_not_solid_material():
    a=arrangement((SphereCut((0.,0.,0.),1.),SphereCut((2.,0.,0.),1.)))
    empty=a.region(3)
    assert a.contains(3,(1.,0.,0.))
    assert not empty.interior_closure((1.,0.,0.))
    assert 3 not in a.positive_masks()
    with pytest.raises(ValueError,match='No feasible'):empty.squared_distances((0.,0.,0.))


def test_real_tangential_cusp_survives_the_inversion_closure_check():
    a=arrangement((SphereCut((0.,0.,0.),1.),SphereCut((.5,0.,0.),.5)))
    crescent=a.region(1)
    # No direction is strictly inward for both tangent sphere boundaries,
    # but a parabolic approach through the crescent has real material.
    assert crescent.interior_closure((1.,0.,0.))
    assert 1 in a.positive_masks()
    assert crescent.squared_distances((1.,0.,0.))[0]==pytest.approx(0.)


def test_two_overlapping_caps_only_touch_the_body_and_have_no_material_lens():
    c=(5+math.sqrt(73))/10
    # The intersection circle of these two spheres has minimum y exactly 1.
    # Its spurious +/- 1.49e-8 z endpoints must not invent an interior cell.
    a=arrangement((SphereCut((c,c,0.),1.4),SphereCut((-c,c,0.),1.4)))
    assert a.contains(3,(0.,1.,0.)) and not a.region(3).interior_closure((0.,1.,0.))
    assert 3 not in a.positive_masks()
    with pytest.raises(ValueError,match='No feasible'):a.region(3).squared_distances((0.,0.,0.))
