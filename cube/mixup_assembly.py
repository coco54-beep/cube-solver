"""Small, colour-independent assemblies made from real Mixup piece skins.

An assembly covers a whole centre/edge position, including both sides of an
edge. Its faces come from real rigid poses, rather than arbitrary rectangles.
"""
from collections import Counter,OrderedDict
from dataclasses import dataclass,replace
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from threading import Lock
from time import monotonic

from cube.articulated import MIXUP_MODELS,poses
from cube.appearance import ROTATIONS,transform_frame
from cube.articulated_observation import new_cube,normal,project,contains,polygon_key,centre2,face_world
from cube.polyhedral import CUBE,dot,clip,cross,add,unit,mean,rotate

EPS=1e-6
_CACHE=OrderedDict()
_LOCK=Lock()
_BUNDLED=None
CATALOG_VERSION=9


def area(points):
    total=(0.,0.,0.)
    for p,q in zip(points,points[1:]+points[:1]):total=add(total,cross(p,q))
    return math.sqrt(dot(total,total))/2


def area2(points):
    return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(points,points[1:]+points[:1])))/2


def _atoms(block):
    x1,y1,x2,y2=block['bounds'];xm=(x1+x2)/2;ym=(y1+y2)/2
    parent=tuple((x,y,0.) for x,y in block['outline']);result=[]
    for left,right in ((x1,xm),(xm,x2)):
        for low,high in ((y1,ym),(ym,y2)):
            poly=parent
            for axis,bound in (((1,0,0),right),((-1,0,0),-left),((0,1,0),high),((0,-1,0),-low)):
                poly=clip(poly,axis,bound)
                if not poly:break
            if poly:
                outline=tuple((x,y) for x,y,_ in poly)
                result.append((centre2(outline),area2(outline)))
    return tuple(result)


@dataclass(frozen=True)
class AssemblyPiece:
    role:str
    panels:tuple
    mask:int
    body:tuple=()
    direction:tuple=()

    @property
    def signature(self):
        return (self.role,tuple(sorted(polygon_key(p) for p in self.panels)),
                tuple(sorted(polygon_key(p) for p in self.body)),
                tuple(round(v,6) for v in self.direction))


@dataclass(frozen=True)
class Assembly:
    key:str
    kind:str
    positions:tuple
    pieces:tuple
    group_key:str=''

    @property
    def counts(self):return Counter(p.role for p in self.pieces)

    def diagram(self,blocks,primary):
        if inner_pattern(self.pieces) is not None and all(p.body for p in self.pieces):
            return _inner_diagram(self.pieces,blocks[primary]['face'])
        return _assembly_diagram(self.pieces,blocks,self.positions,primary)


class AssemblyDiagram(tuple):
    """Face drawings with an optional fixed viewport for orientation previews."""
    def __new__(cls,faces,bounds=None,joined=False):
        result=super().__new__(cls,faces);result.bounds=bounds;result.joined=joined;return result


def _assembly_diagram(pieces,blocks,positions,primary):
    """Draw one assembly, not a copy of every panel in each observation view.

    A centre crossing an edge is one physical face. An edge's two different
    faces remain joined along their real seam in a single coherent view.
    """
    faces=tuple(blocks[i]['face'] for i in positions)
    target=unit(tuple(sum(CUBE[f][i] for f in faces) for i in range(3)))
    if len(faces)==2:
        along=unit(cross(CUBE[faces[0]],CUBE[faces[1]]))
        if next(v for v in along if abs(v)>EPS)<0:along=tuple(-v for v in along)
        eye=unit(tuple(target[i]+.28*along[i] for i in range(3)))
        right=unit(cross(along,eye));up=cross(eye,right)
    else:
        origin,x,y=face_world(((0.,0.),(1.,0.),(0.,1.)),blocks[primary]['face'])
        x=tuple(v-o for v,o in zip(x,origin));y=tuple(v-o for v,o in zip(y,origin))
        eye=unit(tuple(target[i]+.12*x[i]+.18*y[i] for i in range(3)))
        right=unit(cross(y,eye));up=cross(eye,right)
    result=[];seen=set()
    for piece in pieces:
        vertices={polygon_key((p,))[0]:p for poly in piece.panels for p in poly}
        centre=mean(tuple(vertices.values()))
        for world in piece.panels:
            key=polygon_key(world)
            if key in seen or dot(normal(world),eye)<=EPS:continue
            seen.add(key)
            # Inset the complete piece once; independent face insets split a
            # single edge into two apparent blocks and break its shared seam.
            poly=tuple(tuple(centre[i]+.92*(p[i]-centre[i]) for i in range(3)) for p in world)
            result.append((dot(mean(poly),eye),piece.role,tuple((dot(p,right),dot(p,up)) for p in poly)))
    return AssemblyDiagram(((role,poly,None) for _,role,poly in sorted(result,key=lambda p:p[0])),joined=True)


def inner_ridge(piece):
    """The long edge opposite the coloured face, where the black faces meet."""
    if not piece.body or not piece.panels:raise ValueError('observe.invalid')
    panel=piece.panels[0];n=normal(panel)
    points={polygon_key((p,))[0]:p for poly in piece.body for p in poly
            if abs(dot(n,tuple(p[i]-panel[0][i] for i in range(3))))>EPS}
    if len(points)<2:raise ValueError('observe.invalid')
    points=tuple(points[k] for k in sorted(points))
    return max(((p,q) for i,p in enumerate(points) for q in points[i+1:]),
               key=lambda pair:sum((a-b)**2 for a,b in zip(*pair)))


def inner_turn_axis(pieces):
    """Half-turn axis through the fixed ridge's centre, toward the cube origin.

    The ridge is preserved as a line segment (its ends exchange). The radial
    axis is perpendicular to it, so split components exchange along the strip
    on a whole turn. A component's own turn keeps its own ridge segment fixed.
    """
    ridges=tuple(inner_ridge(p) for p in pieces)
    direction=unit(tuple(b-a for a,b in zip(*ridges[0])))
    points=tuple(p for ridge in ridges for p in ridge)
    low=min(points,key=lambda p:dot(p,direction));high=max(points,key=lambda p:dot(p,direction))
    pivot=mean((low,high))
    for p in points:
        offset=tuple(p[i]-pivot[i] for i in range(3))
        if dot(cross(offset,direction),cross(offset,direction))>EPS*EPS:
            raise ValueError('observe.invalid')
    radial=tuple(pivot[i]-dot(pivot,direction)*direction[i] for i in range(3))
    if dot(radial,radial)<EPS*EPS:raise ValueError('observe.invalid')
    return unit(radial),pivot


def _turn_piece(piece,axis,pivot,angle):
    def polygon(poly):
        return tuple(tuple(pivot[i]+v for i,v in enumerate(rotate(
            tuple(p[j]-pivot[j] for j in range(3)),axis,angle))) for p in poly)
    return replace(piece,panels=tuple(polygon(poly) for poly in piece.panels),
                   body=tuple(polygon(poly) for poly in piece.body),
                   direction=rotate(piece.direction,axis,angle) if piece.direction else ())


def inner_direction(cube,home,pose=None):
    solid=cube.solids[home]
    if solid.role!='inner_edge':return ()
    frame=cube.orientations[cube.frames[home] if pose is None else pose]
    for poly,color in solid.faces:
        if color<0:
            n=normal(poly)
            if sum(abs(v)>EPS for v in n)>1:return transform_frame(frame,n)
    return ()


def inner_pattern(pieces):
    """The unsplit strip, or the relative directions of its two components."""
    if not pieces or any(p.role!='inner_edge' for p in pieces):return None
    if len(pieces)==1:return 'whole'
    if len(pieces)!=2 or any(not p.direction for p in pieces):return None
    try:inner_turn_axis(pieces)
    except ValueError:return None
    return 'same' if dot(*(normal(p.panels[0]) for p in pieces))>1-EPS else 'opposite'


def inner_arrangement(pieces):
    """Distinguish the two handed opposite pairs, even after a half turn.

    Turning a whole opposite pair exchanges its coloured panels, but does
    not produce the pair made by flipping the other wedge independently.
    The triple product is unchanged by exchanging the two piece indices.
    """
    pattern=inner_pattern(pieces)
    if pattern!='opposite':return pattern
    first,second=pieces;n=normal(first.panels[0])
    displacement=tuple(b-a for a,b in zip(mean(first.panels[0]),mean(second.panels[0])))
    handedness=dot(cross(n,displacement),first.direction)
    return 'opposite_a' if handedness>0 else 'opposite_b'


def _inner_diagram(pieces,face):
    """An oblique view of the actual wedge bodies, not rectangular arrows."""
    axis=CUBE[face];_,centre=inner_turn_axis(pieces)
    eye=unit((1.8,-2.8,4.5));right=unit(cross((0.,1.,0.),eye));up=cross(eye,right)
    def local(p):
        v=tuple(p[i]-centre[i] for i in range(3))
        x,y=project((v,),face)[0]
        return (x,y,dot(v,axis))
    def screen(p):return (dot(p,right),dot(p,up))
    surfaces=[]
    for piece in pieces:
        ridge=inner_ridge(piece);pivot=mean(ridge)
        along=unit(tuple(b-a for a,b in zip(*ridge)))
        panels={polygon_key(poly) for poly in piece.panels}
        for world in piece.body:
            n=local(tuple(centre[i]+normal(world)[i] for i in range(3)))
            if dot(n,eye)<=EPS:continue
            # Show the seam with an axial inset only. Shrinking about a body
            # centroid would move the very ridge that must stay fixed.
            poly=tuple(local(tuple(p[i]-.04*dot(tuple(p[j]-pivot[j] for j in range(3)),along)*along[i]
                                   for i in range(3))) for p in world)
            role='inner_edge' if polygon_key(world) in panels else 'inner_edge_body'
            surfaces.append((dot(mean(poly),eye),role,tuple(screen(p) for p in poly),None))
    # Both directions share the same framing, anchored to the ridge. Fitting
    # only the currently visible faces would conceal its fixed world position.
    extent=[screen(local(p)) for piece in pieces for version in (piece,half_turn_inner(piece))
            for poly in version.body for p in poly]
    bounds=(min(x for x,y in extent),min(y for x,y in extent),
            max(x for x,y in extent),max(y for x,y in extent))
    return AssemblyDiagram(((role,poly,marker) for _,role,poly,marker in sorted(surfaces,key=lambda s:s[0])),bounds)


def half_turn_inner(piece):
    """Reverse a wedge while fixing its black ridge, not its coloured panel."""
    axis,pivot=inner_turn_axis((piece,))
    return _turn_piece(piece,axis,pivot,math.pi)


def assembly_group(pieces):
    if inner_pattern(pieces) is None:return orientation_key(pieces)
    # Strip direction has a local half-turn symmetry. Keep relative wedge
    # direction in the key, while merging the whole strip's 0/180° choices.
    try:axis,pivot=inner_turn_axis(pieces)
    except ValueError:return orientation_key(pieces)
    flipped=tuple(_turn_piece(piece,axis,pivot,math.pi) for piece in pieces)
    return min(orientation_key(pieces),orientation_key(flipped))


def legacy_inner_sources(kind,blocks,positions):
    """Map v7 face-centred templates to ridge-centred templates for migration.

    Only an exact old template or its recorded half turn is eligible. Real
    imported geometry and unrecognised observations are never reinterpreted.
    """
    options=assemblies(kind,blocks,positions);result={};face=blocks[positions[0]]['face']
    pivot=mean(face_world(blocks[positions[0]]['outline'],face))
    for base in options:
        if any(p.role!='inner_edge' for p in base.pieces):continue
        if any(dot(normal(poly),CUBE[face])<1-EPS for p in base.pieces for poly in p.panels):continue
        for mask in range(1<<len(base.pieces)):
            old=tuple(_turn_piece(p,normal(p.panels[0]),mean(p.panels[0]),math.pi) if mask>>i&1 else p
                      for i,p in enumerate(base.pieces))
            new=tuple(half_turn_inner(p) if mask>>i&1 else p for i,p in enumerate(base.pieces))
            source=Assembly(assembly_key(new),kind,tuple(positions),new,assembly_group(new))
            rotated=tuple(_turn_piece(p,CUBE[face],pivot,-math.pi) for p in old)
            result[assembly_key(old)]=(source,{0:assembly_key(old),2:assembly_key(rotated)})
    return result


@lru_cache(maxsize=256)
def orientation_key(pieces):
    """Only a rotation of the entire assembly may merge two menu choices.

    Bevel bodies retain the relative orientation of multiple inner edges.
    Reflections and independent rotations of a component are not equivalent.
    """
    # A mixed centre can lie on an edge diagonal. A quarter turn about that
    # diagonal is not one of the 24 cube frames. Use a right-handed intrinsic
    # frame so those orientations also share one card, without reflecting or
    # rotating individual components independently.
    vertices={polygon_key((p,))[0]:p for piece in pieces for poly in piece.panels for p in poly}
    radial=mean(tuple(vertices.values()))
    if dot(radial,radial)<EPS*EPS:
        radial=normal(pieces[0].panels[0])
    z=unit(radial);frames=[]
    for point in vertices.values():
        tangent=tuple(point[i]-dot(point,z)*z[i] for i in range(3))
        if dot(tangent,tangent)<EPS*EPS:continue
        x=unit(tangent);y=cross(z,x)
        frames.append(tuple(tuple(axis[i] for axis in (x,y,z)) for i in range(3)))
    signatures=[]
    for frame in frames or ROTATIONS:
        def oriented(poly):
            return tuple(tuple(0. if v==0 else v for v in p)
                         for p in polygon_key(tuple(transform_frame(frame,p) for p in poly)))
        signatures.append(tuple(sorted((piece.role,
            tuple(sorted(oriented(poly) for poly in piece.panels)),
            tuple(sorted(oriented(poly) for poly in piece.body)),
            (tuple(round(v,6) for v in transform_frame(frame,piece.direction))
             if piece.direction else ())) for piece in pieces)))
    return hashlib.sha256(repr(min(signatures)).encode()).hexdigest()[:20]


def assembly_key(pieces):
    signature=tuple(sorted(p.signature for p in pieces))
    return 'assembly_'+hashlib.sha256(repr(signature).encode()).hexdigest()[:20]


@lru_cache(maxsize=8)
def geometry_signature(kind):
    cube=new_cube(kind)
    signature=(tuple((s.role,tuple((color,polygon_key(poly)) for poly,color in s.faces if color>=0 or s.role=='inner_edge')) for s in cube.solids),
               tuple(tuple(round(v,6) for row in frame for v in row) for frame in cube.orientations))
    return hashlib.sha256(repr(signature).encode()).hexdigest()


def _bundled(kind,positions):
    global _BUNDLED
    if _BUNDLED is None:
        try:
            path=Path(__file__).resolve().parent.parent/'assets'/'mixup_assemblies.json'
            data=json.loads(path.read_text(encoding='utf-8'))
            _BUNDLED=data if data.get('version')==CATALOG_VERSION else {}
        except (OSError,ValueError):_BUNDLED={}
    model=_BUNDLED.get('models',{}).get(kind)
    if model is None or model['geometry']!=geometry_signature(kind):return None
    records=model['regions'].get(','.join(map(str,positions)))
    if records is None:return None
    return tuple(Assembly(item['key'],kind,positions,tuple(AssemblyPiece(piece['role'],
        tuple(tuple(tuple(p) for p in poly) for poly in piece['panels']),piece['mask'],
        tuple(tuple(tuple(p) for p in poly) for poly in piece.get('body',())),tuple(piece.get('direction',())))
        for piece in item['pieces']),item['group']) for item in records)


def _local_assemblies(kind,blocks,positions,cancelled=None,seconds=6.,use_bundled=True):
    """Enumerate bounded exact covers using whole physical pieces (max 4)."""
    positions=tuple(sorted(positions));cache_key=('local',kind,positions)
    with _LOCK:
        if cache_key in _CACHE:
            result=_CACHE[cache_key];_CACHE.move_to_end(cache_key);return result
    if use_bundled:
        result=_bundled(kind,positions)
        if result is not None:
            with _LOCK:
                _CACHE[cache_key]=result
                while len(_CACHE)>32:_CACHE.popitem(last=False)
            return result
    deadline=monotonic()+seconds
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline:raise ValueError('mixup.entry_assembly_timeout')
    cube=new_cube(kind);regions=[];offset=0
    for index in positions:
        block=blocks[index];atoms=_atoms(block)
        regions.append((block,atoms,offset));offset+=len(atoms)
    target=(1<<offset)-1;candidates={}
    from cube.mixup import skins_cross
    for home,solid in enumerate(cube.solids):
        if solid.role=='corner':continue
        for pose in range(len(cube.orientations)):
            guard();faces=cube.placed_faces(home,pose);panels=tuple(poly for poly,color in faces if color>=0)
            mask=0;valid=True
            for world in panels:
                n=normal(world);seen=False
                for block,atoms,start in regions:
                    if dot(n,CUBE[block['face']])<=EPS:continue
                    outline=project(world,block['face'])
                    if not all(contains(block['outline'],p) for p in outline):valid=False;break
                    covered=[i for i,(point,_) in enumerate(atoms) if contains(outline,point)]
                    if not covered or abs(sum(atoms[i][1] for i in covered)-area2(outline))>EPS:
                        valid=False;break
                    bits=sum(1<<(start+i) for i in covered)
                    if mask&bits:valid=False;break
                    mask|=bits;seen=True
                if not valid or not seen:valid=False;break
            if valid and mask:
                body=tuple(poly for poly,color in faces) if solid.role=='inner_edge' else ()
                piece=AssemblyPiece(solid.role,panels,mask,body,inner_direction(cube,home,pose))
                candidates.setdefault(piece.signature,piece)
    choices=tuple(sorted(candidates.values(),key=lambda p:p.signature));by_atom=[[] for _ in range(offset)]
    for i,piece in enumerate(choices):
        for bit in range(offset):
            if piece.mask>>bit&1:by_atom[bit].append(i)
    result={};nodes=0;ordinary_edge=blocks[positions[0]]['role']=='edge' and not MIXUP_MODELS[kind][1]
    def visit(covered,chosen):
        nonlocal nodes
        guard();nodes+=1
        if nodes>12000:raise ValueError('mixup.entry_assembly_timeout')
        if covered==target:
            pieces=tuple(choices[i] for i in chosen);counts=Counter(p.role for p in pieces)
            if ordinary_edge:
                if len(pieces)==4 and counts!={'centre':4}:return
                if len(pieces)==3:
                    allowed=({'centre':2,'edge':1},) if MIXUP_MODELS[kind][0]==(4,4,4) else ({'centre':2,'edge':1},{'centre':3})
                    if counts not in allowed:return
            signature=tuple(sorted(p.signature for p in pieces))
            key=assembly_key(pieces)
            pieces=tuple(sorted(pieces,key=lambda p:p.signature))
            result.setdefault(signature,Assembly(key,kind,positions,pieces,assembly_group(pieces)))
            return
        if len(chosen)>=4:return
        available=None
        for bit,indices in enumerate(by_atom):
            if covered>>bit&1:continue
            options=[i for i in indices if not choices[i].mask&covered]
            if not options:return
            if available is None or len(options)<len(available):available=options
        for i in available:
            faces=tuple((poly,0) for poly in choices[i].panels)
            if any(skins_cross(faces,tuple((poly,0) for poly in choices[j].panels)) for j in chosen):continue
            visit(covered|choices[i].mask,chosen+(i,))
    visit(0,())
    ordered=tuple(sorted(result.values(),key=lambda a:(len(a.pieces),tuple(sorted(a.counts.items())),a.key)))
    # Flip either wedge independently: the two opposite arrangements are
    # different bodies. A whole-strip half turn cannot change their handedness.
    # The two same-direction arrangements share a card and use the turn control.
    variants=[]
    for assembly in ordered:
        if blocks[positions[0]]['role']=='inner_edge' and inner_pattern(assembly.pieces) in ('same','opposite'):
            for mask in range(1,1<<len(assembly.pieces)):
                pieces=tuple(half_turn_inner(p) if mask>>i&1 else p for i,p in enumerate(assembly.pieces))
                variant=Assembly(assembly_key(pieces),kind,positions,pieces,assembly_group(pieces))
                if all(v.key!=variant.key for v in ordered+tuple(variants)):
                    variants.append(variant)
    ordered=ordered+tuple(variants)
    if blocks[positions[0]]['role']=='inner_edge':
        ranks={'whole':0,'same':1,'opposite_a':2,'opposite_b':3}
        ordered=tuple(sorted(ordered,key=lambda a:ranks.get(inner_arrangement(a.pieces),4)))
    with _LOCK:
        _CACHE[cache_key]=ordered;_CACHE.move_to_end(cache_key)
        while len(_CACHE)>32:_CACHE.popitem(last=False)
    return ordered


@lru_cache(maxsize=4)
def _plus_reference_pieces(kind):
    """Resolve ordinary Mixup pieces to the corresponding real Plus pieces.

    Parent grid coordinates identify the source block. The Plus model supplies
    its own cut surface at exactly the same rigid pose; no vertices are scaled.
    """
    ordinary=new_cube(kind.replace('mixup_plus_','mixup_'));plus=new_cube(kind)
    dimensions=MIXUP_MODELS[kind][0]
    def location(solid,depth):
        return (solid.role,tuple((-2 if v<0 else 2) if abs(v)>depth+EPS else
                (-1 if v<0 else 1) if dimensions[i]==4 else 0 for i,v in enumerate(solid.anchor)))
    d0=math.sqrt(2)-1;d1=(2*math.sqrt(2)-1)/7
    targets={location(s,d1):i for i,s in enumerate(plus.solids) if s.role in ('centre','edge')}
    result={}
    for home,solid in enumerate(ordinary.solids):
        if solid.role not in ('centre','edge'):continue
        other=targets[location(solid,d0)]
        for pose in range(len(ordinary.orientations)):
            panels=tuple(p for p,c in ordinary.placed_faces(home,pose) if c>=0)
            actual=tuple(p for p,c in plus.placed_faces(other,pose) if c>=0)
            signature=(solid.role,tuple(sorted(polygon_key(p) for p in panels)))
            result.setdefault(signature,AssemblyPiece(solid.role,actual,0))
    return result


def _shared_assemblies(kind,blocks,positions,cancelled,seconds,use_bundled):
    positions=tuple(sorted(positions));cache_key=('shared',kind,positions)
    with _LOCK:
        if cache_key in _CACHE:
            result=_CACHE[cache_key];_CACHE.move_to_end(cache_key);return result
    if use_bundled:
        result=_bundled(kind,positions)
        if result is not None:
            with _LOCK:
                _CACHE[cache_key]=result
                while len(_CACHE)>32:_CACHE.popitem(last=False)
            return result
    deadline=monotonic()+seconds
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline:raise ValueError('mixup.entry_assembly_timeout')
    # The ordinary series defines the choices, their orientation variants and
    # order. Plus changes the physical surface only, rather than inventing a
    # second menu by moving a union of prototypes between viewing sites.
    from cube.mixup_entry import MixupEntryDraft
    reference_kind=kind.replace('mixup_plus_','mixup_');reference=MixupEntryDraft(reference_kind)
    faces=tuple(sorted(blocks[i]['face'] for i in positions));role=blocks[positions[0]]['role']
    region=next(reference.linked_positions(i) for i,b in enumerate(reference.blocks)
        if b['role']==role and tuple(sorted(reference.blocks[j]['face'] for j in reference.linked_positions(i)))==faces)
    options=_local_assemblies(reference_kind,reference.blocks,region,cancelled,
                               max(.01,deadline-monotonic()),use_bundled)
    correspondence=_plus_reference_pieces(kind);result=[];seen=set()
    for option in options:
        guard();pieces=tuple(correspondence[(p.role,tuple(sorted(polygon_key(q) for q in p.panels)))] for p in option.pieces)
        key=assembly_key(pieces);group=assembly_group(pieces)
        if group in seen:continue
        seen.add(group);result.append(Assembly(key,kind,positions,pieces,group))
    result=tuple(result)
    with _LOCK:
        _CACHE[cache_key]=result
        while len(_CACHE)>32:_CACHE.popitem(last=False)
    return result


def assemblies(kind,blocks,positions,cancelled=None,seconds=6.,use_bundled=True):
    positions=tuple(sorted(positions))
    if (MIXUP_MODELS[kind][1] and positions and
            all(blocks[i]['role'] in ('edge','centre') for i in positions)):
        return _shared_assemblies(kind,blocks,positions,cancelled,seconds,use_bundled)
    return _local_assemblies(kind,blocks,positions,cancelled,seconds,use_bundled)
