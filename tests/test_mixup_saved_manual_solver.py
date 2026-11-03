"""Solve the same visible-only inputs which exposed the Plus timeouts."""
import json
from pathlib import Path
from time import monotonic
import pytest
from cube.articulated_observation import ObservationDraft,match_observations
from solver.mixup import solve_mixup
from solver.mixup_reduction import geometry,repair_inner_primitives

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('kind',('mixup_333','mixup_334','mixup_344','mixup_444',
                               'mixup_plus_333','mixup_plus_334','mixup_plus_344','mixup_plus_444'))
def test_visible_observations_solve_without_retained_path(kind):
    path=ROOT/'reports/input-audit/2026-10-23/mixup-fresh-probes'/(kind+'-observations.json')
    state=json.loads(path.read_text(encoding='utf-8'))
    assert 'frames' not in state and 'history' not in state
    matched=match_observations(ObservationDraft(kind,state),seconds=20.)
    assert matched.status=='matched'
    cube=matched.cube;before=cube.frames,tuple(cube.colors)
    assert not cube.history
    started=monotonic();result=solve_mixup(cube,lambda:monotonic()-started>45)
    assert (cube.frames,tuple(cube.colors))==before and not cube.history
    replay=cube.clone();replay.apply_moves(result.moves)
    assert result.success and replay.is_solved()


def test_inner_primitive_cancel_preserves_source():
    model=geometry('mixup_plus_344');cube=model.cube.clone();before=cube.frames
    with pytest.raises(InterruptedError):repair_inner_primitives(cube,cancel=lambda:True)
    assert cube.frames==before
