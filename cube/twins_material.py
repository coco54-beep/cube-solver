"""Closed material construction for the labelled Twins geometric profile.

This is not a catalogue alias for the older regular-only skin. Parameters
describe the public geometric prototype. Desktop gate and observation checks
do not establish a complete physical-shell or manufacturer-track match.
"""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,EDGE_AXES,OCTA,body,scale,dot,unit,rotate
from cube.compound_solids import centroid
from cube.crazy_comet import vertices,volume
from cube.mirror_tower import _clip_solid

EDGE_CUT=1.13/(2*math.sqrt(2))
J=math.acos(1/3)
AXES=tuple(unit(v) for v in ((0,1,1),(1,0,1),(0,-1,1),(-1,0,1),(-1,1,0),(1,1,0)))


def partition(cells,normal,bound):
    result=[]
    for faces in cells:
        values=[dot(normal,p)-bound for p in vertices(faces)]
        if max(values)<=1e-8 or min(values)>=-1e-8:result.append(faces);continue
        for sign in (1,-1):
            kept=tuple(_clip_solid(faces,scale(normal,sign),bound*sign))
            if volume(kept)>1e-11:result.append(kept)
    return tuple(result)


def transformed(faces,axis,angle):
    return tuple((tuple(rotate(p,axis,angle) for p in poly),color) for poly,color in faces)


def _construction_turn(cells,axis,angle):
    """Rotate both caps during geometric refinement; retain an undo tag."""
    result=[]
    for faces,tags in cells:
        distance=dot(centroid((faces,)),axis)
        selected=abs(distance)>EDGE_CUT+1e-8
        result.append((transformed(faces,axis,angle) if selected else faces,tags+(selected,)))
    return tuple(result)


@lru_cache(maxsize=1)
def structure():
    shell=tuple((tuple(scale(p,.5) for p in poly),i) for i,poly in enumerate(body(CUBE)))
    cells=(shell,)
    for normal in EDGE_AXES:cells=partition(cells,normal,EDGE_CUT)
    for normal in OCTA:cells=partition(cells,normal,0.)
    # Extra contacts are exposed only in the specified double-cap positions.
    contacts=((0,5,1,-1),(3,4,1,-1),(2,5,1,1),(1,4,1,1),
              (4,0,1,-1),(3,2,1,-1),(5,0,-1,1),(1,2,-1,1),
              (2,3,-1,1),(4,1,1,1),(0,3,1,-1),(5,1,1,-1))
    for a,b,sa,sb in contacts:
        placed=_construction_turn(tuple((faces,()) for faces in cells),AXES[a],sa*J)
        placed=_construction_turn(placed,AXES[b],sb*J);following=[]
        for faces,tags in placed:
            divided=partition((faces,),AXES[a],-EDGE_CUT)
            divided=partition(divided,AXES[a],EDGE_CUT)
            for part in divided:
                if tags[1]:part=transformed(part,AXES[b],-sb*J)
                if tags[0]:part=transformed(part,AXES[a],-sa*J)
                following.append(part)
        cells=tuple(following)
    divided=[]
    for faces in cells:
        centre=centroid((faces,))
        cap_count=sum(dot(n,centre)>EDGE_CUT+1e-8 for n in EDGE_AXES)
        parts=(faces,)
        if cap_count==1:
            for n in ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)):parts=partition(parts,n,0.)
        divided.extend(parts)
    # Small exterior chamfers are plastic, not new turn axes or new colours.
    result=[]
    for faces in divided:
        for n in OCTA:faces=tuple(_clip_solid(faces,n,.5*math.sqrt(3)*.95))
        for n in EDGE_AXES:faces=tuple(_clip_solid(faces,n,.5*math.sqrt(2)*.982))
        if volume(faces)>1e-11:result.append(faces)
    panels=tuple((h,c,p) for h,faces in enumerate(result) for p,c in faces if c>=0)
    return tuple(result),panels
