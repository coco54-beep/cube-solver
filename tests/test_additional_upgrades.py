import json
from pathlib import Path
import zlib
import pytest

from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import apply_word,piece_orbits,scramble
from solver.solution_loops import shorten_visible_loops
from solver.minx_plans import orbit_plan


@pytest.mark.parametrize('n',range(4,14))
def test_offline_minx_plans_preserve_protected_stickers(n):
    cube=PolyhedralPuzzle('megaminx',n);g=cube.geometry
    targets={i:o for i,o in enumerate(piece_orbits('megaminx',n)) if len(o)>1}
    macros,order,staged=orbit_plan(cube,targets)
    protected=set()
    for i in order:
        word,base=macros[i];action=apply_word(g,word)
        a,b,c=base
        assert [g.stickers[action[g.pieces[p][0]]].piece for p in base]==[b,c,a]
        must_return=protected if staged else set(range(len(g.stickers)))-{
            s for p in targets[i] for s in g.pieces[p]}
        assert all(action[s]==s for s in must_return)
        protected.update(s for p in targets[i] for s in g.pieces[p])


def test_minx_plan_rejects_mismatched_assets(monkeypatch):
    import solver.minx_plans as module
    monkeypatch.setattr(module,'_assets',lambda:{'4':{'geometry':'obsolete'}})
    assert orbit_plan(PolyhedralPuzzle('megaminx',4),{}) is None


@pytest.mark.parametrize('kind,n',[('fto',3),('skewb',5),('moyu',5),('war_drum',4),('blossom',3)])
def test_loop_eraser_removes_complete_excursions(kind,n):
    cube=PolyhedralPuzzle(kind,n);move=cube.moves()[0]
    order=cube.geometry.spec.order(move.axis)
    unit=Move(move.axis,move.layer,cube.geometry.spec.step(move.axis))
    cube.apply_move(unit)
    original=(unit,unit.inverse(cube.geometry.spec.turn_order))*20+(unit.inverse(cube.geometry.spec.turn_order),)
    before=tuple(cube.colors)
    shortened=shorten_visible_loops(cube,original)
    assert len(shortened)<len(original) and tuple(cube.colors)==before
    for m in shortened:cube.apply_move(m)
    assert cube.is_solved()


def test_loop_optimizer_cancel_and_invalid_result_fallback():
    cube=PolyhedralPuzzle('fto',3);scramble(cube,10,2)
    m=cube.moves()[0];word=(m,m.inverse(cube.geometry.spec.turn_order))*20
    assert shorten_visible_loops(cube,word)==word
    with pytest.raises(InterruptedError):shorten_visible_loops(cube,word,lambda:True)


def test_icosahedron_overrides_preserve_exact_core_action():
    from solver.icosahedron import core_points
    path=Path(__file__).resolve().parents[1]/'solver/data/icosahedron_short_core.bin'
    records=json.loads(zlib.decompress(path.read_bytes()))
    count=0
    for n,record in records.items():
        cube=PolyhedralPuzzle('icosahedron',int(n));points=core_points(cube)
        for replacement in record['replacements']:
            original=apply_word(cube.geometry,[Move(*m) for m in replacement['original']])
            shorter=apply_word(cube.geometry,[Move(*m) for m in replacement['word']])
            assert all(original[s]==shorter[s] for s in points)
            assert len(replacement['word'])<len(replacement['original'])
            count+=1
    assert count==11


@pytest.mark.parametrize('n',(2,3,4,5))
def test_rebuilt_twist_generators_match_their_vectors(n):
    from solver.icosahedron import core_points,orientation_units,orientation_vector,_twist_data
    cube=PolyhedralPuzzle('icosahedron',n);points=core_points(cube)
    ids={s:i for i,s in enumerate(points)};units=orientation_units(cube,points)
    record=_twist_data()[str(n)]
    for vector,word in record['short']+record['long']:
        action=apply_word(cube.geometry,[Move(*m) for m in word])
        actual=orientation_vector(tuple(ids[action[s]] for s in points),units)
        assert tuple(vector)==tuple(actual[5])
        assert not any(actual[2])


@pytest.mark.parametrize('n',(3,5))
def test_rebuilt_edge_generators_match_their_bits(n):
    from solver.icosahedron import core_points,orientation_units,orientation_vector,_edge_data
    cube=PolyhedralPuzzle('icosahedron',n);points=core_points(cube)
    ids={s:i for i,s in enumerate(points)};units=orientation_units(cube,points)
    for mask,word in _edge_data()[str(n)]['generators']:
        action=apply_word(cube.geometry,[Move(*m) for m in word])
        actual=orientation_vector(tuple(ids[action[s]] for s in points),units)
        assert mask==sum(v<<i for i,v in enumerate(actual[2]))
        assert not any(actual[5])


@pytest.mark.parametrize('kind,n',[('fto',3),('skewb',5),('war_drum',4),('blossom',3)])
def test_short_rewrites_preserve_complete_actions(kind,n):
    from solver.solution_loops import _short_actions
    import random
    cube=PolyhedralPuzzle(kind,n)
    rules=_short_actions(cube,None)
    for action in random.Random(13).sample(list(rules),min(30,len(rules))):
        assert bytes(apply_word(cube.geometry,rules[action]))==action


@pytest.mark.parametrize('kind',('axis','windmill','fisher'))
def test_shape_candidate_compares_complete_moves_and_keeps_input(kind,monkeypatch):
    from scripts.audit_solvers import make_sample
    import solver.shape_cube as module
    cube,_=make_sample(kind,3,13)
    original=tuple((p,c.home,tuple(sorted(c.stickers.items()))) for p,c in cube.cubies.items())
    raw=module._solve_shape_cube;baselines=[]
    def capture(*args,**kwargs):
        result=raw(*args,**kwargs)
        if not baselines:baselines.append(result)
        return result
    monkeypatch.setattr(module,'_solve_shape_cube',capture)
    result=module.solve_shape_cube(cube,optimize_budget=.15)
    assert result.success and len(result.moves)<=len(baselines[0].moves)
    assert original==tuple((p,c.home,tuple(sorted(c.stickers.items()))) for p,c in cube.cubies.items())
    cube.apply_moves(result.moves);assert cube.is_solved()


@pytest.mark.parametrize('seed',(1,13,54))
def test_square1_compares_total_solution_and_replays(seed):
    from cube.square1 import Square1Cube
    from solver.square1 import solve_square1
    cube=Square1Cube.solved().scramble(12,seed).entered()
    before=tuple(cube.slots)
    baseline=solve_square1(cube,optimize_budget=0)
    shorter=solve_square1(cube,optimize_budget=.03)
    assert len(shorter)<=len(baseline) and tuple(cube.slots)==before
    cube.apply_moves(shorter);assert cube.is_solved()


@pytest.mark.parametrize('seed',(1,13,54))
def test_mirror_tower_compares_complete_shape_solution(seed):
    from cube.mirror_tower import MirrorTowerCube
    from solver.mirror_tower_optimal import solve_mirror_tower
    cube=MirrorTowerCube.solved();scramble(cube,18,seed)
    cube=cube.entered()
    baseline=solve_mirror_tower(cube,optimize_budget=0)
    result=solve_mirror_tower(cube,optimize_budget=.05)
    assert len(result)<=len(baseline)
    for move in result:cube.apply_move(move)
    assert cube.is_solved()
