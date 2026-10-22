"""QiYi O2: a single rigid coloured cage and six travelling centre discs.

The modern retail version has no coloured hidden edges. Its observable
state is the 24 rotations of the six centres relative to the fixed cage.
"""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,Spec,Geometry,Sticker,body,key,rotate,cross,add,scale


def specification():
    return Spec('o2',1,CUBE,CUBE,(),4)


@lru_cache(maxsize=1)
def geometry():
    spec=specification();stickers=[]
    frames=[]
    for face,normal in enumerate(CUBE):
        u=(1.,0.,0.) if not normal[0] else (0.,0.,1.)
        v=cross(normal,u)
        def point(x,y):return add(normal,add(scale(u,x),scale(v,y)))
        circle=tuple((math.cos(i*math.tau/48),math.sin(i*math.tau/48)) for i in range(48))
        inner=tuple(point(.69*x,.69*y) for x,y in circle)
        outer=tuple(point(.985*x/max(abs(x),abs(y)),.985*y/max(abs(x),abs(y))) for x,y in circle)
        patches=tuple((outer[i],outer[(i+1)%48],inner[(i+1)%48],inner[i]) for i in range(48))
        frames.append((inner,outer))
        stickers.append(Sticker(0,face,tuple(body(CUBE)[face]),patches))
    for face,(inner,outer) in enumerate(frames):
        # Keep the disc in the face plane; shrink only its radial component
        # so the black circular joint remains visible at thumbnail size.
        normal=CUBE[face]
        disc=tuple(add(normal,scale(add(p,scale(normal,-1)),.96)) for p in inner)
        stickers.append(Sticker(face+1,face,disc))
    permutations=[];layers=[]
    face_index={key(n):i for i,n in enumerate(CUBE)}
    for axis in CUBE:
        permutation=list(range(12));moving=[]
        for face,normal in enumerate(CUBE):
            destination=face_index[key(rotate(normal,axis,math.pi/2))]
            permutation[6+face]=6+destination
            if destination!=face:moving.append(face+1)
        permutations.append((tuple(permutation),));layers.append((tuple(moving),))
    return Geometry(spec,tuple(stickers),(tuple(range(6)),)+tuple((6+i,) for i in range(6)),
                    ((0.,0.,0.),)+CUBE,tuple(permutations),tuple(layers))


def outlines():
    g=geometry();result=[]
    for i,s in enumerate(g.stickers):
        if i<6:
            outer=body(CUBE)[i];inner=g.stickers[i+6].polygon
            result.append(tuple(zip(outer,outer[1:]+outer[:1]))+tuple(zip(inner,inner[1:]+inner[:1])))
        else:result.append(tuple(zip(s.polygon,s.polygon[1:]+s.polygon[:1])))
    return tuple(result)


def is_solved(colors):
    return len(colors)==12 and all(c>=0 for c in colors) and len(set(colors[:6]))==6 and tuple(colors[:6])==tuple(colors[6:])
