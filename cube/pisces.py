"""Independent twelve-axis Four-Corner/Pisces material construction.

The outer body is a faceted approximation to the pillowed shell. Every
closed material cell, including the unpainted core, participates in gates.
Rendering facets of one coloured patch are not separate puzzle pieces.
"""
import math
from functools import lru_cache
from collections import defaultdict
from cube.polyhedral import CUBE,Spec,Geometry,Sticker,Move,add,scale,cross,dot,unit,mean,rotate,key
from cube.compound_solids import face_normal
from cube.twins_material import partition
from cube.planar_twins_state import PlanarTwinsState as TwinsState
from cube.crazy_comet import vertices
from cube.appearance import transform_frame
from cube.lanlan_comet import polygon_key

AXES=tuple(unit(p) for p in ((1,-1,3),(1,-3,1),(3,-1,1),(1,1,-3),
                            (1,3,-1),(3,1,-1),(-1,1,3),(-1,3,1),
                            (-3,1,1),(-1,-1,-3),(-1,-3,-1),(-3,-1,-1)))
ANGLE1=math.degrees(math.acos(7/18))
ANGLE2=math.degrees(math.acos(-5/6))
CUT=.518


@lru_cache(maxsize=1)
def shell():
    """Six pillowed faces, each with one diamond and eight side facets."""
    result=[]
    for face,n in enumerate(CUBE):
        u=next(p for p in CUBE if dot(n,p)==0);v=cross(n,u)
        radial=(u,v,scale(u,-1),scale(v,-1))
        inner=tuple(add(scale(n,.6),scale(p,.15)) for p in radial)
        corners=tuple(add(scale(n,.5),scale(add(a,b),.5)) for a,b in zip(radial,radial[1:]+radial[:1]))
        result.append((inner,face))
        for i in range(4):
            result.append(((inner[i],corners[i],inner[(i+1)%4]),face))
            result.append(((inner[i],corners[i-1],corners[i]),face))
    # Every facet must bound the same convex body, with outward normals.
    all_points=tuple(p for poly,color in result for p in poly)
    for poly,color in result:
        n=face_normal(poly);bound=dot(n,poly[0])
        if any(dot(n,p)>bound+1e-8 for p in all_points):raise ValueError('Nonconvex Pisces housing')
    return tuple(result)


@lru_cache(maxsize=1)
def structure():
    cells=(shell(),)
    for n in AXES:cells=partition(cells,n,CUT)
    return tuple(cells),fields_for(cells)


def fields_for(cells):
    panels=[]
    for h,solid in enumerate(cells):
        fields=defaultdict(dict)
        for poly,color in solid:
            if color>=0:
                for p in poly:fields[color][key(p)]=p
        # A field is a nonplanar surface patch; this vertex cloud is used for
        # rigid matching. The renderer draws its actual facets separately.
        panels.extend((h,color,tuple(points.values())) for color,points in sorted(fields.items()))
    return tuple(panels)


@lru_cache(maxsize=1)
def layout():
    solids,panels=structure();return tuple(range(len(solids))),solids,panels


class PiscesCube(TwinsState):
    puzzle_kind='lanlan_pisces'
    geometry_profile='faceted-pillow'
    layout=staticmethod(layout)
    turn_axes=AXES
    cut_bounds=(CUT,)*12
    # Physical amounts are degrees, not a fictitious finite fivefold turn.
    turn_steps=(1,)*12
    observation_model='lanlan-pisces-faceted-v1'
    face_normals=CUBE

    def panel_normal(self,face,poly):return self.face_normals[face]

    def validate_pose(self):
        from cube.appearance import IDENTITY_FRAME
        core=next(h for h in range(len(self.solids)) if sum(owner==h for owner,face,p in self.panels)==self.color_count)
        if any(abs(a-b)>1e-7 for col,reference in zip(self.frames[core],IDENTITY_FRAME) for a,b in zip(col,reference)):
            error=ValueError('tilted.fixed_core')
            error.locations=[dict(sticker=i) for i,(h,f,p) in enumerate(self.panels) if h==core]
            raise error

    def moves(self):
        return tuple(Move(a,0,angle) for a in range(12) for angle in (ANGLE1,-ANGLE1,ANGLE2,-ANGLE2))

    @property
    def geometry(self):
        cached=getattr(self,'_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        world=self.world_panels();pieces=[[] for _ in self.solids];stickers=[]
        for i,((h,c,p),placed) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[h],self.face_normals[c])
            face=max(range(len(self.face_normals)),key=lambda f:dot(self.face_normals[f],normal))
            stickers.append(Sticker(h,face,placed));pieces[h].append(i)
        layers=[]
        for axis in range(12):
            try:selected=self.selection(axis)
            except ValueError:selected=()
            layers.append((selected,))
        centres=tuple(transform_frame(f,mean(vertices(s))) for f,s in zip(self.frames,self.solids))
        g=Geometry(Spec(self.puzzle_kind,3,self.face_normals,self.turn_axes,(),360,axis_steps=self.turn_steps),
                   tuple(stickers),tuple(map(tuple,pieces)),centres,((),)*12,tuple(layers))
        self._geometry=self.frames,g;return g
