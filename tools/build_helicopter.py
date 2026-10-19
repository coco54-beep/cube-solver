"""Prepare regular Helicopter Cube solving tables for desktop and Android."""
import json
import heapq
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import StabilizerChain, apply_word, piece_orbits, simplify, _parity
from solver.polyhedral_reduction import primitives


def build():
    cube = PolyhedralPuzzle('helicopter', 3)
    g = cube.geometry
    # Reverse sifting fixes corners first, then the triangular centres.
    points = tuple(sorted(range(len(g.stickers)),
                          key=lambda s: (len(g.pieces[g.stickers[s].piece]), s)))
    chain = StabilizerChain(cube, points=points)
    stages = []
    for table in chain.trans:
        stage = {}
        for pos, (permutation, word) in table.items():
            expanded = simplify(tuple(word.flatten(2)), 2)
            full = apply_word(g, expanded)
            if tuple(points[permutation[i]] for i in range(len(points))) != tuple(full[s] for s in points):
                raise ValueError('Helicopter prepared word does not match its permutation')
            stage[str(pos)] = dict(permutation=permutation,
                                  word=[(m.axis, m.layer, m.amount) for m in expanded])
        stages.append(stage)
    targets = {i: o for i, o in enumerate(piece_orbits('helicopter', 3))
               if len(g.pieces[o[0]]) == 1}
    macros = primitives(cube, targets, deep=True, use_prepared=False)
    centre_points = sum(len(o) for o in targets.values())
    point_index = {s:i for i,s in enumerate(points)}
    parity_moves = {}
    for table in stages[:centre_points]:
        for entry in table.values():
            signature = 0
            for bit, orbit in enumerate(targets.values()):
                ids = tuple(point_index[g.pieces[p][0]] for p in orbit)
                local = {s:i for i,s in enumerate(ids)}
                signature |= _parity([local[entry['permutation'][s]] for s in ids]) << bit
            word = entry['word']
            if signature and (signature not in parity_moves or len(word)<len(parity_moves[signature])):
                parity_moves[signature] = word
    # Only eight even parity signatures exist across the four centre rings.
    parity_words = {0: []}
    queue = [(0,0)]
    while queue:
        cost, signature = heapq.heappop(queue)
        if cost != len(parity_words[signature]):
            continue
        for bits, word in parity_moves.items():
            target = signature ^ bits
            combined = parity_words[signature] + word
            if target not in parity_words or len(combined)<len(parity_words[target]):
                parity_words[target] = combined
                heapq.heappush(queue,(len(combined),target))
    if len(parity_words) != 8:
        raise ValueError('Helicopter parity table is incomplete')
    record = dict(geometry=geometry_key(g), points=points, stages=stages,
                  centre_points=centre_points,
                  parity={str(i):word for i,word in parity_words.items()},
                  cycles={str(i): dict(word=[(m.axis,m.layer,m.amount) for m in word],base=base)
                          for i,(word,base) in macros.items()})
    path = Path(__file__).resolve().parents[1] / 'solver/data/helicopter.bin'
    path.write_bytes(zlib.compress(json.dumps(record,separators=(',',':')).encode(),9))
    print('table bytes',path.stat().st_size,'transversals',sum(map(len,stages)))


if __name__ == '__main__':
    build()
