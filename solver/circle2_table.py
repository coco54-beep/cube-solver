"""Offline Circle-2 shell plus shallow meet-in-the-middle solving."""
import gzip
import pickle
from collections import deque
from pathlib import Path
from time import monotonic

from cube.circle_cube import Circle2Cube
from solver.circle_cube import _atoms, _circle2_maps

ROOT=Path(__file__).resolve().parent
TABLE=ROOT/'data'/'circle2_table.bin'
FORMAT=1

def key(c):return bytes(c.colors)+bytes(v+1 for v in c.anchor)

def inverse(move):
    if move.amount % 4 == 2:return move
    return type(move)(move.axis,move.layer,(-move.amount)%4)

def build(path=TABLE,depth=6):
    start=Circle2Cube();root=key(start);parents={root:None};front=[start]
    for _ in range(depth):
        nxt=[]
        for state in front:
            k=key(state)
            for move in _atoms(state):
                child=state.clone();child.apply_move(move);ck=key(child)
                if ck in parents:continue
                parents[ck]=(k,move);nxt.append(child)
        front=nxt
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=pickle.dumps({'version':FORMAT,'kind':'circle_2','depth':depth,'root':root,'parents':parents},protocol=4)
    path.write_bytes(gzip.compress(payload,compresslevel=6))
    return len(parents),path.stat().st_size

def load(path=TABLE):
    with gzip.open(path,'rb') as f:data=pickle.load(f)
    if data.get('version')!=FORMAT:raise ValueError('circle2.table_version')
    return data

def word_to(parents,k):
    out=[]
    while parents.get(k) is not None:
        parent,move=parents[k];out.append(move);k=parent
    return list(reversed(out))

def solve(cube,cancelled=None,seconds=30.,target_depth=6):
    if cube.is_solved():return []
    try:data=load()
    except (OSError,ValueError,pickle.UnpicklingError):raise ValueError('circle2.table_missing')
    parents=data['parents'];start=key(cube)
    def verify(word):
        w=cube.clone();w.circle_history=None
        for m in word:
            if cancelled and cancelled():raise InterruptedError()
            w.apply_move(m)
        return w.is_solved()
    if start in parents:
        w=[inverse(m) for m in reversed(word_to(parents,start))]
        if verify(w):return w
    deadline=monotonic()+seconds
    q=deque([(cube,())]);seen={start}
    for _ in range(target_depth):
        if monotonic()>deadline:break
        nxt=deque()
        while q:
            state,path=q.popleft()
            for move in _atoms(state):
                if cancelled and cancelled():raise InterruptedError()
                child=state.clone();child.apply_move(move);k=key(child)
                if k in seen:continue
                seen.add(k);w=path+(move,)
                if k in parents:
                    tail=word_to(parents,k);result=list(w)+[inverse(m) for m in reversed(tail)]
                    if verify(result):return result
                nxt.append((child,w))
        q=nxt
    raise ValueError('rigid.search_limit')
