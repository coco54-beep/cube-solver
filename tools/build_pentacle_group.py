"""Finite root group after independent continuous face-disc normalization."""
import json
import sys
import zlib
from collections import Counter
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from solver.pentacle_state import root_slots,normalize,permutation,geometry_fingerprint
from tools.weighted_group_builder import build


def compact(word):
    out=[]
    for a,l,n in word:
        if out and out[-1][:2]==(a,l):n+=out.pop()[2]
        n=round((n+180.)%360.-180.,10)
        if abs(n)>1e-6:out.append((a,l,n))
    return tuple(out)


def inverse_word(word):return tuple((a,l,-n) for a,l,n in reversed(word))


def run():
    started=monotonic();root,slots,centres=root_slots();identity=tuple(range(len(root.panels)));pool={}
    for face in range(6):
        for angle in (72,144,-144,-72):
            work=PentacleCube();work.apply_move(Move(face,0,angle));p=permutation(work)
            assert sorted(p)==list(identity);pool[p]=((face,0,angle),)
        for angle in (90,180,270):
            work=PentacleCube();alignment=work.alignment_moves(face);work.apply_moves(alignment)
            core=Move(face,1,angle);work.apply_move(core);work,correction=normalize(work)
            p=permutation(work);assert sorted(p)==list(identity)
            word=compact(tuple((m.axis,m.layer,m.amount) for m in alignment+(core,)+correction))
            if p not in pool or len(word)<len(pool[p]):pool[p]=word
    counts=Counter(p.home for p in root.panels)
    base=sorted(identity,key=lambda i:(i not in centres,-counts[root.panels[i].home],i))
    group=PermutationGroup([Permutation(p) for p in pool]);group._schreier_sims(base=base)
    print('ROOT GENERATORS',len(pool),'degree',len(identity),'order',group.order(),flush=True)
    records=build(pool,group.base,group.basic_orbits,group.orbits(),compact,inverse_word,
                  report=lambda *args:print('stabilizer',*args,flush=True))
    checked=0
    for orbit in records:
        for entry in orbit.values():
            work=PentacleCube();work.apply_moves(Move(*raw) for raw in entry['word'])
            assert permutation(work)==tuple(entry['permutation']);checked+=1
    data=dict(version=1,kind='pentacle',geometry=geometry_fingerprint(),base=group.base,transversals=records,
              order=str(group.order()),orbits=[sorted(o) for o in group.orbits()],
              goal_colors=[p.face for p in root.panels],verified_transversals=checked)
    out=Path('solver/data/pentacle_group.bin')
    out.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',out.stat().st_size,'verified',checked,'seconds',round(monotonic()-started,3),flush=True)


if __name__=='__main__':run()
