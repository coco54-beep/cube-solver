"""Physical surface plates for the fixed bandaged-cube entry workflow."""
from dataclasses import dataclass
from cube.coordinates import FACE_NORMALS,pos_from_rc,rc_from_pos

MAIN_STEPS=('1×1','2×1','2×2')


def rotated_cells(row,column,shape,quarter_turns=0):
    """Rotate cell centres around the clicked cell, including 180/270°."""
    if shape=='other':return ()
    width,height=map(int,shape.split('×'))
    result=[]
    for dr in range(height):
        for dc in range(width):
            rr,cc=dr,dc
            for _ in range(quarter_turns%4):rr,cc=cc,-rr
            result.append((row+rr,column+cc))
    return tuple(sorted(result))


@dataclass(frozen=True)
class Plate:
    face: str
    cells: tuple
    shape: str


def plate_shape(cells):
    rows={r for r,c in cells};cols={c for r,c in cells}
    if len(cells)!=len(rows)*len(cols):return 'other'
    if max(rows)-min(rows)+1!=len(rows) or max(cols)-min(cols)+1!=len(cols):return 'other'
    a,b=sorted((len(rows),len(cols)),reverse=True)
    return f'{a}×{b}'


def plates(cube):
    # Geometry alone determines plates. Colour equality must never glue
    # neighbouring pieces or separate a fixed bonded group.
    from cube.bandaged_cube import BandagedCube
    if not isinstance(cube,BandagedCube):return ()
    cached=getattr(cube,'_entry_plates',None)
    signature=tuple(sorted((c.home,c.pos) for c in cube.cubies.values()))
    if cached is not None and cached[0]==signature:return cached[1]
    result=[]
    for face,normal in FACE_NORMALS.items():
        seen=set()
        for r in range(cube.n):
            for c in range(cube.n):
                if (r,c) in seen:continue
                pos=pos_from_rc(cube.n,face,r,c)
                cells=tuple(sorted(rc_from_pos(cube.n,face,p) for p in cube.surface_group(pos,normal)))
                seen.update(cells);result.append(Plate(face,cells,plate_shape(cells)))
    result=tuple(result);cube._entry_plates=(signature,result)
    return result


def steps(cube):
    extra=sorted({p.shape for p in plates(cube)}-set(MAIN_STEPS))
    return MAIN_STEPS+tuple(extra)


def completed(plate,data):
    colors={data[plate.face][r][c] for r,c in plate.cells}
    return len(colors)==1 and bool(next(iter(colors)))


def entered_plates(connections):
    return tuple(Plate(face,tuple(sorted(cells)),plate_shape(cells))
                 for face,cells in sorted(connections))


def reconstruct(kind,data,connections,seconds=2.):
    """Recover rigid preset groups at their *entered*, rather than home, slots.

    Colours identify visible stickers; the user's seams distinguish bonded
    plates from adjacent equally coloured pieces. No scramble history is used.
    This checks the rigid inventory, not reachability through constrained turns.
    """
    from collections import Counter
    from time import monotonic
    from cube.bandaged_cube import BandagedCube
    from cube.appearance import ROTATIONS,transform_frame
    from cube.cubie_model import Cubie
    base=BandagedCube.solved(kind);n=base.n
    chosen=entered_plates(connections)
    cells=[(p.face,r,c) for p in chosen for r,c in p.cells]
    if Counter(cells)!=Counter((f,r,c) for f in FACE_NORMALS for r in range(n) for c in range(n)):
        raise ValueError('bandage.entry_incomplete')
    if any(not completed(p,data) for p in chosen):
        raise ValueError('bandage.entry_incomplete')
    if Counter(p.shape for p in chosen)!=Counter(p.shape for p in plates(base)):
        raise ValueError('bandage.entry_inventory')
    expected={(p.face,p.cells) for p in chosen}
    groups=list(base.groups)
    bonded=set().union(*groups) if groups else set()
    groups.extend(frozenset((h,)) for h in base.cubies if h not in bonded)
    candidates=[]
    for group in groups:
        options=[];seen=set()
        for frame in ROTATIONS:
            pieces={};surfaces={};valid=True
            for home in group:
                pos=transform_frame(frame,home)
                stickers={transform_frame(frame,normal):color
                          for normal,color in base.cubies[home].stickers.items()}
                for face,normal in FACE_NORMALS.items():
                    if normal not in stickers:continue
                    r,c=rc_from_pos(n,face,pos)
                    if data[face][r][c]!=stickers[normal]:valid=False;break
                    surfaces.setdefault(face,[]).append((r,c))
                if not valid:break
                pieces[pos]=Cubie(home,pos,stickers,frame)
            if not valid or any((f,tuple(sorted(v))) not in expected for f,v in surfaces.items()):continue
            # Unobservable rotations of an isolated square centre are identical.
            signature=tuple(sorted((p,c.home,tuple(sorted(c.stickers.items()))) for p,c in pieces.items()))
            if signature in seen:continue
            seen.add(signature);options.append(pieces)
        if not options:raise ValueError('bandage.entry_layout')
        candidates.append(options)
    deadline=monotonic()+seconds
    def match(remaining,work):
        if monotonic()>deadline:raise ValueError('bandage.entry_budget')
        if not remaining:return work
        available=[(i,[p for p in candidates[i] if not work.keys() & p.keys()]) for i in remaining]
        index,options=min(available,key=lambda pair:len(pair[1]))
        for option in options:
            result=match(remaining-{index},work|option)
            if result is not None:return result
        return None
    result=match(set(range(len(groups))),{})
    if result is None:raise ValueError('bandage.entry_layout')
    return BandagedCube(result,kind)
