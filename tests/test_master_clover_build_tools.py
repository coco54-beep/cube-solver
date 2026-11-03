"""Regressions exposed by the double-layer geometric and group probes."""
import math
from cube.polyhedral import CUBE,EDGE_AXES,Spec,scale,cross,dot
from cube.curved_partition import SphereCut,shell


def test_coincident_face_arcs_are_not_emitted_twice():
    # A sphere on the back edge can share the front trace of a different
    # sphere at the front edge. Both membership bits still matter in 3D.
    cuts=tuple(SphereCut(tuple(round(v) for v in scale(n,math.sqrt(2))),r)
               for r in (1.,math.sqrt(5)) for n in EDGE_AXES)
    panels=shell(Spec('coincident-traces',3,CUBE,EDGE_AXES,(),360),cuts)
    for face in range(6):
        area=sum(abs(sum(dot(cross(a,b),CUBE[f]) for a,b in zip(p,p[1:]+p[:1])))/2
                 for m,f,p in panels if f==face)
        assert math.isclose(area,4.,abs_tol=1e-8)


def test_more_than_sixteen_independent_parity_orbits_retain_the_exact_group():
    from tools.weighted_group_builder import build
    from tools.exact_group_certificate import Certificate
    degree=40;identity=tuple(range(degree));pool={};orbits=[]
    for i in range(20):
        p=list(identity);p[2*i],p[2*i+1]=p[2*i+1],p[2*i]
        pool[tuple(p)]=(i,);orbits.append({2*i,2*i+1})
    base=tuple(range(degree));cert=Certificate(degree,base)
    for p in pool:cert.add(p)
    assert cert.order==2**20
    rows=build(pool,base,[tuple(row) for row in cert.trans],orbits,tuple,lambda w:tuple(reversed(w)),preserve_group=True)
    assert math.prod(map(len,rows))==2**20
    for row in rows:
        for record in row.values():
            p=list(identity)
            for i in record['word']:p=[2*i+1 if v==2*i else 2*i if v==2*i+1 else v for v in p]
            assert tuple(p)==tuple(record['permutation'])
