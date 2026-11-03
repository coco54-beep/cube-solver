"""Smooth spherical patches and shared curves for the Ivy ball shell."""
from functools import lru_cache
import math
from cube.polyhedral import add,scale,dot,cross,unit,clip,triangulate

RADIUS=math.sqrt(3)


def point(p):return scale(unit(p),RADIUS)


def _triangles(sticker,normal):
    # Clip the original panel to a shared face grid before projecting it.
    # Refining ear-clipped skinny triangles independently creates T junctions
    # and folded chords on the sphere. Shared cells keep its skin watertight
    # and need fewer triangles, including along the curved sticker boundaries.
    dims=tuple(i for i in range(3) if abs(normal[i])<.5)
    divisions=16
    ranges=tuple(range(max(0,math.floor((min(p[d] for p in sticker.polygon)+1)*divisions/2)),
                       min(divisions,math.ceil((max(p[d] for p in sticker.polygon)+1)*divisions/2)))
                 for d in dims)
    for u in ranges[0]:
        for v in ranges[1]:
            poly=sticker.polygon
            for dim,j in zip(dims,(u,v)):
                axis=tuple(float(i==dim) for i in range(3))
                poly=clip(poly,axis,-1+2*(j+1)/divisions) if poly else ()
                poly=clip(poly,scale(axis,-1),1-2*j/divisions) if poly else ()
            if poly:yield from triangulate(poly,normal)


@lru_cache(maxsize=1)
def skin():
    from cube.yeet_ball import geometry
    g=geometry();result=[]
    for sticker in g.stickers:
        patches=[]
        for tri in _triangles(sticker,g.spec.normals[sticker.face]):
            vertices=tuple(point(p) for p in tri)
            normal=cross(add(vertices[1],scale(vertices[0],-1)),
                         add(vertices[2],scale(vertices[0],-1)))
            if dot(normal,normal)<1e-16:continue
            patches.append((vertices,unit(normal),tuple(unit(p) for p in tri)))
        result.append(tuple(patches))
    return tuple(result)


@lru_cache(maxsize=4096)
def edge(a,b):
    distance=math.sqrt(dot(add(a,scale(b,-1)),add(a,scale(b,-1))))
    count=max(1,math.ceil(distance/.05))
    return tuple(point(add(scale(a,1-i/count),scale(b,i/count))) for i in range(count+1))
