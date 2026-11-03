"""Exact native-word quotient for Starminx I's thirty oriented edges."""
import sys,json,zlib,math
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import simplify,inverse_word,apply_word,piece_orbits
from solver.lattice_data import geometry_key
from tools.weighted_group_builder import build
from sympy.combinatorics import Permutation,PermutationGroup


def main():
    started=monotonic();c=PolyhedralPuzzle('starminx_i',3);g=c.geometry
    core={p for orbit in piece_orbits('starminx_i',3) if len(orbit)!=60 for p in orbit}
    slots=tuple(i for p,piece in enumerate(g.pieces) if p in core for i in piece);index={s:i for i,s in enumerate(slots)}
    pool={}
    for m in c.moves():
        for a in range(1,5):
            move=Move(m.axis,m.layer,a);p=g.permutation(move)
            pool[tuple(index[p[i]] for i in slots)]=((m.axis,m.layer,a),)
    group=PermutationGroup([Permutation(p) for p in pool]);base=list(reversed(range(len(slots))))
    group._schreier_sims(base=base)
    def compact(raw):return tuple((m.axis,m.layer,m.amount) for m in simplify(tuple(Move(*m) for m in raw),5))
    def backwards(raw):return tuple((m.axis,m.layer,m.amount) for m in inverse_word(tuple(Move(*m) for m in raw),5))
    records=build(pool,base,group.basic_orbits,(),compact,backwards,limit=120,bucket_limit=180,preserve_group=True,
                  report=lambda *row:print(*row,flush=True))
    for row in records:
        for rec in row.values():
            action=apply_word(g,tuple(Move(*m) for m in rec['word']))
            assert tuple(index[action[s]] for s in slots)==tuple(rec['permutation'])
    macros=json.loads(Path('demo/data/expanded_macros.json').read_text())['models']['starminx_i']
    rec=next(rec for rec in macros if rec['role'][1]==1)
    action=apply_word(g,tuple(Move(*m) for m in rec['word']));origin=rec['pieces'][0]
    second=g.stickers[action[g.pieces[origin][0]]].piece
    third=g.stickers[action[g.pieces[second][0]]].piece
    data=dict(version=1,geometry=geometry_key(g),slots=slots,base=base,transversals=records,order=str(group.order()),
              centre_word=rec['word'],centre_base=(origin,second,third))
    target=Path('solver/data/starminx_i_edges.bin')
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('SAVED',target.stat().st_size,'bytes',round(monotonic()-started,3),'seconds',flush=True)


if __name__=='__main__':main()
