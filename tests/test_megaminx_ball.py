"""The photographed VeryPuzzle #59 ball, not the #60 C1 mechanism."""
from collections import Counter
import json,math
import pytest
from cube.polyhedral import PolyhedralPuzzle,Move,dot,cross,add,scale,rotate,unit


def test_spherical_panels_cover_ball_and_share_real_plane_cut_circles():
    from cube.megaminx_ball import skin,CUT_HEIGHT,RADIUS
    c=PolyhedralPuzzle('megaminx_ball',3);g=c.geometry
    original=PolyhedralPuzzle('megaminx',3)
    assert g.spec.kind=='megaminx_ball' and g.layers==original.geometry.layers
    assert g.spec.axes==original.geometry.spec.axes and len(g.spec.normals)==20
    assert Counter(map(len,g.pieces))=={5:12,2:30,1:20}
    assert Counter(s.face for s in g.stickers)=={f:7 for f in range(20)}
    assert c.color_count==20 and len(c.colors)==140
    solid_angle=0.;area=0.
    for panels in skin():
        for (a,b,c),normal,normals in panels:
            assert all(dot(p,p)==pytest.approx(RADIUS**2,abs=1e-10) for p in (a,b,c))
            cr=cross(add(b,scale(a,-1)),add(c,scale(a,-1)))
            assert dot(cr,add(add(a,b),c))>0
            area+=math.sqrt(dot(cr,cr))/2
            solid_angle+=2*math.atan2(abs(dot(a,cross(b,c))),1+dot(a,b)+dot(b,c)+dot(c,a))
    assert solid_angle==pytest.approx(4*math.pi,abs=1e-9)
    assert area/(4*math.pi*RADIUS**2)==pytest.approx(1.,abs=.005)
    # Every cap is bounded by its actual small circle; a radial projection
    # of the flat minx would miss this constant plane height along each arc.
    for axis,(pieces,) in enumerate(g.layers):
        points=[p for s in g.stickers if s.piece in pieces for p in s.polygon]
        assert min(dot(g.spec.axes[axis],p) for p in points)==pytest.approx(CUT_HEIGHT,abs=1e-8)
        action=g.permutations[axis][0]
        for s,sticker in enumerate(g.stickers):
            if sticker.piece not in pieces:continue
            expected=g.stickers[action[s]].polygon
            for p in sticker.polygon[::5]:
                turned=rotate(p,g.spec.axes[axis],math.tau/5)
                assert min(math.dist(turned,q) for q in expected)<1e-8


@pytest.mark.parametrize('seed',range(12))
@pytest.mark.parametrize('length',(30,100))
def test_observed_scramble_reentered_without_history_solves(seed,length):
    from cube.polyhedral_scramble import scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    source=PolyhedralPuzzle('megaminx_ball',3);scramble(source,length,20261027+seed)
    entered=PolyhedralPuzzle('megaminx_ball',3,[-1]*140)
    for i,color in enumerate(source.colors):entered.colors[i]=color
    before=tuple(entered.colors);answers=[];clear()
    SolveService()._run(entered,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message if answers else 'No result'
    replay=entered.entered()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved() and tuple(entered.colors)==before and not entered.scramble_history
    assert len(answers[0].moves)<1200
    clear()


def test_input_cancel_impossible_piece_and_session():
    from cube.megaminx_ball import solve
    from cube.polyhedral_scramble import scramble
    from app.session import encode,decode
    c=PolyhedralPuzzle('megaminx_ball',3);c.colors[0]=-1
    with pytest.raises(ValueError):solve(c)
    c=PolyhedralPuzzle('megaminx_ball',3)
    a,b,*_=next(p for p in c.geometry.pieces if len(p)==5)
    c.colors[a],c.colors[b]=c.colors[b],c.colors[a];before=tuple(c.colors)
    with pytest.raises(ValueError):solve(c)
    assert tuple(c.colors)==before
    with pytest.raises(InterruptedError):solve(PolyhedralPuzzle('megaminx_ball',3),lambda:True)
    c=PolyhedralPuzzle('megaminx_ball',3);scramble(c,100,54);c.colors[5]=-1
    restored=decode(json.loads(json.dumps(encode(c.entered()))))
    assert restored.puzzle_kind==c.puzzle_kind and restored.colors==c.colors and not restored.scramble_history
    with pytest.raises(ValueError):PolyhedralPuzzle('megaminx_ball',4)
    # An obsolete 12-colour / 132-panel session must fail safely, rather than
    # silently assigning those old IDs to this different colour layout.
    with pytest.raises(ValueError,match='Wrong sticker count'):
        PolyhedralPuzzle('megaminx_ball',3,[0]*132)


def test_global_input_constraints_reject_flip_mirrored_cap_and_odd_swaps():
    from cube.megaminx_ball import validate
    from cube.polyhedral_scramble import scramble
    for seed in range(100):
        c=PolyhedralPuzzle('megaminx_ball',3);scramble(c,100,seed);validate(c)
    for size in (2,5):
        c=PolyhedralPuzzle('megaminx_ball',3)
        slots=next(p for p in c.geometry.pieces if len(p)==size)
        a,b=slots[:2];c.colors[a],c.colors[b]=c.colors[b],c.colors[a]
        before=tuple(c.colors)
        with pytest.raises(ValueError):validate(c)
        assert tuple(c.colors)==before
    for size in (1,2):
        c=PolyhedralPuzzle('megaminx_ball',3)
        a,b=[p for p in c.geometry.pieces if len(p)==size][:2]
        for i,j in zip(a,b):c.colors[i],c.colors[j]=c.colors[j],c.colors[i]
        with pytest.raises(ValueError):validate(c)


def test_twenty_triangular_regions_and_cap_orientation_are_observable():
    from cube.megaminx_ball import CUT_HEIGHT,validate,solve
    from solver.megaminx_ball import _centres,_centre_basis
    c=PolyhedralPuzzle('megaminx_ball',3);g=c.geometry
    # Each monochrome corner is one complete curved triangle, not three
    # differently coloured wedges meeting at the old pentagonal face borders.
    for slots in g.pieces:
        if len(slots)!=1:continue
        panel=g.stickers[slots[0]];active=[]
        for normal in g.spec.axes:
            if sum(abs(dot(normal,p)-CUT_HEIGHT)<1e-8 for p in panel.polygon)>2:active.append(normal)
        assert len(active)==3
        assert dot(unit(tuple(sum(p[k] for p in panel.polygon) for k in range(3))),
                   g.spec.normals[panel.face])==pytest.approx(1.,abs=1e-8)
    assert len(_centre_basis())==12
    # Rotating the five colours of a cap alone is a legal visible state.
    # Ordinary minx solving would overlook it and return a false zero-step solve.
    for axis,slots in enumerate(_centres()):
        work=c.entered();inv=g.inverse_permutation(Move(axis,0,1))
        for i in slots:work.colors[i]=c.colors[inv[i]]
        assert not work.is_solved();validate(work)
        word=solve(work);assert word
        for move in word:work.apply_move(move)
        assert work.is_solved()


def test_original_model_exercises_and_existing_category():
    from candidate_puzzles import catalogue_family,CATALOGUE_FAMILIES
    from demo.expanded_tutorials import lessons
    from demo.expanded_curriculum import chapters
    from demo.expanded_support import entry_screen
    assert catalogue_family('megaminx_ball')=='round_family'
    assert sum('megaminx_ball' in kinds for kinds in CATALOGUE_FAMILIES.values())==1
    assert entry_screen('megaminx_ball')=='PolyhedralScreen' and len(chapters('megaminx_ball'))==4
    for step in lessons('megaminx_ball',3):
        for case in step['cases']:
            work=case['initial'].entered()
            for move in case['moves']:work.apply_move(move)
            assert work.is_solved()
