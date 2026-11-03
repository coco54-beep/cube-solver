"""Whole-solid partial turns and history-independent shape alignment."""
from collections import Counter
import math,random
import pytest
from cube.curvy_copter import CopterState,JUMBLE
from cube.polyhedral import Move
from cube.appearance import IDENTITY_FRAME


def walk(seed,length):
    rng=random.Random(seed);cube=CopterState()
    for _ in range(length):
        moves=list(cube.moves());rng.shuffle(moves)
        for move in moves:
            try:cube.apply_move(move);break
            except ValueError:continue
        else:raise AssertionError('No legal Curvy Copter move')
    return cube


def test_spherical_reference_enumerates_material_without_zero_volume_ghosts():
    c=CopterState();counts=Counter(home for home,face,p in c.panels)
    assert len(c.regions)==45 and len(c.panels)==72 and Counter(counts.values())=={1:24,2:12,3:8}
    assert not set(c.signatures)-{c.signatures[h] for h in counts}-{0}
    assert set(c.signatures)==set(c.regions[0].arrangement.positive_masks())
    assert c.signatures[-1]==0 and c.regions[-1].mask==0
    for axis in range(12):
        selected=c.selection(axis)
        assert Counter(counts[h] for h in selected)=={1:4,2:1,3:2}
        assert len(c.regions)-1 not in selected
    assert c.aligned_permutation()==tuple(range(72))


def test_unaligned_edge_locks_neighbour_and_rejected_turn_preserves_state():
    c=CopterState();c.apply_move(Move(0,0,JUMBLE));before=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(Move(1,0,180))
    assert c.signature()==before
    with pytest.raises(ValueError,match='align_first'):c.aligned_permutation()
    c.apply_move(Move(0,0,-JUMBLE))
    assert c.aligned_permutation()==tuple(range(72))
    assert max(abs(a-b) for f in c.frames for u,v in zip(f,IDENTITY_FRAME) for a,b in zip(u,v))<1e-12


def test_two_preparations_open_a_real_jumbling_turn_and_restore_the_shell():
    c=CopterState();base=c.clone()
    c.apply_move(Move(0,0,-JUMBLE));c.apply_move(Move(8,0,-JUMBLE))
    assert c.can_apply(Move(1,0,180))
    changed_selection=c.selection(1)
    assert changed_selection!=base.selection(1)
    c.apply_move(Move(1,0,180));c.apply_move(Move(0,0,JUMBLE));c.apply_move(Move(8,0,JUMBLE))
    perm=c.aligned_permutation()
    assert perm!=tuple(range(72)) and c.frames[-1]==IDENTITY_FRAME
    # This is not the usual 180-degree slot action in disguise.
    ordinary=base.clone();ordinary.apply_move(Move(1,0,180))
    assert perm!=ordinary.aligned_permutation()
    assert sorted(perm)==list(range(72)) and c.paints==base.paints


@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('length',(30,100))
def test_deep_phase_alignment_attempt_replays_without_changing_the_observation(seed,length):
    from solver.curvy_copter import align_edge_phases
    source=walk(20261027+seed,length)
    # Only observed poses and colours are transferred, no move witness.
    c=CopterState(source.frames,source.paints);before=c.signature()
    work,word=align_edge_phases(c);assert len(word)<=12
    replay=CopterState(c.frames,c.paints)
    for move in word:replay.apply_move(move)
    assert replay.signature()==work.signature() and c.signature()==before
    assert replay.paints==c.paints and replay.frames[-1]==IDENTITY_FRAME


@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('length',(30,100))
def test_two_preparation_shape_repair_replays_every_guarded_turn(seed,length):
    from solver.curvy_copter import normalize
    source=walk(20261027+seed,length)
    observed=CopterState(source.frames,source.paints);before=observed.signature()
    restored,word=normalize(observed,seconds=15.)
    replay=CopterState(observed.frames,observed.paints)
    for move in word:replay.apply_move(move)
    assert replay.signature()==restored.signature() and observed.signature()==before
    assert sorted(restored.aligned_permutation())==list(range(72))
    assert replay.paints==observed.paints


def test_repair_protrusions_even_when_all_edge_carriers_are_already_aligned():
    from solver.curvy_copter import align_edge_phases,normalize
    c=walk(20261027,30);before=c.signature()
    phase,word=align_edge_phases(c)
    assert all(abs((p+90)%180-90)<1e-6 for p in phase.edge_phases())
    with pytest.raises(ValueError,match='align_first'):phase.aligned_permutation()
    restored,moves=normalize(c)
    assert sorted(restored.aligned_permutation())==list(range(72))
    replay=CopterState(c.frames,c.paints)
    for move in moves:replay.apply_move(move)
    assert replay.signature()==restored.signature()
    assert c.signature()==before


def test_shape_repair_deadline_leaves_observed_poses_intact():
    from solver.curvy_copter import normalize
    observed=walk(20261027,30);before=observed.signature()
    with pytest.raises(TimeoutError):normalize(observed,seconds=0.)
    assert observed.signature()==before


@pytest.mark.parametrize('seed',(20262027,20262036))
def test_deep_repair_uses_a_regular_setup_to_escape_a_score_plateau(seed):
    from solver.curvy_copter import normalize
    source=walk(seed,300);observed=CopterState(source.frames,source.paints);before=observed.signature()
    result,word=normalize(observed,seconds=20.)
    result.aligned_permutation();replay=observed.clone()
    for move in word:replay.apply_move(move)
    assert replay.signature()==result.signature() and observed.signature()==before


def test_editable_adapter_keeps_reference_kernel_and_profile_explicit():
    from candidate_puzzles import BY_KIND
    from cube.copter_input import CopterCube
    assert not hasattr(CopterState(),'puzzle_kind')
    assert CopterCube.geometry_profile=='sphere-cut'
    assert BY_KIND['lanlan_curvy_copter'].mechanism=='copter'
    assert 'spherical' in BY_KIND['lanlan_curvy_copter'].name


def test_phase_alignment_accepts_a_free_non_landmark_angle_and_cancel_keeps_input():
    from solver.curvy_copter import normalize
    c=CopterState();c.apply_move(Move(3,0,31.7));before=c.signature()
    with pytest.raises(InterruptedError):normalize(c,lambda:True)
    assert c.signature()==before
    work,word=normalize(c);assert work.aligned_permutation()==tuple(range(72))
    assert len(word)==1 and c.signature()==before


@pytest.mark.parametrize('move',(Move(True,0,180),Move(0,True,180),Move(0,0,float('nan')),Move(0,1,180)))
def test_invalid_turn_does_not_partially_apply(move):
    c=CopterState();before=c.signature()
    with pytest.raises(ValueError):c.apply_move(move)
    assert c.signature()==before
