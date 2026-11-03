"""Discover short closed tools using actual Pisces whole-material gates."""
import sys,math,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.pisces import PiscesCube,AXES,ANGLE1,ANGLE2
from cube.polyhedral import Move,rotate,dot


def discover():
    start=time.monotonic();found={};tested=0;blocked=0;unclosed=0
    angles=(ANGLE1,-ANGLE1,ANGLE2,-ANGLE2)
    for a in range(12):
        for alpha in angles:
            for b in range(12):
                if b==a:continue
                turned=rotate(AXES[b],AXES[a],math.radians(-alpha))
                c=next((c for c,n in enumerate(AXES) if dot(turned,n)>1-1e-9),None)
                if c is None:continue
                for beta in angles:
                    word=(Move(a,0,alpha),Move(b,0,beta),Move(a,0,-alpha),Move(c,0,-beta))
                    tested+=1;cube=PiscesCube()
                    try:cube.apply_moves(word)
                    except ValueError:blocked+=1;continue
                    for repeat in range(1,7):
                        try:action=cube.aligned_permutation()
                        except ValueError:
                            if repeat==6:unclosed+=1;break
                            try:cube.apply_moves(word)
                            except ValueError:blocked+=1;break
                            continue
                        if action!=tuple(range(len(action))):found.setdefault(action,word*repeat)
                        break
    return found,dict(tested=tested,blocked=blocked,unclosed=unclosed,count=len(found),seconds=time.monotonic()-start)


if __name__=='__main__':
    found,stats=discover();print(stats,flush=True)
    out=Path('artifacts/research/pisces');out.mkdir(parents=True,exist_ok=True)
    (out/'closed-actions.json').write_text(json.dumps(dict(stats=stats,actions=[dict(permutation=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()]),indent=2),encoding='utf-8')
