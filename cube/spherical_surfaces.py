"""Analytic oriented circular boundaries on a sphere clipped by planes."""
from itertools import combinations
import math
from cube.polyhedral import dot,cross,add,scale,unit,key
from cube.curved_partition import arc_steps,radial_remainder


def outline(planes,surface_radius=1.,segments=None):
    """Intersect a sphere with linear halfspaces; return its oriented arcs."""
    points={};incidence=[set() for _ in planes]
    for i,j in combinations(range(len(planes)),2):
        a,ha=planes[i];b,hb=planes[j];cosine=dot(a,b);det=1-cosine*cosine
        if det<1e-12:continue
        centre=add(scale(a,(ha-cosine*hb)/det),scale(b,(hb-cosine*ha)/det))
        r2=radial_remainder(surface_radius**2,dot(centre,centre))
        if r2<-1e-10:continue
        offset=scale(unit(cross(a,b)),math.sqrt(max(0.,r2)))
        for p in (add(centre,offset),add(centre,scale(offset,-1))):
            if all(dot(n,p)<=h+1e-9 for n,h in planes):
                k=key(p);points[k]=p;incidence[i].add(k);incidence[j].add(k)
    edges=[]
    for (normal,height),keys in zip(planes,incidence):
        if len(keys)<2:continue
        centre=scale(normal,height);radius=math.sqrt(surface_radius**2-height**2)
        u=unit(add(points[min(keys)],scale(centre,-1)));v=cross(normal,u)
        angles=sorted((math.atan2(dot(points[k],v),dot(points[k],u))%math.tau,k) for k in keys)
        def point(t):return add(centre,add(scale(u,radius*math.cos(t)),scale(v,radius*math.sin(t))))
        for (lo,start),(hi,end) in zip(angles,angles[1:]+[(angles[0][0]+math.tau,angles[0][1])]):
            if not all(dot(n,point((lo+hi)/2))<=h+1e-9 for n,h in planes):continue
            # Interior lies to the left of cross(radial, plane normal).
            count=(arc_steps(hi-lo,segments) if segments is not None
                   else max(1,math.ceil((hi-lo)*radius/.035)))
            arc=(points[end],)+tuple(point(hi-(hi-lo)*i/count) for i in range(1,count))+(points[start],)
            edges.append((end,start,arc))
    if not edges:raise ValueError('Spherical panel has no boundary')
    pending={start:(end,arc) for start,end,arc in edges}
    if len(pending)!=len(edges):raise ValueError('Spherical panel boundary branches')
    first=min(pending);current=first;outline=[]
    while current in pending:
        current,arc=pending.pop(current);outline.extend(arc[:-1])
        if current==first:break
    if current!=first or pending:raise ValueError('Spherical panel is disconnected')
    return tuple(outline)

