"""Eight rigid 1:2 mirror corners behind a decorative white 3x3 grid."""
from functools import lru_cache
from cube.mirror import MirrorCube
from cube.mastermorphix import (IDENTITY,ROTATIONS,positions_for_order,placements,
                               transform,make_piece,MorphixInputError)


@lru_cache(maxsize=8)
def piece_faces(home):
    bounds=tuple((-2/3,0.) if v<0 else (0.,4/3) for v in home);result=[]
    for axis in range(3):
        others=[a for a in range(3) if a!=axis]
        for side in (0,1):
            points=[]
            for a,b in ((0,0),(1,0),(1,1),(0,1)):
                p=[0.,0.,0.];p[axis]=bounds[axis][side]
                p[others[0]]=bounds[others[0]][a];p[others[1]]=bounds[others[1]][b]
                points.append(tuple(p))
            normal=tuple((1 if side else -1) if a==axis else 0 for a in range(3))
            result.append((tuple(points),normal,(home[axis]>0)==bool(side)))
    return tuple(result)


@lru_cache(maxsize=192)
def appearance(home,frame):
    return tuple(sorted((outside,tuple(sorted(tuple(round(v,6) for v in transform(frame,p)) for p in poly)))
                        for poly,normal,outside in piece_faces(home)))


def core3(cube):
    from cube.cube3 import Cube3
    full=Cube3.solved()
    for position,piece in cube.cubies.items():full.cubies[position]=piece.clone()
    return full


def _twist_valid(cube):
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import _build_cubestring,_tface,_tcubie
    fc=_tface.FaceCube()
    if fc.from_string(_build_cubestring(cubies_to_facelets(core3(cube).cubies,3)))!=_tcubie.CUBE_OK:return False
    cc=fc.to_cubie_cube()
    return sorted(cc.cp)==list(range(8)) and sum(cc.co)%3==0


def normalize_entry(cube):
    """Resolve repeated shapes and invisible twists without inventing colours."""
    if set(cube.cubies)!=set(cube.positions):raise MorphixInputError('incomplete')
    options={}
    for pos,piece in cube.cubies.items():
        if piece.home not in cube.positions:raise MorphixInputError('invalid')
        target=appearance(piece.home,piece.frame)
        options[pos]=[(h,f) for h in cube.positions for f in placements(h,pos) if appearance(h,f)==target]
        if not options[pos]:raise MorphixInputError('invalid')
    order=sorted(cube.positions,key=lambda p:len(options[p]));chosen={};used=set();work=cube.clone()
    def visit(index):
        if index==len(order):
            work.cubies={p:make_piece(h,p,f,2) for p,(h,f) in chosen.items()}
            return _twist_valid(work)
        pos=order[index]
        for h,f in options[pos]:
            if h in used:continue
            chosen[pos]=(h,f);used.add(h)
            if visit(index+1):return True
            used.remove(h)
        return False
    if not visit(0):raise MorphixInputError('invalid')
    return work


class BlankerCube(MirrorCube):
    puzzle_kind='blanker'

    def __init__(self,cubies,palette=('MIRROR',),n=2):
        if n!=2:raise ValueError('Blanker uses a two-layer mechanism')
        super().__init__(cubies,palette,n)

    @classmethod
    def solved(cls,palette=('MIRROR',),n=2):return super().solved(palette,n)

    def piece_faces(self,home):return piece_faces(home)
