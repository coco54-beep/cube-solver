"""Dogic colourways share real cuts and turns; only paint regions differ."""
from collections import Counter
import json,random
import pytest
from cube.polyhedral import PolyhedralPuzzle,key,solved_colors,Move
from cube.expanded_polyhedra import dogic_physical_layout,dogic_physical_outlines


def panel_key(poly):return tuple(sorted(key(p) for p in poly))


def test_both_colourways_share_eighty_whole_triangles_and_all_layer_actions():
    normals,parts,layers=dogic_physical_layout();a=PolyhedralPuzzle('dogic_i',3);b=PolyhedralPuzzle('dogic_20',3)
    assert len(parts)==len(a.geometry.pieces)==len(b.geometry.pieces)==80
    assert Counter(face for face,poly,owner in parts)=={i:4 for i in range(20)}
    assert sum(owner is None for face,poly,owner in parts)==20
    assert a.geometry.centres==b.geometry.centres and a.geometry.layers==b.geometry.layers==layers
    assert a.geometry.spec.axes==b.geometry.spec.axes and len(layers)==12
    assert a.moves()==b.moves() and len(a.moves())==24
    for move in a.moves():
        assert move.amount==1  # A fifth turn is 72 degrees in this notation.
        pa,pb=a.geometry.permutation(move),b.geometry.permutation(move)
        for home,(sa,sb) in enumerate(zip(a.geometry.pieces,b.geometry.pieces)):
            da={a.geometry.stickers[pa[i]].piece for i in sa}
            db={b.geometry.stickers[pb[i]].piece for i in sb}
            assert len(da)==1 and da==db
        for model in (a,b):
            before=list(model.colors)
            for _ in range(5):model.apply_move(move)
            assert model.colors==before


def test_physical_outlines_are_identical_and_inlays_add_no_radial_cut():
    shapes=[]
    for kind in ('dogic_i','dogic_20'):
        model=PolyhedralPuzzle(kind,3);lines=dogic_physical_outlines(kind)
        assert len(lines)==len(model.colors)
        shapes.append({(s.piece,tuple(sorted((key(a),key(b)))))
                       for s,segments in zip(model.geometry.stickers,lines) for a,b in segments})
    assert shapes[0]==shapes[1] and len(shapes[0])==80*3
    # The renderer uses these same outlines for grey and painted states.
    from renderer.polyhedral_view import outlines
    for kind in ('dogic_i','dogic_20'):assert outlines(kind,3)==dogic_physical_outlines(kind)


def test_twenty_colors_are_one_color_per_complete_triangle_face():
    cube=PolyhedralPuzzle('dogic_20',3)
    assert cube.color_count==20 and len(cube.colors)==80
    assert Counter(cube.colors)=={i:4 for i in range(20)}
    for face in range(20):
        assert {cube.colors[i] for i,s in enumerate(cube.geometry.stickers) if s.face==face}=={face}
    other=PolyhedralPuzzle('dogic_i',3)
    assert other.color_count==12 and len(other.colors)==120
    assert Counter(other.colors)=={i:10 for i in range(12)}
    assert all(len({other.colors[i] for i in slots})==3 for slots in other.geometry.pieces if len(slots)==3)


def test_inset_tiles_and_y_shaped_plastic_are_identical_in_both_colourways():
    from renderer.dogic_skin import skin
    twelve=skin('dogic_i');twenty=skin('dogic_20')
    assert len(twelve)==120 and len(twenty)==80
    assert sum(map(len,twelve))==sum(map(len,twenty))==120
    assert {panel_key(p) for row in twelve for p in row}=={panel_key(p) for row in twenty for p in row}
    normals,parts,_=dogic_physical_layout()
    for kind in ('dogic_i','dogic_20'):
        c=PolyhedralPuzzle(kind,3)
        for home,(face,poly,owner) in enumerate(parts):
            patches=[p for slot in c.geometry.pieces[home] for p in skin(kind)[slot]]
            assert len(patches)==(1 if owner is not None else 3)
            # All three inlays stay on this ONE mechanical centre triangle.
            for patch in patches:
                assert all(abs(sum(n*x for n,x in zip(normals[face],v))-1)<1e-7 for v in patch)
                assert len(patch)==15  # Rounded corners, not another cut.


@pytest.mark.parametrize('kind',('dogic_i','dogic_20'))
def test_inlay_housing_follows_every_whole_piece_rotation(kind):
    from renderer.dogic_skin import skin
    from cube.polyhedral import rotate
    import math
    c=PolyhedralPuzzle(kind,3);g=c.geometry;tiles=skin(kind)
    for move in c.moves():
        action=g.permutation(move);moving=set(g.layers[move.axis][move.layer])
        for slot,s in enumerate(g.stickers):
            if s.piece not in moving:continue
            placed={panel_key(tuple(rotate(p,g.spec.axes[move.axis],2*math.pi/5) for p in patch))
                    for patch in tiles[slot]}
            assert placed=={panel_key(p) for p in tiles[action[slot]]}


@pytest.mark.parametrize('kind',('dogic_i','dogic_20'))
def test_existing_state_table_and_saved_inputs_still_match(kind):
    from solver.expanded_polyhedra import prepared_chain
    from app.session import encode,decode
    cube=PolyhedralPuzzle(kind,3);rng=random.Random(20261027)
    for _ in range(100):cube.apply_move(rng.choice(cube.moves()))
    assert prepared_chain(cube) is not None
    restored=decode(json.loads(json.dumps(encode(cube))))
    assert restored.colors==cube.colors and restored.geometry.pieces==cube.geometry.pieces


@pytest.mark.parametrize('kind',('dogic_i','dogic_20'))
@pytest.mark.parametrize('length',(30,100))
def test_observed_reentry_solves_without_a_scramble_log(kind,length):
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    rng=random.Random(20261027+length);source=PolyhedralPuzzle(kind,3)
    for _ in range(length):source.apply_move(rng.choice(source.moves()))
    entered=PolyhedralPuzzle(kind,3,colors=source.colors);before=tuple(entered.colors);clear();answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message
    assert tuple(entered.colors)==before and not entered.scramble_history
    replay=entered.clone()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved()
