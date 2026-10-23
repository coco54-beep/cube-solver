"""Reproduce visible-input-only Tangram solve acceptance on desktop."""
import hashlib
import json
import random
import sys
from pathlib import Path
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.articulated import ArticulatedCube
from cube.articulated_observation import ObservationDraft, match_observations, polygon_key
from solver.articulated import solve_articulated
from solver.tangram_geometry import geometry


def signature(cube):
    return sorted((colour, polygon_key(points))
                  for home in range(len(cube.solids))
                  for points, colour in cube.placed_faces(home) if colour >= 0)


def run(output):
    report = {'method': 'visible-observations -> empty-history match -> solve -> physical replay',
              'platform': sys.platform, 'cases': [], 'assets': {}}
    for kind, count in (('tangram', 60), ('tangram_extreme', 40), ('tangram_extreme',100)):
        model = geometry(kind)
        asset = Path('solver/data')/(kind+'_group.bin')
        report['assets'][kind] = {'bytes': asset.stat().st_size,
                                 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest()}
        for seed in ((0,2) if count==100 else (37, 91, 20261023)):
            source = ArticulatedCube(kind)
            rng = random.Random(seed)
            previous = None
            for _ in range(count):
                frames, move = rng.choice([(f, m) for f, m in model.children(source.frames)
                                          if (m.axis, m.layer) != previous])
                source.apply_move(move)
                assert source.frames == frames
                previous = move.axis, move.layer
            state = json.loads(json.dumps(ObservationDraft.from_cube(source).state()))
            assert 'frames' not in state and 'history' not in state
            begun = monotonic()
            result = match_observations(ObservationDraft(kind, state), seconds=20.)
            matched = monotonic()
            assert result.status == 'matched', (kind, seed, result.status)
            cube = result.cube
            assert not cube.history and signature(cube) == signature(source)
            before = cube.frames
            word = solve_articulated(cube)
            solved = monotonic()
            assert cube.frames == before and not cube.history
            replay = cube.clone()
            replay.apply_moves(word)
            assert replay.is_solved()
            case = dict(kind=kind, seed=seed, scramble_turns=count,
                        visible_observations=sum(map(len,state['views'])),
                        manual_history_empty=True, geometry_matches=True,
                        solution_turns=len(word), physical_replay_solved=True,
                        match_seconds=round(matched-begun,3),
                        solve_with_verification_seconds=round(solved-matched,3),
                        independent_replay_seconds=round(monotonic()-solved,3))
            report['cases'].append(case)
            print(json.dumps(case), flush=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    run(Path(sys.argv[1] if len(sys.argv)>1 else 'reports/solver-audit/2026-10-23/tangram-acceptance.json'))
