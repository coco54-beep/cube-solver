"""Relaxed shape tables guide a non-pruning, cancellable shape search."""
import random
from time import monotonic
import pytest
from solver.tangram_geometry import geometry
from solver.tangram_shapes import ShapePatterns,patterns,restore_shape


def state(seed,length):
    model=geometry('tangram_extreme');rng=random.Random(seed);frames=tuple(model.cube.frames);last=None
    for _ in range(length):
        frames,move=rng.choice([(child,move) for child,move in model.children(frames) if (move.axis,move.layer)!=last])
        last=move.axis,move.layer
    return frames


@pytest.mark.parametrize('seed',range(24))
def test_thousand_turn_shape_recovery_is_physically_legal(seed,record_property):
    model=geometry('tangram_extreme');frames=state(seed,1000);table=patterns();begun=monotonic()
    word=model.restore_shape(frames,cancel=lambda:monotonic()-begun>10.)
    elapsed=monotonic()-begun
    cube=model.cube.clone();cube.colors=frames;assert not cube.history
    cube.apply_moves(word)
    assert model.shape_code(cube.frames)==model.root_code
    record_property('shape_seconds',round(elapsed,4));record_property('shape_moves',len(word))


def test_pattern_is_zero_at_goal_and_consistent_across_legal_edges():
    model=geometry('tangram_extreme');table=patterns();assert table.estimate(model.root_code)==0
    for seed in range(12):
        code=model.shape_code(state(seed,80));h=table.estimate(code);assert h!=255
        for child,move in model.shape_children(code):assert abs(h-table.estimate(child))<=1


def test_zero_transposition_cache_does_not_drop_a_shape_solution():
    model=geometry('tangram_extreme');frames=state(37,1000)
    word=restore_shape(model,frames,cache_limit=0)
    for move in word:frames=model.apply(frames,move);assert frames is not None
    assert model.shape_code(frames)==model.root_code


def test_pattern_guard_cancel_and_optional_developer_deadline(monkeypatch):
    import solver.tangram_table as tables
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'solver/data/tangram_extreme_shape_patterns.bin'
    with monkeypatch.context() as patch:
        patch.setattr(tables,'geometry_fingerprint',lambda kind:'changed')
        with pytest.raises(ValueError,match='rigid.solver_data'):ShapePatterns(path)
    model=geometry('tangram_extreme');frames=state(37,100)
    with pytest.raises(InterruptedError):model.restore_shape(frames,cancel=lambda:True)
    with pytest.raises(TimeoutError,match='rigid.search_limit'):restore_shape(model,frames,seconds=-1)


@pytest.mark.parametrize('kind',('tangram','tangram_extreme'))
def test_complete_group_certificate_matches_the_actual_prepared_table(kind):
    import json,hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    rows=json.loads((root/'reports/solver-audit/2026-10-23/tangram-completeness-proof.json').read_text())
    row=next(r for r in rows if r['kind']==kind)
    assert row['asset_sha256']==hashlib.sha256((root/'solver/data'/(kind+'_group.bin')).read_bytes()).hexdigest()
    assert int(row['full_move_group_order'])==int(row['full_root_stabilizer_order'])*row['complete_shape_orbit']
    assert row['all_moves_legal_on_reachable_positions']
