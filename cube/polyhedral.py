"""Geometry and sticker permutations for vertex and face turning puzzles.

All moves act on the entered stickers. No scramble log is needed to reconstruct
a state. Geometry is expressed in units of the body's inradius.
"""
from collections import Counter, defaultdict
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
OCTA = TETRA + tuple(scale(p, -1) for p in TETRA)
CUBE = ((0,1,0),(1,0,0),(0,0,1),(0,-1,0),(-1,0,0),(0,0,-1))
EDGE_AXES = tuple(unit(add(a,b)) for a,b in combinations(CUBE,2) if dot(a,b)==0)
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
    axis_steps: tuple = ()
    axis_cuts: tuple = ()
    bounds: tuple = ()

    def step(self,axis):
        return self.axis_steps[axis] if self.axis_steps else 1

    def order(self,axis):
        return self.turn_order//self.step(axis)


def body_faces(spec):
    return body(tuple(scale(n,1/d) for n,d in zip(spec.normals,spec.bounds))) if spec.bounds else body(spec.normals)


# Four-colour Dino: white and yellow on opposite face pairs, red and blue on
# the remaining opposite pair. Face order is CUBE (U,R,F,D,L,B); the palette
# order is the one used by the entry screen (yellow, red, blue, white).
DINO4_FACE_COLORS=(3,0,1,3,0,2)


def solved_colors(cube):
    """Solved sticker colours, honouring the four-colour Dino mapping."""
    if getattr(cube,'puzzle_kind',None)=='dino4':
        return tuple(DINO4_FACE_COLORS[sticker.face] for sticker in cube.geometry.stickers)
    return tuple(sticker.face for sticker in cube.geometry.stickers)


@lru_cache(maxsize=1)
def _skewb_ultimate_axes():
    """The eight dodecahedron vertices forming Skewb Ultimate's inscribed cube.

    The puzzle turns around the cube corners; those eight directions are a
    subset of the dodecahedron's twenty vertices, but are not axis-aligned.
    Find the subset whose pairwise distances form a cube: twelve edges,
    twelve face diagonals and four body diagonals.
    """
    vertices=[]
    seen=set()
    for face in body(DODECA):
        for vertex in face:
            k=key(vertex)
            if k not in seen:
                seen.add(k)
                vertices.append(unit(vertex))
    for subset in combinations(range(len(vertices)),8):
        counts=Counter(round(sum((a-b)**2 for a,b in zip(vertices[i],vertices[j])),6)
                       for i,j in combinations(subset,2))
        if len(counts)==3 and sorted(counts.values())==[4,12,12]:
            return tuple(vertices[i] for i in subset)
    raise ValueError('No inscribed cube found for the Skewb Ultimate axes')


def specification(kind, n):
    if kind in ('petal_tetrahedron', 'petal_tetrahedron_nocentre') and n == 3:
        from cube.petal_icosahedron import petal_geometry
        return petal_geometry(kind == 'petal_tetrahedron', solid='tetrahedron').spec
    if kind in ('petal_icosahedron', 'petal_icosahedron_nocentre') and n == 3:
        from cube.petal_icosahedron import petal_geometry
        return petal_geometry(kind == 'petal_icosahedron').spec
    if kind == 'war_drum':
        from cube.war_drum import drum_specification
        return drum_specification(n)
    if kind == 'pentahedron':
        from cube.prism import prism_specification
        return prism_specification(n)
    if kind == 'void_minx' and n == 3:
        # Void Megaminx: the ordinary third-order Megaminx with its twelve
        # single-sticker centres removed. The retained pieces keep the exact
        # Megaminx move orbits.
        return Spec(kind, n, DODECA, DODECA, (.7,), 5)
    if kind == 'skewb_ultimate' and n == 3:
        # Skewb Ultimate: a dodecahedron turned around the eight inscribed-cube
        # corners. The zero-depth cuts give eight three-sticker corners and
        # six four-sticker centres.
        return Spec(kind, n, DODECA, _skewb_ultimate_axes(), (0.,)*8, 3)
    if kind == 'ivy' and n == 3:
        from cube.ivy import ivy_specification
        return ivy_specification()
    if kind == 'blossom' and n == 3:
        from cube.blossom import blossom_specification
        return blossom_specification()
    if kind=='icosahedron' and n in (2,3,4,5):
        normals=tuple({key(unit(v)):unit(v) for face in body(DODECA) for v in face}.values())
        # The supplied Raphaël Royal Icosamate has five layers and 500
        # triangular stickers. Its family turns around the twelve vertices.
        # Opposite vertex cuts give barycentric divisions of each face;
        # a/3 is the standard Regular Astrominx depth.
        a=3*.18759247376021
        cuts=tuple(a*(2*i/n-1) for i in range(1,n))
        return Spec(kind,n,normals,DODECA,cuts,5)
    if kind=='football' and n in (3,5):
        from cube.football import football_specification
        return football_specification(n)
    if kind == 'clover' and n == 3:
        return Spec(kind, n, CUBE, EDGE_AXES, (1.,), 2)
    if kind == 'void_cube' and n == 3:
        return Spec(kind, n, CUBE, CUBE, (-1/3, 1/3), 4)
    if kind == 'void_tower' and n == 3:
        return Spec(kind, n, TETRA, TETRA, (0.,), 3)
    if kind == 'fto' and n in (2, 3, 4):
        cuts = {2: (0.,), 3: (1/3,), 4: (0., .5)}[n]
        return Spec(kind, n, OCTA, OCTA, cuts, 3)
    if kind == 'eight_petals' and n == 3:
        return Spec(kind, n, CUBE, OCTA, (1/math.sqrt(3),), 3)
    if kind == 'dino' and n == 2:
        # Dino: twelve two-colour edges, all eight corner axes, no corners.
        return Spec(kind, n, CUBE, OCTA, (1/math.sqrt(3),), 3)
    if kind == 'dino4' and n == 2:
        # Four-colour Dino: the same twelve-edge mechanism as the Dino, with
        # white/yellow on opposite face pairs and red/blue on the third pair.
        return Spec(kind, n, CUBE, OCTA, (1/math.sqrt(3),), 3)
    if kind == 'dino' and n in (4,6):
        # Lattice/Master Dino: retain the eight Dino axes. Subdivide the
        # corner-side region with additional shallow cuts; there is no
        # bisecting cut. Catalogue orders 4/6 belong to this Dino family.
        layers=n//2
        cuts=tuple((1+2*i/layers)/math.sqrt(3) for i in range(layers))
        return Spec(kind,n,CUBE,OCTA,cuts,3)
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
        object.__setattr__(self, "_inv_cache", {})

    def permutation(self, move):
        order = self.spec.turn_order
        amount = move.amount % order
        step=self.spec.step(move.axis)
        if amount%step:
            raise ValueError('This face cannot turn by that angle')
        key = (move.axis, move.layer, amount)
        cache = self._perm_cache
        result = cache.get(key)
        if result is None:
            perm = self.permutations[move.axis][move.layer]
            result = tuple(range(len(perm)))
            for _ in range(amount//step):
                result = tuple(map(perm.__getitem__, result))
            cache[key] = result
        return result

    def inverse_permutation(self, move):
        """Destination-indexed permutation, cached alongside ``permutation``."""
        order = self.spec.turn_order
        amount = move.amount % order
        key = (move.axis, move.layer, amount)
        cache = self._inv_cache
        result = cache.get(key)
        if result is None:
            perm = self.permutation(move)
            inv = [0] * len(perm)
            for source, destination in enumerate(perm):
                inv[destination] = source
            result = tuple(inv)
            cache[key] = result
        return result


def _cut_skin(spec):
    fragments=[]
    planes=tuple((axis,d) for i,axis in enumerate(spec.axes)
                 for d in (spec.axis_cuts[i] if spec.axis_cuts else spec.cuts))
    for face,polygon in enumerate(body_faces(spec)):
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
    if kind in ('petal_tetrahedron', 'petal_tetrahedron_nocentre') and n == 3:
        from cube.petal_icosahedron import petal_geometry
        return petal_geometry(kind == 'petal_tetrahedron', solid='tetrahedron')
    if kind in ('petal_icosahedron', 'petal_icosahedron_nocentre') and n == 3:
        from cube.petal_icosahedron import petal_geometry
        return petal_geometry(kind == 'petal_icosahedron')
    spec=specification(kind,n)
    if kind == 'void_tower':
        return _without_centres(geometry('moyu', n), spec)
    if kind == 'void_minx':
        return _without_centres(geometry('megaminx', n), spec)
    if spec.even_minx:
        return _even_geometry(n)
    if kind=='moyu' and n in (4,6):
        return _even_geometry(n,kind)
    if kind=='blossom':
        from cube.blossom import blossom_skin
        fragments=blossom_skin(spec)
    elif kind=='ivy':
        from cube.ivy import ivy_skin
        fragments=ivy_skin(spec)
    else:
        fragments=(_clover_skin(spec) if kind=='clover' else
               _redi_skin(spec) if kind=='eight_petals' else _cut_skin(spec))
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
    for axis_id,axis in enumerate(spec.axes):
        angle=2*math.pi/spec.order(axis_id)
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
        if kind=='blossom':
            from cube.blossom import edge_caps
            cap,radius=edge_caps()[axis_id]
            bands=[{i for i,p in enumerate(centres)
                    if dot(add(p,scale(cap,-1)),add(p,scale(cap,-1)))<radius*radius-EPS}]
        elif kind=='clover':
            cap=scale(axis,math.sqrt(2))
            bands=[{i for i,p in enumerate(centres)
                    if dot(add(p,scale(cap,-1)),add(p,scale(cap,-1)))<1-EPS}]
        elif n==2 and kind=='pyraminx':
            corner=max((i for i,p in enumerate(pieces) if len(p)==3),key=lambda i:projections[i])
            # Mini Pyraminx has four independent tips and fixed face centres.
            band={corner}
            bands=[band]
        else:
            thresholds=sorted(spec.axis_cuts[axis_id] if spec.axis_cuts else spec.cuts,reverse=True)
            bands=[]
            upper=float('inf')
            for lower in thresholds:
                bands.append({i for i,p in enumerate(projections) if lower+EPS<p<upper-EPS})
                upper=lower
            if kind=='skewb':
                # Cuts split the complete diagonal into ncuts+1
                # physical regions. Include the opposite outer cap too:
                # omitting it is a generating-set convention, but prevents
                # direct touch turns of that side in the interactive model.
                bands.append({i for i,p in enumerate(projections) if p<upper-EPS})
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
    result=Geometry(spec,tuple(stickers),tuple(pieces),tuple(centres),
                    tuple(all_perms),tuple(all_layers))
    if kind == 'war_drum' and n % 2 == 0:
        from cube.war_drum import drum_even_geometry
        return drum_even_geometry(result, spec)
    if kind == 'eight_petals':
        return _flower_geometry(result, spec)
    if kind in ('clover','blossom','ivy'):
        return _patch_faces(result)
    return _without_centres(result, spec) if kind == 'void_cube' else result


def _without_centres(source, spec):
    """Remove whole centre pieces while retaining exact closed move orbits."""
    kept=tuple(i for i, slots in enumerate(source.pieces) if len(slots)>1)
    piece_index={p:i for i,p in enumerate(kept)}
    retained=tuple(s for s,sticker in enumerate(source.stickers) if sticker.piece in piece_index)
    index={s:i for i,s in enumerate(retained)}
    stickers=tuple(Sticker(piece_index[source.stickers[s].piece], source.stickers[s].face,
                           source.stickers[s].polygon,source.stickers[s].patches) for s in retained)
    pieces=tuple(tuple(index[s] for s in source.pieces[p]) for p in kept)
    permutations=tuple(tuple(tuple(index[perm[s]] for s in retained) for perm in axis)
                       for axis in source.permutations)
    layers=tuple(tuple(tuple(piece_index[p] for p in layer if p in piece_index) for layer in axis)
                 for axis in source.layers)
    return Geometry(spec,stickers,pieces,tuple(source.centres[p] for p in kept),permutations,layers)


def _redi_skin(spec):
    """Twenty Redi pieces: eight fixed-position corners and twelve edges.

    Each face has four corner triangles and four edge pentagons meeting at
    its centre. Cutting all eight planes instead would invent fixed centres.
    Piece signatures use physical home positions, not colour or face number.
    """
    fragments = []
    for face, poly in enumerate(body(spec.normals)):
        centre = mean(poly)
        def toward(a, b):
            return add(scale(a, .75), scale(b, .25))
        for i, vertex in enumerate(poly):
            previous, following = poly[i-1], poly[(i+1) % 4]
            fragments.append((('corner', key(vertex)), face,
                              (vertex, toward(vertex, following), toward(vertex, previous))))
            end = following
            edge = (toward(vertex, end), toward(end, vertex),
                    toward(end, poly[(i+2) % 4]), centre, toward(vertex, previous))
            fragments.append((('edge', key(mean((vertex, end)))), face, edge))
    return fragments


def _clover_skin(spec):
    """Spherical edge cuts: twelve two-colour caps, 24 single-colour leaves.

    A radius-one sphere at each edge midpoint intersects its two faces in
    quarter circles through the face centre and adjacent cube vertices.
    Unlike Redi, a normal move rotates an edge cap by 180 degrees.
    """
    fragments=[]
    for face,vertices in enumerate(body(spec.normals)):
        centre=mean(vertices)
        def arc(edge,corner):
            u,v=add(centre,scale(edge,-1)),add(corner,scale(edge,-1))
            return tuple(add(edge,add(scale(u,math.cos(t)),scale(v,math.sin(t))))
                         for t in (i*math.pi/24 for i in range(13)))
        for i,corner in enumerate(vertices):
            nxt,previous=vertices[(i+1)%4],vertices[i-1]
            before,after=mean((corner,previous)),mean((corner,nxt))
            first,second=arc(before,corner),arc(after,corner)
            leaf=first+tuple(reversed(second[:-1]))
            if dot(cross(add(leaf[1],scale(leaf[0],-1)),
                         add(mean(leaf),scale(leaf[0],-1))),spec.normals[face])<0:
                leaf=tuple(reversed(leaf))
            fragments.append((('leaf',face,key(corner)),face,leaf))
            left=arc(before,corner)
            right=arc(mean((nxt,vertices[(i+2)%4])),nxt)
            cap=(corner,nxt)+tuple(reversed(right[:-1]))+left[1:-1]
            fragments.append((('edge',key(after)),face,cap))
    return fragments


def _patch_faces(source):
    stickers=[]
    for s in source.stickers:
        patches=triangulate(s.polygon,source.spec.normals[s.face])
        stickers.append(Sticker(s.piece,s.face,s.polygon,patches))
    return Geometry(source.spec,tuple(stickers),source.pieces,source.centres,
                    source.permutations,source.layers)


def triangulate(polygon,normal):
    """Triangulate concave face outlines without filling another piece's area."""
    points=[]
    for point in polygon:
        if not points or key(points[-1])!=key(point):
            points.append(point)
    if len(points)>1 and key(points[0])==key(points[-1]):
        points.pop()
    def side(a,b,c):
        return dot(cross(add(b,scale(a,-1)),add(c,scale(a,-1))),normal)
    if sum(dot(cross(a,b),normal) for a,b in zip(points,points[1:]+points[:1]))<0:
        points.reverse()
    triangles=[]
    while len(points)>3:
        for i,b in enumerate(points):
            a,c=points[i-1],points[(i+1)%len(points)]
            turn=side(a,b,c)
            if abs(turn)<1e-10:
                points.pop(i)
                break
            if turn<0:
                continue
            others=[p for j,p in enumerate(points)
                    if j not in ((i-1)%len(points),i,(i+1)%len(points))]
            if any(min(side(a,b,p),side(b,c,p),side(c,a,p))>=-1e-10 for p in others):
                continue
            triangles.append((a,b,c))
            points.pop(i)
            break
        else:
            raise ValueError('Flower outline cannot be triangulated without overlap')
    if len(points)==3 and side(*points)>1e-10:
        triangles.append(tuple(points))
    return tuple(triangles)


def _flower_geometry(source, spec):
    """Partition each square into eight leaves with shared curved seams.

    Source piece IDs, mechanical centres and permutations remain intact.
    Eight Petals uses Redi mechanics; edge-turning Clover has a separate skin.
    """
    piece_positions={tuple(0 if abs(v)<EPS else (1 if v>0 else -1) for v in p):i
                     for i,p in enumerate(source.centres)}
    polygons={}
    for face, vertices in enumerate(body(spec.normals)):
        centre=mean(vertices)
        def curved_path(corner, neighbour):
            # The physical corner is the circle centre; corner-to-face-centre
            # is exactly half the square's diagonal. Intersect the adjoining
            # edge with this circle instead of forcing an edge midpoint.
            radial=add(centre,scale(corner,-1))
            radius=math.sqrt(dot(radial,radial))
            u=unit(add(neighbour,scale(corner,-1)))
            v=unit(radial)
            cosine=dot(u,v)
            tangent=unit(add(v,scale(u,-cosine)))
            angle=math.acos(max(-1,min(1,cosine)))
            a=add(corner,scale(u,radius))
            arc=tuple(add(corner,add(scale(u,radius*math.cos(t)),
                                     scale(tangent,radius*math.sin(t))))
                      for t in (angle*i/20 for i in range(21)))
            # Both adjoining polygons share the exact hub and edge endpoints.
            return (a,)+arc[1:-1]+(centre,)
        for i,corner in enumerate(vertices):
            nxt=vertices[(i+1)%4]
            before=vertices[i-1]
            first=curved_path(corner,nxt)
            other=curved_path(nxt,corner)
            second=curved_path(before,corner)
            # Neighbouring corner circles bound this corner's patch. Using
            # its own circle here would overlap the adjacent corner patches.
            poly=(corner,)+other+tuple(reversed(second[:-1]))
            polygons[(piece_positions[tuple(round(v) for v in corner)],face)]=poly
            poly=tuple(reversed(first+tuple(reversed(other[:-1]))))
            position=tuple(round(v) for v in mean((corner,nxt)))
            polygons[(piece_positions[position],face)]=poly
    stickers=[]
    for sticker in source.stickers:
        poly=polygons[(sticker.piece,sticker.face)]
        patches=triangulate(poly,spec.normals[sticker.face])
        stickers.append(Sticker(sticker.piece,sticker.face,poly,patches))
    return Geometry(spec,tuple(stickers),source.pieces,source.centres,
                    source.permutations,source.layers)


class PolyhedralPuzzle:
    def __init__(self,kind,n,colors=None):
        self.geometry=geometry(kind,n)
        self.puzzle_kind=kind
        self.n=n
        self.colors=list(colors if colors is not None else solved_colors(self))
        if len(self.colors)!=len(self.geometry.stickers):
            raise ValueError('Wrong sticker count')

    @classmethod
    def solved(cls,kind,n):
        return cls(kind,n)

    def clone(self):
        return type(self)(self.puzzle_kind,self.n,self.colors)

    def apply_move(self,move):
        inverse=self.geometry.inverse_permutation(move)
        self.colors=list(map(self.colors.__getitem__,inverse))
        return self

    @property
    def color_count(self):
        return 4 if self.puzzle_kind == 'dino4' else len(self.geometry.spec.normals)

    def is_solved(self):
        if self.puzzle_kind == 'dino4':
            return (len(self.colors)==len(self.geometry.stickers) and
                    all(color==DINO4_FACE_COLORS[sticker.face]
                        for color,sticker in zip(self.colors,self.geometry.stickers)))
        if self.puzzle_kind == 'void_cube':
            from solver.polyhedral import _body_frames, _transform
            faces={key(normal):i for i,normal in enumerate(self.geometry.spec.normals)}
            return any(all(color==faces[key(_transform(frame,self.geometry.spec.normals[s.face]))]
                           for color,s in zip(self.colors,self.geometry.stickers))
                       for frame in _body_frames(self.puzzle_kind,self.n))
        return len(self.colors)==len(self.geometry.stickers) and all(
            color==s.face for color,s in zip(self.colors,self.geometry.stickers))

    def moves(self):
        return tuple(Move(axis,layer,self.geometry.spec.step(axis)) for axis,layers in enumerate(self.geometry.layers)
                     for layer in range(len(layers)))

    def entered(self):
        """Rebuild an input state using only its painted facelets."""
        return type(self)(self.puzzle_kind,self.n,self.colors)
