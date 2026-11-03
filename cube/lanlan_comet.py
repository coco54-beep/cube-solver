"""Independent scooped-shell construction for the requested LanLan Comet.

The earlier planar_rhombic_12 remains a separate puzzle. Dimensions below
describe the public geometric prototype, not measured manufacturing tolerances.
"""
import math
from functools import lru_cache
from cube.polyhedral import CUBE, EDGE_AXES, add, body, dot, key, scale, rotate, unit
from cube.compound_solids import tetrahedral_shell, split, vertices, boundary, centroid

CUT=.8/math.sqrt(2)


@lru_cache(maxsize=1)
def shell():
    """Twelve concave octagons and 24 gold facets around recessed poles.

    The gold facets belong to 24 three-colour outer pieces around the poles;
    the small innermost square and four triangular gaps remain bare plastic.
    """
    faces=[]
    for face,poly in enumerate(body(EDGE_AXES)):
        corners=tuple(scale(p,1/math.sqrt(2)) for p in poly)
        poles=[p for p in corners if sum(abs(v)>1e-7 for v in p)==1]
        outline=[]
        for i,p in enumerate(corners):
            if p not in poles:outline.append(p);continue
            opposite=next(q for q in poles if q!=p)
            outline.extend((add(scale(p,2/3),scale(corners[i-1],1/3)),
                            add(scale(p,.8),scale(opposite,.2)),
                            add(scale(p,2/3),scale(corners[(i+1)%4],1/3))))
        faces.append((tuple(outline),face))
    for pole in CUBE:
        # Tangent square ordered so its normal points out along this pole.
        tangent=next(n for n in CUBE if dot(n,pole)==0)
        from cube.polyhedral import cross
        other=cross(pole,tangent)
        directions=(tangent,other,scale(tangent,-1),scale(other,-1))
        rim=tuple(add(scale(pole,.8),scale(u,.2)) for u in directions)
        shoulders=tuple(add(scale(pole,5/6),scale(add(u,v),1/6))
                        for u,v in zip(directions,directions[1:]+directions[:1]))
        inner=tuple(add(scale(pole,23/30),scale(add(u,v),1/30))
                    for u,v in zip(directions,directions[1:]+directions[:1]))
        faces.append((inner,-1))
        for i in range(4):
            faces.append(((inner[i],rim[i],shoulders[i],rim[(i+1)%4]),12))
            faces.append(((inner[i-1],rim[i],inner[i]),-1))
    return tuple(faces)


@lru_cache(maxsize=1)
def initial_cells():
    cells=[(0,tetrahedral_shell(shell()))]
    for axis,normal in enumerate(EDGE_AXES):
        following=[]
        for mask,parts in cells:
            negative,positive=split(parts,normal,CUT)
            if negative:following.append((mask,negative))
            if positive:following.append((mask|(1<<axis),positive))
        cells=following
    return tuple(sorted(cells,key=lambda cell:(cell[0]==0,cell[0])))


@lru_cache(maxsize=1)
def initial_boundary():
    return tuple((mask,boundary(parts)) for mask,parts in initial_cells())


def _rotated(parts,axis,angle):
    return tuple(tuple((tuple(rotate(p,axis,angle) for p in poly),color)
                       for poly,color in solid) for solid in parts)


@lru_cache(maxsize=1)
def material_cells():
    """Unbandage contacts exposed at the two closed-jumbling orientations.

    Keep all convex fragments of each cell together. Refinement affects only
    the contacts exposed on another outer cap, rather than slicing the entire
    resting shell with an arbitrary collection of extra global planes.
    """
    axes=tuple(unit(p) for p in ((1,1,0),(1,-1,0),(1,0,1),
                                (1,0,-1),(0,1,1),(0,1,-1)))
    angle=math.acos(1/3)
    contacts=((1,1,(3,5)),(1,-1,(2,4)),(0,1,(2,5)),(0,-1,(3,4)),
              (2,1,(1,)),(2,-1,(0,)),(3,1,(0,)),(3,-1,(1,)))
    cells=tuple(parts for mask,parts in initial_cells())
    for carrier,sign,targets in contacts:
        result=[]
        for parts in cells:
            extent=tuple(dot(axes[carrier],p) for p in vertices(parts))
            moved=min(extent)>=CUT-1e-7 or max(extent)<=-CUT+1e-7
            if not moved:result.append(parts);continue
            placed=_rotated(parts,axes[carrier],sign*angle)
            branches=[placed]
            for target in targets:
                following=[]
                for branch in branches:
                    if abs(dot(centroid(branch),axes[target]))<=CUT+1e-7:
                        following.append(branch);continue
                    subcells=[branch]
                    for normal in EDGE_AXES:
                        subcells=[half for cell in subcells for half in split(cell,normal,CUT) if half]
                    following.extend(subcells)
                branches=following
            result.extend(_rotated(branch,axes[carrier],-sign*angle) for branch in branches)
        cells=tuple(result)
    return cells


@lru_cache(maxsize=1)
def structure():
    solids=tuple(boundary(parts) for parts in material_cells())
    panels=tuple((home,color,poly) for home,faces in enumerate(solids) for poly,color in faces if color>=0)
    return solids,panels


def polygon_key(poly):
    return tuple(sorted(tuple(round(v,5) for v in p) for p in poly))


@lru_cache(maxsize=1)
def layout():
    solids,panels=structure()
    masks=tuple(sum(1<<i for i,n in enumerate(EDGE_AXES) if dot(n,centroid(parts))>CUT)
                for parts in material_cells())
    return masks,solids,panels


from cube.crazy_comet import CometCube, vertices as solid_vertices
from cube.appearance import transform_frame, IDENTITY_FRAME


class LanlanCometCube(CometCube):
    puzzle_kind='lanlan_comet_physical'
    geometry_profile='scooped-unbandaged-comet'
    cut=CUT
    color_count=13
    layout=staticmethod(layout)

    @staticmethod
    def panel_normal(face,poly):
        from cube.compound_solids import face_normal
        return face_normal(poly)

    def observation_data(self):
        return dict(model='lanlan-comet-scooped',version=1,frames=self.frames,paints=self.paints)

    @classmethod
    def from_observation(cls,data):
        if (type(data) is not dict or data.get('model')!='lanlan-comet-scooped'
                or type(data.get('version')) is not int or data.get('version')!=1
                or type(data.get('frames')) not in (list,tuple)
                or type(data.get('paints')) not in (list,tuple)):
            raise ValueError('rigid.invalid')
        return cls(data['frames'],data['paints'])

    def aligned_permutation(self):
        # An unbandaged wing can exchange positions through a non-cubic pose.
        # Do not restrict these pieces to the cube's 24 global symmetries.
        slots={polygon_key(poly):i for i,(home,face,poly) in enumerate(self.panels)}
        result=[];owners={}
        for home,face,poly in self.panels:
            target=slots.get(polygon_key(tuple(transform_frame(self.frames[home],p) for p in poly)))
            if target is None:raise ValueError('copter.align_first')
            destination=self.panels[target][0]
            if home in owners and owners[home]!=destination:raise ValueError('copter.invalid_shape')
            owners[home]=destination;result.append(target)
        if sorted(result)!=list(range(len(self.panels))):raise ValueError('copter.invalid_shape')
        if len(set(owners.values()))!=len(owners):raise ValueError('copter.invalid_shape')
        for home,destination in owners.items():
            a=polygon_key(tuple(transform_frame(self.frames[home],p)
                                for p in solid_vertices(self.solids[home])))
            b=polygon_key(solid_vertices(self.solids[destination]))
            if a!=b:raise ValueError('copter.invalid_shape')
        return tuple(result)

    def aligned_frames(self,home):return tuple(frame for destination,frame,mapping in placements(home))

    def frame_aligned(self,home,frame):return _pose_key(frame) in aligned_frame_keys(home)


def _pose_key(frame):return tuple(round(v,6) for column in frame for v in column)


@lru_cache(maxsize=69)
def aligned_frame_keys(home):return frozenset(_pose_key(frame) for destination,frame,mapping in placements(home))


@lru_cache(maxsize=69)
def placements(home):
    """All proper, whole-solid congruences into resting shell slots."""
    from cube.polyhedral import cross, mean
    from cube.curvy_copter import multiply, inverse_point, frame_key
    from cube.compound_solids import face_normal
    solids,panels=structure();parts=material_cells()
    source_slots=[i for i,(h,f,p) in enumerate(panels) if h==home]
    if not source_slots:return ((home,IDENTITY_FRAME,()),)
    centre=centroid(parts[home]);points=solid_vertices(solids[home]);radius=dot(centre,centre)
    u=unit(centre)
    # A radial ray and an off-axis boundary point define a right-handed frame.
    p=next(p for p in panels[source_slots[0]][2] if dot(cross(p,u),cross(p,u))>1e-12)
    v=unit(add(p,scale(u,-dot(p,u))));source=(u,v,cross(u,v))
    target_slots={polygon_key(poly):i for i,(h,f,poly) in enumerate(panels)}
    result=[];seen=set()
    for destination,faces in enumerate(solids):
        slots=[i for i,(h,f,p) in enumerate(panels) if h==destination]
        if len(slots)!=len(source_slots):continue
        target_centre=centroid(parts[destination])
        if abs(dot(target_centre,target_centre)-radius)>1e-8:continue
        target_u=unit(target_centre)
        for q in solid_vertices(faces):
            qv=add(q,scale(target_u,-dot(q,target_u)))
            if dot(qv,qv)<1e-12:continue
            target_v=unit(qv);target=(target_u,target_v,cross(target_u,target_v))
            rotation=tuple(transform_frame(target,inverse_point(source,column)) for column in IDENTITY_FRAME)
            signature=(destination,frame_key(rotation))
            if signature in seen:continue
            if polygon_key(tuple(transform_frame(rotation,p) for p in points))!=polygon_key(solid_vertices(faces)):continue
            mapping=tuple(target_slots.get(polygon_key(tuple(transform_frame(rotation,p) for p in panels[i][2])))
                          for i in source_slots)
            if None in mapping or set(mapping)!=set(slots):continue
            seen.add(signature);result.append((destination,rotation,tuple(zip(source_slots,mapping))))
    if not result:raise ValueError('Comet piece has no resting placement')
    return tuple(result)
