"""VeryPuzzle #59 D5: spherical skin on a twelve-axis Megaminx.

Twenty triangular colour regions are dual to the twelve turning caps.
Colour boundaries are spherical Voronoi edges. Mechanical seams are plane /
sphere circles, not a radial projection of flat Megaminx cuts. The chosen cut
height is a photographic proportion, not a manufacturer's measured dimension.
Mechanical piece IDs retain the standard Megaminx action; visible colour
panels follow the dual triangular scheme, including five-colour centres.
"""
from dataclasses import replace
from functools import lru_cache
from cube.polyhedral import (Geometry,Sticker,geometry as source_geometry,
                            dot,cross,add,scale,unit,mean,rotate,key)
import math

RADIUS=1.0
CUT_HEIGHT=.75


from cube.spherical_surfaces import outline as _outline


@lru_cache(maxsize=1)
def geometry():
    source=source_geometry('megaminx',3);normals=source.spec.normals
    colour_normals=tuple(unit(mean(tuple(normals[source.stickers[i].face] for i in slots)))
                         for slots in source.pieces if len(slots)==3)
    owners=tuple(sum(1<<axis for axis,bands in enumerate(source.layers) if p in bands[0])
                 for p in range(len(source.pieces)))
    colour_masks=tuple(owners[p] for p,slots in enumerate(source.pieces) if len(slots)==3)
    stickers=[];pieces=[]
    for piece,mask in enumerate(owners):
        slots=[]
        cuts=tuple((scale(n,-1) if mask&(1<<i) else n,
                    -CUT_HEIGHT if mask&(1<<i) else CUT_HEIGHT) for i,n in enumerate(normals))
        for face,normal in enumerate(colour_normals):
            # Incidence gives five patches at a cap centre, two on an edge,
            # and one complete triangular corner, without sampling.
            if mask&colour_masks[face]!=mask:continue
            planes=tuple((unit(add(n,scale(normal,-1))),0.) for i,n in enumerate(colour_normals)
                         if i!=face)+cuts
            try:polygon=_outline(planes)
            except ValueError as exc:
                if str(exc)=='Spherical panel has no boundary':continue
                raise
            # Exclude zero-area boundary contacts; those are not stickers.
            if len(polygon)<3:continue
            slots.append(len(stickers));stickers.append(Sticker(piece,face,polygon))
        pieces.append(tuple(slots))
    lookup={(s.piece,s.face):i for i,s in enumerate(stickers)}
    colour_index={key(n):i for i,n in enumerate(colour_normals)}
    permutations=[]
    for axis,(layer,) in enumerate(source.layers):
        old_action=source.permutations[axis][0];moving=set(layer);action=[]
        for i,s in enumerate(stickers):
            if s.piece not in moving:action.append(i);continue
            target=source.stickers[old_action[source.pieces[s.piece][0]]].piece
            face=colour_index[key(rotate(colour_normals[s.face],normals[axis],math.tau/5))]
            action.append(lookup[target,face])
        permutations.append((tuple(action),))
    return Geometry(replace(source.spec,kind='megaminx_ball',normals=colour_normals,cuts=(CUT_HEIGHT,)),
                    tuple(stickers),tuple(pieces),source.centres,tuple(permutations),source.layers)


@lru_cache(maxsize=1)
def skin():
    """Shared circular outlines and radial fans, without triangulation seams."""
    result=[]
    for sticker in geometry().stickers:
        hub=scale(unit(mean(sticker.polygon)),RADIUS);triangles=[]
        for a,b in zip(sticker.polygon,sticker.polygon[1:]+sticker.polygon[:1]):
            normal=cross(add(a,scale(hub,-1)),add(b,scale(hub,-1)))
            if dot(normal,normal)<1e-18:continue
            triangles.append(((hub,a,b),unit(normal),(unit(hub),unit(a),unit(b))))
        result.append(tuple(triangles))
    return tuple(result)


def _validate_minx(cube):
    """Local identities, independent even orbits and orientation sums."""
    from solver.polyhedral import identify,_parity
    state=identify(cube);g=cube.geometry
    for size,modulus in ((2,2),(3,3)):
        pieces=tuple(p for p,slots in enumerate(g.pieces) if len(slots)==size)
        indices={p:i for i,p in enumerate(pieces)}
        destinations=[indices[g.stickers[state[g.pieces[p][0]]].piece] for p in pieces]
        if _parity(destinations):raise ValueError('The entered pieces violate an orientation or permutation constraint')
        def ordered(piece):
            slots=sorted(g.pieces[piece],key=lambda i:g.stickers[i].face)
            if size==3:
                normals=[g.spec.normals[g.stickers[i].face] for i in slots]
                if dot(cross(normals[0],normals[1]),normals[2])<0:slots[1],slots[2]=slots[2],slots[1]
            return slots
        total=0
        for p in pieces:
            first=state[ordered(p)[0]]
            total+=ordered(g.stickers[first].piece).index(first)
        if total%modulus:raise ValueError('The entered pieces violate an orientation or permutation constraint')
    return state


def validate(cube):
    from solver.megaminx_ball import lift
    return lift(cube)


def solve(cube,cancel=None,progress=None):
    from solver.megaminx_ball import solve as solve_ball
    return solve_ball(cube,cancel,progress)
