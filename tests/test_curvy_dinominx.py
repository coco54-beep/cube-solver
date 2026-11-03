"""AJ's two-depth geometry, independent deep entry and user-visible failures."""
from collections import Counter
import json,math
import pytest
from cube.polyhedral import PolyhedralPuzzle,Move,body,dot,cross,rotate,add,scale
from solver.polyhedral import piece_orbits


def test_adjacent_shallow_circles_are_tangent_at_body_edge_midpoints():
    from cube.curvy_dinominx import cuts
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4);g=c.geometry
    shallow=cuts()[1::2]
    for face,polygon in enumerate(body(g.spec.normals)):
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            left=min(shallow,key=lambda cut:sum((x-y)**2 for x,y in zip(cut.centre,a)))
            right=min(shallow,key=lambda cut:sum((x-y)**2 for x,y in zip(cut.centre,b)))
            distance=math.dist(left.centre,right.centre)
            assert left.radius+right.radius==pytest.approx(distance,abs=1e-10)
            midpoint=scale(add(a,b),.5)
            assert math.dist(midpoint,left.centre)==pytest.approx(left.radius,abs=1e-10)
            assert math.dist(midpoint,right.centre)==pytest.approx(right.radius,abs=1e-10)
            # The exact contact survives outline generation on both sides;
            # no small positive-area panel is inserted between the circles.
            for cut in (left,right):
                bit=cuts().index(cut)
                matching=[g.stickers[i] for p in g.layers[bit//2][1] for i in g.pieces[p]
                          if g.stickers[i].face==face]
                assert any(min(math.dist(v,midpoint) for v in s.polygon)<1e-7 for s in matching)


def test_aj_has_two_real_cap_depths_and_twenty_six_panels_per_face():
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4);g=c.geometry
    assert (len(g.pieces),len(g.stickers),len(g.spec.axes),len(c.moves()))==(131,312,20,40)
    assert Counter(map(len,g.pieces))=={2:90,3:40,12:1}
    assert len(set(tuple(round(v,7) for v in p) for p in g.centres))==131
    assert Counter(s.face for s in g.stickers)=={i:26 for i in range(12)}
    assert all(len(rows)==2 for rows in g.layers)
    assert all(set(deep)!=set(shallow) and set(shallow)<set(deep) for deep,shallow in g.layers)
    before=tuple(c.colors)
    with pytest.raises(ValueError):c.apply_move(Move(0,0,.5))
    assert tuple(c.colors)==before
    areas=Counter()
    for s in g.stickers:
        areas[s.face]+=sum(dot(cross(a,b),g.spec.normals[s.face]) for a,b in zip(s.polygon,s.polygon[1:]+s.polygon[:1]))/2
    for face,poly in enumerate(body(g.spec.normals)):
        full=sum(dot(cross(a,b),g.spec.normals[face]) for a,b in zip(poly,poly[1:]+poly[:1]))/2
        assert abs(areas[face]-full)<1e-8
    for move in c.moves():
        p=g.permutation(move)
        assert sorted(p)==list(range(312)) and all(p[p[p[s]]]==s for s in range(312))
        assert all(len({g.stickers[p[s]].piece for s in piece})==1 for piece in g.pieces)
        for source,dest in enumerate(p):
            if source==dest:continue
            wanted=g.stickers[dest].polygon
            def distance(point,a,b):
                d=add(b,scale(a,-1));q=add(point,scale(a,-1))
                t=max(0.,min(1.,dot(q,d)/max(1e-20,dot(d,d))))
                v=add(q,scale(d,-t));return dot(v,v)
            for point in g.stickers[source].polygon[::5]:
                point=rotate(point,g.spec.axes[move.axis],math.tau/3)
                assert min(distance(point,a,b) for a,b in zip(wanted,wanted[1:]+wanted[:1]))<1e-7


@pytest.mark.parametrize('seed',range(12))
@pytest.mark.parametrize('length',(30,100))
def test_observed_deep_and_shallow_scrambles_reenter_and_solve(seed,length):
    from cube.polyhedral_scramble import scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    clear();source=PolyhedralPuzzle('aj_curvy_dinominx_4',4);scramble(source,length,20261027+seed)
    entered=PolyhedralPuzzle(source.puzzle_kind,4,[-1]*312)
    for i,color in enumerate(source.colors):entered.colors[i]=color
    before=tuple(entered.colors);answers=[]
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message if answers else 'Missing result'
    replay=entered.entered()
    for m in answers[0].moves:replay.apply_move(m)
    assert replay.is_solved() and tuple(entered.colors)==before and not entered.scramble_history
    assert len(answers[0].moves)<2000
    clear()


def test_aj_staged_tools_preserve_caps_and_cover_every_required_transport():
    from solver.rex_dodecahedron import prepared,flip_paths
    from solver.polyhedral import piece_orbits,apply_word
    from solver.polyhedral_reduction import Transports
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4);g=c.geometry;orbits=piece_orbits(c.puzzle_kind,4)
    order,macros,flip_word,base=prepared(c.puzzle_kind,4)
    assert [len(orbits[i]) for i in order]==[30,60]
    assert [len(macros[i][0]) for i in order]==[4,8]
    assert len(flip_paths(c.puzzle_kind,4))==435
    guarded={s for o in orbits if len(o)==1 for p in o for s in g.pieces[p]}
    action=apply_word(g,flip_word)
    assert all(action[s]==s for s in guarded)
    for i in order:
        word,cycle=macros[i];effect=apply_word(g,word)
        assert all(effect[s]==s for s in guarded)
        guarded.update(s for p in orbits[i] for s in g.pieces[p])
        paths=Transports(c,orbits[i],cycle)
        while paths._expand():pass
        assert (paths.parents>=0).sum()==len(orbits[i])*(len(orbits[i])-1)*(len(orbits[i])-2)//3


def test_aj_illegal_input_cancel_and_save_preserve_the_original_observation():
    from solver.curvy_dinominx import validate,solve
    from services.failures import classify
    from cube.polyhedral_scramble import scramble
    from app.session import encode,decode
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4)
    edges=next(o for o in piece_orbits(c.puzzle_kind,4) if len(o)==30)
    a,b=c.geometry.pieces[edges[0]]
    c.colors[a],c.colors[b]=c.colors[b],c.colors[a];before=tuple(c.colors)
    with pytest.raises(ValueError,match='aj.error.edge_flip'):validate(c)
    assert tuple(c.colors)==before and classify('aj.error.edge_flip')=='illegal'
    with pytest.raises(InterruptedError):solve(c,lambda:True)
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4);core=next(p for p in c.geometry.pieces if len(p)==12)
    from solver.polyhedral import _body_frames,_transform
    from cube.polyhedral import key
    faces={key(n):i for i,n in enumerate(c.geometry.spec.normals)}
    frame=_body_frames(c.puzzle_kind,4)[1]
    for s in core:c.colors[s]=faces[key(_transform(frame,c.geometry.spec.normals[c.geometry.stickers[s].face]))]
    with pytest.raises(ValueError,match='aj.error.fixed_centres'):validate(c)
    assert classify('aj.error.fixed_centres')=='illegal'
    c=PolyhedralPuzzle('aj_curvy_dinominx_4',4);scramble(c,100,54);c.colors[7]=-1
    restored=decode(json.loads(json.dumps(encode(c))))
    assert restored.puzzle_kind==c.puzzle_kind and restored.colors==c.colors and not restored.scramble_history
    with pytest.raises(ValueError,match='every sticker'):validate(restored)


def test_aj_has_one_home_in_the_existing_dodecahedral_family():
    from candidate_puzzles import catalogue_family,CATALOGUE_FAMILIES,BY_KIND
    from demo.expanded_support import entry_screen
    assert BY_KIND['aj_curvy_dinominx_4'].n==4
    assert catalogue_family('aj_curvy_dinominx_4')=='megaminx'
    assert sum('aj_curvy_dinominx_4' in kinds for kinds in CATALOGUE_FAMILIES.values())==1
    assert entry_screen('aj_curvy_dinominx_4')=='PolyhedralScreen'
