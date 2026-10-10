"""Geometry and sticker permutations for vertex and face turning puzzles.

All moves act on the entered stickers. No scramble log is needed to reconstruct
a state. Geometry is expressed in units of the body's inradius.
"""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
import math

EPS = 1e-7


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def scale(a, k):
    return tuple(k*x for x in a)


def unit(a):
    return scale(a, 1/math.sqrt(dot(a, a)))


def key(a):
    return tuple(round(x, 6) for x in a)


def mean(points):
    return tuple(sum(p[i] for p in points)/len(points) for i in range(3))


def rotate(point, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    return add(add(scale(point, c), scale(cross(axis, point), s)),
               scale(axis, dot(axis, point)*(1-c)))


def clip(poly, axis, bound):
    """Clip a convex polygon to dot(axis, p) <= bound."""
    out = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        da, db = dot(axis, a)-bound, dot(axis, b)-bound
        if da <= EPS:
            out.append(a)
        if (da < -EPS and db > EPS) or (db < -EPS and da > EPS):
            t = da/(da-db)
            out.append(add(a, scale(add(b, scale(a, -1)), t)))
    clean = []
    for p in out:
        if not clean or key(p) != key(clean[-1]):
            clean.append(p)
    if len(clean)>1 and key(clean[0])==key(clean[-1]):
        clean.pop()
    if len(clean)<3:
        return ()
    area = sum(math.sqrt(dot(cross(add(clean[i], scale(clean[0], -1)),
                                  add(clean[i+1], scale(clean[0], -1))),
                             cross(add(clean[i], scale(clean[0], -1)),
                                   add(clean[i+1], scale(clean[0], -1)))))
               for i in range(1,len(clean)-1))
    return tuple(clean) if area>EPS else ()


TETRA = tuple(unit(p) for p in ((-1,-1,-1),(-1,1,1),(1,-1,1),(1,1,-1)))
CUBE = ((0,1,0),(1,0,0),(0,0,1),(0,-1,0),(-1,0,0),(0,0,-1))
PHI = (1+math.sqrt(5))/2
# Standard minx face names: U F L BL BR R FR FL DL B DR D.
_H=1/math.sqrt(5)
_R=2/math.sqrt(5)
DODECA = ((0.,1.,0.),) + tuple(
    (_R*math.sin(i*2*math.pi/5),_H,_R*math.cos(i*2*math.pi/5))
    for i in (0,4,3,2,1)) + tuple(
    (_R*math.sin(i*2*math.pi/5+math.pi/5),-_H,
     _R*math.cos(i*2*math.pi/5+math.pi/5)) for i in (0,4,3,2,1)) + ((0.,-1.,0.),)


@lru_cache(maxsize=4)
def body(normals):
    vertices = {}
    for a,b,c in combinations(normals,3):
        det = dot(a,cross(b,c))
        if abs(det)<EPS:
            continue
        p = scale(add(add(cross(b,c),cross(c,a)),cross(a,b)),1/det)
        if all(dot(n,p)<=1+EPS for n in normals):
            vertices[key(p)] = p
    faces = []
    for normal in normals:
        points = [p for p in vertices.values() if abs(dot(normal,p)-1)<EPS]
        centre = mean(points)
        u = unit(add(points[0],scale(centre,-1)))
        v = cross(normal,u)
        points.sort(key=lambda p:math.atan2(dot(add(p,scale(centre,-1)),v),
                                           dot(add(p,scale(centre,-1)),u)))
        faces.append(tuple(points))
    return tuple(faces)


@dataclass(frozen=True)
class Move:
    axis: int
    layer: int = 0
    amount: int = 1

    def inverse(self, order):
        return Move(self.axis,self.layer,(-self.amount)%order)


@dataclass(frozen=True)
class Spec:
    kind: str
    n: int
    normals: tuple
    axes: tuple
    cuts: tuple
    turn_order: int
    even_minx: bool = False


def specification(kind, n):
    if kind == 'megaminx' and 2<=n<=13:
        k=n//2
        cuts = (.7,) if n==3 else tuple(.64+.36*i/k for i in range(k))
        return Spec(kind,n,DODECA,DODECA,cuts,5,n%2==0)
    if kind == 'pyraminx' and 2<=n<=7:
        return Spec(kind,n,TETRA,tuple(scale(p,-1) for p in TETRA),
                    tuple(-1+4*i/n for i in range(1,n)),3)
    if kind == 'moyu' and 3<=n<=7:
        # Commercial orders count segments along an edge. Odd towers are
        # HMT, Master HMT and Elite HMT; even towers remove the middle edge
        # and the centres abutting it from the next odd tower.
        # HMT face cuts stay on the shallow side of the body's centre.
        # Inradius-normalised depths: Master F90/F60, Elite F90/F65/F40.
        # A symmetric +/- distribution instead cuts through the face centre,
        # producing an inverted triangle (five) or a hexagon (seven).
        cuts = {3:(0.,),4:(0.,1/3),5:(0.,1/3),
                6:(0.,5/18,5/9),7:(0.,5/18,5/9)}[n]
        return Spec(kind,n,TETRA,TETRA,cuts,3)
    if kind == 'skewb' and n in (3,5,7):
        # Commercial skewb orders count the segments per edge: odd orders
        # 3/5/7 correspond to 1/2/3 cuts (Skewb, Master Skewb, Elite Skewb).
        cuts = {3:(0.,),5:(-.275,.275),7:(-.38,0.,.38)}[n]
        return Spec(kind,n,CUBE,tuple(scale(p,-1) for p in TETRA),cuts,3)
    raise ValueError('Unsupported puzzle order')


@dataclass(frozen=True)
class Sticker:
    piece: int
    face: int
    polygon: tuple
    patches: tuple = ()


@dataclass(frozen=True)
class Geometry:
    spec: Spec
    stickers: tuple
    pieces: tuple
    centres: tuple
    permutations: tuple
    layers: tuple

    def __post_init__(self):
        object.__setattr__(self, "_perm_cache", {})

    def permutation(self, move):
        order = self.spec.turn_order
        amount = move.amount % order
        key = (move.axis, move.layer, amount)
        cache = self._perm_cache
        result = cache.get(key)
        if result is None:
            perm = self.permutations[move.axis][move.layer]
            result = tuple(range(len(perm)))
            for _ in range(amount):
                result = tuple(map(perm.__getitem__, result))
            cache[key] = result
        return result


def _cut_skin(spec):
    fragments=[]
    planes=tuple((axis,d) for axis in spec.axes for d in spec.cuts)
    for face,polygon in enumerate(body(spec.normals)):
        cells=[polygon]
        for axis,d in planes:
            cells=[part for cell in cells for part in (
                clip(cell,axis,d),clip(cell,scale(axis,-1),-d)) if part]
        for cell in cells:
            p=mean(cell)
            signature=tuple(dot(axis,p)>d+EPS for axis,d in planes)
            fragments.append((signature,face,cell))
    return fragments


def _even_geometry(n,kind='megaminx'):
    """Remove mid-edges and edge-aligned centres from the next odd order.

    The retained orbits are invariant under the exact odd-order layer moves.
    Removed face regions are distributed among adjacent retained stickers;
    they do not introduce extra, independently movable pieces.
    """
    odd=geometry(kind,n+1)
    spec=specification(kind,n)
    kept=[]
    faces=body(spec.normals)
    for i,indices in enumerate(odd.pieces):
        if len(indices)==3:
            kept.append(i)
        elif len(indices)==2:
            a,b=(spec.normals[odd.stickers[j].face] for j in indices)
            if abs(dot(cross(a,b),odd.centres[i]))>EPS:
                kept.append(i)
        else:
            s=odd.stickers[indices[0]]
            normal=spec.normals[s.face]
            radial=add(odd.centres[i],scale(normal,-dot(normal,odd.centres[i])))
            if dot(radial,radial)<EPS:
                continue
            poly=faces[s.face]
            directions=[add(mean((a,b)),scale(normal,-1))
                        for a,b in zip(poly,poly[1:]+poly[:1])]
            aligned=any(dot(cross(radial,d),cross(radial,d))<EPS*EPS
                        and dot(radial,d)>0 for d in directions)
            if not aligned:
                kept.append(i)
    piece_map={old:new for new,old in enumerate(kept)}
    retained=[j for i in kept for j in odd.pieces[i]]
    sticker_map={old:new for new,old in enumerate(retained)}
    sides=len(faces[0])
    expected=len(faces)*sides*(n//2)**2
    if len(retained)!=expected:
        raise ValueError('Kilominx retained-orbit count mismatch')
    permutations=[]
    layers=[]
    for axis_perms in odd.permutations:
        new_perms=[]
        new_layers=[]
        for perm in axis_perms:
            if any(perm[i] not in sticker_map for i in retained):
                raise ValueError('Kilominx orbit is not invariant under a turn')
            new=tuple(sticker_map[perm[i]] for i in retained)
            if new==tuple(range(len(new))):
                continue
            new_perms.append(new)
            new_layers.append(tuple(sorted({piece_map[odd.stickers[i].piece]
                                           for i in retained if perm[i]!=i})))
        permutations.append(tuple(new_perms))
        layers.append(tuple(new_layers))
    # Even faces have one quadrilateral sector per vertex. Transport one
    # sector assignment using body symmetries to keep moves and shapes equal.
    k=n//2
    face0=faces[0]
    normal0=spec.normals[0]
    directions=tuple(unit(add(v,scale(normal0,-1))) for v in face0)
    source_x=directions[0]
    source_y=cross(normal0,source_x)
    a=face0[0]
    b,c=mean((a,face0[1])),mean((a,face0[-1]))
    def at(u,v):
        return add(add(scale(a,(1-u)*(1-v)),scale(b,u*(1-v))),
                   add(scale(c,(1-u)*v),scale(normal0,u*v)))
    cells=[]
    for row in range(k):
        for col in range(k):
            poly=(at(col/k,row/k),at((col+1)/k,row/k),
                  at((col+1)/k,(row+1)/k),at(col/k,(row+1)/k))
            count=3 if row==col==0 else (2 if row==0 or col==0 else 1)
            cells.append((poly,count))
    source=[]
    for j in retained:
        if odd.stickers[j].face!=0:
            continue
        radial=add(mean(odd.stickers[j].polygon),scale(normal0,-1))
        sector=max(range(sides),key=lambda i:dot(radial,directions[i]))
        if sector==0:
            source.append(j)
    if len(source)!=k*k:
        raise ValueError('Kilominx sector does not match its retained orbits')
    assignments={}
    pairs=sorted((sum((a-b)**2 for a,b in zip(mean(poly),mean(odd.stickers[j].polygon))),i,j)
                 for i,(poly,count) in enumerate(cells) for j in source
                 if len(odd.pieces[odd.stickers[j].piece])==count)
    used=set()
    for _,i,j in pairs:
        if i not in assignments and j not in used:
            assignments[i]=j
            used.add(j)
    centres={key(mean(odd.stickers[j].polygon)):j for j in retained}
    polygons={}
    for face,vertices in enumerate(faces):
        normal=spec.normals[face]
        for vertex in vertices:
            x=unit(add(vertex,scale(normal,-1)))
            y=cross(normal,x)
            def transform(p):
                return add(add(scale(x,dot(p,source_x)),scale(y,dot(p,source_y))),
                           scale(normal,dot(p,normal0)))
            for i,(poly,_) in enumerate(cells):
                point=transform(mean(odd.stickers[assignments[i]].polygon))
                target=centres.get(key(point))
                if target is None:
                    target=min(retained,key=lambda j:sum((a-b)**2 for a,b in
                               zip(point,mean(odd.stickers[j].polygon))))
                    if sum((a-b)**2 for a,b in zip(point,mean(odd.stickers[target].polygon)))>1e-9:
                        raise ValueError('Kilominx sector symmetry failed')
                polygons[target]=tuple(transform(p) for p in poly)
    if len(polygons)!=len(retained):
        raise ValueError('Kilominx quadrilateral partition is incomplete')
    stickers=tuple(Sticker(piece_map[odd.stickers[j].piece],odd.stickers[j].face,
                           polygons[j]) for j in retained)
    pieces=tuple(tuple(sticker_map[j] for j in odd.pieces[i]) for i in kept)
    return Geometry(spec,stickers,pieces,tuple(odd.centres[i] for i in kept),
                    tuple(permutations),tuple(layers))


@lru_cache(maxsize=4)
def geometry(kind,n):
    spec=specification(kind,n)
    if spec.even_minx:
        return _even_geometry(n)
    if kind=='moyu' and n in (4,6):
        return _even_geometry(n,kind)
    fragments=_cut_skin(spec)
    groups=defaultdict(list)
    for signature,face,poly in fragments:
        if n==2 and kind=='pyraminx' and not any(signature):
            signature=('centre',face)
        groups[signature].append((face,poly))
    stickers=[]
    pieces=[]
    centres=[]
    for group in groups.values():
        piece=len(pieces)
        indices=[]
        vertices={key(p):p for _,poly in group for p in poly}
        centres.append(mean(tuple(vertices.values())))
        for face,poly in sorted(group):
            indices.append(len(stickers))
            stickers.append(Sticker(piece,face,poly))
        pieces.append(tuple(indices))
    centre_index={key(p):i for i,p in enumerate(centres)}
    face_index={key(p):i for i,p in enumerate(spec.normals)}
    sticker_index={(s.piece,s.face):i for i,s in enumerate(stickers)}
    all_perms=[]
    all_layers=[]
    angle=2*math.pi/spec.turn_order
    for axis in spec.axes:
        point_perm=[]
        for p in centres:
            q=key(rotate(p,axis,angle))
            if q not in centre_index:
                # Rounded centroid errors can straddle the last decimal.
                candidates=[(sum((a-b)**2 for a,b in zip(rotate(p,axis,angle),c)),i)
                            for i,c in enumerate(centres)]
                distance,j=min(candidates)
                if distance>1e-9:
                    raise ValueError('Geometry is not closed under a legal turn')
                point_perm.append(j)
            else:
                point_perm.append(centre_index[q])
        normal_perm=[face_index[key(rotate(normal,axis,angle))] for normal in spec.normals]
        projections=[dot(axis,p) for p in centres]
        if n==2 and kind=='pyraminx':
            corner=max((i for i,p in enumerate(pieces) if len(p)==3),key=lambda i:projections[i])
            # Mini Pyraminx has four independent tips and fixed face centres.
            band={corner}
            bands=[band]
        else:
            thresholds=sorted(spec.cuts,reverse=True)
            bands=[]
            upper=float('inf')
            for lower in thresholds:
                bands.append({i for i,p in enumerate(projections) if lower+EPS<p<upper-EPS})
                upper=lower
        axis_perms=[]
        kept=[]
        for band in bands:
            if not band:
                continue
            if {point_perm[i] for i in band}!=band:
                raise ValueError('A layer is not invariant under its rotation')
            perm=tuple(sticker_index[(point_perm[s.piece],normal_perm[s.face])]
                       if s.piece in band else i for i,s in enumerate(stickers))
            if len(set(perm))!=len(perm):
                raise ValueError('Turn must be a bijection')
            if perm!=tuple(range(len(perm))):
                axis_perms.append(perm)
                kept.append(tuple(sorted(band)))
        all_perms.append(tuple(axis_perms))
        all_layers.append(tuple(kept))
    return Geometry(spec,tuple(stickers),tuple(pieces),tuple(centres),
                    tuple(all_perms),tuple(all_layers))


class PolyhedralPuzzle:
    def __init__(self,kind,n,colors=None):
        self.geometry=geometry(kind,n)
        self.puzzle_kind=kind
        self.n=n
        self.colors=list(colors if colors is not None else
                         (s.face for s in self.geometry.stickers))
        if len(self.colors)!=len(self.geometry.stickers):
            raise ValueError('Wrong sticker count')

    @classmethod
    def solved(cls,kind,n):
        return cls(kind,n)

    def clone(self):
        return type(self)(self.puzzle_kind,self.n,self.colors)

    def apply_move(self,move):
        perm=self.geometry.permutation(move)
        colors=self.colors
        result=[0]*len(colors)
        for source,destination in enumerate(perm):
            result[destination]=colors[source]
        self.colors=result
        return self

    def is_solved(self):
        return len(self.colors)==len(self.geometry.stickers) and all(
            color==s.face for color,s in zip(self.colors,self.geometry.stickers))

    def moves(self):
        return tuple(Move(axis,layer) for axis,layers in enumerate(self.geometry.layers)
                     for layer in range(len(layers)))

    def entered(self):
        """Rebuild an input state using only its painted facelets."""
        return type(self)(self.puzzle_kind,self.n,self.colors)
