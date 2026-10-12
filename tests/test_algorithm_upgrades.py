"""Candidate legality, paired football flips, and compact native minx search."""
import pytest

from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import piece_orbits,scramble
from solver.polyhedral_optimize import _atoms
from solver.football import _assets,edge_units,solve_football
from solver.football_flips import paired_flip_word
from solver.high_minx_reduction import native_beam


@pytest.mark.parametrize('n,count',((4,18),(5,22)))
def test_prism_candidates_have_no_duplicates_or_identity(n,count):
    cube=PolyhedralPuzzle('pentahedron',n)
    atoms=_atoms(cube)
    assert len(atoms)==len(set(atoms))==count
    for atom in atoms:
        assert atom.amount and atom.amount%cube.geometry.spec.step(atom.axis)==0
        assert cube.geometry.permutation(atom)!=tuple(range(len(cube.colors)))


@pytest.mark.parametrize('n',(3,5))
@pytest.mark.parametrize('size',(2,10,16,18,30))
def test_pair_flip_words_preserve_core_positions_and_fix_requested_bits(n,size):
    cube=PolyhedralPuzzle('football',n)
    vector=[int(i<size) for i in range(30)]
    word=paired_flip_word(cube,_assets()[str(n)],vector)
    assert word is not None
    for move in word:cube.apply_move(move)
    points,units=edge_units(cube)
    for i,pair in enumerate(units[2]):
        actual=[cube.colors[points[s]] for s in pair]
        goal=[cube.geometry.stickers[points[s]].face for s in pair]
        assert actual==(list(reversed(goal)) if vector[i] else goal)


def test_pair_flip_cancel_and_unreachable_odd_target():
    cube=PolyhedralPuzzle('football',3)
    with pytest.raises(InterruptedError):
        paired_flip_word(cube,_assets()['3'],[1,1]+[0]*28,cancel=lambda:True)
    assert paired_flip_word(cube,_assets()['3'],[1]+[0]*29) is None


@pytest.mark.parametrize('n,seed',((3,54),(3,13),(5,54),(5,13)))
def test_football_selects_a_complete_solution_no_longer_than_its_baseline(monkeypatch,n,seed):
    import solver.football as module
    cube=PolyhedralPuzzle('football',n);scramble(cube,24,seed)
    cube=cube.entered();initial=tuple(cube.colors)
    raw=module._solve_football
    baselines=[]
    def capture(*args,**kwargs):
        result=raw(*args,**kwargs)
        if not kwargs.get('improve_flips'):baselines.append(result)
        return result
    monkeypatch.setattr(module,'_solve_football',capture)
    result=solve_football(cube)
    assert len(result)<=len(baselines[0])
    assert tuple(cube.colors)==initial
    for move in result:cube.apply_move(move)
    assert cube.is_solved()


def test_football_optimization_failure_keeps_the_baseline(monkeypatch):
    import solver.football_flips as module
    def failure(*args,**kwargs):raise ValueError('Unavailable experimental plan')
    monkeypatch.setattr(module,'paired_flip_word',failure)
    cube=PolyhedralPuzzle('football',3);scramble(cube,12,1)
    result=solve_football(cube)
    for move in result:cube.apply_move(move)
    assert cube.is_solved()


GOLDEN={
    4:((6,0,3),(7,1,2),(6,1,1),(0,0,4),(9,0,1),(3,1,1),(3,0,1),(11,0,4)),
    6:((9,0,4),(8,1,3),(11,0,3),(8,2,1),(0,2,2),(4,2,1),(1,1,4),(5,0,3)),
    13:((8,2,3),(11,0,3),(8,5,1),(1,3,2),(0,5,2),(1,2,2),(4,5,1),(5,0,3)),
}


@pytest.mark.parametrize('n',(4,6,13))
@pytest.mark.parametrize('accelerated',(False,True))
def test_compact_search_keeps_reference_paths_and_scalar_fallback(n,accelerated):
    cube=PolyhedralPuzzle('megaminx',n);scramble(cube,12,3)
    positions=[p for orbit in piece_orbits('megaminx',n) if len(orbit)>1 for p in orbit]
    word=native_beam(cube,positions,width=12,max_depth=8,accelerated=accelerated)
    assert tuple((m.axis,m.layer,m.amount) for m in word)==GOLDEN[n]


def test_native_search_cancellation():
    cube=PolyhedralPuzzle('megaminx',4)
    positions=list(range(len(cube.geometry.pieces)))
    with pytest.raises(InterruptedError):
        native_beam(cube,positions,cancel=lambda:True)
