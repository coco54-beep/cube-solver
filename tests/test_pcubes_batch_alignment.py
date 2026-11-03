"""Independent geometric checks for the remaining local reference families."""
import math
import random
import pytest
from cube.polyhedral import PolyhedralPuzzle,Spec,CUBE,OCTA,DODECA,body,_cut_skin,dot,Move
from cube.articulated_observation import polygon_key


@pytest.mark.parametrize('kind,n', [('pentagonal_domino',2),('pentagonal_prism',3),
                                  ('pentagonal_4',4),('professor_pentagonal',5)])
def test_prism_reference_dimensions_and_every_inverse(kind,n):
    c=PolyhedralPuzzle(kind,n);g=c.geometry
    # R is circumradius. The XML gives H=R*sin(36)*n/3, except Professor H=R*sin(36).
    radius=1/math.cos(math.pi/5)
    height=radius*math.sin(math.pi/5)*(n/3 if n<5 else 1)
    assert max(abs(p[1]) for s in g.stickers for p in s.polygon)==pytest.approx(height)
    assert g.spec.axis_cuts[0]==pytest.approx(tuple(height*(1-2*i/n) for i in range(1,n)))
    for m in c.moves():
        assert g.spec.step(m.axis)==(2 if m.axis<2 else 5)
        before=list(c.colors);c.apply_move(m);c.apply_move(m.inverse(10));assert c.colors==before


@pytest.mark.parametrize('kind,n', [('rubik_cheese',2),('cheese_3',3)])
def test_cheese_reference_radius_height_and_closed_housings(kind,n):
    from cube.layered_cheese import housing
    c=PolyhedralPuzzle(kind,n);g=c.geometry
    points=[v for s in g.stickers for v in s.polygon]
    assert max(abs(v[1]) for v in points)==pytest.approx(.5)
    assert max(math.hypot(v[0],v[2]) for v in points)==pytest.approx(1)
    assert len(g.pieces)==6*n and len(g.stickers)==6*n+12
    assert max(abs(v[1]) for _,poly,_ in housing(kind) for v in poly)==pytest.approx(.5)
    for m in c.moves():
        original=list(c.colors);c.apply_move(m);c.apply_move(m.inverse(6));assert c.colors==original


def test_trajber_four_layer_cut_recipe_matches_every_external_patch():
    from cube.solid_shape_mods import faces_for
    from cube.mastermorphix import positions_for_order
    cut=math.sqrt(3)/4 # Reference vertices +/-.75, cuts +/-.1875, app vertices +/-sqrt(3).
    expected={(f,polygon_key(p)) for _,f,p in _cut_skin(Spec('reference',4,OCTA,CUBE,(-cut,0.,cut),4))}
    actual={(f,polygon_key(p)) for home in positions_for_order(4) for p,f in faces_for('trajber',home,4) if f>=0}
    assert actual==expected


def test_dogic_reference_two_vertex_cut_depths_match_both_colourways():
    from cube.expanded_polyhedra import dogic_physical_layout
    normals,parts,_=dogic_physical_layout()
    radius=max(math.sqrt(dot(v,v)) for face in body(normals) for v in face)
    shallow=(radius+radius/math.sqrt(5))/2;deep=radius/math.sqrt(5)
    expected={(face,polygon_key(poly)) for _,face,poly in _cut_skin(Spec('reference',3,normals,DODECA,(deep,shallow),5))}
    assert expected=={(face,polygon_key(poly)) for face,poly,owner in parts}
    a=PolyhedralPuzzle('dogic_i',3);b=PolyhedralPuzzle('dogic_20',3)
    assert a.geometry.layers==b.geometry.layers


@pytest.mark.parametrize('n,radius', [(2,.7),(3,.8)])
def test_circle_reference_radius_preserves_exact_arc_boundaries(n,radius):
    from cube.circle_cube import _panels
    arcs=[p for (inside,r,c),poly,patches in _panels(n) if inside
          for patch in patches for p in patch if math.hypot(*p)>radius-1e-6]
    assert arcs and all(math.hypot(*p)==pytest.approx(radius) for p in arcs)


def test_mixup_334_half_centre_does_not_nominate_a_slab_outside_its_skin():
    from cube.mixup import MixupCube,_panel_bounds
    from cube.articulated import MIXUP_MODELS
    c=MixupCube('mixup_334');c.apply_move(Move(0,1,1))
    assert c.can_apply(Move(1,0,2)) # Previously rejected solely by an out-of-piece anchor.
    for kind in MIXUP_MODELS:
        c=MixupCube(kind);rng=random.Random(917)
        for _ in range(6):
            for h,point in enumerate(c.geometry.centres):
                bounds=_panel_bounds(kind,h,c.frames[h])
                assert all(lo-1e-7<=point[a]<=hi+1e-7 for a,(lo,hi) in enumerate(bounds))
            c.apply_move(rng.choice([m for m in c.moves() if c.can_apply(m)]))


def test_mixup_anchors_are_identical_for_geometrically_identical_pieces():
    from cube.mixup import MixupCube
    from cube.articulated import MIXUP_MODELS,proper_poses
    from cube.appearance import transform_frame
    for kind in MIXUP_MODELS:
        c=MixupCube(kind);known={}
        for h,s in enumerate(c.solids):
            for pose in proper_poses('mixup'):
                skins=tuple(sorted(polygon_key(poly) for poly,color in c.placed_faces(h,pose) if color>=0))
                anchor=tuple(round(v,6) for v in transform_frame(c.orientations[pose],s.anchor))
                identity=s.role,skins
                if identity in known:assert known[identity]==anchor
                known[identity]=anchor


def test_mixup_reference_backings_match_cut_recipe_and_edited_input():
    from cube.mixup import MixupCube
    from cube.articulated import MIXUP_MODELS
    from tools.audit_pcubes_mixup_parts import reference,skin_signature
    from renderer.mixup_housing import placed_housing,housing_for_panels
    from renderer.articulated_view import ArticulatedView
    for kind in MIXUP_MODELS:
        c=MixupCube(kind)
        ref={skin_signature(s):s for s in reference(kind)}
        for home,solid in enumerate(c.solids):
            expected={polygon_key(poly) for poly,col in ref[skin_signature(solid.faces)] if col<0}
            assert {polygon_key(poly) for poly in placed_housing(kind,home,0)}==expected
        c.apply_move(next(m for m in c.moves() if m.layer==1 and c.can_apply(m)))
        for home,solid in enumerate(c.solids):
            skins=tuple(sorted(polygon_key(poly) for poly,col in c.placed_faces(home) if col>=0))
            assert {polygon_key(p) for p in housing_for_panels(kind,skins,solid.role)}=={
                polygon_key(p) for p in placed_housing(kind,home,c.frames[home])}
            rendered=ArticulatedView.piece_surfaces(c,home)
            assert {polygon_key(p) for p in placed_housing(kind,home,c.frames[home])}<={
                polygon_key(p) for p,n,col,*_ in rendered if col<0}


def test_pentacle_reference_chords_and_raised_skin_keep_free_turns():
    from cube.pentacle import PentacleCube,CUT,RADIUS
    from renderer.pentacle_view import PentacleView,DISC_HEIGHT
    from types import SimpleNamespace
    assert RADIUS==1 and CUT==pytest.approx(1/2.8) and DISC_HEIGHT==1.3
    c=PentacleCube();assert len(c.panels)==114 and len(c.paint_slots)==90
    surfaces=PentacleView._surfaces(SimpleNamespace(),c)
    assert all(dot(p,normal)==pytest.approx(1.3015) for poly,normal,color,slot,*_ in surfaces
               if color>=0 and c.panels[slot].home in c.discs for p in poly)
    before=c.frames;c.apply_move(Move(0,0,23.7));c.apply_move(Move(0,0,-23.7));assert c.frames==before
