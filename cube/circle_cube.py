"""Circle 3x3 / Crazy Planet: independent inner sectors and outer cubies.

Planet masks are canonical orientations, not claims about factory colour labels.
A zero face holds its own disc stationary; adjacent-layer sectors still move.
"""
import math
from functools import lru_cache
from cube.coordinates import FACE_NORMALS, FACE_SPEC, pos_from_rc
from cube.polyhedral import CUBE, Spec, Geometry, Sticker, mean, rotate, key

FACES = ('U','R','F','D','L','B')
# Six face flags, in FACES order. Mars has three consecutive belt faces;
# Neptune has three mutually adjacent zero faces, meeting at one corner.
PLANETS = {
    'mercury': frozenset('U'),
    'venus': frozenset('UD'),
    'earth': frozenset('UR'),
    'mars': frozenset('URL'),
    'jupiter': frozenset('RFDLB'),
    'saturn': frozenset('RFLB'),
    'uranus': frozenset('FDLB'),
    'neptune': frozenset('DLB'),
}
KINDS = tuple('crazy_'+p for p in PLANETS)


def circle_specification(kind, n=3):
    if n != 3 or kind not in KINDS:
        raise ValueError('Unsupported Circle planet')
    return Spec(kind,3,CUBE,CUBE,(1/3,),4)


def _clip(poly, axis, bound, sign):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=sign*(a[axis]-bound); db=sign*(b[axis]-bound)
        if da >= -1e-10: out.append(a)
        if (da < -1e-10) != (db < -1e-10):
            t=da/(da-db)
            out.append(tuple(a[j]+t*(b[j]-a[j]) for j in range(2)))
    return tuple(out)


def _cell(poly,r,c):
    for axis,lo,hi in ((0,-1+c*2/3,-1+(c+1)*2/3),
                       (1,-1+r*2/3,-1+(r+1)*2/3)):
        poly=_clip(poly,axis,lo,1)
        if len(poly)<3:return ()
        poly=_clip(poly,axis,hi,-1)
        if len(poly)<3:return ()
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))
    return poly if abs(area)>1e-10 else ()


def _boundary(patches):
    edges={}
    points={}
    for patch in patches:
        for a,b in zip(patch,patch[1:]+patch[:1]):
            ka,kb=tuple(round(v,8) for v in a),tuple(round(v,8) for v in b)
            if ka==kb:continue
            points[ka]=a;points[kb]=b
            if (kb,ka) in edges:del edges[kb,ka]
            else:edges[ka,kb]=True
    nxt={a:b for a,b in edges}
    start=next(iter(nxt));cur=start;result=[]
    for _ in range(len(edges)+1):
        result.append(points[cur]);cur=nxt[cur]
        if cur==start:break
    if len(result)!=len(edges):raise ValueError('Circle patch boundary is not continuous')
    return tuple(result)


@lru_cache(maxsize=1)
def _panels():
    pieces={}
    # Include diagonal rays so the square boundary has exact corners.
    for i in range(96):
        a,b=i*math.tau/96,(i+1)*math.tau/96
        u,v=(math.cos(a),math.sin(a)),(math.cos(b),math.sin(b))
        inner=tuple((.76*p[0],.76*p[1]) for p in (u,v))
        outer=tuple((p[0]/max(abs(p[0]),abs(p[1])),p[1]/max(abs(p[0]),abs(p[1]))) for p in (u,v))
        for inside,poly in ((True,((0.,0.),inner[0],inner[1])),
                            (False,(inner[0],outer[0],outer[1],inner[1]))):
            for r in range(3):
                for c in range(3):
                    patch=_cell(poly,r,c)
                    if patch:pieces.setdefault((inside,r,c),[]).append(patch)
    return tuple((label,_boundary(tuple(patches)),tuple(patches)) for label,patches in sorted(pieces.items()))


def _point(face,p):
    axis,sign,ra,rs,ca,cs=FACE_SPEC[face]
    out=[0.,0.,0.];out[axis]=sign;out[ra]=p[1]*rs;out[ca]=p[0]*cs
    return tuple(out)


@lru_cache(maxsize=8)
def circle_geometry(kind,n=3):
    spec=circle_specification(kind,n)
    one=PLANETS[kind.removeprefix('crazy_')]
    entries=[]; groups={}
    for faceid,face in enumerate(FACES):
        for (inside,r,c),polygon,patches in _panels():
            pos=pos_from_rc(3,face,r,c)
            # Inner sectors are separate physical pieces. The outer shell
            # retains ordinary corner/edge grouping across adjacent faces.
            signature=('inner',face,r,c) if inside else ('outer',pos)
            groups.setdefault(signature,[]).append(len(entries))
            entries.append((faceid,inside,pos,tuple(_point(face,p) for p in polygon),
                            tuple(tuple(_point(face,p) for p in patch) for patch in patches)))
    pieces=tuple(tuple(g) for g in groups.values())
    piece_for={s:p for p,slots in enumerate(pieces) for s in slots}
    stickers=tuple(Sticker(piece_for[i],e[0],e[3],e[4]) for i,e in enumerate(entries))
    centres=tuple(mean(tuple(p for s in slots for p in entries[s][3])) for slots in pieces)
    lookup={(face,inside,pos):i for i,(face,inside,pos,*_) in enumerate(entries)}
    normalid={key(normal):i for i,normal in enumerate(CUBE)}
    perms=[];layers=[]
    for axis,normal in enumerate(CUBE):
        selected=[];mapping=[]
        a,sgn=next((a,v) for a,v in enumerate(normal) if v)
        for i,(face,inside,pos,*_) in enumerate(entries):
            moving=pos[a]==sgn and not (inside and face==axis and FACES[axis] not in one)
            if moving:
                target=tuple(round(v) for v in rotate(pos,normal,math.pi/2))
                nf=normalid[key(rotate(CUBE[face],normal,math.pi/2))]
                mapping.append(lookup[nf,inside,target]);selected.append(piece_for[i])
            else:mapping.append(i)
        if len(set(mapping))!=len(mapping):raise ValueError('Circle move is not bijective')
        perms.append((tuple(mapping),));layers.append((tuple(sorted(set(selected))),))
    return Geometry(spec,stickers,pieces,centres,tuple(perms),tuple(layers))
