"""Closed Mixup backing shells; generated offline from the reference cut recipe.

The visible skins keep their existing indices. These display polygons do not
replace the engine's independently checked surface-clearance rule.
"""
from functools import lru_cache
from pathlib import Path
import json
import zlib
import hashlib
from cube.appearance import transform_frame
from cube.polyhedral import cross,dot,unit,mean,scale,add,CUBE
from cube.articulated_observation import polygon_key


@lru_cache(maxsize=1)
def _models():
    data=json.loads(zlib.decompress((Path(__file__).resolve().parents[1]/'cube/data/mixup_housings.bin').read_bytes()))
    if data.get('version')!=1:raise ValueError('Unsupported Mixup housing data')
    return data['models']


@lru_cache(maxsize=8)
def skin_fingerprint(kind):
    from cube.articulated import solids
    skins=tuple(tuple((c,polygon_key(p)) for p,c in s.faces if c>=0) for s in solids(kind))
    return hashlib.sha256(repr(skins).encode()).hexdigest()


@lru_cache(maxsize=8)
def _model(kind):
    data=_models()[kind]
    if data.get('skin_mesh')!=skin_fingerprint(kind):raise ValueError('Mixup backing geometry is outdated')
    return data


@lru_cache(maxsize=2048)
def placed_housing(kind,home,pose):
    from cube.articulated import poses
    frame=poses('mixup')[pose]
    return tuple(tuple(transform_frame(frame,p) for p in polygon)
                 for polygon,color in _model(kind)['faces'][home])


def _normal_key(polygon):
    for a,b in zip(polygon[1:],polygon[2:]):
        n=cross(add(a,scale(polygon[0],-1)),add(b,scale(polygon[0],-1)))
        if dot(n,n)>1e-12:
            n=unit(n)
            if dot(n,mean(polygon))<0:n=scale(n,-1)
            return tuple(round(v,4) for v in n)


@lru_cache(maxsize=256)
def _normal_poses(colors,wanted):
    from cube.articulated import poses
    return tuple(i for i,frame in enumerate(poses('mixup'))
                 if tuple(sorted(tuple(round(v,4) for v in transform_frame(frame,CUBE[c])) for c in colors))==wanted)


@lru_cache(maxsize=2048)
def housing_for_panels(kind,piece_key,role):
    """Resolve edited input skins without source IDs or a large pose index."""
    from cube.articulated import solids,poses
    normals=tuple(_normal_key(p) for p in piece_key)
    if None in normals:return ()
    wanted=tuple(sorted(normals))
    for home,solid in enumerate(solids(kind)):
        skins=tuple((p,c) for p,c in solid.faces if c>=0)
        if solid.role!=role or len(skins)!=len(piece_key):continue
        for pose in _normal_poses(tuple(c for p,c in skins),wanted):
            frame=poses('mixup')[pose]
            actual=tuple(sorted(polygon_key(tuple(transform_frame(frame,p) for p in poly)) for poly,c in skins))
            if actual==piece_key:return placed_housing(kind,home,pose)
    return ()
