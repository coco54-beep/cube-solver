"""Closed non-convex rigid pieces represented by convex material fragments.

Fragments are a computational decomposition, never separate puzzle pieces.
Clearance uses the entire union. Coplanar fragment boundaries are removed
before rendering, so tetrahedralization cannot introduce selectable stickers.
"""
from collections import defaultdict
from functools import lru_cache
from cube.polyhedral import add, cross, dot, key, mean, scale, triangulate, unit
from cube.mirror_tower import _clip_solid


def face_normal(poly):
    normal=(0.,0.,0.)
    for a,b in zip(poly,poly[1:]+poly[:1]):normal=add(normal,cross(a,b))
    return unit(normal)


def volume(solid):
    return abs(sum(dot(poly[0],cross(poly[i],poly[i+1]))/6
                   for poly,color in solid for i in range(1,len(poly)-1)))


def centroid(fragments):
    total=0.;weighted=(0.,0.,0.)
    for solid in fragments:
        for poly,color in solid:
            for i in range(1,len(poly)-1):
                a,b,c=poly[0],poly[i],poly[i+1]
                v=dot(a,cross(b,c))/6
                weighted=add(weighted,scale(add(add(a,b),c),v/4));total+=v
    if abs(total)<1e-12:raise ValueError('Empty material cell')
    return scale(weighted,1/total)


@lru_cache(maxsize=4096)
def vertices(fragments):
    return tuple({key(p):p for solid in fragments for poly,color in solid for p in poly}.values())


def tetrahedral_shell(faces):
    """Decompose an outward-oriented shell star-shaped about the origin."""
    result=[];origin=(0.,0.,0.)
    for poly,color in faces:
        for triangle in triangulate(poly,face_normal(poly)):
            a,b,c=triangle
            if dot(a,cross(b,c))<=1e-12:raise ValueError('Shell is not outward star-shaped')
            result.append(((triangle,color),((origin,b,a),-1),
                           ((origin,c,b),-1),((origin,a,c),-1)))
    return tuple(result)


def split(fragments,normal,bound):
    """Partition a whole material union; return negative and positive halves."""
    halves=[[],[]]
    for solid in fragments:
        values=[dot(normal,p)-bound for poly,color in solid for p in poly]
        if max(values)<=1e-9:halves[0].append(solid);continue
        if min(values)>=-1e-9:halves[1].append(solid);continue
        for positive in (0,1):
            kept=tuple(_clip_solid(solid,scale(normal,-1) if positive else normal,
                                   -bound if positive else bound))
            if volume(kept)>1e-12:halves[positive].append(kept)
    return tuple(tuple(parts) for parts in halves)


def boundary(fragments):
    """Cancel internal faces and join coplanar patches, including T-junctions.

    No mesh library or raster tolerance determines piece membership. The
    rounded keys here only join construction vertices for the display shell.
    """
    planes=defaultdict(list)
    for solid in fragments:
        for poly,color in solid:
            normal=face_normal(poly);bound=dot(normal,poly[0])
            sign=next((1 if v>0 else -1 for v in normal if abs(v)>1e-7),1)
            planes[(key(scale(normal,sign)),round(bound*sign,6),color)].append(poly)
    result=[]
    for (_,_,color),polygons in planes.items():
        points={key(p):p for poly in polygons for p in poly};edges=defaultdict(int)
        for poly in polygons:
            for a,b in zip(poly,poly[1:]+poly[:1]):
                delta=add(b,scale(a,-1));length=dot(delta,delta)
                if length<1e-16:continue
                along=[]
                for k,p in points.items():
                    t=dot(add(p,scale(a,-1)),delta)/length
                    if -1e-7<=t<=1+1e-7:
                        error=add(add(a,scale(delta,t)),scale(p,-1))
                        if dot(error,error)<1e-14:along.append((t,k))
                along.sort()
                for (_,u),(_,v) in zip(along,along[1:]):
                    if u==v:continue
                    edges[(u,v)]+=1;edges[(v,u)]-=1
        active={(u,v) for (u,v),count in edges.items() if count>0}
        if any(count>1 for count in edges.values()):raise ValueError('Overlapping material facets')
        while active:
            start,following=min(active);loop=[start];active.remove((start,following))
            while following!=start:
                loop.append(following)
                choices=[v for u,v in active if u==following]
                if len(choices)!=1:raise ValueError('Open or non-manifold material boundary')
                nxt=choices[0];active.remove((following,nxt));following=nxt
            # Remove construction-only points along a straight edge.
            clean=[]
            for i,k in enumerate(loop):
                p=points[k];before=add(p,scale(points[loop[i-1]],-1))
                after=add(points[loop[(i+1)%len(loop)]],scale(p,-1))
                bend=cross(before,after)
                if dot(bend,bend)>1e-16:clean.append(p)
            if len(clean)>=3:result.append((tuple(clean),color))
    return tuple(result)
