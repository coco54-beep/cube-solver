"""Flower sphere cuts reconstructed from the user's 10x10 DWG face.

The twelve drawn arcs determine edge centres at twice the unit edge ray,
edge radius sqrt(5-2*sqrt(2)), corner centres at the cube vertices, and
corner radius sqrt(2). All regular turns permute these complete Boolean
cells, including invisible material. Shape turns use the same whole cells
against transformed analytic cuts, rather than an exterior-only proxy.
"""
import math
from functools import lru_cache
from cube.polyhedral import CUBE,OCTA,EDGE_AXES,Spec,scale
from cube.curved_partition import shell as curved_shell,SphereCut
from cube.spherical_cells import Arrangement,Plane,norm2,sub

AXES=EDGE_AXES+OCTA
EDGE_RADIUS=math.sqrt(5-2*math.sqrt(2))
CORNER_RADIUS=math.sqrt(2)


@lru_cache(maxsize=1)
def cuts():
    return (tuple(SphereCut(scale(n,2.),EDGE_RADIUS) for n in EDGE_AXES)
            +tuple(SphereCut(scale(n,math.sqrt(3)),CORNER_RADIUS) for n in OCTA))


def residual(surface,p):return norm2(sub(p,surface.centre))-surface.radius**2


@lru_cache(maxsize=1)
def panels():return curved_shell(Spec('flower-copter-dwg',3,CUBE,AXES,(),360),cuts())


def build_masks():
    display=panels();visible=tuple(dict.fromkeys(m for m,f,p in display))
    arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    all_masks=set(arrangement.positive_masks())
    if not set(visible)<=all_masks:raise ValueError('Flower displayed panel has no whole material')
    return visible+tuple(sorted(all_masks-set(visible)))


def fingerprint():
    import hashlib
    return hashlib.sha256(repr((cuts(),panels())).encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def structure():
    import json,zlib
    from pathlib import Path
    data=json.loads(zlib.decompress((Path(__file__).parent/'data'/'flower_regular_material.bin').read_bytes()))
    signatures=tuple(data['masks']);display=panels();owners={m:i for i,m in enumerate(signatures)}
    if (data['source']!=fingerprint() or data['version']!=1 or len(owners)!=len(signatures)
            or any(type(m) is not int or m not in range(1<<20) for m in signatures)
            or not {m for m,f,p in display}<=set(signatures)):
        raise ValueError('Flower material certificate does not match its cuts')
    return signatures,signatures,tuple((owners[m],f,p) for m,f,p in display)
