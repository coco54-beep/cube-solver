"""Remove colour-identical equivariant copies from the regular action only.

This is an exact action quotient, not a physical merger of separate pieces.
Full 192-field input is retained and checked against every omitted copy.
"""
from functools import lru_cache
from cube.twins_state import TwinsState
from cube.twins_aligned import generators as full_generators,AlignedTwins,geometry as full_geometry,expand
from cube.twins_cad_material import structure,fingerprint
from cube.polyhedral import Geometry,Spec,Sticker


@lru_cache(maxsize=1)
def reduction():
    g=full_geometry();actions=tuple(a for a,w in full_generators());left=set(range(192));orbits=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for s in queue:
            for a in actions:
                if a[s] not in orbit:orbit.add(a[s]);queue.append(a[s])
        orbits.append(tuple(sorted(orbit)));left-=orbit
    kept=[];representatives=[];copies=[]
    for orbit in orbits:
        if not all(len(g.pieces[g.stickers[s].piece])==1 for s in orbit):kept.extend(orbit);continue
        matched=None
        for rep in representatives:
            if len(rep)!=len(orbit):continue
            for target in orbit:
                mapping={rep[0]:target};queue=[rep[0]];valid=True
                for s in queue:
                    if g.stickers[s].face!=g.stickers[mapping[s]].face:valid=False;break
                    for a in actions:
                        u,v=a[s],a[mapping[s]]
                        if u in mapping:
                            if mapping[u]!=v:valid=False;break
                        else:mapping[u]=v;queue.append(u)
                    if not valid:break
                if valid and set(mapping.values())==set(orbit):matched=mapping;break
            if matched is not None:break
        if matched is None:kept.extend(orbit);representatives.append(orbit)
        else:copies.extend(sorted(matched.items()))
    return tuple(sorted(kept)),tuple(copies)


def compress(colors):
    if len(colors)!=192:raise ValueError('rigid.invalid')
    kept,copies=reduction()
    for a,b in copies:
        if colors[a]!=colors[b]:
            error=ValueError('tilted.group_unresolved');error.locations=[dict(sticker=a),dict(sticker=b)];raise error
    return tuple(colors[i] for i in kept)


@lru_cache(maxsize=1)
def layout():
    groups,regions,panels=structure();return groups,regions,tuple(panels[i] for i in reduction()[0])


class ReducedTwins(TwinsState):layout=staticmethod(layout)


@lru_cache(maxsize=1)
def generators():
    kept,copies=reduction();indices={s:i for i,s in enumerate(kept)}
    return tuple((tuple(indices[a[s]] for s in kept),w) for a,w in full_generators())


@lru_cache(maxsize=1)
def geometry():
    g=full_geometry();kept,copies=reduction();pieces=[[] for _ in g.pieces];stickers=[]
    for i,s in enumerate(kept):stickers.append(g.stickers[s]);pieces[g.stickers[s].piece].append(i)
    spec=Spec('_twins_cad_reduced',3,g.spec.normals,g.spec.axes,(),6,axis_steps=g.spec.axis_steps)
    return Geometry(spec,tuple(stickers),tuple(map(tuple,pieces)),g.centres,
                    tuple((a,) for a,w in generators()),g.layers)


class AlignedReducedTwins(AlignedTwins):
    puzzle_kind='_twins_cad_reduced'
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(reduction()[0]):raise ValueError('Wrong Twins quotient panel count')


def source_key():return fingerprint()+'-colour-equivariance-v1'
