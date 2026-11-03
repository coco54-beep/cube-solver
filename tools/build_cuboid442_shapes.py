"""Vectorized exhaustive orientation graph; NumPy is offline only."""
import json
import struct
import sys
import zlib
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from solver.cuboid442 import corner_states,corner_turn,corner_actions,code,MOVES,geometry_fingerprint


def build():
    started=monotonic();states,index=corner_states();count=len(states)
    turns={};whole={};forbidden={}
    for face in range(6):
        selected=corner_actions()[face,1][2];axis=corner_actions()[face,1][3]
        forbidden[face]=np.array([any(s[i]==axis for i in selected) for s in states])
        for n in (1,2,3):
            turns[face,n]=np.array([index[code(corner_turn(s,face,n))] for s in states],dtype=np.int32)
            whole[face,n]=np.array([index[code(corner_turn(s,face,n,True))] for s in states],dtype=np.int32)
    parents=np.full(count*count,255,dtype=np.uint8);parents[0]=254;front=np.array([0],dtype=np.int32)
    depth=0
    while len(front):
        outer=front//count;inner=front%count;following=[]
        for i,move in enumerate(MOVES):
            f,l,n=move.axis,move.layer,move.amount
            if l==1:valid=slice(None)
            else:
                face=f if l==0 else (f+3)%6
                valid=~forbidden[face][outer]&~forbidden[face][inner]
            o=outer[valid];a=inner[valid]
            dest=turns[f,n][o]*count+(a if l==0 else turns[f,n][a] if l==1 else whole[f,n][a])
            dest=dest[parents[dest]==255]
            if not len(dest):continue
            dest=np.unique(dest);parents[dest]=MOVES.index(move.inverse(4));following.append(dest)
        front=np.concatenate(following) if following else np.array([],dtype=np.int32);depth+=1
        print(depth,int(np.count_nonzero(parents!=255)),len(front),round(monotonic()-started,3),flush=True)
    header=dict(version=1,kind='cuboid_442',geometry=geometry_fingerprint(),corner_count=count,reachable=int(np.count_nonzero(parents!=255)),
                diameter=depth-1,states=states,moves=[(m.axis,m.layer,m.amount) for m in MOVES])
    encoded=json.dumps(header,separators=(',',':')).encode()
    destination=Path('artifacts/development/cuboid_442-orientations.bin')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(b'CO01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(parents.tobytes(),9))
    print('SAVED bytes',destination.stat().st_size,flush=True)


if __name__=='__main__':build()
