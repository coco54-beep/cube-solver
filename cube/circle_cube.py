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
    if kind=='circle_2' and n==2:
        return Spec(kind,2,CUBE,CUBE,(0.,),4)
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


def _cell(poly,r,c,n=3):
    for axis,lo,hi in ((0,-1+c*2/n,-1+(c+1)*2/n),
                       (1,-1+r*2/n,-1+(r+1)*2/n)):
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


@lru_cache(maxsize=2)
def _panels(n=3):
    pieces={}
    # Include diagonal rays so the square boundary has exact corners.
    for i in range(96):
        a,b=i*math.tau/96,(i+1)*math.tau/96
        u,v=(math.cos(a),math.sin(a)),(math.cos(b),math.sin(b))
        inner=tuple((.76*p[0],.76*p[1]) for p in (u,v))
        outer=tuple((p[0]/max(abs(p[0]),abs(p[1])),p[1]/max(abs(p[0]),abs(p[1]))) for p in (u,v))
        for inside,poly in ((True,((0.,0.),inner[0],inner[1])),
                            (False,(inner[0],outer[0],outer[1],inner[1]))):
            for r in range(n):
                for c in range(n):
                    patch=_cell(poly,r,c,n)
                    if patch:pieces.setdefault((inside,r,c),[]).append(patch)
    return tuple((label,_boundary(tuple(patches)),tuple(patches)) for label,patches in sorted(pieces.items()))


def _point(face,p):
    axis,sign,ra,rs,ca,cs=FACE_SPEC[face]
    out=[0.,0.,0.];out[axis]=sign;out[ra]=p[1]*rs;out[ca]=p[0]*cs
    return tuple(out)


@lru_cache(maxsize=16)
def circle_geometry(kind,n=3,anchor=(-1,-1,-1)):
    spec=circle_specification(kind,n)
    one=frozenset() if kind=='circle_2' else PLANETS[kind.removeprefix('crazy_')]
    entries=[]; groups={}
    for faceid,face in enumerate(FACES):
        for (inside,r,c),polygon,patches in _panels(n):
            pos=pos_from_rc(n,face,r,c)
            if kind=='circle_2' and inside:
                # Opposite-face quarter discs are the two caps of one
                # hidden edge. Its mechanical coordinate has zero along
                # the disc normal; it is not a second corner piece.
                pos=tuple(0 if CUBE[faceid][a] else v for a,v in enumerate(pos))
            # Inner sectors are separate physical pieces. The outer shell
            # retains ordinary corner/edge grouping across adjacent faces.
            signature=(('inner',pos) if kind=='circle_2' else ('inner',face,r,c)) if inside else ('outer',pos)
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
    for axis,normal in enumerate(spec.axes):
        selected=[];mapping=[]
        a,sgn=next((a,v) for a,v in enumerate(normal) if v)
        for i,(face,inside,pos,*_) in enumerate(entries):
            if kind=='circle_2':
                # When the anchored corner turns, its core carries the
                # middle-plane hidden edges too, rotating both disc caps.
                moving=(sgn*pos[a]>=0 if inside and anchor[a]==sgn else pos[a]==sgn)
            else:
                moving=pos[a]==sgn and not (inside and face==axis and FACES[axis] not in one)
            if moving:
                target=tuple(round(v) for v in rotate(pos,normal,math.pi/2))
                nf=normalid[key(rotate(CUBE[face],normal,math.pi/2))]
                mapping.append(lookup[nf,inside,target]);selected.append(piece_for[i])
            else:mapping.append(i)
        if len(set(mapping))!=len(mapping):raise ValueError('Circle move is not bijective')
        perms.append((tuple(mapping),));layers.append((tuple(sorted(set(selected))),))
    return Geometry(spec,stickers,pieces,centres,tuple(perms),tuple(layers))


from cube.polyhedral import PolyhedralPuzzle


class Circle2Cube(PolyhedralPuzzle):
    """Circular 2x2 with a travelling anchored corner and paired disc caps."""
    def __init__(self,kind='circle_2',n=2,colors=None,anchor=(-1,-1,-1)):
        super().__init__(kind,n,colors)
        self.anchor=tuple(anchor)
        if len(self.anchor)!=3 or any(v not in (-1,1) for v in self.anchor):
            raise ValueError('Invalid Circle 2x2 anchor')
        self.geometry=circle_geometry(kind,n,self.anchor)

    def clone(self):
        other=type(self)(colors=self.colors,anchor=self.anchor)
        if tuple(self.colors)==self._circle_snapshot:
            other.circle_history=None if self.circle_history is None else list(self.circle_history)
        return other

    def apply_move(self,move):
        normal=self.geometry.spec.axes[move.axis]
        a,sign=next((a,v) for a,v in enumerate(normal) if v)
        moving=self.anchor[a]==sign
        super().apply_move(move)
        if moving:
            self.anchor=tuple(round(v) for v in rotate(self.anchor,normal,move.amount*math.pi/2))
        self.geometry=circle_geometry(self.puzzle_kind,self.n,self.anchor)
        return self

    def restore(self,other):
        self.colors=list(other.colors);self.anchor=other.anchor
        self.geometry=circle_geometry(self.puzzle_kind,self.n,self.anchor)
        self.circle_history=None if other.circle_history is None else list(other.circle_history)
        self._circle_snapshot=tuple(self.colors)

    def entered(self):
        other=self.clone()
        # The labelled anchored corner also identifies core orientation
        # after a fresh manual entry, without needing scramble history.
        for slots in self.geometry.pieces:
            if len(slots)==3 and {self.colors[i] for i in slots}=={3,4,5}:
                other.anchor=tuple(sum(CUBE[self.geometry.stickers[i].face][a] for i in slots) for a in range(3))
                other.geometry=circle_geometry(other.puzzle_kind,2,other.anchor)
                break
        return other

    def is_solved(self):
        return getattr(self,'anchor',(-1,-1,-1))==(-1,-1,-1) and super().is_solved()
