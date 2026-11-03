"""Research full labelled chain; production uses build_material_stages.py.

The exhaustive chain can produce impractically long words. Keep its output
outside runtime solver data so it cannot replace the staged colour solver.
"""
import sys,json,zlib
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from cube.twins_aligned import AlignedTwins,generators,source_key
from cube.polyhedral import Move
from solver.polyhedral import simplify,inverse_word,apply_word,compose,inverse
from solver.lattice_data import geometry_key
from tools.weighted_group_builder import build
from tools.exact_group_certificate import Certificate

SUN='--sun' in sys.argv
SHORT='--short' in sys.argv
WITNESS='--witness' in sys.argv
if SUN:
    from cube.suncube_aligned import AlignedSunCube as AlignedTwins,generators,source_key


def run():
    started=monotonic();cube=AlignedTwins();g=cube.geometry
    pool={a:((i,0,g.spec.step(i)),) for i,(a,w) in enumerate(generators())}
    order=g.spec.turn_order
    def compact(raw):return tuple((m.axis,0,m.amount) for m in simplify(tuple(Move(*m) for m in raw),order))
    def backwards(raw):return tuple((m.axis,0,m.amount) for m in inverse_word(tuple(Move(*m) for m in raw),order))
    if SHORT:
        atoms=tuple(pool.items());near={};leaves={i for i,s in enumerate(g.stickers) if len(g.pieces[s.piece])==1}
        def commutator(a,aw,b,bw):
            p=compose(compose(compose(a,b),inverse(a)),inverse(b))
            return p,compact(aw+bw+backwards(aw)+backwards(bw))
        for a,aw in atoms:
            for b,bw in atoms:
                p,w=commutator(a,aw,b,bw);support={i for i,x in enumerate(p) if i!=x}
                if support and len(support)<=32:near.setdefault(p,w)
        extras={}
        for a,aw in near.items():
            support={i for i,x in enumerate(a) if i!=x}
            if len(support)<=6 and support<=leaves:extras[a]=aw
            for b,bw in atoms:
                p,w=commutator(a,aw,b,bw);support={i for i,x in enumerate(p) if i!=x}
                if support and len(support)<=6 and support<=leaves:
                    if p not in extras or len(w)<len(extras[p]):extras[p]=w
        print('SHORT_LEAF_TOOLS',len(extras),flush=True)
        pool.update(extras)
    base=sorted(range(len(cube.colors)),
        key=lambda s:(-len(g.pieces[g.stickers[s].piece]),-s))
    group=Certificate(len(base),base,track_words=WITNESS)
    from solver.polyhedral import Word
    for action in sorted(pool,key=lambda p:sum(i!=x for i,x in enumerate(p))):
        word=None
        if WITNESS:
            word=Word()
            for m in pool[action]:word=word.then(Word(move=Move(*m)))
        group.add(action,word)
    expected_orbits=[tuple(row) for row in group.trans]
    print('TWINS_ORDER',group.order,'GENERATORS',len(pool),flush=True)
    if WITNESS:
        print('STRONG_WORDS',len(group.words),'LONGEST',max(w.length for w in group.words.values()),flush=True)
        if '--probe-witness' in sys.argv:return
    def odd(p,o):return Permutation([sorted(o).index(p[i]) for i in sorted(o)]).is_odd
    left=set(base);orbits=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for beta in queue:
            for p in pool:
                if p[beta] not in orbit:orbit.add(p[beta]);queue.append(p[beta])
        orbits.append(orbit);left-=orbit
    parity=[o for o in orbits if len(o)>1 and any(odd(p,o) for p in pool)]
    records=build(pool,base,expected_orbits,parity,compact,backwards,
                  preserve_group=True,limit=100,bucket_limit=100,report=lambda *r:print(*r,flush=True))
    verified=0
    for row in records:
        for record in row.values():
            assert apply_word(g,tuple(Move(*m) for m in record['word']))==tuple(record['permutation'])
            verified+=1
    data=dict(version=1,geometry=geometry_key(g),source=source_key(),base=base,
              order=str(group.order),transversals=records,verified_transversals=verified,
              macros=[[(m.axis,m.layer,m.amount) for m in w] for a,w in generators()])
    target=Path('artifacts/research')/('suncube' if SUN else 'twins')/'full_colour_chain.bin'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target,target.stat().st_size,verified,monotonic()-started,flush=True)


if __name__=='__main__':run()
