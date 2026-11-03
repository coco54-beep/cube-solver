"""Cull only interfaces with a proven coincident whole-material neighbour.

Pieces in the same rotated arrangement can have different cubic local frames.
Reduce these frames modulo the 24 cubic symmetries, then look up every atom
on the other side of a cut. Unmatched interfaces stay visible. Animation
separates moving and stationary aggregates before this test, so their shared
cut opens correctly. This affects drawing only, never physical clearance.
"""
from functools import lru_cache
from cube.appearance import ROTATIONS
from cube.curvy_copter import multiply
from cube.flower_copter import canonical_frame_action,transform_mask


@lru_cache(maxsize=8192)
def basis(frame):
    candidates=[]
    for proper in ROTATIONS:
        key=tuple(round(v,8) for col in multiply(frame,proper) for v in col)
        candidates.append((key,proper))
    key,proper=min(candidates)
    inverse=tuple(tuple(proper[j][i] for j in range(3)) for i in range(3))
    return key,inverse


@lru_cache(maxsize=2)
def topology(kind):
    if kind=='flower':
        from cube.flower_material import structure
        atoms=structure()[0];owners={m:h for h,m in enumerate(atoms)}
        groups=tuple((m,) for m in atoms)
    else:
        from cube.twins_cad_material import structure,data,group
        homes={g:h for h,g in enumerate(structure()[0])}
        atoms=tuple(data()['atoms']);owners={m:homes[group(m)] for m in atoms}
        groups=tuple(tuple(m for m in atoms if owners[m]==h) for h in range(len(homes)))
    neighbours=tuple(tuple(tuple(m^(1<<axis) for m in row
                                  if m^(1<<axis) in owners and owners[m^(1<<axis)]!=h)
                            for axis in range(20)) for h,row in enumerate(groups))
    return groups,neighbours


@lru_cache(maxsize=16384)
def transformed(kind,mask,proper):
    if kind=='flower':return transform_mask(mask,canonical_frame_action(proper)[0])
    from cube.twins_cad_material import canonical_action
    edge,diag,cart,faces=canonical_action(proper)
    result=sum(1<<j for i,j in enumerate(edge) if mask&(1<<i))
    for start,mapping in ((12,diag),(16,cart)):
        result+=sum(1<<(start+j) for i,(j,flip) in enumerate(mapping) if bool(mask&(1<<(start+i)))!=flip)
    return result+(mask&(1<<19))


def visible_cuts(cube,kind,moving=()):
    groups,neighbours=topology(kind);moving=set(moving);placements=[];occupied=set()
    for h,frame in enumerate(cube.frames):
        bucket,proper=basis(frame);bucket=(bucket,h in moving);placements.append((bucket,proper))
        occupied.update((bucket,transformed(kind,m,proper)) for m in groups[h])
    return tuple(frozenset(axis for axis,row in enumerate(neighbours[h])
                           if not row or any((bucket,transformed(kind,m,proper)) not in occupied for m in row))
                 for h,(bucket,proper) in enumerate(placements))
