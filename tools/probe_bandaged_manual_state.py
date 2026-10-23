"""Solve one saved visible manual bandage input with a bounded cancel token."""
import json
import sys
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.bandaged_entry import reconstruct
from cube.conversion import cubies_to_facelets
from services.solve_service import SolveService


def run(path,seconds=30.):
    data=json.loads(path.read_text(encoding='utf-8'))
    seams={(p['face'],tuple(tuple(c) for c in p['cells'])) for p in data['plates']}
    cube=reconstruct(data['kind'],data['facelets'],seams)
    assert not cube.history and cubies_to_facelets(cube.cubies,cube.n)==data['facelets']
    started=monotonic()
    class Cancel:
        def is_set(self):return monotonic()-started>seconds
    result=[]
    SolveService()._run(cube,result.append,None,Cancel())
    result=result[0]
    replay=False
    if result.success:
        work=cube.clone();work.apply_moves(result.moves);replay=work.is_solved()
        assert replay
    report=dict(kind=data['kind'],seed=data['seed'],scramble_turns=data['scramble_turns'],
                actual_controls=data.get('actual_controls',False),history_empty=not cube.history,
                success=result.success,replay_solved=replay,moves=len(result.moves),
                seconds=round(monotonic()-started,3),message=result.message)
    print('MANUAL_BANDAGE_RESULT '+json.dumps(report),flush=True)
    return report


if __name__=='__main__':run(Path(sys.argv[1]),float(sys.argv[2]) if len(sys.argv)>2 else 30.)
