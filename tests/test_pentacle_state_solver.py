"""Rebuild visible disc phases and colours on a fresh, empty Pentacle."""
import random
import pytest
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from solver.pentacle_state import disc_corrections,panel_key,solve_pentacle_state,table
from solver.pentacle import solve_pentacle


def visible_input(source):
    observed={panel_key(patches):color for patches,color in zip(source.world_panels(),source._paints)}
    entered=PentacleCube(paints=[-1]*len(source.panels))
    for face,correction in enumerate(disc_corrections(source)):
        if abs(correction)>1e-6:entered.apply_move(Move(face,0,-correction))
    for i,patches in enumerate(entered.world_panels()):entered.paint(i,observed[panel_key(patches)])
    assert not entered.history
    assert {panel_key(p):c for p,c in zip(entered.world_panels(),entered._paints)}==observed
    return entered


def scrambled(seed,length):
    rng=random.Random(seed);source=PentacleCube()
    for _ in range(length):
        face=rng.randrange(6)
        source.apply_moves(source.alignment_moves(face))
        source.apply_move(Move(face,1,rng.choice((90,180,270))))
        source.apply_move(Move(rng.randrange(6),0,rng.uniform(-180,180)))
    return source


@pytest.mark.parametrize('length',[20,60])
@pytest.mark.parametrize('seed',range(6))
def test_visible_manual_state(seed,length):
    cube=visible_input(scrambled(seed,length));before=cube.colors
    word=solve_pentacle(cube)
    assert cube.colors==before and not cube.history
    replay=cube.clone();replay.apply_moves(word)
    assert replay.is_solved()


def test_group_resource():
    data=table()
    assert data['kind']=='pentacle' and data['verified_transversals']==1221
    assert len(data['goal_colors'])==114


def test_hidden_carrier_permutation_is_not_a_colour_goal():
    source=scrambled(9,5);cube=PentacleCube()
    hidden_homes={cube.panels[i].home for i in cube.hidden_panels}
    cube.frames=tuple(source.frames[i] if i in hidden_homes else f
                      for i,f in enumerate(cube.frames))
    cube._history_snapshot=cube.frames
    assert cube.is_solved()
    assert solve_pentacle_state(cube)==()
    # The existing mechanical group remains usable: hidden carriers never
    # exchange with a visible corner or disc panel.
    for orbit in table()['orbits']:
        assert not (set(orbit)&cube.hidden_panels) or set(orbit)<=cube.hidden_panels


def test_cancelled():
    with pytest.raises(InterruptedError):solve_pentacle_state(PentacleCube(),lambda:True)
    with pytest.raises(InterruptedError):solve_pentacle(PentacleCube(),lambda:True)


def test_resource_fingerprint_guard(monkeypatch):
    import solver.pentacle_state as module
    module.table.cache_clear()
    try:
        monkeypatch.setattr(module,'geometry_fingerprint',lambda:'changed')
        with pytest.raises(ValueError,match='pentacle.solver_data'):module.table()
    finally:module.table.cache_clear()


def test_incomplete_colours_rejected_without_changing_input():
    cube=visible_input(scrambled(7,20));cube.paint(0,-1);before=cube.colors
    with pytest.raises(ValueError,match='pentacle.invalid_colours'):solve_pentacle(cube)
    assert cube.colors==before and not cube.history


def test_cached_selection_matches_projected_vertices():
    from cube.polyhedral import CUBE,dot
    from cube.pentacle import CUT,EPS
    cube=scrambled(37,12)
    for axis,normal in enumerate(CUBE):
        for layer in (0,1):
            for strict in (False,True):
                selected=set();blocked=False
                for home in range(len(cube.frames)):
                    values=[dot(normal,v) for p,patches in zip(cube.panels,cube.world_panels())
                            if p.home==home for poly in patches for v in poly]
                    lo,hi=min(values),max(values)
                    if layer==0:
                        if home in cube.discs and lo>1-EPS and hi<1+EPS:selected.add(home)
                    elif lo>=CUT-EPS:selected.add(home)
                    elif strict and hi>CUT+EPS:blocked=True;break
                if blocked:
                    with pytest.raises(ValueError,match='pentacle.align_first'):cube.selection(axis,layer,strict)
                else:assert cube.selection(axis,layer,strict)==frozenset(selected)
