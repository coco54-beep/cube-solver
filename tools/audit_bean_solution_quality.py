"""Paired visible-only bean inputs; keep the original measured baseline."""
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble
from solver.dial_beans import solve

OUT=Path('reports/expansion/2026-10-26/bean-quality')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline='--baseline' in sys.argv
    if baseline:
        if (OUT/'before.json').exists():raise SystemExit('Recorded pre-change baseline already exists; it must not be overwritten.')
        rows=[]
        for kind,n in (('bean_6',6),('bean_10',10)):
            for length in (3,6,30,100):
                for seed in (20261026,20261027,20261028,20261029):
                    cube=PolyhedralPuzzle(kind,n);scramble(cube,length,seed)
                    rows.append(dict(kind=kind,n=n,turns=length,seed=seed,colors=list(cube.colors)))
    else:rows=json.loads((OUT/'before.json').read_text(encoding='utf8'))
    result=[]
    for row in rows:
        cube=PolyhedralPuzzle(row['kind'],row['n'],row['colors']);before=list(cube.colors)
        assert cube.scramble_history is None
        started=perf_counter();word=solve(cube);elapsed=perf_counter()-started
        assert cube.colors==before
        replay=cube.entered()
        for move in word:replay.apply_move(move)
        assert replay.is_solved()
        item=dict(row)
        prefix='before' if baseline else 'after'
        item[prefix+'_moves']=len(word);item[prefix+'_seconds']=round(elapsed,4)
        item['replay_solved']=True;result.append(item)
        print(row['kind'],row['turns'],row['seed'],len(word),round(elapsed,3),flush=True)
    (OUT/('before.json' if baseline else 'comparison.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    if not baseline:
        summary=dict(cases=len(result),before=sum(r['before_moves'] for r in result),
                     after=sum(r['after_moves'] for r in result),
                     improved=sum(r['after_moves']<r['before_moves'] for r in result),
                     worse=sum(r['after_moves']>r['before_moves'] for r in result),
                     max_seconds=max(r['after_seconds'] for r in result),history_free=True)
        summary['deep_cases']={}
        for kind in ('bean_6','bean_10'):
            group=[r for r in result if r['kind']==kind and r['turns']>=30]
            old=sum(r['before_moves'] for r in group);new=sum(r['after_moves'] for r in group)
            summary['deep_cases'][kind]=dict(cases=len(group),before=old,after=new,
                reduction_percent=round(100*(1-new/old),1),max_moves=max(r['after_moves'] for r in group))
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(summary)


if __name__=='__main__':main()
