"""Oriented three/four-layer shape modifications with rigid piece surfaces."""
from functools import lru_cache
from itertools import product
from math import sqrt

from cube.mastermorphix import MastermorphixCube,IDENTITY,make_piece,positions_for_order,transform,_clip
from cube.polyhedral import CUBE,body,mean,cross,add,scale,dot,unit,key
from cube.coordinates import coord_values

PALETTE=('W','R','G','Y','O','B')
# A 180 degree rotation around (1,1,1) gives the same shell as a 60 degree
# rotation, up to the cube's 120 degree body symmetry.
AXIS_FRAME=((-1/3,2/3,2/3),(2/3,-1/3,2/3),(2/3,2/3,-1/3))


def _cut_shell(polygons,home,n,core_half=1.):
    values = coord_values(n)
    for axis,coordinate in enumerate(home):
        index = values.index(coordinate)
        if index < n-1:
            polygons = _clip(polygons,axis,1,core_half*(2*(index+1)/n-1))
        if index > 0:
            polygons = _clip(polygons,axis,-1,-core_half*(2*index/n-1))
    return tuple((tuple(points),color) for points,color in polygons)


@lru_cache(maxsize=256)
def axis_faces(home,n=3):
    normals=tuple(transform(AXIS_FRAME,n) for n in CUBE)
    polygons=[(list(face),color) for color,face in enumerate(body(normals))]
    return _cut_shell(polygons,home,n)


def faces_for(kind,home,n=3):
    if kind in ('windmill_unequal', 'fisher_unequal', 'windmill_offset', 'fisher_offset'):
        return unequal_height_faces(kind, home, n)
    if kind=='axis':
        return axis_faces(home,n)
    if kind=='football':
        return football_faces(home)
    if kind=='pandora':
        return pandora_faces(home)
    if kind=='windmill':
        return windmill_faces(home,n)
    if kind=='fisher':
        return fisher_faces(home,n)
    raise ValueError('Unsupported shape modification')


@lru_cache(maxsize=104)
def unequal_height_faces(kind, home, n=3):
    """Photo-based mirror variants: offset shell, fixed cubic mechanism.

    Both the diagonal-face centre and the extrusion lengths are asymmetric.
    Offset the exterior without enlarging Fisher's central cutting square.
    Its middle band and diagonal-face centre retain the ordinary Fisher cut
    spacing; the different outer-piece sizes come from the shell offset.
    Dimensions approximate the reference photographs, not manufacturer data.
    Shape the exterior BEFORE clipping; internal cut spacing remains equal
    along every mechanism axis, so quarter turns move closed rigid solids.
    """
    if n != 3:
        raise ValueError('Unequal-height mirror variants require order three')
    base = kind.split('_', 1)[0]
    if base == 'windmill':
        frame = ((sqrt(3)/2,0,-.5),(0,1,0),(.5,0,sqrt(3)/2))
        core_half = 3*(sqrt(3)-1)/2
        height = .96
        # The opposite shell edges have x = +/-(sqrt(3)-1)/2.
        # A z-only lateral offset keeps both x cuts passing through those
        # edges; only the other parallel cut family becomes eccentric.
        offset = (0., -.10, -.08)
    elif base == 'fisher':
        s = sqrt(.5)
        frame = ((s,0,-s),(0,1,0),(s,0,s))
        core_half = 1.
        height = 1.
        # Only one diagonal cut family is offset relative to the exterior.
        # Keep the x-normal parallel pair at its original face position;
        # the z-normal pair supplies the eccentricity. Y controls height only.
        offset = (0., .15, .16)
    else:
        raise ValueError('Unsupported unequal-height shell')
    if kind.endswith('_unequal'):
        # Independent variant: retain the original diagonal-face cuts, and
        # change only the outer lengths along the extrusion axis.
        core_half = 3*(sqrt(3)-1)/2 if base == 'windmill' else 1.
        height = 1.
        offset = (0., -.22, 0.)
    normals = tuple(transform(frame, normal) for normal in CUBE)
    polygons = [([(x+offset[0], y*height+offset[1], z+offset[2])
                 for x,y,z in face], color)
                for color,face in enumerate(body(normals))]
    return _cut_shell(polygons, home, n, core_half)


def physical_signature(cube):
    return tuple(sorted((color,tuple(sorted(tuple(round(v,6) for v in transform(piece.frame,p)) for p in points)))
                        for piece in cube.cubies.values() for points,color in faces_for(cube.puzzle_kind,piece.home,cube.n)
                        if color>=0))


class AxisCube(MastermorphixCube):
    puzzle_kind='axis'
    supported_orders=(3,4)
    distinct_piece_shapes=True

    def __init__(self,cubies,palette=PALETTE,n=3):
        if n not in self.supported_orders or len(palette)!=6 or len(set(palette))!=6:
            raise ValueError('Unsupported shape order or palette')
        self.cubies=cubies
        self.palette=tuple(palette)
        self.n=self.size=n
        self.positions=positions_for_order(n)

    @classmethod
    def solved(cls,palette=PALETTE,n=3):
        return cls({p:make_piece(p,p,IDENTITY,n) for p in positions_for_order(n)},palette,n)

    def is_solved(self):
        return set(self.cubies)==set(self.positions) and physical_signature(self)==physical_signature(type(self).solved(self.palette,self.n))

@lru_cache(maxsize=8)
def football_faces(home):
    from cube.football import shell_faces
    polygons=[(list(p),color) for p,color in shell_faces()]
    for axis,coordinate in enumerate(home):
        polygons=_clip(polygons,axis,-coordinate,0.)
    return tuple((tuple(p),color) for p,color in polygons)

class FootballCube(AxisCube):
    puzzle_kind='football'

    def __init__(self,cubies,palette=('W','B'),n=2):
        if n!=2:
            raise ValueError('Football corner mechanism requires order two')
        self.cubies=cubies
        self.palette=tuple(palette)
        self.n=self.size=2
        self.positions=positions_for_order(2)

    @classmethod
    def solved(cls,palette=('W','B'),n=2):
        return cls({p:make_piece(p,p,IDENTITY,2) for p in positions_for_order(2)},palette,n)


@lru_cache(maxsize=26)
def pandora_faces(home):
    """One large square centre and eight triangular patches on each face.

    The centre's side is half the housing's side. Its corners land on the
    four diagonals joining adjacent edge midpoints, so every coloured panel
    tiles the cubic shell without an exposed, unpainted corner-hat region.
    """
    output=[]
    for color,vertices in enumerate(body(CUBE)):
        normal=CUBE[color]
        centre=mean(vertices)
        inner=tuple(add(centre,scale(add(v,scale(centre,-1)),.5)) for v in vertices)
        patches=[]
        patches.append((tuple(int(v) for v in normal),inner,inner))
        for i,corner in enumerate(vertices):
            before=mean((vertices[i-1],corner))
            after=mean((corner,vertices[(i+1)%4]))
            owner=tuple(round(v) for v in corner)
            triangle=(corner,after,before)
            patches.append((owner,triangle,triangle))
            edge_home=tuple(round(v) for v in after)
            triangle=(after,inner[(i+1)%4],inner[i])
            patches.append((edge_home,triangle,triangle))
        for owner,skin,sticker in patches:
            if owner!=home:
                continue
            # Each visible triangle and centre has a closed back and walls;
            # it stays attached to its own mechanical piece during turns.
            back=tuple(scale(p,.86) for p in skin)
            output.append((skin,-1))
            output.append((tuple(reversed(back)),-1))
            for a,b,c,d in zip(skin,skin[1:]+skin[:1],back,back[1:]+back[:1]):
                output.append(((a,c,d,b),-1))
            pivot=mean(sticker)
            painted=tuple(add(add(pivot,scale(add(p,scale(pivot,-1)),.94)),scale(normal,.001)) for p in sticker)
            output.append((painted,color))
    return tuple(output)


class PandoraCube(AxisCube):
    puzzle_kind='pandora'
    supported_orders=(3,)


@lru_cache(maxsize=128)
def windmill_faces(home,n=3):
    """A cube shell offset 30 degrees around the vertical mechanism axis.

    The inner cuts pass through the shell's four vertical edges. This leaves
    two-colour corners, single-colour equatorial edges, and rectangular side
    centres rather than the tiny extra coloured slivers of an arbitrary cut.
    All three axes use the same cut distance so rigid quarter turns retain
    their mechanical boundaries while the exterior changes shape.
    """
    frame=((sqrt(3)/2,0,-.5),(0,1,0),(.5,0,sqrt(3)/2))
    normals=tuple(transform(frame,normal) for normal in CUBE)
    polygons=[(list(face),color) for color,face in enumerate(body(normals))]
    bound=(sqrt(3)-1)/2
    return _cut_shell(polygons,home,n,3*bound)


class WindmillCube(AxisCube):
    puzzle_kind='windmill'


@lru_cache(maxsize=128)
def fisher_faces(home,n=3):
    """Fisher shell: a cubic exterior rotated 45 degrees about vertical.

    Equatorial mechanical centres span two exterior colours at a shell edge;
    equatorial mechanical edges are single-colour rectangular blocks. Each
    piece is clipped as a closed solid, then transformed rigidly during turns.
    """
    s=sqrt(.5)
    frame=((s,0,-s),(0,1,0),(s,0,s))
    normals=tuple(transform(frame,normal) for normal in CUBE)
    polygons=[(list(face),color) for color,face in enumerate(body(normals))]
    return _cut_shell(polygons,home,n)


class FisherCube(AxisCube):
    puzzle_kind='fisher'


def normalize_fisher(cube):
    """Choose an invisible single-colour edge flip to satisfy virtual parity.

    A shape-card input cannot distinguish the two orientations of the four
    equatorial edges. Only accept a relabelling with identical coloured
    surfaces and a valid complete 3x3 state; genuine invalid inputs remain
    unchanged for the ordinary solver to report.
    """
    from cube.mastermorphix import placements,position_kind
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import verify_3x3
    work=cube.clone()
    if verify_3x3(cubies_to_facelets(work.cubies,3))[0]:
        return work

    def signature(piece):
        return tuple(sorted((color,tuple(sorted(key(transform(piece.frame,p)) for p in points)))
                            for points,color in fisher_faces(piece.home) if color>=0))

    for pos,piece in cube.cubies.items():
        if position_kind(pos)!='edge' or piece.home[1]!=0:
            continue
        original=signature(piece)
        for frame in placements(piece.home,pos):
            if frame==piece.frame:
                continue
            candidate=make_piece(piece.home,pos,frame,3)
            if signature(candidate)!=original:
                continue
            work.cubies[pos]=candidate
            if verify_3x3(cubies_to_facelets(work.cubies,3))[0]:
                return work
        work.cubies[pos]=piece.clone()
    return work


def normalize_football(cube):
    """Match visually identical black/white pieces before imposing twist sum.

    The ball pattern has rotational symmetries. Their virtual corner labels
    must be chosen as a matching problem, rather than rejecting a duplicate
    user-selected card whose physical shape is identical.
    """
    from cube.mastermorphix import placements
    from cube.cube3 import Cube3
    from cube.cubie_model import Cubie
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import _build_cubestring,_tface,_tcubie
    def signature(home,frame):
        return tuple(sorted((color,tuple(sorted(key(transform(frame,p)) for p in points)))
                            for points,color in faces_for('football',home) if color>=0))
    work=cube.clone()
    positions=tuple(cube.positions)
    choices={}
    for pos in positions:
        piece=cube.cubies[pos]
        wanted=signature(piece.home,piece.frame)
        choices[pos]=tuple(make_piece(home,pos,frame,2) for home in positions
                           for frame in placements(home,pos) if signature(home,frame)==wanted)
    order=sorted(positions,key=lambda p:len(choices[p]))
    def match(i,used):
        if i==len(order):
            virtual=Cube3.solved()
            for pos,piece in work.cubies.items():
                virtual.cubies[pos]=Cubie(piece.home,pos,dict(piece.stickers))
            face=_tface.FaceCube()
            if face.from_string(_build_cubestring(cubies_to_facelets(virtual.cubies,3)))!=_tcubie.CUBE_OK:
                return False
            return sum(face.to_cubie_cube().co)%3==0
        pos=order[i]
        for candidate in choices[pos]:
            if candidate.home not in used:
                work.cubies[pos]=candidate
                if match(i+1,used|{candidate.home}):
                    return True
        return False
    if not match(0,set()):
        raise ValueError('shape.error.duplicate')
    return work
