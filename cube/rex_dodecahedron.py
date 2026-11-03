"""MF8 Bauhinia's spherical cuts and complete regular 120-degree actions.

The catalogue explicitly exposes the regular 120-degree mode. Partial-turn,
hidden filler and jumbling acceptance are not represented by these fixed slots.
"""
from functools import lru_cache
import math
from cube.polyhedral import (DODECA,Spec,Geometry,Sticker,body,unit,key,mean,
                            rotate,_patch_faces)
from cube.curved_partition import SphereCut,shell


@lru_cache(maxsize=1)
def cuts():
    vertices=tuple({key(p):p for poly in body(DODECA) for p in poly}.values())
    edge=min(sum((a-b)**2 for a,b in zip(p,q)) for p in vertices for q in vertices if p!=q)**.5
    return tuple(SphereCut(p,edge) for p in vertices)


@lru_cache(maxsize=1)
def geometry():
    cs=cuts();spec=Spec('mf8_bauhinia_minx',3,DODECA,tuple(unit(c.centre) for c in cs),(),3)
    fragments=shell(spec,cs);groups={}
    for membership,face,polygon in fragments:groups.setdefault(membership,[]).append((face,polygon))
    signatures=tuple(groups);owners={s:i for i,s in enumerate(signatures)}
    stickers=[];pieces=[];centres=[]
    for piece,signature in enumerate(signatures):
        slots=[]
        for face,polygon in sorted(groups[signature]):
            slots.append(len(stickers));stickers.append(Sticker(piece,face,polygon))
        pieces.append(tuple(slots))
        # A sampled-outline average drifts when equal arcs happen to round to
        # different segment counts. Cut-centre barycentres are unique here and
        # transform exactly under every body symmetry, so matching entered
        # two-colour pieces does not depend on display tessellation.
        centres.append(mean(tuple(c.centre for i,c in enumerate(cs) if signature&(1<<i))))
    slots={(s.piece,s.face):i for i,s in enumerate(stickers)}
    cut_index={key(c.centre):i for i,c in enumerate(cs)};face_index={key(n):i for i,n in enumerate(DODECA)}
    permutations=[];layers=[]
    for axis,normal in enumerate(spec.axes):
        destinations=tuple(cut_index[key(rotate(c.centre,normal,math.tau/3))] for c in cs)
        face_map=tuple(face_index[key(rotate(n,normal,math.tau/3))] for n in DODECA)
        moving=tuple(p for p,s in enumerate(signatures) if s&(1<<axis))
        selected=set(moving)
        def target(signature):return sum(1<<destinations[i] for i in range(len(cs)) if signature&(1<<i))
        row=tuple(slots[owners[target(signatures[s.piece])],face_map[s.face]]
                  if s.piece in selected else i for i,s in enumerate(stickers))
        if sorted(row)!=list(range(len(stickers))):raise ValueError('Rex dodecahedron turn is not bijective')
        if any(row[row[row[i]]]!=i for i in range(len(stickers))):raise ValueError('Rex turn must have order three')
        permutations.append((row,));layers.append((moving,))
    return _patch_faces(Geometry(spec,tuple(stickers),tuple(pieces),tuple(centres),tuple(permutations),tuple(layers)))
