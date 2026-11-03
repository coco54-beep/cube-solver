"""Raised dial surfaces; logical sticker identities stay independent of skin.

pCubes Time Machine.xml: W=.4, WC=1.3*W, RC=.9*W.
Coordinates here use W=1. The inner opening follows our entry model.
"""
from functools import lru_cache
import math
from cube.dial_beans import time_geometry, face_point
from cube.polyhedral import CUBE, add, scale, cross, unit

RADIUS = .9
HEIGHT = 1.3


def point(face, radius, angle, height):
    return add(face_point(face,radius*math.cos(angle),radius*math.sin(angle)),
               scale(CUBE[face],height-1))


@lru_cache(maxsize=1)
def skin():
    rows=[]
    for i,sticker in enumerate(time_geometry().stickers):
        if i<24:
            rows.append(tuple((p,CUBE[sticker.face],()) for p in sticker.patches))
            continue
        face=(i-24)//12;number=(i-24)%12
        angles=[math.radians(60-30*number)+j*math.pi/36 for j in range(7)]
        cap=tuple(point(face,.45,t,HEIGHT) for t in reversed(angles))+tuple(
                  point(face,RADIUS,t,HEIGHT) for t in angles)
        patches=[(cap,CUBE[face],())]
        for radius,sign in ((RADIUS,1),(.45,-1)):
            for a,b in zip(angles,angles[1:]):
                patch=(point(face,radius,a,1),point(face,radius,b,1),
                       point(face,radius,b,HEIGHT),point(face,radius,a,HEIGHT))
                normal=scale(unit(add(point(face,1,(a+b)/2,1),scale(CUBE[face],-1))),sign)
                if sign<0:patch=tuple(reversed(patch))
                patches.append((patch,normal,()))
        # Radial faces become visible while the neighbouring half turns away.
        for t,sign in ((angles[0],-1),(angles[-1],1)):
            patch=(point(face,.45,t,1),point(face,RADIUS,t,1),
                   point(face,RADIUS,t,HEIGHT),point(face,.45,t,HEIGHT))
            normal=scale(unit(cross(CUBE[face],add(point(face,1,t,1),scale(CUBE[face],-1)))),sign)
            if sign>0:patch=tuple(reversed(patch))
            patches.append((patch,normal,()))
        rows.append(tuple(patches))
    return tuple(rows)


@lru_cache(maxsize=1)
def outlines():
    """Only top boundaries and vertical sector seams, no facet grid."""
    result=[]
    from renderer.polyhedral_view import outlines as ordinary_outlines
    flat=ordinary_outlines('time_machine',2)
    for i,patches in enumerate(skin()):
        if i<24:result.append(flat[i]);continue
        cap=patches[0][0]
        edges=list(zip(cap,cap[1:]+cap[:1]))
        face=(i-24)//12;number=(i-24)%12
        for t in (math.radians(60-30*number),math.radians(90-30*number)):
            edges.append((point(face,RADIUS,t,1),point(face,RADIUS,t,HEIGHT)))
        result.append(tuple(edges))
    return tuple(result)
