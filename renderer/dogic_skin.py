"""Dogic's inset triangular tiles and three inlays on each rigid centre.

Black Y-shaped inlay separators are visible plastic, not extra movable pieces.
The twenty-colour option keeps the same three inlays with one logical colour.
"""
from functools import lru_cache
import math
from cube.polyhedral import add,scale,cross,dot,unit,clip,mean
from cube.expanded_polyhedra import dogic_geometry,dogic_physical_layout


def inset(poly,normal,gap):
    result=poly
    for a,b in zip(poly,poly[1:]+poly[:1]):
        inward=unit(cross(normal,add(b,scale(a,-1))))
        result=clip(result,scale(inward,-1),-dot(inward,a)-gap)
    return result


def rounded(poly,fraction=.10):
    result=[]
    for i,p in enumerate(poly):
        before=add(scale(p,1-fraction),scale(poly[i-1],fraction))
        after=add(scale(p,1-fraction),scale(poly[(i+1)%len(poly)],fraction))
        for j in range(5):
            t=j/4
            result.append(add(add(scale(before,(1-t)**2),scale(p,2*t*(1-t))),scale(after,t*t)))
    return tuple(result)


@lru_cache(maxsize=2)
def skin(kind):
    g=dogic_geometry(kind);normals,parts,_=dogic_physical_layout()
    edge=math.dist(parts[0][1][1],parts[0][1][2])*2
    result=[]
    for s in g.stickers:
        face,whole,owner=parts[s.piece]
        if owner is None and kind=='dogic_20':
            pivot=mean(whole)
            regions=tuple((pivot,whole[i-1],whole[i]) for i in range(3))
        else:regions=(s.polygon,)
        result.append(tuple(rounded(inset(poly,normals[face],edge*.012)) for poly in regions))
    return tuple(result)
