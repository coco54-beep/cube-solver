"""Exact relaxed shape distances and complete memory-bounded shape search."""
from functools import lru_cache
from pathlib import Path
from time import monotonic
import json
import struct
import zlib
import hashlib


@lru_cache(maxsize=1)
def shape_fingerprint():
    from solver.tangram_geometry import geometry
    from solver.tangram_table import geometry_fingerprint
    model=geometry('tangram_extreme')
    raw=(geometry_fingerprint('tangram_extreme'),model.root_code,
         tuple((m.axis,m.layer,m.amount,blocked,shifts) for m,blocked,shifts in model.shape_rules),
         tuple((h,p,values) for (h,p),values in sorted(model.features.items())))
    return hashlib.sha256(json.dumps(raw,separators=(',',':')).encode()).hexdigest()


class ShapePatterns:
    def __init__(self,path=None):
        from solver.tangram_table import geometry_fingerprint
        path=Path(path) if path else Path(__file__).parent/'data/tangram_extreme_shape_patterns.bin'
        try:
            raw=path.read_bytes();size=struct.unpack_from('<I',raw,4)[0]
            data=json.loads(raw[8:8+size]);blob=memoryview(zlib.decompress(raw[8+size:]))
        except (OSError,ValueError,struct.error,zlib.error):raise ValueError('rigid.solver_data') from None
        if (raw[:4]!=b'TP01' or data.get('version')!=2 or data.get('kind')!='tangram_extreme'
            or data.get('geometry')!=geometry_fingerprint('tangram_extreme')
            or data.get('shape_model')!=shape_fingerprint()):raise ValueError('rigid.solver_data')
        self.cap_mask=data['cap_mask']
        self.caps={state:i for i,state in enumerate(data['caps'])}
        cap_count=len(self.caps)
        self.indices=[]
        for states in data['parts']:
            if len(states)!=924 or len(set(states))!=924:raise ValueError('rigid.solver_data')
            lookup=[-1]*4096
            for i,state in enumerate(states):lookup[state]=i
            self.indices.append(lookup)
        self.distances=[];self.relations=[];offset=0
        for record in data['patterns']:
            a,b=record['pair'];payload=blob[offset:offset+record['size']];offset+=record['size']
            if record['mode']=='distance':
                if len(payload)!=cap_count*924**2:raise ValueError('rigid.solver_data')
                self.distances.append((a,b,payload))
            elif record['mode']=='relation':
                if len(payload)!=cap_count*924*2:raise ValueError('rigid.solver_data')
                self.relations.append((a,b,tuple(x[0] for x in struct.iter_unpack('<H',payload))))
            else:raise ValueError('rigid.solver_data')
        if offset!=len(blob) or len(self.distances)!=3 or len(self.relations)!=3:raise ValueError('rigid.solver_data')

    def estimate(self,state):
        cap=self.caps.get(state&self.cap_mask,-1)
        if cap<0:return 255
        poses=tuple(self.indices[i][state>>(4+12*i)&4095] for i in range(6))
        if min(poses)<0:return 255
        for a,b,relation in self.relations:
            if relation[cap*924+poses[a]]!=poses[b]:return 255
        return max(distance[cap*924**2+poses[a]*924+poses[b]] for a,b,distance in self.distances)


@lru_cache(maxsize=1)
def patterns():return ShapePatterns()


def restore_shape(model,frames,cancel=None,progress=None,seconds=None,table=None,cache_limit=120000):
    """IDA* does not discard a beam or stop at an arbitrary depth/node count.

    Pattern distances are admissible relaxations of the exact cut rules.
    Transpositions use bounded memory; a full cache stops storing entries,
    never removes a branch. Cancellation and optional caller deadlines remain.
    """
    if cancel and cancel():raise InterruptedError()
    start=model.shape_code(frames)
    if start.bit_count()!=len(frames):raise ValueError('rigid.invalid')
    if start==model.root_code:return ()
    table=table or patterns();bound=table.estimate(start)
    if bound==255:raise ValueError('rigid.invalid')
    roots=model.shape_atlas(cancel);begun=monotonic();root=model.root_code
    def guard():
        if cancel and cancel():raise InterruptedError()
        if seconds is not None and monotonic()-begun>seconds:raise TimeoutError('rigid.search_limit')
    def goal(node):
        tail=roots.get(node[0])
        return tuple(m.inverse(6) for m in reversed(tail)) if tail is not None else None
    def children(node):
        state,last=node;candidates=[]
        for child,move in model.shape_children(state):
            band=move.axis,move.layer
            if band==last:continue
            h=table.estimate(child)
            if h!=255:candidates.append((h,(child&~root).bit_count(),child,move,band))
        for h,score,child,move,band in sorted(candidates,key=lambda item:item[:2]):yield (child,band),move
    def cancelled():guard();return False
    def update(bound,nodes):
        if progress:progress(-1,0)
    from solver.complete_search import deepen,Exhausted
    try:path=deepen((start,None),goal,children,lambda node:table.estimate(node[0]),
                    cancel=cancelled,progress=update,cache_limit=cache_limit,
                    resume_key=('tangram-shape-v1',model.root_code))
    except Exhausted:raise ValueError('rigid.invalid') from None
    frames=tuple(frames)
    for move in path:
        guard();frames=model.apply(frames,move)
        if frames is None:raise ValueError('rigid.invalid')
    if model.shape_code(frames)!=root:raise ValueError('rigid.invalid')
    return tuple(path)
