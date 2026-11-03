"""Calvin / Aleh / Evgeniy's cubic-core extension family.

An extension is a complete 3x3 plane. Its centre is attached to the core
centre; its other eight blocks can rotate independently when that plane is
complete. A core turn carries the extensions anchored to its core cubies.
"""
from functools import lru_cache
from itertools import product
from cube.polyhedral import CUBE,Spec,Geometry,Sticker

EXTENSIONS={
    'i_cube':(0,),
    'l_cube':(0,1),
    't_cube':(0,3,1),
    'x_cube':(0,3,1,4),
    'tri_cube':(0,1,2),
    'temple_cube':(0,1,2,4,5),
    'cross_cube':tuple(range(6)),
}


def dimensions(kind):
    normals=[CUBE[f] for f in EXTENSIONS[kind]]
    return tuple(3+sum(abs(n[a]) for n in normals) for a in range(3))


@lru_cache(maxsize=7)
def letter_layout(kind):
    core=tuple(product((-2,0,2),repeat=3));cells=[[p] for p in core];free=[]
    for face in EXTENSIONS[kind]:
        normal=CUBE[face];axis,sign=next((a,v) for a,v in enumerate(normal) if v)
        for piece,p in enumerate(core):
            if p[axis]!=sign*2:continue
            outer=tuple(p[a]+2*normal[a] for a in range(3))
            if sum(v!=0 for v in p)==1:cells[piece].append(outer)
            else:free.append([outer])
    cells.extend(free);cells=tuple(tuple(g) for g in cells)
    occupied={p for g in cells for p in g}
    boxes=tuple(tuple((min(p[a] for p in g)/2-.5,max(p[a] for p in g)/2+.5)
                      for a in range(3)) for g in cells)
    panels=[];entries=[];lookup={}
    for piece,group in enumerate(cells):
        for face,normal in enumerate(CUBE):
            exposed=[p for p in group if tuple(p[a]+2*normal[a] for a in range(3)) not in occupied]
            if not exposed:continue
            home=max(exposed,key=lambda p:sum(p[a]*normal[a] for a in range(3)))
            lookup[piece,face]=len(entries);entries.append((home,normal));panels.append(Sticker(piece,face,()))
    dims=dimensions(kind)
    bounds=tuple(2.5 if f in EXTENSIONS[kind] else 1.5 for f in range(6))
    spec=Spec(kind,max(dims),CUBE,CUBE,(),4,axis_steps=(1,)*6,bounds=bounds)
    identity=tuple(range(len(panels)))
    base=Geometry(spec,tuple(panels),tuple(() for _ in cells),(),((identity,)*4,)*6,())
    return cells,boxes,tuple(entries),lookup,base


def register_models(models):
    for kind in EXTENSIONS:models[kind]=(dimensions(kind),5)


def extension_demands(kind,p):
    return tuple(tuple(p[a]+2*CUBE[face][a] for a in range(3))
                 for face in EXTENSIONS[kind]
                 if sum(p[a]*CUBE[face][a] for a in range(3))==2)
