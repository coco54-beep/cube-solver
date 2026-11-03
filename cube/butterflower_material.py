"""Clover edge spheres with the user's confirmed radius-one corner cuts.

The body is [-1,1]^3. Unlike the deeper DWG Flower, the edge sphere centres
are the edge midpoints and both edge and corner radii are exactly 1.0.
"""
import math
from functools import lru_cache
from cube.polyhedral import CUBE,EDGE_AXES,OCTA,Spec,scale
from cube.curved_partition import SphereCut,shell
from cube.spherical_cells import Arrangement,Plane

AXES=EDGE_AXES+OCTA
CORNER_RADIUS=1.0


@lru_cache(maxsize=1)
def cuts():
    return (tuple(SphereCut(scale(n,math.sqrt(2)),1.) for n in EDGE_AXES)
            +tuple(SphereCut(scale(n,math.sqrt(3)),CORNER_RADIUS) for n in OCTA))


@lru_cache(maxsize=1)
def panels():return shell(Spec('butterflower-radius-one',3,CUBE,AXES,(),360),cuts())


def fingerprint():
    import hashlib
    return hashlib.sha256(repr((cuts(),panels())).encode('ascii')).hexdigest()


def build_masks():
    visible=tuple(dict.fromkeys(m for m,f,p in panels()))
    all_masks=set(Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts()).positive_masks())
    if not set(visible)<=all_masks:raise ValueError('Butterflower panel has no material')
    return visible+tuple(sorted(all_masks-set(visible)))


@lru_cache(maxsize=1)
def structure():
    import json,zlib
    from pathlib import Path
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/butterflower_regular_material.bin').read_bytes()))
    masks=tuple(data['masks']);owners={m:i for i,m in enumerate(masks)};display=panels()
    if (data['version']!=1 or data['source']!=fingerprint() or len(owners)!=len(masks)
            or any(type(m) is not int or m not in range(1<<20) for m in masks)
            or not {m for m,f,p in display}<=set(masks)):
        raise ValueError('Butterflower material certificate does not match its cuts')
    return masks,masks,tuple((owners[m],f,p) for m,f,p in display)
