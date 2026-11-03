"""Cube mechanisms carrying octahedral and dodecahedral rigid shells."""
from functools import lru_cache
import math
from cube.polyhedral import CUBE,OCTA,DODECA,EDGE_AXES,body,scale,dot
from cube.shape_cube import AxisCube,_cut_shell

KINDS=frozenset(('trajber','trajber_4','dodecahedron_2','dodecahedron_3',
                 'rhombic_3','rhombic_4','rhombic_mask_4','caneball_4'))
COLOURS=((.98,.98,.98,1),(.02,.65,.18,1),(.9,.05,.06,1),(.51,.12,.73,1),
         (.97,.31,.61,1),(1,.47,.02,1),(.05,.2,.91,1),(.62,.86,.12,1),
         (1,.85,.02,1),(.02,.73,.83,1),(.58,.6,.64,1),(.2,.08,.47,1))


def default_colors(kind):
    if kind=='rhombic_mask_4':
        # Six vertex caps share the metallic colour. The twelve remaining
        # truncated rhombic faces keep their original colours.
        return COLOURS+((.68,.52,.22,1),)
    return COLOURS[:8 if kind.startswith('trajber') or kind=='caneball_4' else 12]


@lru_cache(maxsize=256)
def faces_for(kind,home,n):
    if kind=='caneball_4':
        if n!=4:raise ValueError('Caneball requires a four-layer mechanism')
        # The faceted ball has eight triangular caps, twelve edge squares and
        # six axial squares. Colour is attached to the OCTANT, not the facet.
        # Every corner, wing and centre therefore has one visible colour.
        d=(2*math.sqrt(2)-1)/math.sqrt(3)
        normals=CUBE+EDGE_AXES+tuple(scale(axis,1/d) for axis in OCTA)
        color=max(range(8),key=lambda i:dot(OCTA[i],tuple(1 if v>0 else -1 for v in home)))
        return _cut_shell([(list(face),color) for face in body(normals)],home,n,2*(math.sqrt(2)-1))
    if kind in ('rhombic_3','rhombic_4','rhombic_mask_4'):
        if n != (3 if kind=='rhombic_3' else 4):
            raise ValueError('Wrong rhombic shell order')
        # The four-valent vertices sit on the six cubic mechanism axes.
        # A rhombic face's large middle patch is an EDGE of that mechanism.
        # Place the cuts through the rhombus edges, retaining the photographed
        # large middle patches and small triangular ends.
        a=math.sqrt(2)-1
        core_half=3*a if n==3 else 2*a
        normals=EDGE_AXES
        if kind=='rhombic_mask_4':
            # Truncate the six four-valent tips. These gold squares are the
            # four mechanical centres, while the twelve remaining faces keep
            # their original rhombic colours. The square rims must land on
            # the outer mechanical cuts: sqrt(2) - (sqrt(2)-1) = 1.
            # Extending the cap to 1.05 introduces extra coloured wing facets
            # (eight fields per side instead of the photographed four).
            normals=EDGE_AXES+CUBE
        polygons=[(list(face),i if i<12 else 12) for i,face in enumerate(body(normals))]
        return _cut_shell(polygons,home,n,core_half)
    normals=OCTA if kind.startswith('trajber') else DODECA
    if kind.startswith('trajber') and n!=4:
        raise ValueError('This Trajber model requires a four-layer mechanism')
    # Four mechanical layers, with cuts at -sqrt(3)/4, 0, +sqrt(3)/4.
    # The central cut is a real movable boundary, not a drawn extra seam.
    core_half=math.sqrt(3)/2 if kind.startswith('trajber') else 1.
    return _cut_shell([(list(face),i) for i,face in enumerate(body(normals))],home,n,core_half)


class SolidShapeCube(AxisCube):
    def __init__(self,cubies,palette=None,n=3):
        count=len(default_colors(self.puzzle_kind))
        if n not in self.supported_orders:raise ValueError('Unsupported solid shell order')
        if palette is None:palette=tuple('S_'+self.puzzle_kind+'_'+str(i) for i in range(count))
        if len(palette)!=count or len(set(palette))!=count:raise ValueError('Wrong solid shell palette')
        from app.constants import COLOR_INFO
        for i,rgba in enumerate(default_colors(self.puzzle_kind)):
            COLOR_INFO.setdefault(palette[i],(str(i+1),rgba))
        self.cubies=cubies;self.palette=tuple(palette);self.n=self.size=n
        from cube.mastermorphix import positions_for_order
        self.positions=positions_for_order(n)

    @classmethod
    def solved(cls,palette=None,n=3):
        from cube.mastermorphix import make_piece,IDENTITY,positions_for_order
        return cls({p:make_piece(p,p,IDENTITY,n) for p in positions_for_order(n)},palette,n)


class TrajberCube(SolidShapeCube):
    puzzle_kind='trajber'
    supported_orders=(4,)

    def __init__(self,cubies,palette=None,n=4):
        super().__init__(cubies,palette,n)

    @classmethod
    def solved(cls,palette=None,n=4):
        return super().solved(palette,n)

# Accept existing four-layer development checkpoints under the old class name.
# There is a single physical implementation and no three-layer fallback.
MasterTrajberCube=TrajberCube

class Dodecahedron2Cube(SolidShapeCube):
    puzzle_kind='dodecahedron_2'
    supported_orders=(2,)

class Dodecahedron3Cube(SolidShapeCube):
    puzzle_kind='dodecahedron_3'
    supported_orders=(3,)

class Rhombic3Cube(SolidShapeCube):
    puzzle_kind='rhombic_3'
    supported_orders=(3,)

class Rhombic4Cube(SolidShapeCube):
    puzzle_kind='rhombic_4'
    supported_orders=(4,)

class RhombicMask4Cube(SolidShapeCube):
    puzzle_kind='rhombic_mask_4'
    supported_orders=(4,)

class Caneball4Cube(SolidShapeCube):
    puzzle_kind='caneball_4'
    supported_orders=(4,)

FACTORIES={cls.puzzle_kind:cls for cls in (TrajberCube,Dodecahedron2Cube,Dodecahedron3Cube,
                                        Rhombic3Cube,Rhombic4Cube,RhombicMask4Cube,Caneball4Cube)}
FACTORIES['trajber_4']=TrajberCube
