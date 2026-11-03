"""Paired full-solution comparison on the exact same visible-only input."""
import json
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.master_brilic import solve_master_brilic
from solver.polyhedral import solve_polyhedral


def compare(path):
    data=json.loads(path.read_text(encoding='utf-8'))
    cube=PolyhedralPuzzle('master_brilic',3,list(data['colours']))
    assert not cube.scramble_history
    before=tuple(cube.colors);started=perf_counter()
    def labelled(cube,transports,orbit,primitive,fallback,*args,**kwargs):return fallback
    with patch('solver.polyhedral_reduction.color_orbit_word',labelled):
        original=tuple(solve_master_brilic(cube))
    baseline_seconds=perf_counter()-started;started=perf_counter()
    improved=tuple(solve_polyhedral(cube));seconds=perf_counter()-started
    for word in (original,improved):
        replay=cube.entered()
        for move in word:replay.apply_move(move)
        assert replay.is_solved()
    assert tuple(cube.colors)==before
    return dict(input_file=str(path),before=len(original),after=len(improved),
                saved=len(original)-len(improved),baseline_seconds=round(baseline_seconds,3),
                optimized_seconds=round(seconds,3),both_replay_solved=True,input_unchanged=True)


if __name__=='__main__':
    root=Path('reports/optimization/2026-10-26')
    paths=sorted((root/'brilic-ranked/inputs').glob('master_brilic-*.json'))
    rows=[compare(path) for path in paths]
    assert rows and all(row['after']<=row['before'] for row in rows)
    (root/'brilic-paired-quality.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps(rows))
