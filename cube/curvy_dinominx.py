"""AJ's two-depth corner-turning dodecahedron.

Twenty vertex axes each have a deep and a shallow spherical cap. Both turn
120 degrees; the twelve centre panels belong to the stationary inner body.
Adjacent shallow circles meet at the midpoint of each body edge. The deep
radius sets the photographed panel proportions, not ordinary 4x4 layers.
"""
from functools import lru_cache
import math
from cube.polyhedral import (DODECA,Spec,Geometry,Sticker,body,unit,key,mean,
                            rotate,scale,_patch_faces)
from cube.curved_partition import SphereCut,shell


@lru_cache(maxsize=1)
def cuts():
    vertices=tuple({key(p):p for polygon in body(DODECA) for p in polygon}.values())
    edge=min(sum((a-b)**2 for a,b in zip(p,q)) for p in vertices for q in vertices if p!=q)**.5
    # Adjacent vertices lie in their shared face plane, so their shallow
    # section circles have radius edge/2 and are externally tangent there.
    return tuple(SphereCut(v,edge*r) for v in vertices for r in (.75,.5))


@lru_cache(maxsize=1)
def geometry():
    cs=cuts();axes=tuple(unit(c.centre) for c in cs[::2])
    # The renderer/UI uses two layer records. Selection is by sphere
    # membership below, never by a flat dot-product cut at these labels.
    spec=Spec('aj_curvy_dinominx_4',4,DODECA,axes,(0.,1.),3)
    groups={}
    for signature,face,polygon in shell(spec,cs):
        groups.setdefault(signature,[]).append((face,polygon))
    signatures=tuple(groups);owners={s:i for i,s in enumerate(signatures)}
    stickers=[];pieces=[];centres=[]
    for piece,signature in enumerate(signatures):
        slots=[]
        for face,polygon in sorted(groups[signature]):
            slots.append(len(stickers));stickers.append(Sticker(piece,face,polygon))
        pieces.append(tuple(slots))
        included=[c.centre for i,c in enumerate(cs) if signature&(1<<i)]
        # Nested caps on the same vertex have different reference radii.
        # This exact covariant point must not depend on display arc samples.
        centres.append(scale(mean(included),len(included)/(len(included)+1)) if included else (0.,0.,0.))
    slots={(s.piece,s.face):i for i,s in enumerate(stickers)}
    cut_index={(key(c.centre),round(c.radius,8)):i for i,c in enumerate(cs)}
    face_index={key(n):i for i,n in enumerate(DODECA)}
    permutations=[];layers=[]
    for axis,normal in enumerate(axes):
        destinations=tuple(cut_index[(key(rotate(c.centre,normal,math.tau/3)),round(c.radius,8))] for c in cs)
        face_map=tuple(face_index[key(rotate(n,normal,math.tau/3))] for n in DODECA)
        def target(s):return sum(1<<destinations[i] for i in range(len(cs)) if s&(1<<i))
        axis_perms=[];axis_layers=[]
        for layer in range(2):
            moving=tuple(p for p,s in enumerate(signatures) if s&(1<<(2*axis+layer)))
            selected=set(moving)
            row=tuple(slots[owners[target(signatures[s.piece])],face_map[s.face]]
                      if s.piece in selected else i for i,s in enumerate(stickers))
            if sorted(row)!=list(range(len(stickers))):raise ValueError('Curvy Dinominx turn is not bijective')
            if any(row[row[row[i]]]!=i for i in range(len(row))):raise ValueError('Curvy Dinominx turn is not order three')
            axis_perms.append(row);axis_layers.append(moving)
        permutations.append(tuple(axis_perms));layers.append(tuple(axis_layers))
    return _patch_faces(Geometry(spec,tuple(stickers),tuple(pieces),tuple(centres),tuple(permutations),tuple(layers)))
