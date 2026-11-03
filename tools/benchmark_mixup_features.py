"""Compare cached cut checks with the previous per-piece reference engine."""
from functools import lru_cache
import json
from pathlib import Path
import random
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.mixup_reduction import geometry


def benchmark(kind,steps=100,repeats=5):
    model=geometry(kind);rng=random.Random(20261106);frames=tuple(model.cube.frames)
    samples=[]
    for _ in range(steps):
        features=model.state_features(frames)
        moves=[m for options in model._moves for _,m in options]
        samples.extend((frames,features,move) for move in rng.sample(moves,min(20,len(moves))))
        frames,_=rng.choice(list(model.children(frames,features,complete=True)))
    @lru_cache(maxsize=2048)
    def legacy_features(frames):
        return tuple(model.features[h][p] or model.feature(h,p) for h,p in enumerate(frames))
    def legacy_apply(frames,features,move):
        layers=getattr(move,'layers',()) or (move.layer,)
        bit=model._range_at.get((move.axis,tuple(layers)))
        if bit is None:return None
        flag=1<<bit
        if any(not f[2]&flag for f in features):return None
        ordinary,corners=model.turn_tables(move.axis,move.amount)
        child=list(frames);selected=False
        for home,f in enumerate(features):
            if not f[3]&flag:continue
            selected=True;pose=(corners if model._corners[home] else ordinary)[frames[home]]
            if pose==255:return None
            child[home]=pose
        if not selected:return None
        child=tuple(child);return child,legacy_features(child)
    # Warm per-piece geometric features equally before timing either engine.
    expected=[legacy_apply(*sample) for sample in samples]
    actual=[model.apply(*sample) for sample in samples]
    assert actual==expected
    timings={}
    for name,function in (('reference',legacy_apply),('cached',model.apply)):
        times=[]
        for _ in range(3):
            legacy_features.cache_clear();model._state_features.cache_clear()
            started=perf_counter()
            for _ in range(repeats):
                for sample in samples:function(*sample)
            times.append(perf_counter()-started)
        timings[name]=min(times)
    return dict(kind=kind,queries=len(samples)*repeats,identical_results=True,
                reference_seconds=round(timings['reference'],4),
                cached_seconds=round(timings['cached'],4),
                speedup=round(timings['reference']/timings['cached'],2))


if __name__=='__main__':
    rows=[benchmark(kind) for kind in ('mixup_333','mixup_plus_344','mixup_plus_444')]
    out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('reports/optimization/2026-10-26/mixup-feature-benchmark.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps(rows))
