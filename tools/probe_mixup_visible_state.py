"""Re-enter a new Mixup scramble from observable shapes/colours, then solve."""
import json
import random
import sys
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.mixup import scramble_mixup
from cube.mixup_entry import MixupEntryDraft
from cube.articulated_observation import ObservationDraft,match_observations,polygon_key
from solver.mixup import solve_mixup


def signature(cube):
    return sorted((c,polygon_key(poly)) for h in range(len(cube.solids))
                  for poly,c in cube.placed_faces(h) if c>=0)


def run(kind,seconds=60):
    random.seed(20261023)
    source=scramble_mixup(kind,seconds=1.5)
    source_length=len(source.history)
    state=json.loads(json.dumps(MixupEntryDraft.from_cube(source).observations().state()))
    assert 'frames' not in state and 'history' not in state
    folder=Path('reports/input-audit/2026-10-23/mixup-fresh-probes')
    folder.mkdir(parents=True,exist_ok=True)
    (folder/(kind+'-observations.json')).write_text(json.dumps(state,indent=2),encoding='utf-8')
    begun=monotonic();matched=match_observations(ObservationDraft(kind,state),seconds=20.)
    row=dict(kind=kind,seed=20261023,scramble_turns=source_length,observation_match=matched.status)
    if matched.status=='matched':
        cube=matched.cube;assert not cube.history and signature(cube)==signature(source)
        before=cube.frames;started=monotonic()
        try:
            result=solve_mixup(cube,lambda:monotonic()-started>seconds)
            assert not cube.history and cube.frames==before
            replay=cube.clone();replay.apply_moves(result.moves);assert replay.is_solved()
            row.update(success=result.success,moves=len(result.moves),replay_solved=True,history_empty=True)
        except (ValueError,InterruptedError,TimeoutError) as error:
            row.update(success=False,history_empty=True,message=str(error) or type(error).__name__)
        row['solve_seconds']=round(monotonic()-started,3)
    else:row['success']=False
    row['total_seconds']=round(monotonic()-begun,3)
    path=folder/(kind+'.json')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(row,indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)


if __name__=='__main__':run(sys.argv[1],float(sys.argv[2]) if len(sys.argv)>2 else 60.)
