"""Whole-solid congruences for observation entry and shape restoration.

These placements compare material, not colours or piece labels. A displayed
patch is never sufficient evidence that the complete solid fits a position.
"""
from functools import lru_cache
from cube.polyhedral import add,scale,unit,cross,dot,mean
from cube.appearance import IDENTITY_FRAME,transform_frame
from cube.curvy_copter import inverse_point,frame_key
from cube.crazy_comet import vertices,volume


def points_key(points):return tuple(sorted(tuple(round(v,6) for v in p) for p in points))
def pose_key(frame):return tuple(round(v,6) for col in frame for v in col)


@lru_cache(maxsize=8)
def inventory(factory):
    c=factory();points=tuple(vertices(s) for s in c.solids)
    # Volume centroids remain valid when display faces have been subdivided.
    from cube.compound_solids import centroid
    centres=tuple(centroid((s,)) for s in c.solids)
    slots=tuple(tuple(i for i,(h,f,p) in enumerate(c.panels) if h==home) for home in range(len(points)))
    return c,points,centres,slots


@lru_cache(maxsize=2048)
def placements(factory,home):
    c,points,centres,slots=inventory(factory);centre=centres[home]
    if dot(centre,centre)<1e-14:
        return ((home,IDENTITY_FRAME,tuple((s,s) for s in slots[home])),)
    u=unit(centre)
    p=next(p for p in points[home] if dot(cross(p,u),cross(p,u))>1e-12)
    v=unit(add(p,scale(u,-dot(p,u))));source=(u,v,cross(u,v))
    radius=dot(centre,centre);size=volume(c.solids[home]);result=[];seen=set()
    targets={points_key(poly):i for i,(h,f,poly) in enumerate(c.panels)}
    for destination,qpoints in enumerate(points):
        if len(slots[destination])!=len(slots[home]):continue
        if abs(dot(centres[destination],centres[destination])-radius)>1e-8:continue
        if abs(volume(c.solids[destination])-size)>1e-8:continue
        qu=unit(centres[destination]);qkey=points_key(qpoints)
        for q in qpoints:
            qv=add(q,scale(qu,-dot(q,qu)))
            if dot(qv,qv)<1e-12:continue
            qv=unit(qv);target=(qu,qv,cross(qu,qv))
            frame=tuple(transform_frame(target,inverse_point(source,col)) for col in IDENTITY_FRAME)
            signature=(destination,pose_key(frame))
            if signature in seen:continue
            if points_key(tuple(transform_frame(frame,p) for p in points[home]))!=qkey:continue
            mapping=tuple(targets.get(points_key(tuple(transform_frame(frame,p) for p in c.panels[i][2]))) for i in slots[home])
            if None in mapping or set(mapping)!=set(slots[destination]):continue
            seen.add(signature);result.append((destination,frame,tuple(zip(slots[home],mapping))))
    if not result:raise ValueError('Rigid piece has no resting placement')
    return tuple(result)


@lru_cache(maxsize=2048)
def frame_keys(factory,home):return frozenset(pose_key(f) for d,f,m in placements(factory,home))
