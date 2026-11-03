"""Closed display surfaces of the sphere-cut Copter model.

These surfaces display the Boolean solids. Clearance still uses analytic
regions, never this triangle approximation. Internal spherical faces follow
the same cuts; no black rectangular backing plates substitute for them.
"""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,dot,add,scale,unit,cross,mean,triangulate
from cube.curvy_copter import CopterState,cuts
from cube.spherical_surfaces import outline


def _sphere_face(mask,index):
    sphere=cuts()[index];planes=[]
    for normal in CUBE:planes.append((normal,1-dot(normal,sphere.centre)))
    for j,other in enumerate(cuts()):
        if j==index:continue
        delta=add(other.centre,scale(sphere.centre,-1));distance=math.sqrt(dot(delta,delta))
        normal=scale(delta,-1/distance)
        bound=(other.radius**2-sphere.radius**2-distance**2)/(2*distance)
        if not mask&(1<<j):normal=scale(normal,-1);bound=-bound
        planes.append((normal,bound))
    active=[]
    for normal,bound in planes:
        if bound<=-sphere.radius+1e-9:return ()
        if bound<sphere.radius-1e-9:active.append((normal,bound))
    try:boundary=outline(tuple(active),sphere.radius,segments=180)
    except ValueError as exc:
        if str(exc)=='Spherical panel has no boundary':return ()
        raise
    if len(boundary)<3:return ()
    # These patches are star-shaped from this inward spherical hub. A
    # boundary-only triangulation can put a whole curved internal triangle
    # onto the same body plane as a coloured sticker, hiding the sticker.
    hub=scale(unit(mean(boundary)),sphere.radius)
    if any(dot(n,hub)>h+1e-8 for n,h in active):raise ValueError('Copter sphere patch is not star-shaped')
    result=[]
    sign=1 if mask&(1<<index) else -1
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):
        curved=(hub,a,b)
        if dot(cross(add(a,scale(hub,-1)),add(b,scale(hub,-1))),hub)<1e-14:continue
        # Check display spokes independently of analytic collision geometry.
        for endpoint in (a,b,scale(unit(add(a,b)),sphere.radius)):
            for t in (.25,.5,.75):
                sample=scale(unit(add(scale(hub,1-t),scale(endpoint,t))),sphere.radius)
                if any(dot(n,sample)>h+1e-6 for n,h in active):raise ValueError('Copter sphere fan leaves its solid')
        normal=scale(unit(mean(curved)),sign)
        points=tuple(add(sphere.centre,p) for p in curved)
        if sign<0:points=tuple(reversed(points))
        result.append((points,normal,-1))
    return tuple(result)


@lru_cache(maxsize=1)
def surfaces():
    cube=CopterState();result=[]
    for home,mask in enumerate(cube.signatures):
        parts=[]
        for slot,(owner,face,polygon) in enumerate(cube.panels):
            if owner==home:
                parts.extend((tri,CUBE[face],slot) for tri in triangulate(polygon,CUBE[face]))
        for index in range(len(cuts())):parts.extend(_sphere_face(mask,index))
        result.append(tuple(parts))
    return tuple(result)
