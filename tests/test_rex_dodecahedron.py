"""Spherical cuts, full regular-state restoration and visible input failures."""
from collections import Counter
import json,math
import pytest
from cube.polyhedral import PolyhedralPuzzle,Move,rotate,key,dot,cross,add,scale


def test_circle_arrangement_reproduces_rex_and_curvy_piece_counts():
    from cube.curved_partition import SphereCut,shell
    from cube.polyhedral import CUBE,Spec,EDGE_AXES,body
    vertices=tuple({key(p):p for f in body(CUBE) for p in f}.values())
    rex=shell(Spec('research',3,CUBE,tuple(vertices),(),3),tuple(SphereCut(v,2.) for v in vertices))
    counts=Counter(mask for mask,face,polygon in rex)
    assert len(rex)==54 and Counter(counts.values())=={1:30,2:12}
    c=(5+math.sqrt(73))/10
    curvy=shell(Spec('research',3,CUBE,EDGE_AXES,(),2),
                tuple(SphereCut(scale(a,math.sqrt(2)*c),1.4) for a in EDGE_AXES))
    counts=Counter(mask for mask,face,polygon in curvy)
    assert len(curvy)==72 and Counter(counts.values())=={1:24,2:12,3:8}


def test_bauhinia_panels_cover_every_face_and_have_exact_whole_piece_actions():
    from cube.polyhedral import body
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);g=c.geometry
    assert (len(g.pieces),len(g.stickers),len(g.spec.axes))==(162,192,20)
    assert Counter(len(p) for p in g.pieces)=={1:132,2:30}
    assert Counter(s.face for s in g.stickers)=={i:16 for i in range(12)}
    original=tuple(c.colors)
    with pytest.raises(ValueError):c.apply_move(Move(0,0,.5))
    assert tuple(c.colors)==original
    areas=Counter()
    for s in g.stickers:
        areas[s.face]+=sum(dot(cross(a,b),g.spec.normals[s.face]) for a,b in zip(s.polygon,s.polygon[1:]+s.polygon[:1]))/2
    for face,poly in enumerate(body(g.spec.normals)):
        full=sum(dot(cross(a,b),g.spec.normals[face]) for a,b in zip(poly,poly[1:]+poly[:1]))/2
        assert abs(areas[face]-full)<1e-8
    for m in c.moves():
        p=g.permutation(m)
        assert sorted(p)==list(range(192))
        assert all(p[p[p[s]]]==s for s in range(192))
        assert all(len({g.stickers[p[s]].piece for s in piece})==1 for piece in g.pieces)
        for source,dest in enumerate(p):
            if source==dest:continue
            polygon=tuple(rotate(v,g.spec.axes[m.axis],math.tau/3) for v in g.stickers[source].polygon)
            wanted=g.stickers[dest].polygon
            # The analytic arcs have shared end points; their sampling counts
            # can differ by one at floating-point ceil boundaries.
            def distance(p,a,b):
                d=add(b,scale(a,-1));q=add(p,scale(a,-1))
                t=max(0.,min(1.,dot(q,d)/max(1e-20,dot(d,d))))
                v=add(q,scale(d,-t));return dot(v,v)
            assert all(min(distance(point,a,b) for a,b in zip(wanted,wanted[1:]+wanted[:1]))<1e-7 for point in polygon)


@pytest.mark.parametrize('seed',range(12))
@pytest.mark.parametrize('length',(30,100))
def test_entered_regular_scrambles_solve_without_history(seed,length):
    from cube.polyhedral_scramble import scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    clear();source=PolyhedralPuzzle('mf8_bauhinia_minx',3);scramble(source,length,20261027+seed)
    entered=PolyhedralPuzzle(source.puzzle_kind,3,[-1]*192)
    for i,color in enumerate(source.colors):entered.colors[i]=color
    original=tuple(entered.colors);answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message if answers else 'Missing result'
    replay=entered.entered()
    for m in answers[0].moves:replay.apply_move(m)
    assert replay.is_solved() and not entered.scramble_history and tuple(entered.colors)==original
    assert len(answers[0].moves)<4000
    clear()


def test_rex_cycle_assets_and_pair_transport_cover_the_complete_regular_orbits():
    from solver.rex_dodecahedron import prepared,flip_paths
    from solver.polyhedral import piece_orbits,apply_word
    from solver.polyhedral_reduction import Transports
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);g=c.geometry;orbits=piece_orbits(c.puzzle_kind,3)
    order,macros,flip_word,base=prepared();assert len(flip_paths())==435
    protected=set()
    for i in order:
        word,cycle=macros[i];effect=apply_word(g,word)
        assert all(effect[s]==s for s in protected)
        protected.update(s for p in orbits[i] for s in g.pieces[p])
        transports=Transports(c,orbits[i],cycle)
        while transports._expand():pass
        assert (transports.parents>=0).sum()==len(orbits[i])*(len(orbits[i])-1)*(len(orbits[i])-2)//3
    effect=apply_word(g,flip_word)
    edges=orbits[0]
    assert {p for p in edges if any(effect[s]!=s for s in g.pieces[p])}==set(base)
    assert all(g.stickers[effect[s]].piece==p for p in edges for s in g.pieces[p])


def test_input_rejects_incomplete_wrong_inventory_and_single_flipped_edge():
    from solver.rex_dodecahedron import solve
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);c.colors[0]=-1
    with pytest.raises(ValueError):solve(c)
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);a,b=next(p for p in c.geometry.pieces if len(p)==2)
    c.colors[a],c.colors[b]=c.colors[b],c.colors[a]
    with pytest.raises(ValueError,match='rex.error.edge_flip'):solve(c)
    with pytest.raises(InterruptedError):solve(c,lambda:True)
    from solver.rex_dodecahedron import validate
    from solver.polyhedral import piece_orbits
    from services.failures import classify
    assert classify('rex.error.edge_flip')=='illegal'
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);centres=piece_orbits(c.puzzle_kind,3)[3]
    a,b=(c.geometry.pieces[p][0] for p in centres[:2])
    c.colors[a],c.colors[b]=c.colors[b],c.colors[a];original=tuple(c.colors)
    with pytest.raises(ValueError,match='rex.error.orbit_parity'):validate(c)
    assert tuple(c.colors)==original and classify('rex.error.orbit_parity')=='illegal'


def test_entered_state_and_renderer_route_round_trip():
    from app.session import encode,decode
    from candidate_puzzles import catalogue_family,CATALOGUE_FAMILIES
    from cube.polyhedral_scramble import scramble
    c=PolyhedralPuzzle('mf8_bauhinia_minx',3);scramble(c,100,54);c.colors[7]=-1
    restored=decode(json.loads(json.dumps(encode(c))))
    assert restored.puzzle_kind==c.puzzle_kind and restored.colors==c.colors and not restored.scramble_history
    assert catalogue_family(c.puzzle_kind)=='megaminx'
    assert sum(c.puzzle_kind in kinds for kinds in CATALOGUE_FAMILIES.values())==1
