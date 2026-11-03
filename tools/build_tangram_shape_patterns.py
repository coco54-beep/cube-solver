"""Offline exact relaxed occupancy distances for Tangram Extreme shapes."""
import sys
import json
import struct
import zlib
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from solver.tangram_geometry import geometry
from solver.tangram_table import geometry_fingerprint
from solver.tangram_shapes import shape_fingerprint


def projected_states(model,mask):
    root=model.root_code&mask;states=[root];index={root:0}
    for state in states:
        for move,blocked,shifts in model.shape_rules:
            if state&blocked:continue
            child=0
            for delta,where in shifts:
                bits=state&where;child|=bits<<delta if delta>=0 else bits>>-delta
            if child not in index:index[child]=len(states);states.append(child)
    transitions=np.full((len(model.moves),len(states)),-1,dtype=np.int32)
    for j,state in enumerate(states):
        for i,(move,blocked,shifts) in enumerate(model.shape_rules):
            if state&blocked:continue
            child=0
            for delta,where in shifts:
                bits=state&where;child|=bits<<delta if delta>=0 else bits>>-delta
            transitions[i,j]=index[child]
    for i,move in enumerate(model.moves):
        inverse=model.moves.index(move.inverse(6));valid=transitions[i]>=0
        assert np.array_equal(transitions[inverse,transitions[i,valid]],np.flatnonzero(valid))
    return states,transitions


def build(pairs=None):
    model=geometry('tangram_extreme');begun=monotonic()
    cap_mask=15|(((1<<12)-1)<<76)
    caps,cap_moves=projected_states(model,cap_mask)
    parts=[projected_states(model,((1<<12)-1)<<(4+12*i)) for i in range(6)]
    assert len(caps)==8 and all(len(states)==924 for states,moves in parts)
    # The two members of each pair describe coupled skins. Check that
    # relationship exactly; only the three independent pairs need distances.
    pairs=pairs or [(0,1),(2,3),(4,5),(0,2),(0,4),(2,4)]
    records=[];blobs=[];n=924;nn=n*n
    for a,b in pairs:
        ta=parts[a][1];tb=parts[b][1]
        distance=np.full(len(caps)*nn,255,dtype=np.uint8);distance[0]=0
        front=np.array([0],dtype=np.int32);depth=0
        while len(front):
            cap=front//nn;left=front//n%n;right=front%n;following=[]
            for i in range(len(model.moves)):
                c=cap_moves[i,cap];x=ta[i,left];y=tb[i,right]
                valid=(c>=0)&(x>=0)&(y>=0)
                dest=(c[valid]*nn+x[valid]*n+y[valid]).astype(np.int32)
                dest=dest[distance[dest]==255]
                if not len(dest):continue
                dest=np.unique(dest);distance[dest]=depth+1;following.append(dest)
            front=np.concatenate(following) if following else np.array([],dtype=np.int32)
            depth+=1
        reachable=int(np.count_nonzero(distance!=255))
        if reachable==len(caps)*n:
            valid=distance.reshape(len(caps)*n,n)!=255
            assert np.all(valid.sum(axis=1)==1)
            payload=valid.argmax(axis=1).astype('<u2').tobytes();mode='relation'
        else:payload=distance.tobytes();mode='distance'
        records.append(dict(pair=[a,b],mode=mode,size=len(payload),reachable=reachable,diameter=depth-1))
        blobs.append(payload)
        print('pattern',a,b,records[-1]['reachable'],'diameter',depth-1,'seconds',round(monotonic()-begun,2),flush=True)
    header=dict(version=2,kind='tangram_extreme',geometry=geometry_fingerprint('tangram_extreme'),shape_model=shape_fingerprint(),cap_mask=cap_mask,
                caps=caps,parts=[[s>>(4+12*i) for s in states] for i,(states,moves) in enumerate(parts)],patterns=records)
    encoded=json.dumps(header,separators=(',',':')).encode()
    out=Path('artifacts/development/tangram_extreme_shape_patterns.bin');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(b'TP01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(b''.join(blobs),9))
    print('SAVED',out.stat().st_size,'seconds',round(monotonic()-begun,3),flush=True)


if __name__=='__main__':build()
