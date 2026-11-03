"""Drawing3 exterior and its cubic-symmetric CSG material extension.

CAD fixes the exterior seams, not the manufacturer's internal tracks.
The conditional radial/Cartesian cuts define hidden material for geometric
clearance checks. These solid tests do not certify manufactured internal rails.
"""
import math,json,zlib,hashlib
from pathlib import Path
from functools import lru_cache
from cube.polyhedral import CUBE,EDGE_AXES,OCTA,scale,dot,key
from cube.curved_partition import SphereCut
from cube.spherical_cells import Plane,residual

CAD_SHA256='b586334c54c1e8d5190dc74df428245a7856968a8af380cdad004c7755f2081c'
CENTRAL_RADIUS=2.799999438923789/5
AXES=EDGE_AXES+OCTA
DIAGONALS=tuple(n for n in OCTA if next(v for v in n if abs(v)>1e-8)>0)
CARTESIAN=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))


@lru_cache(maxsize=1)
def cuts():
    return (tuple(SphereCut(scale(n,2.),math.sqrt(5-2*math.sqrt(2))) for n in EDGE_AXES)
            +tuple(Plane(n,0.) for n in DIAGONALS+CARTESIAN)
            +(SphereCut((0.,0.,0.),math.sqrt(1+CENTRAL_RADIUS**2)),))


def group(mask):
    edge=mask&4095;count=edge.bit_count()
    return edge,(mask>>12)&15,((mask>>16)&7) if count==1 else -1,((mask>>19)&1) if count==2 else -1


def point_group(p):return group(sum(1<<i for i,c in enumerate(cuts()) if residual(c,p)<0))


def fingerprint():return hashlib.sha256(repr((CAD_SHA256,cuts(),'conditional-csg-v1')).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def data():
    payload=json.loads(zlib.decompress((Path(__file__).parent/'data/twins_cad_regular.bin').read_bytes()))
    if payload['source']!=fingerprint() or payload['version']!=1:raise ValueError('Twins CAD cache differs from its source')
    return payload


@lru_cache(maxsize=1)
def structure():
    d=data();groups=tuple(tuple(g) for g in d['groups'])
    panels=tuple((h,f,tuple(tuple(p) for p in poly)) for h,f,poly in d['panels'])
    return groups,groups,panels


def frame_action(frame):
    from cube.appearance import ROTATIONS,transform_frame
    proper=tuple(tuple(round(v) for v in col) for col in frame)
    if proper not in ROTATIONS or max(abs(a-b) for u,v in zip(proper,frame) for a,b in zip(u,v))>1e-7:
        raise ValueError('twins.regular_only')
    return canonical_action(proper)


@lru_cache(maxsize=24)
def canonical_action(proper):
    from cube.appearance import transform_frame
    edge_index={key(n):i for i,n in enumerate(EDGE_AXES)}
    face_index={key(n):i for i,n in enumerate(CUBE)}
    edge=tuple(edge_index[key(transform_frame(proper,n))] for n in EDGE_AXES)
    def signed_map(normals):
        indices={key(n):(i,False) for i,n in enumerate(normals)}
        indices.update({key(scale(n,-1)):(i,True) for i,n in enumerate(normals)})
        return tuple(indices[key(transform_frame(proper,n))] for n in normals)
    return edge,signed_map(DIAGONALS),signed_map(CARTESIAN),tuple(face_index[key(transform_frame(proper,n))] for n in CUBE)


@lru_cache(maxsize=5000)
def transform_group(g,action):
    edge,diag,cart,faces=action
    def signed(bits,mapping):return sum(1<<j for i,(j,flip) in enumerate(mapping) if bool(bits&(1<<i))!=flip)
    return (sum(1<<edge[i] for i in range(12) if g[0]&(1<<i)),signed(g[1],diag),
            signed(g[2],cart) if g[2]>=0 else -1,g[3])
