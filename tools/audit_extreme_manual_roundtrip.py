"""Deep Extreme entry round trips through visible observations only."""
import json
import random
import sys
from pathlib import Path
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.articulated import ArticulatedCube
from cube.articulated_observation import ObservationDraft, match_observations, polygon_key, _panels
from solver.articulated import solve_articulated
from solver.tangram_geometry import geometry


def signature(cube):
    return sorted((colour, polygon_key(points))
                  for home in range(len(cube.solids))
                  for points, colour in cube.placed_faces(home) if colour >= 0)


def run(output, whole_pieces=False):
    model = geometry('tangram_extreme')
    rows = []
    for count in (30, 100, 300, 1000):
        for seed in (0, 2, 37, 91, 719, 20261023):
            source = ArticulatedCube('tangram_extreme')
            rng = random.Random(seed)
            previous = None
            for _ in range(count):
                frames, move = rng.choice([(f, m) for f, m in model.children(source.frames)
                                          if (m.axis, m.layer) != previous])
                source.frames = frames
                previous = move.axis, move.layer
            draft=ObservationDraft.from_cube(source)
            if whole_pieces:
                draft=ObservationDraft('tangram_extreme')
                for home,pose in enumerate(source.frames):
                    panel=next(p for face in range(6) for p in _panels(source,home,pose,face))
                    draft.record_piece(panel)
            state = json.loads(json.dumps(draft.state()))
            assert not {'frames', 'history'} & state.keys()
            begun = monotonic()
            matched = match_observations(ObservationDraft('tangram_extreme', state), seconds=20.)
            matched_at = monotonic()
            assert matched.status == 'matched', (seed, count, matched.status)
            entered = matched.cube
            assert not entered.history and signature(entered) == signature(source)
            before = entered.frames
            word = solve_articulated(entered)
            solved_at = monotonic()
            assert entered.frames == before and not entered.history
            replay = entered.clone()
            replay.apply_moves(word)
            assert replay.is_solved(), (seed, count)
            row = dict(seed=seed, scramble_turns=count,
                       entry_mode='whole_piece_cards' if whole_pieces else 'visible_observations',
                       axis_phase=0 if source.axis_available(0) else 1,
                       visible_observations=sum(map(len, state['views'])),
                       manual_history_empty=True, geometry_matches=True,
                       solution_turns=len(word), physical_replay_solved=True,
                       match_seconds=round(matched_at-begun, 3),
                       solve_seconds=round(solved_at-matched_at, 3),
                       replay_seconds=round(monotonic()-solved_at, 3))
            rows.append(row)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(rows, indent=2), encoding='utf-8')
            print(json.dumps(row), flush=True)
    assert {row['axis_phase'] for row in rows} == {0, 1}


if __name__ == '__main__':
    run(Path(sys.argv[1] if len(sys.argv) > 1 else
             'reports/expansion/2026-11-01/tangram-extreme/manual-results.json'),
        whole_pieces='--whole-pieces' in sys.argv)
