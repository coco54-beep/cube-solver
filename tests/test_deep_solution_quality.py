"""Shorter fixed-slot solutions keep full colours and physical replay valid."""
import random

import pytest

from cube.polyhedral import PolyhedralPuzzle
from demo.expanded_support import scramble
from solver.polyhedral import solve_polyhedral
from solver.solution_loops import _state_bridges,shorten_polyhedral_word


@pytest.mark.parametrize('kind,n',[
    ('starminx_i',3),('pentultimate',3),('master_pentultimate',3),
    ('dogic_i',3),('dogic_20',3),('siamese_a',3),
    ('pentagonal_prism',3),('professor_pentagonal',5),('masterball',4)])
def test_bridge_shortcuts_preserve_entire_visible_state_and_leave_input(kind,n):
    from solver.polyhedral_optimize import _atoms
    source=scramble(PolyhedralPuzzle(kind,n),92,30).entered()
    before=tuple(source.colors);rng=random.Random(305);atoms=_atoms(source)
    word=tuple(rng.choice(atoms) for _ in range(140))
    reduced=_state_bridges(source,word,budget=.1)
    assert len(reduced)<=len(word) and tuple(source.colors)==before
    original=source.clone();changed=source.clone()
    for move in word:original.apply_move(move)
    for move in reduced:changed.apply_move(move)
    assert original.colors==changed.colors


def test_bridge_deadline_and_cancellation():
    cube=PolyhedralPuzzle('pentagonal_prism',3)
    word=tuple(cube.moves())*20
    assert _state_bridges(cube,word,budget=0)==word
    with pytest.raises(InterruptedError):_state_bridges(cube,word,lambda:True)


@pytest.mark.parametrize('kind,n',[
    ('master_pentultimate',3),('master_brilic',3),('dogic_20',3),
    ('siamese_b',3),('professor_pentagonal',5)])
def test_new_family_production_route_shortens_actual_state_solution(monkeypatch,kind,n):
    import solver.solution_loops as module
    cube=scramble(PolyhedralPuzzle(kind,n),20261103,100).entered()
    before=tuple(cube.colors);counts=[]
    def measured(model,word,cancel=None):
        original=tuple(word);reduced=shorten_polyhedral_word(model,original,cancel)
        counts.append((len(original),len(reduced)))
        return reduced
    monkeypatch.setattr(module,'shorten_polyhedral_word',measured)
    result=solve_polyhedral(cube)
    assert counts and all(after<=before for before,after in counts)
    assert tuple(cube.colors)==before and not cube.scramble_history
    replay=cube.clone()
    for move in result:replay.apply_move(move)
    assert replay.is_solved()


def test_invalid_shortened_result_falls_back_to_original(monkeypatch):
    import solver.solution_loops as module
    cube=scramble(PolyhedralPuzzle('dogic_20',3),96,30).entered()
    word=tuple(cube.moves())*20
    monkeypatch.setattr(module,'shorten_visible_loops',lambda *args:())
    assert shorten_polyhedral_word(cube,word)==word


def test_colour_planner_reduces_actual_brilic_stage_and_verifies_full_solution(monkeypatch):
    import solver.polyhedral_reduction as module
    from solver.master_brilic import solve_master_brilic
    original=module.color_orbit_word;counts=[]
    def measured(cube,transports,orbit,primitive,fallback,*args,**kwargs):
        result=original(cube,transports,orbit,primitive,fallback,*args,**kwargs)
        counts.append((len(fallback),len(result)))
        return result
    monkeypatch.setattr(module,'color_orbit_word',measured)
    cube=scramble(PolyhedralPuzzle('master_brilic',3),20261104,100).entered()
    before=tuple(cube.colors);word=solve_master_brilic(cube)
    assert counts and all(after<=before for before,after in counts)
    assert any(after<before for before,after in counts)
    assert tuple(cube.colors)==before
    for move in word:cube.apply_move(move)
    assert cube.is_solved()


def test_colour_planner_deadline_cancel_and_rejects_false_macro(monkeypatch):
    from solver.master_brilic import prepared_cycles
    from solver.polyhedral import piece_orbits,inverse_word
    from solver.polyhedral_reduction import Transports,color_orbit_word
    cube=PolyhedralPuzzle('master_brilic',3)
    orbits=piece_orbits('master_brilic',3)
    index,orbit=next((i,o) for i,o in enumerate(orbits) if len(o)==60 and len(cube.geometry.pieces[o[0]])==1)
    primitive,base=prepared_cycles(cube,{index:orbit})[index]
    for move in primitive:cube.apply_move(move)
    fallback=inverse_word(primitive,5);transports=Transports(cube,orbit,base,both_directions=True)
    assert color_orbit_word(cube,transports,orbit,primitive,fallback,budget=0)==fallback
    transports.cancel=lambda:True
    with pytest.raises(InterruptedError):color_orbit_word(cube,transports,orbit,primitive,fallback)
    transports.cancel=None
    monkeypatch.setattr(transports,'conjugate',lambda *args:())
    assert color_orbit_word(cube,transports,orbit,primitive,fallback,budget=1)==fallback


@pytest.mark.parametrize('kind',('mixup_333','mixup_334','mixup_344','mixup_444',
                                'mixup_plus_333','mixup_plus_334','mixup_plus_344','mixup_plus_444'))
def test_neutral_setups_with_same_shell_keep_identical_cuts_and_successor_shells(kind):
    from solver.mixup_reduction import geometry
    model=geometry(kind);root=tuple(model.cube.frames);features,key,_=model.describe(root)
    alias=next(child for child,move in model.children(root,features,complete=True)
               if child!=root and model.describe(child)[1]==key)
    def edges(frames):
        fs=model.state_features(frames)
        return {move:model.describe(child)[1] for child,move in model.children(frames,fs,complete=True)}
    assert edges(root)==edges(alias)
