"""Rounded flower puzzle shells with cached shared seams and normals."""
from functools import lru_cache
import math
from cube.polyhedral import geometry, add, scale, cross, dot, unit,clip,CUBE


@lru_cache(maxsize=12000)
def flower_point(point,kind='eight_petals'):
    radius=.16 if kind=='eight_petals' else .10
    extent=1-radius
    core=tuple(max(-extent,min(extent,v)) for v in point)
    delta=add(point,scale(core,-1))
    return add(core,scale(unit(delta),radius))


def flower_normal(point,kind='eight_petals'):
    extent=.84 if kind=='eight_petals' else .90
    core=tuple(max(-extent,min(extent,v)) for v in point)
    return unit(add(point,scale(core,-1)))


@lru_cache(maxsize=3)
def flower_skin(n=3,kind='eight_petals'):
    result=[]
    g=geometry(kind,n)
    for sticker in g.stickers:
        facets=[]
        tangent_axes=[axis for axis in CUBE[:3] if abs(dot(axis,g.spec.normals[sticker.face]))<.5]
        extent=.84 if kind=='eight_petals' else .90
        # Split the rounded rim into small strips; keep flat interiors coarse.
        divisions=(-1,-extent-2*(1-extent)/3,-extent-(1-extent)/3,-extent,
                   extent,extent+(1-extent)/3,extent+2*(1-extent)/3,1)
        for triangle in sticker.patches:
            cells=[triangle]
            for axis in tangent_axes:
                pieces=[]
                for cell in cells:
                    for lo,hi in zip(divisions,divisions[1:]):
                        part=clip(clip(cell,axis,hi),scale(axis,-1),-lo)
                        if part:
                            pieces.append(part)
                cells=pieces
            for cell in cells:
                for i in range(1,len(cell)-1):
                    triangle=(cell[0],cell[i],cell[i+1])
                    points=tuple(flower_point(p,kind) for p in triangle)
                    normal=cross(add(points[1],scale(points[0],-1)),add(points[2],scale(points[0],-1)))
                    if dot(normal,normal)<1e-16:
                        continue
                    if dot(normal,g.spec.normals[sticker.face])<0:
                        normal=scale(normal,-1)
                    facets.append((points,unit(normal),tuple(flower_normal(p,kind) for p in triangle)))
        result.append(tuple(facets))
    return tuple(result)


@lru_cache(maxsize=4000)
def flower_edge(a,b,kind='eight_petals'):
    delta=add(b,scale(a,-1))
    divisions=max(1,min(24,math.ceil(math.sqrt(dot(delta,delta))/.08)))
    return tuple(flower_point(add(a,scale(delta,i/divisions)),kind) for i in range(divisions+1))


@lru_cache(maxsize=3)
def flower_hubs(kind):
    """Small recessed openings at the shared tips, matching the flower cuts."""
    if kind in ('ivy','super_ivy'):
        # Ivy's leaf is solid; it has no flower hub opening at the face centre.
        return ()
    lobes=8 if kind=='eight_petals' else 4
    result=[]
    for normal in CUBE:
        u=next(axis for axis in CUBE[:3] if abs(dot(axis,normal))<.5)
        v=cross(normal,u)
        rim=[]
        for i in range(lobes*4):
            angle=2*math.pi*i/(lobes*4)
            radius=.025+.008*math.cos(lobes*angle)
            rim.append(add(normal,add(scale(u,radius*math.cos(angle)),scale(v,radius*math.sin(angle)))))
        result.append((normal,tuple((normal,a,b) for a,b in zip(rim,rim[1:]+rim[:1]))))
    return tuple(result)
