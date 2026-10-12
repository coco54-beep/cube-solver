"""Clip the twelve-color minx skin against thirty-two football panels."""
from functools import lru_cache
from cube.football import shell_planes,football_point
from cube.polyhedral import geometry,clip,add,scale

@lru_cache(maxsize=1)
def football_skin():
    g=geometry('football',3)
    planes=shell_planes()
    result=[]
    for sticker in g.stickers:
        patches=[]
        for normal,bound,_ in planes:
            poly=sticker.polygon
            for other,other_bound,_ in planes:
                poly=clip(poly,add(scale(other,1/other_bound),scale(normal,-1/bound)),0.)
                if not poly:
                    break
            if poly:
                points=tuple(football_point(p) for p in poly)
                patches.append((points,normal,(normal,)*len(points)))
        result.append(tuple(patches))
    return tuple(result)

@lru_cache(maxsize=3000)
def football_edge(a,b):
    # Include every panel transition, keeping the line on the flat shell.
    planes=shell_planes()
    ts={0.,1.}
    from cube.polyhedral import dot
    delta=add(b,scale(a,-1))
    for i,(n,d,_) in enumerate(planes):
        for m,e,_ in planes[i+1:]:
            normal=add(scale(n,1/d),scale(m,-1/e))
            denominator=dot(normal,delta)
            if abs(denominator)>1e-10:
                t=-dot(normal,a)/denominator
                if 0<t<1:
                    ts.add(t)
    return tuple(football_point(add(a,scale(delta,t))) for t in sorted(ts))
