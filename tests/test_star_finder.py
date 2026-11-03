"""Closed-position geometry checks, independent of a scramble witness."""
from collections import Counter
import math
import pytest
from cube.polyhedral import PolyhedralPuzzle, Move, dot, cross, body_faces


def test_photo_layout_has_six_triangles_per_hexagon_and_eleven_pentagon_fields():
    c=PolyhedralPuzzle('kairis_star_finder',3);g=c.geometry
    assert len(g.stickers)==252 and c.color_count==32
    assert len(g.pieces)==162 and Counter(map(len,g.pieces))=={1:72,2:90}
    assert len(g.spec.axes)==20 and all(len(a)==1 for a in g.layers)
    faces=Counter(s.face for s in g.stickers)
    assert all(faces[f]==11 for f in range(12))
    assert all(faces[f]==6 for f in range(12,32))
    assert Counter(len(s.polygon) for s in g.stickers if s.face<12)=={3:120,5:12}
    assert all(len(s.polygon)==3 for s in g.stickers if s.face>=12)
    for face,outline in enumerate(body_faces(g.spec)):
        def area(p):return abs(sum(dot(cross(a,b),g.spec.normals[face]) for a,b in zip(p,p[1:]+p[:1])))/2
        assert math.isclose(sum(area(s.polygon) for s in g.stickers if s.face==face),area(outline),abs_tol=1e-8)


@pytest.mark.parametrize('axis',range(20))
def test_whole_piece_turns_close_and_inverse_without_moving_unselected_fields(axis):
    c=PolyhedralPuzzle('kairis_star_finder',3);g=c.geometry;before=tuple(c.colors)
    p=g.permutation(Move(axis,0,1));assert sorted(p)==list(range(252))
    selected=set(g.layers[axis][0]);assert len(selected)==27
    for piece,slots in enumerate(g.pieces):
        assert len({g.stickers[p[s]].piece for s in slots})==1
        if piece not in selected:assert all(p[s]==s for s in slots)
    c.apply_move(Move(axis,0,1));assert not c.is_solved()
    c.apply_move(Move(axis,0,-1));assert tuple(c.colors)==before
    for _ in range(3):c.apply_move(Move(axis,0,1))
    assert tuple(c.colors)==before


def test_every_visible_piece_is_wholly_on_one_side_of_each_cut():
    g=PolyhedralPuzzle('kairis_star_finder',3).geometry
    for axis in g.spec.axes:
        depth=g.spec.cuts[0]
        for slots in g.pieces:
            values=[dot(axis,p)-depth for s in slots for p in g.stickers[s].polygon]
            assert min(values)>=-1e-8 or max(values)<=1e-8


@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_scrambled_colour_reentry_solves_without_any_scramble_history(seed,length):
    from random import Random
    from solver.star_finder import solve
    rng=Random(seed);scrambled=PolyhedralPuzzle('kairis_star_finder',3)
    for _ in range(length):scrambled.apply_move(Move(rng.randrange(20),0,rng.choice((1,2))))
    # Simulate manual entry face by face into a new unpainted model.
    entered=PolyhedralPuzzle('kairis_star_finder',3,[-1]*252)
    for face in range(32):
        for slot,s in enumerate(entered.geometry.stickers):
            if s.face==face:entered.colors[slot]=scrambled.colors[slot]
    assert entered.scramble_history is None
    before=tuple(entered.colors);word=solve(entered)
    assert tuple(entered.colors)==before
    for m in word:entered.apply_move(m)
    assert entered.is_solved()


def test_staged_certificate_preserves_completed_orbits_and_covers_every_triple():
    from solver.rex_dodecahedron import prepared,flip_paths
    from solver.polyhedral import apply_word,piece_orbits
    from solver.polyhedral_reduction import Transports
    c=PolyhedralPuzzle('kairis_star_finder',3);g=c.geometry
    order,macros,flip,base=prepared(c.puzzle_kind,3);protected=set()
    orbits=piece_orbits(c.puzzle_kind,3)
    assert sorted(order)==list(range(4)) and len(flip_paths(c.puzzle_kind,3))==435
    for i in order:
        word,cycle=macros[i];p=apply_word(g,word)
        assert all(p[s]==s for s in protected)
        changed={h for h in orbits[i] if any(p[s]!=s for s in g.pieces[h])}
        assert changed==set(cycle)
        transport=Transports(c,orbits[i],cycle,both_directions=True)
        while transport._expand():pass
        count=len(orbits[i]);assert (transport.parents>=0).sum()==count*(count-1)*(count-2)//3
        protected.update(s for h in orbits[i] for s in g.pieces[h])
    p=apply_word(g,flip);edges=next(o for o in orbits if len(o)==30)
    assert {h for h in edges if any(p[s]!=s for s in g.pieces[h])}==set(base)
    assert all(g.stickers[p[s]].piece==h for h in edges for s in g.pieces[h])


def test_bad_input_illegal_half_turn_and_cancellation_leave_input_untouched():
    from solver.star_finder import solve,validate
    c=PolyhedralPuzzle('kairis_star_finder',3);before=tuple(c.colors)
    with pytest.raises(ValueError):c.apply_move(Move(0,0,.5))
    assert tuple(c.colors)==before
    c.colors[0]=-1;partial=tuple(c.colors)
    with pytest.raises(ValueError,match='every sticker'):validate(c)
    assert tuple(c.colors)==partial
    c=PolyhedralPuzzle('kairis_star_finder',3);c.apply_move(Move(0,0,1));before=tuple(c.colors)
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert tuple(c.colors)==before


def test_service_and_session_codec_use_the_new_model_without_history():
    from services.solve_service import SolveService,CancelToken
    from app.session import encode,decode
    from services.solution_cache import clear
    clear();c=PolyhedralPuzzle('kairis_star_finder',3)
    for axis in (0,8,3,17,5,14,12):c.apply_move(Move(axis,0,1))
    entered=decode(encode(c.entered()));before=tuple(entered.colors);answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success
    assert tuple(entered.colors)==before and entered.scramble_history is None
    for m in answers[0].moves:entered.apply_move(m)
    assert entered.is_solved();clear()
