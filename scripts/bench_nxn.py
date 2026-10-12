"""Compare entered NxN states, recording player moves and complete replay."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_solvers import make_sample
from cube.cube_n import MAX_N
from solver.solver_n import solve_nxn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--orders', type=int, nargs='+', default=list(range(6, MAX_N + 1)))
    parser.add_argument('--seeds', type=int, nargs='+', default=[20261012])
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in args.orders:
        for seed in args.seeds:
            cube, scramble_steps = make_sample('cube', n, seed, cover=True)
            started = time.perf_counter()
            result = solve_nxn(cube)
            replay = cube.clone()
            replay.apply_moves(result.moves)
            row = dict(order=n, seed=seed, sample_mode='all_generators',
                       scramble_steps=scramble_steps, success=result.success,
                       replay_solved=replay.is_solved(), steps=len(result.moves),
                       seconds=round(time.perf_counter()-started, 3),
                       message=result.message,
                       stage_steps={name: sum(len(s.moves) for s in result.stages
                                              if s.name == name)
                                    for name in ('nxn_core', 'nxn_wings', 'nxn_centers')})
            rows.append(row)
            args.output.write_text(json.dumps(rows, indent=2), encoding='utf-8')
            print(json.dumps(row), flush=True)
            if not result.success or not replay.is_solved():
                raise RuntimeError(row)


if __name__ == '__main__':
    main()
