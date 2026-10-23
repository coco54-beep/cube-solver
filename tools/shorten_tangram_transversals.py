"""Offline weighted Schreier loops, independent of any input scramble."""
import heapq
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solver.tangram_table import TangramTable, compact, geometry_fingerprint
from tools.optimize_tangram_tables import inverse


def shorten(kind, source_path):
    source = TangramTable(kind, source_path)
    identity = tuple(range(source.degree))
    original = {}
    def remember(pool, p, word):
        if p == identity:return
        word = compact(word)
        if p not in pool or len(word) < len(pool[p]):pool[p] = word
    for index, record in enumerate(source.records):
        remember(original, tuple(record['permutation']), source.strong_word(index+1))
    pool = original.copy()
    transversals = []
    for level, base in enumerate(source.base):
        for p, w in original.items():
            if all(p[b] == b for b in source.base[:level]):remember(pool, p, w)
        gens = dict(pool)
        for p, word in pool.items():
            remember(gens, tuple(inverse(p)), tuple(m.inverse(6) for m in reversed(word)))
        distances = {base: 0}
        paths = {base: (identity, ())}
        queue = [(0, base)]
        while queue:
            distance, beta = heapq.heappop(queue)
            if distance != distances[beta]:continue
            p, word = paths[beta]
            for g, gw in gens.items():
                target = g[beta]
                cost = distance + len(gw)
                if cost >= distances.get(target, float('inf')):continue
                distances[target] = cost
                paths[target] = tuple(g[x] for x in p), compact(word+gw)
                heapq.heappush(queue, (cost, target))
        assert set(paths) == set(source.transversals[level]), (level, len(paths))
        transversals.append(paths)
        following = {}
        for p, word in pool.items():
            if p[base] == base:remember(following, p, word)
        inverses = {beta: tuple(inverse(p)) for beta, (p, _) in paths.items()}
        for beta, (p, word) in paths.items():
            for g, gw in gens.items():
                gamma = g[beta]
                gi = inverses[gamma]
                loop = tuple(gi[g[x]] for x in p)
                candidate = word+gw+tuple(m.inverse(6) for m in reversed(paths[gamma][1]))
                remember(following, loop, candidate)
        # Keep bounded, reusable short algorithms; original strong generators
        # are reinserted at every level so the represented group cannot shrink.
        pool = dict(sorted(following.items(), key=lambda item:(len(item[1]),sum(i!=j for i,j in enumerate(item[0]))))[:5000])
        print(level, len(paths), max(map(len,(w for _,w in paths.values()))), len(pool), flush=True)
    data = dict(version=1, kind=kind, geometry=geometry_fingerprint(kind),
                degree=source.degree, base=source.base, moves=[], strong=[], transversals=[])
    for paths in transversals:
        orbit = {}
        for beta, (p, word) in paths.items():
            if word:
                index = len(data['strong'])
                data['strong'].append(dict(permutation=p, original=len(data['moves']), product=[]))
                data['moves'].append([[m.axis,m.layer,m.amount] for m in word])
                product = [index]
            else:product = []
            orbit[str(beta)] = dict(permutation=p, product=product)
        data['transversals'].append(orbit)
    out = Path('artifacts/development')/(kind+'-weighted-group.bin')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('saved',out,out.stat().st_size,flush=True)
    return out


if __name__ == '__main__':shorten(sys.argv[1], sys.argv[2])
