"""Offline beam discovery; every emitted circuit replays the exact kernel."""
import sys,math,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from cube.pisces import PiscesCube,AXES,ANGLE1,ANGLE2,CUT
from cube.polyhedral import Move,rotate
from cube.appearance import IDENTITY_FRAME
from cube.crazy_comet import vertices
from cube.rigid_placements import placements
from itertools import product

if '--clover-pyraminx' in sys.argv:
    from cube.clover_pyraminx import CloverPyraminxCube as PiscesCube,CUT

base=PiscesCube();initial=np.array(base.frames,dtype=float);axes=np.array(AXES)
v=[vertices(s) for s in base.solids];width=max(map(len,v))
v=np.array([tuple(row)+(row[0],)*(width-len(row)) for row in v])
rest=np.array([f for d,f,m in placements(PiscesCube,1)])
corners=[h for h,ss in enumerate(base.geometry.pieces) if len(ss)==3]
angles=(ANGLE1,-ANGLE1,ANGLE2,-ANGLE2)
turns={(a,x):np.array([rotate(p,AXES[a],math.radians(x)) for p in IDENTITY_FRAME]) for a in range(12) for x in angles}


def step(state,a,x):
    local=state@axes[a];values=np.einsum('hvi,hi->hv',v,local)
    lo=values.min(axis=1);hi=values.max(axis=1)
    if np.any((lo<CUT-1e-8)&(hi>CUT+1e-8)):return None
    selected=lo>=CUT-1e-8
    if not np.any(selected):return None
    following=state.copy();following[selected]=following[selected]@turns[a,x];return following


def apply(state,word):
    for a,x in word:
        state=step(state,a,x)
        if state is None:return None
    return state


def distances(state):return np.min(np.sum((state[:,None]-rest[None])**2,axis=(2,3)),axis=1)
def signature(state):return np.round(state*1e6).astype(np.int32).tobytes()


if __name__=='__main__':
    start=time.monotonic();tools=[]
    for a,b in product(range(12),repeat=2):
        if a==b:continue
        for x,y in product(angles,repeat=2):
            word=((a,x),(b,y))
            rotation=turns[a,x]@turns[b,y]
            if np.min(np.sum((rest-rotation)**2,axis=(1,2)))<1e-10:tools.append(word)
    print('corner circuits',len(tools),flush=True)
    seen={signature(initial)};beam=[(initial,())];found={}
    for depth in range(1,9):
        following=[]
        for state,word in beam:
            for tool in tools:
                new=apply(state,tool)
                if new is None:continue
                k=signature(new)
                if k in seen:continue
                seen.add(k);candidate=word+tool;d=distances(new);score=np.count_nonzero(d>1e-8)
                if score==0:
                    physical=tuple(Move(a,0,x) for a,x in candidate)
                    try:
                        work=PiscesCube().apply_moves(physical);p=work.aligned_permutation()
                    except ValueError:continue
                    if p!=tuple(range(len(p))):
                        found.setdefault(p,physical);print('CLOSED',len(found),len(candidate),candidate,flush=True)
                else:following.append((int(score),float(d.sum()),new,candidate))
        following.sort(key=lambda row:row[:2]);beam=[(state,word) for score,d,state,word in following[:256]]
        print('depth',depth,'seen',len(seen),'beam',len(following),'best',following[0][:2] if following else None,'seconds',time.monotonic()-start,flush=True)
        if not beam or time.monotonic()-start>180:break
    out=Path('artifacts/research')/('clover-pyraminx' if '--clover-pyraminx' in sys.argv else 'pisces');out.mkdir(parents=True,exist_ok=True)
    (out/'circuit-actions.json').write_text(json.dumps([dict(permutation=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()]),encoding='utf-8')
    print('DONE',len(found),flush=True)
