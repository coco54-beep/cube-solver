"""Two fixed-core 3×3 cubes sharing a 1×1×3 or 2×1×3 block.

The supplied A/B pictures distinguish these two overlaps. A turn of either
core is exposed only when it leaves every shared cubie fixed.
"""
from functools import lru_cache
from itertools import product
from cube.polyhedral import CUBE, Spec, Sticker, body, mean, add, scale
from cube.expanded_polyhedra import assemble


def core_centres(kind):
    if kind == 'siamese_a':return ((0,0,0),(2,-2,0))
    if kind == 'siamese_b':return ((0,0,0),(1,-2,0))
    raise ValueError('Unsupported Siamese Cube')


@lru_cache(maxsize=2)
def configuration(kind):
    origins=core_centres(kind)
    cells=tuple({tuple(o[a]+v[a] for a in range(3)) for v in product((-1,0,1),repeat=3)}
                for o in origins)
    shared=cells[0]&cells[1]
    axes=[];pivots=[];bands=[]
    for core,origin in enumerate(origins):
        for axis in range(3):
            direction=tuple(int(a==axis) for a in range(3))
            free=[]
            for value in (-1,0,1):
                band={p for p in cells[core] if p[axis]==origin[axis]+value}
                if not band&shared:free.append(band)
            if free:
                axes.append(direction);pivots.append(origin);bands.append(tuple(free))
    return cells,tuple(shared),tuple(axes),tuple(pivots),tuple(bands)


@lru_cache(maxsize=2)
def siamese_geometry(kind):
    cells,shared,axes,pivots,bands=configuration(kind)
    occupied=cells[0]|cells[1]
    panels=[];pieces=[];centres=[];positions={}
    faces=body(CUBE)
    for pos in sorted(occupied):
        exposed=[face for face,normal in enumerate(CUBE)
                 if tuple(pos[a]+normal[a] for a in range(3)) not in occupied]
        if not exposed:continue
        p=len(pieces);positions[pos]=p;slots=[]
        for face in exposed:
            poly=tuple(add(pos,scale(v,.5)) for v in faces[face])
            slots.append(len(panels));panels.append(Sticker(p,face,poly))
        pieces.append(tuple(slots));centres.append(pos)
    selected=tuple(tuple({positions[p] for p in band if p in positions} for band in layers)
                   for layers in bands)
    spec=Spec(kind,3,CUBE,axes,(),4)
    return assemble(spec,panels,pieces,centres,selected,pivots)


def move_origin(kind,move):return configuration(kind)[3][move.axis]
