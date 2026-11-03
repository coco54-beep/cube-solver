"""Six-sector Cheese cylinders, matching the user's two/three-layer models.

The original one-layer Hungarian Cheese is a different puzzle. These models
have independently rotating 60-degree horizontal layers and 180-degree
half-cylinder flips. Each wedge owns one rim sticker and, on the outside
layers, one cap sticker. Mesh triangles never become input stickers.
"""
from functools import lru_cache
import math
from cube.polyhedral import Spec,Sticker,mean,unit
from cube.expanded_polyhedra import assemble

KINDS={'rubik_cheese':2,'cheese_3':3}
SEGMENTS=12
HALF_HEIGHT=.5


def point(theta,y):return (math.sin(theta),y,math.cos(theta))


@lru_cache(maxsize=2)
def cheese_geometry(kind):
    n=KINDS[kind]
    height=HALF_HEIGHT
    caps=((0.,1.,0.),(0.,-1.,0.))
    rim=tuple(point((i+.5)*math.pi/3,0.) for i in range(6))
    axes=caps+tuple(point(i*math.pi/3+math.pi/2,0.) for i in range(3))
    spec=Spec(kind,n,caps+rim,axes,(),6,axis_steps=(1,1,3,3,3),
              bounds=(height,height)+(1.,)*6)
    panels=[];pieces=[];centres=[]
    for layer in range(n):
        lo=-height+2*height*layer/n;hi=lo+2*height/n
        for sector in range(6):
            a=sector*math.pi/3;b=a+math.pi/3;p=len(pieces);indices=[]
            if layer in (0,n-1):
                y=hi if layer==n-1 else lo
                polygon=((0.,y,0.),)+tuple(point(a+(b-a)*j/SEGMENTS,y) for j in range(SEGMENTS+1))
                if layer==0:polygon=tuple(reversed(polygon))
                indices.append(len(panels));panels.append(Sticker(p,0 if layer==n-1 else 1,polygon))
            polygon=tuple(point(a+(b-a)*j/SEGMENTS,lo) for j in range(SEGMENTS+1))+tuple(
                point(b-(b-a)*j/SEGMENTS,hi) for j in range(SEGMENTS+1))
            indices.append(len(panels));panels.append(Sticker(p,sector+2,polygon))
            pieces.append(tuple(indices));centres.append(point((a+b)/2,(lo+hi)/2))
    selected=[tuple({l*6+s for s in range(6)} for l in reversed(range(n))),
              tuple({l*6+s for s in range(6)} for l in range(n))]
    for boundary in range(3):
        selected.append(({l*6+s for l in range(n) for s in range(6)
                          if math.sin((s+.5-boundary)*math.pi/3)>1e-7},))
    return assemble(spec,panels,pieces,centres,selected)


@lru_cache(maxsize=2)
def skin(kind):
    rows=[]
    for sticker in cheese_geometry(kind).stickers:
        if sticker.face<2:
            normal=(0.,1. if sticker.face==0 else -1.,0.)
            rows.append(((sticker.polygon,normal,(normal,)*len(sticker.polygon)),));continue
        polygon=sticker.polygon
        lower=polygon[:SEGMENTS+1];upper=tuple(reversed(polygon[SEGMENTS+1:]))
        patches=[]
        for j in range(SEGMENTS):
            quad=(lower[j],lower[j+1],upper[j+1],upper[j])
            normal=unit(mean(tuple((x,0.,z) for x,y,z in quad)))
            patches.append((quad,normal,tuple(unit((x,0.,z)) for x,y,z in quad)))
        rows.append(tuple(patches))
    return tuple(rows)


def goal_colors(kind):return tuple(s.face for s in cheese_geometry(kind).stickers)


@lru_cache(maxsize=2)
def housing(kind):
    """Black horizontal/radial cut faces close each wedge during animation."""
    n=KINDS[kind];height=HALF_HEIGHT;rows=[]
    for layer in range(n):
        lo=-height+2*height*layer/n;hi=lo+2*height/n
        for sector in range(6):
            a=sector*math.pi/3;b=a+math.pi/3;piece=layer*6+sector
            for y,sign in ((lo,-1),(hi,1)):
                poly=((0.,y,0.),)+tuple(point(a+(b-a)*j/SEGMENTS,y) for j in range(SEGMENTS+1))
                rows.append((piece,poly,(0.,float(sign),0.)))
            for theta,sign in ((a,-1),(b,1)):
                poly=((0.,lo,0.),point(theta,lo),point(theta,hi),(0.,hi,0.))
                rows.append((piece,poly,(sign*math.cos(theta),0.,-sign*math.sin(theta))))
    return tuple(rows)
