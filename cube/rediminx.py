"""Rediminx's raised dodecahedral shell, cut by twenty vertex planes.

The five facets of a raised face are patches, not additional pieces.
Slot identities remain shared with the Dinominx mechanism.
"""
from collections import defaultdict, Counter
from functools import lru_cache
import math
from cube.polyhedral import (geometry as base_geometry,Spec,Sticker,Geometry,
                            body,mean,add,scale,dot,key,clip,cross,unit)

RAISE=1.15
CUT=.79/math.sqrt((5+2*math.sqrt(5))/15)


def _boundary(patches):
    """Cancel shared facet edges, including subdivided collinear edges."""
    points={key(p):p for patch in patches for p in patch}
    edges=Counter()
    for patch in patches:
        for a,b in zip(patch,patch[1:]+patch[:1]):
            v=add(b,scale(a,-1));length=dot(v,v)
            if length<1e-16:continue
            splits={0.:a,1.:b}
            for p in points.values():
                delta=add(p,scale(a,-1));t=dot(delta,v)/length
                if 1e-8<t<1-1e-8 and dot(cross(delta,v),cross(delta,v))<1e-16:
                    splits[t]=p
            ordered=[splits[t] for t in sorted(splits)]
            for p,q in zip(ordered,ordered[1:]):edges[tuple(sorted((key(p),key(q))))]+=1
    adjacent=defaultdict(list)
    for (a,b),count in edges.items():
        if count==1:adjacent[a].append(b);adjacent[b].append(a)
    if not adjacent or any(len(v)!=2 for v in adjacent.values()):
        raise ValueError('Rediminx panel boundary is not closed')
    start=min(adjacent);previous=None;current=start;result=[]
    while True:
        result.append(points[current])
        nxt=next(v for v in adjacent[current] if v!=previous)
        previous,current=current,nxt
        if current==start:break
        if len(result)>len(adjacent):raise ValueError('Rediminx boundary repeats')
    if len(result)!=len(adjacent):raise ValueError('Rediminx panel has multiple boundaries')
    return tuple(result)


@lru_cache(maxsize=1)
def rediminx_geometry():
    source=base_geometry('dinominx',3);s=source.spec
    spec=Spec('rediminx',3,s.normals,s.axes,(CUT,),s.turn_order)
    fragments=defaultdict(lambda:defaultdict(list))
    for face,poly in enumerate(body(spec.normals)):
        peak=scale(mean(poly),RAISE)
        for a,b in zip(poly,poly[1:]+poly[:1]):
            cells=[(a,b,peak)]
            for axis in spec.axes:
                cells=[p for cell in cells for p in
                       (clip(cell,axis,CUT),clip(cell,scale(axis,-1),-CUT)) if p]
            for cell in cells:
                signature=tuple(dot(axis,mean(cell))>CUT+1e-7 for axis in spec.axes)
                fragments[signature if any(signature) else ('centre',face)][face].append(cell)
    by_faces={tuple(sorted(source.stickers[i].face for i in piece)):p
              for p,piece in enumerate(source.pieces)}
    stickers=[None]*len(source.stickers);centres=[None]*len(source.pieces)
    slots={(sticker.piece,sticker.face):i for i,sticker in enumerate(source.stickers)}
    for group in fragments.values():
        piece=by_faces[tuple(sorted(group))]
        centres[piece]=mean(tuple({key(v):v for patches in group.values()
                                   for poly in patches for v in poly}.values()))
        for face,patches in group.items():
            polygon=_boundary(patches)
            normal=cross(add(polygon[1],scale(polygon[0],-1)),
                         add(polygon[2],scale(polygon[0],-1)))
            if dot(normal,s.normals[face])<0:polygon=tuple(reversed(polygon))
            stickers[slots[piece,face]]=Sticker(piece,face,polygon,tuple(patches))
    if any(s is None for s in stickers):raise ValueError('Incomplete Rediminx shell')
    return Geometry(spec,tuple(stickers),source.pieces,tuple(centres),source.permutations,source.layers)


@lru_cache(maxsize=1)
def skin():
    return tuple(tuple((poly,unit(cross(add(poly[1],scale(poly[0],-1)),
                                       add(poly[2],scale(poly[0],-1)))),())
                       for poly in sticker.patches) for sticker in rediminx_geometry().stickers)
