"""Re-enter measured visible poses and colours, then certify full playback."""
import sys,json,math
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.butterflower import ButterflowerCube
from cube.butterflower_aligned import scrambled
from cube.appearance import IDENTITY_FRAME
from cube.polyhedral import rotate
from cube.curvy_copter import multiply
from solver.butterflower import prepare_observation,solve


def euler(frame):
    r=tuple(tuple(frame[j][i] for j in range(3)) for i in range(3))
    y=math.atan2(-r[2][0],math.hypot(r[0][0],r[1][0]))
    if abs(math.cos(y))<1e-8:x=0.;z=math.atan2(-r[0][1],r[1][1])
    else:x=math.atan2(r[2][1],r[2][2]);z=math.atan2(r[1][0],r[0][0])
    return x,y,z


def run():
    rows=[]
    for length in (30,100,300):
        for seed in range(8):
            source=scrambled(seed,length);visible={h for h,f,p in source.panels}
            entered=ButterflowerCube(paints=(-1,)*120)
            for home in visible:
                for axis,angle in zip(((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),euler(source.frames[home])):
                    turn=tuple(rotate(v,axis,angle) for v in IDENTITY_FRAME)
                    entered.set_piece_frame(home,multiply(turn,entered.frames[home]))
            for i,color in enumerate(source.paints):entered.paint(i,color)
            before=entered.signature();start=perf_counter()
            ready=prepare_observation(entered,seconds=15);word=solve(ready,seconds=15)
            elapsed=perf_counter()-start
            assert entered.signature()==before and ready.clone().apply_moves(word).is_solved()
            assert not hasattr(entered,'history') and not hasattr(entered,'scramble_history')
            rows.append(dict(seed=seed,length=length,passed=True,moves=len(word),seconds=round(elapsed,4),
                             visible_pose_rebuilt=True,hidden_inferred=True,input_unchanged=True))
            print(length,seed,len(word),round(elapsed,3),flush=True)
    target=Path(__file__).resolve().parents[1]/'reports/expansion/2026-10-29/butterflower/jumble-manual-results.json'
    target.write_text(json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':run()
